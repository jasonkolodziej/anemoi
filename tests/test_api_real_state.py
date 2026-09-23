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
from pathlib import Path

import numpy as np
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
    assert "no real ERA5T-vs-operational skew samples yet" in body["reasons"][0]

    r = client.get("/v1/retraining/triggers")
    assert r.status_code == 200
    # Not asserted empty: pending_retrain_jobs() is real now (#149), and
    # nightly_latent (real, time-of-day-dependent, unrelated to this
    # fixture's own storms/registry) can legitimately fire at 02:00 UTC --
    # exactly what real production behavior should do. Real drift/desync
    # detection is exercised precisely, with controlled inputs, in the
    # dedicated pending_retrain_jobs tests below.
    assert isinstance(r.json(), list)


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


# --- real drift detection (#148) --------------------------------------------


def _get_real_state(client):
    """The live RealState singleton behind `client` -- built lazily on
    first request, so trigger one before reaching into it. Real drift
    bookkeeping is exercised directly against the instance below, since
    fully registering real torch models just to reach a real (non-
    synthetic-fallback) cycle is already covered in depth by
    test_real_inference_cycle.py; what's under test here is RealState's
    own bookkeeping/wiring, not the model math."""
    from anemoi.api import real_state

    client.get("/v1/storms")
    assert real_state._REAL_STATE is not None
    return real_state._REAL_STATE


def _make_deterministic_forecast(env_features=None, contributors=None):
    from anemoi.inference.cycle import DeterministicForecast

    return DeterministicForecast(
        target_time=datetime(2026, 9, 1, tzinfo=UTC), lead_hours=(48,),
        lats=np.array([20.0]), lons=np.array([-60.0]), winds_kt=np.array([50.0]),
        contributors=contributors or {}, env_features=env_features,
    )


class _FakeCycleOutput:
    """A minimal stand-in for CycleOutput -- `_record_drift_sample` only
    ever reads `.deterministic.env_features`/`.deterministic.contributors`,
    and `_record_skew_sample` additionally reads `.label` (see each's own
    implementation), so a full CyclePlan/ForecastProducts isn't needed to
    exercise either one honestly."""

    def __init__(self, deterministic, label="20260901_00Z"):
        self.deterministic = deterministic
        self.label = label


def test_drift_report_is_honest_zero_when_no_reference_has_been_fit(client):
    state = _get_real_state(client)
    report = state.drift_report("lstm")
    assert report.n_live == 0
    assert report.features == ()


def test_drift_report_is_honest_zero_for_a_model_that_never_contributed(client, tmp_path):
    """Even with a real reference fit and real live samples collected,
    a model that has never itself contributed to a real cycle this
    process's lifetime must not borrow another model's drift assessment."""
    from anemoi.data.features import FEATURE_NAMES
    from anemoi.data.sources import Flavor
    from anemoi.monitoring.drift import ReferenceDistribution
    from anemoi.monitoring.reference_store import save_reference

    state = _get_real_state(client)
    reference = ReferenceDistribution.fit(
        np.random.default_rng(0).normal(0.0, 1.0, size=(50, len(FEATURE_NAMES))),
        Flavor.GDAS_FINETUNE,
    )
    save_reference(reference, Path(state.registry.root) / "drift_reference.json")

    for _ in range(40):
        forecast = _make_deterministic_forecast(
            env_features=np.random.default_rng(1).normal(0.0, 1.0, len(FEATURE_NAMES)),
            contributors={"lstm": 1.0},
        )
        state._record_drift_sample(_FakeCycleOutput(forecast))

    assert state.drift_report("lstm").n_live == 40
    assert state.drift_report("cnn").n_live == 0  # cnn never contributed


def test_drift_report_detects_real_drift_once_enough_samples_are_collected(client):
    from anemoi.data.features import FEATURE_NAMES
    from anemoi.data.sources import Flavor
    from anemoi.monitoring.drift import ReferenceDistribution
    from anemoi.monitoring.reference_store import save_reference

    state = _get_real_state(client)
    reference = ReferenceDistribution.fit(
        np.random.default_rng(0).normal(0.0, 1.0, size=(50, len(FEATURE_NAMES))),
        Flavor.GDAS_FINETUNE,
    )
    save_reference(reference, Path(state.registry.root) / "drift_reference.json")

    # Too few samples yet -- honest n_live, not a fabricated drift verdict.
    for _ in range(10):
        forecast = _make_deterministic_forecast(
            env_features=np.zeros(len(FEATURE_NAMES)), contributors={"lstm": 1.0},
        )
        state._record_drift_sample(_FakeCycleOutput(forecast))
    early_report = state.drift_report("lstm")
    assert early_report.n_live == 10
    assert early_report.features == ()

    # Real shift: live samples now centred well away from the reference mean.
    for _ in range(30):
        forecast = _make_deterministic_forecast(
            env_features=np.full(len(FEATURE_NAMES), 10.0), contributors={"lstm": 1.0},
        )
        state._record_drift_sample(_FakeCycleOutput(forecast))

    report = state.drift_report("lstm")
    assert report.n_live == 40
    assert report.alert is True


