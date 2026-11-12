"""Transformer optimisation: a capped peak learning rate, linear warmup,
cosine decay and gradient clipping (`configs/curriculum.yaml` ``transformer``).

**Found** on the first multi-basin run (2026-11-12): with plain Adam at a
constant 1e-3, the transformer's Stage A ended at a training loss of 1.63
on standardised targets, worse than predicting the mean (~1.0), while the
CNN reached 0.02 and the GNN 0.25 on the same windows. A pre-norm
transformer trained from scratch without warmup at that rate is known to
stall early, so it never fitted and lost Atlantic skill against the
Atlantic-only v5. The other models keep plain Adam: they train fine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .. import config


@dataclass(frozen=True, slots=True)
class TransformerOptim:
    #: The stage's learning rate is capped at this.
    max_learning_rate: float
    #: Fraction of a stage's optimiser steps spent warming up linearly.
    warmup_fraction: float
    #: Where cosine decay ends, as a fraction of the peak.
    min_learning_rate_fraction: float
    #: Global gradient-norm clip; 0 turns clipping off.
    grad_clip_norm: float
    weight_decay: float

    def __post_init__(self) -> None:
        if not 0.0 < self.max_learning_rate < 1.0:
            raise config.ConfigError(
                "curriculum.yaml: transformer.max_learning_rate out of range"
            )
        if not 0.0 <= self.warmup_fraction < 1.0:
            raise config.ConfigError(
                "curriculum.yaml: transformer.warmup_fraction must be in [0, 1)"
            )
        if not 0.0 <= self.min_learning_rate_fraction <= 1.0:
            raise config.ConfigError(
                "curriculum.yaml: transformer.min_learning_rate_fraction must be in [0, 1]"
            )
        if self.grad_clip_norm < 0.0 or self.weight_decay < 0.0:
            raise config.ConfigError(
                "curriculum.yaml: transformer.grad_clip_norm and weight_decay must be >= 0"
            )


def transformer_optim() -> TransformerOptim:
    return TransformerOptim(
        max_learning_rate=config.get("curriculum", "transformer.max_learning_rate", float),
        warmup_fraction=config.get("curriculum", "transformer.warmup_fraction", float),
        min_learning_rate_fraction=config.get(
            "curriculum", "transformer.min_learning_rate_fraction", float
        ),
        grad_clip_norm=config.get("curriculum", "transformer.grad_clip_norm", float),
        weight_decay=config.get("curriculum", "transformer.weight_decay", float),
    )


#: Read at import, like every other config value, so a bad value fails the
#: process at start rather than mid-run.
TRANSFORMER_OPTIM: TransformerOptim = transformer_optim()


def lr_factor(step: int, total_steps: int, warmup_fraction: float, min_fraction: float) -> float:
    """Multiplier on the peak rate at optimiser ``step`` (0-based): linear
    warmup to 1, then cosine down to ``min_fraction`` at the last step."""
    total_steps = max(total_steps, 1)
    warmup = int(round(warmup_fraction * total_steps))
    if warmup and step < warmup:
        return (step + 1) / warmup
    span = max(total_steps - warmup, 1)
    progress = min(max(step - warmup, 0) / span, 1.0)
    return min_fraction + (1.0 - min_fraction) * 0.5 * (1.0 + math.cos(math.pi * progress))


class TransformerOptimizer:
    """AdamW with the schedule and clipping above. ``step(loss)`` replaces
    the ``backward``/``step`` pair, so a training loop changes in one place."""

    def __init__(self, torch: Any, params, stage_lr: float, total_steps: int,
                 settings: TransformerOptim | None = None) -> None:
        self.settings = settings or TRANSFORMER_OPTIM
        self._torch = torch
        self._params = [p for p in params]
        self.peak = min(stage_lr, self.settings.max_learning_rate)
        self.opt = torch.optim.AdamW(
            self._params, lr=self.peak, weight_decay=self.settings.weight_decay,
        )
        s = self.settings
        self.sched = torch.optim.lr_scheduler.LambdaLR(
            self.opt,
            lambda step: lr_factor(
                step, total_steps, s.warmup_fraction, s.min_learning_rate_fraction,
            ),
        )

    def zero_grad(self) -> None:
        self.opt.zero_grad()

    def step(self, loss) -> None:
        loss.backward()
        if self.settings.grad_clip_norm > 0.0:
            self._torch.nn.utils.clip_grad_norm_(self._params, self.settings.grad_clip_norm)
        self.opt.step()
        self.sched.step()
