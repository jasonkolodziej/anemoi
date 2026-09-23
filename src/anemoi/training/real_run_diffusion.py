"""Real training run for Anemoi-Spread, the conditional diffusion ensemble
generator (#22, §3.5, §5.7).

Unlike the five Group 1 models, diffusion has no track/gridded input of its
own -- it denoises a trajectory conditioned on real latents extracted from
the trained Group 1 models (`training.real_latents.extract_joint_latents`).
Its curriculum is therefore a single stage rather than Stage A -> Stage B:
there is no meaningful "ERA5-only pretraining" phase for a model whose only
real input is latents that are already built from Stage-B-trained
encoders, and every derived-model registration is operational-flavor-only
anyway (`tracking.registry.ModelRegistry.register`, §4.6.1).

Training is the standard DDPM epsilon-prediction objective
(`models.diffusion.build_diffusion`'s own ``betas``/``alphas``/``alpha_bars``
buffers, cosine schedule) over the real masked multi-lead displacement
targets `training.real_latents.JointLatentSamples.y` produced from the same
real HURDAT2 tracks every other real runner trains against -- masked the
same way (`iter_stage_windows`'s zero-fill + boolean mask for leads beyond a
short track), so a masked entry contributes nothing to the loss instead of
being fabricated or dropped whole-sample.

Validation reduces the trained ensemble to a single deterministic forecast
(the per-sample ensemble mean) for `metrics.track.verify` -- a standard way
to get a point verification number out of a probabilistic model without
claiming the mean IS the model's real product (the real product is the full
ensemble; `metrics.probabilistic.spread_skill` is the check for that, not
exercised by this promotion-facing MetricSet).
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from ..data.sources import Flavor
from ..metrics.track import ForecastPoint, VerificationPair, to_metric_dict, verify
from ..models.base import DEFAULT_LEADS, require_torch
from ..tracking.checkpoint_store import CheckpointStore
from .curriculum import Curriculum, CurriculumRun, StageResult, stage_b
from .device import get_device
from .promotion import MetricSet
from .real_latents import JointLatentBundle, JointLatentSamples
from .real_run import displacement_to_latlon


def _standardize(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std < 1e-8] = 1.0
    return (x - mean) / std, mean, std


def _standardize_y(y: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n_leads = y.shape[1]
    mean = np.zeros((n_leads, 3))
    std = np.ones((n_leads, 3))
    for li in range(n_leads):
        valid = mask[:, li]
        if valid.any():
            vals = y[valid, li, :]
            mean[li] = vals.mean(axis=0)
            s = vals.std(axis=0)
            s[s < 1e-8] = 1.0
            std[li] = s
    return mean, std


@dataclass(frozen=True, slots=True)
class DiffusionArtifacts:
    model: object
    z_mean: np.ndarray
    z_std: np.ndarray
    y_mean: np.ndarray
    y_std: np.ndarray
    #: The real `build_diffusion(...)` kwargs this run used -- see
    #: `real_run.RunArtifacts.arch_params`'s docstring for why this is the
    #: only real record of what shape a checkpoint's weights are (#78).
    arch_params: dict = field(default_factory=dict)


def train_diffusion_stage(
    train_samples: JointLatentSamples,
    val_samples: JointLatentSamples,
    *,
    hidden_dim: int = 256,
    n_layers: int = 6,
    n_timesteps: int = 200,
    epochs: int = 200,
    learning_rate: float = 1e-3,
    n_ensemble_eval: int = 20,
    seed: int = 20260806,
    patience: int = 20,
    device=None,
) -> tuple[object, float, float, MetricSet, DiffusionArtifacts, int]:
    """Train the `TrajectoryDenoiser` against one `JointLatentBundle` split.

    Mirrors `real_run.train_lstm_stage`'s shape (masked loss, verification
    pairs, standardisation stats returned) as closely as a probabilistic
    model's training loop can -- the real difference is the DDPM objective
    (predict the noise added at a random timestep) in place of direct
    supervised regression.

    **Real early stopping (#166), not previously here.** Every epoch's own
    real val loss is now tracked; training stops once `patience` epochs
    pass with no real improvement, and the returned model is the real
    *best-val-loss* checkpoint, not whatever epoch `epochs` happened to
    land on. Confirmed live 2026-09-23 against the real deployed model
    (diffusion v6): with no early stopping, real val loss fell to a real
    minimum at epoch 35 of a fixed 200, then rose monotonically to 2.1x
    that minimum by epoch 199 while train loss kept falling -- a real,
    clean overfitting curve, not a training instability. The real
    consequence for the *ensemble*, not just the point-verification
    metric: real spread/skill ratio (`metrics.probabilistic.SpreadSkill`)
    across every real lead and quantity was 0.10-0.19 (severely
    underdispersed) at epoch 199, vs. 0.50-0.93 at epoch 35, on the exact
    same trained-weights history -- only the stopping point differed. See
    GitHub #166 for the full real diagnostic.
    """
    if len(train_samples) == 0 or len(val_samples) == 0:
        raise ValueError("empty train or val latent set -- has the 'latents' task run yet?")

    from ..models.diffusion import build_diffusion

    torch = require_torch()
    device = device or get_device()
    generator = torch.Generator(device=device).manual_seed(seed)

    z_train, z_mean, z_std = _standardize(train_samples.z)
    z_val = (val_samples.z - z_mean) / z_std
    y_mean, y_std = _standardize_y(train_samples.y, train_samples.mask)
    y_train_z = (train_samples.y - y_mean) / y_std
    y_val_z = (val_samples.y - y_mean) / y_std

    model, spec = build_diffusion(
        latent_dim=train_samples.z.shape[-1], hidden_dim=hidden_dim, n_layers=n_layers,
        n_timesteps=n_timesteps, lead_hours=DEFAULT_LEADS,
    )
    model.to(device)
    n_leads = len(DEFAULT_LEADS)

    zt = torch.as_tensor(z_train, dtype=torch.float32, device=device)
    yt = torch.as_tensor(y_train_z, dtype=torch.float32, device=device)
    mt = torch.as_tensor(train_samples.mask, dtype=torch.float32, device=device).unsqueeze(-1)
    n_train = zt.shape[0]

    zv = torch.as_tensor(z_val, dtype=torch.float32, device=device)
    yv = torch.as_tensor(y_val_z, dtype=torch.float32, device=device)
    mv = torch.as_tensor(val_samples.mask, dtype=torch.float32, device=device).unsqueeze(-1)
    n_val = zv.shape[0]

    opt = torch.optim.Adam(model.parameters(), lr=learning_rate)

    def masked_noise_loss(z: object, y: object, m: object, n: int) -> object:
        t = torch.randint(0, n_timesteps, (n,), device=device, generator=generator)
        noise = torch.randn(y.shape, device=device, generator=generator)
        alpha_bar = model.alpha_bars[t].view(-1, 1, 1)
        noisy = torch.sqrt(alpha_bar) * y + torch.sqrt(1.0 - alpha_bar) * noise
        predicted_noise = model(noisy, t, z)
        diff2 = (predicted_noise - noise) ** 2 * m
        return diff2.sum() / m.sum().clamp(min=1.0)

    best_val_loss = float("inf")
    best_state: dict | None = None
    epochs_run = 0
    epochs_since_improvement = 0
    for epoch in range(epochs):
        model.train()
        opt.zero_grad()
        loss = masked_noise_loss(zt, yt, mt, n_train)
        loss.backward()
        opt.step()
        epochs_run = epoch + 1

        model.eval()
        with torch.no_grad():
            val_l = float(masked_noise_loss(zv, yv, mv, n_val).item())
        if val_l < best_val_loss:
            best_val_loss = val_l
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            epochs_since_improvement = 0
        else:
            epochs_since_improvement += 1
            if epochs_since_improvement >= patience:
                break

    # best_state always exists once at least one epoch has run (the first
    # epoch's val loss is < inf by construction); `epochs >= 1` is a real
    # precondition every real caller already satisfies.
    model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        train_loss = float(masked_noise_loss(zt, yt, mt, n_train).item())
        val_loss = best_val_loss

        pred_mean_z = np.zeros((n_val, n_leads, 3), dtype=np.float32)
        for i in range(n_val):
            members = model.sample(zv[i : i + 1], n_members=n_ensemble_eval, generator=generator)
            pred_mean_z[i] = members.mean(dim=0).cpu().numpy()
    pred_mean = pred_mean_z * y_std + y_mean

    pairs: list[VerificationPair] = []
    for si in range(n_val):
        base_lat, base_lon = val_samples.base_lat[si], val_samples.base_lon[si]
        for li, lead_hours in enumerate(DEFAULT_LEADS):
            if not val_samples.mask[si, li]:
                continue
            pred_dx, pred_dy, pred_wind = pred_mean[si, li]
            pred_lat, pred_lon = displacement_to_latlon(base_lat, base_lon, pred_dx, pred_dy)
            obs_dx, obs_dy, obs_wind = val_samples.y[si, li]
            obs_lat, obs_lon = displacement_to_latlon(base_lat, base_lon, obs_dx, obs_dy)
            pairs.append(
                VerificationPair(
                    forecast=ForecastPoint(
                        lead_hours=lead_hours, lat=pred_lat, lon=pred_lon,
                        max_wind_kt=float(pred_wind),
                    ),
                    obs_lat=obs_lat, obs_lon=obs_lon, obs_wind_kt=float(obs_wind),
                )
            )

    if not pairs:
        raise ValueError("no verifiable (lead, sample) pairs in val")
    val_metrics = MetricSet(
        split="val", flavor=Flavor.GDAS_FINETUNE, values=to_metric_dict(verify(pairs)),
    )
    arch_params = {
        "latent_dim": train_samples.z.shape[-1], "hidden_dim": hidden_dim, "n_layers": n_layers,
        "n_timesteps": n_timesteps, "lead_hours": list(DEFAULT_LEADS),
    }
    artifacts = DiffusionArtifacts(
        model=model, z_mean=z_mean, z_std=z_std, y_mean=y_mean, y_std=y_std,
        arch_params=arch_params,
    )
    return model, train_loss, val_loss, val_metrics, artifacts, epochs_run


def run_diffusion_curriculum(
    joint_latents: JointLatentBundle,
    checkpoint_store: CheckpointStore,
    *,
    seed: int = 20260806,
    hidden_dim: int = 256,
    n_layers: int = 6,
    n_timesteps: int = 200,
    epochs: int = 200,
    learning_rate: float = 1e-3,
    n_ensemble_eval: int = 20,
    patience: int = 20,
    curriculum_kwargs: dict | None = None,
) -> tuple[CurriculumRun, MetricSet, object, DiffusionArtifacts]:
    """Run the real (single-stage) curriculum for Anemoi-Spread against a
    real `JointLatentBundle` (`training.real_latents.extract_joint_latents`'s
    output), uploading the trained checkpoint to durable storage.

    Returns ``(run, val_metrics, model, artifacts)`` -- ``model`` is kept
    as its own return value for backward compatibility with existing
    callers; ``artifacts`` (added #78) carries the real standardisation
    stats and `build_diffusion(...)` kwargs a real inference path needs
    that ``model``/``run``/``val_metrics`` don't. ``model`` is the real
    early-stopped (best real val loss) checkpoint (#166), not necessarily
    the one trained for the full ``epochs``.
    """
    require_torch()
    curriculum = Curriculum(model_name="diffusion", stages=(stage_b(**(curriculum_kwargs or {})),))
    run = CurriculumRun(curriculum=curriculum)
    stage = curriculum.stages[0]

    model, train_loss, val_loss, val_metrics, artifacts, epochs_run = train_diffusion_stage(
        joint_latents.train, joint_latents.val,
        hidden_dim=hidden_dim, n_layers=n_layers, n_timesteps=n_timesteps,
        epochs=epochs, learning_rate=learning_rate, n_ensemble_eval=n_ensemble_eval, seed=seed,
        patience=patience,
    )

    torch = require_torch()
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = Path(tmpdir) / f"{stage.name}.pt"
        torch.save(model.state_dict(), local_path)
        key = f"checkpoints/diffusion/{stage.name}/{datetime.now(UTC):%Y%m%dT%H%M%S}.pt"
        checkpoint_uri = checkpoint_store.upload(local_path, key)

    run.record(
        StageResult(
            stage_name=stage.name, flavor=stage.flavor, epochs_completed=epochs_run,
            final_train_loss=train_loss, final_val_loss=val_loss, checkpoint_uri=checkpoint_uri,
            completed_at=datetime.now(UTC),
        )
    )
    return run, val_metrics, model, artifacts
