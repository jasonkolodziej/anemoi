"""Real ERA5T-vs-operational skew audit wiring (#148, the skew half).

`monitoring.skew`'s `SkewMonitor`/`SkewSample`/`audit_due` are the real,
tested §4.6.3 logic -- unchanged since they were built. What was missing
(see `Monitoring.md`'s "Production wiring" note, written for the drift
half) is a real paired dataset to feed them: re-running the deterministic
stack on ERA5T inputs for a cycle old enough to audit, then pairing that
against what the operational (GDAS-driven) run actually produced.

That needs two things neither `monitoring.skew` nor `api.real_state` had:

1. **A durable record of what operationally ran.** `RealState.storms[...]
   .cycles` is in-memory only (see its own docstring) -- fine for drift's
   rolling window (30 live samples typically accumulate within one warm
   container's lifetime), but skew's audit delay is *five days*
   (`monitoring.skew.AUDIT_DELAY`), far longer than any observed
   Cloudflare Container lifetime in this project. Without a durable
   record, there is nothing left to compare against by the time ERA5T
   catches up. `OperationalCycleRecord` (below) is that record: the real
   replay inputs (`Track`/`Fix`) a cycle used, plus its real fused output,
   persisted the same "local JSON + best-effort durable mirror via
   `CheckpointStore`" way `monitoring.reference_store` already persists
   the drift reference.

2. **A way to swap the input source through the existing inference path.**
   `training.real_inference_cycle.build_real_deterministic_fn` and
   `training.real_inference_live`'s `build_live_*_x` builders now all take
   an optional `fields_fetcher` override (default: the real live/
   operational GDAS path, `real_inference_live._current_fields`,
   unchanged). `audit_one` (below) is the one real caller that passes
   something else: `real_inference_live.era5t_fields`, backed by
   `data.real_gridded.fetch_era5t_one` -- confirmed live 2026-09-22 that
   ARCO-ERA5's same store already used for Stage A pretraining also
   carries the ERA5T tail. This re-runs the *actual* deterministic stack,
   not a separate parallel approximation of it that could quietly drift
   out of sync with what production really does.

`audit_run` is the real entry point (`anemoi skew-audit`): find every
durably-recorded operational cycle that's `audit_due` and not yet
audited, replay it against ERA5T, and persist any resulting real
`SkewSample`s to the durable corpus `api.real_state.RealState.skew_report`
reads.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .skew import AUDIT_DELAY, SkewMonitor, SkewSample, audit_due

if TYPE_CHECKING:
    from ..data.besttrack import Fix, Track
    from ..inference.cycle import CycleOutput
    from ..tracking.checkpoint_store import CheckpointStore
    from ..tracking.registry import ModelRegistry
    from ..training.real_inference_live import FieldsFetcher

#: Durable-storage prefix for one real operational cycle's replay inputs --
#: one JSON object per (storm_id, cycle label), written by `RealState.
#: run_cycle` (via `record_operational_cycle`) right after a real
#: (non-synthetic-fallback) deterministic forecast, read back by the
#: offline `anemoi skew-audit` CLI -- likely from a different machine, the
#: same reason `monitoring.reference_store`'s own docstring gives for its
#: durable mirror.
OPERATIONAL_PREFIX = "monitoring/skew_operational/"

#: Durable key for the accumulated real SkewSample corpus.
SKEW_SAMPLES_KEY = "monitoring/skew_samples.json"

#: Durable key for the set of already-audited "{storm_id}:{label}" cycles.
AUDITED_CYCLES_KEY = "monitoring/skew_audited_cycles.json"

#: How many trailing real fixes to persist alongside a cycle's replay
#: inputs -- generous headroom over `training.capacity_ablation
#: .SEQUENCE_LENGTH + 1` (5), the most any live builder actually windows
#: over today.
_TRACK_WINDOW_FIXES = 20

#: If ERA5T still hasn't produced a usable real sample this long after a
#: cycle's own target time, stop retrying it on every future audit run --
#: `AUDIT_DELAY` (5 days) is the *typical* real ERA5T publish lag, but the
#: real-world variance around it (same reasoning as `real_inference_live
#: .gdas_likely_unpublished`'s own docstring) means a cycle can validly
#: need more than one audit pass before ERA5T is actually there. Twice
#: `AUDIT_DELAY` is a real, generous cutoff, not a guess with no basis.
_GIVE_UP_AFTER = 2 * AUDIT_DELAY


def _fix_to_dict(fix: Fix) -> dict[str, Any]:
    return {
        "storm_id": fix.storm_id,
        "valid_time": fix.valid_time.isoformat(),
        "lat": fix.lat,
        "lon": fix.lon,
        "max_wind_kt": fix.max_wind_kt,
        "min_pressure_mb": fix.min_pressure_mb,
        "quality": fix.quality.value,
    }


def _fix_from_dict(data: dict[str, Any]) -> Fix:
    from ..data.besttrack import Fix, TrackQuality

    return Fix(
        storm_id=data["storm_id"],
        valid_time=datetime.fromisoformat(data["valid_time"]),
        lat=data["lat"],
        lon=data["lon"],
        max_wind_kt=data["max_wind_kt"],
        min_pressure_mb=data["min_pressure_mb"],
        quality=TrackQuality(data["quality"]),
    )


@dataclass(frozen=True, slots=True)
class OperationalCycleRecord:
    """Everything needed to replay one real operational cycle's real
    deterministic forecast later against ERA5T: the storm's real recent
    history and the exact `Fix` the cycle ran against, captured at the
    time -- not re-derived from `RealState`'s current storm state days
    later, which may have moved on well past this cycle's own target
    time."""

    storm_id: str
    label: str
    track_name: str | None
    track_fixes: tuple[Fix, ...]
    current: Fix
    target_time: datetime
    lead_hours: tuple[int, ...]
    op_lats: tuple[float, ...]
    op_lons: tuple[float, ...]
    op_winds_kt: tuple[float, ...]

    def track(self) -> Track:
        from ..data.besttrack import Track

        return Track(storm_id=self.storm_id, fixes=self.track_fixes, name=self.track_name)


def _record_key(storm_id: str, label: str) -> str:
    return f"{OPERATIONAL_PREFIX}{storm_id}/{label}.json"


def record_to_json(record: OperationalCycleRecord) -> str:
    return json.dumps(
        {
            "storm_id": record.storm_id,
            "label": record.label,
            "track_name": record.track_name,
            "track_fixes": [_fix_to_dict(f) for f in record.track_fixes],
            "current": _fix_to_dict(record.current),
            "target_time": record.target_time.isoformat(),
            "lead_hours": list(record.lead_hours),
            "op_lats": list(record.op_lats),
            "op_lons": list(record.op_lons),
            "op_winds_kt": list(record.op_winds_kt),
        },
        indent=2,
        sort_keys=True,
    )


def record_from_json(text: str) -> OperationalCycleRecord:
    data = json.loads(text)
    return OperationalCycleRecord(
        storm_id=data["storm_id"],
        label=data["label"],
        track_name=data["track_name"],
        track_fixes=tuple(_fix_from_dict(d) for d in data["track_fixes"]),
        current=_fix_from_dict(data["current"]),
        target_time=datetime.fromisoformat(data["target_time"]),
        lead_hours=tuple(data["lead_hours"]),
        op_lats=tuple(data["op_lats"]),
        op_lons=tuple(data["op_lons"]),
        op_winds_kt=tuple(data["op_winds_kt"]),
    )


def record_operational_cycle(
    storm_id: str,
    track: Track,
    current: Fix,
    output: CycleOutput,
    *,
    local_root: Path | str,
    checkpoint_store: CheckpointStore | None = None,
) -> None:
    """Persist one real operational cycle's replay inputs, best-effort --
    called from `RealState.run_cycle` right after a real (non-synthetic-
    fallback) deterministic forecast, i.e. ``output.deterministic
    .contributors`` non-empty (the synthetic/climatological fallback's own
    ``contributors={}`` is the existing "no real model ran" signal, see
    `api.real_state._synthetic_fallback_deterministic`) -- there is
    nothing real to audit for a cycle no real model contributed to.

    Never raises: a skew-recording failure must not fail the cycle that
    triggered it, the same best-effort contract `RealState
    ._record_drift_sample`'s own docstring already establishes for #148's
    drift half.
    """
    det = output.deterministic
    if not det.contributors:
        return
    fixes = tuple(f for f in track.fixes if f.valid_time <= current.valid_time)[
        -_TRACK_WINDOW_FIXES:
    ]
    if not fixes:
        return
    record = OperationalCycleRecord(
        storm_id=storm_id,
        label=output.label,
        track_name=track.name,
        track_fixes=fixes,
        current=current,
        target_time=det.target_time,
        lead_hours=tuple(int(h) for h in det.lead_hours),
        op_lats=tuple(float(v) for v in det.lats),
        op_lons=tuple(float(v) for v in det.lons),
        op_winds_kt=tuple(float(v) for v in det.winds_kt),
    )
    try:
        path = Path(local_root) / "skew" / "operational" / storm_id / f"{output.label}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(record_to_json(record))
        if checkpoint_store is not None:
            checkpoint_store.upload(path, _record_key(storm_id, output.label))
    except Exception:  # noqa: BLE001 - best-effort, see docstring
        pass


def list_operational_records(checkpoint_store: CheckpointStore) -> list[OperationalCycleRecord]:
    """Every real operational cycle record currently in durable storage --
    the offline `anemoi skew-audit` CLI's own real input list. Requires a
    real ``checkpoint_store`` (unlike `cli.cmd_drift_reference_fit`'s
    optional one): these records are written to a live API process's own
    local disk, which a Cloudflare Container's cold start does not
    preserve -- durable storage is the only way an audit run on a
    different machine can discover them at all, not just a nice-to-have
    mirror.
    """
    records: list[OperationalCycleRecord] = []
    bucket = checkpoint_store.config.bucket
    for key in checkpoint_store.list(OPERATIONAL_PREFIX):
        if not key.endswith(".json"):
            continue
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / "record.json"
            try:
                checkpoint_store.download(f"s3://{bucket}/{key}", tmp_path)
                records.append(record_from_json(tmp_path.read_text()))
            except Exception:  # noqa: BLE001 - one bad/unreadable record must not sink the run
                continue
    return records


def _skew_sample_to_dict(sample: SkewSample) -> dict[str, Any]:
    return {
        "target_time": sample.target_time.isoformat(),
        "lead_hours": sample.lead_hours,
        "operational_lat": sample.operational_lat,
        "operational_lon": sample.operational_lon,
        "operational_wind_kt": sample.operational_wind_kt,
        "era5t_lat": sample.era5t_lat,
        "era5t_lon": sample.era5t_lon,
        "era5t_wind_kt": sample.era5t_wind_kt,
    }


def _skew_sample_from_dict(data: dict[str, Any]) -> SkewSample:
    return SkewSample(
        target_time=datetime.fromisoformat(data["target_time"]),
        lead_hours=int(data["lead_hours"]),
        operational_lat=float(data["operational_lat"]),
        operational_lon=float(data["operational_lon"]),
        operational_wind_kt=float(data["operational_wind_kt"]),
        era5t_lat=float(data["era5t_lat"]),
        era5t_lon=float(data["era5t_lon"]),
        era5t_wind_kt=float(data["era5t_wind_kt"]),
    )


def save_skew_samples(
    samples: list[SkewSample], path: Path | str, checkpoint_store: CheckpointStore | None = None
) -> None:
    """Local write always succeeds, durable push best-effort -- the same
    contract `monitoring.reference_store.save_reference` already uses."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([_skew_sample_to_dict(s) for s in samples], indent=2))
    if checkpoint_store is None:
        return
    try:
        checkpoint_store.upload(path, SKEW_SAMPLES_KEY)
    except Exception:  # noqa: BLE001 - a flaky durable store must never fail a save
        pass


