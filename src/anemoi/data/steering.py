"""Forecast-lead steering along a GFS-advected track (docs/skill_gap_plan.md
Phase 1, step 2: the steering-along-track spike).

The models see one GFS snapshot, the t-6 cycle's f006 valid at the cycle
time ``t`` (#215), so nothing tells them how the steering flow evolves over
the next 48 h. This module reads the same t-6 run's forecasts valid at
``t, t+6, ..., t+48`` (``f006 ... f054``) and summarises the flow where the
storm is likely to be:

* **Deep-layer mean (DLM) wind** over 850-200 hPa, pressure-weighted
  (trapezoid over the six levels, :data:`DLM_WEIGHTS`), and the 850-200 hPa
  **shear**, each averaged over a disc of :data:`DISC_RADIUS_DEG` around a
  point.
* **The point** follows a beta-advection track computed from the same
  fields: start at the storm's position at ``t``; every 6 h move with the
  disc-mean DLM wind plus a fixed beta drift (:data:`BETA_DRIFT_MS`). No
  a-deck track is read (Decision Log 66 keeps a-decks verification-only),
  so training and serving compute the track the same way from the same run.

The feature block per window is ``(len(STEERING_LEADS_H), 6)``: for each lead
``(u_dlm, v_dlm, u_shear, v_shear)`` in m/s and the track's ``(dx_east_nm,
dy_north_nm)`` from the start. :func:`steering_vector` flattens it.

The cache mirrors ``data.gridded_cache``: one ``.npz`` per (storm, valid
time) under ``<cache_dir>/<storm_id>/<YYYYMMDDHH>.npz``, centred on the same
best-track position as the gridded crop it goes with (Decision Log 67 covers
the working-fix offset live).
"""

from __future__ import annotations

import io
import json
import math
import time
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from .gridded_cache import FetchTask
from .real_gridded import GRID_NLAT, GRID_NLON, GRID_RESOLUTION_DEG, fetch_grib2_messages, gfs_url

#: Hours after the cycle time ``t``; each is read from the t-6 run, so as
#: forecast hour ``lead + NWP_LAG_H``.
STEERING_LEADS_H: tuple[int, ...] = (0, 6, 12, 18, 24, 30, 36, 42, 48)
#: The run is the same t-6 GFS cycle Stage B's crops come from (#215).
NWP_LAG_H = 6

STEERING_LEVELS_HPA: tuple[int, ...] = (850, 700, 500, 300, 250, 200)
#: Trapezoid pressure weights over STEERING_LEVELS_HPA (hPa; sum 650 = 850-200).
DLM_WEIGHTS: tuple[float, ...] = (75.0, 175.0, 200.0, 125.0, 50.0, 25.0)

#: Disc the flow is averaged over: wide enough that the storm's own
#: symmetric circulation mostly cancels, as in deep-layer steering analyses.
DISC_RADIUS_DEG = 5.0
#: Beta drift added to the steering flow, m/s (east, north): about 2 m/s
#: toward the northwest, the Northern Hemisphere value. Every basin trained
#: on (AL, EP, CP) is northern.
BETA_DRIFT_MS: tuple[float, float] = (-1.4, 1.4)

FEATURE_NAMES: tuple[str, ...] = (
    "u_dlm_ms", "v_dlm_ms", "u_shear_ms", "v_shear_ms", "dx_east_nm", "dy_north_nm",
)
STEERING_DIM = len(STEERING_LEADS_H) * len(FEATURE_NAMES)

#: Bump when the features' definition changes; recorded in the cache's meta.
FEATURE_VERSION = 1
CACHE_META_NAME = "_meta.json"

_M_PER_DEG = 111_195.0
_M_PER_NM = 1852.0
_STEP_S = 6 * 3600.0


def steering_targets() -> list[tuple[str, str, tuple[str, int]]]:
    return [(sn, f"{p} mb", (sn, p)) for p in STEERING_LEVELS_HPA for sn in ("UGRD", "VGRD")]


