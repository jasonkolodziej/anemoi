"""Forecast-lead steering as a Transformer input (Decision Log 68): the model
option, training, serving's live fetch and gate, and latent extraction."""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from anemoi.data import steering
from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.features import GriddedFields
from anemoi.data.gridded_cache import FetchTask, cache_path, save_cached_fields
from anemoi.data.real_gridded import GRID_NLAT, GRID_NLON
from anemoi.data.sources import Flavor

DIM = steering.STEERING_DIM


def make_track(storm_id: str, season: int, n: int = 26, *, seed: int = 0) -> Track:
    """As tests/test_real_run_transformer.py's: a storm drifting northwest."""
    rng = np.random.default_rng(seed)
    lat, lon = 15.0, -50.0
    start = datetime(season, 8, 1, tzinfo=UTC)
    fixes = []
    for i in range(n):
        lat += float(rng.uniform(0.1, 0.3))
        lon -= float(rng.uniform(0.2, 0.5))
        fixes.append(Fix(
            storm_id=storm_id, valid_time=start + timedelta(hours=6 * i),
            lat=round(lat, 2), lon=round(lon, 2), max_wind_kt=float(50 + 2 * i),
            min_pressure_mb=float(995 - 1.5 * i), quality=TrackQuality.FINAL,
        ))
    return Track(storm_id=storm_id, fixes=tuple(fixes))


def _fields(valid_time, flavor=Flavor.GDAS_FINETUNE, shape=(41, 41)) -> GriddedFields:
    grid = lambda v: np.full(shape, v)  # noqa: E731
    return GriddedFields(
        valid_time=valid_time, flavor=flavor,
        u200=grid(15.0), v200=grid(5.0), u850=grid(10.0), v850=grid(3.0),
        z500=grid(5750.0), rh700=grid(62.0), t700=grid(281.0), mslp=grid(1012.0),
        sst=grid(28.0), ohc=grid(60.0),
    )


def cache_all_fixes(cache_dir, track: Track, flavor: Flavor) -> None:
    for fix in track.fixes:
        task = FetchTask(track.storm_id, fix.valid_time, fix.lat, fix.lon)
        save_cached_fields(cache_path(cache_dir, task), _fields(fix.valid_time, flavor), task)


def cache_steering(cache_dir, track: Track, rng, *, skip=()) -> None:
    for fix in track.fixes:
        if fix.valid_time in skip:
            continue
        task = FetchTask(track.storm_id, fix.valid_time, fix.lat, fix.lon)
        feats = rng.normal(size=(len(steering.STEERING_LEADS_H), len(steering.FEATURE_NAMES)))
        steering.save_steering(
            steering.steering_path(cache_dir, track.storm_id, fix.valid_time),
            feats.astype(np.float32), task,
        )


def _uniform(u: float, v: float) -> steering.LeadFlow:
    full = lambda x: np.full((GRID_NLAT, GRID_NLON), x, dtype=np.float32)  # noqa: E731
    return steering.LeadFlow(full(u), full(v), full(0.0), full(0.0))


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


# --------------------------------------------------------------------------- #
# Inputs (no torch)
# --------------------------------------------------------------------------- #


def test_transformer_input_appends_steering_after_the_basin_channels():
    from anemoi.training.real_run_transformer import (
        GRID_SIZE,
        TRANSFORMER_FIELD_NAMES,
        transformer_input,
    )

    fields = _fields(datetime(2022, 8, 1, tzinfo=UTC))
    plain = transformer_input(fields, "AL012022", ("AL", "EP"))
    vec = np.arange(DIM, dtype=np.float32)
    x = transformer_input(fields, "AL012022", ("AL", "EP"), steering=vec)
    n = len(TRANSFORMER_FIELD_NAMES) + 2
    assert plain.shape == (n, *GRID_SIZE)
    assert x.shape == (n + DIM, *GRID_SIZE)
    assert np.array_equal(x[:n], plain)
    assert np.array_equal(x[n:, 3, 5], vec)  # one constant channel per feature
    assert np.all(x[n + 7] == 7.0)


def test_n_steering_of_reads_arch_params_and_defaults_to_zero():
    from anemoi.training.real_run_transformer import n_steering_of

    assert n_steering_of(None) == 0
    assert n_steering_of({"d_model": 16}) == 0
    assert n_steering_of({"n_steering": DIM}) == DIM