def load_skew_samples(
    path: Path | str, checkpoint_store: CheckpointStore | None = None
) -> list[SkewSample]:
    """Best-effort pull from durable storage, then read ``path`` -- an
    empty list if nothing has ever been audited yet, not an exception (the
    same honest-empty contract `monitoring.reference_store.load_reference`
    already uses for a not-yet-fit reference)."""
    path = Path(path)
    if checkpoint_store is not None:
        try:
            if checkpoint_store.exists(SKEW_SAMPLES_KEY):
                bucket = checkpoint_store.config.bucket
                checkpoint_store.download(f"s3://{bucket}/{SKEW_SAMPLES_KEY}", path)
        except Exception:  # noqa: BLE001 - a stale/local-only corpus must still be usable
            pass
    if not path.exists():
        return []
    try:
        return [_skew_sample_from_dict(d) for d in json.loads(path.read_text())]
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return []


def _load_audited_cycles(
    path: Path | str, checkpoint_store: CheckpointStore | None
) -> set[str]:
    path = Path(path)
    if checkpoint_store is not None:
        try:
            if checkpoint_store.exists(AUDITED_CYCLES_KEY):
                bucket = checkpoint_store.config.bucket
                checkpoint_store.download(f"s3://{bucket}/{AUDITED_CYCLES_KEY}", path)
        except Exception:  # noqa: BLE001
            pass
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text()))
    except (json.JSONDecodeError, ValueError):
        return set()


