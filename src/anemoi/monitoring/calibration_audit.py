"""Real served-product calibration monitor (#166's live-monitoring
follow-up -- "build 4" from that issue's own discussion).

`training.spread_backtest` (#10) already answers a real research question
offline: if the cone were rebuilt from raw ensemble members against a
fixed 2023-2025 validation split, would it be calibrated? That tool needs
raw per-member positions, which are sampled and then discarded once the
served cone/intensity-PDF aggregates are computed -- nothing durable keeps
them today, and threading them all the way through `inference.cycle
.run_cycle`'s real, already-tested pipeline just to persist them would be
a real, invasive change for a monitoring surface, not the pipeline itself.

This module answers a narrower, more directly product-facing question
instead, using data that is *already* durably stored: **was the cone and
intensity band this system actually served to a real user right, once the
real truth became known?** No raw members needed -- only the already-
served `api.schemas.CycleResult` (#175, durably persisted by every real
cycle) and the storm's own real subsequent fixes.

That second part is also why this doesn't need `monitoring.skew_audit`'s
own offline-replay machinery (a separate durable "operational record" of
replay inputs, a days-later CLI, ERA5T's multi-day publish lag): the real
truth a served cycle's calibration needs -- what the storm actually did
next -- is already flowing into the same live `api.real_state.RealState`
process via the exact mechanism that already exists
(`_refresh_live_storms`'s periodic real NHC feed poll), not published
days later by a separate slow pipeline. `audit_storm` is meant to be
called right after that refresh, best-effort, the same never-fail-the-
caller contract every other real monitoring hook in this codebase follows
(`RealState._record_drift_sample`/`_record_skew_sample`).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..geo import haversine_nm
from ..time_utils import parse_cycle_label

if TYPE_CHECKING:
    from ..api.schemas import CycleResult
    from ..data.besttrack import Fix
    from ..tracking.checkpoint_store import CheckpointStore

#: Durable key for the accumulated real CalibrationSample corpus.
CALIBRATION_SAMPLES_KEY = "monitoring/calibration_samples.json"

#: Durable key for the set of already-audited "{storm_id}:{label}:{lead}"
#: leads -- one entry per (cycle, lead), not per cycle: a cycle's own
#: leads become due at different real times (12h before 120h), so
#: "already audited" has to be tracked at that granularity too.
AUDITED_LEADS_KEY = "monitoring/calibration_audited_leads.json"

#: The real served cone is a 2/3-probability circle
#: (`inference.postprocess.build_cone`'s own docstring, and
#: `training.spread_backtest.ConeOutcome`'s docstring says the same) --
#: a calibrated cone contains the truth about 67% of the time.
CONE_NOMINAL_RATE = 2.0 / 3.0

#: The intensity band is the p10-p90 spread by construction -- a
#: calibrated band contains the truth 80% of the time, definitionally,
#: not a measured/assumed constant the way the cone's is.
INTENSITY_NOMINAL_RATE = 0.8

#: How far a real containment rate may sit from its nominal value and
#: still read as "calibrated" -- an absolute margin (containment rate
#: isn't a ratio of two comparable quantities the way `SpreadSkill.ratio`
#: is, so that class's own 0.8/1.25 *ratio* thresholds don't translate
#: directly). +/-15 points mirrors the real gap this session's own
#: spread-backtest runs treated as "still off" (49% cone miss vs. the
#: 33% nominal, an 16-point gap, was reported as real progress but not
#: yet fully calibrated) without being so tight that ordinary sampling
#: noise at low real sample counts reads as miscalibration.
_VERDICT_MARGIN = 0.15

#: A rate computed from fewer real samples than this is real but not
#: reportable as a verdict -- the same "n_live=0"/"reasons" honesty
#: `RealState.drift_report`/`skew_report` already use for "too little
#: real data yet," not a fabricated verdict from a handful of samples.
MIN_CASES = 5


@dataclass(frozen=True, slots=True)
class CalibrationSample:
    """One real, already-resolved (storm, cycle, lead) pair: did the
    served cone and the served intensity band actually contain what the
    storm went on to do. `cone_hit`/`cone_basis`/`intensity_hit` are
    ``None`` when that lead's real cycle had no cone segment / no
    intensity_pdf entry to check at all (a real absence, never fabricated
    as a miss or a hit)."""

    storm_id: str
    label: str
    lead_hours: int
    cone_basis: str | None
    cone_hit: bool | None
    intensity_hit: bool | None
    audited_at: datetime


@dataclass(frozen=True, slots=True)
class LeadProductCalibration:
    """Real aggregate calibration for one (lead, product) pair, over
    every real audited sample seen so far."""

    lead_hours: int
    quantity: str  # "cone" or "intensity"
    n_cases: int
    containment_rate: float | None
    nominal_rate: float
    verdict: str  # "too narrow" / "too wide" / "calibrated" / "not enough data"

    def to_dict(self) -> dict[str, Any]:
        return {
            "lead_hours": self.lead_hours,
            "quantity": self.quantity,
            "n_cases": self.n_cases,
            "containment_rate": self.containment_rate,
            "nominal_rate": self.nominal_rate,
            "verdict": self.verdict,
        }


def _sample_to_dict(s: CalibrationSample) -> dict[str, Any]:
    return {
        "storm_id": s.storm_id,
        "label": s.label,
        "lead_hours": s.lead_hours,
        "cone_basis": s.cone_basis,
        "cone_hit": s.cone_hit,
        "intensity_hit": s.intensity_hit,
        "audited_at": s.audited_at.isoformat(),
    }


def _sample_from_dict(d: dict[str, Any]) -> CalibrationSample:
    return CalibrationSample(
        storm_id=d["storm_id"],
        label=d["label"],
        lead_hours=int(d["lead_hours"]),
        cone_basis=d["cone_basis"],
        cone_hit=d["cone_hit"],
        intensity_hit=d["intensity_hit"],
        audited_at=datetime.fromisoformat(d["audited_at"]),
    )


def save_calibration_samples(
    samples: list[CalibrationSample],
    path: Path | str,
    checkpoint_store: CheckpointStore | None = None,
) -> None:
    """Local write always succeeds, durable push best-effort -- the same
    contract `monitoring.skew_audit.save_skew_samples` already uses."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([_sample_to_dict(s) for s in samples], indent=2), encoding="utf-8"
    )
    if checkpoint_store is None:
        return
    try:
        checkpoint_store.upload(path, CALIBRATION_SAMPLES_KEY)
    except Exception:  # noqa: BLE001 - a flaky durable store must never fail a save
        pass