def test_live_env_features_window_is_capped(client):
    state = _get_real_state(client)
    state._live_env_features_max = 5  # keep the test fast
    for i in range(8):
        forecast = _make_deterministic_forecast(
            env_features=np.full(11, float(i)), contributors={"lstm": 1.0},
        )
        state._record_drift_sample(_FakeCycleOutput(forecast))
    assert len(state._live_env_features) == 5
    # Oldest samples are dropped, not the newest.
    assert state._live_env_features[-1][0] == 7.0


def test_env_features_none_is_not_recorded_as_a_sample(client):
    state = _get_real_state(client)
    forecast = _make_deterministic_forecast(env_features=None, contributors={"lstm": 1.0})
    state._record_drift_sample(_FakeCycleOutput(forecast))
    assert state._live_env_features == []
    # The model still counts as having contributed, even without a real
    # gridded field this specific cycle.
    assert "lstm" in state._models_ever_contributed


# ---- skew (#148, the remaining half) -------------------------------------


def _make_storm_state(storm_id="AL012026"):
    from anemoi.api.real_state import RealStormState
    from anemoi.data.besttrack import Fix, Track, TrackQuality

    fixes = tuple(
        Fix(
            storm_id=storm_id, valid_time=datetime(2026, 9, 1, tzinfo=UTC), lat=20.0, lon=-60.0,
            max_wind_kt=50.0, min_pressure_mb=990.0, quality=TrackQuality.FINAL,
        )
        for _ in (0,)
    )
    return RealStormState(storm_id, Track(storm_id=storm_id, fixes=fixes, name="Test"))


def test_skew_report_is_honest_zero_with_no_samples(client):
    state = _get_real_state(client)
    report = state.skew_report()
    assert report.n == 0
    assert report.alert is False
    assert "no real ERA5T-vs-operational skew samples yet" in report.reasons[0]


def test_record_skew_sample_is_a_noop_for_the_synthetic_fallback(client):
    """No real model contributed -- nothing real to persist, the same
    signal `_record_drift_sample`'s sibling test already relies on."""
    state = _get_real_state(client)
    storm = _make_storm_state()
    forecast = _make_deterministic_forecast(contributors={})
    state._record_skew_sample(storm, storm.track.fixes[0], _FakeCycleOutput(forecast))
    assert not (Path(state.registry.root) / "skew" / "operational").exists()


def test_record_skew_sample_persists_locally_without_a_configured_checkpoint_store(client):
    """This test's env has no real S3_ARTIFACT_* credentials (see the
    `client` fixture) -- `_record_skew_sample` must still write the local
    replay-inputs file (best-effort durable push aside), the same
    local-write-always-succeeds contract `monitoring.skew_audit
    .record_operational_cycle`'s own docstring establishes."""
    state = _get_real_state(client)
    storm = _make_storm_state()
    fix = storm.track.fixes[0]
    forecast = _make_deterministic_forecast(contributors={"lstm": 1.0})
    state._record_skew_sample(storm, fix, _FakeCycleOutput(forecast))

    local_path = (
        Path(state.registry.root) / "skew" / "operational" / storm.storm_id / "20260901_00Z.json"
    )
    assert local_path.exists()


