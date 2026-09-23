"""Consistency distillation for Anemoi-Spread (training.consistency_distillation, #15)."""

from __future__ import annotations

import json

import numpy as np
import pytest

from anemoi.metrics.ensemble_calibration import LeadCalibration
from anemoi.metrics.probabilistic import SpreadSkill
from anemoi.training.consistency_distillation import (
    ConfigResult,
    TradeoffReport,
    evaluate_step_budget_tradeoff,
    format_tradeoff_report,
)

pytestmark = pytest.mark.torch

_LEADS = (12, 24, 36, 48, 72, 96, 120)
_LATENT = 6
_ARCH = dict(latent_dim=_LATENT, hidden_dim=16, n_layers=1, n_timesteps=10, lead_hours=_LEADS)


def _lc(lead, quantity, spread, rmse, n=20):
    return LeadCalibration(
        lead_hours=lead, quantity=quantity, n_cases=n,
        rank_counts=(10, 0, 0, 10), spread_skill=SpreadSkill(spread=spread, skill=rmse),
    )


# --- the decision rule, in isolation (constructed reports, no real model) ---


def _report(student_overall, teacher_overall=None, track_errors=(29.0, 15.0)):
    teacher_overall = teacher_overall or [
        _lc(72, "along_track_nm", 40.0, 100.0), _lc(72, "cross_track_nm", 40.0, 100.0),
    ]
    configs = [
        ConfigResult("teacher", 10, 0.1, track_errors[0], teacher_overall),
        ConfigResult("student-1step", 1, 0.01, track_errors[1], student_overall),
    ]

    teacher_ratios = {(r.lead_hours, r.quantity): r.ratio for r in teacher_overall}
    student_ratios = {(r.lead_hours, r.quantity): r.ratio for r in student_overall}
    reasons = []
    for key, tr in teacher_ratios.items():
        sr = student_ratios.get(key)
        if sr is None or sr < 0.7 * tr:
            reasons.append(f"shortfall {key}")
    recommendation = "warranted" if not reasons else "not_warranted"
    return TradeoffReport(
        configs=configs, n_val_cases=20, recommendation=recommendation, reasons=reasons,
    )


def test_a_student_close_to_teacher_calibration_is_warranted():
    student_overall = [
        _lc(72, "along_track_nm", 38.0, 100.0), _lc(72, "cross_track_nm", 39.0, 100.0),
    ]
    report = _report(student_overall)
    assert report.recommendation == "warranted"


def test_a_collapsed_student_is_not_warranted():
    """A student whose spread collapsed well below the teacher's own
    (already-imperfect) spread must not be recommended, even though the
    teacher itself may not be "calibrated" outright -- the bar is relative
    to the model it was distilled from, per the module's own decision rule."""
    student_overall = [
        _lc(72, "along_track_nm", 5.0, 100.0), _lc(72, "cross_track_nm", 5.0, 100.0),
    ]
    report = _report(student_overall)
    assert report.recommendation == "not_warranted"
    assert any("along_track_nm" in r for r in report.reasons)


# --- the real end-to-end harness (synthetic teacher/student, no registry) ---


def _fake_samples(n, seed):
    from anemoi.training.real_latents import CONTEXT_FEATURE_NAMES, JointLatentSamples

    rng = np.random.default_rng(seed)
    n_leads = len(_LEADS)
    y = np.zeros((n, n_leads, 3))
    y[..., 0] = -20.0 * (np.arange(n_leads) + 1)
    y[..., 1] = 20.0 * (np.arange(n_leads) + 1)
    y[..., 2] = 80.0
    y[..., :2] += rng.normal(0, 10.0, size=(n, n_leads, 2))
    context = np.zeros((n, len(CONTEXT_FEATURE_NAMES)))
    return JointLatentSamples(
        z=rng.normal(size=(n, _LATENT)), y=y, mask=np.ones((n, n_leads), dtype=bool),
        base_lat=np.full(n, 20.0), base_lon=np.full(n, -60.0),
        predictions=np.zeros((n, 5, n_leads, 3)), true_absolute=np.zeros((n, n_leads, 3)),
        context=context, latent_dims=(_LATENT,),
    )


def _stats(train):
    z_mean, z_std = train.z.mean(0), train.z.std(0)
    z_std[z_std < 1e-8] = 1.0
    y_mean, y_std = train.y.mean(0), train.y.std(0)
    y_std[y_std < 1e-8] = 1.0
    return dict(z_mean=z_mean, z_std=z_std, y_mean=y_mean, y_std=y_std)


