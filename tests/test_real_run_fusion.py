"""Real training run for the consensus fusion layer (#22,
training.real_run_fusion).

Trains against synthetic-but-correctly-shaped `JointLatentSamples` (the
same shape `real_latents.extract_joint_latents` produces, exercised for
real in tests/test_real_latents.py) -- what's worth verifying here is the
fusion training loop itself (masked absolute-space loss, verification,
checkpoint upload), not real latent extraction again.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from anemoi.data.sources import Flavor
from anemoi.models.base import DEFAULT_LEADS

T_N_LEADS = 7
T_N_MODELS = 5


def _make_samples(n: int, *, seed: int):
    from anemoi.training.real_latents import JointLatentSamples

    rng = np.random.default_rng(seed)
    base_lat = rng.uniform(10.0, 30.0, size=n)
    base_lon = rng.uniform(-80.0, -40.0, size=n)
    true_lat = base_lat[:, None] + rng.normal(scale=1.0, size=(n, T_N_LEADS))
    true_lon = base_lon[:, None] + rng.normal(scale=1.0, size=(n, T_N_LEADS))
    true_wind = np.abs(rng.normal(scale=10.0, size=(n, T_N_LEADS))) + 50.0
    true_absolute = np.stack([true_lat, true_lon, true_wind], axis=-1).astype(np.float32)

    # Each of the 5 "models" predicts the true value plus its own real,
    # bounded noise -- close enough that a learned consensus should improve
    # on any one model's raw error, without hardcoding which model "wins".
    noisy = [
        true_absolute + rng.normal(scale=2.0, size=true_absolute.shape) for _ in range(T_N_MODELS)
    ]
    predictions = np.stack(noisy, axis=1).astype(np.float32)

    mask = np.ones((n, T_N_LEADS), dtype=bool)
    mask[:, -1] = rng.random(n) > 0.5
    context = rng.normal(size=(n, 10)).astype(np.float32)
    y = np.zeros((n, T_N_LEADS, 3), dtype=np.float32)  # unused by fusion training

    return JointLatentSamples(
        z=np.zeros((n, 1), dtype=np.float32), y=y, mask=mask, base_lat=base_lat, base_lon=base_lon,
        predictions=predictions, true_absolute=true_absolute, context=context, latent_dims=(1,),
    )


torch_installed = pytest.importorskip("torch", reason="needs the torch extra")


@pytest.mark.torch
def test_train_fusion_stage_reduces_loss_and_produces_val_metrics():
    from anemoi.training.real_run_fusion import train_fusion_stage

    train_samples = _make_samples(24, seed=1)
    val_samples = _make_samples(8, seed=2)

    model, train_loss, val_loss, val_metrics = train_fusion_stage(
        train_samples, val_samples, hidden_dim=8, epochs=100, learning_rate=1e-2, device="cpu",
    )
    assert train_loss >= 0.0
    assert val_loss >= 0.0
    assert val_metrics.split == "val"
    assert val_metrics.flavor is Flavor.GDAS_FINETUNE
    assert "track_error_12h_nm" in val_metrics.values

    # A learned consensus over 5 noisy-but-unbiased predictors should beat
    # any single one of them on the training set it was fit to.
    single_model_err = train_samples.predictions[:, 0] - train_samples.true_absolute
    single_model_mse = float(np.mean(single_model_err**2))
    assert train_loss < single_model_mse


@pytest.mark.torch
def test_train_fusion_stage_rejects_empty_samples():
    from anemoi.training.real_latents import JointLatentSamples
    from anemoi.training.real_run_fusion import train_fusion_stage

    empty = JointLatentSamples(
        z=np.empty((0, 1)), y=np.empty((0, T_N_LEADS, 3)),
        mask=np.empty((0, T_N_LEADS), dtype=bool),
        base_lat=np.empty((0,)), base_lon=np.empty((0,)),
        predictions=np.empty((0, T_N_MODELS, T_N_LEADS, 3)),
        true_absolute=np.empty((0, T_N_LEADS, 3)),
        context=np.empty((0, 10)), latent_dims=(1,),
    )
    non_empty = _make_samples(4, seed=1)
    with pytest.raises(ValueError, match="empty train or val"):
        train_fusion_stage(empty, non_empty, epochs=1, device="cpu")


@pytest.mark.torch
def test_train_fusion_stage_rejects_a_val_set_built_with_a_different_model_count():
    """The fusion model's ``n_models`` is fixed from the TRAIN set's
    predictions width at construction (`build_fusion(n_models=...)`); a val
    set built from a differently-sized Group 1 set (e.g. a stale
    `JointLatentBundle`) must surface `models.fusion.ConsensusFusion
    .forward`'s own real mismatch error, not silently broadcast or
    truncate."""
    from anemoi.training.real_latents import JointLatentSamples
    from anemoi.training.real_run_fusion import train_fusion_stage

    train_samples = _make_samples(8, seed=1)
    val_samples = _make_samples(4, seed=2)
    val_wrong = JointLatentSamples(
        z=val_samples.z, y=val_samples.y, mask=val_samples.mask,
        base_lat=val_samples.base_lat, base_lon=val_samples.base_lon,
        predictions=val_samples.predictions[:, :3], true_absolute=val_samples.true_absolute,
        context=val_samples.context, latent_dims=val_samples.latent_dims,
    )
    with pytest.raises(ValueError, match="expected 5 model predictions"):
        train_fusion_stage(train_samples, val_wrong, epochs=1, device="cpu")


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


@pytest.mark.torch
def test_run_fusion_curriculum_uploads_a_checkpoint_and_registers_stage_b():
    from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config
    from anemoi.training.real_latents import JointLatentBundle
    from anemoi.training.real_run_fusion import run_fusion_curriculum

    bundle = JointLatentBundle(train=_make_samples(16, seed=1), val=_make_samples(6, seed=2))
    config = S3Config(
        endpoint_url="https://example.r2.cloudflarestorage.com",
        bucket="anemoi-test", access_key_id="key", secret_access_key="secret",
    )
    store = CheckpointStore(config, client=_FakeS3Client())

    run, val_metrics, model, artifacts = run_fusion_curriculum(
        bundle, store, hidden_dim=8, epochs=10, seed=1,
    )

    assert run.complete
    assert [r.stage_name for r in run.results] == ["B"]
    assert run.results[0].flavor is Flavor.GDAS_FINETUNE
    assert run.results[0].checkpoint_uri.startswith("s3://anemoi-test/checkpoints/fusion/")
    assert "track_error_12h_nm" in val_metrics.values
    assert model is not None
    assert artifacts.arch_params == {
        "n_models": T_N_MODELS, "context_dim": 10, "hidden_dim": 8, "weight_floor": 0.02,
        "lead_hours": list(DEFAULT_LEADS),
    }
