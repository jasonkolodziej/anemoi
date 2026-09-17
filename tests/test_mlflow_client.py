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
