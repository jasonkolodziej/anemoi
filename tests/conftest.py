"""Shared fixtures and torch skip handling."""

import os
from datetime import UTC, datetime

import pytest

from anemoi.data.availability import LatencyOracle
from anemoi.models.base import torch_available

TARGET = datetime(2026, 8, 6, 6, tzinfo=UTC)


def pytest_collection_modifyitems(config, items):
    """Skip torch-marked tests when the optional extra is not installed, and
    network-marked tests unless explicitly opted into (they hit real public
    data sources -- not something a default `pytest` run should depend on)."""
    skip_torch = pytest.mark.skip(reason="torch extra not installed (uv sync --extra torch)")
    run_network = os.environ.get("ANEMOI_RUN_NETWORK_TESTS") == "1"
    skip_network = pytest.mark.skip(
        reason="network test skipped by default; set ANEMOI_RUN_NETWORK_TESTS=1 to run"
    )
    for item in items:
        if "torch" in item.keywords and not torch_available():
            item.add_marker(skip_torch)
        if "network" in item.keywords and not run_network:
            item.add_marker(skip_network)


@pytest.fixture
def target_time():
    return TARGET


@pytest.fixture
def oracle():
    """Nominal feed timing: everything arrives at its typical latency."""
    return LatencyOracle()


@pytest.fixture
def worst_case_oracle():
    return LatencyOracle(use_max_latency=True)
