"""Stage B noise-emulator sensitivity (#12)."""

from __future__ import annotations

import pytest

from anemoi.data.synthetic import generate_archive
from anemoi.training.noise_sensitivity import (
    NoiseSensitivityReport,
    NoiseSensitivityResult,
    run_noise_sensitivity,
)


def _result(val_loss: float, label: str = "default") -> NoiseSensitivityResult:
    return NoiseSensitivityResult(
        noise_label=label,
        position_rms_nm=15.0,
        intensity_rms_kt=5.0,
        pressure_rms_mb=3.0,
        final_train_loss=val_loss * 0.8,
        final_val_loss=val_loss,
    )


# --- NoiseSensitivityReport (pure dataclass logic, no torch needed) -----------


def test_relative_change_is_zero_when_losses_match():
    report = NoiseSensitivityReport(default=_result(1.0), literature=_result(1.0, "literature"))
    assert report.relative_change == pytest.approx(0.0)


def test_relative_change_sign_matches_direction_of_the_move():
    worse = NoiseSensitivityReport(default=_result(1.0), literature=_result(1.5, "literature"))
    better = NoiseSensitivityReport(default=_result(1.0), literature=_result(0.5, "literature"))
    assert worse.relative_change > 0.0
    assert better.relative_change < 0.0


def test_is_load_bearing_above_threshold():
    report = NoiseSensitivityReport(default=_result(1.0), literature=_result(1.2, "literature"))
    assert report.is_load_bearing(threshold=0.05)
    assert "LOAD-BEARING" in report.recommend(threshold=0.05)


def test_is_not_load_bearing_below_threshold():
    report = NoiseSensitivityReport(default=_result(1.0), literature=_result(1.02, "literature"))
    assert not report.is_load_bearing(threshold=0.05)
    assert "NOT LOAD-BEARING" in report.recommend(threshold=0.05)


def test_relative_change_rejects_nonpositive_default_loss():
    report = NoiseSensitivityReport(default=_result(0.0), literature=_result(1.0, "literature"))
    with pytest.raises(ValueError, match="positive"):
        _ = report.relative_change


# --- run_noise_sensitivity (torch-backed) --------------------------------------


@pytest.mark.torch
def test_run_noise_sensitivity_covers_both_candidates_on_a_small_synthetic_archive():
    from anemoi.models.base import require_torch

    require_torch()
    # Spans train (2018-2019) and val (2020) boundaries from DEFAULT_BOUNDARIES.
    tracks = generate_archive(2018, 2020, storms_per_season=8, seed=7)
    report = run_noise_sensitivity(tracks, hidden_dim=8, n_augment=1, epochs=2, seed=1)

    assert report.default.noise_label == "default"
    assert report.literature.noise_label == "literature"
    assert report.default.position_rms_nm == pytest.approx(15.0)
    assert report.literature.intensity_rms_kt > report.default.intensity_rms_kt
    assert isinstance(report.relative_change, float)
    assert isinstance(report.recommend(), str)


@pytest.mark.torch
def test_run_noise_sensitivity_raises_without_val_storms():
    from datetime import UTC, datetime, timedelta

    from anemoi.data.besttrack import Fix, Track, TrackQuality

    fixes = tuple(
        Fix(
            storm_id="AL012026",
            valid_time=datetime(2026, 8, 6, tzinfo=UTC) + timedelta(hours=6 * i),
            lat=20.0 + 0.2 * i,
            lon=-60.0 - 0.3 * i,
            max_wind_kt=50.0,
            min_pressure_mb=995.0,
            quality=TrackQuality.FINAL,
        )
        for i in range(8)
    )
    tracks = [Track(storm_id="AL012026", fixes=fixes)]  # 2026: not in any split
    with pytest.raises(ValueError, match="non-empty train and val"):
        run_noise_sensitivity(tracks, hidden_dim=4, epochs=1)
