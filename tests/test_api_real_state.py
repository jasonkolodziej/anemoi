"""Real ingestion-backed API state (#78/#85's real remainder).

Keeps DemoState the default, unchanged path -- these tests confirm
opting into RealState (ANEMOI_API_REAL_STATE) serves real HURDAT2
storms and degrades gracefully (the same synthetic fallback DemoState
uses) when no real trained model is registered yet, without re-proving
the real model math test_real_inference_cycle.py/
test_real_inference_ensemble.py already cover in depth.
"""

from __future__ import annotations

import warnings
from datetime import UTC, datetime

import pytest

pytest.importorskip("fastapi")

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from fastapi.testclient import TestClient  # noqa: E402

pytestmark = [
    pytest.mark.api,
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
]

RADII = ", ".join(["-999"] * 12)

# Format-compliant HURDAT2 (same fixture convention as tests/test_hurdat2.py) --
# a constructed storm, not a transcription of a real archive entry.
_HURDAT2_FIXTURE = f"""\
AL012026,     REALTEST,     4,
20260901, 0000,  , TS, 20.0N,  60.0W,  40, 1005, {RADII},
20260901, 0600,  , TS, 20.5N,  61.0W,  45, 1002, {RADII},
20260901, 1200,  , TS, 21.0N,  62.0W,  50,  995, {RADII},
20260901, 1800,  , HU, 21.6N,  63.2W,  65,  985, {RADII},
"""


@pytest.fixture
def hurdat2_file(tmp_path):
    path = tmp_path / "hurdat2-real-test.txt"
    path.write_text(_HURDAT2_FIXTURE)
    return path


