"""The transformer's learning-rate schedule and optimiser (training/optim.py)."""

from __future__ import annotations

import math

import pytest

from anemoi.config import ConfigError
from anemoi.training.optim import TRANSFORMER_OPTIM, TransformerOptim, lr_factor


def test_warmup_rises_linearly_to_the_peak():
    assert lr_factor(0, 100, 0.1, 0.1) == pytest.approx(0.1)
    assert lr_factor(4, 100, 0.1, 0.1) == pytest.approx(0.5)
    assert lr_factor(9, 100, 0.1, 0.1) == pytest.approx(1.0)


def test_cosine_decays_to_the_floor_on_the_last_update():
    # Updates are indices 0..total_steps-1; warmup is 0..9 here.
    assert lr_factor(10, 100, 0.1, 0.1) == pytest.approx(1.0)
    mid = lr_factor(10 + 89 // 2, 100, 0.1, 0.1)
    assert mid == pytest.approx(0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * (89 // 2) / 89)))
    assert lr_factor(99, 100, 0.1, 0.1) == pytest.approx(0.1)


def test_a_short_stage_still_ends_on_the_floor():
    """Review of #238: a two-update stage used to finish at 0.55."""
    assert lr_factor(1, 2, 0.0, 0.1) == pytest.approx(0.1)


def test_no_warmup_starts_at_the_peak():
    assert lr_factor(0, 100, 0.0, 0.1) == pytest.approx(1.0)


def test_config_values_are_validated():
    with pytest.raises(ConfigError):
        TransformerOptim(
            max_learning_rate=0.0, warmup_fraction=0.05, min_learning_rate_fraction=0.1,
            grad_clip_norm=1.0, weight_decay=0.01,
        )


def test_the_optimiser_caps_the_stage_rate_warms_up_and_clips():
    torch = pytest.importorskip("torch")
    from anemoi.training.optim import TransformerOptimizer

    p = torch.nn.Parameter(torch.zeros(3))
    opt = TransformerOptimizer(torch, [p], stage_lr=1e-3, total_steps=100)
    assert opt.peak == min(1e-3, TRANSFORMER_OPTIM.max_learning_rate)
    first_lr = opt.opt.param_groups[0]["lr"]
    assert first_lr < opt.peak  # warming up
    opt.zero_grad()
    loss = (p * 1e6).sum()  # a gradient of norm ~1.7e6
    opt.step(loss)
    # The gradient left after the step is the clipped one: AdamW normalises
    # its own update, so the parameters alone wouldn't show a missing clip.
    assert torch.linalg.vector_norm(p.grad) == pytest.approx(
        TRANSFORMER_OPTIM.grad_clip_norm, rel=1e-4,
    )
