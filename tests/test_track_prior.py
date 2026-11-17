"""GFS's own track as a prior the gridded models correct (training.track_prior)."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import numpy as np
import pytest

from anemoi.data import gfs_track as gt
from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.sources import Flavor
from anemoi.geo import haversine_nm
from anemoi.models.base import DEFAULT_LEADS, NON_BUILD_ARCH_PARAMS, build_kwargs
from anemoi.training import track_prior as tp

T0 = datetime(2022, 9, 1, 12, tzinfo=UTC)
AT = {lead: i for i, lead in enumerate(gt.TRACK_LEADS_H)}


def _persistence() -> np.ndarray:
    steps = np.array([h // 6 for h in DEFAULT_LEADS], dtype=float)
    return np.stack([10.0 * steps, 5.0 * steps, np.full(len(steps), 50.0)], axis=1)


def _positions(until_h: int = 120, start=(21.0, -61.0), dlat_6h=0.5, dlon_6h=0.0) -> np.ndarray:
    """A tracked storm moving steadily from ``start``, lost after ``until_h``."""
    pos = np.full((len(gt.TRACK_LEADS_H), 2), np.nan)
    for lead, i in AT.items():
        if lead <= until_h:
            pos[i] = [start[0] + dlat_6h * lead / 6, start[1] + dlon_6h * lead / 6]
    return pos


def test_prior_is_the_tracks_displacement_shifted_to_the_fix():
    # GFS has the storm 1 deg north and west of the fix; the prior is its
    # motion from there, applied from the fix: 1 deg north per 12 h.
    prior = tp.prior_from_track(_positions(), 20.0, -60.0, _persistence())

    assert prior.shape == (len(DEFAULT_LEADS), 3)
    for i, lead in enumerate(DEFAULT_LEADS):
        assert prior[i, 0] == pytest.approx(0.0, abs=1e-6)
        assert prior[i, 1] == pytest.approx(
            haversine_nm(20.0, -60.0, 20.0 + lead / 12, -60.0), rel=1e-6,
        )
    np.testing.assert_array_equal(prior[:, 2], 0.0)  # intensity stays the model's own


def test_a_lead_gfs_has_lost_the_storm_by_falls_back_to_persistence():
    prior = tp.prior_from_track(_positions(until_h=24), 20.0, -60.0, _persistence())
    assert prior[1, 1] == pytest.approx(haversine_nm(20.0, -60.0, 22.0, -60.0), rel=1e-6)
    np.testing.assert_allclose(prior[2:, :2], _persistence()[2:, :2])


def test_no_prior_without_a_position_at_the_cycle_or_the_first_lead():
    lost_at_once = _positions(until_h=6)       # nothing at the first lead (12 h)
    no_start = _positions()
    no_start[AT[0]] = np.nan
    for positions in (None, lost_at_once, no_start):
        assert tp.prior_from_track(positions, 20.0, -60.0, _persistence()) is None


def _cache(tmp_path, storm_id: str, t: datetime, positions: np.ndarray):
    gt._write_meta(tmp_path, gt.gfs_track_meta())
    gt.save_track(gt.track_path(tmp_path, storm_id, t), positions,
                  gt.TrackTask(storm_id, t, 20.0, -60.0))
    return tmp_path


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


def test_the_window_prior_reads_the_cache(tmp_path):
    cache = _cache(tmp_path, "AL012022", T0, _positions())
    y = np.zeros((len(DEFAULT_LEADS), 3))
    fn = tp.window_prior_fn(cache)
    sw = _window("AL012022", T0, y)
    np.testing.assert_allclose(
        fn(sw), tp.prior_from_track(_positions(), 20.0, -60.0, sw.persistence),
    )
    assert fn(_window("AL022022", T0, y)) is None  # no cached track: no prior


def test_the_prior_is_stage_b_only(tmp_path):
    assert tp.prior_stage_kwargs(SimpleNamespace(flavor=Flavor.ERA5_PRETRAIN), tmp_path) == {}
    assert tp.prior_stage_kwargs(SimpleNamespace(flavor=Flavor.GDAS_FINETUNE), None) == {}
    assert "prior_fn" in tp.prior_stage_kwargs(
        SimpleNamespace(flavor=Flavor.GDAS_FINETUNE), tmp_path,
    )


def test_curriculum_prior_needs_streaming_and_a_cache_with_this_builds_settings(tmp_path):
    assert tp.curriculum_prior(None, streaming=True) is None
    with pytest.raises(ValueError, match="streaming"):
        tp.curriculum_prior(tmp_path, streaming=False)
    with pytest.raises(ValueError, match="no readable"):
        tp.curriculum_prior(tmp_path, streaming=True)
    gt._write_meta(tmp_path, gt.gfs_track_meta())
    assert tp.curriculum_prior(tmp_path, streaming=True) == tmp_path


def test_the_prior_keys_are_not_builder_kwargs():
    recorded = tp.prior_arch_params()
    assert set(recorded) <= NON_BUILD_ARCH_PARAMS
    assert build_kwargs({"d_model": 16, **recorded}) == {"d_model": 16}
    assert tp.prior_name(recorded) == tp.TRACK_PRIOR_NAME
    assert tp.prior_name({}) is None and tp.prior_name(None) is None


def test_only_this_builds_gfs_track_prior_can_be_served():
    assert tp.unservable_reason({"d_model": 16}) is None
    assert tp.unservable_reason(tp.prior_arch_params()) is None
    # The first version read AVNI from the a-decks (Decision Log 66).
    assert "Decision Log 66" in tp.unservable_reason({"track_prior": "AVNI"})
    other = {**tp.prior_arch_params()}
    other[tp.TRACK_PRIOR_INPUTS] = {**gt.gfs_track_meta(), "smooth_cells": 9}
    assert "other settings" in tp.unservable_reason(other)
    assert "other settings" in tp.unservable_reason({"track_prior": tp.TRACK_PRIOR_NAME})


@pytest.mark.torch
def test_a_version_with_a_prior_is_described():
    pytest.importorskip("torch")
    from anemoi.models.architecture import describe

    arch = describe("transformer", {"d_model": 16, **tp.prior_arch_params()})
    assert arch.arch_params["track_prior"] == tp.TRACK_PRIOR_NAME


# --- serving --------------------------------------------------------------


def _track(storm_id: str = "AL012022") -> Track:
    fixes = tuple(
        Fix(storm_id, T0 + timedelta(hours=6 * (i - 3)), 19.7 + 0.1 * i, -60.0, 50.0, 1000.0,
            quality=TrackQuality.WORKING)
        for i in range(4)
    )
    return Track(storm_id=storm_id, fixes=fixes)


def _fake_fields(centre_at):
    """A field fetcher whose vortex is at ``centre_at(lead)``."""
    from test_gfs_track import field_with

    calls = []

    def fetch(valid_time, lead):
        calls.append(lead)
        return field_with(centre_at(lead))

    return fetch, calls


def test_live_prior_is_the_training_prior_and_is_cached(tmp_path, monkeypatch):
    from anemoi.training import real_inference_live as live

    monkeypatch.setattr(live, "_TRACK_FIELD_MEMO", {})
    track = _track()
    current = track.fixes[-1]

    def centre(lead):
        return 20.3 + 0.4 * lead / 6, -60.2 - 0.3 * lead / 6
    fetch, calls = _fake_fields(centre)

    got = live.fetch_live_track_prior(track, current, tmp_path, field_fetcher=fetch)

    # What training reads: the same tracker run into the cache.
    cache = tmp_path / "train"
    gt.run_gfs_track_cache(
        [gt.TrackTask(track.storm_id, T0, current.lat, current.lon, 0.1, 0.0)], cache,
        fetch=fetch, max_workers=1,
    )
    sw = _window(track.storm_id, T0, np.zeros((len(DEFAULT_LEADS), 3)))
    sw = sw.__class__(storm_id=sw.storm_id, window=track.fixes[-2:], current=current,
                      y=sw.y, mask=sw.mask)
    np.testing.assert_allclose(got, tp.window_prior_fn(cache)(sw), atol=1e-6)
    assert got[3, 1] > 150  # 48 h: about 3.2 deg north

    n = len(calls)
    again = live.fetch_live_track_prior(
        track, current, tmp_path, field_fetcher=lambda *a: pytest.fail("refetched"),
    )
    np.testing.assert_allclose(again, got)
    assert len(calls) == n


def test_live_prior_is_none_when_a_lead_is_not_published_or_gfs_has_no_vortex(
    tmp_path, monkeypatch,
):
    from test_gfs_track import field_with

    from anemoi.training import real_inference_live as live

    track = _track()
    current = track.fixes[-1]

    def unpublished(valid_time, lead):
        if lead >= 60:
            raise OSError("404")
        return field_with((20.0, -60.0))

    monkeypatch.setattr(live, "_TRACK_FIELD_MEMO", {})
    assert live.fetch_live_track_prior(track, current, tmp_path, field_fetcher=unpublished) is None
    assert not list(tmp_path.rglob("*.npz"))  # nothing cached: the next cycle retries

    monkeypatch.setattr(live, "_TRACK_FIELD_MEMO", {})
    assert live.fetch_live_track_prior(
        track, current, tmp_path / "b", field_fetcher=lambda t, lead: field_with(),
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
    ok = _version(tp.prior_arch_params())
    prior, reason = _live_prior_for(ok, track, current, tmp_path, fetcher)
    assert reason is None and prior.shape == (len(DEFAULT_LEADS), 3)
    prior, reason = _live_prior_for(ok, track, current, tmp_path, lambda *a: None)
    assert prior is None and "published" in reason


def test_a_version_trained_on_the_adecks_is_never_served(tmp_path):
    from anemoi.training.real_inference_cycle import _live_prior_for

    track = _track()
    called = []
    prior, reason = _live_prior_for(
        _version({"track_prior": "AVNI"}), track, track.fixes[-1], tmp_path,
        lambda *a: called.append(1),
    )
    assert prior is None and "Decision Log 66" in reason
    assert not called  # refused before anything is fetched


def test_one_prior_fetch_is_shared_by_every_model_in_a_forecast(tmp_path):
    from anemoi.training.real_inference_cycle import _live_prior_for, shared_prior

    track = _track()
    current = track.fixes[-1]
    calls = []

    def fetch(*a):
        calls.append(1)
        return None  # e.g. not published: cached too, not retried per model

    once = shared_prior(fetch)
    for _ in ("cnn", "transformer", "gnn"):
        prior, reason = _live_prior_for(
            _version(tp.prior_arch_params()), track, current, tmp_path, once,
        )
        assert prior is None and reason
    assert len(calls) == 1


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


# --- latents ---------------------------------------------------------------


def test_latents_refuse_an_adeck_prior_and_need_the_cache(monkeypatch, tmp_path):
    from anemoi.training.real_latents import GFS_TRACK_DIR_ENV, _prior_source

    def artifacts(arch):
        return {"gnn": SimpleNamespace(arch_params=arch)}

    assert _prior_source(artifacts({"hidden": 8})) == (None, frozenset())
    with pytest.raises(ValueError, match="Decision Log 66"):
        _prior_source(artifacts({"track_prior": "AVNI"}))
    monkeypatch.delenv(GFS_TRACK_DIR_ENV, raising=False)
    with pytest.raises(ValueError, match=GFS_TRACK_DIR_ENV):
        _prior_source(artifacts(tp.prior_arch_params()))
    monkeypatch.setenv(GFS_TRACK_DIR_ENV, str(tmp_path))
    with pytest.raises(ValueError, match="no readable"):
        _prior_source(artifacts(tp.prior_arch_params()))
    gt._write_meta(tmp_path, gt.gfs_track_meta())
    fn, readers = _prior_source(artifacts(tp.prior_arch_params()))
    assert readers == {"gnn"} and callable(fn)


# --- training end to end ---------------------------------------------------


def _cache_truth(cache, track: Track, rng, noise_deg: float) -> None:
    """A GFS track that is the storm's own future track plus noise: a
    prior the model only has to correct a little."""
    by_time = {f.valid_time: f for f in track.fixes}
    for fix in track.fixes:
        pos = np.full((len(gt.TRACK_LEADS_H), 2), np.nan)
        for lead, i in AT.items():
            future = by_time.get(fix.valid_time + timedelta(hours=lead))
            if future is not None:
                pos[i] = [future.lat + rng.normal(0, noise_deg),
                          future.lon + rng.normal(0, noise_deg)]
        gt.save_track(gt.track_path(cache, track.storm_id, fix.valid_time), pos,
                      gt.TrackTask(track.storm_id, fix.valid_time, fix.lat, fix.lon))


@pytest.mark.torch
def test_curriculum_with_a_prior_scores_prior_plus_correction(tmp_path):
    pytest.importorskip("torch")
    from test_steering_input import _curriculum_tracks, _FakeS3Client, cache_all_fixes

    from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config
    from anemoi.training.real_run_transformer import run_transformer_curriculum

    era5, gdas, cache = tmp_path / "era5", tmp_path / "gdas", tmp_path / "gfs_track"
    tracks = _curriculum_tracks()
    rng = np.random.default_rng(0)
    gt._write_meta(cache, gt.gfs_track_meta())
    for t in tracks:
        cache_all_fixes(era5, t, Flavor.ERA5_PRETRAIN)
        cache_all_fixes(gdas, t, Flavor.GDAS_FINETUNE)
        _cache_truth(cache, t, rng, 0.05)

    def run(gfs_track_dir):
        store = CheckpointStore(S3Config(
            endpoint_url="https://example.r2.cloudflarestorage.com", bucket="anemoi-test",
            access_key_id="key", secret_access_key="secret"), client=_FakeS3Client())
        return run_transformer_curriculum(
            tracks, store, era5, gdas, seed=42, n_augment=1, d_model=16, dropout=0.0,
            streaming=True, batch_size=4, gfs_track_dir=gfs_track_dir,
            curriculum_kwargs={"a": {"epochs": 1}, "b": {"epochs": 1}},
        )

    _r, plain, plain_artifacts = run(None)
    _r, with_prior, artifacts = run(cache)

    assert "track_prior" not in plain_artifacts.arch_params
    assert artifacts.arch_params["track_prior"] == tp.TRACK_PRIOR_NAME
    assert artifacts.arch_params[tp.TRACK_PRIOR_INPUTS] == gt.gfs_track_meta()
    assert tp.unservable_reason(artifacts.arch_params) is None
    # One epoch learns little, so what's scored is the prior: the true
    # track shifted to the emulated working fix, whose noise (about 13 nm)
    # is then the error at every lead, instead of one that grows with lead.
    assert with_prior.values["track_error_72h_nm"] < plain.values["track_error_72h_nm"]
    assert with_prior.values["track_error_72h_nm"] < 30.0


# --- CLI ---------------------------------------------------------------------


def test_cli_train_refuses_the_prior_for_lstm_and_pinn(tmp_path):
    from anemoi import cli

    for model in ("lstm", "pinn"):
        args = argparse.Namespace(
            model=model, hurdat2="unused.txt", seed=1, n_augment=1, hidden_dim=8,
            era5_cache_dir=str(tmp_path), gdas_cache_dir=str(tmp_path),
            registry_root=str(tmp_path / "registry"), streaming=True, batch_size=None,
            num_workers=0, gfs_track_dir=str(tmp_path),
        )
        assert cli.cmd_train(args) == 1
