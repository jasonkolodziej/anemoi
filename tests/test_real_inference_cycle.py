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


def _upload_state_dict(model, name, store, tmp_path, suffix=""):
    import torch

    local_path = tmp_path / f"{name}{suffix}-det-fn-test.pt"
    torch.save(model.state_dict(), local_path)
    return store.upload(local_path, f"checkpoints/{name}/B/test{suffix}.pt")


def _register_real_version(
    name, build_kwargs, x_shape, registry, store, tmp_path,
    stage=Stage.PRODUCTION, extra_tags=None, n_leads=7, latent_signature=None,
):
    """Real end-to-end registration: build a real (untrained -- weight
    quality doesn't matter for testing the wiring) model, upload its real
    state_dict, register it with real arch_params + real-shaped
    standardisation stats, promote to ``stage``."""
    from anemoi.training.real_inference import _builder

    model, _spec = _builder(name)(**build_kwargs)
    checkpoint_uri = _upload_state_dict(model, name, store, tmp_path)

    tags = {"arch_params": json.dumps(build_kwargs)}
    if x_shape is not None:
        tags["x_mean"] = json.dumps(np.zeros(x_shape).tolist())
        tags["x_std"] = json.dumps(np.ones(x_shape).tolist())
        tags["y_mean"] = json.dumps(np.zeros((n_leads, 3)).tolist())
        tags["y_std"] = json.dumps(np.ones((n_leads, 3)).tolist())
    tags.update(extra_tags or {})

    version = registry.register(
        name, run_id=f"test-{name}", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 100.0 + hash(name) % 50}, tags=tags,
        checkpoint_uri=checkpoint_uri, latent_signature=latent_signature,
    )
    registry.transition(name, version.version, stage)
    return model


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


