"""Concurrent real-ERA5 fetch and local cache for Stage A training data.

PLAN.md §4 "Gridded fields" / #22. A single real ERA5 sample fetch takes
~7-15s (docs/capacity_ablation.md's benchmark; docs/train_infrastructure.md
for the co-located-VM figure) -- dominated by ARCO-ERA5's chunk
decompression, not just network latency, so running from a co-located GCP
VM helps but doesn't remove the cost. The training split alone is ~16k
fixes; fetched sequentially that is tens of hours. This module fetches
concurrently -- the work is I/O-bound (waiting on GCS chunk reads), so a
thread pool gets close to linear speedup -- and caches each sample to disk
as a compressed ``.npz``, so:

* a training loop reads from local disk, not the network, on every epoch
* the fetch itself is resumable -- a Spot preemption or an interrupted run
  just needs :func:`run_fetch_cache` called again; already-cached samples
  are skipped by default (``skip_existing=True``)

Known gap, not solved here: :func:`anemoi.data.real_gridded._crop_box`'s
storm-relative box is always an odd side length (``2*n+1``), so it can never
exactly match :func:`anemoi.models.transformer.build_transformer`'s default
40x40 grid (needs a side divisible by ``patch_size``). Fixing that is a
training-loop-building concern (resample/pad/adjust ``patch_size``), not a
fetch-caching one -- the raw fetched box is cached as-is and reconciled
downstream.
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
    """One task per fix across all given tracks -- the sample list a Stage A
    cache run needs to cover."""
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


def _default_fetch_fn(box_deg: float) -> FieldsFetcher:
    """Build a fetch function sharing one ARCO-ERA5 store handle across every
    call -- opening the store per sample costs ~1-2s each (avoidable, see
    ``real_gridded.open_era5_store``'s docstring), which matters at
    thousands of samples even though it's noise for a single fetch."""
    from .real_gridded import era5_to_gridded_fields, open_era5, open_era5_store

    store = open_era5_store()

    def fetch(valid_time: datetime, lat: float, lon: float) -> GriddedFields:
        ds = open_era5(valid_time, store=store)
        return era5_to_gridded_fields(ds, center_lat=lat, center_lon=lon, box_deg=box_deg)

    return fetch


def run_fetch_cache(
    tracks: list[Track],
    cache_dir: Path | str,
    *,
    box_deg: float = 10.0,
    max_workers: int = 8,
    skip_existing: bool = True,
    fetch_fn: FieldsFetcher | None = None,
    progress_every: int = 50,
) -> FetchCacheReport:
    """Fetch real ERA5 GriddedFields for every fix across ``tracks``,
    concurrently, caching each to ``cache_dir``.

    ``fetch_fn`` -- ``(valid_time, lat, lon) -> GriddedFields`` -- is
    injectable so tests can supply a fast synthetic fetcher instead of
    hitting the network; the real default (built by :func:`_default_fetch_fn`
    when omitted) opens the ARCO-ERA5 store once and shares it across worker
    threads. One failed sample is recorded in the report rather than
    aborting the run -- a network blip on sample 8,000 of 16,474 should not
    discard everything fetched so far.
    """
    cache_dir = Path(cache_dir)
    tasks = build_fetch_tasks(tracks)
    fetch_fn = fetch_fn if fetch_fn is not None else _default_fetch_fn(box_deg)

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
                    f"[era5_cache] {i}/{len(pending)} done "
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
