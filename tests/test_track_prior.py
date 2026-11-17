"""AVNI's track as a prior the gridded models correct (training.track_prior)."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import numpy as np
import pytest

from anemoi.data.atcf import Adeck, AdeckPoint
from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.sources import Flavor
from anemoi.geo import haversine_nm
from anemoi.models.base import DEFAULT_LEADS, NON_BUILD_ARCH_PARAMS, build_kwargs
from anemoi.training import track_prior as tp

T0 = datetime(2022, 9, 1, 12, tzinfo=UTC)


def _adeck(storm_id: str, points: dict) -> Adeck:
    return Adeck(
        storm_id=storm_id, points=points, n_rows=len(points), n_skipped=0,
        n_other_storm=0, n_basin_mismatch=0, conflicts={},
    )


def _persistence() -> np.ndarray:
    steps = np.array([h // 6 for h in DEFAULT_LEADS], dtype=float)
    return np.stack([10.0 * steps, 5.0 * steps, np.full(len(steps), 50.0)], axis=1)


def test_prior_is_avni_displacement_with_persistence_where_avni_stops():
    # AVNI 1 deg north at 12 h, 1 deg east at 24 h, nothing after.
    points = {
        ("AVNI", T0, 12): AdeckPoint(lat=21.0, lon=-60.0, max_wind_kt=55.0),
        ("AVNI", T0, 24): AdeckPoint(lat=20.0, lon=-59.0, max_wind_kt=60.0),
    }
    prior = tp.prior_from_adeck(_adeck("AL012022", points), T0, 20.0, -60.0, _persistence())

    assert prior.shape == (len(DEFAULT_LEADS), 3)
    assert prior[0, 0] == pytest.approx(0.0, abs=1e-6)
    assert prior[0, 1] == pytest.approx(haversine_nm(20.0, -60.0, 21.0, -60.0), rel=1e-6)
    assert prior[1, 0] == pytest.approx(haversine_nm(20.0, -60.0, 20.0, -59.0), rel=1e-3)
    assert abs(prior[1, 1]) < 1.0
    np.testing.assert_allclose(prior[2:, :2], _persistence()[2:, :2])
    np.testing.assert_array_equal(prior[:, 2], 0.0)  # intensity stays the model's own


def test_no_prior_without_avni_at_the_first_lead_or_the_cycle():
    later = {("AVNI", T0, 24): AdeckPoint(lat=20.0, lon=-59.0, max_wind_kt=60.0)}
    other_cycle = {("AVNI", T0 - timedelta(hours=6), 12): AdeckPoint(21.0, -60.0, 50.0)}
    no_position = {("AVNI", T0, 12): AdeckPoint(lat=None, lon=None, max_wind_kt=50.0)}
    for points in (later, other_cycle, no_position):
        assert tp.prior_from_adeck(
            _adeck("AL012022", points), T0, 20.0, -60.0, _persistence(),
        ) is None
    assert tp.prior_from_adeck(None, T0, 20.0, -60.0, _persistence()) is None


def _window(storm_id: str, t: datetime, y: np.ndarray):
    from anemoi.training.real_run import StageWindow

    prev = Fix(storm_id, t - timedelta(hours=6), 19.9, -60.0, 50.0, 1000.0,
               quality=TrackQuality.WORKING)
    cur = Fix(storm_id, t, 20.0, -60.0, 50.0, 1000.0, quality=TrackQuality.WORKING)
    return StageWindow(
        storm_id=storm_id, window=(prev, cur), current=cur, y=y,
        mask=np.ones(len(DEFAULT_LEADS), dtype=bool),
    )


def test_split_subtracts_the_prior_and_add_priors_restores_the_forecast():
    y = np.arange(len(DEFAULT_LEADS) * 3, dtype=float).reshape(-1, 3)
    with_prior = _window("AL012022", T0, y)
    without = _window("AL022022", T0, y)
    prior = np.full((len(DEFAULT_LEADS), 3), 7.0)

    kept, residual, priors = tp.split_by_prior(
        [with_prior, without], lambda sw: prior if sw.storm_id == "AL012022" else None,
    )

    assert kept == [with_prior]
    np.testing.assert_allclose(residual[0].y, y - prior)
    assert residual[0].storm_id == with_prior.storm_id
    assert residual[0].current == with_prior.current
    np.testing.assert_allclose(tp.add_priors(residual[0].y[None], kept, priors)[0], y)


def test_the_prior_is_stage_b_only():
    adecks = {"AL012022": _adeck("AL012022", {})}
    assert tp.prior_stage_kwargs(SimpleNamespace(flavor=Flavor.ERA5_PRETRAIN), adecks) == {}
    assert tp.prior_stage_kwargs(SimpleNamespace(flavor=Flavor.GDAS_FINETUNE), None) == {}
    assert "prior_fn" in tp.prior_stage_kwargs(SimpleNamespace(flavor=Flavor.GDAS_FINETUNE), adecks)


def test_curriculum_adecks_needs_streaming_and_some_adeck(tmp_path):
    tracks = [SimpleNamespace(storm_id="AL012022")]
    assert tp.curriculum_adecks(None, tracks, streaming=True) is None
    with pytest.raises(ValueError, match="streaming"):
        tp.curriculum_adecks(tmp_path, tracks, streaming=False)
    with pytest.raises(ValueError, match="no a-deck"):
        tp.curriculum_adecks(tmp_path, tracks, streaming=True)


def test_track_prior_is_not_a_builder_kwarg():
    assert "track_prior" in NON_BUILD_ARCH_PARAMS
    assert build_kwargs({"d_model": 16, "track_prior": "AVNI"}) == {"d_model": 16}
    assert tp.prior_name({"track_prior": "AVNI"}) == "AVNI"
    assert tp.prior_name({}) is None and tp.prior_name(None) is None


@pytest.mark.torch
def test_a_version_with_a_prior_is_described_and_loaded():
    pytest.importorskip("torch")
    from anemoi.models.architecture import describe

    arch = describe("transformer", {"d_model": 16, "track_prior": "AVNI"})
    assert arch.arch_params["track_prior"] == "AVNI"


# --- serving --------------------------------------------------------------


def _track(storm_id: str = "AL012022") -> Track:
    fixes = tuple(
        Fix(storm_id, T0 + timedelta(hours=6 * (i - 3)), 19.7 + 0.1 * i, -60.0, 50.0, 1000.0,
            quality=TrackQuality.WORKING)
        for i in range(4)
    )
    return Track(storm_id=storm_id, fixes=fixes)


def test_live_prior_matches_training_and_is_none_without_avni(tmp_path):
    from anemoi.training import real_inference_live as live

    track = _track()
    current = track.fixes[-1]
    points = {("AVNI", T0, lead): AdeckPoint(20.0 + lead / 12, -60.0, 50.0)
              for lead in DEFAULT_LEADS}
    adeck = _adeck(track.storm_id, points)

    got = live.fetch_live_track_prior(track, current, tmp_path, adeck_fetcher=lambda s: adeck)
    sw = _window(track.storm_id, T0, np.zeros((len(DEFAULT_LEADS), 3)))
    sw = sw.__class__(storm_id=sw.storm_id, window=track.fixes[-2:], current=current,
                      y=sw.y, mask=sw.mask)
    want = tp.window_prior_fn({track.storm_id: adeck})(sw)
    np.testing.assert_allclose(got, want)

    assert live.fetch_live_track_prior(
        track, current, tmp_path, adeck_fetcher=lambda s: None,
    ) is None


def _version(arch: dict):
    return SimpleNamespace(tags={"arch_params": json.dumps(arch)})


def test_serving_gate_only_applies_to_a_version_trained_with_a_prior(tmp_path):
    from anemoi.training.real_inference_cycle import _live_prior_for

    track = _track()
    current = track.fixes[-1]
    called = []

    def fetcher(*a):
        called.append(1)
        return np.ones((len(DEFAULT_LEADS), 3))

    assert _live_prior_for(_version({"d_model": 16}), track, current, tmp_path, fetcher) == (
        None, None,
    )
    assert not called
    prior, reason = _live_prior_for(
        _version({"track_prior": "AVNI"}), track, current, tmp_path, fetcher,
    )
    assert reason is None and prior.shape == (len(DEFAULT_LEADS), 3)
    prior, reason = _live_prior_for(
        _version({"track_prior": "AVNI"}), track, current, tmp_path, lambda *a: None,
    )
    assert prior is None and "AVNI" in reason


@pytest.mark.torch
def test_served_forecast_is_the_prior_plus_the_correction():
    torch = pytest.importorskip("torch")
    from anemoi.training.real_inference_cycle import _run_group1_model

    n = len(DEFAULT_LEADS)

    class Zero(torch.nn.Module):
        def forward(self, x):
            return torch.zeros(x.shape[0], n, 3)

    stats = {
        "x_mean": np.zeros((1, 1, 1, 1)), "x_std": np.ones((1, 1, 1, 1)),
        "y_mean": np.zeros((n, 3)), "y_std": np.ones((n, 3)),
    }
    current = _track().fixes[-1]
    raw = np.zeros((1, 2, 2))
    plain = _run_group1_model("cnn", Zero(), raw, stats, current)
    prior = np.zeros((n, 3))
    prior[:, 1] = 60.0  # 60 nm north at every lead
    shifted = _run_group1_model("cnn", Zero(), raw, stats, current, prior=prior)

    np.testing.assert_allclose(plain[:, 0], current.lat)
    np.testing.assert_allclose(shifted[:, 0], current.lat + 1.0, atol=0.01)
    np.testing.assert_allclose(shifted[:, 1], current.lon, atol=1e-6)


# --- training end to end ---------------------------------------------------


def _avni_from_truth(track: Track, rng, noise_deg: float) -> Adeck:
    """An AVNI that is the storm's own future track plus noise: a prior
    the model only has to correct a little."""
    by_time = {f.valid_time: f for f in track.fixes}
    points = {}
    for fix in track.fixes:
        for lead in DEFAULT_LEADS:
            future = by_time.get(fix.valid_time + timedelta(hours=lead))
            if future is None:
                continue
            points[("AVNI", fix.valid_time, lead)] = AdeckPoint(
                lat=future.lat + float(rng.normal(0, noise_deg)),
                lon=future.lon + float(rng.normal(0, noise_deg)),
                max_wind_kt=future.max_wind_kt,
            )
    return _adeck(track.storm_id, points)


@pytest.mark.torch
def test_curriculum_with_a_prior_scores_prior_plus_correction(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    from test_steering_input import _curriculum_tracks, _FakeS3Client, cache_all_fixes

    from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config
    from anemoi.training.real_run_transformer import run_transformer_curriculum

    era5, gdas = tmp_path / "era5", tmp_path / "gdas"
    tracks = _curriculum_tracks()
    for t in tracks:
        cache_all_fixes(era5, t, Flavor.ERA5_PRETRAIN)
        cache_all_fixes(gdas, t, Flavor.GDAS_FINETUNE)
    rng = np.random.default_rng(0)
    adecks = {t.storm_id: _avni_from_truth(t, rng, 0.05) for t in tracks}
    monkeypatch.setattr(tp, "load_adecks", lambda d, ids: {s: adecks[s] for s in ids})

    def run(adeck_dir):
        store = CheckpointStore(S3Config(
            endpoint_url="https://example.r2.cloudflarestorage.com", bucket="anemoi-test",
            access_key_id="key", secret_access_key="secret"), client=_FakeS3Client())
        return run_transformer_curriculum(
            tracks, store, era5, gdas, seed=42, n_augment=1, d_model=16, dropout=0.0,
            streaming=True, batch_size=4, adeck_dir=adeck_dir,
            curriculum_kwargs={"a": {"epochs": 1}, "b": {"epochs": 1}},
        )

    _r, plain, plain_artifacts = run(None)
    _r, with_prior, artifacts = run(tmp_path)

    assert "track_prior" not in plain_artifacts.arch_params
    assert artifacts.arch_params["track_prior"] == "AVNI"
    # One epoch learns little; the near-perfect prior is what's scored.
    assert with_prior.values["track_error_24h_nm"] < 0.5 * plain.values["track_error_24h_nm"]


# --- CLI ---------------------------------------------------------------------


def test_cli_train_refuses_the_prior_for_lstm_and_pinn(tmp_path):
    from anemoi import cli

    for model in ("lstm", "pinn"):
        args = argparse.Namespace(
            model=model, hurdat2="unused.txt", seed=1, n_augment=1, hidden_dim=8,
            era5_cache_dir=str(tmp_path), gdas_cache_dir=str(tmp_path),
            registry_root=str(tmp_path / "registry"), streaming=True, batch_size=None,
            num_workers=0, adeck_dir=str(tmp_path),
        )
        assert cli.cmd_train(args) == 1


def test_one_prior_fetch_is_shared_by_every_model_in_a_forecast(tmp_path):
    from anemoi.training.real_inference_cycle import _live_prior_for, shared_prior

    track = _track()
    current = track.fixes[-1]
    calls = []

    def fetch(*a):
        calls.append(1)
        return None  # e.g. NHC unreachable: cached too, not retried per model

    once = shared_prior(fetch)
    for _ in ("cnn", "transformer", "gnn"):
        prior, reason = _live_prior_for(
            _version({"track_prior": "AVNI"}), track, current, tmp_path, once,
        )
        assert prior is None and reason
    assert len(calls) == 1


def test_live_adeck_text_is_capped_while_decompressing(monkeypatch):
    import gzip

    from anemoi.data import adeck_source
    from anemoi.training import real_inference_live as live

    monkeypatch.setattr(adeck_source, "MAX_ADECK_TEXT_BYTES", 100)
    body = gzip.compress(b"x" * 10_000)
    monkeypatch.setattr(adeck_source, "_get", lambda url: body)
    assert live.fetch_live_adeck("AL012022") is None

    line = (b"AL, 01, 2022090112, 03, AVNI,  12, 210N,  600W,  50,\n")
    monkeypatch.setattr(adeck_source, "MAX_ADECK_TEXT_BYTES", 10_000)
    monkeypatch.setattr(adeck_source, "_get", lambda url: gzip.compress(line))
    adeck = live.fetch_live_adeck("AL012022")
    assert adeck is not None and adeck.get("AVNI", T0, 12).lat == pytest.approx(21.0)
