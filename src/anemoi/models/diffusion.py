"""Anemoi-Spread: conditional diffusion ensemble generator.

Scope v2.1 §3.5. Denoises a track/intensity trajectory conditioned on Anemoi-Core
latents to produce 20-50 structurally diverse ensemble members.

A caveat worth keeping in the code rather than only in the review: conditioning
purely on the deterministic latent anchors the ensemble to the deterministic
guess and tends toward underdispersion, exactly when it matters most (bimodal
recurvature). ``extra_conditioning_dim`` exists so raw environmental fields or
GEFS/EPS perturbations can be concatenated to the conditioning vector, and
:func:`anemoi.metrics.probabilistic.spread_skill` is the check on whether that
was enough.
"""

from __future__ import annotations

from .base import DEFAULT_LEADS, ModelSpec, require_torch


def build_diffusion(
    latent_dim: int = 256,
    extra_conditioning_dim: int = 0,
    hidden_dim: int = 256,
    n_layers: int = 6,
    n_timesteps: int = 200,
    dropout: float = 0.0,
    lead_hours: tuple[int, ...] = DEFAULT_LEADS,
):
    """Conditional denoising model over trajectories.

    Returns ``(module, spec)``. Uses a cosine noise schedule, which degrades
    less gracelessly at low step counts than the linear schedule -- and step
    count is a hard constraint here, since the whole ensemble must be generated
    inside the 13-minute §6.2.2 budget.

    ``dropout`` (#166, default 0.0 -- unchanged behavior unless a caller opts
    in): applied inside each residual block, after its hidden activation.
    Real early stopping (`training.real_run_diffusion.train_diffusion_stage`)
    already recovered most of a real overfitting-driven ensemble-calibration
    collapse (spread/skill 0.10-0.19 -> 0.44-0.94, diffusion v7), but the
    residual gap was concentrated at 72-120h leads (ratio 0.4-0.7, still
    below the 0.8 "calibrated" threshold) -- the architecture itself has no
    regularization at all (no dropout anywhere, and the optimizer used no
    weight decay), which was next on #166's own proposed-investigation list.
    Real Adam weight decay is the training-loop side of the same lever --
    see `train_diffusion_stage`'s own ``weight_decay`` parameter.

    If that budget binds in practice, the better answer is not the scheduler's
    load-shedding path -- which drops ensemble members, trading tail resolution
    for punctuality with no middle setting. Consistency models (Song et al. 2023,
    arXiv:2303.01469) support one-step generation by design while still allowing
    multistep sampling to trade compute for quality, giving a graded response to
    time pressure instead of a binary drop. They can be **distilled from an
    already-trained diffusion model**, so this is not an architectural commitment
    to make up front: train here, distil for the operational path if needed.
    SWIFT (Stock et al. 2025, arXiv:2509.25631) is prior art for weather.
    """
    torch = require_torch()
    nn = torch.nn

    n_leads = len(lead_hours)
    traj_dim = n_leads * 3
    cond_dim = latent_dim + extra_conditioning_dim

    spec = ModelSpec(
        name="diffusion", input_dim=cond_dim, latent_dim=hidden_dim, lead_hours=lead_hours
    )

    betas = _cosine_schedule(torch, n_timesteps)
    alphas = 1.0 - betas
    alpha_bars = torch.cumprod(alphas, dim=0)

    class TrajectoryDenoiser(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.register_buffer("betas", betas)
            self.register_buffer("alphas", alphas)
            self.register_buffer("alpha_bars", alpha_bars)
            self.time_embed = nn.Sequential(
                nn.Linear(1, hidden_dim), nn.SiLU(), nn.Linear(hidden_dim, hidden_dim)
            )
            self.cond_embed = nn.Sequential(
                nn.Linear(cond_dim, hidden_dim), nn.SiLU(), nn.Linear(hidden_dim, hidden_dim)
            )
            self.input_proj = nn.Linear(traj_dim, hidden_dim)
            self.blocks = nn.ModuleList(
                [
                    nn.Sequential(
                        nn.LayerNorm(hidden_dim),
                        nn.Linear(hidden_dim, hidden_dim),
                        nn.SiLU(),
                        nn.Dropout(dropout),
                        nn.Linear(hidden_dim, hidden_dim),
                    )
                    for _ in range(n_layers)
                ]
            )
            self.out = nn.Linear(hidden_dim, traj_dim)

        def forward(self, noisy_traj, t, conditioning):
            h = self.input_proj(noisy_traj.flatten(1))
            h = h + self.time_embed(t.float().unsqueeze(-1) / n_timesteps)
            h = h + self.cond_embed(conditioning)
            for block in self.blocks:
                h = h + block(h)
            return self.out(h).view(-1, n_leads, 3)

        @torch.no_grad()
        def sample(self, conditioning, n_members: int = 20, generator=None, clip_x0: float = 6.0):
            """Ancestral sampling of ``n_members`` trajectories.

            ``conditioning`` is (1, cond_dim) or (n_members, cond_dim); a single
            row is broadcast so every member shares the Anemoi-Core guess and differs
            only through the noise path.

            ``clip_x0`` (default 6.0, real standard-deviation units since the
            target this samples is standardized) bounds each step's predicted
            *x0* before it feeds the next step's posterior mean -- the
            standard "clip_denoised" mitigation (Nichol & Dhariwal 2021,
            arXiv:2102.09672, `improved-diffusion`'s `p_mean_variance`).
            Real bug found training against real ERA5/GDAS latents
            (2026-09-18): the previous version computed the posterior mean
            directly from the predicted noise (mathematically the same as an
            *unclipped* x0), so a denoiser badly out-of-distribution on a
            validation-time latent (this model overfits fast on the small,
            1448-sample real latent dataset -- real `val_loss` came back
            ~8x `train_loss`) could drift x0 to an arbitrary magnitude at
            an early, high-noise step, and every later step's posterior
            mean is a moving average that includes that unclipped x0, so
            the drift persists and compounds across the remaining ~200
            steps rather than self-correcting. Confirmed via a real MLflow
            query: `track_error_48h_nm` around 4800 (every other model,
            same run, landed 250-310) and `intensity_error_36h_kt` around
            1000 (every other model landed 12-17) -- both symptomatic of
            an unbounded z-score, not a units/scale bug (the
            un-standardization step downstream is unchanged and correct).
            6.0 is a deliberately loose bound -- real standardized
            meteorological targets essentially never exceed +/-6 std devs,
            so this stops runaway divergence without constraining any
            plausible real trajectory, including genuine tail events.
            """
            if conditioning.shape[0] == 1:
                conditioning = conditioning.expand(n_members, -1)
            elif conditioning.shape[0] != n_members:
                raise ValueError("conditioning batch must be 1 or n_members")

            x = torch.randn(n_members, n_leads, 3, generator=generator,
                            device=conditioning.device)
            for step in reversed(range(n_timesteps)):
                t = torch.full((n_members,), step, device=conditioning.device, dtype=torch.long)
                predicted_noise = self(x, t, conditioning)
                alpha = self.alphas[step]
                alpha_bar = self.alpha_bars[step]
                alpha_bar_prev = self.alpha_bars[step - 1] if step > 0 else x.new_tensor(1.0)

                x0_pred = (x - torch.sqrt(1.0 - alpha_bar) * predicted_noise)
                x0_pred = (x0_pred / torch.sqrt(alpha_bar)).clamp(-clip_x0, clip_x0)

                beta = self.betas[step]
                coef_x0 = beta * torch.sqrt(alpha_bar_prev) / (1.0 - alpha_bar)
                coef_xt = (1.0 - alpha_bar_prev) * torch.sqrt(alpha) / (1.0 - alpha_bar)
                mean = coef_x0 * x0_pred + coef_xt * x
                if step > 0:
                    noise = torch.randn(x.shape, generator=generator, device=x.device)
                    x = mean + torch.sqrt(beta) * noise
                else:
                    x = mean
            return x

    return TrajectoryDenoiser(), spec


def _cosine_schedule(torch, n_timesteps: int, s: float = 0.008):
    steps = torch.arange(n_timesteps + 1, dtype=torch.float32) / n_timesteps
    f = torch.cos((steps + s) / (1 + s) * torch.pi * 0.5) ** 2
    alpha_bars = f / f[0]
    betas = 1.0 - alpha_bars[1:] / alpha_bars[:-1]
    return torch.clip(betas, 1e-4, 0.999)
