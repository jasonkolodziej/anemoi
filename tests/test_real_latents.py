"""Real latent extraction from the five trained Group 1 Stage B models
(#22, training.real_latents).

Builds genuinely-trained (tiny, few-epoch) real models via the same
train_*_stage functions the per-model runners use, rather than hand-rolled
stand-ins -- what's worth verifying here is that `extract_joint_latents`
correctly reproduces each model's real input/output space (using its
RunArtifacts' exact standardisation stats) and lines up all five models'
latents/predictions/context on the same real windows.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.features import FEATURE_NAMES, GriddedFields
from anemoi.data.gridded_cache import FetchTask, cache_path, save_cached_fields
from anemoi.data.sources import Flavor

T = datetime(2026, 8, 6, 0, tzinfo=UTC)


def make_track(storm_id: str, season: int, n: int = 26, *, seed: int = 0) -> Track:
    rng = np.random.default_rng(seed)
    lat, lon = 15.0, -50.0
    start = datetime(season, 8, 1, tzinfo=UTC)
    fixes = []
    for i in range(n):
        lat += float(rng.uniform(0.1, 0.3))
        lon -= float(rng.uniform(0.2, 0.5))
        fixes.append(
            Fix(
                storm_id=storm_id,
                valid_time=start + timedelta(hours=6 * i),
                lat=round(lat, 2),
                lon=round(lon, 2),
                max_wind_kt=float(50 + 2 * i),
                min_pressure_mb=float(995 - 1.5 * i),
                quality=TrackQuality.FINAL,
            )
        )
    return Track(storm_id=storm_id, fixes=tuple(fixes))


def make_fields(valid_time: datetime, flavor: Flavor, shape=(41, 41)) -> GriddedFields:
    grid = lambda v: np.full(shape, v)  # noqa: E731
    return GriddedFields(
        valid_time=valid_time, flavor=flavor,
        u200=grid(15.0), v200=grid(5.0), u850=grid(10.0), v850=grid(3.0),
        z500=grid(5750.0), rh700=grid(62.0), t700=grid(281.0), mslp=grid(1012.0),
        sst=grid(28.0), ohc=grid(60.0),
    )


def _task_for(track: Track, fix: Fix) -> FetchTask:
    return FetchTask(storm_id=track.storm_id, valid_time=fix.valid_time, lat=fix.lat, lon=fix.lon)


def cache_all_fixes(cache_dir: Path, track: Track, flavor: Flavor, shape=(41, 41)) -> None:
    for fix in track.fixes:
        task = _task_for(track, fix)
        fields = make_fields(fix.valid_time, flavor, shape)
        save_cached_fields(cache_path(cache_dir, task), fields, task)


torch_installed = pytest.importorskip("torch", reason="needs the torch extra")


@pytest.mark.torch
def test_extract_joint_latents_lines_up_all_five_models_on_real_windows(tmp_path):
    from anemoi.data.splits import STAGE_B_BOUNDARIES, Split, assign_splits, filter_tracks
    from anemoi.data.storm_relative import STORM_RELATIVE_COLUMNS
    from anemoi.models.cnn import build_cnn
    from anemoi.models.gnn import build_gnn
    from anemoi.models.lstm import build_lstm
    from anemoi.models.pinn import build_pinn
    from anemoi.models.transformer import build_transformer
    from anemoi.training.curriculum import stage_b
    from anemoi.training.real_latents import (
        CONTEXT_FEATURE_NAMES,
        GROUP1_ORDER,
        extract_joint_latents,
    )
    from anemoi.training.real_run import RunArtifacts, train_lstm_stage
    from anemoi.training.real_run_cnn import CNN_FIELD_NAMES, train_cnn_stage
    from anemoi.training.real_run_gnn import EDGE_FEATURES, NODE_FEATURES, train_gnn_stage
    from anemoi.training.real_run_pinn import _train_candidate_lstm, train_pinn_stage
    from anemoi.training.real_run_transformer import GRID_SIZE, train_transformer_stage

    tracks = [
        make_track("AL012021", season=2021, n=26, seed=0),
        make_track("AL022021", season=2021, n=26, seed=1),
        make_track("AL012023", season=2023, n=26, seed=2),
    ]
    cache_dir = tmp_path / "gdas_cache"
    for t in tracks:
        cache_all_fixes(cache_dir, t, Flavor.GDAS_FINETUNE)

    assignment = assign_splits(tracks, STAGE_B_BOUNDARIES)
    train_tracks = filter_tracks(tracks, assignment, Split.TRAIN)
    val_tracks = filter_tracks(tracks, assignment, Split.VAL)
    assert train_tracks and val_tracks  # sanity: the fixture must actually exercise both splits

    stage = stage_b(epochs=1, learning_rate=1e-2)
    rng = np.random.default_rng(1)
    leads = (12, 24, 36, 48, 72, 96, 120)
    hidden = 8

    lstm_model, _ = build_lstm(
        input_dim=len(STORM_RELATIVE_COLUMNS), hidden_dim=hidden, lead_hours=leads,
    )
    lstm_model, _tl, _vl, _vm, lstm_stats = train_lstm_stage(
        lstm_model, stage, train_tracks, val_tracks, rng, n_augment=1, device="cpu",
    )
    lstm_artifacts = RunArtifacts(model=lstm_model, x_mean=lstm_stats[0], x_std=lstm_stats[1],
                                   y_mean=lstm_stats[2], y_std=lstm_stats[3])

    cnn_model, _ = build_cnn(in_channels=len(CNN_FIELD_NAMES), latent_dim=hidden, lead_hours=leads)
    cnn_model, *_, cnn_stats = train_cnn_stage(
        cnn_model, stage, train_tracks, val_tracks, cache_dir, rng, n_augment=1, device="cpu",
    )
    cnn_artifacts = RunArtifacts(model=cnn_model, x_mean=cnn_stats[0], x_std=cnn_stats[1],
                                  y_mean=cnn_stats[2], y_std=cnn_stats[3])

    trf_model, _ = build_transformer(
        n_variables=10, grid_size=GRID_SIZE, patch_size=4, d_model=hidden,
        n_heads=2, n_layers=1, dropout=0.0, lead_hours=leads,
    )
    trf_model, *_, trf_stats = train_transformer_stage(
        trf_model, stage, train_tracks, val_tracks, cache_dir, rng, n_augment=1, device="cpu",
    )
    trf_artifacts = RunArtifacts(model=trf_model, x_mean=trf_stats[0], x_std=trf_stats[1],
                                  y_mean=trf_stats[2], y_std=trf_stats[3])

    gnn_model, _ = build_gnn(
        node_features=NODE_FEATURES, edge_features=EDGE_FEATURES, hidden_dim=hidden,
        n_layers=1, lead_hours=leads,
    )
    gnn_model, *_, gnn_stats = train_gnn_stage(
        gnn_model, stage, train_tracks, val_tracks, cache_dir, rng, n_augment=1, device="cpu",
    )
    gnn_artifacts = RunArtifacts(model=gnn_model, x_mean=gnn_stats[0], x_std=gnn_stats[1],
                                  y_mean=gnn_stats[2], y_std=gnn_stats[3])

    candidate = _train_candidate_lstm(
        train_tracks, rng, n_augment=1, device="cpu", hidden_dim=hidden, epochs=2,
    )
    pinn_model, _ = build_pinn(input_dim=len(FEATURE_NAMES), hidden_dim=hidden, lead_hours=leads)
    pinn_model, *_, env_stats = train_pinn_stage(
        pinn_model, candidate, stage, train_tracks, val_tracks, cache_dir, rng,
        n_augment=1, device="cpu",
    )
    pinn_artifacts = RunArtifacts(
        model=pinn_model, candidate_model=candidate, env_mean=env_stats[0], env_std=env_stats[1],
    )

    trained_artifacts = {
        "lstm": lstm_artifacts, "cnn": cnn_artifacts, "transformer": trf_artifacts,
        "gnn": gnn_artifacts, "pinn": pinn_artifacts,
    }

    bundle = extract_joint_latents(
        tracks, trained_artifacts, cache_dir, seed=7, n_augment=1, device="cpu",
    )

    assert len(bundle) > 0
    assert len(bundle.train) > 0
    assert len(bundle.val) > 0
    for samples in (bundle.train, bundle.val):
        assert samples.latent_dims == (hidden, hidden, hidden, hidden, hidden)
        assert samples.z.shape == (len(samples), hidden * 5)
        assert np.all(np.isfinite(samples.z))
        assert samples.predictions.shape == (len(samples), len(GROUP1_ORDER), len(leads), 3)
        assert np.all(np.isfinite(samples.predictions))
        # a real predicted position must be a real coordinate, not a raw
        # un-un-standardised displacement or NaN
        assert np.all(np.abs(samples.predictions[..., 0]) <= 90.0)
        assert np.all(np.abs(samples.predictions[..., 1]) <= 180.0)
        assert samples.true_absolute.shape == (len(samples), len(leads), 3)
        assert samples.context.shape == (len(samples), len(CONTEXT_FEATURE_NAMES))
        assert np.all(np.isfinite(samples.context))
        assert samples.y.shape == (len(samples), len(leads), 3)
        assert samples.mask.shape == (len(samples), len(leads))
        assert samples.base_lat.shape == (len(samples),)


def test_extract_joint_latents_rejects_missing_group1_model(tmp_path):
    from anemoi.training.real_latents import extract_joint_latents

    with pytest.raises(ValueError, match="missing trained Group 1"):
        extract_joint_latents([], {"lstm": object()}, tmp_path, seed=1)