def _save_audited_cycles(
    audited: set[str], path: Path | str, checkpoint_store: CheckpointStore | None
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(audited), indent=2))
    if checkpoint_store is None:
        return
    try:
        checkpoint_store.upload(path, AUDITED_CYCLES_KEY)
    except Exception:  # noqa: BLE001
        pass


@dataclass(frozen=True, slots=True)
class _AuditPlan:
    """Just enough of `inference.scheduler.CyclePlan` for
    `build_real_deterministic_fn`'s closure to run: it only ever reads
    ``plan.target_time`` (see its own return statement). Reconstructing a
    full `CyclePlan` would need a real `LatencyOracle` run against a cycle
    that already happened days ago -- information this audit doesn't have
    and, since it only replays the deterministic path, doesn't need."""

    target_time: datetime


def _era5t_fetcher(era5_store: Any) -> FieldsFetcher:
    """A `FieldsFetcher` bound to one already-open ERA5T Zarr store handle
    -- `audit_run` opens it once and reuses it across every due record in
    one CLI invocation, the same "share one store handle" optimisation
    `data.era5_cache`'s own module docstring already establishes for
    Stage A's thousands-of-samples case (here, a handful of cycles per
    run, but the store-open cost is the same either way)."""
    from ..data.real_gridded import fetch_era5t_one

    def fetch(track: Track, current: Fix, cache_dir: Path | str) -> Any:
        del track, cache_dir
        try:
            return fetch_era5t_one(
                current.valid_time, current.lat, current.lon, store=era5_store
            )
        except Exception:  # noqa: BLE001 - no real field available must degrade, never crash
            return None

    return fetch