@dataclass(frozen=True, slots=True)
class LeadFlow:
    """One lead's global flow summaries on the 0.25 deg lattice (90N first,
    0E first), float32."""

    u_dlm: np.ndarray
    v_dlm: np.ndarray
    u_shear: np.ndarray
    v_shear: np.ndarray


def lead_flow(messages: dict[tuple[str, int], np.ndarray]) -> LeadFlow:
    """DLM wind and 850-200 hPa shear from one file's UGRD/VGRD messages."""
    total = sum(DLM_WEIGHTS)
    pairs = list(zip(STEERING_LEVELS_HPA, DLM_WEIGHTS, strict=True))
    u = sum(w * messages[("UGRD", p)] for p, w in pairs) / total
    v = sum(w * messages[("VGRD", p)] for p, w in pairs) / total
    for arr in (u, v):
        if arr.shape != (GRID_NLAT, GRID_NLON):
            raise ValueError(f"expected a ({GRID_NLAT}, {GRID_NLON}) grid, got {arr.shape}")
    return LeadFlow(
        u_dlm=np.asarray(u, dtype=np.float32),
        v_dlm=np.asarray(v, dtype=np.float32),
        u_shear=np.asarray(messages[("UGRD", 200)] - messages[("UGRD", 850)], dtype=np.float32),
        v_shear=np.asarray(messages[("VGRD", 200)] - messages[("VGRD", 850)], dtype=np.float32),
    )


def disc_mean(
    values: np.ndarray, lat: float, lon: float, radius_deg: float = DISC_RADIUS_DEG,
) -> float:
    """Area-weighted (cos latitude) mean of a global lattice field over the
    cells within ``radius_deg`` of great-circle distance of ``(lat, lon)``;
    NaN cells are ignored. Wraps at 0/360."""
    res = GRID_RESOLUTION_DEG
    n_lat = int(math.ceil(radius_deg / res))
    i0 = int(round((90.0 - lat) / res))
    rows = np.arange(max(i0 - n_lat, 0), min(i0 + n_lat, GRID_NLAT - 1) + 1)
    lats = 90.0 - rows * res
    coslat = max(math.cos(math.radians(lat)), 0.05)
    n_lon = int(math.ceil(radius_deg / res / coslat))
    j0 = int(round((lon % 360.0) / res))
    cols = np.arange(j0 - n_lon, j0 + n_lon + 1) % GRID_NLON
    lons = cols * res
    lat_r, lon_r = np.radians(lats)[:, None], np.radians(lons)[None, :]
    plat, plon = math.radians(lat), math.radians(lon % 360.0)
    cos_d = (np.sin(plat) * np.sin(lat_r) + np.cos(plat) * np.cos(lat_r) * np.cos(lon_r - plon))
    dist = np.degrees(np.arccos(np.clip(cos_d, -1.0, 1.0)))
    block = values[np.ix_(rows, cols)].astype(np.float64)
    weight = np.where((dist <= radius_deg) & np.isfinite(block), np.cos(lat_r), 0.0)
    total = weight.sum()
    if total <= 0:
        return float("nan")
    return float(np.nansum(np.where(weight > 0, block, 0.0) * weight) / total)


def steering_features(
    flows: Sequence[LeadFlow], lat0: float, lon0: float,
    *, beta_drift_ms: tuple[float, float] = BETA_DRIFT_MS, radius_deg: float = DISC_RADIUS_DEG,
) -> np.ndarray:
    """``(len(flows), 6)`` features along the beta-advection track from
    ``(lat0, lon0)``; ``flows[k]`` is valid ``6k`` h after the start."""
    out = np.zeros((len(flows), len(FEATURE_NAMES)), dtype=np.float32)
    lat, lon = lat0, lon0
    east_m = north_m = 0.0
    for k, flow in enumerate(flows):
        u = disc_mean(flow.u_dlm, lat, lon, radius_deg)
        v = disc_mean(flow.v_dlm, lat, lon, radius_deg)
        us = disc_mean(flow.u_shear, lat, lon, radius_deg)
        vs = disc_mean(flow.v_shear, lat, lon, radius_deg)
        out[k] = (u, v, us, vs, east_m / _M_PER_NM, north_m / _M_PER_NM)
        if not all(math.isfinite(x) for x in (u, v)):
            raise ValueError(f"no steering flow at {lat:.2f}, {lon:.2f} (lead {6 * k} h)")
        de = (u + beta_drift_ms[0]) * _STEP_S
        dn = (v + beta_drift_ms[1]) * _STEP_S
        east_m += de
        north_m += dn
        lat = float(np.clip(lat + dn / _M_PER_DEG, -89.0, 89.0))
        lon = lon + de / (_M_PER_DEG * max(math.cos(math.radians(lat)), 0.05))
    return out


# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #


def steering_path(cache_dir: Path | str, storm_id: str, valid_time: datetime) -> Path:
    return Path(cache_dir) / storm_id / f"{valid_time:%Y%m%d%H}.npz"


def save_steering(path: Path, features: np.ndarray, task: FetchTask) -> None:
    """One write, as ``gridded_cache.save_cached_fields`` (gcsfuse streams it)."""
    buf = io.BytesIO()
    np.savez_compressed(
        buf, features=features.astype(np.float32),
        lat=np.float64(task.lat), lon=np.float64(task.lon),
        cycle=np.bytes_((task.valid_time - timedelta(hours=NWP_LAG_H)).isoformat()),
        feature_version=np.int64(FEATURE_VERSION),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".npz.part")
    tmp.write_bytes(buf.getvalue())
    tmp.replace(path)


def load_steering(path: Path | str) -> np.ndarray:
    with np.load(path) as z:
        if int(z["feature_version"]) != FEATURE_VERSION:
            raise ValueError(f"{path}: feature version {int(z['feature_version'])}, "
                             f"expected {FEATURE_VERSION}")
        return np.asarray(z["features"], dtype=np.float32)


def steering_vector(
    cache_dir: Path | str, storm_id: str, valid_time: datetime,
) -> np.ndarray | None:
    """The flattened ``(STEERING_DIM,)`` features for a window, or ``None``
    when the cache has none (or a non-finite value)."""
    path = steering_path(cache_dir, storm_id, valid_time)
    if not path.exists():
        return None
    vec = load_steering(path).reshape(-1)
    return vec if np.isfinite(vec).all() else None


def write_meta(cache_dir: Path | str) -> None:
    meta = {
        "feature_version": FEATURE_VERSION,
        "leads_h": list(STEERING_LEADS_H),
        "nwp_lag_h": NWP_LAG_H,
        "levels_hpa": list(STEERING_LEVELS_HPA),
        "dlm_weights": list(DLM_WEIGHTS),
        "disc_radius_deg": DISC_RADIUS_DEG,
        "beta_drift_ms": list(BETA_DRIFT_MS),
        "feature_names": list(FEATURE_NAMES),
    }
    path = Path(cache_dir) / CACHE_META_NAME
    path.parent.mkdir(parents=True, exist_ok=True)

    def check() -> bool:
        if not path.exists():
            return False
        old = json.loads(path.read_text())
        if old != meta:
            raise ValueError(f"{path} was written with other settings: {old}")
        return True

    if check():
        return
    # Parallel Cloud Run tasks all start here at once, on GCS FUSE. Create the
    # file exclusively, so a task never overwrites meta another task already
    # published (with other settings, it would mix incompatible entries).
    # A task that loses (the file exists, or the mount refuses the write with
    # a stale file handle) waits for the winner's file to become visible:
    # the mount caches "not found" for a few seconds (gcsfuse's negative stat
    # TTL is 5 s by default), so one read straight away isn't enough.
    text = json.dumps(meta, indent=1) + "\n"
    try:
        with path.open("x") as fh:
            fh.write(text)
        return
    except OSError as exc:
        error = exc
    deadline = time.monotonic() + META_WAIT_S
    while True:
        try:
            if check():
                return
        except (OSError, json.JSONDecodeError):
            pass  # not visible or not complete yet
        if time.monotonic() >= deadline:
            raise error
        time.sleep(META_POLL_S)