@pytest.mark.torch
def test_build_real_deterministic_fn_uses_the_real_learned_fusion_with_all_five(tmp_path):
    """Once all five real Group 1 predictions are available, the real
    ConsensusFusion model must be used instead of the non-learned
    fallback -- confirmed by the contributors summing to 1 (fusion's own
    softmax-normalised weights, same as the fallback's own guarantee)
    and containing exactly the five real model names, not the fallback
    path's differently-shaped output."""
    from anemoi.data.features import FEATURE_NAMES
    from anemoi.data.storm_relative import STORM_RELATIVE_COLUMNS
    from anemoi.inference.scheduler import CyclePlan
    from anemoi.models.lstm import build_lstm

    track = make_track("AL011985", n=SEQUENCE_LENGTH + 5)
    current = track.fixes[-1]
    cache_current_fix(tmp_path, track, current)

    registry = ModelRegistry(tmp_path / "registry")
    store = _store()
    leads = [12, 24, 36, 48, 72, 96, 120]

    _register_real_version(
        "lstm", {"input_dim": 5, "hidden_dim": 8, "lead_hours": leads},
        x_shape=(5,), registry=registry, store=store, tmp_path=tmp_path,
    )
    _register_real_version(
        "cnn", {"in_channels": len(CNN_FIELD_NAMES), "latent_dim": 8, "lead_hours": leads},
        x_shape=(1, len(CNN_FIELD_NAMES), 1, 1), registry=registry, store=store, tmp_path=tmp_path,
    )
    _register_real_version(
        "transformer", {
            "n_variables": len(TRANSFORMER_FIELD_NAMES), "grid_size": list(GRID_SIZE),
            "d_model": 8, "dropout": 0.0, "lead_hours": leads,
        },
        x_shape=(1, len(TRANSFORMER_FIELD_NAMES), 1, 1),
        registry=registry, store=store, tmp_path=tmp_path,
    )
    _register_real_version(
        "gnn", {
            "node_features": NODE_FEATURES, "edge_features": 3, "hidden_dim": 8,
            "lead_hours": leads,
        },
        x_shape=(1, 1, NODE_FEATURES), registry=registry, store=store, tmp_path=tmp_path,
    )

    # PINN: a real candidate LSTM checkpoint, then the corrector itself
    # tagged with the candidate's real uri/arch_params + real env stats.
    candidate_model, _spec = build_lstm(
        input_dim=len(STORM_RELATIVE_COLUMNS), hidden_dim=6, lead_hours=tuple(leads),
    )
    candidate_uri = _upload_state_dict(
        candidate_model, "pinn", store, tmp_path, suffix="-candidate",
    )
    _register_real_version(
        "pinn", {"input_dim": len(FEATURE_NAMES), "hidden_dim": 8, "lead_hours": leads},
        x_shape=None, registry=registry, store=store, tmp_path=tmp_path,
        extra_tags={
            "env_mean": json.dumps(np.zeros(len(FEATURE_NAMES)).tolist()),
            "env_std": json.dumps(np.ones(len(FEATURE_NAMES)).tolist()),
            "candidate_arch_params": json.dumps({
                "input_dim": len(STORM_RELATIVE_COLUMNS), "hidden_dim": 6, "lead_hours": leads,
            }),
            "candidate_checkpoint_uri": candidate_uri,
        },
    )

    # fusion: n_models=5, context_dim=len(CONTEXT_FEATURE_NAMES)=10. Derived
    # models must record the real latent_signature of the Group 1 set
    # they were trained against (registry.register's own §5.7 check).
    from anemoi.tracking.registry import GROUP1_MODELS, latent_signature

    signature = latent_signature({name: registry.latest(name).version for name in GROUP1_MODELS})
    _register_real_version(
        "fusion", {"n_models": 5, "context_dim": 10, "hidden_dim": 8, "weight_floor": 0.02,
                    "lead_hours": leads},
        x_shape=None, registry=registry, store=store, tmp_path=tmp_path,
        latent_signature=signature,
    )

    deterministic_fn = build_real_deterministic_fn(track, registry, store, tmp_path)
    plan = CyclePlan(
        target_time=current.valid_time, cycle_start=current.valid_time,
        stages=(), inputs=None, vitals_estimated=False,
    )

    forecast = deterministic_fn(plan, current)

    assert forecast.lead_hours == tuple(leads)
    assert np.all(np.isfinite(forecast.lats))
    assert np.all(np.isfinite(forecast.lons))
    assert np.all(np.isfinite(forecast.winds_kt))
    assert set(forecast.contributors) == {"lstm", "cnn", "transformer", "gnn", "pinn"}
    assert pytest.approx(sum(forecast.contributors.values()), abs=1e-4) == 1.0


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
    with pytest.raises(InferenceCycleError, match="no real Group 1 model") as excinfo:
        deterministic_fn(plan, current)

    # #100: the message must say *why*, per model -- not just that nothing
    # contributed. An empty registry means every model's reason is the
    # same, but the mechanism (not this particular reason) is what matters.
    message = str(excinfo.value)
    for name in ("lstm", "cnn", "transformer", "gnn", "pinn"):
        assert f"{name}: no registered staging/production version" in message


@pytest.mark.torch
def test_deterministic_fn_reports_missing_standardisation_stats_by_name(tmp_path):
    """The exact real #100 scenario: a version with a real, loadable
    checkpoint (real arch_params, real weights) but no x/y standardisation
    stats -- registered before PR #82 -- must be told apart from "no
    registered version" or "no live feature", not lumped into one generic
    failure."""
    from anemoi.inference.scheduler import CyclePlan

    track = make_track("AL011985", n=SEQUENCE_LENGTH + 5)
    current = track.fixes[-1]
    cache_current_fix(tmp_path, track, current)

    registry = ModelRegistry(tmp_path / "registry")
    store = _store()
    _register_real_version(
        "cnn", {
            "in_channels": len(CNN_FIELD_NAMES), "latent_dim": 8,
            "lead_hours": [12, 24, 36, 48, 72, 96, 120],
        },
        x_shape=None,  # the real #100 gap: no standardisation tags at all
        registry=registry, store=store, tmp_path=tmp_path, stage=Stage.STAGING,
    )

    deterministic_fn = build_real_deterministic_fn(track, registry, store, tmp_path)
    plan = CyclePlan(
        target_time=current.valid_time, cycle_start=current.valid_time,
        stages=(), inputs=None, vitals_estimated=False,
    )
    with pytest.raises(InferenceCycleError) as excinfo:
        deterministic_fn(plan, current)

    message = str(excinfo.value)
    assert "cnn: missing x/y standardisation stats (predates #82)" in message
    assert "lstm: no registered staging/production version" in message
