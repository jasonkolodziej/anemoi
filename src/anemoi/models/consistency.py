"""Anemoi-Spread consistency model, distilled from a trained diffusion model.

GitHub #15. `models.diffusion.build_diffusion`'s own docstring already names
the motivation: the 13-minute Anemoi-Spread stage budget (`inference.
scheduler.DEFAULT_BUDGETS`) currently has exactly one response to time
pressure -- `inference.scheduler`'s load-shedding profile, which drops the
ensemble from 20 to 10 members (`REDUCED_ENSEMBLE_MEMBERS`), a binary cut
with no middle setting. Consistency models (Song et al. 2023,
arXiv:2303.01469) support one-step generation by construction while still
allowing multistep sampling to trade compute for quality -- a graded
response instead of a binary one -- and are trained by *distilling* an
already-trained diffusion model rather than trained from scratch, which is
why #15 could only start once #22 produced a real trained diffusion
champion.

This module is the *model*: the consistency function itself and its
sampler. `training.consistency_distillation` is the *training procedure*
(discrete-time consistency distillation, Song et al. Algorithm 2) and the
real one-step-vs-multistep evaluation harness. Neither registers this model
into `tracking.registry` -- #15's acceptance criteria are "prototyped,
measured, decision recorded," not "shipped to the serving path"; the issue
says explicitly this is "an evaluation, not an up-front architectural
commitment."

## Boundary condition

A consistency function must satisfy ``f(x, t_min) = x`` -- the "least
noise" step maps to itself, so the function is a legitimate parametrisation
of a single point on the diffusion ODE trajectory rather than an arbitrary
network. This uses the same skip-connection construction as EDM (Karras et
al. 2022) and the original consistency models paper: ``f(x, t) = c_skip(t)
* x + c_out(t) * F_theta(x, t, cond)``, with ``c_skip``/``c_out`` chosen so
the boundary condition holds *exactly* at the schedule's own least-noise
step (index 0), not just approximately:

    c_skip(t) = alpha_bar[t] / alpha_bar[0]
    c_out(t)  = sqrt(1 - c_skip(t)**2)

At ``t=0``, ``c_skip=1`` and ``c_out=0`` exactly, by construction, for any
schedule -- ``f(x, 0) = x``. As ``t`` grows, ``c_skip`` falls off with the
same cosine schedule `models.diffusion` already uses (`alpha_bar`), so the
raw network's contribution grows exactly where the input is least
informative. This is one valid choice among many that satisfy the boundary
condition (Song et al.'s own EDM parametrisation is another) -- picked here
so the consistency model reuses the exact same ``alpha_bars`` buffer the
diffusion teacher does, with no extra hyperparameter to tune.
"""

from __future__ import annotations

from .base import DEFAULT_LEADS, ModelSpec, require_torch
from .diffusion import _cosine_schedule


def build_consistency_model(
    latent_dim: int = 256,
    extra_conditioning_dim: int = 0,
    hidden_dim: int = 256,
    n_layers: int = 6,
    n_timesteps: int = 200,
    lead_hours: tuple[int, ...] = DEFAULT_LEADS,
):
    """Build a `TrajectoryConsistencyModel`. Returns ``(module, spec)``.

    Signature mirrors `models.diffusion.build_diffusion` deliberately: a
    consistency model distilled from a diffusion teacher must share its
    ``latent_dim``/``extra_conditioning_dim``/``n_timesteps``/``lead_hours``
    (the schedule and conditioning shape the distillation teacher step
    depends on) even when ``hidden_dim``/``n_layers`` differ -- a smaller
    student is a real point in the compute/quality tradeoff this exists to
    measure (`training.consistency_distillation.evaluate_step_budget_
    tradeoff`), not a bug.
    """
    torch = require_torch()
    nn = torch.nn

    n_leads = len(lead_hours)
    traj_dim = n_leads * 3
    cond_dim = latent_dim + extra_conditioning_dim

    spec = ModelSpec(
        name="consistency", input_dim=cond_dim, latent_dim=hidden_dim, lead_hours=lead_hours
    )

    betas = _cosine_schedule(torch, n_timesteps)
    alphas = 1.0 - betas
    alpha_bars = torch.cumprod(alphas, dim=0)

    class TrajectoryConsistencyModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
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
                        nn.Linear(hidden_dim, hidden_dim),
                    )
                    for _ in range(n_layers)
                ]
            )
            self.out = nn.Linear(hidden_dim, traj_dim)

        def forward(self, noisy_traj, t, conditioning):
            """Raw ``F_theta`` -- not yet boundary-satisfying. Use
            `consistency_fn` for the real consistency function."""
            h = self.input_proj(noisy_traj.flatten(1))
            h = h + self.time_embed(t.float().unsqueeze(-1) / n_timesteps)
            h = h + self.cond_embed(conditioning)
            for block in self.blocks:
                h = h + block(h)
            return self.out(h).view(-1, n_leads, 3)

        def skip_coeffs(self, t):
            """``(c_skip, c_out)`` at integer step(s) ``t``, each shaped for
            broadcast against a (batch, n_leads, 3) trajectory."""
            ratio = self.alpha_bars[t] / self.alpha_bars[0]
            c_skip = ratio.view(-1, 1, 1)
            c_out = torch.sqrt((1.0 - ratio**2).clamp(min=0.0)).view(-1, 1, 1)
            return c_skip, c_out

        def consistency_fn(self, x, t, conditioning):
            """The real consistency function ``f(x, t, cond)``. ``t`` is an
            integer step index tensor, one per batch row (may all be equal)."""
            c_skip, c_out = self.skip_coeffs(t)
            return c_skip * x + c_out * self(x, t, conditioning)

        @torch.no_grad()
        def sample(self, conditioning, n_members: int = 20, n_steps: int = 1, generator=None):
            """Generate ``n_members`` trajectories with ``n_steps`` network
            evaluations (the real compute knob this model exists to expose).

            ``n_steps=1``: the whole point of a consistency model -- one
            evaluation from pure noise straight to the trajectory estimate.

            ``n_steps>1``: multistep consistency sampling (Song et al.
            Algorithm 1). Refines the one-step estimate by re-noising it to
            an intermediate, lower-noise step and re-applying ``f`` -- each
            extra step trades compute for quality, the graded response
            load shedding cannot offer.
            """
            if n_steps < 1:
                raise ValueError("n_steps must be >= 1")
            if conditioning.shape[0] == 1:
                conditioning = conditioning.expand(n_members, -1)
            elif conditioning.shape[0] != n_members:
                raise ValueError("conditioning batch must be 1 or n_members")

            device = conditioning.device
            if n_steps == 1:
                schedule = [n_timesteps - 1]
            else:
                schedule = (
                    torch.linspace(n_timesteps - 1, 1, n_steps, device=device)
                    .round()
                    .long()
                    .tolist()
                )

            x = torch.randn(n_members, n_leads, 3, generator=generator, device=device)
            t = torch.full((n_members,), schedule[0], device=device, dtype=torch.long)
            x0_hat = self.consistency_fn(x, t, conditioning)
            for step in schedule[1:]:
                alpha_bar = self.alpha_bars[step]
                noise = torch.randn(x0_hat.shape, generator=generator, device=device)
                x = torch.sqrt(alpha_bar) * x0_hat + torch.sqrt(1.0 - alpha_bar) * noise
                t = torch.full((n_members,), step, device=device, dtype=torch.long)
                x0_hat = self.consistency_fn(x, t, conditioning)
            return x0_hat

    return TrajectoryConsistencyModel(), spec