#: How long a task that lost the race to write the meta waits for the
#: winner's file, and how often it looks.
META_WAIT_S = 30.0
META_POLL_S = 1.0


FlowFetcher = Callable[[datetime, int], LeadFlow]


def fetch_lead_flow(valid_time: datetime, lead_h: int, *, session=None) -> LeadFlow:
    """The flow valid ``lead_h`` after ``valid_time``, from the run
    ``NWP_LAG_H`` before ``valid_time``."""
    target = valid_time + timedelta(hours=lead_h)
    url = gfs_url(target, lead_h + NWP_LAG_H)
    return lead_flow(fetch_grib2_messages(url, steering_targets(), session=session))


@dataclass
class SteeringCacheReport:
    n_times: int = 0
    n_written: int = 0
    n_skipped: int = 0
    n_failed: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)
    elapsed_s: float = 0.0


def group_by_time(tasks: Iterable[FetchTask]) -> dict[datetime, list[FetchTask]]:
    out: dict[datetime, list[FetchTask]] = defaultdict(list)
    for t in tasks:
        out[t.valid_time].append(t)
    return dict(sorted(out.items()))


def shard_times(times: Sequence[datetime], shard_index: int, shard_count: int) -> list[datetime]:
    if not 0 <= shard_index < shard_count:
        raise ValueError(f"shard {shard_index} of {shard_count}")
    return [t for i, t in enumerate(sorted(times)) if i % shard_count == shard_index]


def run_steering_cache(
    tasks: Iterable[FetchTask],
    cache_dir: Path | str,
    *,
    fetch: FlowFetcher | None = None,
    max_workers: int = 4,
    skip_existing: bool = True,
    shard_index: int = 0,
    shard_count: int = 1,
    progress_every: int = 25,
) -> SteeringCacheReport:
    """Write steering features for every task. The flow for a valid time is
    fetched once (nine files, twelve messages each) and shared by every storm
    active then; valid times are cut into shards for parallel tasks."""
    cache_dir = Path(cache_dir)
    write_meta(cache_dir)
    by_time = group_by_time(tasks)
    times = shard_times(list(by_time), shard_index, shard_count)
    report = SteeringCacheReport(n_times=len(times))
    started = time.monotonic()

    if fetch is None:
        import requests  # noqa: PLC0415

        session = requests.Session()

        def fetch(t: datetime, lead: int) -> LeadFlow:
            return fetch_lead_flow(t, lead, session=session)

    def one_time(t: datetime) -> tuple[int, int, list[tuple[str, str]]]:
        todo = [task for task in by_time[t]
                if not (skip_existing and steering_path(cache_dir, task.storm_id, t).exists())]
        if not todo:
            return 0, len(by_time[t]), []
        try:
            flows = [fetch(t, lead) for lead in STEERING_LEADS_H]
        except Exception as exc:  # noqa: BLE001 -- one bad cycle mustn't stop the shard
            return 0, 0, [(f"{task.storm_id} {t:%Y%m%d%H}", repr(exc)) for task in todo]
        written, failed = 0, []
        for task in todo:
            try:
                feats = steering_features(flows, task.lat, task.lon)
                save_steering(steering_path(cache_dir, task.storm_id, t), feats, task)
                written += 1
            except Exception as exc:  # noqa: BLE001
                failed.append((f"{task.storm_id} {t:%Y%m%d%H}", repr(exc)))
        return written, len(by_time[t]) - len(todo), failed

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(one_time, t) for t in times]
        for i, fut in enumerate(as_completed(futures), start=1):
            written, skipped, failed = fut.result()
            report.n_written += written
            report.n_skipped += skipped
            report.n_failed += len(failed)
            report.failures.extend(failed)
            if progress_every and i % progress_every == 0:
                print(f"  {i}/{len(times)} times: {report.n_written} written, "
                      f"{report.n_skipped} skipped, {report.n_failed} failed", flush=True)
    report.elapsed_s = time.monotonic() - started
    return report