def test_steering_tag_only_for_a_version_that_reads_steering():
    from anemoi.tracking.experiment_tracking import STEERING_INPUTS_TAG, steering_input_tags

    assert steering_input_tags(SimpleNamespace(arch_params={"d_model": 16})) == {}
    assert steering_input_tags(None) == {}
    tags = steering_input_tags(SimpleNamespace(arch_params={"n_steering": DIM},
                                               steering_inputs=steering.steering_meta()))
    assert json.loads(tags[STEERING_INPUTS_TAG]) == steering.steering_meta()
    with pytest.raises(ValueError, match="record the settings"):
        steering_input_tags(SimpleNamespace(arch_params={"n_steering": DIM},
                                            steering_inputs=None))


def test_cache_meta_is_the_same_settings_the_tag_records(tmp_path):
    steering.write_meta(tmp_path)
    assert json.loads((tmp_path / steering.CACHE_META_NAME).read_text()) == (
        steering.steering_meta())
    steering.require_meta(tmp_path)


def test_a_cache_without_meta_or_with_other_settings_is_refused(tmp_path):
    with pytest.raises(ValueError, match="no readable"):
        steering.require_meta(tmp_path)
    (tmp_path / steering.CACHE_META_NAME).write_text("{not json")
    with pytest.raises(ValueError, match="no readable"):
        steering.require_meta(tmp_path)
    other = {**steering.steering_meta(), "beta_drift_ms": [0.0, 0.0]}
    (tmp_path / steering.CACHE_META_NAME).write_text(json.dumps(other))
    with pytest.raises(ValueError, match="other settings"):
        steering.require_meta(tmp_path)


def test_the_settings_digest_changes_with_any_setting():
    base = steering.steering_meta_digest()
    assert base == steering.steering_meta_digest(steering.steering_meta())
    assert base != steering.steering_meta_digest(
        {**steering.steering_meta(), "disc_radius_deg": 4.0})


# --------------------------------------------------------------------------- #
# Live fetch
# --------------------------------------------------------------------------- #


def test_live_steering_matches_the_training_features_and_is_cached(tmp_path):
    from anemoi.training import real_inference_live as live

    live._FLOW_MEMO.clear()
    track = make_track("AL012022", 2022, n=4)
    current = track.fixes[-1]
    calls: list = []

    def fetcher(valid_time, lead):
        calls.append((valid_time, lead))
        return _uniform(5.0, 1.0)

    vec = live.fetch_live_steering(track, current, tmp_path, flow_fetcher=fetcher)
    expected = steering.steering_features(
        [_uniform(5.0, 1.0)] * len(steering.STEERING_LEADS_H), current.lat, current.lon,
    ).reshape(-1)
    assert vec.shape == (DIM,)
    assert np.allclose(vec, expected)
    assert [lead for _, lead in calls] == list(steering.STEERING_LEADS_H)
    path = live.live_steering_path(tmp_path, track.storm_id, current)
    assert path.exists()
    assert steering.steering_meta_digest() in path.parts  # other settings: another directory

    # a second storm in the same cycle reuses the fetched flows
    other = make_track("AL022022", 2022, n=4, seed=3)  # same valid times, other positions
    assert other.fixes[-1].valid_time == current.valid_time
    live.fetch_live_steering(other, other.fixes[-1], tmp_path, flow_fetcher=fetcher)
    assert len(calls) == len(steering.STEERING_LEADS_H)

    # cached: no fetch at all
    live._FLOW_MEMO.clear()
    again = live.fetch_live_steering(
        track, current, tmp_path, flow_fetcher=lambda *a: pytest.fail("fetched again"))
    assert np.array_equal(again, vec)


def test_live_steering_is_none_when_any_lead_is_missing(tmp_path):
    from anemoi.training import real_inference_live as live

    live._FLOW_MEMO.clear()
    track = make_track("AL012022", 2022, n=4)

    def fetcher(valid_time, lead):
        if lead == 48:
            raise OSError("f054 not published yet")
        return _uniform(5.0, 1.0)

    assert live.fetch_live_steering(track, track.fixes[-1], tmp_path,
                                    flow_fetcher=fetcher) is None
    assert not live.live_steering_path(tmp_path, track.storm_id, track.fixes[-1]).exists()