def audit_one(
    record: OperationalCycleRecord,
    registry: ModelRegistry,
    checkpoint_store: CheckpointStore,
    cache_dir: Path | str,
    *,
    era5_store: Any = None,
) -> list[SkewSample]:
    """Re-run the real deterministic stack for one past operational cycle
    against ERA5T instead of GDAS, and pair the result against what
    operationally ran at each real lead hour shared by both -- the real
    measurement §4.6.3 calls for. Returns no samples (not an exception) if
    no real model could contribute to the ERA5T replay (`InferenceCycleError`
    -- e.g. ERA5T genuinely isn't available yet for this exact valid time),
    the same "can't contribute this time" contract every other real
    inference path in this codebase already has to handle.
    """
    from ..training.real_inference_cycle import InferenceCycleError, build_real_deterministic_fn
    from ..training.real_inference_live import era5t_fields

    fetcher = _era5t_fetcher(era5_store) if era5_store is not None else era5t_fields
    deterministic_fn = build_real_deterministic_fn(
        record.track(), registry, checkpoint_store, cache_dir, fields_fetcher=fetcher,
    )
    try:
        forecast = deterministic_fn(_AuditPlan(record.target_time), record.current)
    except InferenceCycleError:
        return []

    era5t_by_lead = dict(
        zip(forecast.lead_hours, zip(forecast.lats, forecast.lons, forecast.winds_kt, strict=True),
            strict=True)
    )
    samples: list[SkewSample] = []
    for lead, op_lat, op_lon, op_wind in zip(
        record.lead_hours, record.op_lats, record.op_lons, record.op_winds_kt, strict=True
    ):
        if lead not in era5t_by_lead:
            continue
        e_lat, e_lon, e_wind = era5t_by_lead[lead]
        samples.append(
            SkewSample(
                target_time=record.target_time,
                lead_hours=lead,
                operational_lat=op_lat,
                operational_lon=op_lon,
                operational_wind_kt=op_wind,
                era5t_lat=float(e_lat),
                era5t_lon=float(e_lon),
                era5t_wind_kt=float(e_wind),
            )
        )
    return samples


