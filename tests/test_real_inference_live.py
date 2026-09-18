"""Real-time feature building for live inference (#78)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.features import GriddedFields
from anemoi.data.gridded_cache import FetchTask, cache_path, save_cached_fields
from anemoi.data.sources import Flavor
from anemoi.data.storm_relative import storm_relative_sequence
from anemoi.training.capacity_ablation import SEQUENCE_LENGTH
from anemoi.training.real_inference_live import (
    build_live_cnn_x,
    build_live_gnn_x,
    build_live_lstm_x,
    build_live_transformer_x,
)

torch_installed = pytest.importorskip("torch", reason="needs the torch extra")


def make_track(storm_id: str, n: int, *, seed: int = 0) -> Track:
    rng = np.random.default_rng(seed)
    lat, lon = 15.0, -50.0
    start = datetime(2026, 8, 1, tzinfo=UTC)
    fixes = []
    for i in range(n):
        lat += float(rng.uniform(0.1, 0.3))
        lon -= float(rng.uniform(0.2, 0.5))
        fixes.append(Fix(
            storm_id=storm_id, valid_time=start + timedelta(hours=6 * i),
            lat=round(lat, 2), lon=round(lon, 2),
            max_wind_kt=float(50 + 2 * i), min_pressure_mb=float(995 - 1.5 * i),
            quality=TrackQuality.WORKING,
        ))
    return Track(storm_id=storm_id, fixes=tuple(fixes))


def make_fields(valid_time: datetime, shape=(41, 41)) -> GriddedFields:
    grid = lambda v: np.full(shape, v)  # noqa: E731
    return GriddedFields(
        valid_time=valid_time, flavor=Flavor.GDAS_FINETUNE,
        u200=grid(15.0), v200=grid(5.0), u850=grid(10.0), v850=grid(3.0),
        z500=grid(5750.0), rh700=grid(62.0), t700=grid(281.0), mslp=grid(1012.0),
        sst=grid(28.0), ohc=grid(60.0),
    )


def cache_current_fix(cache_dir, track: Track, fix: Fix, shape=(41, 41)) -> None:
    task = FetchTask(storm_id=track.storm_id, valid_time=fix.valid_time, lat=fix.lat, lon=fix.lon)
    save_cached_fields(cache_path(cache_dir, task), make_fields(fix.valid_time, shape), task)


# --- LSTM (no gridded fields needed) -----------------------------------------


def test_build_live_lstm_x_matches_storm_relative_sequence_directly():
    track = make_track("AL011985", n=SEQUENCE_LENGTH + 5)
    current = track.fixes[-1]

    x = build_live_lstm_x(track, current)

    expected_window = track.window_ending(current.valid_time, SEQUENCE_LENGTH + 1)
    assert expected_window is not None
    assert np.array_equal(x, storm_relative_sequence(expected_window))


def test_build_live_lstm_x_is_none_with_too_short_a_history():
    track = make_track("AL011985", n=2)
    current = track.fixes[-1]
    assert build_live_lstm_x(track, current) is None


def test_build_live_lstm_x_is_none_when_current_is_not_in_the_track():
    track = make_track("AL011985", n=SEQUENCE_LENGTH + 5)
    fake_current = Fix(
        storm_id="AL011985", valid_time=datetime(1999, 1, 1, tzinfo=UTC),
        lat=0.0, lon=0.0, max_wind_kt=10.0, min_pressure_mb=1000.0,
        quality=TrackQuality.WORKING,
    )
    assert build_live_lstm_x(track, fake_current) is None


# --- CNN/Transformer/GNN (need a real cached field for `current`) -----------


def test_build_live_cnn_x_returns_the_real_sanitized_channel_stack(tmp_path):
    from anemoi.training.real_run_cnn import CNN_FIELD_NAMES

    track = make_track("AL011985", n=3)
    current = track.fixes[-1]
    cache_current_fix(tmp_path, track, current, shape=(9, 9))

    x = build_live_cnn_x(track, current, tmp_path)

    assert x.shape == (len(CNN_FIELD_NAMES), 9, 9)
    assert np.all(np.isfinite(x))


def test_build_live_cnn_x_is_none_without_a_cached_field():
    track = make_track("AL011985", n=3)
    current = track.fixes[-1]
    assert build_live_cnn_x(track, current, "/nonexistent/cache") is None


def test_build_live_transformer_x_trims_to_the_real_grid_size(tmp_path):
    from anemoi.training.real_run_transformer import GRID_SIZE

    track = make_track("AL011985", n=3)
    current = track.fixes[-1]
    cache_current_fix(tmp_path, track, current, shape=(41, 41))

    x = build_live_transformer_x(track, current, tmp_path)

    assert x.shape[1:] == GRID_SIZE


def test_build_live_gnn_x_returns_node_features_and_a_real_topology(tmp_path):
    from anemoi.training.real_run_gnn import NODE_FEATURES

    track = make_track("AL011985", n=3)
    current = track.fixes[-1]
    cache_current_fix(tmp_path, track, current, shape=(41, 41))

    result = build_live_gnn_x(track, current, tmp_path)

    assert result is not None
    node_features, topo = result
    assert node_features.shape == (topo.n_nodes, NODE_FEATURES)
    assert np.all(np.isfinite(node_features))


def test_build_live_gnn_x_is_none_without_a_cached_field():
    track = make_track("AL011985", n=3)
    current = track.fixes[-1]
    assert build_live_gnn_x(track, current, "/nonexistent/cache") is None