def test_live_steering_is_none_before_the_gfs_archive(tmp_path):
    from anemoi.training import real_inference_live as live

    track = make_track("AL011985", 1985, n=4)
    assert live.fetch_live_steering(
        track, track.fixes[-1], tmp_path,
        flow_fetcher=lambda *a: pytest.fail("nothing to fetch before 2021")) is None


# --------------------------------------------------------------------------- #
# Serving gate
# --------------------------------------------------------------------------- #


def _version(arch: dict, *, tag: dict | None | str = "match"):
    from anemoi.tracking.experiment_tracking import STEERING_INPUTS_TAG

    tags = {"arch_params": json.dumps(arch)}
    if tag == "match":
        tags[STEERING_INPUTS_TAG] = json.dumps(steering.steering_meta())
    elif tag is not None:
        tags[STEERING_INPUTS_TAG] = json.dumps(tag)
    return SimpleNamespace(tags=tags)


def test_serving_gate_only_applies_to_a_version_that_reads_steering(tmp_path):
    from anemoi.training.real_inference_cycle import _live_steering_for

    track = make_track("AL012022", 2022, n=4)
    current = track.fixes[-1]
    fail = lambda *a: pytest.fail("fetched for a model that doesn't read steering")  # noqa: E731
    assert _live_steering_for("lstm", _version({"n_steering": DIM}), track, current,
                              tmp_path, fail) == (None, None)
    for name in ("transformer", "cnn", "gnn", "pinn"):
        assert _live_steering_for(name, _version({"d_model": 16}, tag=None), track,
                                  current, tmp_path, fail) == (None, None)
        vec = np.ones(DIM, dtype=np.float32)
        got, reason = _live_steering_for(name, _version({"n_steering": DIM}), track, current,
                                         tmp_path, lambda *a, vec=vec: vec)
        assert reason is None and got is vec


def test_serving_gate_feeds_the_vector_or_skips_with_a_reason(tmp_path):
    from anemoi.training.real_inference_cycle import _live_steering_for

    track = make_track("AL012022", 2022, n=4)
    current = track.fixes[-1]
    vec = np.ones(DIM, dtype=np.float32)
    v = _version({"n_steering": DIM})

    got, reason = _live_steering_for("transformer", v, track, current, tmp_path,
                                     lambda *a: vec)
    assert reason is None and np.array_equal(got, vec)

    got, reason = _live_steering_for("transformer", v, track, current, tmp_path,
                                     lambda *a: None)
    assert got is None and "couldn't be fetched" in reason

    got, reason = _live_steering_for("transformer", v, track, current, tmp_path,
                                     lambda *a: np.ones(DIM - 6))
    assert got is None and reason

    other = {**steering.steering_meta(), "disc_radius_deg": 3.0}
    for bad in (_version({"n_steering": DIM}, tag=other), _version({"n_steering": DIM}, tag=None)):
        got, reason = _live_steering_for(
            "transformer", bad, track, current, tmp_path,
            lambda *a: pytest.fail("fetched for a version trained on other settings"))
        assert got is None and "other settings" in reason


# --------------------------------------------------------------------------- #
# Model and training (torch)
# --------------------------------------------------------------------------- #


@pytest.mark.torch
def test_builder_without_steering_keeps_the_old_layout():
    pytest.importorskip("torch")
    from anemoi.models.transformer import build_transformer

    plain, spec = build_transformer(n_variables=4, grid_size=(8, 8), d_model=16, n_heads=2,
                                    n_layers=1, dropout=0.0)
    keys = set(plain.state_dict())
    assert "patch.weight" in keys and not any(k.startswith("patch.extra") for k in keys)
    assert spec.input_dim == 4
    steer, spec = build_transformer(n_variables=4, grid_size=(8, 8), d_model=16, n_heads=2,
                                    n_layers=1, dropout=0.0, n_steering=5)
    keys = set(steer.state_dict())
    assert {"patch.base.weight", "patch.extra.weight"} <= keys
    assert "patch.extra.bias" not in keys
    assert spec.input_dim == 9


