"""Source-agnostic pieces of data.gridded_cache not already exercised via
era5_cache/gdas_cache's thin wrappers: track time-filtering and the durable
archive-sync pass (#22 long-term GDAS/Stage B data strategy).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.features import GriddedFields
from anemoi.data.gridded_cache import (
    FetchTask,
    archive_key,
    build_fetch_tasks,
    cache_path,
    filter_tracks_by_min_valid_time,
    run_fetch_cache,
    save_cached_fields,
    sync_cache_to_archive,
)
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


# --- filter_tracks_by_min_valid_time --------------------------------------------


def test_filter_drops_fixes_earlier_than_the_cutoff():
    old = make_track("AL01", 3, start=datetime(2015, 8, 1, tzinfo=UTC))
    new = make_track("AL02", 3, start=datetime(2022, 8, 1, tzinfo=UTC))
    cutoff = datetime(2021, 1, 1, tzinfo=UTC)

    kept = filter_tracks_by_min_valid_time([old, new], cutoff)

    assert [t.storm_id for t in kept] == ["AL02"]
    assert all(f.valid_time >= cutoff for f in kept[0].fixes)


def test_filter_drops_a_storm_entirely_if_no_fixes_survive():
    old = make_track("AL01", 2, start=datetime(2010, 1, 1, tzinfo=UTC))
    kept = filter_tracks_by_min_valid_time([old], datetime(2021, 1, 1, tzinfo=UTC))
    assert kept == []


def test_filter_keeps_a_straddling_storm_partially():
    straddler = make_track("AL03", 4, start=datetime(2020, 12, 31, 12, tzinfo=UTC))
    cutoff = datetime(2021, 1, 1, tzinfo=UTC)

    kept = filter_tracks_by_min_valid_time([straddler], cutoff)

    assert len(kept) == 1
    assert len(kept[0].fixes) < 4
    assert all(f.valid_time >= cutoff for f in kept[0].fixes)


# --- sync_cache_to_archive --------------------------------------------------------


class FakeArchive:
    """Same duck-typed surface as tracking.checkpoint_store.CheckpointStore --
    exists()/upload() only, in-memory."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.upload_calls: list[str] = []

    def exists(self, key: str) -> bool:
        return key in self.objects

    def upload(self, local_path: Path | str, key: str) -> str:
        self.upload_calls.append(key)
        self.objects[key] = Path(local_path).read_bytes()
        return f"s3://fake-bucket/{key}"


def test_sync_uploads_every_locally_cached_file_not_already_archived(tmp_path):
    tracks = [make_track("AL01", 3)]
    tasks = build_fetch_tasks(tracks)
    for task in tasks:
        save_cached_fields(cache_path(tmp_path, task), make_fields(), task)

    archive = FakeArchive()
    report = sync_cache_to_archive(
        tasks, tmp_path, archive, prefix="gdas_archive", progress_every=0
    )

    assert report.n_uploaded == 3
    assert report.n_already_archived == 0
    assert report.n_missing_local == 0
    assert report.n_failed == 0
    assert len(archive.upload_calls) == 3


def test_sync_skips_files_missing_locally_without_failing(tmp_path):
    tracks = [make_track("AL01", 2)]
    tasks = build_fetch_tasks(tracks)
    # Only cache one of the two locally.
    save_cached_fields(cache_path(tmp_path, tasks[0]), make_fields(), tasks[0])

    archive = FakeArchive()
    report = sync_cache_to_archive(
        tasks, tmp_path, archive, prefix="gdas_archive", progress_every=0
    )

    assert report.n_uploaded == 1
    assert report.n_missing_local == 1
    assert report.n_failed == 0


def test_sync_is_resumable_and_does_not_reupload_what_the_archive_already_has(tmp_path):
    tracks = [make_track("AL01", 3)]
    tasks = build_fetch_tasks(tracks)
    for task in tasks:
        save_cached_fields(cache_path(tmp_path, task), make_fields(), task)

    archive = FakeArchive()
    sync_cache_to_archive(tasks, tmp_path, archive, prefix="gdas_archive", progress_every=0)
    assert len(archive.upload_calls) == 3

    # Re-run: the archive already has everything, nothing should re-upload.
    report = sync_cache_to_archive(
        tasks, tmp_path, archive, prefix="gdas_archive", progress_every=0
    )
    assert report.n_uploaded == 0
    assert report.n_already_archived == 3
    assert len(archive.upload_calls) == 3  # unchanged


def test_sync_records_upload_failures_without_aborting_the_run(tmp_path):
    tracks = [make_track("AL01", 3)]
    tasks = build_fetch_tasks(tracks)
    for task in tasks:
        save_cached_fields(cache_path(tmp_path, task), make_fields(), task)

    class FlakyArchive(FakeArchive):
        def upload(self, local_path, key):
            if "AL01" in key and key.endswith("2026080606.npz"):
                raise RuntimeError("simulated R2 blip")
            return super().upload(local_path, key)

    archive = FlakyArchive()
    report = sync_cache_to_archive(
        tasks, tmp_path, archive, prefix="gdas_archive", progress_every=0
    )

    assert report.n_uploaded == 2
    assert report.n_failed == 1
    assert "simulated R2 blip" in report.failures[0][1]


def test_archive_key_is_deterministic_and_namespaced_by_prefix():
    task = FetchTask(storm_id="AL092026", valid_time=T, lat=20.0, lon=-60.0)
    assert archive_key("gdas_archive", task) == "gdas_archive/AL092026/2026080600.npz"
    assert archive_key("era5_archive", task) == "era5_archive/AL092026/2026080600.npz"


def test_run_fetch_cache_still_works_unaffected_by_the_archive_addition(tmp_path):
    """Guards against the archive-sync addition accidentally coupling into
    the unrelated fetch path."""
    tracks = [make_track("AL01", 2)]

    def fake_fetch(valid_time, lat, lon):
        return make_fields()

    report = run_fetch_cache(tracks, tmp_path, fake_fetch, progress_every=0)
    assert report.n_fetched == 2
    assert report.n_failed == 0
