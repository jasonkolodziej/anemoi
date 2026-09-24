"""Smoke tests for anemoi.api.

Marked ``api`` so they skip automatically when the ``api`` extra (fastapi,
uvicorn) is not installed, the same pattern ``torch``-marked tests use for
the optional torch extra.
"""

from __future__ import annotations

import warnings

import pytest

pytest.importorskip("fastapi")

# Third-party lazy-import deprecation noise (anyio/starlette internals, not
# anemoi code) -- the repo's global `filterwarnings = ["error::DeprecationWarning"]`
# would otherwise turn it into a collection error on some dependency pinnings.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from fastapi.testclient import TestClient  # noqa: E402

pytestmark = [
    pytest.mark.api,
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from anemoi.api import demo_state

    demo_state._STATE = None  # force a fresh DemoState rooted in tmp_path
    from anemoi.api.main import app

    return TestClient(app)


def test_health(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_state_mode_is_demo_by_default(client, monkeypatch):
    monkeypatch.delenv("ANEMOI_API_REAL_STATE", raising=False)
    r = client.get("/v1/health")
    assert r.json()["state_mode"] == "demo"


def test_health_state_mode_is_real_when_opted_in(client, monkeypatch):
    monkeypatch.setenv("ANEMOI_API_REAL_STATE", "1")
    r = client.get("/v1/health")
    assert r.json()["state_mode"] == "real"


def test_models_are_the_six_gods(client):
    r = client.get("/v1/models")
    assert r.status_code == 200
    body = r.json()
    assert len(body["gods"]) == 6
    assert {g["slug"] for g in body["gods"]} == {
        "boreas", "notus", "eurus", "zephyrus", "kaikias", "skiron",
    }


def test_sources_marks_operational_role(client):
    r = client.get("/v1/sources")
    assert r.status_code == 200
    assert any(s["role"] == "operational" for s in r.json())


def test_schedule_matches_cli_cycle_count(client):
    r = client.get("/v1/schedule", params={"date": "2026-08-06"})
    assert r.status_code == 200
    assert len(r.json()["plans"]) == 4  # four synoptic cycles/day


def test_storms_list_and_detail(client):
    r = client.get("/v1/storms")
    assert r.status_code == 200
    storms = r.json()
    assert len(storms) > 0
    storm_id = storms[0]["storm_id"]
    # Every demo storm is synthesized as "AL{index}{season}" -- basin is a
    # direct slice of storm_id, so this should always be Atlantic/trained.
    assert storms[0]["basin"] == "AL"
    assert storms[0]["trained_basin"] is True

    r = client.get(f"/v1/storms/{storm_id}")
    assert r.status_code == 200
    assert r.json()["storm_id"] == storm_id


def test_unknown_storm_is_404(client):
    r = client.get("/v1/storms/DOES-NOT-EXIST")
    assert r.status_code == 404


def test_run_cycle_matches_dissemination_shape(client):
    r = client.get("/v1/storms")
    storm_id = r.json()[0]["storm_id"]

    r = client.post(f"/v1/storms/{storm_id}/cycles", json={"cycle": "20260806_06Z", "members": 20})
    assert r.status_code == 201
    body = r.json()
    payload = body["payload"]
    # Field-for-field the same keys as CycleOutput.payload() (Inference Cycle wiki).
    assert set(payload) == {
        "cycle", "issued_at", "advisory_deadline", "nwp_cycle_lag_hours",
        "vitals", "ensemble_size", "rapid_intensification", "ri_probability",
        "cone", "flags", "coastline_lat", "coastline_lon",
    }
    # No coastline was requested -- both must be null, not silently
    # defaulted to something that would render a fake landfall marker.
    assert payload["coastline_lat"] is None
    assert payload["coastline_lon"] is None
    assert body["products"]["intensity_pdf"]
    assert len(body["products"]["deterministic_track"]) == 7  # the seven lead times

    # Re-fetching the same cycle returns the cached result, not a re-run.
    r2 = client.get(f"/v1/storms/{storm_id}/cycles/20260806_06Z")
    assert r2.status_code == 200
    assert r2.json()["payload"]["cycle"] == "20260806_06Z"


def test_registry_has_all_seven_models(client):
    r = client.get("/v1/registry")
    assert r.status_code == 200
    assert {e["model"] for e in r.json()} == {
        "lstm", "cnn", "transformer", "gnn", "pinn", "diffusion", "fusion",
    }


def test_registry_version_round_trips_provenance_fields(client):
    r = client.get("/v1/registry")
    assert r.status_code == 200
    lstm = next(e for e in r.json() if e["model"] == "lstm")
    latest = lstm["latest"]
    assert latest is not None
    # #92 gap 1: tags/input_flavor/latent_signature/checkpoint_uri were
    # silently dropped by ModelVersionOut/model_version_out before this --
    # assert they now round-trip through the API rather than through
    # ModelRegistry directly, which would miss a schema/convert regression.
    assert latest["tags"] == {"input_flavor": "gdas_finetune", "nwp_cycle_lag": "6"}
    assert latest["input_flavor"] == "gdas_finetune"
    assert latest["latent_signature"] is None
    assert latest["checkpoint_uri"] is None

    fusion = next(e for e in r.json() if e["model"] == "fusion")
    assert fusion["latest"]["latent_signature"] is not None


def test_active_pin_is_internally_consistent(client):
    r = client.get("/v1/registry/pins/active")
    assert r.status_code == 200
    pin = r.json()
    assert pin is not None
    assert set(pin["members"]) == {
        "lstm", "cnn", "transformer", "gnn", "pinn", "diffusion", "fusion",
    }


def test_drift_all_covers_every_model(client):
    r = client.get("/v1/monitoring/drift")
    assert r.status_code == 200
    assert len(r.json()) == 7


def test_skew_report_shape(client):
    r = client.get("/v1/monitoring/skew")
    assert r.status_code == 200
    assert "mean_track_delta_nm" in r.json()


def test_calibration_report_shape(client):
    r = client.get("/v1/monitoring/calibration")
    assert r.status_code == 200
    body = r.json()
    assert len(body) > 0  # demo state's synthetic-but-plausible curve
    assert {"cone", "intensity"} <= {entry["quantity"] for entry in body}
    assert all(entry["n_cases"] > 0 for entry in body)


def test_retraining_triggers_is_a_list(client):
    r = client.get("/v1/retraining/triggers")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_api_key_gate_when_enabled(client, monkeypatch):
    monkeypatch.setenv("ANEMOI_API_KEY", "secret")
    r = client.get("/v1/storms")
    assert r.status_code == 401
    r = client.get("/v1/storms", headers={"X-Anemoi-Api-Key": "secret"})
    assert r.status_code == 200
