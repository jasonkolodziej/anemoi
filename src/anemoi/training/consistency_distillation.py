"""Consistency distillation for Anemoi-Spread (GitHub #15).

Distils `models.consistency.build_consistency_model` from an already-trained
`models.diffusion` teacher (discrete-time consistency distillation, Song et
al. 2023 Algorithm 2, arXiv:2303.01469), then measures the real one-step vs
multistep compute/quality tradeoff against the teacher's own full-budget
ancestral sample -- the concrete question #15 exists to answer: does a
distilled student give Anemoi-Spread a graded response to the 13-minute
diffusion-stage budget (`inference.scheduler.DEFAULT_BUDGETS`), as a
supplement to the existing binary load-shedding path (#8), before the
diffusion budget actually binds in production.

## Distillation objective

For each real training pair ``(z, y)`` (the same masked joint-latent
conditioning and trajectory targets `training.real_run_diffusion
.train_diffusion_stage` trains the teacher against): pick an adjacent step
pair ``(n, n+1)``, forward-diffuse the real trajectory ``y`` to ``x_{n+1}``,
take one **deterministic** teacher step (DDIM, not the teacher's own
stochastic ancestral step -- a consistency trajectory must be well-defined,
so the target construction cannot itself be noisy) to get ``x_n``, and train
the student so ``f_student(x_{n+1}, n+1) ≈ f_target(x_n, n)`` where
``f_target`` is an EMA copy of the student (standard consistency-training
stabiliser -- without it the target moves as fast as the student being
trained against it and the objective can fail to converge).

Distance is measured with the pseudo-Huber norm (``sqrt(diff^2 + c^2) - c``),
applied elementwise and mask-averaged the same way every other masked loss
in this codebase is (`real_run_diffusion.train_diffusion_stage`'s
``masked_noise_loss``) -- a deliberate simplification of the paper's
whole-vector norm, consistent with this codebase's existing masked-loss
convention rather than a claim of exact paper fidelity.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..metrics.ensemble_calibration import LeadCalibration, calibrate
from ..metrics.track import ForecastPoint, VerificationPair, to_metric_dict, verify
from .real_latents import JointLatentSamples
from .real_run import displacement_to_latlon


def _pseudo_huber(diff, c: float):
    return (diff**2 + c**2).sqrt() - c


def distill_consistency_model(
    teacher: object,
    train_samples: JointLatentSamples,
    val_samples: JointLatentSamples,
    *,
    z_mean: np.ndarray,
    z_std: np.ndarray,
    y_mean: np.ndarray,
    y_std: np.ndarray,
    arch_params: dict,
    student_hidden_dim: int | None = None,
    student_n_layers: int | None = None,
    epochs: int = 300,
    learning_rate: float = 1e-4,
    ema_decay: float = 0.999,
    huber_c: float = 0.1,
    n_val_samples_per_epoch: int = 256,
    patience: int = 30,
    seed: int = 20260806,
    device=None,
) -> tuple[object, float, float, int]:
    """Distil a `models.consistency.TrajectoryConsistencyModel` from
    ``teacher``. Returns ``(student, train_loss, val_loss, epochs_run)``.

    ``z_mean``/``z_std``/``y_mean``/``y_std`` must be the teacher's own
    standardisation stats (`real_inference.load_standardization_stats`) --
    refit stats would put the student in a different space than the
    teacher's noise predictions, making the distillation target meaningless.
    ``arch_params`` must likewise be the teacher's own (`latent_dim`,
    `n_timesteps`, `lead_hours`, `extra_conditioning_dim`) -- the schedule
    and conditioning shape the DDIM teacher step depends on;
    ``student_hidden_dim``/``student_n_layers`` may still differ, a real
    point in the compute/quality tradeoff (a smaller student is cheaper per
    step on top of already needing fewer steps).

    Mirrors `real_run_diffusion.train_diffusion_stage`'s shape: one
    full-batch gradient step per epoch (this codebase's real latent
    datasets are a few hundred to ~1500 samples, not large-batch-training
    scale), real early stopping via `patience`, returns the real
    best-val-loss snapshot -- here the EMA target network's snapshot, since
    that (not the raw student) is the network multistep/one-step sampling
    actually uses.
    """
    from ..models.base import require_torch
    from ..models.consistency import build_consistency_model
    from .device import get_device

    if len(train_samples) == 0 or len(val_samples) == 0:
        raise ValueError("empty train or val latent set")
    if epochs < 1:
        raise ValueError("epochs must be >= 1")
    if patience < 1:
        raise ValueError("patience must be >= 1")

    torch = require_torch()
    device = device or get_device()
    generator = torch.Generator(device=device).manual_seed(seed)

    n_timesteps = arch_params["n_timesteps"]
    student_kwargs = dict(arch_params)
    if student_hidden_dim is not None:
        student_kwargs["hidden_dim"] = student_hidden_dim
    if student_n_layers is not None:
        student_kwargs["n_layers"] = student_n_layers

    student, _spec = build_consistency_model(**student_kwargs)
    target, _spec = build_consistency_model(**student_kwargs)
    target.load_state_dict(student.state_dict())
    for p in target.parameters():
        p.requires_grad_(False)
    student.to(device)
    target.to(device)
    # Every real caller loads `teacher` CPU-resident (`real_inference
    # .load_trained_model`'s `map_location="cpu"`, no `.to(device)`) and
    # keeps using that same reference for CPU-only inference afterwards
    # (`evaluate_step_budget_tradeoff`, mirroring `spread_backtest`'s own
    # convention) -- moving it here for training speed must not leak back
    # to the caller as a side effect, so both device and train/eval mode
    # are restored in `finally` below, even if training itself raises
    # (OOM, a NaN loss, a keyboard interrupt).
    teacher_original_device = next(teacher.parameters()).device
    teacher_original_training = teacher.training

    def prep(samples: JointLatentSamples):
        z = torch.as_tensor((samples.z - z_mean) / z_std, dtype=torch.float32, device=device)
        y = torch.as_tensor((samples.y - y_mean) / y_std, dtype=torch.float32, device=device)
        m = torch.as_tensor(samples.mask, dtype=torch.float32, device=device).unsqueeze(-1)
        return z, y, m

    zt, yt, mt = prep(train_samples)
    zv, yv, mv = prep(val_samples)

    opt = torch.optim.Adam(student.parameters(), lr=learning_rate)

    def step_loss(predict_net, target_net, z, y, m, n: int) -> object:
        idx = torch.randperm(z.shape[0], generator=generator, device=device)[
            : min(n, z.shape[0])
        ]
        z, y, m = z[idx], y[idx], m[idx]
        bsz = z.shape[0]
        n_idx = torch.randint(0, n_timesteps - 1, (bsz,), device=device, generator=generator)
        t_next = n_idx + 1
        noise = torch.randn(y.shape, device=device, generator=generator)
        alpha_bars = teacher.alpha_bars
        ab_next = alpha_bars[t_next].view(-1, 1, 1)
        x_next = torch.sqrt(ab_next) * y + torch.sqrt(1.0 - ab_next) * noise
        with torch.no_grad():
            eps_hat = teacher(x_next, t_next, z)
            x0_hat = ((x_next - torch.sqrt(1.0 - ab_next) * eps_hat) / torch.sqrt(ab_next))
            x0_hat = x0_hat.clamp(-6.0, 6.0)
            ab_n = alpha_bars[n_idx].view(-1, 1, 1)
            x_n = torch.sqrt(ab_n) * x0_hat + torch.sqrt(1.0 - ab_n) * eps_hat
            target_val = target_net.consistency_fn(x_n, n_idx, z)
        pred = predict_net.consistency_fn(x_next, t_next, z)
        loss_elem = _pseudo_huber(pred - target_val, huber_c)
        return (loss_elem * m).sum() / m.sum().clamp(min=1.0)

    try:
        teacher.to(device)
        teacher.eval()

        best_val_loss = float("inf")
        best_state: dict | None = None
        epochs_run = 0
        since_improve = 0
        n_train = train_samples.z.shape[0]
        for epoch in range(epochs):
            student.train()
            opt.zero_grad()
            loss = step_loss(student, target, zt, yt, mt, n_train)
            loss.backward()
            opt.step()
            with torch.no_grad():
                for p_t, p_s in zip(target.parameters(), student.parameters(), strict=True):
                    p_t.mul_(ema_decay).add_(p_s, alpha=1.0 - ema_decay)
            epochs_run = epoch + 1

            student.eval()
            target.eval()
            with torch.no_grad():
                val_loss_val = float(
                    step_loss(target, target, zv, yv, mv, n_val_samples_per_epoch).item()
                )
            if val_loss_val < best_val_loss:
                best_val_loss = val_loss_val
                best_state = {k: v.detach().clone() for k, v in target.state_dict().items()}
                since_improve = 0
            else:
                since_improve += 1
                if since_improve >= patience:
                    break

        target.load_state_dict(best_state)
        target.eval()
        with torch.no_grad():
            train_loss = float(
                step_loss(target, target, zt, yt, mt, n_train).item()
            )
    finally:
        teacher.to(teacher_original_device)
        teacher.train(teacher_original_training)

    target.to("cpu")
    return target, train_loss, best_val_loss, epochs_run


@dataclass(frozen=True, slots=True)
class ConfigResult:
    """One sampler configuration's real measured cost and quality."""

    label: str
    nfe: int
    wall_time_s: float
    track_error_48h_nm: float | None
    overall: list[LeadCalibration]

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "nfe": self.nfe,
            "wall_time_s": self.wall_time_s,
            "track_error_48h_nm": self.track_error_48h_nm,
            "overall": [r.to_dict() for r in self.overall],
        }


