"""Concurrent real-ERA5 fetch and local cache for Stage A training data.

PLAN.md §4 "Gridded fields" / #22. A single real ERA5 sample fetch takes
~7-15s (docs/capacity_ablation.md's benchmark; docs/train_infrastructure.md
for the co-located-VM figure) -- dominated by ARCO-ERA5's chunk
decompression, not just network latency, so running from a co-located GCP
VM helps but doesn't remove the cost. The training split alone is ~16k
fixes; fetched sequentially that is tens of hours. This module fetches
concurrently -- the work is I/O-bound (waiting on GCS chunk reads), so a
thread pool gets a real (if sub-linear in practice -- see
docs/train_infrastructure.md's measured throughput) speedup -- and caches
each sample to disk as a compressed ``.npz``, so:

* a training loop reads from local disk, not the network, on every epoch
* the fetch itself is resumable -- a Spot preemption or an interrupted run
  just needs :func:`run_fetch_cache` called again; already-cached samples
  are skipped by default (``skip_existing=True``)

Thin wrapper around :mod:`anemoi.data.gridded_cache`'s source-agnostic
engine -- this module supplies only the ERA5-specific default fetch
function. See :mod:`anemoi.data.gdas_cache` for the GDAS/Stage B analog.

Known gap, not solved here: :func:`anemoi.data.real_gridded._crop_box`'s
storm-relative box is always an odd side length (``2*n+1``), so it can never
exactly match :func:`anemoi.models.transformer.build_transformer`'s default
40x40 grid (needs a side divisible by ``patch_size``). Fixing that is a
training-loop-building concern (resample/pad/adjust ``patch_size``), not a
fetch-caching one -- the raw fetched box is cached as-is and reconciled
downstream.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .besttrack import Track
from .features import GriddedFields
from .gridded_cache import (
    FetchCacheReport,
    FetchTask,
    FieldsFetcher,
    build_fetch_tasks,
    cache_path,
    load_cached_fields,
    save_cached_fields,
)
from .gridded_cache import run_fetch_cache as _run_fetch_cache

__all__ = [
    "FetchCacheReport",
    "FetchTask",
    "FieldsFetcher",
    "build_fetch_tasks",
    "cache_path",
    "load_cached_fields",
    "run_fetch_cache",
    "save_cached_fields",
]


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
    threads.
    """
    fetch_fn = fetch_fn if fetch_fn is not None else _default_fetch_fn(box_deg)
    return _run_fetch_cache(
        tracks,
        cache_dir,
        fetch_fn,
        max_workers=max_workers,
        skip_existing=skip_existing,
        progress_every=progress_every,
        label="era5_cache",
    )
