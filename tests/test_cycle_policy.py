"""Who may run which cycle, and when (#212, `anemoi.api.cycle_policy`).

Before this, any signed-in user's POST replaced the shared, official cycle
(with their overrides, or a label years outside the storm), a manual run
before t+1:30 made the scheduled run skip the storm, and two runs of one
label could execute at once.
"""

from __future__ import annotations

import threading
import warnings
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from fastapi.testclient import TestClient

from anemoi.api.cycle_policy import (
    MANUAL,
    SCHEDULED,
    CycleConflict,
    InFlight,
    RunRequest,
    check_run,
    stored_source,
)
from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.inference.cycle import CycleError, RunInfo
from anemoi.time_utils import cycle_label, floor_synoptic

pytestmark = [
    pytest.mark.api,
    pytest.mark.filterwarnings("ignore::UserWarning"),
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
]

T0 = datetime(2026, 9, 1, 0, tzinfo=UTC)
SCHED = {"X-Anemoi-Run-Source": "scheduled"}
USER = {"X-Anemoi-User-Id": "user-1"}
OPERATOR = {"X-Anemoi-User-Id": "op-1"}


class _Stored:
    def __init__(self, source: str | None) -> None:
        self.run = RunInfo(source=source) if source else None


def _check(target, cycles=None, request=None, *, active=False, now=None):
    check_run(
        storm_id="AL012026", target=target, first_fix=T0, latest_fix=T0 + timedelta(hours=18),
        active=active, cycles=cycles or {}, request=request or RunRequest(),
        now=now or T0 + timedelta(days=30),
    )


# ---- the rules, directly --------------------------------------------------


def test_a_label_outside_the_storm_is_refused():
    with pytest.raises(CycleError, match="outside AL012026's track"):
        _check(T0 - timedelta(hours=6))
    with pytest.raises(CycleError, match="outside"):
        _check(T0 + timedelta(hours=36))
    _check(T0 + timedelta(hours=30))  # within 12 h of the latest fix


def test_a_manual_run_never_replaces_an_existing_cycle():
    label = cycle_label(T0)
    for existing in (SCHEDULED, MANUAL, None):
        with pytest.raises(CycleConflict) as exc:
            _check(T0, {label: _Stored(existing)}, RunRequest(MANUAL, "user-1"))
        assert exc.value.code == "exists"


def test_a_scheduled_run_replaces_a_manual_one_but_not_another_scheduled_one():
    label = cycle_label(T0)
    _check(T0, {label: _Stored(MANUAL)}, RunRequest(SCHEDULED))
    with pytest.raises(CycleConflict) as exc:
        _check(T0, {label: _Stored(SCHEDULED)}, RunRequest(SCHEDULED))
    assert exc.value.code == "exists"
    # A result stored before #212 says nothing: it counts as official.
    with pytest.raises(CycleConflict):
        _check(T0, {label: _Stored(None)}, RunRequest(SCHEDULED))


def test_an_operator_may_replace_an_existing_cycle(monkeypatch):
    monkeypatch.setenv("ANEMOI_OPERATOR_USER_IDS", "op-1, op-2")
    label = cycle_label(T0)
    _check(T0, {label: _Stored(SCHEDULED)}, RunRequest(MANUAL, "op-2", replace=True))
    with pytest.raises(CycleConflict):  # only when asked to
        _check(T0, {label: _Stored(SCHEDULED)}, RunRequest(MANUAL, "op-2"))
    with pytest.raises(CycleConflict):  # and only an operator
        _check(T0, {label: _Stored(SCHEDULED)}, RunRequest(MANUAL, "user-1", replace=True))


def test_a_manual_run_waits_for_the_scheduled_one_on_an_active_storm():
    target = T0 + timedelta(hours=18)
    early = target + timedelta(minutes=45)
    with pytest.raises(CycleConflict) as exc:
        _check(target, request=RunRequest(MANUAL, "user-1"), active=True, now=early)
    assert exc.value.code == "not_scheduled_yet"
    assert "19:30Z" in str(exc.value)
    # The scheduled run itself, a later manual run (the cron failed), and an
    # inactive storm (no cron runs it) are all allowed.
    _check(target, request=RunRequest(SCHEDULED), active=True, now=early)
    later = target + timedelta(hours=2)
    _check(target, request=RunRequest(MANUAL, "user-1"), active=True, now=later)
    _check(target, request=RunRequest(MANUAL, "user-1"), active=False, now=early)