def test_skew_report_alerts_on_real_skew_once_enough_samples_are_persisted(client):
    from datetime import timedelta

    from anemoi.monitoring.skew import SkewSample
    from anemoi.monitoring.skew_audit import save_skew_samples

    state = _get_real_state(client)
    # A synoptic (00/06/12/18Z) anchor close to real wall-clock "now" --
    # `SkewSample.__post_init__` requires an exact synoptic time, and
    # `skew_report` itself windows against the real `datetime.now(UTC)`.
    anchor = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    anchor = anchor.replace(hour=(anchor.hour // 6) * 6)
    samples = [
        SkewSample(
            target_time=anchor - timedelta(hours=6 * (i + 1)), lead_hours=48,
            operational_lat=20.0, operational_lon=-60.0, operational_wind_kt=90.0,
            era5t_lat=22.0, era5t_lon=-63.0, era5t_wind_kt=60.0,  # large, real deltas
        )
        for i in range(10)
    ]
    # The canonical path -- must match monitoring.skew_audit.audit_run's
    # own samples_path exactly, or a real deployment's skew corpus silently
    # reads as empty despite audit_run having written real samples.
    save_skew_samples(samples, Path(state.registry.root) / "skew" / "skew_samples.json")
    state._skew_samples = None  # force a reload from the file just written

    report = state.skew_report()
    assert report.n == 10
    assert report.alert is True
    assert report.mean_abs_intensity_delta_kt == pytest.approx(30.0)


def test_skew_report_falls_back_to_the_legacy_flat_path(client):
    """A real local file at the pre-fix `registry_root/skew_samples.json`
    path (no "skew/" subdirectory) must still be found -- `_get_skew_samples`
    only reaches this fallback when the canonical path is empty both
    locally and durably, so this also confirms the canonical path is tried
    first and doesn't error out just because it's missing."""
    from datetime import timedelta

    from anemoi.monitoring.skew import SkewSample
    from anemoi.monitoring.skew_audit import save_skew_samples

    state = _get_real_state(client)
    anchor = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    anchor = anchor.replace(hour=(anchor.hour // 6) * 6)
    samples = [
        SkewSample(
            target_time=anchor - timedelta(hours=6 * (i + 1)), lead_hours=48,
            operational_lat=20.0, operational_lon=-60.0, operational_wind_kt=90.0,
            era5t_lat=22.0, era5t_lon=-63.0, era5t_wind_kt=60.0,
        )
        for i in range(10)
    ]
    save_skew_samples(samples, Path(state.registry.root) / "skew_samples.json")
    state._skew_samples = None

    report = state.skew_report()
    assert report.n == 10
    assert report.alert is True


# ---- pending_retrain_jobs / latent desync (§5.7, #149) --------------------


def _stage_group1_and_derived(registry, *, desync=False):
    from anemoi.data.sources import Flavor
    from anemoi.tracking.registry import GROUP1_MODELS, Stage, latent_signature

    metrics = {"track_error_48h_nm": 70.0}
    versions = {}
    for name in GROUP1_MODELS:
        v = registry.register(name, run_id=f"run-{name}", input_flavor=Flavor.GDAS_FINETUNE,
                              metrics=metrics)
        registry.transition(name, v.version, Stage.STAGING)
        versions[name] = v.version

    sig = latent_signature(versions)
    for name in ("diffusion", "fusion"):
        v = registry.register(name, run_id=f"run-{name}", input_flavor=Flavor.GDAS_FINETUNE,
                              metrics=metrics, latent_signature=sig)
        registry.transition(name, v.version, Stage.STAGING)

    if desync:
        # A real #149 scenario: lstm's champion changes (a fresh retrain,
        # or a registry-reconcile re-stage -- indistinguishable from the
        # registry's own point of view) with no pin_set/derived retrain
        # involved at all.
        new_lstm = registry.register("lstm", run_id="lstm-v2", input_flavor=Flavor.GDAS_FINETUNE,
                                     metrics=metrics)
        registry.transition("lstm", new_lstm.version, Stage.STAGING)


def test_pending_retrain_jobs_is_empty_for_a_coherent_registry(client):
    """Not asserted as an unconditionally empty list: pending_retrain_jobs()
    calls evaluate_all with real wall-clock time, so calendar/nightly
    triggers unrelated to this test's own registry state can legitimately
    fire depending on when the suite happens to run (see the sibling fix
    in test_real_state_monitoring_and_retraining_routes_do_not_500). What
    this test actually asserts: a coherent Group 1/derived champion set
    produces no LATENT_DESYNC job."""
    from anemoi.training.triggers import Reason

    state = _get_real_state(client)
    _stage_group1_and_derived(state.registry)
    jobs = state.pending_retrain_jobs()
    assert not any(j.reason is Reason.LATENT_DESYNC for j in jobs)


def test_pending_retrain_jobs_detects_a_real_latent_desync(client):
    from anemoi.training.triggers import Reason

    state = _get_real_state(client)
    _stage_group1_and_derived(state.registry, desync=True)

    jobs = state.pending_retrain_jobs()
    desynced = {j.model: j for j in jobs if j.reason is Reason.LATENT_DESYNC}
    assert set(desynced) == {"diffusion", "fusion"}
    assert all("latent_signature" in j.note for j in desynced.values())


def test_pending_retrain_jobs_route_serves_a_real_latent_desync(client):
    """End-to-end through the real HTTP route, not just the RealState
    method directly -- confirms the new Reason/Trigger enum values
    (LATENT_DESYNC) round-trip cleanly through RetrainJobOut."""
    state = _get_real_state(client)
    _stage_group1_and_derived(state.registry, desync=True)

    r = client.get("/v1/retraining/triggers")
    assert r.status_code == 200
    body = r.json()
    desynced = [j for j in body if j["reason"] == "latent_desync"]
    assert {j["model"] for j in desynced} == {"diffusion", "fusion"}
    assert all(j["trigger_tag"] == "latent_desync" for j in desynced)