@pytest.mark.torch
def test_a_zero_steering_conv_computes_the_plain_model():
    torch = pytest.importorskip("torch")
    from anemoi.models.transformer import build_transformer

    kw = dict(n_variables=4, grid_size=(8, 8), d_model=16, n_heads=2, n_layers=1, dropout=0.0)
    torch.manual_seed(0)
    plain, _ = build_transformer(**kw)
    steer, _ = build_transformer(**kw, n_steering=5)
    state = {("patch.base." + k[len("patch."):] if k.startswith("patch.") else k): v
             for k, v in plain.state_dict().items()}
    steer.load_state_dict({**steer.state_dict(), **state})
    plain.eval()
    steer.eval()
    x = torch.randn(2, 4, 8, 8)
    assert torch.allclose(plain(x)[0], steer(torch.cat([x, 50 * torch.randn(2, 5, 8, 8)], 1))[0],
                          atol=1e-5)


def _curriculum_tracks():
    return [
        make_track("AL011985", season=1985, n=26, seed=0),
        make_track("AL012021", season=2021, n=26, seed=1),
        make_track("AL022021", season=2021, n=26, seed=2),
        make_track("AL012022", season=2022, n=26, seed=7),
        make_track("AL012023", season=2023, n=26, seed=3),
    ]


@pytest.mark.torch
def test_curriculum_with_steering_trains_the_conv_in_stage_b_only(tmp_path):
    torch = pytest.importorskip("torch")
    from anemoi.models.transformer import build_transformer
    from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config
    from anemoi.tracking.experiment_tracking import arch_params_tag
    from anemoi.training.real_run_transformer import run_transformer_curriculum

    era5, gdas, steer = tmp_path / "era5", tmp_path / "gdas", tmp_path / "steer"
    rng = np.random.default_rng(0)
    tracks = _curriculum_tracks()
    for t in tracks:
        cache_all_fixes(era5, t, Flavor.ERA5_PRETRAIN)
        cache_all_fixes(gdas, t, Flavor.GDAS_FINETUNE)
        cache_steering(steer, t, rng)
    steering.write_meta(steer)
    client = _FakeS3Client()
    store = CheckpointStore(S3Config(
        endpoint_url="https://example.r2.cloudflarestorage.com", bucket="anemoi-test",
        access_key_id="key", secret_access_key="secret"), client=client)

    run, _metrics, artifacts = run_transformer_curriculum(
        tracks, store, era5, gdas, seed=42, n_augment=1, d_model=16, dropout=0.0,
        streaming=True, batch_size=4, steering_cache_dir=steer,
        curriculum_kwargs={"a": {"epochs": 1}, "b": {"epochs": 2, "learning_rate": 1e-2}},
    )
    assert run.complete
    assert artifacts.arch_params["n_steering"] == DIM
    assert artifacts.steering_inputs == steering.steering_meta()

    def extra_of(stage):
        key = next(k for k in client.objects if f"/transformer/{stage}/" in k)
        state = torch.load(io.BytesIO(client.objects[key]), weights_only=True)
        return state["patch.extra.weight"]

    assert extra_of("A").abs().sum() == 0  # ERA5 years: zeros in, no gradient
    assert extra_of("B").abs().sum() > 0

    # what serving rebuilds from the registry tag loads these weights
    params = json.loads(arch_params_tag(artifacts))
    rebuilt, _ = build_transformer(**{k: tuple(v) if isinstance(v, list) else v
                                      for k, v in params.items()})
    rebuilt.load_state_dict(artifacts.model.state_dict())


@pytest.mark.torch
def test_curriculum_without_steering_records_no_n_steering(tmp_path):
    pytest.importorskip("torch")
    from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config
    from anemoi.training.real_run_transformer import run_transformer_curriculum

    era5, gdas = tmp_path / "era5", tmp_path / "gdas"
    tracks = _curriculum_tracks()
    for t in tracks:
        cache_all_fixes(era5, t, Flavor.ERA5_PRETRAIN)
        cache_all_fixes(gdas, t, Flavor.GDAS_FINETUNE)
    store = CheckpointStore(S3Config(
        endpoint_url="https://example.r2.cloudflarestorage.com", bucket="anemoi-test",
        access_key_id="key", secret_access_key="secret"), client=_FakeS3Client())
    _run, _m, artifacts = run_transformer_curriculum(
        tracks, store, era5, gdas, seed=42, n_augment=1, d_model=16, dropout=0.0,
        streaming=True, batch_size=4,
        curriculum_kwargs={"a": {"epochs": 1}, "b": {"epochs": 1}},
    )
    assert "n_steering" not in artifacts.arch_params