@dataclass(slots=True)
class TradeoffReport:
    configs: list[ConfigResult]
    n_val_cases: int
    recommendation: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "configs": [c.to_dict() for c in self.configs],
            "n_val_cases": self.n_val_cases,
            "recommendation": self.recommendation,
            "reasons": self.reasons,
        }


#: Same long-lead track quantities #10's own decision rule watches --
#: recurvature-driven underdispersion opens up days out, not at 12-24h.
_LONG_LEADS: tuple[int, ...] = (72, 96, 120)
_TRACK_QUANTITIES: tuple[str, ...] = ("along_track_nm", "cross_track_nm")


def _sample_config(
    model, sample_kwargs: dict, val_samples: JointLatentSamples, stats: dict,
    lead_hours: tuple[int, ...], n_members: int, sample_seed: int,
) -> tuple[np.ndarray, float]:
    """Real end-to-end sample for every val case: same conversion pipeline
    `training.spread_backtest.run_spread_backtest` uses (un-standardise,
    `real_run.displacement_to_latlon`), so results are directly comparable
    to the production #10 backtest's own numbers."""
    import time

    from ..models.base import require_torch

    torch = require_torch()
    n_cases, n_leads = val_samples.mask.shape
    members_abs = np.zeros((n_cases, n_members, n_leads, 3))
    generator = torch.Generator().manual_seed(sample_seed)
    z_z = (val_samples.z - stats["z_mean"]) / stats["z_std"]
    start = time.perf_counter()
    with torch.no_grad():
        for ci in range(n_cases):
            z_t = torch.as_tensor(z_z[ci : ci + 1], dtype=torch.float32)
            samples = model.sample(
                z_t, n_members=n_members, generator=generator, **sample_kwargs
            ).cpu().numpy()
            disp = samples * stats["y_std"] + stats["y_mean"]
            base_lat, base_lon = val_samples.base_lat[ci], val_samples.base_lon[ci]
            for li in range(n_leads):
                for mi in range(n_members):
                    lat, lon = displacement_to_latlon(base_lat, base_lon, *disp[mi, li, :2])
                    members_abs[ci, mi, li] = (lat, lon, disp[mi, li, 2])
    wall_time_s = time.perf_counter() - start
    return members_abs, wall_time_s


