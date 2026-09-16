"""Capacity-vs-sample-size ablation harness (#9)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.storm_relative import STORM_RELATIVE_COLUMNS
from anemoi.data.synthetic import generate_archive
from anemoi.training.capacity_ablation import (
    _FIXES_PER_SAMPLE,
    AblationCell,
    AblationReport,
    build_samples,
    run_capacity_ablation,
    train_cell,
)

T = datetime(2026, 8, 6, 0, tzinfo=UTC)


def make_track(storm_id: str, n: int, *, seed: int = 0) -> Track:
    rng = np.random.default_rng(seed)
    lat, lon = 15.0, -50.0
    fixes = []
    for i in range(n):
        lat += float(rng.uniform(0.1, 0.4))
        lon -= float(rng.uniform(0.2, 0.6))
        fixes.append(
            Fix(
                storm_id=storm_id,
                valid_time=T + timedelta(hours=6 * i),
                lat=round(lat, 2),
                lon=round(lon, 2),
                max_wind_kt=float(50 + 3 * i),
                min_pressure_mb=float(995 - 2 * i),
                quality=TrackQuality.FINAL,
            )
        )
    return Track(storm_id=storm_id, fixes=tuple(fixes))


# --- build_samples (pure numpy, no torch needed) ------------------------------


def test_build_samples_shapes_match_sequence_length_and_columns():
    track = make_track("AL012026", n=_FIXES_PER_SAMPLE + 2)
    rng = np.random.default_rng(1)
    x, y = build_samples([track], rng, n_augment=1)
    assert x.ndim == 3
    assert x.shape[1:] == (4, len(STORM_RELATIVE_COLUMNS))  # SEQUENCE_LENGTH == 4
    assert y.shape == (x.shape[0], 3)


def test_build_samples_augmentation_multiplies_sample_count():
    track = make_track("AL012026", n=_FIXES_PER_SAMPLE + 2)
    rng = np.random.default_rng(2)
    x1, _ = build_samples([track], rng, n_augment=1)
    x3, _ = build_samples([track], rng, n_augment=3)
    assert x3.shape[0] == 3 * x1.shape[0]


def test_build_samples_skips_storms_shorter_than_required():
    short = make_track("AL022026", n=_FIXES_PER_SAMPLE - 1)
    rng = np.random.default_rng(3)
    x, y = build_samples([short], rng, n_augment=1)
    assert x.shape[0] == 0
    assert y.shape[0] == 0


def test_build_samples_wind_label_uses_final_track_not_the_noisy_working_input():
    """The wind label must come from the FINAL track even though the input
    window is drawn from an EMULATED (noisy) working track -- if it used the
    same noisy realisation, the model would be trained to predict noise.
    (The position label legitimately does vary with the noisy input: it is
    the displacement from wherever the noisy "current" fix placed the storm
    to the true future position -- exactly what a real forecast must do.)"""
    track = make_track("AL032026", n=_FIXES_PER_SAMPLE)
    rng = np.random.default_rng(4)
    _, y_a = build_samples([track], rng, n_augment=1)
    rng2 = np.random.default_rng(5)
    _, y_b = build_samples([track], rng2, n_augment=1)
    assert np.allclose(y_a[:, 2], y_b[:, 2])  # wind column: identical across noise draws
    assert not np.allclose(y_a[:, :2], y_b[:, :2])  # position: varies with the noisy input


# --- AblationReport (pure dataclass logic, no torch needed) -------------------


def _cell(hidden_dim, fraction, val_loss):
    return AblationCell(
        hidden_dim=hidden_dim,
        sample_fraction=fraction,
        n_storms=10,
        n_train_samples=100,
        n_val_samples=20,
        final_train_loss=val_loss * 0.8,
        final_val_loss=val_loss,
    )


def test_capacity_helps_when_val_loss_keeps_dropping_with_width():
    report = AblationReport(cells=(_cell(8, 1.0, 1.0), _cell(128, 1.0, 0.5)))
    assert report.capacity_helps_at_full_data()
    assert "GO" in report.recommend()
    assert "NO-GO" not in report.recommend()


def test_capacity_does_not_help_when_val_loss_plateaus():
    report = AblationReport(cells=(_cell(8, 1.0, 1.0), _cell(128, 1.0, 0.995)))
    assert not report.capacity_helps_at_full_data()
    assert "NO-GO" in report.recommend()


def test_capacity_helps_uses_the_largest_fraction_present():
    report = AblationReport(
        cells=(_cell(8, 0.5, 1.0), _cell(128, 0.5, 0.1), _cell(8, 1.0, 1.0), _cell(128, 1.0, 0.99))
    )
    assert not report.capacity_helps_at_full_data()  # judged at fraction=1.0, not 0.5


def test_at_fraction_filters_and_sorts_by_hidden_dim():
    report = AblationReport(cells=(_cell(64, 1.0, 0.3), _cell(8, 1.0, 1.0)))
    cells = report.at_fraction(1.0)
    assert [c.hidden_dim for c in cells] == [8, 64]


def test_capacity_helps_requires_at_least_two_capacity_levels():
    report = AblationReport(cells=(_cell(8, 1.0, 1.0),))
    with pytest.raises(ValueError, match="two capacity levels"):
        report.capacity_helps_at_full_data()


def test_to_markdown_includes_every_cell():
    report = AblationReport(cells=(_cell(8, 1.0, 1.0), _cell(64, 0.5, 0.6)))
    table = report.to_markdown()
    assert "8" in table and "64" in table
    assert table.startswith("|")


# --- torch-backed training (needs the torch extra) ----------------------------


pytestmark_torch = pytest.mark.torch


@pytest.mark.torch
def test_train_cell_returns_finite_losses():
    from anemoi.models.base import require_torch

    require_torch()
    tracks = [make_track(f"AL{i:02d}2026", n=_FIXES_PER_SAMPLE + 3, seed=i) for i in range(6)]
    rng = np.random.default_rng(6)
    x_train, y_train = build_samples(tracks[:4], rng, n_augment=2)
    x_val, y_val = build_samples(tracks[4:], rng, n_augment=1)

    train_loss, val_loss = train_cell(
        x_train, y_train, x_val, y_val, hidden_dim=8, epochs=3, seed=0
    )
    assert np.isfinite(train_loss)
    assert np.isfinite(val_loss)


@pytest.mark.torch
def test_train_cell_rejects_empty_splits():
    empty = np.empty((0, 4, len(STORM_RELATIVE_COLUMNS)))
    empty_y = np.empty((0, 3))
    non_empty = np.zeros((2, 4, len(STORM_RELATIVE_COLUMNS)))
    non_empty_y = np.zeros((2, 3))
    with pytest.raises(ValueError, match="empty train or val"):
        train_cell(empty, empty_y, non_empty, non_empty_y, hidden_dim=8, epochs=1)


@pytest.mark.torch
def test_run_capacity_ablation_covers_the_full_grid_on_a_small_synthetic_archive():
    from anemoi.models.base import require_torch

    require_torch()
    # Spans train (2018-2019) and val (2020) boundaries from DEFAULT_BOUNDARIES.
    tracks = generate_archive(2018, 2020, storms_per_season=8, seed=42)
    report = run_capacity_ablation(
        tracks,
        hidden_dims=(4, 8),
        sample_fractions=(0.5, 1.0),
        n_augment=1,
        epochs=2,
        seed=1,
    )
    assert len(report.cells) == 2 * 2
    assert all(np.isfinite(c.final_val_loss) for c in report.cells)
    assert isinstance(report.recommend(), str)


@pytest.mark.torch
def test_run_capacity_ablation_raises_without_val_storms():
    tracks = [make_track("AL012026", n=_FIXES_PER_SAMPLE + 2)]  # 2026: not in any split
    with pytest.raises(ValueError, match="non-empty train and val"):
        run_capacity_ablation(tracks, hidden_dims=(4,), sample_fractions=(1.0,))