@pytest.fixture
def teacher_and_data():
    from anemoi.models.diffusion import build_diffusion

    train, val = _fake_samples(30, 1), _fake_samples(15, 2)
    teacher, _spec = build_diffusion(**_ARCH)
    teacher.eval()
    return teacher, train, val, _stats(train)


def test_distillation_trains_a_student_without_mutating_the_teachers_device(teacher_and_data):
    """A real regression this module's own harness must not reintroduce:
    `distill_consistency_model` moves `teacher` to a training device for
    speed, but every real caller (`evaluate_step_budget_tradeoff`,
    mirroring `spread_backtest`) expects a CPU-resident model afterwards,
    the same convention `real_inference.load_trained_model` uses."""
    import torch

    from anemoi.training.consistency_distillation import distill_consistency_model

    teacher, train, val, stats = teacher_and_data
    device_before = next(teacher.parameters()).device

    student, train_loss, val_loss, epochs_run = distill_consistency_model(
        teacher, train, val, arch_params=_ARCH, epochs=6, patience=3,
        n_val_samples_per_epoch=15, **stats,
    )

    assert next(teacher.parameters()).device == device_before
    assert next(student.parameters()).device == torch.device("cpu")
    assert epochs_run >= 1
    assert np.isfinite(train_loss)
    assert np.isfinite(val_loss)


@pytest.mark.parametrize("kwargs", [{"epochs": 0}, {"patience": 0}])
def test_distillation_rejects_a_non_positive_epochs_or_patience(teacher_and_data, kwargs):
    from anemoi.training.consistency_distillation import distill_consistency_model

    teacher, train, val, stats = teacher_and_data
    with pytest.raises(ValueError, match="epochs|patience"):
        distill_consistency_model(teacher, train, val, arch_params=_ARCH, **kwargs, **stats)


def test_distillation_restores_the_teachers_device_and_mode_even_if_training_raises(
    teacher_and_data,
):
    """The real regression Copilot review caught on PR #170: a mid-loop
    exception (OOM, a NaN loss, a keyboard interrupt) must not leave the
    caller's `teacher` stranded on the training device or in train() mode
    -- both must be restored in `finally`, not only on the success path."""
    from anemoi.training.consistency_distillation import distill_consistency_model

    teacher, train, val, stats = teacher_and_data
    device_before = next(teacher.parameters()).device
    teacher.eval()

    def boom(*_args, **_kwargs):
        raise RuntimeError("simulated mid-training failure")

    teacher.forward = boom

    with pytest.raises(RuntimeError, match="simulated mid-training failure"):
        distill_consistency_model(
            teacher, train, val, arch_params=_ARCH, epochs=6, patience=3, **stats,
        )

    assert next(teacher.parameters()).device == device_before
    assert teacher.training is False


def test_evaluate_step_budget_tradeoff_runs_end_to_end(teacher_and_data):
    from anemoi.models.consistency import build_consistency_model

    teacher, train, val, stats = teacher_and_data
    student, _spec = build_consistency_model(**_ARCH)

    report = evaluate_step_budget_tradeoff(
        teacher, student, val, stats, _LEADS, teacher_n_timesteps=_ARCH["n_timesteps"],
        student_step_options=(1, 2), n_members=6, min_cases=5,
    )

    assert report.n_val_cases == 15
    assert [c.label for c in report.configs] == ["teacher", "student-1step", "student-2step"]
    assert [c.nfe for c in report.configs] == [10, 1, 2]
    for c in report.configs:
        assert c.wall_time_s >= 0.0
        assert c.track_error_48h_nm is None or np.isfinite(c.track_error_48h_nm)
    assert report.recommendation in {"warranted", "not_warranted", "insufficient_data"}
    assert "recommendation" in format_tradeoff_report(report)
    json.dumps(report.to_dict())  # serialisable for the CLI's --out


def test_evaluate_step_budget_tradeoff_reports_insufficient_data_below_min_cases(teacher_and_data):
    from anemoi.models.consistency import build_consistency_model

    teacher, train, val, stats = teacher_and_data
    student, _spec = build_consistency_model(**_ARCH)

    report = evaluate_step_budget_tradeoff(
        teacher, student, val, stats, _LEADS, teacher_n_timesteps=_ARCH["n_timesteps"],
        student_step_options=(1,), n_members=4, min_cases=1000,
    )

    assert report.recommendation == "insufficient_data"
