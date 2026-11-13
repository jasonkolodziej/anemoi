"""The steering-along-track spike (training.steering_spike)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from anemoi.data import steering
from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.features import GriddedFields
from anemoi.data.gridded_cache import FetchTask, cache_path, save_cached_fields
from anemoi.data.sources import Flavor

pytest.importorskip("torch", reason="needs the torch extra")

pytestmark = pytest.mark.torch


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


def cache_all_fixes(cache_dir, track: Track, flavor: Flavor) -> None:
    grid = lambda v: np.full((41, 41), v)  # noqa: E731
    for fix in track.fixes:
        task = FetchTask(track.storm_id, fix.valid_time, fix.lat, fix.lon)
        fields = GriddedFields(
            valid_time=fix.valid_time, flavor=flavor,
            u200=grid(15.0), v200=grid(5.0), u850=grid(10.0), v850=grid(3.0),
            z500=grid(5750.0), rh700=grid(62.0), t700=grid(281.0), mslp=grid(1012.0),
            sst=grid(28.0), ohc=grid(60.0),
        )
        save_cached_fields(cache_path(cache_dir, task), fields, task)


def _cache_steering(cache_dir, track, rng) -> None:
    for fix in track.fixes:
        task = FetchTask(track.storm_id, fix.valid_time, fix.lat, fix.lon)
        feats = rng.normal(size=(len(steering.STEERING_LEADS_H), len(steering.FEATURE_NAMES)))
        steering.save_steering(
            steering.steering_path(cache_dir, track.storm_id, fix.valid_time),
            feats.astype(np.float32), task,
        )


def test_expanded_patch_channels_start_as_the_same_function():
    import torch

    from anemoi.models.transformer import build_transformer
    from anemoi.training.steering_spike import expand_patch_channels

    torch.manual_seed(0)
    model, _ = build_transformer(n_variables=4, grid_size=(8, 8), d_model=16, n_heads=2,
                                 n_layers=1, dropout=0.0)
    model.eval()
    x = torch.randn(3, 4, 8, 8)
    before, _ = model(x)
    expand_patch_channels(model, 5)
    assert model.patch.in_channels == 9
    assert model.patch.extra.weight.abs().sum() == 0
    after, _ = model(torch.cat([x, torch.randn(3, 5, 8, 8) * 100], dim=1))
    assert torch.allclose(before, after, atol=1e-5)
    assert model.patch.extra.weight.requires_grad


def test_track_errors_are_zero_for_a_perfect_forecast_and_nan_without_a_target():
    from anemoi.training.real_run import iter_stage_windows
    from anemoi.training.steering_spike import track_errors_nm

    track = make_track("AL012022", season=2022, n=26)
    windows = list(iter_stage_windows([track], np.random.default_rng(0), 1))
    pred = np.stack([sw.y for sw in windows])
    errors, storms = track_errors_nm(windows, pred)
    finite = np.isfinite(errors)
    assert finite.any() and (~finite).any()  # the last windows have no 48 h target
    assert np.allclose(errors[finite], 0.0, atol=1e-6)
    assert set(storms) == {"AL012022"}
    shifted = pred.copy()
    shifted[:, :, 1] += 60.0  # 60 nm further north at every lead
    errors2, _ = track_errors_nm(windows, shifted)
    assert np.allclose(errors2[finite], 60.0, atol=0.5)


def test_compare_refuses_arms_on_different_windows_and_pairs_the_rest():
    from anemoi.training.steering_spike import ArmResult, compare

    storms = np.array(["AL01"] * 4 + ["EP02"] * 2)
    keys = [(s, str(i)) for i, s in enumerate(storms)]
    base = ArmResult("baseline", 1, keys, np.array([100, 100, np.nan, 100, 50, 50.0]),
                     storms, 0.0)
    other = ArmResult("steering", 1, keys, np.array([90, 80, 70, np.nan, 60, 40.0]),
                      storms, 0.0)
    out = compare(base, other)
    assert out["AL"]["n_cases"] == 2
    assert out["AL"]["mean_diff_nm"] == pytest.approx(-15.0)
    assert out["AL"]["ci95"] is None  # one storm: no interval
    assert out["EP"]["mean_diff_nm"] == pytest.approx(0.0)
    assert out["CP"] == {"n_cases": 0, "n_storms": 0}
    with pytest.raises(ValueError, match="different windows"):
        compare(base, ArmResult("steering", 1, keys[::-1], other.errors, storms, 0.0))


def test_the_spike_runs_both_arms_on_the_same_windows_and_registers_nothing(tmp_path):
    from anemoi.training.steering_spike import run_steering_spike

    era5, gdas, steer = tmp_path / "era5", tmp_path / "gdas", tmp_path / "steer"
    tracks = [
        make_track("AL011985", season=1985, n=26, seed=0),
        make_track("AL012021", season=2021, n=26, seed=1),
        make_track("AL022021", season=2021, n=26, seed=2),
        make_track("AL012022", season=2022, n=26, seed=7),
        make_track("AL022022", season=2022, n=26, seed=8),
        make_track("AL012023", season=2023, n=26, seed=3),
    ]
    rng = np.random.default_rng(0)
    for t in tracks:
        cache_all_fixes(era5, t, Flavor.ERA5_PRETRAIN)
        cache_all_fixes(gdas, t, Flavor.GDAS_FINETUNE)
        if t.storm_id != "AL022022":  # no steering: dropped from both arms
            _cache_steering(steer, t, rng)

    report = run_steering_spike(
        tracks, era5, gdas, steer, seeds=(1, 2), n_augment=1, batch_size=4, d_model=16,
        dropout=0.0, curriculum_kwargs={"a": {"epochs": 1}, "b": {"epochs": 1}},
        log=lambda _m: None,
    )
    assert [(a["arm"], a["seed"]) for a in report["arms"]] == [
        ("baseline", 1), ("steering", 1), ("baseline", 2), ("steering", 2)]
    n_val = {a["n_val_windows"] for a in report["arms"]}
    assert len(n_val) == 1 and n_val.pop() > 0
    al = report["steering_minus_baseline"]["1"]["AL"]
    assert al["n_storms"] == 1  # AL012022 only: AL022022 had no steering
    assert np.isfinite(al["mean_diff_nm"])
    assert "2_minus_1" in report["baseline_seed_noise"]
    assert not list(tmp_path.rglob("registry.json"))


def test_steering_vectors_are_appended_after_the_basin_channels(tmp_path):
    """The streaming runner's ``extra_x`` adds constant channels and drops a
    window it maps to None."""
    from anemoi.models.transformer import build_transformer
    from anemoi.training.curriculum import stage_b
    from anemoi.training.real_run_transformer import (
        GRID_SIZE,
        TRANSFORMER_FIELD_NAMES,
        train_transformer_stage_streaming,
    )

    train, val = (make_track("AL012021", 2021, n=26, seed=1),
                  make_track("AL012022", 2022, n=26, seed=2))
    for t in (train, val):
        cache_all_fixes(tmp_path, t, Flavor.GDAS_FINETUNE)
    skip = val.fixes[10].valid_time
    seen: dict = {}

    def extra(sw):
        return None if sw.current.valid_time == skip else np.full(3, 7.0)

    model, _ = build_transformer(n_variables=len(TRANSFORMER_FIELD_NAMES) + 3,
                                 grid_size=GRID_SIZE, d_model=16, n_heads=2, n_layers=1,
                                 dropout=0.0)
    train_transformer_stage_streaming(
        model, stage_b(epochs=1), [train], [val], tmp_path, np.random.default_rng(0),
        n_augment=1, batch_size=4, basins=(), extra_x=extra,
        on_validation=lambda w, p: seen.update(windows=w, pred=p),
    )
    times = [sw.current.valid_time for sw in seen["windows"]]
    assert skip not in times and len(times) == len(seen["pred"]) > 0
    assert seen["pred"].shape[1:] == (7, 3)
    # constant channels after the fields
    assert model.patch.in_channels == len(TRANSFORMER_FIELD_NAMES) + 3


def test_stage_b_trains_the_steering_conv_and_keeps_the_rest_frozen(tmp_path):
    """Stage B freezes everything outside ``head.``; the steering conv must
    still learn (PR #245 review), and only when it is named trainable."""
    import torch

    from anemoi.models.transformer import build_transformer
    from anemoi.training.curriculum import stage_b
    from anemoi.training.real_run_transformer import (
        GRID_SIZE,
        TRANSFORMER_FIELD_NAMES,
        train_transformer_stage_streaming,
    )
    from anemoi.training.steering_spike import STEERING_PARAMS, expand_patch_channels

    train, val = (make_track("AL012021", 2021, n=26, seed=1),
                  make_track("AL012022", 2022, n=26, seed=2))
    for t in (train, val):
        cache_all_fixes(tmp_path, t, Flavor.GDAS_FINETUNE)
    rng = np.random.default_rng(0)
    vecs: dict = {}

    def extra(sw):  # varies by window, so it carries signal
        key = (sw.storm_id, sw.current.valid_time)
        return vecs.setdefault(key, rng.normal(size=4))

    def run(trainable):
        torch.manual_seed(0)
        model, _ = build_transformer(n_variables=len(TRANSFORMER_FIELD_NAMES),
                                     grid_size=GRID_SIZE, d_model=16, n_heads=2, n_layers=1,
                                     dropout=0.0)
        expand_patch_channels(model, 4)
        base_before = model.patch.base.weight.detach().cpu().clone()
        train_transformer_stage_streaming(
            model, stage_b(epochs=2, learning_rate=1e-2), [train], [val], tmp_path,
            np.random.default_rng(0), n_augment=1, batch_size=4, basins=(), extra_x=extra,
            trainable=trainable,
        )
        return model, base_before

    model, base_before = run((STEERING_PARAMS,))
    assert model.patch.extra.weight.abs().sum() > 0
    assert torch.equal(model.patch.base.weight.detach().cpu(), base_before)
    frozen, _ = run(())
    assert frozen.patch.extra.weight.abs().sum() == 0  # what the review caught
    with pytest.raises(ValueError, match="no parameter"):
        run(("nope.",))


def test_with_zero_steering_both_arms_are_the_same_run(tmp_path, monkeypatch):
    """All-zero steering standardises to zeros, so the steering conv gets no
    gradient and the arms differ only if their batch order differs (PR #245
    review: building the conv used to advance torch's RNG in one arm)."""
    from anemoi.training import steering_spike

    era5, gdas, steer = tmp_path / "era5", tmp_path / "gdas", tmp_path / "steer"
    tracks = [
        make_track("AL011985", season=1985, n=26, seed=0),
        make_track("AL012021", season=2021, n=26, seed=1),
        make_track("AL022021", season=2021, n=26, seed=2),
        make_track("AL012022", season=2022, n=26, seed=7),
        make_track("AL012023", season=2023, n=26, seed=3),
    ]
    for t in tracks:
        cache_all_fixes(era5, t, Flavor.ERA5_PRETRAIN)
        cache_all_fixes(gdas, t, Flavor.GDAS_FINETUNE)
        for fix in t.fixes:
            steering.save_steering(
                steering.steering_path(steer, t.storm_id, fix.valid_time),
                np.zeros((len(steering.STEERING_LEADS_H), len(steering.FEATURE_NAMES)),
                         dtype=np.float32),
                FetchTask(t.storm_id, fix.valid_time, fix.lat, fix.lon),
            )
    report = steering_spike.run_steering_spike(
        tracks, era5, gdas, steer, seeds=(1,), n_augment=1, batch_size=4, d_model=16,
        dropout=0.0, curriculum_kwargs={"a": {"epochs": 1}, "b": {"epochs": 2}},
        log=lambda _m: None,
    )
    al = report["steering_minus_baseline"]["1"]["AL"]
    assert al["n_cases"] > 0
    assert al["mean_diff_nm"] == pytest.approx(0.0, abs=1e-6)