def evaluate_step_budget_tradeoff(
    teacher: object,
    student: object,
    val_samples: JointLatentSamples,
    stats: dict,
    lead_hours: tuple[int, ...],
    *,
    teacher_n_timesteps: int,
    student_step_options: tuple[int, ...] = (1, 2, 4),
    n_members: int = 20,
    min_cases: int = 10,
    sample_seed: int = 0,
    underdispersion_tolerance: float = 0.7,
    track_error_tolerance: float = 1.15,
) -> TradeoffReport:
    """Real teacher-vs-student, step-count-vs-step-count measurement.

    ``teacher`` is sampled once at its own full ancestral-sampling budget
    (``teacher_n_timesteps`` network evaluations -- the real production
    cost today). ``student`` is sampled once per ``student_step_options``
    entry. Both go through the identical conversion pipeline
    (`training.spread_backtest`'s pattern) so calibration and point-error
    numbers are directly comparable to the production #10 backtest.

    **The decision rule** (stated up front, same discipline
    `spread_backtest.recommend_extra_conditioning` uses): a student
    step-count is a real candidate for supplementing load shedding (#8) if
    its long-lead track spread/skill ratio is at least
    ``underdispersion_tolerance`` of the teacher's own ratio at that lead
    (not "calibrated" outright -- the teacher itself may already be
    imperfectly calibrated, #166 -- but not *meaningfully worse* than the
    model it was distilled from) and its ``track_error_48h_nm`` is within
    ``track_error_tolerance`` of the teacher's. The smallest step count
    clearing both bars is the real "warranted" evidence; none clearing it
    is "not_warranted" -- load shedding remains the only real response to
    time pressure until a smaller step count does.
    """
    n_cases, n_leads = val_samples.mask.shape
    if n_cases == 0:
        raise ValueError("no validation cases")

    base = np.stack([val_samples.base_lat, val_samples.base_lon], axis=1)
    true_abs = np.zeros((n_cases, n_leads, 3))
    for ci in range(n_cases):
        base_lat, base_lon = val_samples.base_lat[ci], val_samples.base_lon[ci]
        for li in range(n_leads):
            obs_dx, obs_dy, obs_wind = val_samples.y[ci, li]
            obs_lat, obs_lon = displacement_to_latlon(base_lat, base_lon, obs_dx, obs_dy)
            true_abs[ci, li] = (obs_lat, obs_lon, obs_wind)

    def point_track_error_48h(members_abs: np.ndarray) -> float | None:
        pairs: list[VerificationPair] = []
        try:
            li48 = lead_hours.index(48)
        except ValueError:
            return None
        for ci in range(n_cases):
            if not val_samples.mask[ci, li48]:
                continue
            mean_lat = float(members_abs[ci, :, li48, 0].mean())
            mean_lon = float(members_abs[ci, :, li48, 1].mean())
            mean_wind = float(members_abs[ci, :, li48, 2].mean())
            obs_lat, obs_lon, obs_wind = true_abs[ci, li48]
            pairs.append(
                VerificationPair(
                    forecast=ForecastPoint(
                        lead_hours=48, lat=mean_lat, lon=mean_lon, max_wind_kt=mean_wind,
                    ),
                    obs_lat=obs_lat, obs_lon=obs_lon, obs_wind_kt=float(obs_wind),
                )
            )
        if not pairs:
            return None
        return to_metric_dict(verify(pairs)).get("track_error_48h_nm")

    def evaluate(label: str, model, nfe: int, sample_kwargs: dict) -> ConfigResult:
        members_abs, wall_time_s = _sample_config(
            model, sample_kwargs, val_samples, stats, lead_hours, n_members, sample_seed,
        )
        overall = calibrate(
            members_abs, true_abs, val_samples.mask, base, lead_hours, min_cases=min_cases,
        )
        return ConfigResult(
            label=label, nfe=nfe, wall_time_s=wall_time_s,
            track_error_48h_nm=point_track_error_48h(members_abs), overall=overall,
        )

    configs = [evaluate("teacher", teacher, teacher_n_timesteps, {})]
    for n_steps in student_step_options:
        configs.append(
            evaluate(f"student-{n_steps}step", student, n_steps, {"n_steps": n_steps})
        )

    def long_track_ratios(overall: list[LeadCalibration]) -> dict[tuple[int, str], float]:
        return {
            (r.lead_hours, r.quantity): r.ratio
            for r in overall
            if r.lead_hours in _LONG_LEADS and r.quantity in _TRACK_QUANTITIES
        }

    teacher_ratios = long_track_ratios(configs[0].overall)
    teacher_track_error = configs[0].track_error_48h_nm

    if not teacher_ratios:
        return TradeoffReport(
            configs=configs, n_val_cases=n_cases, recommendation="insufficient_data",
            reasons=["no long-lead track quantity met the minimum case count for the teacher"],
        )

    reasons: list[str] = []
    for config in configs[1:]:
        student_ratios = long_track_ratios(config.overall)
        shortfalls: list[str] = []
        for (lead, quantity), teacher_ratio in teacher_ratios.items():
            student_ratio = student_ratios.get((lead, quantity))
            if student_ratio is None:
                shortfalls.append(
                    f"{config.label}: {quantity} at {lead}h did not meet the minimum case "
                    f"count for the student (teacher ratio {teacher_ratio:.2f})"
                )
            elif student_ratio < underdispersion_tolerance * teacher_ratio:
                shortfalls.append(
                    f"{config.label}: {quantity} at {lead}h ratio {student_ratio:.2f} vs "
                    f"teacher {teacher_ratio:.2f} "
                    f"(below {underdispersion_tolerance:.0%} of teacher)"
                )
        if (
            teacher_track_error is not None
            and config.track_error_48h_nm is not None
            and config.track_error_48h_nm > track_error_tolerance * teacher_track_error
        ):
            shortfalls.append(
                f"{config.label}: track_error_48h_nm {config.track_error_48h_nm:.1f} vs "
                f"teacher {teacher_track_error:.1f} (over {track_error_tolerance:.0%})"
            )
        if not shortfalls:
            return TradeoffReport(
                configs=configs, n_val_cases=n_cases, recommendation="warranted",
                reasons=[
                    f"{config.label} clears both bars: {config.nfe} network evaluation(s) vs "
                    f"the teacher's {configs[0].nfe}"
                ],
            )
        reasons.extend(shortfalls)

    return TradeoffReport(
        configs=configs, n_val_cases=n_cases, recommendation="not_warranted", reasons=reasons,
    )


def format_tradeoff_report(report: TradeoffReport) -> str:
    lines = [
        f"Consistency-distillation step-budget tradeoff -- {report.n_val_cases} "
        "validation windows",
        f"{'config':<16} {'NFE':>4} {'wall_s':>8} {'track48h':>9}  long-lead track ratios",
    ]
    for c in report.configs:
        ratios = ", ".join(
            f"{r.quantity}@{r.lead_hours}h={r.ratio:.2f}"
            for r in c.overall
            if r.lead_hours in _LONG_LEADS and r.quantity in _TRACK_QUANTITIES
        )
        te = "n/a" if c.track_error_48h_nm is None else f"{c.track_error_48h_nm:.1f}"
        lines.append(f"{c.label:<16} {c.nfe:>4} {c.wall_time_s:>8.2f} {te:>9}  {ratios}")
    lines.append(f"\nrecommendation: {report.recommendation}")
    lines.extend(f"  - {reason}" for reason in report.reasons)
    return "\n".join(lines)