def test_curriculum_refuses_steering_without_streaming_or_without_the_cache_meta(tmp_path):
    pytest.importorskip("torch")
    from anemoi.training.real_run_transformer import run_transformer_curriculum

    with pytest.raises(ValueError, match="streaming"):
        run_transformer_curriculum(_curriculum_tracks(), None, tmp_path, tmp_path,
                                   steering_cache_dir=tmp_path)
    with pytest.raises(ValueError, match="no readable"):
        run_transformer_curriculum(_curriculum_tracks(), None, tmp_path, tmp_path,
                                   steering_cache_dir=tmp_path, streaming=True)


# --------------------------------------------------------------------------- #
# Latents
# --------------------------------------------------------------------------- #


def test_latents_need_a_steering_cache_for_a_model_that_reads_steering(tmp_path, monkeypatch):
    from anemoi.training.real_latents import STEERING_CACHE_ENV, _steering_source

    monkeypatch.delenv(STEERING_CACHE_ENV, raising=False)
    plain = {m: SimpleNamespace(arch_params={"d_model": 16})
             for m in ("lstm", "cnn", "transformer", "gnn", "pinn")}
    assert _steering_source(plain, None) == (None, frozenset())
    meta = steering.steering_meta()
    reads = SimpleNamespace(arch_params={"n_steering": DIM}, steering_inputs=meta)
    steer = {**plain, "transformer": reads, "pinn": reads}
    with pytest.raises(ValueError, match=STEERING_CACHE_ENV):
        _steering_source(steer, None)
    for recorded in (None, {**meta, "disc_radius_deg": 3.0}):
        other = {**steer, "pinn": SimpleNamespace(arch_params={"n_steering": DIM},
                                                  steering_inputs=recorded)}
        with pytest.raises(ValueError, match="pinn version .*other settings"):
            _steering_source(other, tmp_path)

    track = make_track("AL012022", 2022, n=3)
    cache_steering(tmp_path, track, np.random.default_rng(0), skip={track.fixes[1].valid_time})
    monkeypatch.setenv(STEERING_CACHE_ENV, str(tmp_path))
    with pytest.raises(ValueError, match="no readable"):  # a cache with no meta
        _steering_source(steer, None)
    steering.write_meta(tmp_path)
    source, readers = _steering_source(steer, None)
    assert readers == {"transformer", "pinn"}
    assert source(track.storm_id, track.fixes[0].valid_time).shape == (DIM,)
    assert source(track.storm_id, track.fixes[1].valid_time) is None


# --------------------------------------------------------------------------- #
# CNN, GNN and PINN (Decision Log 68, carried over from the Transformer)
# --------------------------------------------------------------------------- #


def test_gridded_inputs_append_steering_after_the_basin_inputs():
    from anemoi.training.real_run_cnn import CNN_FIELD_NAMES, cnn_input
    from anemoi.training.real_run_gnn import build_mesh_topology, gnn_input
    from anemoi.training.real_run_pinn import pinn_environment

    fields = _fields(datetime(2022, 8, 1, tzinfo=UTC))
    vec = np.arange(DIM, dtype=np.float32)
    basins = ("AL", "EP")

    plain = cnn_input(fields, "AL012022", basins)
    x = cnn_input(fields, "AL012022", basins, steering=vec)
    n = len(CNN_FIELD_NAMES) + 2
    assert plain.shape[0] == n and x.shape == (n + DIM, *plain.shape[1:])
    assert np.array_equal(x[:n], plain) and np.all(x[n + 7] == 7.0)

    topo = build_mesh_topology(fields.shape)
    plain = gnn_input(fields, topo, "AL012022", basins)
    x = gnn_input(fields, topo, "AL012022", basins, steering=vec)
    assert x.shape == (plain.shape[0], plain.shape[1] + DIM)
    assert np.array_equal(x[:, :plain.shape[1]], plain)
    assert np.array_equal(x[3, plain.shape[1]:], vec)  # the same vector on every node

    plain = pinn_environment(fields, "AL012022", basins)
    x = pinn_environment(fields, "AL012022", basins, steering=vec)
    assert np.array_equal(x[:plain.size], plain) and np.array_equal(x[plain.size:], vec)


