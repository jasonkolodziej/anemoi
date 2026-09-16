"""Generic concurrent fetch + local disk cache engine for real gridded-field
sources (#22).

Source-agnostic: :mod:`anemoi.data.era5_cache` and
:mod:`anemoi.data.gdas_cache` are both thin wrappers around
:func:`run_fetch_cache` here, supplying only the source-specific default
fetch function (ARCO-ERA5 Zarr vs. NOAA GDAS GRIB2). The concurrency,
resumability, caching format and failure-isolation logic is identical
either way -- one real ERA5 sample and one real GDAS sample both come out
as the same :class:`~anemoi.data.features.GriddedFields` shape, and both
archives are large enough (tens of thousands of fixes) that fetching
sequentially is impractical either way. See ``docs/train_infrastructure.md``
for the measured throughput this buys.

:func:`sync_cache_to_archive` is a second, independent pass over the same
local cache: it uploads whatever's been fetched to a durable off-box store
(see :class:`ArchiveClient`), so what's on one Spot VM's disk survives that
VM's teardown. Deliberately not folded into :func:`run_fetch_cache` itself
-- keeping fetch (network-bound, resumable via local `skip_existing`) and
archive sync (upload-bound, resumable via the archive's own `exists` check)
as separate passes means a slow/flaky archive endpoint can never stall or
fail a fetch run, and either pass can be re-run alone.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol

import numpy as np

from .besttrack import Track
from .features import GriddedFields
from .sources import Flavor

FieldsFetcher = Callable[[datetime, float, float], GriddedFields]

#: GriddedFields array attributes, in the order cached/restored.
_ARRAY_FIELDS: tuple[str, ...] = (
    "u200", "v200", "u850", "v850", "z500", "rh700", "t700", "mslp", "sst", "ohc",
)


@dataclass(frozen=True, slots=True)
class FetchTask:
    """One (storm, synoptic time) sample to fetch."""

    storm_id: str
    valid_time: datetime
    lat: float
    lon: float


def build_fetch_tasks(tracks: list[Track]) -> list[FetchTask]:
    """One task per fix across all given tracks -- the sample list a cache
    run needs to cover."""
    return [
        FetchTask(storm_id=track.storm_id, valid_time=fix.valid_time, lat=fix.lat, lon=fix.lon)
        for track in tracks
        for fix in track.fixes
    ]


def filter_tracks_by_min_valid_time(tracks: list[Track], min_valid_time: datetime) -> list[Track]:
    """Drop fixes earlier than ``min_valid_time``, and storms left with none.

    `data.splits`' season boundaries are shared across sources and set for
    Stage A's decades-deep ERA5 pretraining (`Split.TRAIN` starts 1980); a
    source whose real archive starts later than that -- GDAS's does, see
    `gdas_cache.GDAS_ARCHIVE_START` -- would otherwise be asked to fetch fixes
    that provably 404 rather than being excluded up front. Splitting this out
    as a source-level filter, separate from the split boundaries themselves,
    keeps Stage A's full historical window intact while making a
    source-specific fetch pipeline honest about what it can actually return.
    """
    filtered = []
    for track in tracks:
        fixes = tuple(f for f in track.fixes if f.valid_time >= min_valid_time)
        if fixes:
            filtered.append(Track(storm_id=track.storm_id, fixes=fixes))
    return filtered


def cache_path(cache_dir: Path | str, task: FetchTask) -> Path:
    return Path(cache_dir) / task.storm_id / f"{task.valid_time:%Y%m%d%H}.npz"


def save_cached_fields(path: Path, fields: GriddedFields, task: FetchTask) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    arrays = {name: getattr(fields, name) for name in _ARRAY_FIELDS}
    np.savez_compressed(
        path,
        storm_id=task.storm_id,
        valid_time=task.valid_time.isoformat(),
        lat=task.lat,
        lon=task.lon,
        flavor=fields.flavor.value,
        **arrays,
    )


def load_cached_fields(path: Path | str) -> GriddedFields:
    with np.load(path, allow_pickle=False) as data:
        return GriddedFields(
            valid_time=datetime.fromisoformat(str(data["valid_time"])),
            flavor=Flavor(str(data["flavor"])),
            **{name: data[name] for name in _ARRAY_FIELDS},
        )


@dataclass(slots=True)
class FetchCacheReport:
    n_total: int
    n_fetched: int
    n_skipped: int
    failures: list[tuple[FetchTask, str]] = field(default_factory=list)
    elapsed_s: float = 0.0

    @property
    def n_failed(self) -> int:
        return len(self.failures)


def run_fetch_cache(
    tracks: list[Track],
    cache_dir: Path | str,
    fetch_fn: FieldsFetcher,
    *,
    max_workers: int = 8,
    skip_existing: bool = True,
    progress_every: int = 50,
    label: str = "gridded_cache",
) -> FetchCacheReport:
    """Fetch real GriddedFields for every fix across ``tracks``, concurrently,
    caching each to ``cache_dir``.

    ``fetch_fn`` -- ``(valid_time, lat, lon) -> GriddedFields`` -- carries
    all source-specific behaviour (which archive, how to share a connection
    across samples); this function only handles the task list, concurrency,
    on-disk caching and resumability. One failed sample is recorded in the
    report rather than aborting the run -- a network blip on sample 8,000 of
    16,474 should not discard everything fetched so far.
    """
    cache_dir = Path(cache_dir)
    tasks = build_fetch_tasks(tracks)

    pending = []
    n_skipped = 0
    for task in tasks:
        if skip_existing and cache_path(cache_dir, task).exists():
            n_skipped += 1
            continue
        pending.append(task)

    def _work(task: FetchTask) -> tuple[FetchTask, str | None]:
        try:
            fields = fetch_fn(task.valid_time, task.lat, task.lon)
            save_cached_fields(cache_path(cache_dir, task), fields, task)
            return task, None
        except Exception as exc:  # noqa: BLE001 - one bad sample must not kill the run
            return task, f"{type(exc).__name__}: {exc}"

    failures: list[tuple[FetchTask, str]] = []
    n_fetched = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_work, task) for task in pending]
        for i, future in enumerate(as_completed(futures), start=1):
            task, error = future.result()
            if error is None:
                n_fetched += 1
            else:
                failures.append((task, error))
            if progress_every and i % progress_every == 0:
                elapsed = time.time() - t0
                rate = i / elapsed if elapsed > 0 else 0.0
                print(
                    f"[{label}] {i}/{len(pending)} done "
                    f"({n_fetched} ok, {len(failures)} failed) "
                    f"{rate:.2f}/s, {elapsed:.0f}s elapsed",
                    flush=True,
                )

    return FetchCacheReport(
        n_total=len(tasks),
        n_fetched=n_fetched,
        n_skipped=n_skipped,
        failures=failures,
        elapsed_s=time.time() - t0,
    )


# --------------------------------------------------------------------------- #
# Durable archive sync
# --------------------------------------------------------------------------- #


class ArchiveClient(Protocol):
    """Whatever `run_fetch_cache` caches locally still lives only on one VM's
    disk -- gone on teardown, and un-shared across VMs. This is the surface a
    durable off-box store must expose to receive it; `tracking.checkpoint_store
    .CheckpointStore` already satisfies it structurally (same put/get/exists
    duck-typed pattern used for MLflow-optional tracking), so no new backend
    is needed -- it's reused here under a different key prefix, not
    subclassed or renamed, since ``S3_ARTIFACT_*`` already names a general
    artifact bucket, not a checkpoint-only one.
    """

    def exists(self, key: str) -> bool: ...
    def upload(self, local_path: Path | str, key: str) -> str: ...


def archive_key(prefix: str, task: FetchTask) -> str:
    return f"{prefix}/{task.storm_id}/{task.valid_time:%Y%m%d%H}.npz"


@dataclass(slots=True)
class SyncReport:
    n_total: int
    n_uploaded: int
    n_already_archived: int
    n_missing_local: int
    failures: list[tuple[FetchTask, str]] = field(default_factory=list)
    elapsed_s: float = 0.0

    @property
    def n_failed(self) -> int:
        return len(self.failures)


def sync_cache_to_archive(
    tasks: list[FetchTask],
    cache_dir: Path | str,
    archive: ArchiveClient,
    *,
    prefix: str,
    max_workers: int = 8,
    progress_every: int = 50,
    label: str = "gridded_cache",
) -> SyncReport:
    """Upload every locally cached fix under ``cache_dir`` to ``archive`` that
    isn't already there.

    The durable-archive counterpart to `run_fetch_cache`'s local
    ``skip_existing``: existence is checked in the archive itself (a
    ``head_object``-backed call, not a separately tracked ledger), so
    re-running this after a partial upload, or as a one-time backfill of
    files fetched before archiving existed, just picks up whatever isn't
    there yet -- same resumability shape as the fetch side, one layer out.
    A task whose local ``.npz`` doesn't exist yet (not yet fetched) is
    counted in ``n_missing_local`` rather than attempted or treated as a
    failure -- sync and fetch are separate, independently resumable passes.
    """
    cache_dir = Path(cache_dir)
    n_missing_local = 0
    to_check: list[tuple[FetchTask, Path, str]] = []
    for task in tasks:
        local_path = cache_path(cache_dir, task)
        if not local_path.exists():
            n_missing_local += 1
            continue
        to_check.append((task, local_path, archive_key(prefix, task)))

    def _work(item: tuple[FetchTask, Path, str]) -> tuple[FetchTask, str | None, bool]:
        task, local_path, key = item
        try:
            if archive.exists(key):
                return task, None, False
            archive.upload(local_path, key)
            return task, None, True
        except Exception as exc:  # noqa: BLE001 - one bad upload must not kill the run
            return task, f"{type(exc).__name__}: {exc}", False

    failures: list[tuple[FetchTask, str]] = []
    n_uploaded = 0
    n_already_archived = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_work, item) for item in to_check]
        for i, future in enumerate(as_completed(futures), start=1):
            task, error, uploaded = future.result()
            if error is not None:
                failures.append((task, error))
            elif uploaded:
                n_uploaded += 1
            else:
                n_already_archived += 1
            if progress_every and i % progress_every == 0:
                elapsed = time.time() - t0
                rate = i / elapsed if elapsed > 0 else 0.0
                print(
                    f"[{label}-archive] {i}/{len(to_check)} checked "
                    f"({n_uploaded} uploaded, {n_already_archived} already there, "
                    f"{len(failures)} failed) {rate:.2f}/s, {elapsed:.0f}s elapsed",
                    flush=True,
                )

    return SyncReport(
        n_total=len(tasks),
        n_uploaded=n_uploaded,
        n_already_archived=n_already_archived,
        n_missing_local=n_missing_local,
        failures=failures,
        elapsed_s=time.time() - t0,
    )