def _prune_samples(samples: list[SkewSample], now: datetime) -> list[SkewSample]:
    monitor = SkewMonitor()
    monitor.samples = list(samples)
    monitor.prune(now)
    return monitor.samples


def audit_run(
    registry: ModelRegistry,
    checkpoint_store: CheckpointStore,
    cache_dir: Path | str,
    local_root: Path | str,
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    """Full real audit pass: every durably-recorded real operational cycle
    that's `monitoring.skew.audit_due` and not yet audited gets replayed
    against ERA5T (§4.6.3), and any resulting real `SkewSample`s are
    appended to the durably-persisted corpus `api.real_state.RealState
    .skew_report` reads. The real entry point behind `anemoi skew-audit`.

    A cycle whose ERA5T replay keeps coming back empty for more than
    `_GIVE_UP_AFTER` past its own target time is marked audited anyway
    (see `_GIVE_UP_AFTER`'s own docstring) -- otherwise a genuinely
    unreachable cycle would be re-fetched from durable storage and
    re-attempted forever.

    Returns a small, real progress summary (not fabricated) for the CLI
    to print.
    """
    now = now or datetime.now(UTC)
    records = list_operational_records(checkpoint_store)

    audited_path = Path(local_root) / "skew" / "audited_cycles.json"
    audited = _load_audited_cycles(audited_path, checkpoint_store)
    samples_path = Path(local_root) / "skew" / "skew_samples.json"
    samples = load_skew_samples(samples_path, checkpoint_store)

    due = [
        r
        for r in records
        if audit_due(r.target_time, now) and f"{r.storm_id}:{r.label}" not in audited
    ]

    era5_store = None
    if due:
        from ..data.real_gridded import open_era5_store

        try:
            era5_store = open_era5_store()
        except Exception:  # noqa: BLE001 - fall back to per-sample opens inside audit_one
            era5_store = None

    n_audited = 0
    n_new_samples = 0
    for record in due:
        try:
            new_samples = audit_one(
                record, registry, checkpoint_store, cache_dir, era5_store=era5_store
            )
        except Exception:  # noqa: BLE001 - one bad record (corrupted payload, a
            # real mismatch between a stored record's lead_hours/op_* arrays
            # tripping audit_one's own zip(..., strict=True)) must degrade,
            # not abort every other due record's audit this run -- the same
            # per-record degrade contract list_operational_records already
            # uses for an unreadable durable record.
            new_samples = []
        if new_samples:
            samples.extend(new_samples)
            n_new_samples += len(new_samples)
            audited.add(f"{record.storm_id}:{record.label}")
            n_audited += 1
        elif now - record.target_time > _GIVE_UP_AFTER:
            audited.add(f"{record.storm_id}:{record.label}")
            n_audited += 1

    samples = _prune_samples(samples, now)
    save_skew_samples(samples, samples_path, checkpoint_store)
    _save_audited_cycles(audited, audited_path, checkpoint_store)

    return {
        "n_records": len(records),
        "n_due": len(due),
        "n_audited": n_audited,
        "n_samples_added": n_new_samples,
    }
