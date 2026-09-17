"""Cloudflare Access header plugin for the MLflow tracking client
(tracking.cloudflare_access, docker/mlflow/)."""

from __future__ import annotations

import pytest

pytest.importorskip("mlflow", reason="needs the tracking extra")


@pytest.mark.tracking
def test_in_context_false_when_neither_var_set(monkeypatch):
    from anemoi.tracking.cloudflare_access import CloudflareAccessRequestHeaderProvider

    monkeypatch.delenv("CF_ACCESS_CLIENT_ID", raising=False)
    monkeypatch.delenv("CF_ACCESS_CLIENT_SECRET", raising=False)
    assert not CloudflareAccessRequestHeaderProvider().in_context()


@pytest.mark.tracking
def test_in_context_false_when_only_client_id_set(monkeypatch):
    from anemoi.tracking.cloudflare_access import CloudflareAccessRequestHeaderProvider

    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "id")
    monkeypatch.delenv("CF_ACCESS_CLIENT_SECRET", raising=False)
    assert not CloudflareAccessRequestHeaderProvider().in_context()


@pytest.mark.tracking
def test_in_context_true_and_correct_headers_when_both_set(monkeypatch):
    from anemoi.tracking.cloudflare_access import CloudflareAccessRequestHeaderProvider

    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "my-id")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", "my-secret")
    provider = CloudflareAccessRequestHeaderProvider()

    assert provider.in_context()
    assert provider.request_headers() == {
        "CF-Access-Client-Id": "my-id",
        "CF-Access-Client-Secret": "my-secret",
    }


@pytest.mark.tracking
def test_registered_as_a_real_mlflow_plugin_via_entry_points():
    """The pyproject.toml entry point must actually resolve -- this is what
    makes MLflow discover the provider on its own, not just importable by
    hand."""
    from importlib.metadata import entry_points

    eps = entry_points(group="mlflow.request_header_provider")
    names = {ep.name: ep.value for ep in eps}
    assert names.get("cloudflare_access") == (
        "anemoi.tracking.cloudflare_access:CloudflareAccessRequestHeaderProvider"
    )


@pytest.mark.tracking
def test_headers_are_actually_applied_by_mlflows_own_resolution(monkeypatch):
    """End to end: mlflow's own request-header resolution machinery picks
    these up through its plugin registry, not just direct instantiation of
    the provider class."""
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "e2e-id")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", "e2e-secret")

    from mlflow.tracking.request_header.registry import resolve_request_headers

    headers = resolve_request_headers()
    assert headers["CF-Access-Client-Id"] == "e2e-id"
    assert headers["CF-Access-Client-Secret"] == "e2e-secret"
