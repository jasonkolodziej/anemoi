"""Real Stage A/B curriculum run for the GNN baseline (#22)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.features import GriddedFields
from anemoi.data.gridded_cache import FetchTask, cache_path, save_cached_fields
from anemoi.data.sources import Flavor
from anemoi.training.real_run_gnn import (
    EDGE_FEATURES,
    NODE_FEATURES,
    batch_graph,
    build_gnn_samples,
    build_mesh_topology,
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


# --- build_mesh_topology -----------------------------------------------------


def test_mesh_topology_node_and_edge_shapes():
    topo = build_mesh_topology((41, 41), stride=4)
    nh = nw = len(range(0, 41, 4))
    assert topo.n_nodes == nh * nw
    assert topo.edge_index.shape[0] == 2
    assert topo.edge_attr.shape == (topo.edge_index.shape[1], EDGE_FEATURES)
    # every edge index must reference a real node
    assert topo.edge_index.max() < topo.n_nodes
    assert topo.edge_index.min() >= 0


def test_mesh_topology_center_index_is_the_middle_node():
    topo = build_mesh_topology((41, 41), stride=4)
    nh = nw = len(range(0, 41, 4))
    assert topo.center_index == (nh // 2) * nw + (nw // 2)


def test_mesh_topology_edges_are_bidirectional():
    topo = build_mesh_topology((9, 9), stride=4)
    pairs = set(zip(topo.edge_index[0].tolist(), topo.edge_index[1].tolist(), strict=True))
    for a, b in pairs:
        assert (b, a) in pairs


# --- build_gnn_samples --------------------------------------------------------


def test_build_gnn_samples_node_feature_width_matches_default(tmp_path):
    track = make_track("AL011985", season=1985, n=26)
    cache_all_fixes(tmp_path, track, Flavor.ERA5_PRETRAIN)
    rng = np.random.default_rng(1)

    samples = build_gnn_samples([track], tmp_path, rng, n_augment=1)

    assert len(samples) > 0
    assert samples.x.shape[-1] == NODE_FEATURES == 12
    assert samples.topology is not None
    assert samples.x.shape[1] == samples.topology.n_nodes


def test_build_gnn_samples_skips_fixes_with_no_cached_file(tmp_path):
    track = make_track("AL011985", season=1985, n=26)
    for i, fix in enumerate(track.fixes):
        if i % 2 == 0:
            task = _task_for(track, fix)
            fields = make_fields(fix.valid_time, Flavor.ERA5_PRETRAIN)
            save_cached_fields(cache_path(tmp_path, task), fields, task)
    rng = np.random.default_rng(2)

    samples = build_gnn_samples([track], tmp_path, rng, n_augment=1)  # must not raise
    assert 0 <= len(samples) <= len(track.fixes)


def test_build_gnn_samples_empty_when_nothing_cached(tmp_path):
    track = make_track("AL011985", season=1985, n=26)
    rng = np.random.default_rng(3)
    samples = build_gnn_samples([track], tmp_path, rng, n_augment=1)
    assert len(samples) == 0
    assert samples.topology is None


def test_build_gnn_samples_rejects_ragged_cached_shapes(tmp_path):
    track = make_track("AL011985", season=1985, n=10)
    for i, fix in enumerate(track.fixes):
        task = _task_for(track, fix)
        shape = (41, 41) if i < 5 else (21, 21)
        fields = make_fields(fix.valid_time, Flavor.ERA5_PRETRAIN, shape)
        save_cached_fields(cache_path(tmp_path, task), fields, task)
    rng = np.random.default_rng(4)
    with pytest.raises(ValueError, match="ragged"):
        build_gnn_samples([track], tmp_path, rng, n_augment=1)


# --- batch_graph ---------------------------------------------------------------


def test_batch_graph_offsets_edges_per_sample_block():
    topo = build_mesh_topology((9, 9), stride=4)
    x = np.zeros((3, topo.n_nodes, NODE_FEATURES), dtype=np.float32)
    x_flat, edge_index, edge_attr, center_indices = batch_graph(x, topo)

    assert x_flat.shape == (3 * topo.n_nodes, NODE_FEATURES)
    assert edge_index.shape == (2, 3 * topo.edge_index.shape[1])
    assert edge_attr.shape == (3 * topo.edge_attr.shape[0], EDGE_FEATURES)
    # no edge should reference a node outside its own sample's block
    n_nodes = topo.n_nodes
    n_edges_per_graph = topo.edge_index.shape[1]
    for i in range(3):
        lo, hi = i * n_edges_per_graph, (i + 1) * n_edges_per_graph
        block_edges = edge_index[:, lo:hi]
        assert block_edges.min() >= i * n_nodes
        assert block_edges.max() < (i + 1) * n_nodes
    assert list(center_indices) == [
        0 * n_nodes + topo.center_index,
        1 * n_nodes + topo.center_index,
        2 * n_nodes + topo.center_index,
    ]


# --- torch-dependent -------------------------------------------------------

torch_installed = pytest.importorskip("torch", reason="needs the torch extra")


@pytest.mark.torch
def test_train_gnn_stage_runs_and_produces_val_metrics(tmp_path):
    from anemoi.models.gnn import build_gnn
    from anemoi.training.curriculum import stage_a
    from anemoi.training.real_run_gnn import train_gnn_stage

    train_tracks = [make_track("AL011985", season=1985, n=26, seed=0)]
    val_tracks = [make_track("AL012020", season=2020, n=26, seed=1)]
    for t in train_tracks + val_tracks:
        cache_all_fixes(tmp_path, t, Flavor.ERA5_PRETRAIN)

    leads = (12, 24, 36, 48, 72, 96, 120)
    model, _spec = build_gnn(
        node_features=NODE_FEATURES, edge_features=EDGE_FEATURES,
        hidden_dim=16, n_layers=2, lead_hours=leads,
    )
    stage = stage_a(epochs=2, learning_rate=1e-2)
    rng = np.random.default_rng(5)

    trained_model, train_loss, val_loss, val_metrics = train_gnn_stage(
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
def test_run_gnn_curriculum_completes_both_stages(tmp_path):
    from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config
    from anemoi.training.real_run_gnn import run_gnn_curriculum

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

    run, val_metrics = run_gnn_curriculum(
        tracks, store, era5_dir, gdas_dir, seed=42, n_augment=1, hidden_dim=16,
    )

    assert run.complete
    assert [r.stage_name for r in run.results] == ["A", "B"]
    assert run.results[-1].flavor is Flavor.GDAS_FINETUNE
    for result in run.results:
        assert result.checkpoint_uri.startswith("s3://anemoi-test/checkpoints/gnn/")
    assert "track_error_12h_nm" in val_metrics.values
