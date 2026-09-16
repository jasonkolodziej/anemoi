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
"""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

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
