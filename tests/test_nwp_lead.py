"""Live cycles read the GFS forecast valid at their own time (#215).

The live path fetched the cycle-time *analysis*, published ~t+3:30 -- two
hours after the cycle runs at t+1:30 -- so the gridded models almost never
contributed to a scheduled cycle, while the payload said "NWP t-6". Now:
the t-6 cycle's f006, else the t-12 cycle's f012 (flagged), cached by
position; Stage B trains on the same forecast hour and records it, and a
model fed another one is flagged.
"""

from __future__ import annotations

import json
import warnings
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.features import GriddedFields
from anemoi.data.gdas_cache import (
    STAGE_B_NWP_LEAD_HOURS,
    CacheLeadMismatch,
    cache_nwp_lead_hours,
    run_fetch_cache,
)
from anemoi.data.gridded_cache import FetchTask, load_cached_fields, save_cached_fields
from anemoi.data.real_gridded import gfs_url
from anemoi.data.sources import Flavor
from anemoi.time_utils import NWP_LAG_HOURS
from anemoi.training.real_inference_live import fetch_live_nwp

pytestmark = [
    pytest.mark.filterwarnings("ignore::UserWarning"),
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
]

T = datetime(2026, 9, 1, 0, tzinfo=UTC)


def _fields(lead=6, source="x"):
    g = np.full((5, 5), 1.0)
    return GriddedFields(
        valid_time=T, flavor=Flavor.GDAS_FINETUNE, u200=g, v200=g, u850=g, v850=g,
        z500=g * 5750, rh700=g * 60, t700=g * 280, mslp=g * 1010, sst=g * 28, ohc=g * 60,
        nwp_lead_hours=lead, source=source,
    )


def _track(n=3):
    return Track(storm_id="AL012026", fixes=tuple(
        Fix(storm_id="AL012026", valid_time=T + timedelta(hours=6 * i), lat=20.0 + i, lon=-60.0,
            max_wind_kt=50.0, min_pressure_mb=995.0, quality=TrackQuality.WORKING)
        for i in range(n)
    ))


def test_stage_b_trains_on_the_lead_live_cycles_read():
    assert STAGE_B_NWP_LEAD_HOURS == NWP_LAG_HOURS == 6


def test_gfs_url_names_the_forecast_valid_at_the_time():
    base = "https://noaa-gfs-bdp-pds.s3.amazonaws.com"
    assert gfs_url(T, 0) == f"{base}/gfs.20260901/00/atmos/gfs.t00z.pgrb2.0p25.anl"
    # 00Z valid from the previous day's 18Z cycle.
    assert gfs_url(T, 6) == f"{base}/gfs.20260831/18/atmos/gfs.t18z.pgrb2.0p25.f006"
    assert gfs_url(T, 12) == f"{base}/gfs.20260831/12/atmos/gfs.t12z.pgrb2.0p25.f012"
    with pytest.raises(ValueError):
        gfs_url(T, 5)


def test_live_fields_come_from_the_t_minus_6_forecast(tmp_path, monkeypatch):
    calls = []

    def fetch_one(valid_time, lat, lon, *, lead_hours=0, **kw):
        calls.append(lead_hours)
        return _fields(lead_hours)

    monkeypatch.setattr("anemoi.data.gdas_cache.fetch_one", fetch_one)
    track = _track()
    current = track.fixes[-1]
    fields, nwp = fetch_live_nwp(track, current, tmp_path)
    assert calls == [6]
    assert (nwp.lag_hours, nwp.forecast_hour, nwp.degraded) == (6, 6, False)
    assert nwp.nwp_cycle == current.valid_time - timedelta(hours=6)
    assert fields.nwp_lead_hours == 6

    calls.clear()
    fetch_live_nwp(track, current, tmp_path)
    assert calls == []  # cached

    # A different position is a different patch, not the cached one.
    moved = Fix(storm_id=current.storm_id, valid_time=current.valid_time, lat=current.lat + 1,
                lon=current.lon, max_wind_kt=50.0, min_pressure_mb=995.0,
                quality=TrackQuality.WORKING)
    fetch_live_nwp(track, moved, tmp_path)
    assert calls == [6]


def test_a_missing_t_minus_6_cycle_falls_back_to_t_minus_12(tmp_path, monkeypatch):
    def fetch_one(valid_time, lat, lon, *, lead_hours=0, **kw):
        if lead_hours == 6:
            raise OSError("404")
        return _fields(lead_hours)

    monkeypatch.setattr("anemoi.data.gdas_cache.fetch_one", fetch_one)
    fields, nwp = fetch_live_nwp(_track(), _track().fixes[-1], tmp_path)
    assert (nwp.lag_hours, nwp.degraded, fields.nwp_lead_hours) == (12, True, 12)


def test_no_nwp_within_the_budget_is_none(tmp_path, monkeypatch):
    def fetch_one(*a, **k):
        raise OSError("down")

    monkeypatch.setattr("anemoi.data.gdas_cache.fetch_one", fetch_one)
    assert fetch_live_nwp(_track(), _track().fixes[-1], tmp_path) == (None, None)