@pytest.fixture
def client(tmp_path, hurdat2_file, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANEMOI_API_REAL_STATE", "1")
    monkeypatch.setenv("HURDAT2_PATH", str(hurdat2_file))
    monkeypatch.setenv("REGISTRY_ROOT", str(tmp_path / "registry"))
    monkeypatch.setenv("GDAS_CACHE_DIR", str(tmp_path / "gdas_cache"))
    # No real network call from these tests by default -- RealState.
    # list_storms/get_storm re-fetch NHC's real live-storm feed on every
    # call past its TTL (see real_state._LIVE_STORMS_TTL), which would
    # otherwise make every test in this file flaky/network-dependent on
    # however many storms NHC happens to be tracking right now. Real
    # coverage of the live fetch itself lives in test_live_atcf.py
    # (network-marked) and test_real_state_merges_a_live_storm below
    # (a fake, not the real network).
    monkeypatch.setattr("anemoi.data.live_atcf.fetch_live_tracks", lambda: [])

    from anemoi.api import real_state

    real_state._REAL_STATE = None  # force a fresh RealState for this test

    from anemoi.api.main import app

    return TestClient(app)


def test_real_state_lists_the_real_hurdat2_storm(client):
    r = client.get("/v1/storms")
    assert r.status_code == 200
    storms = r.json()
    assert len(storms) == 1
    assert storms[0]["storm_id"] == "AL012026"
    assert storms[0]["peak_wind_kt"] == 65.0


def test_real_state_monitoring_and_retraining_routes_do_not_500(client):
    """A real, previously-undiscovered bug: RealState had no
    drift_report/skew_report/pending_retrain_jobs at all, despite its own
    docstring claiming full DemoState surface parity -- these routers call
    them unconditionally, so visiting them against a real deployment 500'd
    (found by actually visiting the deployed console's /monitoring page,
    not assumed). Must return real, honest "nothing tracked yet" data, not
    fabricated synthetic numbers under a real deployment."""
    r = client.get("/v1/monitoring/drift")
    assert r.status_code == 200
    reports = r.json()
    assert len(reports) == 7  # ALL_MODELS
    for report in reports:
        assert report["n_live"] == 0
        assert report["alert"] is False

    r = client.get("/v1/monitoring/skew")
    assert r.status_code == 200
    body = r.json()
    assert body["n"] == 0
    assert body["alert"] is False
    assert "not yet available" in body["reasons"][0]

    r = client.get("/v1/retraining/triggers")
    assert r.status_code == 200
    assert r.json() == []


def test_real_state_run_cycle_degrades_to_the_synthetic_fallback(client):
    """No real trained model is registered in this test's fresh, empty
    registry -- run_cycle must still succeed (never a 500), using the
    same synthetic linear-extrapolation fallback DemoState uses."""
    r = client.post(
        "/v1/storms/AL012026/cycles", json={"cycle": "20260901_18Z", "members": 4},
    )
    assert r.status_code == 201
    body = r.json()
    assert len(body["products"]["deterministic_track"]) == 7
    # No real model or checkpoint store is configured in this test's env
    # -- run_cycle's own ensemble degradation (SS10.1) must have kicked
    # in (the deterministic fallback itself has no flag of its own;
    # RealState.run_cycle's try/except degrades that one silently).
    assert any(f.startswith("spread_fallback:") for f in body["payload"]["flags"])
    # The synthetic fallback runs no real per-model forward pass, so
    # per_model_tracks must be genuinely empty here, not padded with
    # copies of the fused track -- the console's map only draws real
    # per-model lines when this is non-empty.
    assert body["products"]["per_model_tracks"] == {}
    assert body["products"]["missing_model_reasons"] == {}

    # #100: the real reason must be captured (always, cheap), even though
    # this test doesn't expose it over HTTP (ANEMOI_API_DEBUG unset).
    from anemoi.api.real_state import get_real_state

    assert get_real_state().last_deterministic_error is not None
    assert "CheckpointStoreError" in get_real_state().last_deterministic_error


def test_run_cycle_rejects_a_cycle_that_has_not_started_yet(client):
    """LatencyOracle.published_at has no wall-clock concept of 'now' by
    design (a replay harness needs to plan a cycle before it happens) --
    but RealState.run_cycle is the one real call site running against real
    wall-clock time, and without a guard a far-future cycle label came back
    `vitals: observed` using a stale position simply relabeled with the
    future timestamp (found live against EP172026). A synoptic time that
    has not begun yet must be rejected outright, not silently estimated."""
    far_future = "20990101_00Z"
    r = client.post(
        "/v1/storms/AL012026/cycles", json={"cycle": far_future, "members": 4},
    )
    assert r.status_code == 400
    assert "has not started yet" in r.json()["detail"]


def test_run_cycle_allows_the_in_progress_cycle(client):
    """A cycle whose synoptic time has already begun -- even if real vitals
    haven't landed yet -- is the existing, honest `vitals_estimated`
    degraded mode, not something this guard should touch."""
    from anemoi.time_utils import cycle_label, floor_synoptic

    now_cycle = cycle_label(floor_synoptic(datetime.now(UTC)))
    r = client.post(
        "/v1/storms/AL012026/cycles", json={"cycle": now_cycle, "members": 4},
    )
    assert r.status_code == 201


def test_storm_responses_carry_basin_and_trained_basin(client):
    r = client.get("/v1/storms/AL012026")
    assert r.status_code == 200
    body = r.json()
    assert body["basin"] == "AL"
    assert body["trained_basin"] is True

    r = client.get("/v1/storms")
    assert r.status_code == 200
    assert all("basin" in s and "trained_basin" in s for s in r.json())


def test_pacific_storm_is_flagged_as_not_a_trained_basin(client, monkeypatch):
    """EP172026 (Hurricane Polo) is real data, not fabricated -- but no
    trained model has ever seen an Eastern Pacific storm (docs/
    train_infrastructure.md curls only the Atlantic HURDAT2 archive)."""
    from anemoi.data.besttrack import Fix, Track, TrackQuality

    ep_track = Track(
        storm_id="EP172026",
        fixes=(
            Fix(
                storm_id="EP172026",
                valid_time=datetime(2026, 9, 22, 0, 0, tzinfo=UTC),
                lat=15.0,
                lon=-100.0,
                max_wind_kt=60.0,
                min_pressure_mb=990.0,
                quality=TrackQuality.WORKING,
            ),
        ),
    )
    monkeypatch.setattr("anemoi.data.live_atcf.fetch_live_tracks", lambda: [ep_track])

    r = client.get("/v1/storms/EP172026")
    assert r.status_code == 200
    body = r.json()
    assert body["basin"] == "EP"
    assert body["trained_basin"] is False


def test_debug_last_deterministic_error_route_needs_opt_in(tmp_path, hurdat2_file, monkeypatch):
    """The route must not exist at all (404, not a real endpoint returning
    empty data) unless ANEMOI_API_DEBUG is set -- real failure detail is
    not secret, but there is no reason to expose it by default. Builds a
    fresh app via create_app() directly (not the cached module-level
    `app`) -- route registration happens at create_app() time, so a
    monkeypatched env var only takes effect on a fresh instance."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANEMOI_API_REAL_STATE", "1")
    monkeypatch.delenv("ANEMOI_API_DEBUG", raising=False)
    monkeypatch.setenv("HURDAT2_PATH", str(hurdat2_file))
    monkeypatch.setenv("REGISTRY_ROOT", str(tmp_path / "registry"))
    monkeypatch.setenv("GDAS_CACHE_DIR", str(tmp_path / "gdas_cache"))

    from anemoi.api import real_state
    from anemoi.api.main import create_app

    real_state._REAL_STATE = None
    r = TestClient(create_app()).get("/debug/last-deterministic-error")
    assert r.status_code == 404


def test_debug_last_deterministic_error_route_reports_the_real_reason(
    tmp_path, hurdat2_file, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANEMOI_API_REAL_STATE", "1")
    monkeypatch.setenv("ANEMOI_API_DEBUG", "1")
    monkeypatch.setenv("HURDAT2_PATH", str(hurdat2_file))
    monkeypatch.setenv("REGISTRY_ROOT", str(tmp_path / "registry"))
    monkeypatch.setenv("GDAS_CACHE_DIR", str(tmp_path / "gdas_cache"))

    from anemoi.api import real_state
    from anemoi.api.main import create_app

    real_state._REAL_STATE = None
    debug_client = TestClient(create_app())
    r = debug_client.post(
        "/v1/storms/AL012026/cycles", json={"cycle": "20260901_18Z", "members": 4},
    )
    assert r.status_code == 201

    r = debug_client.get("/debug/last-deterministic-error")
    assert r.status_code == 200
    assert "CheckpointStoreError" in r.json()["error"]


def test_real_state_merges_a_live_storm(client, monkeypatch):
    """A currently-active storm from data.live_atcf.fetch_live_tracks
    (faked here, not the real network -- see test_live_atcf.py for that)
    must show up in /v1/storms and /v1/storms/{id} alongside the archive
    storm, with a `working` quality latest_fix (not `final`), and be
    reachable by run_cycle the same way an archive storm is."""
    from anemoi.data.besttrack import Fix, Track, TrackQuality

    live_track = Track(
        storm_id="AL992026",
        fixes=(
            Fix(
                storm_id="AL992026",
                valid_time=datetime(2026, 9, 22, 0, 0, tzinfo=UTC),
                lat=25.0,
                lon=-70.0,
                max_wind_kt=50.0,
                min_pressure_mb=995.0,
                quality=TrackQuality.WORKING,
            ),
        ),
    )
    monkeypatch.setattr("anemoi.data.live_atcf.fetch_live_tracks", lambda: [live_track])

    r = client.get("/v1/storms")
    assert r.status_code == 200
    storm_ids = {s["storm_id"] for s in r.json()}
    assert storm_ids == {"AL012026", "AL992026"}  # archive storm + live storm
    live = next(s for s in r.json() if s["storm_id"] == "AL992026")
    assert live["latest_fix"]["quality"] == "working"
    assert live["active"] is True

    r = client.get("/v1/storms/AL992026")
    assert r.status_code == 200
    assert r.json()["storm_id"] == "AL992026"

    r = client.post(
        "/v1/storms/AL992026/cycles", json={"cycle": "20260922_00Z", "members": 4},
    )
    assert r.status_code == 201


def test_run_cycle_picks_up_a_registry_change_mid_warm_lifetime(
    tmp_path, hurdat2_file, monkeypatch,
):
    """A real incident this covers: `RealState.registry` was built once
    at construction with no checkpoint_store (listing storms must not
    need S3 credentials), so a long-lived warm container instance never
    saw a training run's new registrations/promotions until its next
    cold start -- the same class of staleness `_refresh_live_storms`'s
    TTL already fixed for storms, now fixed for the registry too."""
    from anemoi.api.real_state import RealState
    from anemoi.data.sources import Flavor
    from anemoi.tracking.registry import ModelRegistry, Stage

    monkeypatch.setattr("anemoi.data.live_atcf.fetch_live_tracks", lambda: [])

    durable = tmp_path / "durable.json"

    class FakeStore:
        class config:
            bucket = "fake"

        def exists(self, key):
            return durable.exists()

        def download(self, uri, local_path):
            local_path.write_text(durable.read_text())

        def upload(self, local_path, key):
            durable.write_text(local_path.read_text())

    state = RealState(
        hurdat2_path=str(hurdat2_file),
        registry_root=str(tmp_path / "container-local"),
        checkpoint_store=FakeStore(),
    )
    assert state.registry.versions("cnn") == []

    # A separate ModelRegistry instance (simulating a training run
    # completing elsewhere) registers and stages a real cnn version,
    # pushed to the same durable store this container's registry mirrors.
    writer = ModelRegistry(tmp_path / "writer", checkpoint_store=FakeStore())
    v = writer.register(
        "cnn", run_id="external-run", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 200.0},
    )
    writer.transition("cnn", v.version, Stage.STAGING)

    # Force the TTL to look expired without waiting real minutes.
    state._registry_fetched_at = None
    state.refresh_registry_if_stale()

    versions = state.registry.versions("cnn")
    assert len(versions) == 1
    assert versions[0].run_id == "external-run"
    assert versions[0].stage == Stage.STAGING


def test_registry_route_refreshes_a_stale_registry(client, tmp_path, monkeypatch):
    """A real, found gap: `_refresh_registry`/`refresh_registry_if_stale`
    was only ever called from `run_cycle` -- every registry-reading route
    (`/v1/registry`, `/v1/registry/{model}`, `/v1/registry/pins/active`)
    read `state.registry` directly and could serve a stale in-memory copy
    for the container's entire warm lifetime, found live: a real `anemoi
    registry-reconcile` write never appeared on `/v1/registry` until an
    unrelated `run_cycle` call happened to trigger a refresh.

    Uses a real durable-mirror stand-in (a FakeStore backed by a shared
    file), the same construction `test_run_cycle_picks_up_a_registry_
    change_mid_warm_lifetime` already uses -- registry synchronisation is
    always via the real R2/S3 mirror in production, never a shared local
    directory, so this is what a real external write (a training run,
    `anemoi registry-reconcile`) actually looks like."""
    from anemoi.api.real_state import get_real_state
    from anemoi.data.sources import Flavor
    from anemoi.tracking.registry import ModelRegistry, Stage

    durable = tmp_path / "durable.json"

    class FakeStore:
        class config:
            bucket = "fake"

        def exists(self, key):
            return durable.exists()

        def download(self, uri, local_path):
            local_path.write_text(durable.read_text())

        def upload(self, local_path, key):
            durable.write_text(local_path.read_text())

    monkeypatch.setattr(
        "anemoi.tracking.checkpoint_store.S3Config",
        type("FakeS3Config", (), {"from_env": staticmethod(lambda: "fake-config")}),
    )
    monkeypatch.setattr(
        "anemoi.tracking.checkpoint_store.CheckpointStore", lambda config: FakeStore()
    )

    state = get_real_state()
    assert state.registry.versions("cnn") == []

    # A separate ModelRegistry instance mirroring to the same durable
    # store -- simulating a real external write this container's own
    # in-memory copy has no way to know about yet.
    writer = ModelRegistry(tmp_path / "writer", checkpoint_store=FakeStore())
    v = writer.register(
        "cnn", run_id="external-run", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 200.0},
    )
    writer.transition("cnn", v.version, Stage.STAGING)

    state._registry_fetched_at = None  # force the TTL to look expired

    r = client.get("/v1/registry/cnn")
    assert r.status_code == 200
    assert any(v["run_id"] == "external-run" for v in r.json()["versions"])


def test_demo_state_is_unaffected_by_default(tmp_path, monkeypatch):
    """Without ANEMOI_API_REAL_STATE set at all, the API must behave
    exactly as before -- DemoState, unchanged."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANEMOI_API_REAL_STATE", raising=False)

    from anemoi.api import demo_state

    demo_state._STATE = None

    from anemoi.api.main import app

    demo_client = TestClient(app)
    r = demo_client.get("/v1/storms")
    assert r.status_code == 200
    assert len(r.json()) == 5  # DemoState's own synthetic seed: 5 storms
