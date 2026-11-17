"""The storm's track in the GFS run a cycle reads: a vortex tracker.

A cycle at ``t`` reads the GFS run of ``t-6`` (`steering.NWP_LAG_H`). This
follows the storm through that run's forecast fields, from f006 (valid
``t``) to f126 (valid ``t+120 h``), so the Group 1 models can predict a
correction to GFS's own track (`training.track_prior`) instead of the
whole track.

It is computed from fields Anemoi fetches itself, in training
(``anemoi gfs-track-cache``) and in serving
(`training.real_inference_live.fetch_live_gfs_track`) the same way. NHC's
a-deck rows for the same run (AVNO, AVNI) are written after the cycle and
are verification only (Decision Log 66), so they can't be a model input;
they are what this track is scored against (`baseline-backtest
--gfs-track-dir`).

The tracker, per lead: the 850 hPa relative-vorticity maximum and the
sea-level-pressure minimum, each smoothed over `SMOOTH_CELLS`, within
`SEARCH_RADIUS_DEG` of a first guess (the previous position moved on by the
previous step's motion). The two are averaged when they agree; when they
don't, the one nearer the guess is taken. A lead with neither ends the
track: GFS has dissipated the storm.
"""

from __future__ import annotations

import io
import time
from collections import defaultdict
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from .real_gridded import (
    GDAS_MSLP_KEY,
    GRID_NLAT,
    GRID_NLON,
    GRID_RESOLUTION_DEG,
    fetch_grib2_messages,
    gfs_url,
)
from .steering import NWP_LAG_H, shard_times
from .steering import require_meta as _require_meta
from .steering import write_meta as _write_meta

#: Hours after the cycle's valid time the storm is located at: every 6 h,
#: as operational trackers step, so a storm that stalls or accelerates is
#: still within the search radius of where its last motion puts it (at 12 h
#: steps the tracker lost Helene 2024 when it stalled inland). Every
#: forecast lead (`models.base.DEFAULT_LEADS`) is one of them.
TRACK_LEADS_H: tuple[int, ...] = tuple(range(0, 121, 6))

#: How far from the first guess a centre is looked for.
SEARCH_RADIUS_DEG = 3.5
FIRST_SEARCH_RADIUS_DEG = 3.0
#: Half-width, in 0.25 deg cells, of the box each field is averaged over
#: before its extremum is taken (2 -> 1.25 deg): one grid cell's noise
#: shouldn't place the centre.
SMOOTH_CELLS = 2
#: The smoothed cyclonic 850 hPa vorticity below which there is no vortex.
MIN_VORTICITY_S = 3.0e-5
#: A pressure minimum this close to the edge of the search disc is the
#: environment's gradient, not a centre.
MSLP_EDGE_FRACTION = 0.9
#: The two fixes "agree" within this distance.
AGREE_DEG = 2.0
#: Cells within this of an extremum are averaged, weighted by how far past
#: the disc's median they are, to place the centre between grid points.
CENTROID_DEG = 1.0

TRACK_VERSION = 2
_EARTH_RADIUS_M = 6_371_008.8


@dataclass(frozen=True, slots=True)
class LeadField:
    """One lead's global fields on the 0.25 deg lattice (90N first, 0E first)."""

    u850: np.ndarray
    v850: np.ndarray
    mslp: np.ndarray


@dataclass(frozen=True, slots=True)
class TrackTask:
    """One (storm, cycle) to track: where the storm is at the cycle's valid
    time, and its motion over the 6 h before it (degrees), which seeds the
    first step's guess."""

    storm_id: str
    valid_time: datetime
    lat: float
    lon: float
    dlat_6h: float = 0.0
    dlon_6h: float = 0.0


def track_targets() -> list[tuple[str, str, tuple]]:
    return [
        ("UGRD", "850 mb", ("UGRD", 850)),
        ("VGRD", "850 mb", ("VGRD", 850)),
        (GDAS_MSLP_KEY[0], GDAS_MSLP_KEY[1], GDAS_MSLP_KEY),
    ]


def lead_field(messages: dict) -> LeadField:
    out = LeadField(
        u850=np.asarray(messages[("UGRD", 850)], dtype=np.float32),
        v850=np.asarray(messages[("VGRD", 850)], dtype=np.float32),
        mslp=np.asarray(messages[GDAS_MSLP_KEY], dtype=np.float32),
    )
    for arr in (out.u850, out.v850, out.mslp):
        if arr.shape != (GRID_NLAT, GRID_NLON):
            raise ValueError(f"unexpected grid {arr.shape}, expected {(GRID_NLAT, GRID_NLON)}")
    return out


