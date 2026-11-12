"""`models.architecture` and `GET /v1/registry/{model}/architecture`: the
console's system view, read from the models themselves."""

from __future__ import annotations

import json
import warnings

import pytest

pytest.importorskip("torch")

from anemoi.models.architecture import DESCRIBABLE_MODELS, describe, resolved_params  # noqa: E402


@pytest.mark.parametrize("name", DESCRIBABLE_MODELS)
def test_every_model_runs_its_example_input_and_reports_its_layers(name):
    arch = describe(name)

    assert arch.defaults
    assert arch.total_params > 0
    assert arch.total_params == arch.layers[0].total_params  # the root holds them all
    # The forecast every model ends in: one (lat, lon, wind) per lead.
    out = arch.outputs[0].shape
    assert out[-2:] == [len(arch.lead_hours), 3] or out[-1] == arch.output_dim
    # Every module that ran recorded a shape; container modules may not run.
    assert sum(layer.output_shape is not None for layer in arch.layers) >= 3
    assert sum(layer.own_params for layer in arch.layers) == arch.total_params


def test_a_versions_arch_params_change_what_is_described():
    small = describe("lstm", {"hidden_dim": 16, "num_layers": 1})
    default = describe("lstm")

    assert not small.defaults
    assert small.arch_params["hidden_dim"] == 16
    assert small.total_params < default.total_params
    rnn = next(layer for layer in small.layers if layer.path == "rnn")
    assert rnn.output_shape[-1] == 16


def test_resolved_params_fill_in_the_builders_defaults():
    params = resolved_params("cnn", {"base_width": 8})
    assert params["base_width"] == 8
    assert params["latent_dim"] == 256  # build_cnn's default, not recorded
    assert params["lead_hours"] == [12, 24, 36, 48, 72, 96, 120]


def test_the_gnn_is_fed_the_real_lattice():
    arch = describe("gnn")
    assert not arch.batched
    nodes, edge_index, edges = (t.shape for t in arch.inputs)
    assert nodes == [121, 12]  # 41x41 crop, every 4th cell: 11x11
    assert edge_index == [2, 440]  # 4-connected, both directions
    assert edges == [440, 3]


# --- the endpoint ----------------------------------------------------------------

pytest.importorskip("fastapi")
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from anemoi.api import demo_state

    demo_state._STATE = None
    from anemoi.api.main import app

    return TestClient(app)


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_a_version_without_arch_params_is_described_from_defaults(client):
    r = client.get("/v1/registry/cnn/architecture")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model"] == "cnn"
    assert body["version"] == 1  # the demo pin's
    assert body["defaults"] is True
    assert body["inputs"][0]["shape"] == [1, 5, 41, 41]
    assert body["layers"][0]["path"] == ""


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_a_registered_versions_arch_params_are_used(client):
    from anemoi.api.demo_state import get_state
    from anemoi.data.sources import Flavor

    state = get_state()
    v = state.registry.register(
        "lstm", run_id="r-small", input_flavor=Flavor.GDAS_FINETUNE, metrics={},
        tags={"arch_params": json.dumps({"hidden_dim": 16, "num_layers": 1})},
    )

    body = client.get(f"/v1/registry/lstm/architecture?version={v.version}").json()
    assert body["version"] == v.version
    assert body["defaults"] is False
    assert body["arch_params"]["hidden_dim"] == 16


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_unknown_models_and_versions_are_404(client):
    assert client.get("/v1/registry/resnet/architecture").status_code == 404
    assert client.get("/v1/registry/cnn/architecture?version=999").status_code == 404