def load_calibration_samples(
    path: Path | str, checkpoint_store: CheckpointStore | None = None
) -> list[CalibrationSample]:
    """Best-effort pull from durable storage, then read ``path`` -- an
    empty list if nothing has ever been audited yet, not an exception."""
    path = Path(path)
    if checkpoint_store is not None:
        try:
            if checkpoint_store.exists(CALIBRATION_SAMPLES_KEY):
                bucket = checkpoint_store.config.bucket
                checkpoint_store.download(
                    f"s3://{bucket}/{CALIBRATION_SAMPLES_KEY}", path
                )
        except Exception:  # noqa: BLE001 - a stale/local-only corpus must still be usable
            pass
    if not path.exists():
        return []
    try:
        return [_sample_from_dict(d) for d in json.loads(path.read_text(encoding="utf-8"))]
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return []


def _load_audited(path: Path | str, checkpoint_store: CheckpointStore | None) -> set[str]:
    path = Path(path)
    if checkpoint_store is not None:
        try:
            if checkpoint_store.exists(AUDITED_LEADS_KEY):
                bucket = checkpoint_store.config.bucket
                checkpoint_store.download(f"s3://{bucket}/{AUDITED_LEADS_KEY}", path)
        except Exception:  # noqa: BLE001
            pass
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValueError):
        return set()


def _save_audited(
    audited: set[str], path: Path | str, checkpoint_store: CheckpointStore | None
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(audited), indent=2), encoding="utf-8")
    if checkpoint_store is None:
        return
    try:
        checkpoint_store.upload(path, AUDITED_LEADS_KEY)
    except Exception:  # noqa: BLE001
        pass


def _audited_key(storm_id: str, label: str, lead_hours: int) -> str:
    return f"{storm_id}:{label}:{lead_hours}"


def audit_due(target_time: datetime, lead_hours: int, now: datetime) -> bool:
    """A lead is due once its own real valid time has passed -- unlike
    `monitoring.skew.audit_due`'s ERA5T publish lag, no extra margin is
    needed: the real truth this checks against is the storm's own live
    feed, which already publishes a fix close to its real synoptic time,
    not days later."""
    return now >= target_time + timedelta(hours=lead_hours)