def test_cached_fields_keep_their_lead_and_source(tmp_path):
    path = tmp_path / "f.npz"
    save_cached_fields(path, _fields(6, "gfs-url"), FetchTask("AL012026", T, 20.0, -60.0))
    loaded = load_cached_fields(path)
    assert (loaded.nwp_lead_hours, loaded.source) == (6, "gfs-url")

    # A cache written before #215 has neither: an analysis, source unknown.
    legacy = tmp_path / "legacy.npz"
    with np.load(path) as data:
        kept = {k: data[k] for k in data.files if k not in ("nwp_lead_hours", "source")}
        np.savez(legacy, **kept)
    old = load_cached_fields(legacy)
    assert (old.nwp_lead_hours, old.source) == (0, "")


def test_a_cache_dir_holds_one_lead(tmp_path):
    track = _track(1)
    run_fetch_cache([track], tmp_path / "f6", fetch_fn=lambda *a: _fields(6),
                    min_valid_time=None, progress_every=0, lead_hours=6)
    assert cache_nwp_lead_hours(tmp_path / "f6") == 6
    assert json.loads((tmp_path / "f6" / "_meta.json").read_text()) == {"nwp_lead_hours": 6}

    # A pre-#215 cache (npz files, no _meta.json) holds analyses.
    legacy = tmp_path / "legacy"
    save_cached_fields(legacy / "AL012026" / "x.npz", _fields(0), FetchTask("AL012026", T, 20, -60))
    assert cache_nwp_lead_hours(legacy) == 0
    with pytest.raises(CacheLeadMismatch, match="holds f000 fields"):
        run_fetch_cache([track], legacy, fetch_fn=lambda *a: _fields(6),
                        min_valid_time=None, progress_every=0, lead_hours=6)


def test_training_records_the_lead_it_trained_on(tmp_path):
    from anemoi.tracking.experiment_tracking import NWP_LEAD_TAG, gridded_input_tags

    run_fetch_cache([_track(1)], tmp_path, fetch_fn=lambda *a: _fields(6),
                    min_valid_time=None, progress_every=0, lead_hours=6)
    assert gridded_input_tags(tmp_path) == {NWP_LEAD_TAG: "6"}
    assert gridded_input_tags(None) == {}


# ---- through the real API ---------------------------------------------------

pytest.importorskip("fastapi")
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from fastapi.testclient import TestClient

RADII = ", ".join(["-999"] * 12)
_HURDAT2 = f"""\
AL012026,     NWPTEST,     2,
20260901, 0000,  , TS, 20.0N,  60.0W,  40, 1005, {RADII},
20260901, 0600,  , TS, 20.5N,  61.0W,  45, 1002, {RADII},
"""


class _MemoryS3:
    def __init__(self):
        self.objects = {}

    def put(self, key, local_path):
        self.objects[key] = Path(local_path).read_bytes()

    def get(self, key, local_path):
        Path(local_path).write_bytes(self.objects[key])

    def exists(self, key):
        return key in self.objects

    def list_keys(self, prefix):
        return [k for k in self.objects if k.startswith(prefix)]


@pytest.fixture
def client(tmp_path, monkeypatch):
    from anemoi.api import real_state
    from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config

    hurdat2 = tmp_path / "hurdat2.txt"
    hurdat2.write_text(_HURDAT2)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANEMOI_API_REAL_STATE", "1")
    monkeypatch.setattr("anemoi.data.live_atcf.fetch_live_tracks", lambda: [])
    store = CheckpointStore(
        S3Config(endpoint_url="https://example.r2.cloudflarestorage.com", bucket="t",
                 access_key_id="k", secret_access_key="s"),
        client=_MemoryS3(),
    )
    real_state._REAL_STATE = real_state.RealState(
        hurdat2_path=str(hurdat2), registry_root=str(tmp_path / "registry"),
        checkpoint_store=store, cache_dir=str(tmp_path / "gdas"),
    )
    from anemoi.api.main import app

    yield TestClient(app)
    real_state._REAL_STATE = None


def _run(client):
    return client.post(
        "/v1/storms/AL012026/cycles", json={"cycle": "20260901_06Z"},
        headers={"X-Anemoi-Run-Source": "scheduled"},
    ).json()


def test_the_cycle_reports_the_nwp_it_really_used(client, monkeypatch):
    def fetch_one(valid_time, lat, lon, *, lead_hours=0, **kw):
        if lead_hours == 6:
            raise OSError("t-6 cycle missing")
        return _fields(lead_hours, gfs_url(valid_time, lead_hours))

    monkeypatch.setattr("anemoi.data.gdas_cache.fetch_one", fetch_one)
    body = _run(client)
    assert body["payload"]["nwp_cycle_lag_hours"] == 12
    assert "nwp_stale=12h" in body["payload"]["flags"]
    p = body["provenance"]
    assert p["nwp_forecast_hour"] == 12
    assert p["nwp_cycle"].startswith("2026-08-31T18:00")


def test_no_nwp_at_all_is_flagged(client, monkeypatch):
    monkeypatch.setattr(
        "anemoi.data.gdas_cache.fetch_one", lambda *a, **k: (_ for _ in ()).throw(OSError("down")),
    )
    body = _run(client)
    assert "nwp_unavailable" in body["payload"]["flags"]
    assert body["provenance"]["nwp_forecast_hour"] is None