def test_an_unreadable_stored_label_is_not_overwritten_blind():
    class Unreadable(dict):
        def __getitem__(self, key):
            raise KeyError(key)

    cycles = Unreadable({cycle_label(T0): None})
    with pytest.raises(CycleConflict):
        _check(T0, cycles, RunRequest(SCHEDULED))


def test_stored_source_reads_both_shapes():
    from anemoi.api import schemas

    assert stored_source(_Stored(MANUAL)) == MANUAL
    assert stored_source(_Stored(None)) == SCHEDULED
    assert stored_source(schemas.RunInfoOut(source="manual")) == SCHEDULED  # not a result
    assert stored_source(type("R", (), {"run": schemas.RunInfoOut(source="manual")})()) == MANUAL


def test_in_flight_allows_one_run_per_label():
    guard = InFlight()
    with guard.hold("AL012026", "20260901_00Z"):
        with pytest.raises(CycleConflict) as exc, guard.hold("AL012026", "20260901_00Z"):
            pass
        assert exc.value.code == "in_progress"
        with guard.hold("AL012026", "20260901_06Z"):  # another label is fine
            pass
    with guard.hold("AL012026", "20260901_00Z"):  # released
        pass


def test_run_request_refuses_an_unknown_source():
    with pytest.raises(ValueError):
        RunRequest(source="cron")


# ---- through the real API ---------------------------------------------------

