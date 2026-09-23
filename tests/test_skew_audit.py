"""Real ERA5T-vs-operational skew audit wiring (monitoring.skew_audit, #148)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.inference.cycle import DeterministicForecast
from anemoi.monitoring.skew import AUDIT_DELAY, SkewSample
from anemoi.monitoring.skew_audit import (
    OPERATIONAL_PREFIX,
    OperationalCycleRecord,
    audit_run,
    list_operational_records,
    load_skew_samples,
    record_from_json,
    record_operational_cycle,
    record_to_json,
    save_skew_samples,
)
from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config

#: Mirrors `monitoring.skew_audit._GIVE_UP_AFTER` -- kept as a literal here
#: rather than importing the private constant, so this test doesn't reach
#: past the module's public surface.
_GIVE_UP_AFTER = 2 * AUDIT_DELAY

_CONFIG = S3Config(
    endpoint_url="https://example.r2.cloudflarestorage.com",
    bucket="anemoi-checkpoints", access_key_id="key", secret_access_key="secret",
)


class _FakeClient:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key, local_path):
        self.objects[key] = local_path.read_bytes()

    def get(self, key, local_path):
        local_path.write_bytes(self.objects[key])

    def exists(self, key):
        return key in self.objects

    def list_keys(self, prefix):
        return sorted(k for k in self.objects if k.startswith(prefix))


def _fix(storm_id: str, valid_time: datetime, lat: float, quality=TrackQuality.FINAL) -> Fix:
    return Fix(
        storm_id=storm_id, valid_time=valid_time, lat=lat, lon=-60.0,
        max_wind_kt=50.0, min_pressure_mb=990.0, quality=quality,
    )


def _record(storm_id="AL012026", label="20260901_00Z", target_time=None) -> OperationalCycleRecord:
    target_time = target_time or datetime(2026, 9, 1, tzinfo=UTC)
    fixes = tuple(
        _fix(storm_id, target_time - timedelta(hours=6 * i), 20.0 - i) for i in range(3, -1, -1)
    )
    return OperationalCycleRecord(
        storm_id=storm_id, label=label, track_name="Test", track_fixes=fixes,
        current=fixes[-1], target_time=target_time, lead_hours=(48,),
        op_lats=(22.0,), op_lons=(-63.0,), op_winds_kt=(60.0,),
    )


def test_record_json_round_trips_exactly():
    record = _record()
    restored = record_from_json(record_to_json(record))
    assert restored.storm_id == record.storm_id
    assert restored.label == record.label
    assert restored.track_fixes == record.track_fixes
    assert restored.current == record.current
    assert restored.target_time == record.target_time
    assert restored.lead_hours == record.lead_hours
    assert restored.op_lats == record.op_lats


def test_record_reconstructs_a_valid_track():
    record = _record()
    track = record.track()
    assert isinstance(track, Track)
    assert track.storm_id == record.storm_id
    assert track.name == "Test"
    assert track.fixes == record.track_fixes


def _make_output(contributors, label="20260901_00Z", target_time=None):
    det = DeterministicForecast(
        target_time=target_time or datetime(2026, 9, 1, tzinfo=UTC), lead_hours=(48,),
        lats=np.array([22.0]), lons=np.array([-63.0]), winds_kt=np.array([60.0]),
        contributors=contributors,
    )

    class _Output:
        deterministic = det

    output = _Output()
    output.label = label
    return output


def test_record_operational_cycle_is_a_noop_for_the_synthetic_fallback(tmp_path):
    """No real model contributed (contributors={}) -- nothing real to audit,
    so no local file and no durable upload, the same "no real model ran"
    signal `real_state._synthetic_fallback_deterministic` already uses."""
    track = Track(
        storm_id="AL012026", fixes=(_fix("AL012026", datetime(2026, 9, 1, tzinfo=UTC), 20.0),),
    )
    current = track.fixes[0]
    store = CheckpointStore(_CONFIG, client=_FakeClient())

    record_operational_cycle(
        "AL012026", track, current, _make_output({}),
        local_root=tmp_path, checkpoint_store=store,
    )
    assert not (tmp_path / "skew" / "operational").exists()
    assert store.list(OPERATIONAL_PREFIX) == []


def test_record_operational_cycle_persists_locally_and_durably(tmp_path):
    track = Track(
        storm_id="AL012026",
        fixes=tuple(
            _fix("AL012026", datetime(2026, 9, 1, tzinfo=UTC) - timedelta(hours=6 * i), 20.0 - i)
            for i in range(3, -1, -1)
        ),
    )
    current = track.fixes[-1]
    store = CheckpointStore(_CONFIG, client=_FakeClient())
    output = _make_output({"lstm": 1.0})

    record_operational_cycle(
        "AL012026", track, current, output, local_root=tmp_path, checkpoint_store=store,
    )

    local_path = tmp_path / "skew" / "operational" / "AL012026" / f"{output.label}.json"
    assert local_path.exists()
    assert store.exists(f"{OPERATIONAL_PREFIX}AL012026/{output.label}.json")

    records = list_operational_records(store)
    assert len(records) == 1
    assert records[0].storm_id == "AL012026"
    assert records[0].current == current


def test_save_then_load_skew_samples_round_trips(tmp_path):
    samples = [
        SkewSample(
            target_time=datetime(2026, 9, 1, tzinfo=UTC), lead_hours=48,
            operational_lat=22.0, operational_lon=-63.0, operational_wind_kt=60.0,
            era5t_lat=22.5, era5t_lon=-63.5, era5t_wind_kt=58.0,
        )
    ]
    path = tmp_path / "skew_samples.json"
    save_skew_samples(samples, path)
    loaded = load_skew_samples(path)
    assert len(loaded) == 1
    assert loaded[0].track_delta_nm > 0
    assert loaded[0].intensity_delta_kt == pytest.approx(2.0)


def test_load_skew_samples_is_empty_when_nothing_was_ever_audited(tmp_path):
    assert load_skew_samples(tmp_path / "never.json") == []


def test_audit_run_replays_only_due_records_and_persists_the_result(tmp_path, monkeypatch):
    """Wiring test, not a model-math test (that's `test_real_inference_cycle
    .py`'s job): `audit_one` is monkeypatched to a canned real-shaped
    result, so this exercises `audit_run`'s own due-filtering, audited-set
    bookkeeping, and durable persistence -- the real gap this closes."""
    from anemoi.monitoring import skew_audit as sa

    def _no_real_network():
        raise RuntimeError("no real network in this unit test")

    monkeypatch.setattr("anemoi.data.real_gridded.open_era5_store", _no_real_network)

    now = datetime(2026, 9, 20, tzinfo=UTC)
    due_record = _record(label="due", target_time=now - AUDIT_DELAY - timedelta(days=1))
    not_due_record = _record(label="not_due", target_time=now - timedelta(hours=6))
    give_up_record = _record(label="give_up", target_time=now - _GIVE_UP_AFTER - timedelta(days=1))

    store = CheckpointStore(_CONFIG, client=_FakeClient())
    for record in (due_record, not_due_record, give_up_record):
        record_operational_cycle(
            record.storm_id, record.track(), record.current,
            _make_output({"lstm": 1.0}, label=record.label, target_time=record.target_time),
            local_root=tmp_path, checkpoint_store=store,
        )

    seen_labels: list[str] = []

    def fake_audit_one(record, registry, checkpoint_store, cache_dir, *, era5_store=None):
        seen_labels.append(record.label)
        if record.label == "due":
            return [
                SkewSample(
                    target_time=record.target_time, lead_hours=48,
                    operational_lat=record.op_lats[0], operational_lon=record.op_lons[0],
                    operational_wind_kt=record.op_winds_kt[0],
                    era5t_lat=record.op_lats[0] + 0.5, era5t_lon=record.op_lons[0] - 0.5,
                    era5t_wind_kt=record.op_winds_kt[0] - 3.0,
                )
            ]
        return []  # give_up: ERA5T genuinely never showed up for this hour

    monkeypatch.setattr(sa, "audit_one", fake_audit_one)

    summary = audit_run(
        registry=object(), checkpoint_store=store, cache_dir=tmp_path, local_root=tmp_path, now=now,
    )

    assert summary["n_records"] == 3
    assert sorted(seen_labels) == ["due", "give_up"]  # not_due never replayed
    assert summary["n_audited"] == 2  # due (real sample) + give_up (timed out)
    assert summary["n_samples_added"] == 1

    persisted = load_skew_samples(tmp_path / "skew" / "skew_samples.json", store)
    assert len(persisted) == 1
    assert persisted[0].lead_hours == 48

    # A second run must not re-audit the same cycles.
    seen_labels.clear()
    summary2 = audit_run(
        registry=object(), checkpoint_store=store, cache_dir=tmp_path, local_root=tmp_path, now=now,
    )
    assert seen_labels == []
    assert summary2["n_audited"] == 0
