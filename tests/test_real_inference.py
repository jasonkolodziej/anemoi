"""Real inference: reconstruct a trained model from its registered
checkpoint (#78)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from anemoi.data.sources import Flavor
from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config
from anemoi.tracking.registry import ModelVersion, Stage
from anemoi.training.real_inference import (
    MODEL_NAMES,
    InferenceLoadError,
    load_run_artifacts,
    load_standardization_stats,
    load_trained_model,
    load_trained_pinn_candidate,
)

torch_installed = pytest.importorskip("torch", reason="needs the torch extra")


class _FakeS3Client:
    """Same duck-typed surface tests/test_checkpoint_store.py uses."""

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


def _store() -> CheckpointStore:
    config = S3Config(
        endpoint_url="https://example.r2.cloudflarestorage.com",
        bucket="anemoi-test", access_key_id="key", secret_access_key="secret",
    )
    return CheckpointStore(config, client=_FakeS3Client())


def _make_version(name: str, arch_params: dict, checkpoint_uri: str) -> ModelVersion:
    return ModelVersion(
        name=name, version=1, stage=Stage.NONE, run_id="test-run",
        input_flavor=Flavor.GDAS_FINETUNE, metrics={},
        tags={"arch_params": json.dumps(arch_params)},
        checkpoint_uri=checkpoint_uri,
    )


#: Real, minimal kwargs for each of the 7 architectures -- small enough to
#: build/train instantly, but real (not mocked) build_<model> calls.
_ARCH_PARAMS: dict[str, dict] = {
    "lstm": {"input_dim": 5, "hidden_dim": 8, "lead_hours": [12, 24]},
    "cnn": {"in_channels": 3, "latent_dim": 8, "lead_hours": [12, 24]},
    "transformer": {
        "n_variables": 3, "grid_size": [8, 8], "d_model": 8, "dropout": 0.0,
        "lead_hours": [12, 24],
    },
    "gnn": {"node_features": 5, "edge_features": 3, "hidden_dim": 8, "lead_hours": [12, 24]},
    "pinn": {"input_dim": 5, "hidden_dim": 8, "lead_hours": [12, 24]},
    "diffusion": {
        "latent_dim": 8, "hidden_dim": 8, "n_layers": 1, "n_timesteps": 5, "lead_hours": [12, 24],
    },
    "fusion": {
        "n_models": 3, "context_dim": 4, "hidden_dim": 8, "weight_floor": 0.02,
        "lead_hours": [12, 24],
    },
}


def _real_builder(name: str):
    from anemoi.training.real_inference import _builder

    return _builder(name)


@pytest.mark.torch
@pytest.mark.parametrize("name", MODEL_NAMES)
def test_load_trained_model_reconstructs_real_weights_exactly(name, tmp_path):
    """The strongest real check: the loaded model's weights match the
    original trained model's bit for bit, not just "doesn't crash" --
    proves both the architecture reconstruction (arch_params) and the
    checkpoint round-trip (checkpoint_uri) are correct together."""
    import torch

    arch_params = _ARCH_PARAMS[name]
    build_kwargs = dict(arch_params)
    build_kwargs["lead_hours"] = tuple(build_kwargs["lead_hours"])
    if "grid_size" in build_kwargs:
        build_kwargs["grid_size"] = tuple(build_kwargs["grid_size"])

    original_model, original_spec = _real_builder(name)(**build_kwargs)

    store = _store()
    local_path = tmp_path / f"{name}-checkpoint.pt"
    torch.save(original_model.state_dict(), local_path)
    checkpoint_uri = store.upload(local_path, f"checkpoints/{name}/B/test.pt")

    version = _make_version(name, arch_params, checkpoint_uri)
    loaded_model, loaded_spec = load_trained_model(name, version, store)

    assert loaded_spec == original_spec
    original_state = original_model.state_dict()
    loaded_state = loaded_model.state_dict()
    assert original_state.keys() == loaded_state.keys()
    for key in original_state:
        assert torch.equal(original_state[key], loaded_state[key]), key
    assert not loaded_model.training  # eval() was called


def test_load_trained_model_raises_on_unknown_architecture():
    version = _make_version("not-a-real-model", {}, "s3://fake/x.pt")
    with pytest.raises(InferenceLoadError, match="no real architecture"):
        load_trained_model("not-a-real-model", version, _store())


def test_load_trained_model_raises_without_an_arch_params_tag():
    """A version registered before #78 (or via a path that doesn't set
    the tag) must fail loudly, not silently guess at defaults that might
    not match what that specific version was actually trained with."""
    version = ModelVersion(
        name="lstm", version=1, stage=Stage.NONE, run_id="old-run",
        input_flavor=Flavor.GDAS_FINETUNE, metrics={}, tags={},
        checkpoint_uri="s3://fake/lstm.pt",
    )
    with pytest.raises(InferenceLoadError, match="arch_params"):
        load_trained_model("lstm", version, _store())


def test_load_trained_model_raises_without_a_checkpoint_uri():
    version = _make_version("lstm", _ARCH_PARAMS["lstm"], checkpoint_uri=None)
    with pytest.raises(InferenceLoadError, match="checkpoint_uri"):
        load_trained_model("lstm", version, _store())


@pytest.mark.torch
def test_load_trained_pinn_candidate_reconstructs_real_weights_exactly(tmp_path):
    """PINN's second real model (#80) -- same round-trip strength as the
    main loader, via the candidate_arch_params/candidate_checkpoint_uri
    tags instead of arch_params/checkpoint_uri."""
    import torch

    from anemoi.models.lstm import build_lstm

    candidate_params = {"input_dim": 4, "hidden_dim": 6, "lead_hours": [12, 24]}
    original_model, original_spec = build_lstm(
        input_dim=4, hidden_dim=6, lead_hours=(12, 24),
    )

    store = _store()
    local_path = tmp_path / "pinn-candidate-checkpoint.pt"
    torch.save(original_model.state_dict(), local_path)
    checkpoint_uri = store.upload(local_path, "checkpoints/pinn/B/candidate-test.pt")

    version = ModelVersion(
        name="pinn", version=1, stage=Stage.NONE, run_id="test-run",
        input_flavor=Flavor.GDAS_FINETUNE, metrics={},
        tags={
            "candidate_arch_params": json.dumps(candidate_params),
            "candidate_checkpoint_uri": checkpoint_uri,
        },
        checkpoint_uri="s3://fake/pinn-main.pt",
    )
    loaded_model, loaded_spec = load_trained_pinn_candidate(version, store)

    assert loaded_spec == original_spec
    original_state = original_model.state_dict()
    loaded_state = loaded_model.state_dict()
    for key in original_state:
        assert torch.equal(original_state[key], loaded_state[key]), key
    assert not loaded_model.training


def test_load_trained_pinn_candidate_raises_without_the_candidate_tag():
    version = _make_version("pinn", _ARCH_PARAMS["pinn"], "s3://fake/pinn.pt")
    with pytest.raises(InferenceLoadError, match="candidate_arch_params"):
        load_trained_pinn_candidate(version, _store())


def test_load_standardization_stats_round_trips_real_arrays():
    import numpy as np

    version = _make_version("lstm", _ARCH_PARAMS["lstm"], "s3://fake/lstm.pt")
    version.tags["x_mean"] = json.dumps([1.0, 2.0, 3.0])
    version.tags["x_std"] = json.dumps([0.5, 0.5, 0.5])

    stats = load_standardization_stats(version)

    assert set(stats) == {"x_mean", "x_std"}
    assert np.array_equal(stats["x_mean"], np.array([1.0, 2.0, 3.0]))
    assert np.array_equal(stats["x_std"], np.array([0.5, 0.5, 0.5]))


def test_load_standardization_stats_is_empty_without_any_tags():
    version = _make_version("fusion", _ARCH_PARAMS["fusion"], "s3://fake/fusion.pt")
    assert load_standardization_stats(version) == {}


# --- load_run_artifacts: rebuild RunArtifacts from the registry (#149) -------


def _register_like_training(name, artifacts, store, tmp_path) -> ModelVersion:
    """Serialize ``artifacts`` with the exact tag functions
    `real_orchestrator.RealOrchestratorRunner` uses at registration time --
    so the round trip below tests what a real registered version carries,
    not a hand-built approximation of it."""
    import torch

    from anemoi.tracking.experiment_tracking import (
        arch_params_tag,
        candidate_tags,
        standardization_tags,
    )

    local_path = tmp_path / f"{name}-roundtrip.pt"
    torch.save(artifacts.model.state_dict(), local_path)
    checkpoint_uri = store.upload(local_path, f"checkpoints/{name}/B/roundtrip.pt")
    tags = {"arch_params": arch_params_tag(artifacts)}
    tags.update(candidate_tags(artifacts))
    tags.update(standardization_tags(artifacts))
    return ModelVersion(
        name=name, version=3, stage=Stage.STAGING, run_id="roundtrip",
        input_flavor=Flavor.GDAS_FINETUNE, metrics={}, tags=tags,
        checkpoint_uri=checkpoint_uri,
    )


@pytest.mark.torch
def test_load_run_artifacts_round_trips_a_real_training_runs_artifacts(tmp_path):
    """CNN's stats have the real training-time keepdims shape (1, C, 1, 1)
    -- `real_latents` multiplies them straight against batched arrays, so
    shape must survive the registry round trip, not just values."""
    import numpy as np
    import torch

    from anemoi.training.real_run import RunArtifacts

    arch_params = _ARCH_PARAMS["cnn"]
    build_kwargs = dict(arch_params, lead_hours=tuple(arch_params["lead_hours"]))
    model, _spec = _real_builder("cnn")(**build_kwargs)
    rng = np.random.default_rng(0)
    original = RunArtifacts(
        model=model, arch_params=arch_params,
        x_mean=rng.normal(size=(1, 3, 1, 1)), x_std=rng.uniform(0.5, 2, size=(1, 3, 1, 1)),
        y_mean=rng.normal(size=(2, 3)), y_std=rng.uniform(0.5, 2, size=(2, 3)),
    )
    store = _store()
    version = _register_like_training("cnn", original, store, tmp_path)

    loaded = load_run_artifacts("cnn", version, store)

    for field_name in ("x_mean", "x_std", "y_mean", "y_std"):
        expected, got = getattr(original, field_name), getattr(loaded, field_name)
        assert got.shape == expected.shape, field_name
        assert np.allclose(got, expected), field_name
    for key, value in original.model.state_dict().items():
        assert torch.equal(value, loaded.model.state_dict()[key]), key
    assert loaded.candidate_model is None


@pytest.mark.torch
def test_load_run_artifacts_rebuilds_pinns_candidate_and_env_stats(tmp_path):
    import numpy as np
    import torch

    from anemoi.models.lstm import build_lstm
    from anemoi.training.real_run import RunArtifacts

    store = _store()
    candidate_params = {"input_dim": 4, "hidden_dim": 6, "lead_hours": [12, 24]}
    candidate, _ = build_lstm(input_dim=4, hidden_dim=6, lead_hours=(12, 24))
    cand_path = tmp_path / "cand.pt"
    torch.save(candidate.state_dict(), cand_path)
    cand_uri = store.upload(cand_path, "checkpoints/pinn/B/cand.pt")

    arch_params = _ARCH_PARAMS["pinn"]
    model, _ = _real_builder("pinn")(**dict(arch_params, lead_hours=(12, 24)))
    original = RunArtifacts(
        model=model, arch_params=arch_params, candidate_model=candidate,
        env_mean=np.arange(5.0), env_std=np.ones(5),
        candidate_arch_params=candidate_params, candidate_checkpoint_uri=cand_uri,
    )
    version = _register_like_training("pinn", original, store, tmp_path)

    loaded = load_run_artifacts("pinn", version, store)

    assert np.array_equal(loaded.env_mean, original.env_mean)
    assert loaded.candidate_checkpoint_uri == cand_uri
    for key, value in candidate.state_dict().items():
        assert torch.equal(value, loaded.candidate_model.state_dict()[key]), key


@pytest.mark.torch
def test_load_run_artifacts_refuses_a_version_without_standardisation_stats(tmp_path):
    import torch

    arch_params = _ARCH_PARAMS["lstm"]
    model, _ = _real_builder("lstm")(**dict(arch_params, lead_hours=(12, 24)))
    store = _store()
    path = tmp_path / "lstm.pt"
    torch.save(model.state_dict(), path)
    version = _make_version("lstm", arch_params, store.upload(path, "checkpoints/lstm/B/x.pt"))

    with pytest.raises(InferenceLoadError, match="standardisation stats"):
        load_run_artifacts("lstm", version, store)