RADII = ", ".join(["-999"] * 12)
_HURDAT2 = f"""\
AL012026,     POLICYTEST,     4,
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
    monkeypatch.setenv("ANEMOI_OPERATOR_USER_IDS", "op-1")
    monkeypatch.setattr("anemoi.data.live_atcf.fetch_live_tracks", lambda: [])
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


def _post(client, label, headers=None, **body):
    return client.post(
        "/v1/storms/AL012026/cycles", json={"cycle": label, "members": 4, **body},
        headers=headers or {},
    )


def test_the_run_is_recorded_on_the_served_and_stored_cycle(client, s3):
    r = _post(client, "20260901_06Z", USER, lat=21.0)
    assert r.status_code == 201
    assert r.json()["run"] == {"source": "manual", "overrides": ["lat", "members"]}
    stored = s3.objects["api/cycles/AL012026/20260901_06Z.json"].decode()
    assert '"source":"manual"' in stored
    assert client.get("/v1/storms/AL012026/cycles/20260901_06Z").json()["run"]["source"] == "manual"


def test_a_scheduled_run_with_the_api_defaults_records_no_overrides(client):
    r = client.post(
        "/v1/storms/AL012026/cycles", json={"cycle": "20260901_06Z"}, headers=SCHED,
    )
    assert r.status_code == 201
    assert r.json()["run"] == {"source": "scheduled", "overrides": []}
    assert r.json()["payload"]["ensemble_size"] > 0


def test_a_second_run_of_a_label_is_a_409_with_a_code(client):
    assert _post(client, "20260901_06Z", SCHED).status_code == 201
    again = _post(client, "20260901_06Z", SCHED)
    assert again.status_code == 409
    assert again.json()["code"] == "exists"
    user = _post(client, "20260901_06Z", USER)
    assert user.status_code == 409
    assert "already has a 20260901_06Z cycle" in user.json()["detail"]


def test_the_scheduled_run_replaces_a_manual_one(client):
    assert _post(client, "20260901_12Z", USER, wind_kt=120.0).status_code == 201
    official = _post(client, "20260901_12Z", SCHED)
    assert official.status_code == 201
    assert official.json()["run"]["source"] == "scheduled"
    stored = client.get("/v1/storms/AL012026/cycles/20260901_12Z").json()
    assert stored["run"]["source"] == "scheduled"


def test_an_operator_can_replace_a_cycle(client):
    assert _post(client, "20260901_12Z", SCHED).status_code == 201
    assert _post(client, "20260901_12Z", USER, replace=True).status_code == 409
    assert _post(client, "20260901_12Z", OPERATOR, replace=True).status_code == 201


def test_a_label_outside_the_track_is_a_400(client):
    r = _post(client, "20200101_00Z", USER)
    assert r.status_code == 400
    assert "outside AL012026's track" in r.json()["detail"]


def test_a_manual_run_before_the_scheduled_one_is_refused(client, monkeypatch):
    now_start = floor_synoptic(datetime.now(UTC))
    live = Track(storm_id="AL972026", fixes=(
        Fix(storm_id="AL972026", valid_time=now_start - timedelta(hours=6), lat=25.0, lon=-70.0,
            max_wind_kt=50.0, min_pressure_mb=995.0, quality=TrackQuality.WORKING),
    ))
    monkeypatch.setattr("anemoi.data.live_atcf.fetch_live_tracks", lambda: [live])
    # Freeze "now" just after the synoptic start, whatever the wall clock says.
    from anemoi.api import cycle_policy

    real_check = cycle_policy.check_run

    def check_at_start(**kwargs):
        return real_check(**{**kwargs, "now": now_start + timedelta(minutes=10)})

    monkeypatch.setattr("anemoi.api.real_state.check_run", check_at_start)
    r = client.post(
        "/v1/storms/AL972026/cycles", json={"cycle": cycle_label(now_start), "members": 4},
        headers=USER,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "not_scheduled_yet"


def test_a_concurrent_run_of_the_same_label_is_refused(client, monkeypatch):
    from anemoi.api import real_state

    state = real_state._REAL_STATE
    started, release = threading.Event(), threading.Event()
    real_run = state._run_cycle

    def slow_run(*args, **kwargs):
        started.set()
        release.wait(5)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(state, "_run_cycle", slow_run)
    first: dict = {}
    t = threading.Thread(target=lambda: first.update(r=_post(client, "20260901_18Z", SCHED)))
    t.start()
    assert started.wait(5)
    second = _post(client, "20260901_18Z", SCHED)
    release.set()
    t.join(10)
    assert second.status_code == 409
    assert second.json()["code"] == "in_progress"
    assert first["r"].status_code == 201


def test_the_image_refuses_a_manual_run_with_no_caller(client, monkeypatch):
    monkeypatch.setenv("ANEMOI_REQUIRE_CALLER", "1")
    r = _post(client, "20260901_06Z")
    assert r.status_code == 401
    assert _post(client, "20260901_06Z", SCHED).status_code == 201
    assert _post(client, "20260901_12Z", USER).status_code == 201


def test_the_api_image_sets_require_caller():
    dockerfile = (Path(__file__).parents[1] / "docker" / "multistage.Dockerfile").read_text()
    api_stage = dockerfile[dockerfile.index("AS api"):]
    assert "ENV ANEMOI_REQUIRE_CALLER=1" in api_stage


def test_the_websocket_streams_real_cycles(client):
    """It read the demo state unconditionally, so every real storm was
    "unknown storm" (#212)."""
    from anemoi.api import stream

    assert _post(client, "20260901_06Z", SCHED).status_code == 201
    stream.MAX_STREAM_SECONDS = 0.5
    try:
        with client.websocket_connect("/v1/storms/AL012026/stream") as ws:
            message = ws.receive_json()
    finally:
        stream.MAX_STREAM_SECONDS = 15 * 60
    assert message["type"] == "cycle"
    assert message["data"]["payload"]["cycle"] == "20260901_06Z"


def test_the_demo_state_still_runs_anything():
    from anemoi.api import real_state  # noqa: F401 - ensure no real singleton leaks
    from anemoi.api.main import app

    demo = TestClient(app)
    storm_id = demo.get("/v1/storms").json()[0]["storm_id"]
    for _ in range(2):
        r = demo.post(f"/v1/storms/{storm_id}/cycles", json={"cycle": "20260806_06Z", "members": 4})
        assert r.status_code == 201
        assert r.json()["run"]["source"] == "manual"
