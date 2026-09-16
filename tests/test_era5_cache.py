"""Concurrent real-ERA5 fetch/cache pipeline (#22)."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.era5_cache import (
    FetchTask,
    build_fetch_tasks,
    cache_path,
    load_cached_fields,
    run_fetch_cache,
    save_cached_fields,
)
from anemoi.data.features import GriddedFields
from anemoi.data.sources import Flavor

T = datetime(2026, 8, 6, 0, tzinfo=UTC)


def make_track(storm_id: str, n: int) -> Track:
    fixes = tuple(
        Fix(
            storm_id=storm_id,
            valid_time=T + timedelta(hours=6 * i),
            lat=20.0 + 0.1 * i,
            lon=-60.0 - 0.2 * i,
            max_wind_kt=60.0,
            min_pressure_mb=990.0,
            quality=TrackQuality.FINAL,
        )
        for i in range(n)
    )
    return Track(storm_id=storm_id, fixes=fixes)


def make_fields(seed: float = 1.0) -> GriddedFields:
    grid = lambda v: np.full((5, 5), v)  # noqa: E731
    return GriddedFields(
        valid_time=T,
        flavor=Flavor.ERA5_PRETRAIN,
        u200=grid(15.0 * seed), v200=grid(5.0 * seed),
        u850=grid(10.0 * seed), v850=grid(3.0 * seed),
        z500=grid(5750.0 * seed), rh700=grid(62.0),
        t700=grid(281.0), mslp=grid(1012.0),
        sst=grid(28.0), ohc=grid(60.0),
    )


# --- build_fetch_tasks / cache_path --------------------------------------------


def test_build_fetch_tasks_covers_every_fix_across_tracks():
    tracks = [make_track("AL01", 3), make_track("AL02", 2)]
    tasks = build_fetch_tasks(tracks)
    assert len(tasks) == 5
    assert all(isinstance(t, FetchTask) for t in tasks)
    assert {t.storm_id for t in tasks} == {"AL01", "AL02"}


def test_cache_path_is_deterministic_and_keyed_by_storm_and_time():
    task = FetchTask(storm_id="AL092026", valid_time=T, lat=20.0, lon=-60.0)
    path = cache_path("/tmp/cache", task)
    assert path.parent.name == "AL092026"
    assert path.name == "2026080600.npz"


# --- save/load round trip -------------------------------------------------------


def test_save_and_load_cached_fields_round_trips(tmp_path):
    task = FetchTask(storm_id="AL092026", valid_time=T, lat=20.0, lon=-60.0)
    fields = make_fields(seed=2.0)
    path = cache_path(tmp_path, task)

    save_cached_fields(path, fields, task)
    assert path.exists()

    restored = load_cached_fields(path)
    assert restored.flavor is fields.flavor
    assert restored.valid_time == fields.valid_time
    assert np.array_equal(restored.u200, fields.u200)
    assert np.array_equal(restored.ohc, fields.ohc)


# --- run_fetch_cache (fake fetcher, no network) ---------------------------------


def test_run_fetch_cache_writes_one_file_per_task(tmp_path):
    tracks = [make_track("AL01", 3)]

    def fake_fetch(valid_time, lat, lon):
        return make_fields()

    report = run_fetch_cache(tracks, tmp_path, fetch_fn=fake_fetch, progress_every=0)

    assert report.n_total == 3
    assert report.n_fetched == 3
    assert report.n_skipped == 0
    assert report.n_failed == 0
    assert len(list(tmp_path.glob("AL01/*.npz"))) == 3


def test_run_fetch_cache_skips_already_cached_samples_by_default(tmp_path):
    tracks = [make_track("AL01", 3)]
    calls = []

    def fake_fetch(valid_time, lat, lon):
        calls.append(valid_time)
        return make_fields()

    run_fetch_cache(tracks, tmp_path, fetch_fn=fake_fetch, progress_every=0)
    assert len(calls) == 3

    # Second run: everything already cached, fetch_fn must not be called again.
    report = run_fetch_cache(tracks, tmp_path, fetch_fn=fake_fetch, progress_every=0)
    assert report.n_skipped == 3
    assert report.n_fetched == 0
    assert len(calls) == 3  # unchanged


def test_run_fetch_cache_can_force_refetch_with_skip_existing_false(tmp_path):
    tracks = [make_track("AL01", 2)]
    calls = []

    def fake_fetch(valid_time, lat, lon):
        calls.append(valid_time)
        return make_fields()

    run_fetch_cache(tracks, tmp_path, fetch_fn=fake_fetch, progress_every=0)
    run_fetch_cache(tracks, tmp_path, fetch_fn=fake_fetch, skip_existing=False, progress_every=0)
    assert len(calls) == 4


def test_run_fetch_cache_records_failures_without_aborting_the_run(tmp_path):
    tracks = [make_track("AL01", 4)]

    def flaky_fetch(valid_time, lat, lon):
        if valid_time.hour == 6:
            raise RuntimeError("simulated network blip")
        return make_fields()

    report = run_fetch_cache(tracks, tmp_path, fetch_fn=flaky_fetch, progress_every=0)

    assert report.n_total == 4
    assert report.n_fetched == 3
    assert report.n_failed == 1
    assert "simulated network blip" in report.failures[0][1]
    # the 3 good samples must still be cached despite the 1 failure
    assert len(list(tmp_path.glob("AL01/*.npz"))) == 3


def test_run_fetch_cache_actually_runs_fetches_concurrently(tmp_path):
    """Uses a fetch_fn that blocks briefly and records concurrency; with
    max_workers > 1 several should be in flight at once, not strictly
    serialised -- this is the entire point of the module."""
    tracks = [make_track("AL01", 8)]
    concurrent_peak = 0
    in_flight = 0
    lock = threading.Lock()

    def slow_fetch(valid_time, lat, lon):
        nonlocal concurrent_peak, in_flight
        with lock:
            in_flight += 1
            concurrent_peak = max(concurrent_peak, in_flight)
        time.sleep(0.05)
        with lock:
            in_flight -= 1
        return make_fields()

    run_fetch_cache(tracks, tmp_path, fetch_fn=slow_fetch, max_workers=4, progress_every=0)
    assert concurrent_peak > 1


def test_load_cached_fields_rejects_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_cached_fields(tmp_path / "does_not_exist.npz")
