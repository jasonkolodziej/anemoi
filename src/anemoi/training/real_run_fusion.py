"""Real training run for the consensus fusion layer (#22, §6.1, §5.7).

Like diffusion, fusion has no track/gridded input of its own and no
meaningful ERA5-only pretraining phase -- its curriculum is a single Stage
B against real per-window data from `training.real_latents
.extract_joint_latents`: each Group 1 model's own real Stage B forecast
(``predictions``, already converted to a shared absolute (lat, lon, wind)
space) and a real synoptic ``context`` vector, both already-standardised
inputs built by `real_latents` from real HURDAT2 tracks.

Unlike every other real runner, fusion's target (``true_absolute``) and its
own output are already in absolute coordinates -- `models.fusion
.ConsensusFusion.forward` returns a plain weighted sum of the five models'
own absolute predictions, so there is nothing to un-standardise afterward
(the same reason `real_run_pinn.train_pinn_stage` doesn't standardise its
own absolute-space loss either).
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

from ..data.sources import Flavor
from ..metrics.track import ForecastPoint, VerificationPair, to_metric_dict, verify
from ..models.base import DEFAULT_LEADS, require_torch
from ..tracking.checkpoint_store import CheckpointStore
from .curriculum import Curriculum, CurriculumRun, StageResult, stage_b
from .device import get_device
from .promotion import MetricSet
from .real_latents import JointLatentBundle, JointLatentSamples


def train_fusion_stage(
    train_samples: JointLatentSamples,
    val_samples: JointLatentSamples,
    *,
    hidden_dim: int = 64,
    weight_floor: float = 0.02,
    epochs: int = 200,
    learning_rate: float = 1e-3,
    device=None,
) -> tuple[object, float, float, MetricSet]:
    """Train `models.fusion.build_fusion`'s ``ConsensusFusion`` against one
    `JointLatentBundle` split's real per-model predictions/context/target.
    """
    if len(train_samples) == 0 or len(val_samples) == 0:
        raise ValueError("empty train or val latent set -- has the 'latents' task run yet?")

    from ..models.fusion import build_fusion

    torch = require_torch()
    device = device or get_device()
    n_models = train_samples.predictions.shape[1]
    context_dim = train_samples.context.shape[-1]

    model, spec = build_fusion(
        n_models=n_models, context_dim=context_dim, hidden_dim=hidden_dim,
        lead_hours=DEFAULT_LEADS, weight_floor=weight_floor,
    )
    model.to(device)

    def to_t(samples: JointLatentSamples):
        pred = torch.as_tensor(samples.predictions, dtype=torch.float32, device=device)
        ctx = torch.as_tensor(samples.context, dtype=torch.float32, device=device)
        true = torch.as_tensor(samples.true_absolute, dtype=torch.float32, device=device)
        mask3 = torch.as_tensor(samples.mask, dtype=torch.float32, device=device).unsqueeze(-1)
        return pred, ctx, true, mask3

    pred_t, ctx_t, true_t, mask_t = to_t(train_samples)

    def masked_mse(out, target, mask3):
        diff2 = (out - target) ** 2 * mask3
        return diff2.sum() / mask3.sum().clamp(min=1.0)

    opt = torch.optim.Adam(model.parameters(), lr=learning_rate)
    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        out = model(pred_t, ctx_t)
        loss = masked_mse(out, true_t, mask_t)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        train_loss = float(masked_mse(model(pred_t, ctx_t), true_t, mask_t).item())

        pred_v, ctx_v, true_v, mask_v = to_t(val_samples)
        out_v = model(pred_v, ctx_v)
        val_loss = float(masked_mse(out_v, true_v, mask_v).item())
        out_v_np = out_v.cpu().numpy()

    pairs: list[VerificationPair] = []
    for si in range(len(val_samples)):
        for li, lead_hours in enumerate(DEFAULT_LEADS):
            if not val_samples.mask[si, li]:
                continue
            plat, plon, pwind = out_v_np[si, li]
            tlat, tlon, twind = val_samples.true_absolute[si, li]
            pairs.append(
                VerificationPair(
                    forecast=ForecastPoint(
                        lead_hours=lead_hours, lat=float(plat), lon=float(plon),
                        max_wind_kt=float(pwind),
                    ),
                    obs_lat=float(tlat), obs_lon=float(tlon), obs_wind_kt=float(twind),
                )
            )

    if not pairs:
        raise ValueError("no verifiable (lead, sample) pairs in val")
    val_metrics = MetricSet(
        split="val", flavor=Flavor.GDAS_FINETUNE, values=to_metric_dict(verify(pairs)),
    )
    return model, train_loss, val_loss, val_metrics


def run_fusion_curriculum(
    joint_latents: JointLatentBundle,
    checkpoint_store: CheckpointStore,
    *,
    seed: int = 20260806,
    hidden_dim: int = 64,
    weight_floor: float = 0.02,
    epochs: int = 200,
    learning_rate: float = 1e-3,
    curriculum_kwargs: dict | None = None,
) -> tuple[CurriculumRun, MetricSet, object]:
    """Run the real (single-stage) curriculum for the fusion consensus
    layer against a real `JointLatentBundle`, uploading the trained
    checkpoint to durable storage. ``seed`` is accepted for the same
    per-model-runner calling convention `real_orchestrator` uses, even
    though this training loop (full-batch, no augmentation, no dropout) has
    no other randomness to seed.
    """
    require_torch()
    del seed  # no stochastic step depends on it -- see docstring
    curriculum = Curriculum(model_name="fusion", stages=(stage_b(**(curriculum_kwargs or {})),))
    run = CurriculumRun(curriculum=curriculum)
    stage = curriculum.stages[0]

    model, train_loss, val_loss, val_metrics = train_fusion_stage(
        joint_latents.train, joint_latents.val,
        hidden_dim=hidden_dim, weight_floor=weight_floor, epochs=epochs,
        learning_rate=learning_rate,
    )

    torch = require_torch()
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = Path(tmpdir) / f"{stage.name}.pt"
        torch.save(model.state_dict(), local_path)
        key = f"checkpoints/fusion/{stage.name}/{datetime.now(UTC):%Y%m%dT%H%M%S}.pt"
        checkpoint_uri = checkpoint_store.upload(local_path, key)

    run.record(
        StageResult(
            stage_name=stage.name, flavor=stage.flavor, epochs_completed=epochs,
            final_train_loss=train_loss, final_val_loss=val_loss, checkpoint_uri=checkpoint_uri,
            completed_at=datetime.now(UTC),
        )
    )
    return run, val_metrics, model
