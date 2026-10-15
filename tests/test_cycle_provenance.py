"""What a cycle actually ran on, recorded honestly (#214).

Before: every cycle used the storm's *latest* fix relabelled as the target
time (for a past label, a position from days later) and said `vitals:
observed`; `issued_at`/`on_time` came from the plan, not the clock; a cycle
no real model ran on carried no flag; and nothing recorded model versions,
the fusion used, the gridded source, the commit or the config.
"""

from __future__ import annotations

import json
import warnings
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from fastapi.testclient import TestClient

from anemoi import provenance
from anemoi.api.real_state import initial_fix
from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.time_utils import cycle_label, floor_synoptic

pytestmark = [
    pytest.mark.api,
    pytest.mark.filterwarnings("ignore::UserWarning"),
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
]

T0 = datetime(2026, 9, 1, 0, tzinfo=UTC)
SCHED = {"X-Anemoi-Run-Source": "scheduled"}


def _track(quality=TrackQuality.WORKING, hours=(0, 6, 12, 18), storm_id="AL012026"):
    return Track(storm_id=storm_id, fixes=tuple(
        Fix(storm_id=storm_id, valid_time=T0 + timedelta(hours=h), lat=20.0 + h / 10,
            lon=-60.0 - h / 10, max_wind_kt=40.0 + h, min_pressure_mb=1000.0 - h, quality=quality)
        for h in hours
    ))


# ---- initial_fix --------------------------------------------------------------


def test_the_fix_at_the_cycle_time_is_used_not_the_latest():
    fix, source = initial_fix(_track(), T0 + timedelta(hours=6))
    assert source == "tcvitals"
    assert (fix.lat, fix.max_wind_kt, fix.quality) == (20.6, 46.0, TrackQuality.WORKING)


def test_an_archive_storm_says_its_fix_is_the_final_best_track():
    fix, source = initial_fix(_track(TrackQuality.FINAL), T0 + timedelta(hours=6))
    assert source == "final_best_track"
    assert fix.quality is TrackQuality.WORKING  # never a FINAL model input


def test_missing_vitals_are_extrapolated_and_estimated():
    fix, source = initial_fix(_track(hours=(0, 6, 12)), T0 + timedelta(hours=18))
    assert source == "extrapolated"
    assert fix.quality is TrackQuality.ESTIMATED
    assert fix.lat == pytest.approx(21.8)  # 12Z + one more 6 h step of +0.6


def test_withheld_vitals_are_extrapolated_too():
    fix, source = initial_fix(_track(), T0 + timedelta(hours=18), withhold_vitals=True)
    assert source == "extrapolated"
    assert fix.lat == pytest.approx(21.8)


def test_one_earlier_fix_is_persisted():
    fix, source = initial_fix(_track(hours=(0,)), T0 + timedelta(hours=6))
    assert source == "persisted"
    assert (fix.lat, fix.quality) == (20.0, TrackQuality.ESTIMATED)


def test_overrides_apply_on_top():
    fix, _ = initial_fix(_track(), T0 + timedelta(hours=6), lat=25.0, wind_kt=100.0)
    assert (fix.lat, fix.lon, fix.max_wind_kt) == (25.0, -60.6, 100.0)


# ---- provenance helpers -----------------------------------------------------


def test_git_sha_and_config_digest(monkeypatch):
    provenance.git_sha.cache_clear()
    monkeypatch.setenv("ANEMOI_GIT_SHA", "abc123")
    assert provenance.summary()["git_sha"] == "abc123"
    provenance.git_sha.cache_clear()
    digest = provenance.config_digest()
    assert len(digest) == 64 and digest == provenance.config_digest()


def test_build_info_is_read_from_next_to_configs(monkeypatch, tmp_path):
    import shutil

    from anemoi import config

    shutil.copytree(config.config_dir(), tmp_path / "configs")
    (tmp_path / "build-info.json").write_text(json.dumps({"git_sha": "feedbeef"}))
    monkeypatch.setenv("ANEMOI_CONFIG_DIR", str(tmp_path / "configs"))
    monkeypatch.delenv("ANEMOI_GIT_SHA", raising=False)
    provenance.build_info.cache_clear()
    provenance.git_sha.cache_clear()
    try:
        assert provenance.git_sha() == "feedbeef"
    finally:
        provenance.build_info.cache_clear()
        provenance.git_sha.cache_clear()


# ---- through the real API ---------------------------------------------------

RADII = ", ".join(["-999"] * 12)
_HURDAT2 = f"""\
AL012026,     PROVTEST,     4,
20260901, 0000,  , TS, 20.0N,  60.0W,  40, 1005, {RADII},
20260901, 0600,  , TS, 20.5N,  61.0W,  45, 1002, {RADII},
20260901, 1200,  , TS, 21.0N,  62.0W,  50,  995, {RADII},
20260901, 1800,  , HU, 21.6N,  63.2W,  65,  985, {RADII},
"""


class _MemoryS3:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key, local_path):
        self.objects[key] = Path(local_path).read_bytes()

    def get(self, key, local_path):
        Path(local_path).write_bytes(self.objects[key])

    def exists(self, key):
        return key in self.objects

    def list_keys(self, prefix):
        return [k for k in self.objects if k.startswith(prefix)]


@pytest.fixture
def s3():
    return _MemoryS3()