def _builders():
    from anemoi.models.cnn import build_cnn
    from anemoi.models.gnn import build_gnn
    from anemoi.models.pinn import build_pinn

    return {
        "cnn": (lambda n: build_cnn(in_channels=4, base_width=8, depth=2, latent_dim=16,
                                    n_steering=n)),
        "gnn": (lambda n: build_gnn(node_features=4, hidden_dim=16, n_layers=1, n_steering=n)),
        "pinn": (lambda n: build_pinn(input_dim=4, hidden_dim=16, n_layers=2, n_steering=n)),
    }


def _forward(name, model, x, steer, torch):
    """One forward of ``model`` on base input ``x`` plus ``steer`` (or
    without it when ``steer`` is None)."""
    if name == "cnn":
        inp = x if steer is None else torch.cat(
            [x, steer[:, :, None, None].expand(-1, -1, *x.shape[2:])], 1)
        return model(inp)
    if name == "gnn":
        n_nodes = x.shape[0]
        inp = x if steer is None else torch.cat([x, steer.expand(n_nodes, -1)], 1)
        edge_index = torch.tensor([[0, 1, 2], [1, 2, 0]])
        return model(inp, edge_index, torch.zeros(3, 3), center_index=0)
    env = x if steer is None else torch.cat([x, steer], 1)
    # The trunk's output, not the forecast: the correction head starts at
    # zero, so the forecast is the candidate whatever the trunk computes.
    return model.encode(env, torch.randn(1, 7, 3, generator=torch.Generator().manual_seed(1)))


@pytest.mark.torch
@pytest.mark.parametrize("name", ["cnn", "gnn", "pinn"])
def test_a_zero_steering_path_computes_the_plain_model(name):
    torch = pytest.importorskip("torch")
    from anemoi.training.steering_input import STEERING_PARAMS

    build = _builders()[name]
    torch.manual_seed(0)
    plain, plain_spec = build(0)
    steer_model, spec = build(5)
    assert spec.input_dim == plain_spec.input_dim + 5
    keys = set(steer_model.state_dict())
    extra = {k for k in keys if k.startswith(STEERING_PARAMS[name])}
    assert extra and all(k.endswith(".weight") for k in extra)  # bias-free
    assert not any(".extra." in k for k in plain.state_dict())  # old layout unchanged

    # the steering model with the plain one's weights, and its zero path
    renamed = {}
    for k, v in plain.state_dict().items():
        for prefix in STEERING_PARAMS[name]:
            owner = prefix[: -len("extra.")]
            if k.startswith(owner):
                k = owner + "base." + k[len(owner):]
        renamed[k] = v
    steer_model.load_state_dict({**steer_model.state_dict(), **renamed})
    plain.eval()
    steer_model.eval()
    x = torch.randn(*{"cnn": (1, 4, 8, 8), "gnn": (3, 4), "pinn": (1, 4)}[name])
    torch.testing.assert_close(
        _forward(name, plain, x, None, torch),
        _forward(name, steer_model, x, 50 * torch.randn(1, 5), torch), atol=1e-5, rtol=0,
    )


_CURRICULA = {
    "cnn": ("real_run_cnn", "run_cnn_curriculum", {"latent_dim": 16},
            ("blocks.0.conv1.extra.weight", "blocks.0.skip.extra.weight"),
            "blocks.0.conv1.base.weight"),
    "gnn": ("real_run_gnn", "run_gnn_curriculum", {"hidden_dim": 16},
            ("embed.extra.weight",), "embed.base.weight"),
    "pinn": ("real_run_pinn", "run_pinn_curriculum", {"hidden_dim": 16},
             ("trunk.0.extra.weight",), "trunk.0.base.weight"),
}


