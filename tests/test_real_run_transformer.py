"""Real Stage A/B curriculum run for the Transformer baseline (#22)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.features import GriddedFields
from anemoi.data.gridded_cache import FetchTask, cache_path, save_cached_fields
from anemoi.data.sources import Flavor
from anemoi.training.real_run_transformer import (
    GRID_SIZE,
    TRANSFORMER_FIELD_NAMES,
    build_transformer_samples,
)

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


def test_build_transformer_samples_trims_the_real_41x41_crop_to_grid_size(tmp_path):
    """The real cached crop is 41x41 (box_deg=10.0 at 0.25deg) -- not
    divisible by patch_size, so it must be trimmed to GRID_SIZE (40x40)."""
    track = make_track("AL011985", season=1985, n=26)
    cache_all_fixes(tmp_path, track, Flavor.ERA5_PRETRAIN, shape=(41, 41))
    rng = np.random.default_rng(1)

    samples = build_transformer_samples([track], tmp_path, rng, n_augment=1)

    assert len(samples) > 0
    assert samples.x.shape[1] == len(TRANSFORMER_FIELD_NAMES) == 10
    assert samples.x.shape[2:] == GRID_SIZE == (40, 40)


def test_build_transformer_samples_rejects_a_cache_smaller_than_grid_size(tmp_path):
    track = make_track("AL011985", season=1985, n=26)
    cache_all_fixes(tmp_path, track, Flavor.ERA5_PRETRAIN, shape=(20, 20))
    rng = np.random.default_rng(2)
    with pytest.raises(ValueError, match="smaller than grid_size"):
        build_transformer_samples([track], tmp_path, rng, n_augment=1)


def test_build_transformer_samples_empty_when_nothing_cached(tmp_path):
    track = make_track("AL011985", season=1985, n=26)
    rng = np.random.default_rng(3)
    samples = build_transformer_samples([track], tmp_path, rng, n_augment=1)
    assert len(samples) == 0


# --- torch-dependent -------------------------------------------------------

torch_installed = pytest.importorskip("torch", reason="needs the torch extra")


@pytest.mark.torch
def test_train_transformer_stage_runs_and_produces_val_metrics(tmp_path):
    from anemoi.models.transformer import build_transformer
    from anemoi.training.curriculum import stage_a
    from anemoi.training.real_run_transformer import train_transformer_stage

    train_tracks = [make_track("AL011985", season=1985, n=26, seed=0)]
    val_tracks = [make_track("AL012020", season=2020, n=26, seed=1)]
    for t in train_tracks + val_tracks:
        cache_all_fixes(tmp_path, t, Flavor.ERA5_PRETRAIN)

    leads = (12, 24, 36, 48, 72, 96, 120)
    # dropout=0.0: torch's MPS backend can't do scaled_dot_product_attention
    # with dropout > 0 (see run_transformer_curriculum's dropout docstring).
    model, _spec = build_transformer(
        n_variables=10, grid_size=GRID_SIZE, patch_size=4, d_model=16,
        n_heads=2, n_layers=1, dropout=0.0, lead_hours=leads,
    )
    stage = stage_a(epochs=2, learning_rate=1e-2)
    rng = np.random.default_rng(5)

    trained_model, train_loss, val_loss, val_metrics, _stats = train_transformer_stage(
        model, stage, train_tracks, val_tracks, tmp_path, rng, n_augment=1,
    )
    assert trained_model is model
    assert train_loss >= 0.0
    assert val_loss >= 0.0
    assert "track_error_12h_nm" in val_metrics.values


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
def test_run_transformer_curriculum_completes_both_stages(tmp_path):
    from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config
    from anemoi.training.real_run_transformer import run_transformer_curriculum

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

    # dropout=0.0: torch's MPS backend (this machine, when run locally)
    # can't do scaled_dot_product_attention with dropout > 0 -- a platform
    # gap, not something real training on the CUDA VM needs to work around.
    run, val_metrics, _artifacts = run_transformer_curriculum(
        tracks, store, era5_dir, gdas_dir, seed=42, n_augment=1, d_model=16, dropout=0.0,
    )

    assert run.complete
    assert [r.stage_name for r in run.results] == ["A", "B"]
    assert run.results[-1].flavor is Flavor.GDAS_FINETUNE
    for result in run.results:
        assert result.checkpoint_uri.startswith("s3://anemoi-test/checkpoints/transformer/")
    assert "track_error_12h_nm" in val_metrics.values
