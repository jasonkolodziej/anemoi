"""Real training run for Anemoi-Spread (#22, training.real_run_diffusion).

Trains against synthetic-but-correctly-shaped `JointLatentSamples` (the
same shape `real_latents.extract_joint_latents` produces, exercised for
real in tests/test_real_latents.py) -- what's worth verifying here is the
DDPM training loop itself (masked noise-prediction loss, ensemble-mean
verification, checkpoint upload), not real latent extraction again.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from anemoi.data.sources import Flavor
from anemoi.models.base import DEFAULT_LEADS

T_N_LEADS = 7


def _make_samples(n: int, z_dim: int, *, seed: int) -> JointLatentSamples:  # noqa: F821
    from anemoi.training.real_latents import JointLatentSamples

    rng = np.random.default_rng(seed)
    z = rng.normal(size=(n, z_dim)).astype(np.float32)
    y = rng.normal(scale=10.0, size=(n, T_N_LEADS, 3)).astype(np.float32)
    y[..., 2] = np.abs(y[..., 2]) + 40.0  # wind_kt must be a plausible positive value
    mask = np.ones((n, T_N_LEADS), dtype=bool)
    mask[:, -1] = rng.random(n) > 0.5  # some samples miss the longest lead, like a real short track
    base_lat = rng.uniform(10.0, 30.0, size=n)
    base_lon = rng.uniform(-80.0, -40.0, size=n)
    return JointLatentSamples(
        z=z, y=y, mask=mask, base_lat=base_lat, base_lon=base_lon,
        predictions=np.zeros((n, 5, T_N_LEADS, 3), dtype=np.float32),
        true_absolute=np.zeros((n, T_N_LEADS, 3), dtype=np.float32),
        context=np.zeros((n, 10), dtype=np.float32),
        latent_dims=(z_dim,),
    )


torch_installed = pytest.importorskip("torch", reason="needs the torch extra")


@pytest.mark.torch
def test_train_diffusion_stage_produces_val_metrics_and_artifacts():
    from anemoi.training.real_run_diffusion import train_diffusion_stage

    train_samples = _make_samples(8, z_dim=16, seed=1)
    val_samples = _make_samples(4, z_dim=16, seed=2)

    model, train_loss, val_loss, val_metrics, artifacts, epochs_run = train_diffusion_stage(
        train_samples, val_samples,
        hidden_dim=8, n_layers=1, n_timesteps=5, epochs=3, n_ensemble_eval=2, seed=3,
        patience=10, device="cpu",
    )
    assert train_loss >= 0.0
    assert val_loss >= 0.0
    assert val_metrics.split == "val"
    assert val_metrics.flavor is Flavor.GDAS_FINETUNE
    assert "track_error_12h_nm" in val_metrics.values
    assert artifacts.model is model
    assert artifacts.z_mean.shape == (16,)
    assert artifacts.y_std.shape == (T_N_LEADS, 3)
    assert 1 <= epochs_run <= 3


@pytest.mark.torch
def test_train_diffusion_stage_accepts_dropout_and_weight_decay():
    """#166 follow-up: early stopping alone left a real residual
    underdispersion gap at 72-120h -- dropout/weight_decay are the next
    real lever from the issue's own proposed-investigation list. This is
    a wiring check (both reach `build_diffusion`/the optimizer without
    erroring and still produce a valid trained model), not a calibration
    claim -- see the real ablation script/results referenced from #166
    for whether either value is actually worth promoting."""
    from anemoi.training.real_run_diffusion import train_diffusion_stage

    train_samples = _make_samples(8, z_dim=16, seed=1)
    val_samples = _make_samples(4, z_dim=16, seed=2)

    model, train_loss, val_loss, val_metrics, artifacts, epochs_run = train_diffusion_stage(
        train_samples, val_samples,
        hidden_dim=8, n_layers=1, n_timesteps=5, epochs=3, n_ensemble_eval=2, seed=3,
        patience=10, dropout=0.2, weight_decay=1e-4, device="cpu",
    )
    assert train_loss >= 0.0
    assert val_loss >= 0.0
    assert artifacts.model is model
    assert 1 <= epochs_run <= 3


@pytest.mark.torch
def test_train_diffusion_stage_rejects_empty_samples():
    from anemoi.training.real_latents import JointLatentSamples
    from anemoi.training.real_run_diffusion import train_diffusion_stage

    empty = JointLatentSamples(
        z=np.empty((0, 16)), y=np.empty((0, T_N_LEADS, 3)),
        mask=np.empty((0, T_N_LEADS), dtype=bool),
        base_lat=np.empty((0,)), base_lon=np.empty((0,)),
        predictions=np.empty((0, 5, T_N_LEADS, 3)), true_absolute=np.empty((0, T_N_LEADS, 3)),
        context=np.empty((0, 10)), latent_dims=(16,),
    )
    non_empty = _make_samples(4, z_dim=16, seed=1)
    with pytest.raises(ValueError, match="empty train or val"):
        train_diffusion_stage(empty, non_empty, n_timesteps=5, epochs=1, device="cpu")


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
def test_run_diffusion_curriculum_uploads_a_checkpoint_and_registers_stage_b():
    from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config
    from anemoi.training.real_latents import JointLatentBundle
    from anemoi.training.real_run_diffusion import run_diffusion_curriculum

    bundle = JointLatentBundle(
        train=_make_samples(8, z_dim=16, seed=1), val=_make_samples(4, z_dim=16, seed=2),
    )
    config = S3Config(
        endpoint_url="https://example.r2.cloudflarestorage.com",
        bucket="anemoi-test", access_key_id="key", secret_access_key="secret",
    )
    store = CheckpointStore(config, client=_FakeS3Client())

    run, val_metrics, model, artifacts = run_diffusion_curriculum(
        bundle, store, hidden_dim=8, n_layers=1, n_timesteps=5, epochs=2, n_ensemble_eval=2, seed=4,
    )

    assert run.complete
    assert [r.stage_name for r in run.results] == ["B"]
    assert run.results[0].flavor is Flavor.GDAS_FINETUNE
    assert run.results[0].checkpoint_uri.startswith("s3://anemoi-test/checkpoints/diffusion/")
    assert "track_error_12h_nm" in val_metrics.values
    assert model is not None
    assert artifacts.arch_params == {
        "latent_dim": 16, "hidden_dim": 8, "n_layers": 1, "n_timesteps": 5,
        "lead_hours": list(DEFAULT_LEADS),
    }


@pytest.mark.torch
def test_early_stopping_halts_before_the_epoch_cap_on_a_real_overfitting_run():
    """#166: a high-capacity model against very few real samples overfits
    fast and predictably -- confirm patience actually stops training
    before the full epoch budget, on a real (if synthetic-data) run."""
    from anemoi.training.real_run_diffusion import train_diffusion_stage

    train_samples = _make_samples(6, z_dim=8, seed=1)
    val_samples = _make_samples(6, z_dim=8, seed=2)

    *_rest, epochs_run = train_diffusion_stage(
        train_samples, val_samples,
        hidden_dim=64, n_layers=4, n_timesteps=5, epochs=500, n_ensemble_eval=2,
        seed=5, patience=5, device="cpu",
    )
    assert epochs_run < 500


@pytest.mark.torch
def test_a_longer_epoch_budget_never_returns_a_worse_val_loss():
    """The real point of early stopping: the returned checkpoint is the
    best one *seen*, not whatever the epoch cap happened to land on. A
    longer budget (same patience, same seed) explores a superset of the
    epochs a shorter budget does, so its reported val_loss -- the real
    minimum over epochs actually run -- must never be worse."""
    from anemoi.training.real_run_diffusion import train_diffusion_stage

    train_samples = _make_samples(6, z_dim=8, seed=1)
    val_samples = _make_samples(6, z_dim=8, seed=2)
    kwargs = dict(
        hidden_dim=32, n_layers=2, n_timesteps=5, n_ensemble_eval=2, seed=5,
        patience=1000, device="cpu",  # patience disabled -- isolate the "best over all
    )                                 # epochs run" behaviour from the stopping rule itself

    _m, _tl, short_val, _vm, _a, short_epochs = train_diffusion_stage(
        train_samples, val_samples, epochs=10, **kwargs,
    )
    _m, _tl, long_val, _vm, _a, long_epochs = train_diffusion_stage(
        train_samples, val_samples, epochs=40, **kwargs,
    )

    assert short_epochs == 10
    assert long_epochs == 40
    assert long_val <= short_val + 1e-6
