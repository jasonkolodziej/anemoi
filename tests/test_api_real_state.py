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

    # #100: the real reason must be captured (always, cheap), even though
    # this test doesn't expose it over HTTP (ANEMOI_API_DEBUG unset).
    from anemoi.api.real_state import get_real_state

    assert get_real_state().last_deterministic_error is not None
    assert "CheckpointStoreError" in get_real_state().last_deterministic_error


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
