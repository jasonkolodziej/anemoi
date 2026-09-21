"""Concurrent real-GDAS fetch and local cache for Stage B training data.

PLAN.md §4 "Gridded fields" / #22. GDAS's operational analysis fixes are
served as a single GRIB2 file per cycle (AWS Open Data), byte-range fetched
per message (see ``real_gridded.fetch_gdas_grib2_fields``) rather than read
from a pre-chunked Zarr store the way ERA5 is -- each sample costs ~8 HTTP
requests to the same host instead of one Zarr chunk read. Thin wrapper
around :mod:`anemoi.data.gridded_cache`'s source-agnostic engine -- this
module supplies only the GDAS-specific default fetch function (a shared
``requests.Session`` for connection-pool reuse across samples, in place of
ERA5's shared Zarr store handle). See :mod:`anemoi.data.era5_cache` for the
ERA5/Stage A analog; the concurrency, caching and resumability behaviour is
identical.

Needs the ``gridded`` extra's ``eccodes``, which -- unlike xarray for ERA5
-- has a real, observed failure mode where the package imports but its
native library doesn't load (see ``real_gridded.require_gdas_deps``'s
docstring). If that's broken on your machine, this module still imports
fine (the eccodes import is deferred into the fetch call, same as
``real_gridded.fetch_gdas_grib2_fields`` itself); only actually calling
:func:`run_fetch_cache` will raise.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .besttrack import Track
from .features import GriddedFields
from .gridded_cache import FetchCacheReport, FieldsFetcher, filter_tracks_by_min_valid_time
from .gridded_cache import run_fetch_cache as _run_fetch_cache

__all__ = ["GDAS_ARCHIVE_START", "fetch_one", "run_fetch_cache"]

#: Earliest date with real data in noaa-gfs-bdp-pds, verified via direct S3
#: `list-type=2` listing (2026-09-16) -- the bucket has no documented
#: retention policy, so this is an observed floor, not a guaranteed one.
#: `data.splits`' season boundaries predate this by decades (Stage A/ERA5
#: needs them to); `run_fetch_cache` filters against this separately so
#: fetching an early split doesn't spend a request per fix on a guaranteed
#: 404. See docs/train_infrastructure.md and data.sources's gdas_gfs entry.
GDAS_ARCHIVE_START = datetime(2021, 1, 1, tzinfo=UTC)


def _default_fetch_fn(box_deg: float) -> FieldsFetcher:
    """Build a fetch function sharing one ``requests.Session`` across every
    call -- each sample already makes ~8 requests to the same NOAA host, so
    a shared connection pool matters more here than it does for ERA5's
    single-Zarr-store-open saving."""
    import requests

    from .real_gridded import fetch_gdas_grib2_fields, gdas_to_gridded_fields

    session = requests.Session()

    def fetch(valid_time: datetime, lat: float, lon: float) -> GriddedFields:
        messages = fetch_gdas_grib2_fields(valid_time, session=session)
        return gdas_to_gridded_fields(
            messages, center_lat=lat, center_lon=lon, valid_time=valid_time, box_deg=box_deg
        )

    return fetch


def fetch_one(
    valid_time: datetime, lat: float, lon: float, *, box_deg: float = 10.0
) -> GriddedFields:
    """Fetch real GDAS GriddedFields for one specific sample, on demand --
    not a batch. `training.real_inference_live`'s on-demand cache-miss
    fallback is the motivating caller: `_current_fields` needs exactly one
    window's fields for a real live cycle, not `run_fetch_cache`'s whole
    tracks-list/concurrency/resumability machinery built for training-time
    bulk fetches. GDAS, not ERA5, because live/operational inference is
    always the operational flavor (`data.sources.Flavor.GDAS_FINETUNE` --
    every real registered version already requires it, see
    `tracking.registry.ModelRegistry.register`), and ERA5 is a Stage A
    pretraining-only reanalysis source, not meant to stand in for "real
    data right now."

    A single call, not worth sharing a `requests.Session` across -- that
    optimisation is for `run_fetch_cache`'s thousands of calls.
    """
    return _default_fetch_fn(box_deg)(valid_time, lat, lon)


def run_fetch_cache(
    tracks: list[Track],
    cache_dir: Path | str,
    *,
    box_deg: float = 10.0,
    max_workers: int = 4,
    skip_existing: bool = True,
    fetch_fn: FieldsFetcher | None = None,
    progress_every: int = 50,
    min_valid_time: datetime | None = GDAS_ARCHIVE_START,
) -> FetchCacheReport:
    """Fetch real GDAS GriddedFields for every fix across ``tracks``,
    concurrently, caching each to ``cache_dir``.

    ``max_workers`` defaults lower than ERA5's (4 vs. 8): GDAS analyses are
    only synoptic-hour (00/06/12/18Z) files, so many storm fixes share the
    same underlying GRIB2 file and byte ranges within it -- a lower
    concurrency avoids hammering one NOAA object with many simultaneous
    range requests. ``fetch_fn`` -- ``(valid_time, lat, lon) ->
    GriddedFields`` -- is injectable so tests can supply a fast synthetic
    fetcher instead of hitting the network.

    ``min_valid_time`` defaults to :data:`GDAS_ARCHIVE_START` and drops fixes
    earlier than it before fetching -- ``data.splits``' season boundaries are
    shared with Stage A/ERA5 and go back to 1980, decades before GDAS's real
    archive starts, so an unfiltered ``--split train`` run would spend one
    request per fix discovering each one 404s. Pass ``None`` to disable.
    """
    fetch_fn = fetch_fn if fetch_fn is not None else _default_fetch_fn(box_deg)
    if min_valid_time is not None:
        tracks = filter_tracks_by_min_valid_time(tracks, min_valid_time)
    return _run_fetch_cache(
        tracks,
        cache_dir,
        fetch_fn,
        max_workers=max_workers,
        skip_existing=skip_existing,
        progress_every=progress_every,
        label="gdas_cache",
    )
