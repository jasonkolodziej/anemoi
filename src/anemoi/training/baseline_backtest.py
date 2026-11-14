"""Operational guidance scored on the registry's own validation cases.

Every registered model carries its validation track error per basin
(`metrics.basin`), next to what holding the last motion scores on the same
windows. Neither says how good the number is: whether the windows are hard,
and what the forecasts a cycle already has to hand score on them. This
module scores those forecasts -- NHC's official forecast, the GFS tracker,
CLIPER -- from the ATCF a-decks (`data.atcf.parse_adeck`) on the windows
fusion and diffusion are validated on. If the consensus cannot beat the GFS
track it is given, the layers above GFS are subtracting value.

**The cases are the registry's by construction.** `validation_cases` calls
`real_latents.joint_stage_windows`, the function `extract_joint_latents`
itself builds its windows with: same storms, same initial times, same
emulated working fixes, same truth, same mask. Errors come from
`metrics.homogeneous`, which calls `metrics.track.verify`.

**Three samples, and no single headline.** A model's registered error is a
mean over every window (A). NHC issues no forecast for a remnant low or an
extratropical system, so the cases every technique has (B) are a subset,
and NHC's own published errors are for a narrower one still (C):

* ``A`` -- every registry window. Only what exists for all of them is
  scored here: the two persistence baselines, and the models.
* ``B`` -- the windows of A where every compared member has a forecast.
* ``C`` -- B, and a tropical or subtropical cyclone at both the initial
  and the verifying time: NHC's status rule.

A number is comparable only with another on the same sample. A registered
``{basin}/track_error_48h_nm`` belongs to A. The 70 nm promotion threshold
and NHC's published 48 h error are tropical-stage numbers, so only C is
commensurable with them -- and C still differs from NHC's sample, which
starts at a storm's first advisory (the windows start 24 h into the best
track) and, for the East Pacific, stops at 140W. `reconcile_official_errors`
applies NHC's rules in full and checks the join against NHC's own
per-forecast errors.

**Early and late guidance.** A cycle at ``t`` reads the ``t-6`` GFS run.
``AVNO`` at ``t`` is the run started at ``t``, which arrives after NHC's
``t+3`` advisory: context, not a fair comparator. ``AVNI`` is the previous
run's track shifted to the storm's position at ``t`` (the 6 h interpolation;
``AVN2`` is the 12 h one) and is what was available. ``AVNO-6`` is that
previous run's raw track at ``tau + 6``: the same model fields the project's
models read, with no interpolator. ECMWF's full runs start at 00 and 12Z
only, so its early track (``EMXI/EMX2``) is the 6 h interpolation at
06 and 18Z and the 12 h one at 00 and 12Z, about half each: not the EMXI
NHC verifies. `DECISION_RULE` says which
comparison decides, and is fixed before any model number exists.

**The project's own models** join through a per-case forecast file
(`ValidationForecasts`) that ``anemoi validation-forecasts`` writes where the
checkpoints and the gridded cache are. Without it only the two persistence
baselines link the samples.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import numpy as np

from ..data.atcf import Adeck, storm_basin
from ..data.besttrack import Fix, Track, TrackQuality, WorkingTrackNoise
from ..data.hurdat2 import TROPICAL_STATUSES
from ..data.noise_calibration import calibrate_season
from ..data.sources import Flavor
from ..data.splits import Split, assign_splits, filter_tracks
from ..data.storm_relative import displacement_nm
from ..geo import haversine_nm
from ..metrics.basin import PERSISTENCE_PREFIX, basin_key, per_basin_scores
from ..metrics.homogeneous import (
    BOOTSTRAP_RESAMPLES,
    INTENSITY,
    QUANTITIES,
    TRACK,
    HomogeneousRow,
    Member,
    case_errors,
    homogeneous_mask,
    score_homogeneous,
)
from ..models.base import DEFAULT_LEADS
from .capacity_ablation import SEQUENCE_LENGTH
from .real_latents import GROUP1_ORDER, joint_stage_windows
from .real_run import (
    LEAD_STEPS,
    StageWindow,
    boundaries_for_tracks,
    displacements_to_absolute,
    persistence_of,
    validation_metrics,
)

if TYPE_CHECKING:
    from ..data.nhc_verification import OfficialErrors
    from ..tracking.checkpoint_store import CheckpointStore
    from ..tracking.registry import ModelRegistry
    from .real_latents import JointLatentSamples

LEAD_HOURS: tuple[int, ...] = tuple(DEFAULT_LEADS)

#: NHC verifies the regular advisory. When a special advisory replaced it,
#: the a-deck keeps the regular one as OFCO and OFCL holds the special.
OFFICIAL = "OFCL=OFCO/OFCL"
#: The ECMWF track a cycle has. ECMWF's full runs start at 00 and 12Z, so
#: the a-deck interpolates them 6 h forward to 06 and 18Z (EMXI) and 12 h
#: forward to 00 and 12Z (EMX2): EMXI alone exists at half the initial times.
#: Named for both, so its errors are not read as NHC's EMXI verification.
ECMWF = "EMXI/EMX2"
#: The members scored unless told otherwise. CLP5 is not among them: its
#: track is OCD5's (`technique_diagnostics` measures it), so requiring both
#: could only shrink the sample.
DEFAULT_TECHNIQUES: tuple[str, ...] = (
    OFFICIAL, "AVNI", "AVNO-6", "AVNO", ECMWF, "OCD5", "XTRP",
)
#: What every member is compared with pairwise: the like-for-like GFS
#: track, and the official forecast.
DEFAULT_REFERENCES: tuple[str, ...] = ("AVNI", "OFCL")
#: NHC's skill baseline: CLIPER5 track with Decay-SHIFOR5 intensity.
SKILL_BASELINE = "OCD5"

#: Read from every a-deck whatever members are asked for: the working-fix
#: and technique diagnostics and the reconciliation use them.
DIAGNOSTIC_TECHNIQUES: tuple[str, ...] = ("CARQ", "CLP5", "OCD5", "AVNI", "AVN2", "OFCO", "OFCL")

PERSISTENCE = "persistence"
PERSISTENCE_BESTTRACK = "persistence_besttrack"

SAMPLES: dict[str, str] = {
    "A": "every registry validation window: the sample a registered "
         "{basin}/track_error_{lead}h_nm is a mean over",
    "B": "the windows of A where every compared member has a forecast and the verifying "
         "best-track fix is at the initial time plus the lead",
    "C": "B, and a tropical or subtropical cyclone (TD, TS, HU, SD, SS) at both the "
         "initial and the verifying time: NHC's status rule",
}

#: What a basin's rows are, where it is not what NHC's own tables are.
BASIN_NOTES: dict[str, str] = {
    "EP": "storm id EP: includes CPHC-issued forecasts for those storms west of 140W, "
          "which NHC's East Pacific verification leaves out",
    "CP": "storm id CP: CPHC's forecasts, with no NHC-published per-forecast counterpart",
}

DECISION_RULE = (
    "Fixed before any model number exists. Primary comparison: fusion against AVNI "
    "(the GFS track available at the cycle), Atlantic, 48 h track error, on samples B "
    "and C, with AVNO-6, EMXI/EMX2, OFCL and OCD5 beside it. Fusion's paired difference "
    "from AVNI (fusion minus AVNI) decides: positive with a storm-block interval that "
    "excludes zero on both samples, the ML layer subtracts value; negative and "
    "excluding zero on both, it adds value; otherwise this season does not decide. "
    "Beating AVNO-6 but not AVNI means the ML layer adds less than the interpolator's "
    "shift to the current position. AVNO is late guidance and decides nothing."
)

#: technique -> (kind, what it is). Anything else is plain ``guidance``.
_TECHNIQUES: dict[str, tuple[str, str]] = {
    "OFCL": ("official", "NHC/CPHC official forecast"),
    "OFCO": ("official", "official forecast, the regular advisory a special one replaced"),
    "AVNI": ("early", "GFS tracker, previous run interpolated 6 h to the cycle's position: "
                      "the GFS track available when the cycle runs"),
    "AVN2": ("early", "GFS tracker, the run before last interpolated 12 h"),
    "AVNO": ("late", "raw GFS tracker of the cycle's own run, which arrives after NHC's "
                     "t+3 h advisory; its wind is tracker output, not intensity guidance"),
    "EMXI": ("early", "ECMWF tracker, interpolated to the cycle's position: the 00/12Z run "
                      "shifted 6 h (EMXI) at 06/18Z, the run before shifted 12 h (EMX2) at "
                      "00/12Z -- the ECMWF track available when the cycle runs"),
    "EMX2": ("early", "ECMWF tracker, the run 12 h before interpolated to the cycle"),
    "EMX": ("late", "raw ECMWF tracker of the cycle's own run (00 and 12Z only)"),
    "OCD5": ("baseline", "CLIPER5 track with Decay-SHIFOR5 intensity: NHC's skill baseline"),
    "CLP5": ("baseline", "CLIPER5 climatology-and-persistence track (no intensity)"),
    "XTRP": ("baseline", "extrapolation of the current motion from the working fixes "
                         "(no intensity): persistence as an operational centre has it"),
    "TVCN": ("consensus", "NHC's variable track consensus (no intensity)"),
    "HCCA": ("consensus", "HFIP corrected consensus"),
}

_SPEC_RE = re.compile(
    r"(?:(?P<label>[A-Za-z0-9_+.-]+)=)?"
    r"(?P<techs>[A-Z0-9]{2,4}(?:/[A-Z0-9]{2,4})*)"
    r"(?:-(?P<lag>\d+))?"
)

#: Decimals kept in a written report: 0.001 nm and 0.001 kt.
_REPORT_DECIMALS = 3
#: Lists a written report keeps one entry per line: a row is a record to
#: be read by a program, and the printed table is the view for a person.
_ROW_LISTS: tuple[str, ...] = ("results", "sample_gap", "adecks")

#: A forecast file's base position must be the enumerated one to this many
#: degrees: the emulated fix is quantised to 0.1.
_BASE_TOLERANCE_DEG = 1e-6
#: Rounding of the forecast file: 1e-4 deg is 0.006 nm.
_POSITION_DECIMALS = 4
_WIND_DECIMALS = 2

#: How far a recomputed metric may sit from the registered one. A count is
#: exact; persistence comes from the same NumPy code; a model's forecast is
#: recomputed in float32 on another device.
_TOLERANCE_COUNT = 0.0
_TOLERANCE_PERSISTENCE = 1e-3
_TOLERANCE_MODEL = 0.5


class BaselineBacktestError(RuntimeError):
    pass


# --- the cases ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ValidationCases:
    """The registry's validation windows, one row each, in training's order."""

    storm_ids: tuple[str, ...]
    init_times: tuple[datetime, ...]
    #: The emulated working fix the models read at the initial time.
    base_lat: np.ndarray
    base_lon: np.ndarray
    #: The final best-track fix at the initial time.
    best_lat: np.ndarray
    best_lon: np.ndarray
    #: Truth, ``(n, n_leads, 3)`` absolute (lat, lon, wind_kt), built from the
    #: displacement targets as training builds it.
    obs_abs: np.ndarray
    #: The registry's mask: the verifying best-track fix exists.
    mask: np.ndarray
    #: That fix is at the initial time plus the lead. Training finds it by
    #: position in the track, so a dropped best-track row would shift it.
    time_ok: np.ndarray
    #: `real_run.StageWindow.persistence`, absolute: the registry's baseline.
    persistence_abs: np.ndarray
    #: The same rule from the un-noised best-track fixes.
    persistence_besttrack_abs: np.ndarray
    #: The last 6 h motion (east, north; nm) of the emulated fixes, and of
    #: the best track.
    base_motion_nm: np.ndarray
    best_motion_nm: np.ndarray
    #: HURDAT2 status at the initial time, and at each verifying time.
    init_status: tuple[str, ...]
    verif_status: tuple[tuple[str, ...], ...]
    lead_hours: tuple[int, ...]
    seasons: tuple[int, int]
    seed: int
    n_augment: int

    def __len__(self) -> int:
        return len(self.storm_ids)

    def index(self) -> dict[tuple[str, datetime], int]:
        return {key: i for i, key in enumerate(zip(self.storm_ids, self.init_times, strict=True))}

    def tropical_mask(self) -> np.ndarray:
        """``(n, n_leads)``: a tropical or subtropical cyclone at both the
        initial and the verifying time."""
        init = np.array([s in TROPICAL_STATUSES for s in self.init_status])
        verif = np.array([[s in TROPICAL_STATUSES for s in row] for row in self.verif_status])
        return init[:, None] & verif.reshape(len(self), len(self.lead_hours))

    @property
    def basins(self) -> tuple[str, ...]:
        return tuple(sorted({storm_basin(s) for s in self.storm_ids}))


def validation_tracks(tracks: list[Track]) -> list[Track]:
    """The storms of Stage B's validation split: the storms the cases come
    from, and the ones a-decks are needed for."""
    boundaries = boundaries_for_tracks(Flavor.GDAS_FINETUNE, tracks)
    return filter_tracks(tracks, assign_splits(tracks, boundaries), Split.VAL)


def validation_cases(
    tracks: list[Track],
    statuses: Mapping[tuple[str, datetime], str],
    *,
    seed: int = 20260806,
    n_augment: int = 1,
) -> ValidationCases:
    """Enumerate the validation windows fusion and diffusion are scored on.

    ``tracks`` are the training storms (`cli._training_tracks`), in the
    file's order; ``statuses`` is `data.hurdat2.parse_hurdat2_statuses` of
    the same file. ``seed`` and ``n_augment`` must be the latents task's
    (`real_orchestrator._run_latents`: the run's seed, and 1), or the cases
    are the same and the working fixes are not.
    """
    _train, windows = joint_stage_windows(tracks, seed=seed, n_augment=n_augment)
    if not windows:
        raise BaselineBacktestError("the validation split has no windows")
    finals = {t.storm_id: t for t in tracks}
    positions = {
        t.storm_id: {f.valid_time: i for i, f in enumerate(t.fixes)}
        for t in validation_tracks(tracks)
    }
    n, n_leads = len(windows), len(LEAD_STEPS)

    base_lat = np.array([sw.current.lat for sw in windows])
    base_lon = np.array([sw.current.lon for sw in windows])
    mask = np.stack([sw.mask for sw in windows])
    obs_abs = displacements_to_absolute(
        np.stack([sw.y for sw in windows]), base_lat[:, None], base_lon[:, None],
    )
    persistence_abs = displacements_to_absolute(
        persistence_of(windows), base_lat[:, None], base_lon[:, None],
    )

    best_windows: list[StageWindow] = []
    time_ok = np.zeros((n, n_leads), dtype=bool)
    init_status: list[str] = []
    verif_status: list[tuple[str, ...]] = []
    for i, sw in enumerate(windows):
        final = finals[sw.storm_id]
        init = sw.current.valid_time
        idx = positions[sw.storm_id][init]
        best_windows.append(StageWindow(
            storm_id=sw.storm_id, window=final.fixes[idx - SEQUENCE_LENGTH : idx + 1],
            current=final.fixes[idx], y=sw.y, mask=sw.mask,
        ))
        init_status.append(statuses.get((sw.storm_id, init), ""))
        row = []
        for li, step in enumerate(LEAD_STEPS):
            if not sw.mask[li]:
                row.append("")
                continue
            target = final.fixes[idx + step]
            time_ok[i, li] = target.valid_time == init + timedelta(hours=LEAD_HOURS[li])
            row.append(statuses.get((sw.storm_id, target.valid_time), ""))
        verif_status.append(tuple(row))

    best_lat = np.array([bw.current.lat for bw in best_windows])
    best_lon = np.array([bw.current.lon for bw in best_windows])
    seasons = boundaries_for_tracks(Flavor.GDAS_FINETUNE, tracks)[Split.VAL]
    return ValidationCases(
        storm_ids=tuple(sw.storm_id for sw in windows),
        init_times=tuple(sw.current.valid_time for sw in windows),
        base_lat=base_lat, base_lon=base_lon, best_lat=best_lat, best_lon=best_lon,
        obs_abs=obs_abs, mask=mask, time_ok=time_ok,
        persistence_abs=persistence_abs,
        persistence_besttrack_abs=displacements_to_absolute(
            persistence_of(best_windows), best_lat[:, None], best_lon[:, None],
        ),
        base_motion_nm=np.array([displacement_nm(sw.window[-2], sw.window[-1]) for sw in windows]),
        best_motion_nm=np.array(
            [displacement_nm(bw.window[-2], bw.window[-1]) for bw in best_windows]
        ),
        init_status=tuple(init_status), verif_status=tuple(verif_status),
        lead_hours=LEAD_HOURS, seasons=(int(seasons[0]), int(seasons[1])),
        seed=seed, n_augment=n_augment,
    )


# --- the members -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TechniqueSpec:
    """One a-deck member: ``[LABEL=]TECH[/TECH...][-LAG]``.

    ``AVNO`` is the technique at the case's own initial time. ``OFCO/OFCL``
    takes, for each initial time, the first of the techniques that has any
    row for it. ``AVNO-6`` is the run ``LAG`` hours earlier, read at
    ``tau + LAG``: the same valid times from the previous run.
    """

    name: str
    techniques: tuple[str, ...]
    lag_hours: int = 0

    @classmethod
    def parse(cls, text: str) -> TechniqueSpec:
        match = _SPEC_RE.fullmatch(text.strip())
        if match is None:
            raise BaselineBacktestError(
                f"not a technique spec: {text!r} (expected [LABEL=]TECH[/TECH...][-LAG], "
                "e.g. AVNI, OFCL=OFCO/OFCL, AVNO-6)"
            )
        lag = int(match.group("lag") or 0)
        if lag % 6:
            raise BaselineBacktestError(f"{text!r}: the lag must be a multiple of 6 hours")
        techniques = tuple(match.group("techs").split("/"))
        default = match.group("techs") + (f"-{lag}" if lag else "")
        return cls(name=match.group("label") or default, techniques=techniques, lag_hours=lag)

    @property
    def _known(self) -> tuple[str, str]:
        key = self.name if self.name in _TECHNIQUES else self.techniques[0]
        return _TECHNIQUES.get(key, ("guidance", "a-deck technique"))

    @property
    def kind(self) -> str:
        return "lagged" if self.lag_hours else self._known[0]

    @property
    def description(self) -> str:
        if self.lag_hours:
            return (
                f"{'/'.join(self.techniques)} of the run {self.lag_hours} h before the cycle, "
                f"read at tau + {self.lag_hours} (the same valid times), not shifted to the "
                "storm's current position. For AVNO-6: the raw track of the GFS run a "
                "cycle's model fields come from"
            )
        what = self._known[1]
        if len(self.techniques) > 1:
            what += f"; {' then '.join(self.techniques)}, whichever an initial time has first"
        return what


def techniques_to_read(techniques: Sequence[str] = DEFAULT_TECHNIQUES) -> frozenset[str]:
    """The a-deck techniques a run of ``techniques`` reads: the members'
    own, and the diagnostics'."""
    wanted = set(DIAGNOSTIC_TECHNIQUES)
    for text in techniques:
        wanted.update(TechniqueSpec.parse(text).techniques)
    return frozenset(wanted)


def technique_member(
    spec: TechniqueSpec, cases: ValidationCases, adecks: Mapping[str, Adeck],
) -> tuple[Member, dict[str, dict[str, int]]]:
    """``spec``'s forecast for each case, from the case's own storm's
    a-deck, and how many cases each technique supplied in each basin."""
    pred = np.full(cases.obs_abs.shape, np.nan)
    used: dict[str, dict[str, int]] = {}
    init_times: dict[tuple[str, str], frozenset[datetime]] = {}
    lag = timedelta(hours=spec.lag_hours)
    for i, (storm_id, case_time) in enumerate(zip(cases.storm_ids, cases.init_times, strict=True)):
        adeck = adecks.get(storm_id)
        if adeck is None:
            continue
        init = case_time - lag
        for tech in spec.techniques:
            key = (storm_id, tech)
            if key not in init_times:
                init_times[key] = adeck.init_times(tech)
            if init in init_times[key]:
                break
        else:
            continue
        by_basin = used.setdefault(storm_basin(storm_id), {})
        by_basin[tech] = by_basin.get(tech, 0) + 1
        for li, lead in enumerate(cases.lead_hours):
            point = adeck.get(tech, init, lead + spec.lag_hours)
            if point is None:
                continue
            if point.has_position:
                pred[i, li, 0], pred[i, li, 1] = point.lat, point.lon
            if point.max_wind_kt is not None:
                pred[i, li, 2] = point.max_wind_kt
    return Member(spec.name, spec.kind, pred, spec.description), used


def persistence_members(cases: ValidationCases) -> list[Member]:
    """The registry's baseline, and the same rule without the input noise."""
    return [
        Member(
            PERSISTENCE, "registry_baseline", cases.persistence_abs,
            "the registry's baseline: the last 6 h motion and the current wind of the "
            "emulated working fixes, held (`real_run.StageWindow.persistence`)",
        ),
        Member(
            PERSISTENCE_BESTTRACK, "diagnostic", cases.persistence_besttrack_abs,
            "the same rule from the un-noised final best track: what the registry's "
            "baseline scores without the emulator's noise",
        ),
    ]


# --- the project's models: the per-case forecast file ------------------------


@dataclass(frozen=True, slots=True)
class ValidationForecasts:
    """Each model's forecast for each validation case it has one for:
    the file ``anemoi validation-forecasts`` writes on the training machine
    and ``anemoi baseline-backtest --model-forecasts`` reads here."""

    header: dict
    storm_ids: tuple[str, ...]
    init_times: tuple[datetime, ...]
    base_lat: np.ndarray
    base_lon: np.ndarray
    #: model -> ``(n, n_leads, 3)`` absolute (lat, lon, wind_kt).
    forecasts: dict[str, np.ndarray]

    def __len__(self) -> int:
        return len(self.storm_ids)

    @property
    def consistent(self) -> bool:
        return bool(self.header.get("consistent"))

    def to_dict(self) -> dict:
        cases = []
        for i, (storm_id, init) in enumerate(zip(self.storm_ids, self.init_times, strict=True)):
            cases.append({
                "storm_id": storm_id,
                "init_time": f"{init:%Y%m%d%H}",
                "base": [float(self.base_lat[i]), float(self.base_lon[i])],
                "forecasts": {
                    model: _json_rows(_rounded(values[i]))
                    for model, values in self.forecasts.items()
                },
            })
        return {**self.header, "models": list(self.forecasts), "cases": cases}

    def write(self, path: Path | str) -> None:
        """One case per line: small enough to commit, still readable."""
        body = self.to_dict()
        cases = body.pop("cases")
        head = json.dumps(body, indent=2)
        lines = ",\n".join("    " + json.dumps(c, separators=(",", ":")) for c in cases)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{head[:-2]},\n  \"cases\": [\n{lines}\n  ]\n}}\n", encoding="utf-8")

    @classmethod
    def from_dict(cls, body: Mapping) -> ValidationForecasts:
        try:
            if body["kind"] != "validation_forecasts":
                raise KeyError("kind")
            cases = body["cases"]
            models = list(body["models"])
            header = {k: v for k, v in body.items() if k not in ("cases", "models")}
            forecasts = {
                m: np.array([c["forecasts"][m] for c in cases], dtype=float).reshape(
                    len(cases), len(body["lead_hours"]), 3,
                )
                for m in models
            }
            return cls(
                header=header,
                storm_ids=tuple(str(c["storm_id"]) for c in cases),
                init_times=tuple(
                    datetime.strptime(c["init_time"], "%Y%m%d%H").replace(tzinfo=UTC)
                    for c in cases
                ),
                base_lat=np.array([c["base"][0] for c in cases], dtype=float),
                base_lon=np.array([c["base"][1] for c in cases], dtype=float),
                forecasts=forecasts,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise BaselineBacktestError(f"not a validation-forecasts file: {exc!r}") from exc

    @classmethod
    def read(cls, path: Path | str) -> ValidationForecasts:
        try:
            body = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise BaselineBacktestError(f"cannot read {path}: {exc}") from exc
        return cls.from_dict(body)


def _json_rows(values: np.ndarray) -> list:
    """Nested lists, with ``null`` for a missing (NaN) value: valid JSON,
    and `from_dict`'s ``dtype=float`` reads it back as NaN."""
    return [[None if not np.isfinite(x) else float(x) for x in row] for row in values]


def _rounded(values: np.ndarray) -> np.ndarray:
    out = np.array(values, dtype=float)
    out[..., :2] = np.round(out[..., :2], _POSITION_DECIMALS)
    out[..., 2] = np.round(out[..., 2], _WIND_DECIMALS)
    return out


def _join(
    cases: ValidationCases,
    storm_ids: Sequence[str],
    init_times: Sequence[datetime],
    base_lat: np.ndarray,
    base_lon: np.ndarray,
) -> np.ndarray:
    """Each forecast row's index among ``cases``. Raises when a row is not
    one of the cases or starts from another working fix: a different seed,
    augmentation count or HURDAT2 file, whose forecasts are for other
    inputs and must not be scored as these."""
    index = cases.index()
    rows = np.empty(len(storm_ids), dtype=int)
    for j, key in enumerate(zip(storm_ids, init_times, strict=True)):
        i = index.get(key)
        if i is None:
            raise BaselineBacktestError(
                f"forecast for {key[0]} {key[1]:%Y-%m-%d %HZ} is not a validation window of "
                f"this HURDAT2 file with seed {cases.seed}"
            )
        offset = max(abs(base_lat[j] - cases.base_lat[i]), abs(base_lon[j] - cases.base_lon[i]))
        if offset > _BASE_TOLERANCE_DEG:
            raise BaselineBacktestError(
                f"{key[0]} {key[1]:%Y-%m-%d %HZ}: the forecast starts from "
                f"({base_lat[j]:.1f}, {base_lon[j]:.1f}), the enumerated working fix is "
                f"({cases.base_lat[i]:.1f}, {cases.base_lon[i]:.1f}) -- not the same seed, "
                "augmentation count or HURDAT2 file"
            )
        rows[j] = i
    if len(set(rows.tolist())) != len(rows):
        raise BaselineBacktestError("the forecasts name a validation window more than once")
    return rows


def model_members(
    cases: ValidationCases, forecasts: ValidationForecasts, models: Sequence[str],
) -> tuple[list[Member], int]:
    """``models``' forecasts as members on ``cases``, and how many cases
    the file has no forecast for (windows training skipped for a missing
    or unusable cached field: no member there, so no sample includes them).
    """
    if tuple(forecasts.header.get("lead_hours", ())) != cases.lead_hours:
        raise BaselineBacktestError("the forecast file's lead hours are not the cases'")
    unknown = [m for m in models if m not in forecasts.forecasts]
    if unknown:
        raise BaselineBacktestError(
            f"the forecast file has no {unknown}; it has {sorted(forecasts.forecasts)}"
        )
    rows = _join(
        cases, forecasts.storm_ids, forecasts.init_times, forecasts.base_lat, forecasts.base_lon,
    )
    dumped = forecasts.forecasts.get(PERSISTENCE)
    if dumped is not None:
        ours = cases.persistence_abs[rows]
        if np.abs(dumped - _rounded(ours))[cases.mask[rows]].max(initial=0.0) > 1e-3:
            raise BaselineBacktestError(
                "the forecast file's persistence is not the enumerated windows' persistence"
            )
    versions = forecasts.header.get("versions", {})
    members = []
    for model in models:
        pred = np.full(cases.obs_abs.shape, np.nan)
        pred[rows] = forecasts.forecasts[model]
        version = versions.get(model)
        members.append(Member(
            model, "model", pred,
            f"registered {model}" + (f" v{version}" if version is not None else "")
            + ", from the per-case forecast file",
        ))
    return members, len(cases) - len(rows)


# --- NHC's own verification --------------------------------------------------


def reconcile_official_errors(
    tracks: Sequence[Track],
    statuses: Mapping[tuple[str, datetime], str],
    adecks: Mapping[str, Adeck],
    official: Mapping[str, OfficialErrors],
    *,
    spec: TechniqueSpec | None = None,
    lead_hours: Sequence[int] = LEAD_HOURS,
) -> dict[str, dict]:
    """Score the official forecast under NHC's own rules and compare, case
    by case, with the errors NHC published.

    For each basin NHC publishes a file for: every initial time of every
    storm in ``tracks`` (not only the windows: NHC has no 24 h spin-up),
    the regular advisory, a tropical or subtropical cyclone at both times,
    and the initial position inside the file's stated domain. If the join
    is right, the cases are NHC's and each error is NHC's to its rounding.
    """
    spec = spec or TechniqueSpec.parse(OFFICIAL)
    out: dict[str, dict] = {}
    for basin, theirs in sorted(official.items()):
        storms = [t for t in tracks if storm_basin(t.storm_id) == basin]
        ids = {t.storm_id for t in storms}
        per_lead: dict[int, dict] = {
            lead: {
                "ours": [], "diff": [], "intensity_diff": [],
                "not_counted": {
                    "not_tropical_at_both_times": 0,
                    "initial_position_outside_domain": 0,
                    "unexplained": 0,
                },
            }
            for lead in lead_hours
        }
        seen: set[tuple[str, datetime, int]] = set()
        for track in storms:
            adeck = adecks.get(track.storm_id)
            by_time = {f.valid_time: f for f in track.fixes}
            if adeck is None:
                continue
            init_times = {tech: adeck.init_times(tech) for tech in spec.techniques}
            for fix in track.fixes:
                tech = next((t for t in spec.techniques if fix.valid_time in init_times[t]), None)
                if tech is None:
                    continue
                for lead in lead_hours:
                    point = adeck.get(tech, fix.valid_time, lead)
                    verif = by_time.get(fix.valid_time + timedelta(hours=lead))
                    if point is None or not point.has_position or verif is None:
                        continue
                    key = (track.storm_id, fix.valid_time, lead)
                    row = per_lead[lead]
                    published = theirs.track_nm.get(key)
                    tropical = (
                        statuses.get((track.storm_id, fix.valid_time)) in TROPICAL_STATUSES
                        and statuses.get((track.storm_id, verif.valid_time)) in TROPICAL_STATUSES
                    )
                    reason = (
                        "not_tropical_at_both_times" if not tropical
                        else "initial_position_outside_domain"
                        if not theirs.in_domain(fix.lat, fix.lon)
                        else None
                    )
                    if reason is not None:
                        # Ours to score, not NHC's to count. One NHC did
                        # count all the same shows up under n_only_in_nhc.
                        row["not_counted"][reason] += int(published is None)
                        continue
                    error = float(haversine_nm(verif.lat, verif.lon, point.lat, point.lon))
                    row["ours"].append(error)
                    if published is None:
                        row["not_counted"]["unexplained"] += 1
                        continue
                    seen.add(key)
                    row["diff"].append(abs(error - published))
                    signed = theirs.intensity_kt.get(key)
                    if signed is not None and point.max_wind_kt is not None:
                        row["intensity_diff"].append(
                            abs((point.max_wind_kt - verif.max_wind_kt) - signed)
                        )
        seasons = {t.season for t in storms}
        leads_out = {}
        for lead in lead_hours:
            row = per_lead[lead]
            nhc = [
                v for (sid, _t, ld), v in theirs.track_nm.items()
                if ld == lead and sid[:2] == basin and int(sid[-4:]) in seasons
            ]
            only_nhc = sum(
                1 for key in theirs.track_nm
                if key[2] == lead and key[0] in ids and key not in seen
            )
            leads_out[str(lead)] = {
                "n_ours": len(row["ours"]),
                "mean_ours_nm": _mean_or_none(row["ours"]),
                "n_nhc": len(nhc),
                "mean_nhc_nm": _mean_or_none(nhc),
                "n_common": len(row["diff"]),
                "max_abs_diff_nm": max(row["diff"], default=None),
                "n_common_intensity": len(row["intensity_diff"]),
                "max_abs_intensity_diff_kt": max(row["intensity_diff"], default=None),
                "ours_not_counted_by_nhc": row["not_counted"],
                "n_only_in_nhc": only_nhc,
            }
        nhc_storms = {
            sid for (sid, _t, _ld) in theirs.track_nm
            if sid[:2] == basin and int(sid[-4:]) in seasons
        }
        out[basin] = {
            "seasons": sorted(seasons),
            "official": spec.name,
            "rules": "regular advisory; tropical or subtropical at both times; every "
                     "initial time; initial position inside NHC's stated domain",
            "domain_south_north_west_east": None if theirs.domain is None else list(theirs.domain),
            "storms_only_in_nhc": sorted(nhc_storms - ids),
            "storms_without_adeck": sorted(ids - set(adecks)),
            "by_lead": leads_out,
        }
    return out


def _mean_or_none(values: Sequence[float]) -> float | None:
    return float(np.mean(values)) if len(values) else None


# --- diagnostics -------------------------------------------------------------


def _rms(values: np.ndarray) -> float | None:
    return float(np.sqrt(np.mean(np.square(values)))) if len(values) else None


def working_fix_diagnostics(
    cases: ValidationCases, tracks: Sequence[Track], adecks: Mapping[str, Adeck],
) -> dict:
    """How the emulated working fixes the models read compare with what was
    really issued: CARQ at tau 0 is the as-issued position and intensity
    of each cycle, and CARQ at tau -6 the history a cycle had.

    ``calibration`` is `data.noise_calibration.calibrate_season` on every
    CARQ/best-track pair of the validation storms: the three numbers
    ``configs/curriculum.yaml`` ``working_track_noise`` asks for. ``on_cases``
    puts the real and the emulated error side by side on the cases that
    have both, for the starting position and for the 6 h motion vector
    (which persistence extrapolates and the track models read).
    """
    working: dict[str, list[Fix]] = {}
    for track in tracks:
        adeck = adecks.get(track.storm_id)
        if adeck is None:
            continue
        for init in sorted(adeck.init_times("CARQ")):
            point = adeck.get("CARQ", init, 0)
            if (
                point is None or not point.has_position or point.max_wind_kt is None
                or point.min_pressure_mb is None
            ):
                continue
            working.setdefault(track.storm_id, []).append(Fix(
                storm_id=track.storm_id, valid_time=init, lat=point.lat, lon=point.lon,
                max_wind_kt=point.max_wind_kt, min_pressure_mb=point.min_pressure_mb,
                quality=TrackQuality.WORKING,
            ))
    calibration = calibrate_season(working, list(tracks)) if working else None

    on_cases: dict[str, dict] = {}
    basins = np.array([storm_basin(s) for s in cases.storm_ids])
    position = np.full(len(cases), np.nan)
    motion = np.full(len(cases), np.nan)
    for i, (storm_id, init) in enumerate(zip(cases.storm_ids, cases.init_times, strict=True)):
        adeck = adecks.get(storm_id)
        now = adeck.get("CARQ", init, 0) if adeck else None
        if now is None or not now.has_position:
            continue
        position[i] = haversine_nm(cases.best_lat[i], cases.best_lon[i], now.lat, now.lon)
        before = adeck.get("CARQ", init, -6)
        if before is not None and before.has_position:
            dx, dy = _displacement(before.lat, before.lon, now.lat, now.lon)
            motion[i] = np.hypot(*(np.array([dx, dy]) - cases.best_motion_nm[i]))
    emulated_position = np.asarray(
        haversine_nm(cases.best_lat, cases.best_lon, cases.base_lat, cases.base_lon), dtype=float,
    )
    emulated_motion = np.hypot(*(cases.base_motion_nm - cases.best_motion_nm).T)
    for basin in sorted(set(basins.tolist())):
        has_position = (basins == basin) & np.isfinite(position)
        has_motion = (basins == basin) & np.isfinite(motion)
        on_cases[basin] = {
            "n_cases": int((basins == basin).sum()),
            "n_with_carq": int(has_position.sum()),
            "position_error_mean_nm": {
                "as_issued": _mean_or_none(position[has_position]),
                "emulated": _mean_or_none(emulated_position[has_position]),
            },
            "position_error_rms_nm": {
                "as_issued": _rms(position[has_position]),
                "emulated": _rms(emulated_position[has_position]),
            },
            "n_with_carq_motion": int(has_motion.sum()),
            "motion_6h_error_rms_nm": {
                "as_issued": _rms(motion[has_motion]),
                "emulated": _rms(emulated_motion[has_motion]),
            },
        }
    return {
        "source": "a-deck CARQ rows (tau 0: the as-issued fix of each cycle; tau -6: the "
                  "history the cycle had) against the final best track",
        "calibration": calibration,
        "on_cases": on_cases,
    }


def _displacement(lat0: float, lon0: float, lat1: float, lon1: float) -> tuple[float, float]:
    """`storm_relative.displacement_nm` for two bare positions."""
    return displacement_nm(SimpleNamespace(lat=lat0, lon=lon0), SimpleNamespace(lat=lat1, lon=lon1))


def technique_diagnostics(cases: ValidationCases, adecks: Mapping[str, Adeck]) -> dict:
    """Two facts the default member list rests on, measured rather than
    assumed: CLP5's track is OCD5's (so only one is required), and how
    many cases have the 12 h interpolation (AVN2) but not the 6 h one."""
    distances = []
    for adeck in adecks.values():
        for (tech, init, tau), clp5 in adeck.points.items():
            ocd5 = adeck.get("OCD5", init, tau) if tech == "CLP5" else None
            if ocd5 is not None and clp5.has_position and ocd5.has_position:
                distances.append(haversine_nm(clp5.lat, clp5.lon, ocd5.lat, ocd5.lon))
    avn2_only: dict[str, int] = {}
    for storm_id, init in zip(cases.storm_ids, cases.init_times, strict=True):
        adeck = adecks.get(storm_id)
        if adeck is None:
            continue
        if adeck.get("AVNI", init, 0) is None and adeck.get("AVN2", init, 0) is not None:
            basin = storm_basin(storm_id)
            avn2_only[basin] = avn2_only.get(basin, 0) + 1
    return {
        "clp5_vs_ocd5_track": {
            "n_common_points": len(distances),
            "max_distance_nm": float(max(distances)) if distances else None,
        },
        "cases_with_avn2_but_not_avni": {
            basin: avn2_only.get(basin, 0) for basin in cases.basins
        },
    }


# --- the report --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegisteredError:
    """A model's registered ``{basin}/track_error_{lead}h_nm``, as given."""

    model: str
    basin: str
    lead_hours: int
    track_error_nm: float

    @classmethod
    def parse(cls, text: str) -> RegisteredError:
        match = re.fullmatch(r"(\w+):([A-Z]{2}):(\d+)=([0-9.]+)", text.strip())
        if match is None:
            raise BaselineBacktestError(
                f"not a registered error: {text!r} (expected MODEL:BASIN:LEAD=NM, "
                "e.g. fusion:AL:48=231)"
            )
        return cls(match.group(1), match.group(2), int(match.group(3)), float(match.group(4)))


@dataclass(slots=True)
class BaselineReport:
    seasons: tuple[int, int]
    seed: int
    n_augment: int
    lead_hours: tuple[int, ...]
    members: list[dict]
    registry_sample: dict[str, dict]
    results: list[HomogeneousRow]
    sample_gap: list[dict]
    diagnostics: dict
    notes: list[str]
    references: tuple[str, ...]
    skill_baseline: str | None
    reconciliation: dict | None = None
    model_forecasts: dict | None = None
    #: Set by the caller, which knows the files: the HURDAT2 read, each
    #: a-deck's name, size and sha256, and the commit that ran.
    hurdat2: dict | None = None
    adecks: list[dict] = field(default_factory=list)
    adecks_missing: list[str] = field(default_factory=list)
    official_errors: list[dict] = field(default_factory=list)
    git_commit: str | None = None

    def to_dict(self) -> dict:
        noise = WorkingTrackNoise()
        return {
            "kind": "homogeneous_baseline",
            "git_commit": self.git_commit,
            "split": "val",
            "seasons": list(self.seasons),
            "seed": self.seed,
            "n_augment": self.n_augment,
            "lead_hours": list(self.lead_hours),
            "hurdat2": self.hurdat2,
            "working_track_noise": {
                "position_rms_nm": noise.position_rms_nm,
                "intensity_rms_kt": noise.intensity_rms_kt,
                "pressure_rms_mb": noise.pressure_rms_mb,
                "quantise": noise.quantise,
            },
            "samples": SAMPLES,
            "basin_notes": {b: BASIN_NOTES[b] for b in self.registry_sample if b in BASIN_NOTES},
            "decision_rule": DECISION_RULE,
            "references": list(self.references),
            "skill_baseline": self.skill_baseline,
            "statistics": {
                "mean_error": "mean over cases (metrics.track.verify, the registry's statistic)",
                "storm_mean_error": "mean of the storms' own means",
                "ci95": "storm-block bootstrap of the paired mean difference "
                        f"({BOOTSTRAP_RESAMPLES} resamples, fixed seed)",
                "dm_p_value": "Diebold-Mariano on absolute error, one case per storm",
                "too_few_storms": "fewer than 8 storms: means only, no skill, beat rate, "
                                  "interval or p-value",
            },
            "members": self.members,
            "registry_sample": self.registry_sample,
            "model_forecasts": self.model_forecasts,
            "adecks": self.adecks,
            "adecks_missing": self.adecks_missing,
            "official_errors": self.official_errors,
            "results": [row.to_dict() for row in self.results],
            "sample_gap": self.sample_gap,
            "reconciliation": self.reconciliation,
            "diagnostics": self.diagnostics,
            "notes": self.notes,
        }

    def to_json(self) -> str:
        """`to_dict` as JSON text: numbers rounded to `_REPORT_DECIMALS`,
        and each result row on one line."""
        body = _json_safe(self.to_dict())
        lines: dict[str, str] = {}
        for key in _ROW_LISTS:
            for i, item in enumerate(body.get(key) or []):
                token = f"@@{key}:{i}@@"
                lines[json.dumps(token)] = json.dumps(item, separators=(",", ":"))
                body[key][i] = token
        text = json.dumps(body, indent=2)
        for token, line in lines.items():
            text = text.replace(token, line)
        return text + "\n"

    def row(self, sample: str, basin: str, lead_hours: int, quantity: str) -> HomogeneousRow:
        for row in self.results:
            if (row.sample, row.basin, row.lead_hours, row.quantity) == (
                sample, basin, lead_hours, quantity,
            ):
                return row
        raise KeyError((sample, basin, lead_hours, quantity))


def _json_safe(value):
    """``value`` with floats rounded and non-finite ones as null, so the
    text is strict JSON and no longer than its precision warrants."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, bool | np.bool_):
        return bool(value)
    if isinstance(value, int | np.integer):
        return int(value)
    if value is None or isinstance(value, str):
        return value
    number = float(value)
    return round(number, _REPORT_DECIMALS) if np.isfinite(number) else None


def _registry_sample(cases: ValidationCases) -> dict[str, dict]:
    """What the registry's sample is, per basin, and the registry's own
    persistence numbers on it (`metrics.basin.per_basin_scores`, the
    registered ``{basin}/persistence_track_error_{lead}h_nm``): matching a
    registered version's value shows the cases and working fixes are its."""
    scores = per_basin_scores(
        cases.persistence_abs, cases.obs_abs, cases.mask, cases.storm_ids, cases.lead_hours,
        prefix=PERSISTENCE_PREFIX,
    )
    basins = np.array([storm_basin(s) for s in cases.storm_ids])
    ids = np.array(cases.storm_ids)
    out = {}
    for basin in cases.basins:
        sel = basins == basin
        out[basin] = {
            "n_storms": len(set(ids[sel].tolist())),
            "n_windows": int(sel.sum()),
            "n_by_lead": {
                str(lead): int(cases.mask[sel, li].sum())
                for li, lead in enumerate(cases.lead_hours)
            },
            "n_verifying_fix_not_at_lead": int((cases.mask & ~cases.time_ok)[sel].sum()),
            "persistence_track_error_nm": {
                str(lead): scores[basin_key(basin, f"{PERSISTENCE_PREFIX}track_error_{lead}h_nm")]
                for li, lead in enumerate(cases.lead_hours) if cases.mask[sel, li].any()
            },
        }
    return out


def _sample_gap(
    cases: ValidationCases,
    members: Sequence[Member],
    always: Sequence[Member],
    subsets: Mapping[str, np.ndarray],
    registered: Sequence[RegisteredError],
) -> list[dict]:
    """What separates sample A from each homogeneous subset (B, C), per
    basin and lead (track): how many windows no longer count, what they
    were at their initial time, and what the members that exist everywhere
    score on each side.

    With a model's registered error on A (``registered``), what that error
    allows on a subset S without the model's per-case forecasts. A's sum of
    errors is fixed by the registered mean, so:

    * ``max_mean_on_subset`` -- the model's mean on S if its error on every
      excluded window were zero: it cannot be worse than this on S.
    * ``mean_error_needed_on_excluded_to_tie`` -- the *break-even*: the mean
      error it would need on the excluded windows for its mean on S to
      equal a member's. Compare with what persistence scores on those same
      windows; a negative value means the model beats that member on S
      whatever it does on the rest.

    Both assume the registered mean is over every window of A, which holds
    only if training skipped no validation window for a missing cached
    field; the per-case forecast file settles that.
    """
    basins = np.array([storm_basin(s) for s in cases.storm_ids])
    errors = {m.name: case_errors(m, cases.obs_abs, TRACK) for m in (*members, *always)}
    out = []
    for basin in cases.basins:
        sel = basins == basin
        for li, lead in enumerate(cases.lead_hours):
            in_a = sel & cases.mask[:, li]
            n_a = int(in_a.sum())
            everywhere = [m for m in always if np.isfinite(errors[m.name][in_a, li]).all()]
            row: dict = {
                "basin": basin, "lead_hours": int(lead), "quantity": TRACK, "n_A": n_a,
                "mean_error_on_A": {
                    m.name: _mean_or_none(errors[m.name][in_a, li]) for m in everywhere
                },
                "subsets": {},
            }
            for key, subset in subsets.items():
                in_s = sel & subset[:, li]
                excluded = in_a & ~in_s
                n_s = int(in_s.sum())
                statuses: dict[str, int] = {}
                for i in np.flatnonzero(excluded):
                    status = cases.init_status[i] or "unknown"
                    statuses[status] = statuses.get(status, 0) + 1
                gap: dict = {
                    "n": n_s, "n_excluded": n_a - n_s,
                    "excluded_initial_status": dict(sorted(statuses.items())),
                    "mean_error": {
                        m.name: {
                            "on_subset": _mean_or_none(errors[m.name][in_s, li]),
                            "excluded": _mean_or_none(errors[m.name][excluded, li]),
                        }
                        for m in everywhere
                    },
                }
                bounds = []
                for reg in registered:
                    if (reg.basin, reg.lead_hours) != (basin, lead) or n_s == 0:
                        continue
                    on_s = {
                        m.name: float(errors[m.name][in_s, li].mean())
                        for m in members if np.isfinite(errors[m.name][in_s, li]).all()
                    }
                    bound: dict = {
                        "model": reg.model,
                        "registered_track_error_nm": reg.track_error_nm,
                        "same_cases_as_A": n_a == n_s,
                        "max_mean_on_subset": reg.track_error_nm * n_a / n_s,
                    }
                    if n_a > n_s:
                        bound["mean_error_needed_on_excluded_to_tie"] = {
                            name: (reg.track_error_nm * n_a - mean * n_s) / (n_a - n_s)
                            for name, mean in on_s.items()
                        }
                    bounds.append(bound)
                if bounds:
                    gap["registered_model_bounds"] = bounds
                row["subsets"][key] = gap
            out.append(row)
    return out


def _notes(cases: ValidationCases, has_models: bool) -> list[str]:
    notes = [
        "A number here is comparable only with another on the same sample (A, B or C). A "
        "registered {basin}/track_error_{lead}h_nm is a mean over sample A; it must not be "
        "set beside a technique's error on B or C.",
        "Only sample C is commensurable with the 70 nm promotion threshold, NHC's 51 nm "
        "2026 target and NHC's published 48 h errors, which are tropical-stage numbers. "
        "C still differs from "
        "NHC's sample: the windows start 24 h after a storm's first best-track fix, and "
        "basin is the storm id's (EP rows include CPHC-issued forecasts west of 140W; CP "
        "is CPHC, with no NHC-published counterpart). `reconciliation` applies NHC's "
        "rules in full.",
        "The inputs differ even where the cases are the same. The project's models "
        "forecast from an emulated working fix (the final best track plus noise, "
        "`working_track_noise`); OFCL, AVNI and OCD5 start from the as-issued fix "
        "(`diagnostics.working_fix`). The gridded models' GFS crops are centred on the "
        "final best-track position, so validation inputs are part noisier and part "
        "cleaner than a live cycle's.",
        "`persistence` is the registry's baseline: linear extrapolation of the last 6 h "
        "motion of two independently perturbed fixes, with no climatology. It is not "
        "CLIPER. `persistence_besttrack` removes the noise; OCD5 is NHC's baseline. "
        "'Beats persistence' in the registry is a lower bar than either.",
        "OFCL is issued at t+3 h having seen the early guidance, AVNI included; the "
        "project's cycle is complete at t+1:40. AVNO at t is not available to either.",
        "One validation season. Six-hourly cases of one storm are not independent: read "
        "n_storms and largest_storm_share with every n, and the storm-block interval "
        "before any difference.",
        "The emulator's noise draw alone moves the registry's persistence by about 1% "
        "between two orders of drawing (335.0 against 337.9 nm, Atlantic 48 h, in the "
        "first multi-basin run): a model difference of that size is draw noise.",
    ]
    mismatched = int((cases.mask & ~cases.time_ok).sum())
    if mismatched:
        notes.append(
            f"{mismatched} registry case(s) verify against a best-track fix that is not at "
            "the initial time plus the lead (a dropped best-track row shifts the index). "
            "They stay in sample A, as the registry scored them, and are left out of B and C."
        )
    if not has_models:
        notes.append(
            "No per-case model forecasts were given, so no model is scored here and the "
            "question whether fusion beats the GFS track on the same cases is open. The "
            "two persistence baselines are the only link between the samples; "
            "`sample_gap` bounds what a model's registered error on A allows on B and C, "
            "assuming training skipped no validation window."
        )
    return notes


def run_baseline_backtest(
    tracks: list[Track],
    statuses: Mapping[tuple[str, datetime], str],
    adecks: Mapping[str, Adeck],
    *,
    techniques: Sequence[str] = DEFAULT_TECHNIQUES,
    references: Sequence[str] = DEFAULT_REFERENCES,
    skill_baseline: str | None = SKILL_BASELINE,
    model_forecasts: ValidationForecasts | None = None,
    models: Sequence[str] = ("fusion",),
    official_errors: Mapping[str, OfficialErrors] | None = None,
    registered: Sequence[RegisteredError] = (),
    seed: int = 20260806,
    n_augment: int = 1,
) -> BaselineReport:
    """Score ``techniques`` (and, given ``model_forecasts``, ``models``) on
    the validation windows of ``tracks``. See the module docstring.

    ``adecks`` maps a storm id to its parsed a-deck; a storm without one
    has no technique forecast, and no B or C case. ``official_errors``
    (basin -> NHC's per-forecast errors) adds the reconciliation.
    """
    cases = validation_cases(tracks, statuses, seed=seed, n_augment=n_augment)
    specs = [TechniqueSpec.parse(t) for t in techniques]
    always = persistence_members(cases)
    member_rows: list[dict] = []
    operational: list[Member] = []
    for spec in specs:
        member, used = technique_member(spec, cases, adecks)
        operational.append(member)
        member_rows.append({
            "name": member.name, "kind": member.kind, "description": member.description,
            "techniques": list(spec.techniques), "lag_hours": spec.lag_hours,
            "cases_by_technique": used,
        })
    model_info = None
    project: list[Member] = []
    if model_forecasts is not None:
        project, n_without = model_members(cases, model_forecasts, models)
        model_info = {
            **{k: model_forecasts.header.get(k) for k in (
                "versions", "latent_signature", "consistent", "seed", "n_augment", "hurdat2",
            )},
            "n_cases": len(model_forecasts),
            "n_without_model_forecast": n_without,
        }
    for member in (*always, *project):
        member_rows.append({
            "name": member.name, "kind": member.kind, "description": member.description,
        })
    everyone = [*operational, *always, *project]
    names = [m.name for m in everyone]
    if len(set(names)) != len(names):
        raise BaselineBacktestError(f"duplicate member names: {names}")
    for row, member in zip(member_rows, [*operational, *always, *project], strict=True):
        row["track_only"] = bool(member.has_track.any() and not member.has_intensity.any())
        row["intensity_only"] = bool(member.has_intensity.any() and not member.has_track.any())
        row["no_forecast_for_any_case"] = not (member.has_track | member.has_intensity).any()

    eligible = {
        "A": cases.mask,
        "B": cases.mask & cases.time_ok,
        "C": cases.mask & cases.time_ok & cases.tropical_mask(),
    }
    present = [n for n in names if n in set(references)]
    results: list[HomogeneousRow] = []
    for sample, mask in eligible.items():
        results.extend(score_homogeneous(
            [*always, *project] if sample == "A" else everyone,
            cases.obs_abs, mask, cases.storm_ids, cases.lead_hours, sample=sample,
            references=present if sample != "A" else [PERSISTENCE],
            skill_baseline=skill_baseline if sample != "A" else None,
        ))
    subsets = {
        key: homogeneous_mask(everyone, eligible[key], cases.storm_ids, TRACK)
        for key in ("B", "C")
    }
    val_tracks = validation_tracks(tracks)
    return BaselineReport(
        seasons=cases.seasons, seed=seed, n_augment=n_augment, lead_hours=cases.lead_hours,
        members=member_rows,
        registry_sample=_registry_sample(cases),
        results=results,
        sample_gap=_sample_gap(cases, operational, [*always, *project], subsets, registered),
        diagnostics={
            "working_fix": working_fix_diagnostics(cases, val_tracks, adecks),
            "techniques": technique_diagnostics(cases, adecks),
        },
        notes=_notes(cases, bool(project)),
        references=tuple(present), skill_baseline=skill_baseline,
        reconciliation=(
            reconcile_official_errors(val_tracks, statuses, adecks, official_errors)
            if official_errors else None
        ),
        model_forecasts=model_info,
    )


# --- printing ----------------------------------------------------------------

_QUANTITY_LABEL = {TRACK: "track error (nm)", INTENSITY: "intensity error (kt)"}


def format_report(report: BaselineReport) -> str:
    """The table: per basin, sample and quantity, one line per member with
    the leads as columns, under the number of cases and storms."""
    kinds = {m["name"]: m["kind"] for m in report.members}
    lines = [
        f"Homogeneous baseline -- validation seasons {report.seasons[0]}-{report.seasons[1]}, "
        f"seed {report.seed}",
        "",
        "Samples:",
        *(f"  {key}: {text}" for key, text in SAMPLES.items()),
        "",
        "Decision rule: " + DECISION_RULE,
    ]
    if report.adecks_missing:
        # A storm without an a-deck drops out of B and C for every member,
        # so the samples below are smaller than the season's.
        lines += [
            "",
            f"No a-deck for {len(report.adecks_missing)} validation storm(s), so samples B "
            f"and C leave them out: {', '.join(report.adecks_missing)}",
        ]
    lead_header = "".join(f"{f'{lead}h':>8}" for lead in report.lead_hours)
    basins = sorted({row.basin for row in report.results})
    for basin in basins:
        sample = report.registry_sample.get(basin, {})
        lines += ["", f"=== {basin}: {sample.get('n_windows')} registry windows from "
                      f"{sample.get('n_storms')} storm(s) ==="]
        if basin in BASIN_NOTES:
            lines.append(f"  ({BASIN_NOTES[basin]})")
        for key in SAMPLES:
            for quantity in QUANTITIES:
                rows = [
                    r for r in report.results
                    if (r.sample, r.basin, r.quantity) == (key, basin, quantity)
                ]
                if not rows or not any(r.scores for r in rows):
                    continue
                flags = []
                if any(r.too_few_storms for r in rows):
                    flags.append("* fewer than 8 storms: a description of those storms, "
                                 "not a sample")
                absent = sorted({name for r in rows for name in r.absent})
                if absent:
                    flags.append(f"absent in this basin: {', '.join(absent)}")
                lines += ["", f"  sample {key}, {_QUANTITY_LABEL[quantity]}"]
                lines.append(f"    {'':<22}{'':<18}{lead_header}")
                lines.append(
                    f"    {'cases':<22}{'':<18}" + "".join(f"{r.n_cases:>8}" for r in rows)
                )
                lines.append(
                    f"    {'storms':<22}{'':<18}" + "".join(
                        f"{str(r.n_storms) + ('*' if r.too_few_storms else ''):>8}" for r in rows
                    )
                )
                for name in dict.fromkeys(n for r in rows for n in r.scores):
                    cells = "".join(
                        f"{r.scores[name].mean_error:>8.1f}" if name in r.scores else f"{'-':>8}"
                        for r in rows
                    )
                    lines.append(f"    {name:<22}{kinds.get(name, ''):<18}{cells}")
                lines += [f"    {flag}" for flag in flags]
    if report.reconciliation:
        lines += ["", "Reconciliation with NHC's own per-forecast official errors "
                      "(NHC's rules in full):"]
        for basin, rec in report.reconciliation.items():
            for lead, row in rec["by_lead"].items():
                if int(lead) != 48:
                    continue
                lines.append(
                    f"  {basin} 48 h: ours {_fmt(row['mean_ours_nm'])} nm (n={row['n_ours']}), "
                    f"NHC {_fmt(row['mean_nhc_nm'])} nm (n={row['n_nhc']}); "
                    f"{row['n_common']} common, largest difference "
                    f"{_fmt(row['max_abs_diff_nm'], 2)} nm; "
                    f"only in NHC's: {row['n_only_in_nhc']}; unexplained in ours: "
                    f"{row['ours_not_counted_by_nhc']['unexplained']}"
                )
    if report.model_forecasts is None:
        lines += ["", "No model forecasts given: no project model is scored above."]
    return "\n".join(lines)


def _fmt(value: float | None, decimals: int = 1) -> str:
    return "n/a" if value is None else f"{value:.{decimals}f}"


# --- writing the forecast file (the training machine) ------------------------


def assemble_validation_forecasts(
    val: JointLatentSamples,
    fusion_abs: np.ndarray,
    cases: ValidationCases,
    *,
    versions: Mapping[str, int],
    latent_signature: str | None,
    registered: Mapping[str, Mapping[str, float]],
    hurdat2: Mapping[str, object] | None = None,
    trained_on_hurdat2_sha256: str | None = None,
    git_commit: str | None = None,
    extra_forecasts: Mapping[str, np.ndarray] | None = None,
) -> ValidationForecasts:
    """Build the per-case forecast file from the validation latents (each
    Group 1 model's forecast per window) and fusion's forecast for them,
    and check it against the registry. Needs no torch.

    Every row must be one of ``cases`` and start from the same working fix
    (raises otherwise). Each model's validation metrics are recomputed from
    the arrays being written, with the function training registers them
    with (`real_run.validation_metrics`); ``consistent`` is true when
    fusion's registered per-basin sample counts, persistence errors and own
    errors are all reproduced. The Group 1 models' registered numbers are
    from their own noise draws and are shown, not checked.

    ``extra_forecasts`` (`collect_validation_forecasts`' ``extras``) are
    written beside them under their own names, NaN where they have no
    forecast; their metrics are recomputed on the rows they have.
    """
    if len(val.valid_times) != len(val) or len(val.storm_ids) != len(val):
        raise BaselineBacktestError("the validation latents carry no storm ids or valid times")
    if val.persistence is None:
        raise BaselineBacktestError("the validation latents carry no persistence forecast")
    rows = _join(cases, val.storm_ids, val.valid_times, val.base_lat, val.base_lon)
    persistence_abs = displacements_to_absolute(
        val.persistence, np.asarray(val.base_lat)[:, None], np.asarray(val.base_lon)[:, None],
    )
    forecasts = {
        name: np.asarray(val.predictions[:, i], dtype=float) for i, name in enumerate(GROUP1_ORDER)
    }
    forecasts["fusion"] = np.asarray(fusion_abs, dtype=float)
    for name, pred in (extra_forecasts or {}).items():
        if name in forecasts or name == PERSISTENCE:
            raise BaselineBacktestError(f"extra forecast {name!r} would replace a dumped one")
        forecasts[name] = np.asarray(pred, dtype=float)
    forecasts[PERSISTENCE] = persistence_abs

    def scored(pred: np.ndarray) -> dict:
        has = np.isfinite(pred).all(axis=-1)
        return validation_metrics(
            Flavor.GDAS_FINETUNE, np.where(has[..., None], pred, 0.0), val.true_absolute,
            np.asarray(val.mask) & has, val_storm_ids=val.storm_ids,
            persistence_abs=persistence_abs,
        ).values

    recomputed = {name: scored(pred) for name, pred in forecasts.items() if name != PERSISTENCE}
    checks = []
    for key, value in sorted(registered.get("fusion", {}).items()):
        if key not in recomputed["fusion"]:
            continue
        name = key.rsplit("/", 1)[-1]
        tolerance = (
            _TOLERANCE_COUNT if name.endswith("_samples")
            else _TOLERANCE_PERSISTENCE if name.startswith(PERSISTENCE_PREFIX)
            else _TOLERANCE_MODEL
        )
        got = recomputed["fusion"][key]
        checks.append({
            "metric": key, "registered": float(value), "recomputed": float(got),
            "ok": bool(abs(got - value) <= tolerance),
        })
    failed = [c for c in checks if not c["ok"]]
    read_sha = (hurdat2 or {}).get("hurdat2_sha256")
    header = {
        "kind": "validation_forecasts",
        "git_commit": git_commit,
        "split": "val",
        "seasons": list(cases.seasons),
        "seed": cases.seed,
        "n_augment": cases.n_augment,
        "lead_hours": list(cases.lead_hours),
        "hurdat2": dict(hurdat2) if hurdat2 else None,
        "fusion_trained_on_hurdat2_sha256": trained_on_hurdat2_sha256,
        # Informational: a revision to a test-season storm changes the
        # file but no validation window. The metric checks decide.
        "same_hurdat2_as_training": (
            None if not (read_sha and trained_on_hurdat2_sha256)
            else read_sha == trained_on_hurdat2_sha256
        ),
        "versions": dict(versions),
        "extra_models": list(extra_forecasts or {}),
        "latent_signature": latent_signature,
        "n_cases": len(val),
        "n_enumerated": len(cases),
        "n_without_forecast": len(cases) - len(rows),
        "consistent": bool(checks) and not failed,
        "n_checks": len(checks),
        "failed_checks": failed,
        "registered": {
            name: {k: float(v) for k, v in sorted(metrics.items()) if k in recomputed.get(name, {})}
            for name, metrics in registered.items()
        },
        "recomputed": {
            name: {k: float(v) for k, v in sorted(metrics.items())}
            for name, metrics in recomputed.items()
        },
    }
    return ValidationForecasts(
        header=header, storm_ids=tuple(val.storm_ids), init_times=tuple(val.valid_times),
        base_lat=np.asarray(val.base_lat, dtype=float),
        base_lon=np.asarray(val.base_lon, dtype=float),
        forecasts=forecasts,
    )


def format_forecast_check(forecasts: ValidationForecasts) -> str:
    """The forecast file's own check, for the log of the job that wrote
    it: what was dumped, and fusion's registered 48 h numbers beside the
    ones recomputed from the dumped forecasts."""
    header = forecasts.header
    versions = ", ".join(f"{m} v{v}" for m, v in header.get("versions", {}).items())
    served = {
        True: " (the Group 1 champions served today)",
        False: " (Group 1 is not today's champion set)",
    }.get(header.get("group1_served_today"), "")
    lines = [
        f"validation forecasts: {header.get('n_cases')} of {header.get('n_enumerated')} "
        f"enumerated windows ({header.get('n_without_forecast')} without a forecast), "
        f"seed {header.get('seed')}",
        f"versions: {versions}{served}",
        f"{'metric':<40}{'registered':>12}{'recomputed':>12}",
    ]
    registered = header.get("registered", {}).get("fusion", {})
    recomputed = header.get("recomputed", {}).get("fusion", {})
    for key in sorted(registered):
        if key.endswith(("track_error_48h_nm", "val_samples")):
            lines.append(f"{'fusion ' + key:<40}{registered[key]:>12.2f}{recomputed[key]:>12.2f}")
    for name in header.get("extra_models", []):
        reg = header.get("registered", {}).get(name, {})
        rec = header.get("recomputed", {}).get(name, {})
        n = int(np.isfinite(forecasts.forecasts[name]).all(axis=(1, 2)).sum())
        lines.append(f"{name}: forecasts for {n} of {len(forecasts)} windows "
                     "(registered numbers are its own training's, shown, not checked)")
        for key in sorted(rec):
            if key.endswith("track_error_48h_nm"):
                got = f"{reg[key]:>12.2f}" if key in reg else f"{'-':>12}"
                lines.append(f"{name + ' ' + key:<40}{got}{rec[key]:>12.2f}")
    if header.get("same_hurdat2_as_training") is False:
        lines.append(
            "note: this HURDAT2 is not the file fusion was trained on; the checks below say "
            "whether its validation windows changed"
        )
    for check in header.get("failed_checks", []):
        lines.append(
            f"MISMATCH {check['metric']}: registered {check['registered']:.3f}, "
            f"recomputed {check['recomputed']:.3f}"
        )
    lines.append(
        f"consistent with the registry: {'yes' if forecasts.consistent else 'NO'} "
        f"({header.get('n_checks')} metrics compared)"
    )
    return "\n".join(lines)


def group1_versions_of(signature: str | None) -> dict[str, int]:
    """The Group 1 versions a derived model's ``latent_signature`` names
    (`tracking.registry.latent_signature`: ``lstmv12-cnnv5-...``). Raises
    for anything else: a fusion without one cannot be re-run on its own
    inputs."""
    from ..tracking.registry import GROUP1_MODELS, latent_signature

    parts: dict[str, int] = {}
    for part in (signature or "").split("-"):
        match = re.fullmatch(r"([a-z0-9]+)v(\d+)", part)
        if match is not None:
            parts[match.group(1)] = int(match.group(2))
    if not set(GROUP1_MODELS) <= set(parts) or latent_signature(parts) != signature:
        raise BaselineBacktestError(f"not a Group 1 latent signature: {signature!r}")
    return {name: parts[name] for name in GROUP1_MODELS}


def collect_validation_forecasts(
    tracks: list[Track],
    registry: ModelRegistry,
    checkpoint_store: CheckpointStore,
    gdas_cache_dir: Path | str,
    *,
    seed: int = 20260806,
    n_augment: int = 1,
    fusion_version: int | None = None,
    extra_versions: Mapping[str, int] | None = None,
    steering_cache_dir: Path | str | None = None,
    device=None,
):
    """The torch half: load fusion and the Group 1 versions it was trained
    on, and run them on the validation windows. Returns ``(val, fusion_abs,
    versions, fusion, served, extras)``: the validation `JointLatentSamples`,
    fusion's ``(n, n_leads, 3)`` absolute forecast for them, the versions
    used, fusion's registered version, whether those Group 1 versions
    are the champions served today, and the ``extra_versions`` forecasts.

    ``extra_versions`` (``{"transformer": 9}``) also runs other registered
    versions of Group 1 models on the same windows, each in place of
    fusion's own version of that model, for a paired test of a version
    fusion wasn't trained on. Each comes back as ``extras[f"{model}_v{N}"]
    = (model, N, forecast)``, aligned to ``val``'s rows, NaN where that
    version had no input (a steering Transformer skips a window without
    steering). Fusion is never run on them. ``steering_cache_dir`` is the
    steering cache for a version that reads it (`real_latents`).

    Fusion is the champion unless ``fusion_version`` names one. Its Group 1
    inputs come from its own ``latent_signature``, not from today's
    champions: the forecasts must be the ones it was validated on, which
    the file's check against the registered metrics then confirms. Fusion
    is run as `real_run_fusion.train_fusion_stage` validates it.
    """
    import torch

    from ..tracking.registry import GROUP1_MODELS, RegistryError
    from .real_inference import load_run_artifacts, load_trained_model
    from .real_latents import extract_validation_latents

    try:
        fusion = (
            registry.get("fusion", fusion_version) if fusion_version is not None
            else registry.champion("fusion")
        )
        if fusion is None:
            raise BaselineBacktestError("no staging/production fusion version")
        versions = group1_versions_of(fusion.latent_signature)
        group1 = {m: registry.get(m, versions[m]) for m in GROUP1_MODELS}
    except RegistryError as exc:
        raise BaselineBacktestError(str(exc)) from exc
    champions = {m: registry.champion(m) for m in GROUP1_MODELS}
    served = all(c is not None and c.version == versions[m] for m, c in champions.items())

    artifacts = {m: load_run_artifacts(m, v, checkpoint_store) for m, v in group1.items()}
    val = extract_validation_latents(
        tracks, artifacts, gdas_cache_dir, seed=seed, n_augment=n_augment, device=device,
    )
    if len(val) == 0:
        raise BaselineBacktestError("no validation window had a cached gridded field")
    model, _spec = load_trained_model("fusion", fusion, checkpoint_store)
    with torch.no_grad():
        fusion_abs = model(
            torch.as_tensor(val.predictions, dtype=torch.float32),
            torch.as_tensor(val.context, dtype=torch.float32),
        ).cpu().numpy()
    extras: dict[str, tuple[str, int, np.ndarray]] = {}
    for model, version in (extra_versions or {}).items():
        if model not in GROUP1_MODELS:
            raise BaselineBacktestError(f"{model} is not a Group 1 model")
        try:
            entry = registry.get(model, version)
        except RegistryError as exc:
            raise BaselineBacktestError(str(exc)) from exc
        swapped = {**artifacts, model: load_run_artifacts(model, entry.version, checkpoint_store)}
        try:
            other = extract_validation_latents(
                tracks, swapped, gdas_cache_dir, seed=seed, n_augment=n_augment, device=device,
                steering_cache_dir=steering_cache_dir,
            )
        except ValueError as exc:
            raise BaselineBacktestError(f"{model} v{version}: {exc}") from exc
        extras[f"{model}_v{entry.version}"] = (
            model, entry.version, _aligned(val, other, GROUP1_ORDER.index(model)),
        )
    return val, fusion_abs, {**versions, "fusion": fusion.version}, fusion, served, extras


def _aligned(val, other, index: int) -> np.ndarray:
    """``other``'s forecast from Group 1 model ``index``, on ``val``'s rows
    (matched by storm and valid time); NaN where ``other`` has no row.
    Raises if a shared row starts from a different fix: then the two runs
    did not draw the same working tracks."""
    keys = zip(other.storm_ids, other.valid_times, strict=True)
    at = {(s, t): i for i, (s, t) in enumerate(keys)}
    out = np.full(np.asarray(val.predictions[:, index]).shape, np.nan)
    for i, key in enumerate(zip(val.storm_ids, val.valid_times, strict=True)):
        j = at.get(key)
        if j is None:
            continue
        if (abs(other.base_lat[j] - val.base_lat[i]) > 1e-6
                or abs(other.base_lon[j] - val.base_lon[i]) > 1e-6):
            raise BaselineBacktestError(f"window {key} starts from a different working fix")
        out[i] = other.predictions[j, index]
    return out


def dump_validation_forecasts(
    tracks: list[Track],
    statuses: Mapping[tuple[str, datetime], str],
    registry: ModelRegistry,
    checkpoint_store: CheckpointStore,
    gdas_cache_dir: Path | str,
    *,
    seed: int = 20260806,
    n_augment: int = 1,
    fusion_version: int | None = None,
    extra_versions: Mapping[str, int] | None = None,
    steering_cache_dir: Path | str | None = None,
    hurdat2: Mapping[str, object] | None = None,
    git_commit: str | None = None,
    device=None,
) -> ValidationForecasts:
    """`collect_validation_forecasts`, then `assemble_validation_forecasts`."""
    from ..tracking.registry import GROUP1_MODELS

    val, fusion_abs, versions, fusion, served, extras = collect_validation_forecasts(
        tracks, registry, checkpoint_store, gdas_cache_dir,
        seed=seed, n_augment=n_augment, fusion_version=fusion_version,
        extra_versions=extra_versions, steering_cache_dir=steering_cache_dir, device=device,
    )
    registered = {"fusion": dict(fusion.metrics)}
    for name in GROUP1_MODELS:
        registered[name] = dict(registry.get(name, versions[name]).metrics)
    for label, (model, version, _pred) in extras.items():
        registered[label] = dict(registry.get(model, version).metrics)
    forecasts = assemble_validation_forecasts(
        val, fusion_abs, validation_cases(tracks, statuses, seed=seed, n_augment=n_augment),
        versions={**versions, **{label: v for label, (_m, v, _p) in extras.items()}},
        latent_signature=fusion.latent_signature, registered=registered,
        hurdat2=hurdat2, trained_on_hurdat2_sha256=fusion.tags.get("hurdat2_sha256"),
        git_commit=git_commit,
        extra_forecasts={label: pred for label, (_m, _v, pred) in extras.items()},
    )
    forecasts.header["group1_served_today"] = served
    return forecasts
