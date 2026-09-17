"""Optional real MLflow client construction (tracking.mlflow_client) --
ModelRegistry's local-JSON path is unaffected either way (Scope v2.1
§10.1); this only covers what feeds its optional mlflow_client argument.
"""

from __future__ import annotations

import builtins

import pytest


def test_returns_none_without_mlflow_installed(monkeypatch):
    """Simulates the ModuleNotFoundError branch directly (via a faked
    __import__) so this passes regardless of whether the tracking extra
    happens to be installed in the test environment -- the one test here
    that doesn't need pytest.importorskip("mlflow")."""
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "mlflow.tracking":
            raise ModuleNotFoundError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    from anemoi.tracking.mlflow_client import mlflow_client_from_env

    assert mlflow_client_from_env() is None


pytest.importorskip("mlflow", reason="needs the tracking extra")


@pytest.mark.tracking
def test_returns_none_when_tracking_uri_is_unset(monkeypatch):
    from anemoi.tracking.mlflow_client import mlflow_client_from_env

    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    assert mlflow_client_from_env() is None


@pytest.mark.tracking
def test_builds_a_real_client_when_tracking_uri_is_set(monkeypatch):
    from anemoi.tracking.mlflow_client import mlflow_client_from_env

    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    client = mlflow_client_from_env()

    assert client is not None
    assert client.tracking_uri == "http://localhost:5000"


# --- live connection (real network, opt-in via MLFLOW_TRACKING_URI) --------
#
# Not run by default -- see conftest.py's mlflow_live handling. Point
# MLFLOW_TRACKING_URI (and, if the server is behind Cloudflare Access,
# CF_ACCESS_CLIENT_ID/CF_ACCESS_CLIENT_SECRET) at a real server
# (docker/mlflow/, or a deployed one) and run with:
#   MLFLOW_TRACKING_URI=... uv run pytest -m mlflow_live


@pytest.mark.tracking
@pytest.mark.mlflow_live
def test_mlflow_client_from_env_can_actually_reach_the_configured_server():
    """End-to-end real network check: env vars are set, mlflow_client_from_env()
    builds a real client from them, and a real (read-only, side-effect-free)
    API call round-trips against whatever MLFLOW_TRACKING_URI points at --
    including, if configured, the Cloudflare Access service-token headers
    tracking.cloudflare_access adds to the request automatically."""
    import os

    from anemoi.tracking.mlflow_client import mlflow_client_from_env

    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    assert tracking_uri, "MLFLOW_TRACKING_URI must be set to run this test (see conftest.py)"

    client = mlflow_client_from_env()
    assert client is not None, (
        "mlflow must be installed to run this test (uv sync --extra tracking)"
    )

    has_access_token = bool(os.environ.get("CF_ACCESS_CLIENT_ID")) and bool(
        os.environ.get("CF_ACCESS_CLIENT_SECRET")
    )
    try:
        experiments = client.search_experiments(max_results=1)
    except Exception as exc:  # noqa: BLE001 - surface a clear, actionable message
        hint = (
            "a Cloudflare Access service token is configured -- check it's valid "
            "and scoped to this Access application"
            if has_access_token
            else "no Cloudflare Access service token is configured -- if the server "
            "sits behind Access, set CF_ACCESS_CLIENT_ID/CF_ACCESS_CLIENT_SECRET"
        )
        pytest.fail(
            f"could not reach MLflow at {tracking_uri!r}: {type(exc).__name__}: {exc} ({hint})"
        )
    assert experiments is not None