def audit_cycle(
    storm_id: str,
    result: CycleResult,
    fixes_by_time: dict[datetime, Fix],
    *,
    now: datetime,
    already_audited: set[str],
) -> list[CalibrationSample]:
    """Score every lead of one real stored cycle that's newly due and not
    already audited, against the storm's real fixes at hand -- keyed by
    exact ``valid_time`` match, not a nearest-neighbour search: every real
    fix and every real cycle lead both land on an exact synoptic time
    (`Fix.__post_init__`/`time_utils.require_synoptic` enforce it on one
    side, ``lead_hours`` being a multiple of the synoptic spacing on the
    other), so there is no real ambiguity to resolve.
    """
    target_time = parse_cycle_label(result.payload.cycle)
    cone_by_lead = {seg.lead_hours: seg for seg in result.payload.cone}
    pdf_by_lead = {p.lead_hours: p for p in result.products.intensity_pdf}
    lead_hours = sorted(set(cone_by_lead) | set(pdf_by_lead))

    samples: list[CalibrationSample] = []
    for lead in lead_hours:
        key = _audited_key(storm_id, result.payload.cycle, lead)
        if key in already_audited or not audit_due(target_time, lead, now):
            continue
        truth = fixes_by_time.get(target_time + timedelta(hours=lead))
        if truth is None:
            # Due by wall-clock time, but this storm's real fixes don't
            # (yet, or ever -- a dissipated storm stops getting new real
            # fixes) cover this exact synoptic time. Not an error: the
            # next `audit_storm` call, once this storm's live history has
            # a real fix here, will pick it up.
            continue
        seg = cone_by_lead.get(lead)
        cone_basis = seg.basis if seg is not None else None
        cone_hit = (
            haversine_nm(seg.lat, seg.lon, truth.lat, truth.lon) <= seg.radius_nm
            if seg is not None
            else None
        )
        pdf = pdf_by_lead.get(lead)
        intensity_hit = pdf.p10 <= truth.max_wind_kt <= pdf.p90 if pdf is not None else None
        samples.append(
            CalibrationSample(
                storm_id=storm_id,
                label=result.payload.cycle,
                lead_hours=lead,
                cone_basis=cone_basis,
                cone_hit=cone_hit,
                intensity_hit=intensity_hit,
                audited_at=now,
            )
        )
    return samples


def audit_storm(
    storm_id: str,
    stored_labels: Iterable[str],
    fixes: tuple[Fix, ...],
    checkpoint_store: CheckpointStore,
    local_root: Path | str,
    *,
    now: datetime | None = None,
) -> list[CalibrationSample]:
    """Real entry point for one storm: audits every real stored cycle
    result against the storm's own real accumulated fixes, persists any
    newly-resolved real samples, and returns them. Meant to be called
    from `api.real_state.RealState._refresh_live_storms` right after a
    storm's fixes refresh -- best-effort throughout (a bad/unreadable
    stored cycle is skipped, not fatal to the rest), the same never-fail
    contract every other real monitoring hook in this codebase follows.
    """
    from ..api.cycle_store import load_cycle_result

    now = now or datetime.now(UTC)
    fixes_by_time = {f.valid_time: f for f in fixes}

    audited_path = Path(local_root) / "calibration" / "audited_leads.json"
    audited = _load_audited(audited_path, checkpoint_store)
    samples_path = Path(local_root) / "calibration" / "calibration_samples.json"
    existing = load_calibration_samples(samples_path, checkpoint_store)

    new_samples: list[CalibrationSample] = []
    for label in stored_labels:
        try:
            result = load_cycle_result(checkpoint_store, storm_id, label)
        except Exception:  # noqa: BLE001 - one bad/unreadable cycle must not sink the rest
            continue
        new_samples.extend(
            audit_cycle(storm_id, result, fixes_by_time, now=now, already_audited=audited)
        )

    if new_samples:
        for s in new_samples:
            audited.add(_audited_key(s.storm_id, s.label, s.lead_hours))
        existing.extend(new_samples)
        save_calibration_samples(existing, samples_path, checkpoint_store)
        _save_audited(audited, audited_path, checkpoint_store)
    return new_samples


def _verdict(rate: float | None, nominal: float, n: int) -> str:
    if n < MIN_CASES or rate is None:
        return "not enough data"
    if rate < nominal - _VERDICT_MARGIN:
        return "too narrow"
    if rate > nominal + _VERDICT_MARGIN:
        return "too wide"
    return "calibrated"


def calibrate_products(samples: list[CalibrationSample]) -> list[LeadProductCalibration]:
    """Real aggregate containment rate per (lead, product), over every
    real sample in ``samples``. Pure function, no I/O -- the real
    reporting math `api.real_state.RealState.calibration_report` calls
    against whatever real corpus is currently loaded."""
    by_lead: dict[int, dict[str, list[bool]]] = {}
    for s in samples:
        bucket = by_lead.setdefault(s.lead_hours, {"cone": [], "intensity": []})
        if s.cone_hit is not None:
            bucket["cone"].append(s.cone_hit)
        if s.intensity_hit is not None:
            bucket["intensity"].append(s.intensity_hit)

    reports: list[LeadProductCalibration] = []
    for lead in sorted(by_lead):
        for quantity, nominal in (("cone", CONE_NOMINAL_RATE), ("intensity", INTENSITY_NOMINAL_RATE)):
            hits = by_lead[lead][quantity]
            n = len(hits)
            rate = float(sum(hits)) / n if n else None
            reports.append(
                LeadProductCalibration(
                    lead_hours=lead,
                    quantity=quantity,
                    n_cases=n,
                    containment_rate=rate,
                    nominal_rate=nominal,
                    verdict=_verdict(rate, nominal, n),
                )
            )
    return reports
