"""Concurrent real-GDAS fetch/cache pipeline (#22 Stage B analog of #38's
ERA5 pipeline). Exercises the same shared engine (data.gridded_cache) via
gdas_cache's thin wrapper, with an injected fetch_fn -- no network or
eccodes needed for these.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.features import GriddedFields
from anemoi.data.gdas_cache import GDAS_ARCHIVE_START, run_fetch_cache
from anemoi.data.sources import Flavor

T = datetime(2026, 8, 6, 0, tzinfo=UTC)


def make_track(storm_id: str, n: int, *, start: datetime = T) -> Track:
    fixes = tuple(
        Fix(
            storm_id=storm_id,
            valid_time=start + timedelta(hours=6 * i),
            lat=20.0 + 0.1 * i,
            lon=-60.0 - 0.2 * i,
            max_wind_kt=60.0,
            min_pressure_mb=990.0,
            quality=TrackQuality.FINAL,
        )
        for i in range(n)
    )
    return Track(storm_id=storm_id, fixes=fixes)


def make_fields() -> GriddedFields:
    grid = lambda v: np.full((5, 5), v)  # noqa: E731
    return GriddedFields(
        valid_time=T,
        flavor=Flavor.GDAS_FINETUNE,
        u200=grid(15.0), v200=grid(5.0),
        u850=grid(10.0), v850=grid(3.0),
        z500=grid(5750.0), rh700=grid(62.0),
        t700=grid(281.0), mslp=grid(1012.0),
        sst=grid(28.0), ohc=grid(60.0),
    )


def test_run_fetch_cache_writes_one_file_per_task(tmp_path):
    tracks = [make_track("AL01", 3)]

    def fake_fetch(valid_time, lat, lon):
        return make_fields()

    report = run_fetch_cache(tracks, tmp_path, fetch_fn=fake_fetch, progress_every=0)

    assert report.n_total == 3
    assert report.n_fetched == 3
    assert report.n_failed == 0
    assert len(list(tmp_path.glob("AL01/*.npz"))) == 3


def test_run_fetch_cache_defaults_to_lower_concurrency_than_era5():
    """GDAS's default max_workers is lower than ERA5's -- many fixes share
    the same underlying GRIB2 file/byte ranges, so hammering one NOAA
    object with too many simultaneous range requests is worth avoiding."""
    import inspect

    from anemoi.data.era5_cache import run_fetch_cache as era5_run_fetch_cache

    gdas_default = inspect.signature(run_fetch_cache).parameters["max_workers"].default
    era5_default = inspect.signature(era5_run_fetch_cache).parameters["max_workers"].default
    assert gdas_default < era5_default


def test_run_fetch_cache_is_resumable(tmp_path):
    tracks = [make_track("AL01", 2)]
    calls = []

    def fake_fetch(valid_time, lat, lon):
        calls.append(valid_time)
        return make_fields()

    run_fetch_cache(tracks, tmp_path, fetch_fn=fake_fetch, progress_every=0)
    report = run_fetch_cache(tracks, tmp_path, fetch_fn=fake_fetch, progress_every=0)

    assert report.n_skipped == 2
    assert report.n_fetched == 0
    assert len(calls) == 2  # not re-fetched


def test_run_fetch_cache_records_failures_without_aborting_the_run(tmp_path):
    tracks = [make_track("AL01", 3)]

    def flaky_fetch(valid_time, lat, lon):
        if valid_time.hour == 6:
            raise RuntimeError("simulated NOAA range-request failure")
        return make_fields()

    report = run_fetch_cache(tracks, tmp_path, fetch_fn=flaky_fetch, progress_every=0)

    assert report.n_fetched == 2
    assert report.n_failed == 1
    assert "simulated NOAA range-request failure" in report.failures[0][1]


def test_run_fetch_cache_drops_fixes_before_the_real_archive_start_by_default(tmp_path):
    """GDAS's real archive (noaa-gfs-bdp-pds) starts 2021-01-01 -- a fix
    dated earlier is a guaranteed 404, not a transient failure, so it should
    never reach fetch_fn at all (see gdas_cache.GDAS_ARCHIVE_START)."""
    pre_archive = make_track("AL01", 2, start=datetime(2015, 8, 1, tzinfo=UTC))
    post_archive = make_track("AL02", 2, start=datetime(2022, 8, 1, tzinfo=UTC))
    calls = []

    def fake_fetch(valid_time, lat, lon):
        calls.append(valid_time)
        return make_fields()

    report = run_fetch_cache(
        [pre_archive, post_archive], tmp_path, fetch_fn=fake_fetch, progress_every=0
    )

    assert report.n_total == 2  # only post_archive's fixes were ever tasks
    assert report.n_fetched == 2
    assert all(v >= GDAS_ARCHIVE_START for v in calls)
    assert len(list(tmp_path.glob("AL01/*.npz"))) == 0
    assert len(list(tmp_path.glob("AL02/*.npz"))) == 2


def test_run_fetch_cache_min_valid_time_none_disables_the_filter(tmp_path):
    pre_archive = make_track("AL01", 2, start=datetime(2015, 8, 1, tzinfo=UTC))

    def fake_fetch(valid_time, lat, lon):
        return make_fields()

    report = run_fetch_cache(
        [pre_archive], tmp_path, fetch_fn=fake_fetch, min_valid_time=None, progress_every=0
    )
    assert report.n_total == 2
    assert report.n_fetched == 2


@pytest.mark.gridded
def test_default_fetch_fn_wires_a_shared_session(monkeypatch):
    """The default fetcher must pass one requests.Session through to every
    fetch_gdas_grib2_fields call, not open a fresh one per sample -- verified
    by capturing what real_gridded.fetch_gdas_grib2_fields receives."""
    pytest.importorskip("requests")
    from anemoi.data import gdas_cache

    received_sessions = []

    def fake_fetch_gdas_grib2_fields(valid_time, *, session=None, timeout=60.0):
        received_sessions.append(session)
        return {}

    def fake_gdas_to_gridded_fields(messages, center_lat, center_lon, valid_time, **kw):
        return make_fields()

    monkeypatch.setattr(
        "anemoi.data.real_gridded.fetch_gdas_grib2_fields", fake_fetch_gdas_grib2_fields
    )
    monkeypatch.setattr(
        "anemoi.data.real_gridded.gdas_to_gridded_fields", fake_gdas_to_gridded_fields
    )

    fetch = gdas_cache._default_fetch_fn(box_deg=10.0)
    fetch(T, 20.0, -60.0)
    fetch(T + timedelta(hours=6), 21.0, -61.0)

    assert len(received_sessions) == 2
    assert received_sessions[0] is received_sessions[1]
    assert received_sessions[0] is not None