@pytest.fixture
def client(tmp_path, monkeypatch, s3):
    from anemoi.api import real_state
    from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config

    hurdat2 = tmp_path / "hurdat2.txt"
    hurdat2.write_text(_HURDAT2)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANEMOI_API_REAL_STATE", "1")
    monkeypatch.setattr("anemoi.data.live_atcf.fetch_live_tracks", lambda: [])
    # No network: no gridded analysis unless a test supplies one.
    monkeypatch.setattr(
        "anemoi.training.real_inference_live._current_fields", lambda *a, **k: None,
    )
    store = CheckpointStore(
        S3Config(endpoint_url="https://example.r2.cloudflarestorage.com", bucket="t",
                 access_key_id="k", secret_access_key="s"),
        client=s3,
    )
    real_state._REAL_STATE = real_state.RealState(
        hurdat2_path=str(hurdat2), registry_root=str(tmp_path / "registry"),
        checkpoint_store=store, cache_dir=str(tmp_path / "gdas"),
    )
    from anemoi.api.main import app

    yield TestClient(app)
    real_state._REAL_STATE = None


def test_a_past_cycle_starts_from_its_own_fix_and_says_so(client):
    r = client.post("/v1/storms/AL012026/cycles", json={"cycle": "20260901_06Z"}, headers=SCHED)
    assert r.status_code == 201
    body = r.json()
    p = body["provenance"]
    # The 06Z fix, not the storm's latest (18Z, 21.6N) relabelled as 06Z.
    assert (p["fix"]["lat"], p["fix"]["lon"]) == (20.5, -61.0)
    assert p["fix_source"] == "final_best_track"
    assert p["fusion"] == "synthetic" and p["model_versions"] == {}
    assert p["gridded_source"] is None
    assert (p["basin"], p["trained_basin"]) == ("AL", True)
    assert len(p["config_sha256"]) == 64
    flags = body["payload"]["flags"]
    assert "input:final_best_track" in flags
    assert "deterministic_fallback:synthetic" in flags
    assert body["products"]["degraded"] is True
    # Issued when it actually ran, so a cycle six weeks late is not on time.
    issued = datetime.fromisoformat(body["payload"]["issued_at"])
    assert abs(issued - datetime.now(UTC)) < timedelta(minutes=5)
    assert body["on_time"] is False


def test_every_run_leaves_an_input_record(client, s3):
    assert client.post(
        "/v1/storms/AL012026/cycles", json={"cycle": "20260901_12Z"}, headers=SCHED,
    ).status_code == 201
    (key,) = [k for k in s3.objects if k.startswith("archive/cycles/2026/AL012026/20260901_12Z/")]
    assert key.endswith("/manifest.json")
    manifest = json.loads(s3.objects[key])
    assert manifest["result"]["provenance"]["fix_source"] == "final_best_track"
    assert manifest["result"]["run"]["source"] == "scheduled"
    assert [f["valid_time"][11:13] for f in manifest["fix_window"]] == ["00", "06", "12"]
    assert manifest["fields"] is None  # no gridded fields were available


def test_the_gridded_fields_a_cycle_read_are_kept(client, s3, monkeypatch):
    import numpy as np

    from anemoi.data.features import GriddedFields
    from anemoi.data.sources import Flavor

    grid = np.full((5, 5), 1.0)
    fields = GriddedFields(
        valid_time=T0 + timedelta(hours=18), flavor=Flavor.GDAS_FINETUNE,
        u200=grid, v200=grid, u850=grid, v850=grid, z500=grid * 5750, rh700=grid * 60,
        t700=grid * 280, mslp=grid * 1010, sst=grid * 28, ohc=grid * 60,
    )
    monkeypatch.setattr(
        "anemoi.training.real_inference_live._current_fields", lambda *a, **k: fields,
    )
    assert client.post(
        "/v1/storms/AL012026/cycles", json={"cycle": "20260901_18Z"}, headers=SCHED,
    ).status_code == 201
    prefix = "archive/cycles/2026/AL012026/20260901_18Z/"
    keys = sorted(k for k in s3.objects if k.startswith(prefix))
    assert [k.rsplit("/", 1)[1] for k in keys] == ["fields.npz", "manifest.json"]
    assert json.loads(s3.objects[keys[1]])["fields"] == "fields.npz"


def test_late_vitals_on_a_live_storm_read_as_estimated(client, monkeypatch):
    now_start = floor_synoptic(datetime.now(UTC))
    live = Track(storm_id="EP972026", fixes=tuple(
        Fix(storm_id="EP972026", valid_time=now_start - timedelta(hours=h), lat=15.0,
            lon=-100.0 - h / 6, max_wind_kt=50.0, min_pressure_mb=995.0,
            quality=TrackQuality.WORKING)
        for h in (12, 6)
    ))
    monkeypatch.setattr("anemoi.data.live_atcf.fetch_live_tracks", lambda: [live])
    r = client.post(
        "/v1/storms/EP972026/cycles", json={"cycle": cycle_label(now_start)}, headers=SCHED,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["payload"]["vitals"] == "estimated"
    assert body["provenance"]["fix_source"] == "extrapolated"
    assert body["provenance"]["fix"]["lon"] == pytest.approx(-100.0)  # -102, -101, then -100
    assert "basin_untrained:EP" in body["payload"]["flags"]
    assert body["provenance"]["trained_basin"] is False