def fetch_lead_field(valid_time: datetime, lead_h: int, *, session=None) -> LeadField:
    """The fields valid ``lead_h`` after ``valid_time``, from the run
    ``NWP_LAG_H`` before ``valid_time``."""
    url = gfs_url(valid_time + timedelta(hours=lead_h), lead_h + NWP_LAG_H)
    return lead_field(fetch_grib2_messages(url, track_targets(), session=session))


# --- locating the centre in one field ---------------------------------------


def _box_mean(a: np.ndarray, k: int) -> np.ndarray:
    """Mean over a (2k+1)^2 box, edges repeated."""
    if k <= 0:
        return a
    padded = np.pad(a, k, mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, (2 * k + 1, 2 * k + 1))
    return windows.mean(axis=(-1, -2))


def _window(fld: LeadField, lat: float, lon: float, radius_deg: float):
    """The fields on the cells within ``radius_deg`` (plus the smoothing
    margin) of (lat, lon): ``(lats, lons, u, v, p)``, longitudes continuous
    across the dateline and Greenwich."""
    res = GRID_RESOLUTION_DEG
    margin = SMOOTH_CELLS + 1
    half = int(np.ceil(radius_deg / res)) + margin
    # The search disc measures east-west distance on the ground, so in
    # degrees of longitude it is 1/cos(lat) wider than it is tall: at 60N a
    # centre 6 deg east is 3 deg away. Never more than the whole circle.
    stretch = max(np.cos(np.radians(lat)), 1e-6)
    half_lon = min(int(np.ceil(radius_deg / (res * stretch))) + margin, GRID_NLON // 2 - 1)
    i0 = int(round((90.0 - lat) / res))
    j0 = int(round((lon % 360.0) / res))
    rows = np.arange(max(i0 - half, 0), min(i0 + half, GRID_NLAT - 1) + 1)
    cols = np.arange(j0 - half_lon, j0 + half_lon + 1)
    lats = 90.0 - rows * res
    lons = cols * res
    lons = lons - 360.0 * np.round((lons.mean() - lon) / 360.0)
    take = np.ix_(rows, cols % GRID_NLON)
    return lats, lons, fld.u850[take], fld.v850[take], fld.mslp[take]


def _vorticity(lats: np.ndarray, lons: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Relative vorticity (1/s) on a regular lat/lon window."""
    phi = np.radians(lats)[:, None]
    dv_dlam = np.gradient(v.astype(np.float64), np.radians(lons), axis=1)
    du_dphi = np.gradient(u.astype(np.float64), np.radians(lats), axis=0)
    cos = np.maximum(np.cos(phi), 1e-6)
    return (dv_dlam / cos - du_dphi + u * np.tan(phi)) / _EARTH_RADIUS_M


def _centroid(
    lats: np.ndarray, lons: np.ndarray, weight: np.ndarray, at: tuple[int, int],
) -> tuple[float, float]:
    """The weighted mean position of the cells within `CENTROID_DEG` of
    ``at`` whose ``weight`` is positive."""
    lat0, lon0 = lats[at[0]], lons[at[1]]
    near = (
        (np.abs(lats[:, None] - lat0) <= CENTROID_DEG)
        & (np.abs(lons[None, :] - lon0) <= CENTROID_DEG)
        & (weight > 0)
    )
    w = np.where(near, weight, 0.0)
    total = w.sum()
    if total <= 0:
        return float(lat0), float(lon0)
    return (
        float((w * lats[:, None]).sum() / total),
        float((w * lons[None, :]).sum() / total),
    )


def locate(
    fld: LeadField, guess_lat: float, guess_lon: float, radius_deg: float = SEARCH_RADIUS_DEG,
) -> tuple[float, float] | None:
    """The storm's centre in ``fld`` near the guess, or None when the field
    has no vortex there. Longitude comes back in the guess's range."""
    lats, lons, u, v, p = _window(fld, guess_lat, guess_lon, radius_deg)
    dist = np.hypot(
        lats[:, None] - guess_lat,
        (lons[None, :] - guess_lon) * np.cos(np.radians(guess_lat)),
    )
    disc = dist <= radius_deg
    if not disc.any():
        return None

    cyclonic = _vorticity(lats, lons, u, v) * (1.0 if guess_lat >= 0 else -1.0)
    vort = _box_mean(cyclonic, SMOOTH_CELLS)
    pres = _box_mean(p.astype(np.float64), SMOOTH_CELLS)

    fixes: list[tuple[float, float]] = []
    at = np.unravel_index(np.argmax(np.where(disc, vort, -np.inf)), vort.shape)
    if vort[at] >= MIN_VORTICITY_S:
        fixes.append(_centroid(lats, lons, vort - 0.5 * vort[at], at))
    at = np.unravel_index(np.argmin(np.where(disc, pres, np.inf)), pres.shape)
    if dist[at] <= MSLP_EDGE_FRACTION * radius_deg:
        fixes.append(_centroid(lats, lons, np.median(pres[disc]) - pres, at))
    if not fixes:
        return None
    if len(fixes) == 2:
        (a_lat, a_lon), (b_lat, b_lon) = fixes
        apart = np.hypot(a_lat - b_lat, (a_lon - b_lon) * np.cos(np.radians(guess_lat)))
        if apart <= AGREE_DEG:
            return (a_lat + b_lat) / 2.0, (a_lon + b_lon) / 2.0
        fixes.sort(key=lambda f: np.hypot(
            f[0] - guess_lat, (f[1] - guess_lon) * np.cos(np.radians(guess_lat)),
        ))
    return fixes[0]


def track_many(fields: Iterable[LeadField], tasks: list[TrackTask]) -> list[np.ndarray]:
    """Each task's ``(len(TRACK_LEADS_H), 2)`` (lat, lon) positions through
    ``fields`` (one per `TRACK_LEADS_H`, read one at a time, so a caller may
    fetch them lazily), NaN from the lead GFS loses that storm. Stops
    reading once every storm is lost."""
    out = [np.full((len(TRACK_LEADS_H), 2), np.nan) for _ in tasks]
    motion = [(t.dlat_6h, t.dlon_6h) for t in tasks]
    alive = list(range(len(tasks)))
    k = -1
    for k, fld in enumerate(fields):
        if k >= len(TRACK_LEADS_H):
            raise ValueError(f"more than {len(TRACK_LEADS_H)} fields")
        still = []
        for i in alive:
            if k == 0:
                guess, radius = (tasks[i].lat, tasks[i].lon), FIRST_SEARCH_RADIUS_DEG
            else:
                guess = (out[i][k - 1, 0] + motion[i][0], out[i][k - 1, 1] + motion[i][1])
                radius = SEARCH_RADIUS_DEG
            fix = locate(fld, guess[0], guess[1], radius)
            if fix is None:
                continue
            out[i][k] = fix
            if k:
                motion[i] = (out[i][k, 0] - out[i][k - 1, 0], out[i][k, 1] - out[i][k - 1, 1])
            still.append(i)
        alive = still
        if not alive:
            break
    else:
        if k + 1 != len(TRACK_LEADS_H):
            raise ValueError(f"{k + 1} fields for {len(TRACK_LEADS_H)} leads")
    return out


def track_vortex(
    fields: Iterable[LeadField], lat: float, lon: float,
    dlat_6h: float = 0.0, dlon_6h: float = 0.0,
) -> np.ndarray:
    """`track_many` for one storm at ``(lat, lon)`` whose motion over the
    6 h before was ``(dlat_6h, dlon_6h)`` degrees."""
    task = TrackTask("", datetime.min, lat, lon, dlat_6h, dlon_6h)
    return track_many(fields, [task])[0]


# --- the cache -----------------------------------------------------------------


def gfs_track_meta() -> dict:
    """The settings the tracks are computed with: the cache's meta, and
    recorded on a model version that reads them (the ``track_prior_inputs``
    registry tag), so serving refuses a track computed another way."""
    return {
        "track_version": TRACK_VERSION,
        "leads_h": list(TRACK_LEADS_H),
        "nwp_lag_h": NWP_LAG_H,
        "search_radius_deg": SEARCH_RADIUS_DEG,
        "first_search_radius_deg": FIRST_SEARCH_RADIUS_DEG,
        "smooth_cells": SMOOTH_CELLS,
        "min_vorticity_s": MIN_VORTICITY_S,
        "mslp_edge_fraction": MSLP_EDGE_FRACTION,
        "agree_deg": AGREE_DEG,
        "centroid_deg": CENTROID_DEG,
    }


def gfs_track_meta_digest() -> str:
    import hashlib
    import json

    return hashlib.sha256(json.dumps(gfs_track_meta(), sort_keys=True).encode()).hexdigest()[:12]


def require_meta(cache_dir: Path | str) -> None:
    _require_meta(cache_dir, gfs_track_meta(), what="GFS track")


def track_path(cache_dir: Path | str, storm_id: str, valid_time: datetime) -> Path:
    return Path(cache_dir) / storm_id / f"{valid_time:%Y%m%d%H}.npz"


def save_track(path: Path, positions: np.ndarray, task: TrackTask) -> None:
    buf = io.BytesIO()
    np.savez_compressed(
        buf, positions=positions.astype(np.float32),
        lat=np.float64(task.lat), lon=np.float64(task.lon),
        cycle=np.bytes_((task.valid_time - timedelta(hours=NWP_LAG_H)).isoformat()),
        track_version=np.int64(TRACK_VERSION),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".npz.part")
    tmp.write_bytes(buf.getvalue())
    tmp.replace(path)


def load_track(path: Path | str) -> np.ndarray:
    with np.load(path) as z:
        if int(z["track_version"]) != TRACK_VERSION:
            raise ValueError(
                f"{path}: track version {int(z['track_version'])}, expected {TRACK_VERSION}"
            )
        return np.asarray(z["positions"], dtype=np.float64)


def cached_track(cache_dir: Path | str, storm_id: str, valid_time: datetime) -> np.ndarray | None:
    """The cached ``(len(TRACK_LEADS_H), 2)`` positions for a cycle, or None
    when the cache has none."""
    path = track_path(cache_dir, storm_id, valid_time)
    return load_track(path) if path.exists() else None


def track_tasks(tracks: Iterable) -> list[TrackTask]:
    """One task per fix of each track, with the 6 h motion into it (zero
    for a storm's first fix, or after a gap)."""
    out = []
    for track in tracks:
        prev = None
        for fix in track.fixes:
            dlat = dlon = 0.0
            if prev is not None and fix.valid_time - prev.valid_time == timedelta(hours=6):
                dlat, dlon = fix.lat - prev.lat, fix.lon - prev.lon
            out.append(TrackTask(track.storm_id, fix.valid_time, fix.lat, fix.lon, dlat, dlon))
            prev = fix
    return out


FieldFetcher = Callable[[datetime, int], LeadField]


@dataclass
class GfsTrackCacheReport:
    n_times: int = 0
    n_written: int = 0
    n_skipped: int = 0
    n_failed: int = 0
    #: Tracks written with no position at the first lead: GFS had no vortex.
    n_no_vortex: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)
    elapsed_s: float = 0.0


def run_gfs_track_cache(
    tasks: Iterable[TrackTask],
    cache_dir: Path | str,
    *,
    fetch: FieldFetcher | None = None,
    max_workers: int = 4,
    skip_existing: bool = True,
    shard_index: int = 0,
    shard_count: int = 1,
    progress_every: int = 25,
) -> GfsTrackCacheReport:
    """Track every task's storm and cache the positions. A valid time's
    fields are fetched once (one file per lead, three messages each, one
    lead held at a time) and
    shared by every storm active then; valid times are cut into shards for
    parallel tasks, as `steering.run_steering_cache` does."""
    cache_dir = Path(cache_dir)
    _write_meta(cache_dir, gfs_track_meta())
    by_time: dict[datetime, list[TrackTask]] = defaultdict(list)
    for task in tasks:
        by_time[task.valid_time].append(task)
    times = shard_times(list(by_time), shard_index, shard_count)
    report = GfsTrackCacheReport(n_times=len(times))
    started = time.monotonic()

    if fetch is None:
        import requests  # noqa: PLC0415

        session = requests.Session()

        def fetch(t: datetime, lead: int) -> LeadField:
            return fetch_lead_field(t, lead, session=session)

    def one_time(t: datetime) -> tuple[int, int, int, list[tuple[str, str]]]:
        todo = [task for task in by_time[t]
                if not (skip_existing and track_path(cache_dir, task.storm_id, t).exists())]
        if not todo:
            return 0, len(by_time[t]), 0, []
        try:
            tracked = track_many((fetch(t, lead) for lead in TRACK_LEADS_H), todo)
        except Exception as exc:  # noqa: BLE001 -- one bad cycle mustn't stop the shard
            return 0, 0, 0, [(f"{task.storm_id} {t:%Y%m%d%H}", repr(exc)) for task in todo]
        written, no_vortex, failed = 0, 0, []
        for task, positions in zip(todo, tracked, strict=True):
            try:
                save_track(track_path(cache_dir, task.storm_id, t), positions, task)
                written += 1
                no_vortex += int(not np.isfinite(positions[0]).all())
            except Exception as exc:  # noqa: BLE001
                failed.append((f"{task.storm_id} {t:%Y%m%d%H}", repr(exc)))
        return written, len(by_time[t]) - len(todo), no_vortex, failed

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(one_time, t) for t in times]
        for i, fut in enumerate(as_completed(futures), start=1):
            written, skipped, no_vortex, failed = fut.result()
            report.n_written += written
            report.n_skipped += skipped
            report.n_no_vortex += no_vortex
            report.n_failed += len(failed)
            report.failures.extend(failed)
            if progress_every and i % progress_every == 0:
                print(f"  {i}/{len(times)} times: {report.n_written} written, "
                      f"{report.n_skipped} skipped, {report.n_failed} failed", flush=True)
    report.elapsed_s = time.monotonic() - started
    return report