@pytest.mark.torch
@pytest.mark.parametrize("name", ["cnn", "gnn", "pinn"])
def test_curriculum_trains_the_steering_path_in_stage_b_only(tmp_path, name):
    torch = pytest.importorskip("torch")
    import importlib

    from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config
    from anemoi.tracking.experiment_tracking import arch_params_tag
    from anemoi.training.real_inference import _builder

    module, runner, kwargs, extra_keys, frozen_key = _CURRICULA[name]
    run_curriculum = getattr(importlib.import_module(f"anemoi.training.{module}"), runner)
    era5, gdas, steer = tmp_path / "era5", tmp_path / "gdas", tmp_path / "steer"
    rng = np.random.default_rng(0)
    tracks = _curriculum_tracks()
    for t in tracks:
        cache_all_fixes(era5, t, Flavor.ERA5_PRETRAIN)
        cache_all_fixes(gdas, t, Flavor.GDAS_FINETUNE)
        cache_steering(steer, t, rng)
    steering.write_meta(steer)
    client = _FakeS3Client()
    store = CheckpointStore(S3Config(
        endpoint_url="https://example.r2.cloudflarestorage.com", bucket="anemoi-test",
        access_key_id="key", secret_access_key="secret"), client=client)

    run, _metrics, artifacts = run_curriculum(
        tracks, store, era5, gdas, seed=42, n_augment=1, streaming=True, batch_size=4,
        steering_cache_dir=steer, **kwargs,
        curriculum_kwargs={"a": {"epochs": 1}, "b": {"epochs": 2, "learning_rate": 1e-2}},
    )
    assert run.complete
    assert artifacts.arch_params["n_steering"] == DIM
    assert artifacts.steering_inputs == steering.steering_meta()

    def state_of(stage):
        key = next(k for k in client.objects
                   if f"/{name}/{stage}/" in k and "candidate" not in k)
        return torch.load(io.BytesIO(client.objects[key]), weights_only=True)

    a, b = state_of("A"), state_of("B")
    for key in extra_keys:
        assert a[key].abs().sum() == 0  # ERA5 years: zeros in, no gradient
        assert b[key].abs().sum() > 0
    assert torch.equal(a[frozen_key], b[frozen_key])  # Stage B's freezing still holds

    # what serving rebuilds from the registry tag loads these weights
    params = json.loads(arch_params_tag(artifacts))
    rebuilt, _ = _builder(name)(**{k: tuple(v) if isinstance(v, list) else v
                                   for k, v in params.items()})
    rebuilt.load_state_dict(artifacts.model.state_dict())


def test_steering_stage_kwargs_feed_zeros_on_era5_and_the_cache_on_gdas(tmp_path):
    from anemoi.training.curriculum import stage_a, stage_b
    from anemoi.training.steering_input import STEERING_PARAMS, steering_stage_kwargs

    assert steering_stage_kwargs("cnn", stage_b(), tmp_path, 0) == {}
    a = steering_stage_kwargs("gnn", stage_a(), tmp_path, DIM)
    assert set(a) == {"extra_x"} and not a["extra_x"](None).any()
    b = steering_stage_kwargs("gnn", stage_b(), tmp_path, DIM)
    assert b["trainable"] == STEERING_PARAMS["gnn"]
    track = make_track("AL012022", 2022, n=2)
    cache_steering(tmp_path, track, np.random.default_rng(0), skip={track.fixes[1].valid_time})
    sw = SimpleNamespace(storm_id=track.storm_id, current=track.fixes[0])
    assert b["extra_x"](sw).shape == (DIM,)
    sw = SimpleNamespace(storm_id=track.storm_id, current=track.fixes[1])
    assert b["extra_x"](sw) is None


def test_unfreeze_refuses_a_steering_path_that_isnt_there():
    torch = pytest.importorskip("torch")
    from anemoi.training.steering_input import unfreeze

    model = torch.nn.Linear(2, 2)
    with pytest.raises(ValueError, match="no parameter"):
        unfreeze(model, ("embed.extra.",))
    unfreeze(model, ())  # nothing asked, nothing checked


def test_one_forecast_call_fetches_steering_once_failures_included(tmp_path):
    from anemoi.training.real_inference_cycle import shared_steering

    track = make_track("AL012022", 2022, n=4)
    calls = []

    def fetch(track_, current_, cache_dir_):
        calls.append(current_.valid_time)
        return None  # e.g. a lead not published yet

    once = shared_steering(fetch)
    for _ in range(4):  # four models that read steering
        assert once(track, track.fixes[-1], tmp_path) is None
    assert calls == [track.fixes[-1].valid_time]
    once(track, track.fixes[-2], tmp_path)  # another time is its own fetch
    assert len(calls) == 2
    shared_steering(fetch)(track, track.fixes[-1], tmp_path)  # the next call retries
    assert len(calls) == 3
