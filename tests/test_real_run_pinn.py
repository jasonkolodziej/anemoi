"""Real Stage A/B curriculum run for the PINN baseline (#22)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.features import FEATURE_NAMES, GriddedFields
from anemoi.data.gridded_cache import FetchTask, cache_path, save_cached_fields
from anemoi.data.sources import Flavor
from anemoi.training.real_run_pinn import build_pinn_samples

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


def test_build_pinn_samples_environment_width_matches_feature_names(tmp_path):
    track = make_track("AL011985", season=1985, n=26)
    cache_all_fixes(tmp_path, track, Flavor.ERA5_PRETRAIN)
    rng = np.random.default_rng(1)

    samples = build_pinn_samples([track], tmp_path, rng, n_augment=1)

    assert len(samples) > 0
    assert samples.environment.shape[-1] == len(FEATURE_NAMES) == 11
    assert np.all(np.isfinite(samples.environment))


def test_build_pinn_samples_skips_fixes_with_no_cached_file(tmp_path):
    track = make_track("AL011985", season=1985, n=26)
    for i, fix in enumerate(track.fixes):
        if i % 2 == 0:
            task = _task_for(track, fix)
            fields = make_fields(fix.valid_time, Flavor.ERA5_PRETRAIN)
            save_cached_fields(cache_path(tmp_path, task), fields, task)
    rng = np.random.default_rng(2)

    samples = build_pinn_samples([track], tmp_path, rng, n_augment=1)  # must not raise
    assert 0 <= len(samples) <= len(track.fixes)


def test_build_pinn_samples_empty_when_nothing_cached(tmp_path):
    track = make_track("AL011985", season=1985, n=26)
    rng = np.random.default_rng(3)
    samples = build_pinn_samples([track], tmp_path, rng, n_augment=1)
    assert len(samples) == 0
    assert samples.environment.shape[-1] == len(FEATURE_NAMES)


def test_build_pinn_samples_skips_windows_with_non_finite_environment_features(tmp_path):
    """Real bug found training PINN for real on the VM against the actual
    growing ERA5 cache (#67): real ERA5 SST is NaN over land, and a
    storm-centred box entirely over land has no real ocean pixels to
    average -- data.features.area_mean's nanmean fix makes PARTIAL land
    coverage work, but a box that's entirely land still can't produce a
    finite feature vector. build_pinn_samples must skip that one window,
    not crash the whole curriculum run the way the real VM run did."""
    track = make_track("AL011985", season=1985, n=26)
    for i, fix in enumerate(track.fixes):
        task = _task_for(track, fix)
        shape = (41, 41)
        fields = make_fields(fix.valid_time, Flavor.ERA5_PRETRAIN, shape)
        if i == len(track.fixes) - 1:  # one storm-entirely-over-land fix
            fields = replace(fields, sst=np.full(shape, np.nan))
        save_cached_fields(cache_path(tmp_path, task), fields, task)
    rng = np.random.default_rng(7)

    samples = build_pinn_samples([track], tmp_path, rng, n_augment=1)  # must not raise
    assert len(samples) > 0
    assert np.all(np.isfinite(samples.environment))


def test_filter_windows_with_finite_env_drops_only_the_land_covered_window(tmp_path):
    """Direct test of the streaming-path filter (`train_pinn_stage_streaming`
    uses this, not build_pinn_samples's inline try/except) -- same real bug
    as the build_pinn_samples test above, exercised at the function that
    actually guards `_PinnWindowDataset`'s fixed-length index."""
    from anemoi.training.real_run import StageWindow
    from anemoi.training.real_run_pinn import _filter_windows_with_finite_env

    ok_fix = Fix(
        storm_id="AL011985", valid_time=datetime(1985, 8, 1, tzinfo=UTC),
        lat=20.0, lon=-60.0, max_wind_kt=60.0, min_pressure_mb=990.0,
        quality=TrackQuality.FINAL,
    )
    land_fix = Fix(
        storm_id="AL011985", valid_time=datetime(1985, 8, 1, 6, tzinfo=UTC),
        lat=20.0, lon=-60.0, max_wind_kt=60.0, min_pressure_mb=990.0,
        quality=TrackQuality.FINAL,
    )
    shape = (41, 41)
    ok_fields = make_fields(ok_fix.valid_time, Flavor.ERA5_PRETRAIN, shape)
    land_fields = replace(ok_fields, sst=np.full(shape, np.nan), valid_time=land_fix.valid_time)
    ok_task = FetchTask(
        storm_id="AL011985", valid_time=ok_fix.valid_time, lat=ok_fix.lat, lon=ok_fix.lon,
    )
    land_task = FetchTask(
        storm_id="AL011985", valid_time=land_fix.valid_time, lat=land_fix.lat, lon=land_fix.lon,
    )
    save_cached_fields(cache_path(tmp_path, ok_task), ok_fields, ok_task)
    save_cached_fields(cache_path(tmp_path, land_task), land_fields, land_task)

    windows = [
        StageWindow(
            storm_id="AL011985", window=(ok_fix,), current=ok_fix,
            y=np.zeros((1, 3)), mask=np.array([True]),
        ),
        StageWindow(
            storm_id="AL011985", window=(land_fix,), current=land_fix,
            y=np.zeros((1, 3)), mask=np.array([True]),
        ),
    ]

    kept = _filter_windows_with_finite_env(windows, tmp_path)
    assert len(kept) == 1
    assert kept[0].current.valid_time == ok_fix.valid_time


# --- torch-dependent -------------------------------------------------------

torch_installed = pytest.importorskip("torch", reason="needs the torch extra")


@pytest.mark.torch
def test_candidate_and_true_absolute_round_trips_zero_displacement():
    """A candidate/true displacement of (0,0) must map back to exactly the
    window's base position -- sanity check on the coordinate conversion
    PINN's absolute-lat/lon convention depends on."""
    from anemoi.training.real_run_pinn import PinnStageSamples, _candidate_and_true_absolute

    class ZeroModel:
        def __call__(self, x):
            import torch

            return torch.zeros(x.shape[0], 7, 3)

        def eval(self):
            return self

    samples = PinnStageSamples(
        x_track=np.zeros((2, 4, 5), dtype=np.float32),
        environment=np.zeros((2, len(FEATURE_NAMES)), dtype=np.float32),
        y=np.zeros((2, 7, 3), dtype=np.float32),
        mask=np.ones((2, 7), dtype=bool),
        base_lat=np.array([20.0, 21.0]),
        base_lon=np.array([-60.0, -61.0]),
    )
    candidate_abs, true_abs = _candidate_and_true_absolute(ZeroModel(), samples, device="cpu")
    assert np.allclose(candidate_abs[0, 0, :2], [20.0, -60.0])
    assert np.allclose(true_abs[1, 0, :2], [21.0, -61.0])


@pytest.mark.torch
def test_train_pinn_stage_runs_and_produces_val_metrics(tmp_path):
    from anemoi.models.pinn import build_pinn
    from anemoi.training.curriculum import stage_a
    from anemoi.training.real_run_pinn import _train_candidate_lstm, train_pinn_stage

    train_tracks = [make_track("AL011985", season=1985, n=26, seed=0)]
    val_tracks = [make_track("AL012020", season=2020, n=26, seed=1)]
    for t in train_tracks + val_tracks:
        cache_all_fixes(tmp_path, t, Flavor.ERA5_PRETRAIN)

    rng = np.random.default_rng(5)
    candidate = _train_candidate_lstm(
        train_tracks, rng, n_augment=1, device="cpu", hidden_dim=8, epochs=2,
    )
    leads = (12, 24, 36, 48, 72, 96, 120)
    model, _spec = build_pinn(input_dim=len(FEATURE_NAMES), hidden_dim=8, lead_hours=leads)
    stage = stage_a(epochs=2, learning_rate=1e-2)

    trained_model, train_loss, val_loss, val_metrics, _env_stats = train_pinn_stage(
        model, candidate, stage, train_tracks, val_tracks, tmp_path, rng, n_augment=1, device="cpu",
    )
    assert trained_model is model
    assert train_loss >= 0.0
    assert val_loss >= 0.0
    assert "track_error_12h_nm" in val_metrics.values


@pytest.mark.torch
def test_train_pinn_stage_streaming_runs_and_produces_val_metrics(tmp_path):
    from anemoi.models.pinn import build_pinn
    from anemoi.training.curriculum import stage_a
    from anemoi.training.real_run_pinn import (
        _train_candidate_lstm_streaming,
        train_pinn_stage_streaming,
    )

    train_tracks = [make_track("AL011985", season=1985, n=26, seed=0)]
    val_tracks = [make_track("AL012020", season=2020, n=26, seed=1)]
    for t in train_tracks + val_tracks:
        cache_all_fixes(tmp_path, t, Flavor.ERA5_PRETRAIN)

    rng = np.random.default_rng(5)
    candidate = _train_candidate_lstm_streaming(
        train_tracks, rng, n_augment=1, device="cpu", hidden_dim=8, epochs=2, batch_size=4,
    )
    leads = (12, 24, 36, 48, 72, 96, 120)
    model, _spec = build_pinn(input_dim=len(FEATURE_NAMES), hidden_dim=8, lead_hours=leads)
    stage = stage_a(epochs=2, learning_rate=1e-2)

    trained_model, train_loss, val_loss, val_metrics, stats = train_pinn_stage_streaming(
        model, candidate, stage, train_tracks, val_tracks, tmp_path, rng,
        n_augment=1, batch_size=4, device="cpu",
    )
    assert trained_model is model
    assert train_loss >= 0.0
    assert val_loss >= 0.0
    assert "track_error_12h_nm" in val_metrics.values
    env_mean, env_std = stats
    assert env_mean.shape == (len(FEATURE_NAMES),)


@pytest.mark.torch
def test_train_pinn_stage_streaming_raises_on_empty_cache(tmp_path):
    from anemoi.models.pinn import build_pinn
    from anemoi.training.curriculum import stage_a
    from anemoi.training.real_run_pinn import (
        _train_candidate_lstm_streaming,
        train_pinn_stage_streaming,
    )

    train_tracks = [make_track("AL011985", season=1985, n=26, seed=0)]
    val_tracks = [make_track("AL012020", season=2020, n=26, seed=1)]
    # deliberately no cache_all_fixes call -- nothing cached

    rng = np.random.default_rng(5)
    candidate = _train_candidate_lstm_streaming(
        train_tracks, rng, n_augment=1, device="cpu", hidden_dim=8, epochs=1, batch_size=4,
    )
    leads = (12, 24, 36, 48, 72, 96, 120)
    model, _spec = build_pinn(input_dim=len(FEATURE_NAMES), hidden_dim=8, lead_hours=leads)
    stage = stage_a(epochs=1, learning_rate=1e-2)

    with pytest.raises(ValueError, match="no cached GriddedFields matched"):
        train_pinn_stage_streaming(
            model, candidate, stage, train_tracks, val_tracks, tmp_path, rng,
            n_augment=1, device="cpu",
        )


class _FakeS3Client:
    """Same duck-typed surface tests/test_checkpoint_store.py uses."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key, local_path):
        self.objects[key] = Path(local_path).read_bytes()

    def get(self, key, local_path):
        Path(local_path).write_bytes(self.objects[key])

    def exists(self, key):
        return key in self.objects

    def list_keys(self, prefix):
        return [k for k in self.objects if k.startswith(prefix)]


@pytest.mark.torch
def test_run_pinn_curriculum_completes_both_stages(tmp_path):
    from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config
    from anemoi.training.real_run_pinn import run_pinn_curriculum

    era5_dir = tmp_path / "era5_cache"
    gdas_dir = tmp_path / "gdas_cache"
    tracks = [
        make_track("AL011985", season=1985, n=26, seed=0),
        make_track("AL012021", season=2021, n=26, seed=1),
        make_track("AL022021", season=2021, n=26, seed=2),
        make_track("AL012023", season=2023, n=26, seed=3),
    ]
    for t in tracks:
        cache_all_fixes(era5_dir, t, Flavor.ERA5_PRETRAIN)
        cache_all_fixes(gdas_dir, t, Flavor.GDAS_FINETUNE)

    config = S3Config(
        endpoint_url="https://example.r2.cloudflarestorage.com",
        bucket="anemoi-test", access_key_id="key", secret_access_key="secret",
    )
    store = CheckpointStore(config, client=_FakeS3Client())

    run, val_metrics, _artifacts = run_pinn_curriculum(
        tracks, store, era5_dir, gdas_dir, seed=42, n_augment=1,
        hidden_dim=8, candidate_hidden_dim=8,
    )

    assert run.complete
    assert [r.stage_name for r in run.results] == ["A", "B"]
    assert run.results[-1].flavor is Flavor.GDAS_FINETUNE
    for result in run.results:
        assert result.checkpoint_uri.startswith("s3://anemoi-test/checkpoints/pinn/")
    assert "track_error_12h_nm" in val_metrics.values


@pytest.mark.torch
def test_run_pinn_curriculum_streaming_completes_both_stages(tmp_path):
    from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config
    from anemoi.training.real_run_pinn import run_pinn_curriculum

    era5_dir = tmp_path / "era5_cache"
    gdas_dir = tmp_path / "gdas_cache"
    tracks = [
        make_track("AL011985", season=1985, n=26, seed=0),
        make_track("AL012021", season=2021, n=26, seed=1),
        make_track("AL022021", season=2021, n=26, seed=2),
        make_track("AL012023", season=2023, n=26, seed=3),
    ]
    for t in tracks:
        cache_all_fixes(era5_dir, t, Flavor.ERA5_PRETRAIN)
        cache_all_fixes(gdas_dir, t, Flavor.GDAS_FINETUNE)

    config = S3Config(
        endpoint_url="https://example.r2.cloudflarestorage.com",
        bucket="anemoi-test", access_key_id="key", secret_access_key="secret",
    )
    store = CheckpointStore(config, client=_FakeS3Client())

    run, val_metrics, _artifacts = run_pinn_curriculum(
        tracks, store, era5_dir, gdas_dir, seed=42, n_augment=1,
        hidden_dim=8, candidate_hidden_dim=8, streaming=True, batch_size=4,
    )

    assert run.complete
    assert [r.stage_name for r in run.results] == ["A", "B"]
    assert "track_error_12h_nm" in val_metrics.values
