"""Real deterministic_fn for inference.cycle.run_cycle (#78)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.features import GriddedFields
from anemoi.data.gridded_cache import FetchTask, cache_path, save_cached_fields
from anemoi.data.sources import Flavor
from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config
from anemoi.tracking.registry import ModelRegistry, Stage
from anemoi.training.capacity_ablation import SEQUENCE_LENGTH
from anemoi.training.real_inference_cycle import InferenceCycleError, build_real_deterministic_fn
from anemoi.training.real_run_cnn import CNN_FIELD_NAMES
from anemoi.training.real_run_gnn import NODE_FEATURES
from anemoi.training.real_run_transformer import GRID_SIZE, TRANSFORMER_FIELD_NAMES

torch_installed = pytest.importorskip("torch", reason="needs the torch extra")


class _FakeS3Client:
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


def _store() -> CheckpointStore:
    config = S3Config(
        endpoint_url="https://example.r2.cloudflarestorage.com",
        bucket="anemoi-test", access_key_id="key", secret_access_key="secret",
    )
    return CheckpointStore(config, client=_FakeS3Client())


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


def cache_current_fix(cache_dir, track: Track, fix: Fix, shape=(41, 41)) -> None:
    grid = lambda v: np.full(shape, v)  # noqa: E731
    fields = GriddedFields(
        valid_time=fix.valid_time, flavor=Flavor.GDAS_FINETUNE,
        u200=grid(15.0), v200=grid(5.0), u850=grid(10.0), v850=grid(3.0),
        z500=grid(5750.0), rh700=grid(62.0), t700=grid(281.0), mslp=grid(1012.0),
        sst=grid(28.0), ohc=grid(60.0),
    )
    task = FetchTask(storm_id=track.storm_id, valid_time=fix.valid_time, lat=fix.lat, lon=fix.lon)
    save_cached_fields(cache_path(cache_dir, task), fields, task)


def _register_real_version(
    name, build_kwargs, x_shape, registry, store, tmp_path, stage=Stage.PRODUCTION,
):
    """Real end-to-end registration: build a real (untrained -- weight
    quality doesn't matter for testing the wiring) model, upload its real
    state_dict, register it with real arch_params + real-shaped
    standardisation stats, promote to ``stage``."""
    import torch

    from anemoi.training.real_inference import _builder

    model, _spec = _builder(name)(**build_kwargs)
    local_path = tmp_path / f"{name}-det-fn-test.pt"
    torch.save(model.state_dict(), local_path)
    checkpoint_uri = store.upload(local_path, f"checkpoints/{name}/B/test.pt")

    n_leads = 7
    tags = {
        "arch_params": json.dumps(build_kwargs),
        "x_mean": json.dumps(np.zeros(x_shape).tolist()),
        "x_std": json.dumps(np.ones(x_shape).tolist()),
        "y_mean": json.dumps(np.zeros((n_leads, 3)).tolist()),
        "y_std": json.dumps(np.ones((n_leads, 3)).tolist()),
    }
    version = registry.register(
        name, run_id=f"test-{name}", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 100.0 + hash(name) % 50}, tags=tags,
        checkpoint_uri=checkpoint_uri,
    )
    registry.transition(name, version.version, stage)


@pytest.mark.torch
def test_build_real_deterministic_fn_combines_all_four_real_models(tmp_path):
    from anemoi.inference.scheduler import CyclePlan

    track = make_track("AL011985", n=SEQUENCE_LENGTH + 5)
    current = track.fixes[-1]
    cache_current_fix(tmp_path, track, current)

    registry = ModelRegistry(tmp_path / "registry")
    store = _store()

    _register_real_version(
        "lstm", {"input_dim": 5, "hidden_dim": 8, "lead_hours": [12, 24, 36, 48, 72, 96, 120]},
        x_shape=(5,), registry=registry, store=store, tmp_path=tmp_path,
    )
    _register_real_version(
        "cnn", {
            "in_channels": len(CNN_FIELD_NAMES), "latent_dim": 8,
            "lead_hours": [12, 24, 36, 48, 72, 96, 120],
        },
        x_shape=(1, len(CNN_FIELD_NAMES), 1, 1), registry=registry, store=store, tmp_path=tmp_path,
    )
    _register_real_version(
        "transformer", {
            "n_variables": len(TRANSFORMER_FIELD_NAMES), "grid_size": list(GRID_SIZE),
            "d_model": 8, "dropout": 0.0, "lead_hours": [12, 24, 36, 48, 72, 96, 120],
        },
        x_shape=(1, len(TRANSFORMER_FIELD_NAMES), 1, 1),
        registry=registry, store=store, tmp_path=tmp_path,
    )
    _register_real_version(
        "gnn", {
            "node_features": NODE_FEATURES, "edge_features": 3, "hidden_dim": 8,
            "lead_hours": [12, 24, 36, 48, 72, 96, 120],
        },
        x_shape=(1, 1, NODE_FEATURES), registry=registry, store=store, tmp_path=tmp_path,
    )

    deterministic_fn = build_real_deterministic_fn(track, registry, store, tmp_path)
    plan = CyclePlan(
        target_time=current.valid_time, cycle_start=current.valid_time,
        stages=(), inputs=None, vitals_estimated=False,
    )

    forecast = deterministic_fn(plan, current)

    assert forecast.lead_hours == (12, 24, 36, 48, 72, 96, 120)
    assert np.all(np.isfinite(forecast.lats))
    assert np.all(np.isfinite(forecast.lons))
    assert np.all(np.isfinite(forecast.winds_kt))
    assert set(forecast.contributors) == {"lstm", "cnn", "transformer", "gnn"}
    assert pytest.approx(sum(forecast.contributors.values()), abs=1e-6) == 1.0


def test_build_real_deterministic_fn_raises_with_no_registered_models(tmp_path):
    from anemoi.inference.scheduler import CyclePlan

    track = make_track("AL011985", n=SEQUENCE_LENGTH + 5)
    current = track.fixes[-1]
    registry = ModelRegistry(tmp_path / "registry")
    store = _store()

    deterministic_fn = build_real_deterministic_fn(track, registry, store, tmp_path)
    plan = CyclePlan(
        target_time=current.valid_time, cycle_start=current.valid_time,
        stages=(), inputs=None, vitals_estimated=False,
    )
    with pytest.raises(InferenceCycleError, match="no real Group 1 model"):
        deterministic_fn(plan, current)
