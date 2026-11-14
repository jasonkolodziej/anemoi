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
    tags = steering_input_tags(SimpleNamespace(arch_params={"n_steering": DIM}))
    assert json.loads(tags[STEERING_INPUTS_TAG]) == steering.steering_meta()


def test_cache_meta_is_the_same_settings_the_tag_records(tmp_path):
    steering.write_meta(tmp_path)
    assert json.loads((tmp_path / steering.CACHE_META_NAME).read_text()) == (
        steering.steering_meta())


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
    assert live.live_steering_path(tmp_path, track.storm_id, current).exists()

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


def test_serving_gate_only_applies_to_a_steering_transformer(tmp_path):
    from anemoi.training.real_inference_cycle import _live_steering_for

    track = make_track("AL012022", 2022, n=4)
    current = track.fixes[-1]
    fail = lambda *a: pytest.fail("fetched for a model that doesn't read steering")  # noqa: E731
    assert _live_steering_for("cnn", _version({"n_steering": DIM}), track, current,
                              tmp_path, fail) == (None, None)
    assert _live_steering_for("transformer", _version({"d_model": 16}, tag=None), track,
                              current, tmp_path, fail) == (None, None)


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


def test_curriculum_refuses_steering_without_streaming(tmp_path):
    pytest.importorskip("torch")
    from anemoi.training.real_run_transformer import run_transformer_curriculum

    with pytest.raises(ValueError, match="streaming"):
        run_transformer_curriculum(_curriculum_tracks(), None, tmp_path, tmp_path,
                                   steering_cache_dir=tmp_path)


# --------------------------------------------------------------------------- #
# Latents
# --------------------------------------------------------------------------- #


def test_latents_need_a_steering_cache_for_a_steering_transformer(tmp_path, monkeypatch):
    from anemoi.training.real_latents import STEERING_CACHE_ENV, _steering_source

    monkeypatch.delenv(STEERING_CACHE_ENV, raising=False)
    plain = {"transformer": SimpleNamespace(arch_params={"d_model": 16})}
    assert _steering_source(plain, None) is None
    steer = {"transformer": SimpleNamespace(arch_params={"n_steering": DIM})}
    with pytest.raises(ValueError, match=STEERING_CACHE_ENV):
        _steering_source(steer, None)

    track = make_track("AL012022", 2022, n=3)
    cache_steering(tmp_path, track, np.random.default_rng(0), skip={track.fixes[1].valid_time})
    monkeypatch.setenv(STEERING_CACHE_ENV, str(tmp_path))
    source = _steering_source(steer, None)
    assert source(track.storm_id, track.fixes[0].valid_time).shape == (DIM,)
    assert source(track.storm_id, track.fixes[1].valid_time) is None
