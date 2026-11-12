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


def test_cosine_decays_to_the_floor_by_the_last_step():
    assert lr_factor(10, 100, 0.1, 0.1) == pytest.approx(1.0)
    mid = lr_factor(55, 100, 0.1, 0.1)
    assert mid == pytest.approx(0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * 0.5)))
    assert lr_factor(100, 100, 0.1, 0.1) == pytest.approx(0.1)


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
    loss = (p * 1e6).sum()  # a huge gradient
    opt.step(loss)
    assert torch.linalg.vector_norm(p.detach()) < 1.0  # clipped, so the step stayed small
