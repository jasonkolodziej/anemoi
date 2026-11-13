"""Real NOAA OSPO CoastWatch ocean heat content (the ``sst_ohc`` source's
OHC half; ``data.real_sst`` is the SST half).

Fetch and decode only. Nothing in training or serving reads this module:
``GriddedFields.ohc`` is still ``real_gridded.OHC_PLACEHOLDER_KJ_CM2``
(docs/skill_gap_plan.md Phase 2b wires it, as its own PR and retrain).

What the files are (verified against real files, 2026-11-13):

* **Two chains, one product.** ``{na,np}/YYYY/ohc_{na,np}QG3_YYYY_DDD.nc``
  runs from 2020 day 121 to 2024 day 18; ``{na,np}14/YYYY/ohc_{na,np}14QG3_
  YYYY_DDD.nc`` from 2024 day 15. ``DDD`` is the day of year. On a clean
  day the two agree to RMS 0.0016 kJ/cm2 (NA) and 0.0024 (NP), so this reads
  the old chain up to 2024 day 14 and the new one from day 15.
* **Two formats.** The old chain and na14/np14 up to 2025 day 084 are
  NetCDF-3 classic (xarray reads them through scipy); v1r1, from 2025 day
  085, is HDF5 (h5netcdf). The format is read from the first bytes, not
  from the date.
* **v1r1 is named a day early.** From 2025 day 085 a file is named for the
  day before it was made and holds data through its creation day.
  :func:`creation_day` puts every file on one clock; ``time_coverage_end``
  and ``metadata_link`` don't follow one rule and aren't read.
* **Grids.** NA is 241x401 (0..60N, 100W..0), NP 241x721 (0..60N,
  100E..280E), both 0.25 deg with latitude ascending. Every node is a node
  of ``real_gridded``'s 721x1440 lattice, so :func:`place` flips latitude
  and wraps longitude; nothing is interpolated. The basins overlap in 81
  columns, and in the 80.0W column NP holds 0.0 where NA has real values,
  so NP is written first and NA over it where NA is valid.
* **Values.** ``ohc`` in ``kJ cm^-2``, fill -999 (static land/ice mask).
  0.0 is a real value: water below 26 C.
* **Bad files.** na14 2025 day 199 is blank: every variable is 0.0, the
  coordinates included. :func:`decode_ohc` rejects a file whose coordinates
  aren't the expected arrays or that has no fill cell at all.
* **Degraded days.** Altimetry outages raise the objective-analysis error
  ``sshaE``: 2022 days 201-204 and 208-216 (median up to 0.65 against a
  normal ~0.29) in both basins, and 2024 days 010-022 on the old chain.
  :attr:`OhcFile.degraded` flags a file whose median ``sshaE`` is above
  :data:`DEGRADED_SSHAE_MEDIAN`. A degraded file is still returned, flagged.

**Date rule** (:func:`select_file`). Files post a median 35.5 h and at most
~48 h after 00Z of their name day, so a cycle at ``t`` reads the newest
file whose creation day is on or before ``date(t) - OHC_VALID_LAG``
(``data.availability``). That is leakage-safe for every posting seen and,
because it counts creation days, gives the 2021-2023 (old chain), 2024
(v1r0) and 2025+ (v1r1) splits inputs of the same age. A file that isn't
published (404) or is rejected is stepped over, one creation day at a time
and at most :data:`MAX_STEP_BACK_DAYS` times, and the age actually used is
reported.

**Regression.** SHIPS' developmental SOHC is this product sampled from the
file named for the day before the case: at open-ocean Atlantic cases of
2021-2022 it equals :func:`ohc_at` on that file within 0.5 kJ/cm2
(``tests/test_real_ohc.py``, network-marked).
"""

from __future__ import annotations

import http.client
import io
import math
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError

import numpy as np

from ..time_utils import require_synoptic
from .availability import OHC_VALID_LAG
from .real_gridded import GRID_NLAT, GRID_NLON, GRID_RESOLUTION_DEG

BASE_URL = "https://coastwatch.noaa.gov/data/pub0012/coastwatch/ocean_heat"

#: The order :func:`place` writes the basins in: NA last, so it wins where
#: both are valid (NP's 80.0W column holds 0.0 where NA has data).
BASINS = ("np", "na")

#: First name day of the old ``na``/``np`` chain (2020 day 121).
ARCHIVE_START = date(2020, 4, 30)
#: First name day read from ``na14``/``np14`` (2024 day 15). The old chain
#: runs on to day 18; the two agree to RMS 0.002 kJ/cm2.
NEW_CHAIN_START = date(2024, 1, 15)
#: First v1r1 name day (2025 day 085). From here a file is made the day
#: after the day it is named for, and the format is HDF5.
V1R1_START = date(2025, 3, 26)

#: How many creation days :func:`select_file` steps back past a missing or
#: rejected file. Every missing file a 2021-2025 fix needs has the day
#: before; np14 2024 days 321-340 are a longer gap, which this reports.
MAX_STEP_BACK_DAYS = 3

#: A file whose median ``sshaE`` exceeds this is flagged degraded. Normal
#: seasons sit at 0.287-0.289; 0.35 misses part of the January 2024 outage
#: (0.332-0.343), 0.32 catches it and the July-August 2022 one.
DEGRADED_SSHAE_MEDIAN = 0.32

UNITS = "kJ cm^-2"
FILL_VALUE = -999.0

#: Per-basin grid: first latitude, first longitude (in the file's own
#: convention), and the number of 0.25-degree steps in each.
_GRIDS: dict[str, tuple[float, float, int, int]] = {
    "na": (0.0, -100.0, 241, 401),
    "np": (0.0, 100.0, 241, 721),
}

#: The largest real file is ~6 MB (np14 v1r0); this only bounds a bad reply.
MAX_DOWNLOAD_BYTES = 64 * 2**20

_TIMEOUT_S = 60.0

#: The User-Agent ``data.real_sst`` and ``data.real_ndbc`` send.
DEFAULT_USER_AGENT = "anemoi-api/1.0"

_OHC_HINT = "real OHC fetch needs the 'gridded' extra: uv sync --extra gridded"

_NETCDF3_MAGIC = (b"CDF\x01", b"CDF\x02")
_HDF5_MAGIC = b"\x89HDF"


class OhcFetchError(RuntimeError):
    """A real fetch or decode failure talking to CoastWatch's OHC archive."""


class OhcNotPublished(OhcFetchError):
    """CoastWatch has no file at that URL (HTTP 404)."""


class OhcRejected(OhcFetchError):
    """The file arrived but is not a usable OHC file (wrong grid, units or
    format, blank, or made later than its name says)."""


class OhcUnavailable(OhcFetchError):
    """No basin had a usable file within the step-back window."""


def require_ohc_deps() -> None:
    try:
        import h5netcdf  # noqa: F401, PLC0415
        import scipy  # noqa: F401, PLC0415
        import xarray  # noqa: F401, PLC0415
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(_OHC_HINT) from exc


# --------------------------------------------------------------------------- #
# Names and dates
# --------------------------------------------------------------------------- #


def _check_basin(basin: str) -> None:
    if basin not in _GRIDS:
        raise ValueError(f"basin must be one of {sorted(_GRIDS)}, got {basin!r}")


def expected_coordinates(basin: str) -> tuple[np.ndarray, np.ndarray]:
    """The latitude and longitude arrays a real ``basin`` file carries."""
    _check_basin(basin)
    lat0, lon0, nlat, nlon = _GRIDS[basin]
    lat = lat0 + GRID_RESOLUTION_DEG * np.arange(nlat, dtype=np.float64)
    lon = lon0 + GRID_RESOLUTION_DEG * np.arange(nlon, dtype=np.float64)
    return lat, lon


def ohc_url(basin: str, name_day: date) -> str:
    """CoastWatch URL of the ``basin`` file named for ``name_day``: the old
    chain up to 2024 day 14, ``na14``/``np14`` from day 15."""
    _check_basin(basin)
    if name_day < ARCHIVE_START:
        raise ValueError(f"no CoastWatch OHC file is named before {ARCHIVE_START}: {name_day}")
    folder = f"{basin}14" if name_day >= NEW_CHAIN_START else basin
    doy = name_day.timetuple().tm_yday
    year = name_day.year
    return f"{BASE_URL}/{folder}/{year}/ohc_{folder}QG3_{year}_{doy:03d}.nc"


def creation_day(name_day: date) -> date:
    """The day the file named ``name_day`` was made: the name day, except
    v1r1 files (from :data:`V1R1_START`), which are made the day after."""
    return name_day + timedelta(days=1) if name_day >= V1R1_START else name_day


def name_day_for_creation(made: date) -> date | None:
    """The name day of the file made on ``made``, or ``None`` when no file
    is: v1r0's last file (2025 day 084) is made on its name day, 2025-03-25,
    and v1r1's first (day 085) on 2025-03-27."""
    named = made - timedelta(days=1)
    if named >= V1R1_START:
        return named
    if made >= V1R1_START:
        return None
    return made


def cycle_date(t: datetime) -> date:
    """Calendar date of the cycle at ``t``. ``t`` must be a synoptic UTC
    time, as at every cycle-time entry point (``ValueError`` otherwise): a
    naive local time east of Greenwich would read a file a day too new."""
    require_synoptic(t)
    return t.date()


def target_creation_day(t: datetime) -> date:
    """The newest creation day a cycle at ``t`` may read: ``date(t) - 2``."""
    return cycle_date(t) - timedelta(days=OHC_VALID_LAG.days)


# --------------------------------------------------------------------------- #
# Fetch
# --------------------------------------------------------------------------- #


def _declared_length(headers: Any) -> int | None:
    """The body length a reply's headers promise, or ``None`` when they
    don't (no or a malformed Content-Length, or chunked encoding, which
    overrides it)."""
    if "chunked" in (headers.get("Transfer-Encoding") or "").lower():
        return None
    try:
        length = int(headers.get("Content-Length") or "")
    except ValueError:
        return None
    return length if length >= 0 else None


def http_get(
    url: str, *, user_agent: str | None = DEFAULT_USER_AGENT, timeout: float = _TIMEOUT_S,
) -> bytes:
    """GET ``url``'s bytes. Raises :class:`OhcNotPublished` for a 404 and
    :class:`OhcFetchError` for any other failure, a cut-off reply included:
    CPython's bounded ``read`` returns a body shorter than its
    Content-Length without raising, and a short one would otherwise decode
    as a rejected file and send :func:`select_file` to older data.
    ``user_agent=None`` sends urllib's own default instead."""
    headers = {"User-Agent": user_agent} if user_agent else {}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            declared = _declared_length(resp.headers)
            if declared is not None and declared > MAX_DOWNLOAD_BYTES:
                raise OhcFetchError(f"{url}: {declared} bytes, more than {MAX_DOWNLOAD_BYTES}")
            body = resp.read(MAX_DOWNLOAD_BYTES + 1)
    except HTTPError as exc:
        if exc.code == 404:
            raise OhcNotPublished(url) from exc
        raise OhcFetchError(f"GET {url} failed: HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
        # HTTPException: IncompleteRead (a cut-off chunked body), BadStatusLine.
        raise OhcFetchError(f"GET {url} failed: {exc!r}") from exc
    if len(body) > MAX_DOWNLOAD_BYTES:
        raise OhcFetchError(f"{url}: more than {MAX_DOWNLOAD_BYTES} bytes")
    if declared is not None and len(body) != declared:
        raise OhcFetchError(f"GET {url} failed: cut off at {len(body)} of {declared} bytes")
    return body


#: A URL to its bytes, raising :class:`OhcNotPublished` when there is no file.
Fetch = Callable[[str], bytes]


# --------------------------------------------------------------------------- #
# Decode
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True, eq=False)
class OhcFile:
    """One decoded, validated basin file on its own grid (latitude
    ascending, longitude in the file's convention)."""

    basin: str
    name_day: date
    url: str
    file_format: str  # "netcdf3" | "hdf5"
    lat: np.ndarray
    lon: np.ndarray
    #: ``(len(lat), len(lon))`` float32 kJ/cm2, NaN where the file has fill.
    ohc: np.ndarray
    #: Median of ``sshaE`` over its valid cells; ``None`` if the file has none.
    sshae_median: float | None
    #: The file's ``date_created`` attribute, if it has one (the old chain
    #: doesn't). Informational: the date rule uses :func:`creation_day`.
    date_created: str | None = None

    @property
    def creation_day(self) -> date:
        return creation_day(self.name_day)

    @property
    def degraded(self) -> bool:
        return self.sshae_median is not None and self.sshae_median > DEGRADED_SSHAE_MEDIAN

    @property
    def valid_cells(self) -> int:
        return int(np.isfinite(self.ohc).sum())

    def metadata(self) -> dict[str, Any]:
        return {
            "basin": self.basin,
            "url": self.url,
            "name_day": self.name_day.isoformat(),
            "creation_day": self.creation_day.isoformat(),
            "format": self.file_format,
            "date_created": self.date_created,
            "sshae_median": self.sshae_median,
            "degraded": self.degraded,
            "valid_cells": self.valid_cells,
        }


def detect_format(body: bytes) -> str:
    """``"netcdf3"`` or ``"hdf5"`` from the first bytes; anything else (an
    HTML error page, a truncated reply) is rejected."""
    if body[:4] in _NETCDF3_MAGIC:
        return "netcdf3"
    if body[:4] == _HDF5_MAGIC:
        return "hdf5"
    raise OhcRejected(f"neither NetCDF-3 nor HDF5: starts {body[:8]!r}")


def _grid_values(ds: Any, name: str, shape: tuple[int, int]) -> np.ndarray:
    """A ``(time=1, latitude, longitude)`` variable as a 2-D array."""
    var = ds[name]
    if tuple(var.dims[-2:]) != ("latitude", "longitude") or var.size != shape[0] * shape[1]:
        raise OhcRejected(f"{name} has dims {var.dims} and size {var.size}, not one {shape} grid")
    return np.asarray(var.values).reshape(shape)


def _created_date(value: object) -> date | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _read_checked(
    ds: Any, basin: str, url: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float | None, str | None]:
    """Read and check an open dataset: ``(lat, lon, raw ohc, fill mask,
    sshaE median, date_created)``. Raises :class:`OhcRejected`."""
    missing = [v for v in ("ohc", "latitude", "longitude") if v not in ds.variables]
    if missing:
        raise OhcRejected(f"{url}: no {', '.join(missing)} variable")
    lat = np.asarray(ds["latitude"].values, dtype=np.float64).ravel()
    lon = np.asarray(ds["longitude"].values, dtype=np.float64).ravel()
    want_lat, want_lon = expected_coordinates(basin)
    if not (
        lat.shape == want_lat.shape
        and lon.shape == want_lon.shape
        and np.allclose(lat, want_lat, rtol=0.0, atol=1e-4)
        and np.allclose(lon, want_lon, rtol=0.0, atol=1e-4)
    ):
        raise OhcRejected(
            f"{url}: latitude/longitude are not the {basin.upper()} grid "
            f"(got {lat.size}x{lon.size}, {lat[:1]}..{lat[-1:]}, {lon[:1]}..{lon[-1:]})"
        )
    units = ds["ohc"].attrs.get("units")
    if units != UNITS:
        raise OhcRejected(f"{url}: ohc units are {units!r}, not {UNITS!r}")
    fill = np.float32(ds["ohc"].attrs.get("_FillValue", FILL_VALUE))
    raw = _grid_values(ds, "ohc", (lat.size, lon.size)).astype(np.float32)
    is_fill = (raw == fill) | ~np.isfinite(raw)
    if not is_fill.any():
        raise OhcRejected(f"{url}: no fill cell, so not a real file (blank?)")

    sshae_median = None
    if "sshaE" in ds.variables:
        sshae = _grid_values(ds, "sshaE", (lat.size, lon.size)).astype(np.float32)
        sshae_fill = np.float32(ds["sshaE"].attrs.get("_FillValue", FILL_VALUE))
        ok = np.isfinite(sshae) & (sshae != sshae_fill)
        if ok.any():
            sshae_median = float(np.median(sshae[ok].astype(np.float64)))

    created = ds.attrs.get("date_created")
    return lat, lon, raw, is_fill, sshae_median, None if created is None else str(created)


def decode_ohc(body: bytes, basin: str, name_day: date, *, url: str = "") -> OhcFile:
    """Decode and validate one CoastWatch file. Raises :class:`OhcRejected`
    for a file that isn't NetCDF-3/HDF5, whose latitude/longitude aren't
    ``basin``'s, whose ``ohc`` units aren't ``kJ cm^-2``, that has no fill
    cell (a blank file), or whose ``date_created`` is later than
    :func:`creation_day` says (its data would be fresher than the date
    rule assumes)."""
    require_ohc_deps()
    import xarray as xr  # noqa: PLC0415

    _check_basin(basin)
    url = url or ohc_url(basin, name_day)
    file_format = detect_format(body)
    engine = "scipy" if file_format == "netcdf3" else "h5netcdf"
    try:
        ds = xr.open_dataset(
            io.BytesIO(body), engine=engine, decode_times=False, mask_and_scale=False,
        )
        with ds:
            read = _read_checked(ds, basin, url)
    except OhcRejected:
        raise
    except Exception as exc:  # noqa: BLE001 - a truncated or malformed file is a rejection
        raise OhcRejected(f"{url}: can't be read as {file_format}: {exc}") from exc
    lat, lon, raw, is_fill, sshae_median, date_created = read

    made = _created_date(date_created)
    if made is not None and made > creation_day(name_day):
        raise OhcRejected(
            f"{url}: date_created {date_created} is after its creation day "
            f"{creation_day(name_day)}"
        )

    ohc = np.where(is_fill, np.float32(np.nan), raw).astype(np.float32)
    return OhcFile(
        basin=basin,
        name_day=name_day,
        url=url,
        file_format=file_format,
        lat=lat,
        lon=lon,
        ohc=ohc,
        sshae_median=sshae_median,
        date_created=date_created,
    )


def fetch_ohc_file(basin: str, name_day: date, *, fetch: Fetch | None = None) -> OhcFile:
    """Fetch and decode the ``basin`` file named for ``name_day``.
    ``fetch`` (a URL to its bytes, raising :class:`OhcNotPublished` for a
    404) defaults to :func:`http_get`."""
    url = ohc_url(basin, name_day)
    body = (fetch or http_get)(url)
    return decode_ohc(body, basin, name_day, url=url)


# --------------------------------------------------------------------------- #
# Date rule
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class StepBack:
    """A creation day :func:`select_file` passed over, and why."""

    creation_day: date
    name_day: date | None
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "creation_day": self.creation_day.isoformat(),
            "name_day": self.name_day.isoformat() if self.name_day else None,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True, eq=False)
class BasinChoice:
    """What :func:`select_file` read for one basin: the file (``None`` if
    nothing usable was found), its age and the days stepped over."""

    basin: str
    cycle_day: date
    file: OhcFile | None
    step_backs: tuple[StepBack, ...] = ()

    @property
    def age_days(self) -> int | None:
        """``date(t)`` minus the file's creation day: 2 unless stepped back."""
        return None if self.file is None else (self.cycle_day - self.file.creation_day).days

    def metadata(self) -> dict[str, Any]:
        out: dict[str, Any] = {"basin": self.basin, "available": self.file is not None}
        if self.file is not None:
            out.update(self.file.metadata())
        out["age_days"] = self.age_days
        out["step_backs"] = [s.as_dict() for s in self.step_backs]
        return out


def select_file(
    basin: str,
    t: datetime,
    *,
    fetch: Fetch | None = None,
    max_step_back_days: int = MAX_STEP_BACK_DAYS,
) -> BasinChoice:
    """The ``basin`` file a cycle at ``t`` (a synoptic UTC time) reads: the
    newest whose creation day is on or before ``date(t) - 2``. A creation
    day with no file (404, or v1r1's naming switch) or a rejected file is
    stepped over, at most ``max_step_back_days`` times. Other fetch failures
    raise: a timeout is not a reason to read older data."""
    _check_basin(basin)
    if max_step_back_days < 0:
        raise ValueError(f"max_step_back_days must be >= 0, got {max_step_back_days}")
    fetch = fetch or http_get
    first = target_creation_day(t)
    passed: list[StepBack] = []
    for back in range(max_step_back_days + 1):
        made = first - timedelta(days=back)
        name_day = name_day_for_creation(made)
        if name_day is None:
            passed.append(StepBack(made, None, "no file is made on this day (v1r1 naming switch)"))
            continue
        if name_day < ARCHIVE_START:
            passed.append(StepBack(made, name_day, f"before the archive starts ({ARCHIVE_START})"))
            continue
        try:
            ohc = fetch_ohc_file(basin, name_day, fetch=fetch)
        except OhcNotPublished:
            passed.append(StepBack(made, name_day, "not published (404)"))
            continue
        except OhcRejected as exc:
            passed.append(StepBack(made, name_day, f"rejected: {exc}"))
            continue
        return BasinChoice(basin, cycle_date(t), ohc, tuple(passed))
    return BasinChoice(basin, cycle_date(t), None, tuple(passed))


# --------------------------------------------------------------------------- #
# Global field and point values
# --------------------------------------------------------------------------- #


def _lattice_index(lat: np.ndarray, lon: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Rows and columns of ``real_gridded``'s lattice (90N first, 0E first)
    for exact 0.25-degree nodes."""
    rows = (90.0 - lat) / GRID_RESOLUTION_DEG
    cols = np.mod(lon, 360.0) / GRID_RESOLUTION_DEG
    r, c = np.rint(rows), np.rint(cols)
    on_nodes = np.allclose(rows, r, rtol=0, atol=1e-6) and np.allclose(cols, c, rtol=0, atol=1e-6)
    if not on_nodes or r.min() < 0 or r.max() > GRID_NLAT - 1:
        raise ValueError("coordinates are not nodes of the 0.25-degree lattice")
    return r.astype(np.int64), c.astype(np.int64) % GRID_NLON


def place(files: Iterable[OhcFile]) -> np.ndarray:
    """``(721, 1440)`` float32 kJ/cm2 on ``real_gridded``'s lattice, NaN
    where no file has data. NP is written first and NA over it where NA is
    finite, whatever order ``files`` come in."""
    out = np.full((GRID_NLAT, GRID_NLON), np.nan, dtype=np.float32)
    by_basin = {f.basin: f for f in files}
    for basin in BASINS:
        ohc = by_basin.get(basin)
        if ohc is None:
            continue
        rows, cols = _lattice_index(ohc.lat, ohc.lon)
        valid = np.isfinite(ohc.ohc)
        rr, cc = np.meshgrid(rows, cols, indexing="ij")
        out[rr[valid], cc[valid]] = ohc.ohc[valid]
    return out


@dataclass(frozen=True, slots=True, eq=False)
class OhcField:
    """The global OHC field a cycle at ``cycle_time`` reads, and where it
    came from."""

    cycle_time: datetime
    #: ``(721, 1440)`` float32 kJ/cm2 on ``real_gridded``'s lattice.
    values: np.ndarray
    #: One per basin, in :data:`BASINS` order (NP, then NA).
    basins: tuple[BasinChoice, ...]

    @property
    def degraded(self) -> bool:
        return any(b.file is not None and b.file.degraded for b in self.basins)

    def metadata(self) -> dict[str, Any]:
        return {
            "cycle_time": self.cycle_time.isoformat(),
            "rule": f"newest file with creation day <= date(t) - {OHC_VALID_LAG.days} days",
            "valid_cells": int(np.isfinite(self.values).sum()),
            "degraded": self.degraded,
            "basins": [b.metadata() for b in self.basins],
        }


def ohc_global(
    t: datetime,
    *,
    fetch: Fetch | None = None,
    max_step_back_days: int = MAX_STEP_BACK_DAYS,
) -> OhcField:
    """Global OHC for a cycle at ``t`` (a synoptic UTC time) under the
    date rule (:func:`select_file`, per basin). A basin with no usable file
    in the window stays NaN and is reported; raises :class:`OhcUnavailable`
    when neither basin has one."""
    choices = tuple(
        select_file(basin, t, fetch=fetch, max_step_back_days=max_step_back_days)
        for basin in BASINS
    )
    if all(c.file is None for c in choices):
        reasons = "; ".join(
            f"{c.basin}: " + ", ".join(f"{s.creation_day} {s.reason}" for s in c.step_backs)
            for c in choices
        )
        raise OhcUnavailable(f"no usable OHC file for a cycle at {t.isoformat()}: {reasons}")
    values = place(c.file for c in choices if c.file is not None)
    return OhcField(cycle_time=t, values=values, basins=choices)


def _bilinear(values: np.ndarray, fi: float, fj: float, *, wrap: bool) -> float:
    """Bilinear value at fractional index ``(fi, fj)``; NaN off the grid or
    when any of the four corners is NaN."""
    nlat, nlon = values.shape
    if not (0.0 <= fi <= nlat - 1):
        return math.nan
    i0 = min(math.floor(fi), nlat - 2)
    fy = fi - i0
    if wrap:
        j0 = math.floor(fj)
        fx = fj - j0
        j0 %= nlon
        j1 = (j0 + 1) % nlon
    else:
        if not (0.0 <= fj <= nlon - 1):
            return math.nan
        j0 = min(math.floor(fj), nlon - 2)
        fx = fj - j0
        j1 = j0 + 1
    corners = [float(values[i0, j0]), float(values[i0, j1]),
               float(values[i0 + 1, j0]), float(values[i0 + 1, j1])]
    if not all(math.isfinite(c) for c in corners):
        return math.nan
    c00, c01, c10, c11 = corners
    return (
        (1 - fy) * (1 - fx) * c00 + (1 - fy) * fx * c01 + fy * (1 - fx) * c10 + fy * fx * c11
    )


def ohc_at(lat: float, lon: float, source: OhcFile | OhcField | np.ndarray) -> float:
    """Bilinear OHC (kJ/cm2) at ``(lat, lon)`` on the 0.25-degree grid; NaN
    unless all four corners are valid. ``lon`` may be -180..180 or 0..360.
    ``source`` is one basin file on its own grid, an :class:`OhcField`, or
    a ``(721, 1440)`` lattice array.

    The corners are the nodes at and north-east of ``(floor(lat),
    floor(lon))`` on the 0.25-degree grid, on every source, so a point on a
    node line still needs the next node north (east): the convention the
    SHIPS comparison's open-ocean classification was made with. On a
    file's own north or east edge the cell steps back inside the file."""
    if isinstance(source, OhcFile):
        lon_e = lon % 360.0
        if source.lon[0] < 0.0 and lon_e > 180.0:
            lon_e -= 360.0
        fi = (lat - source.lat[0]) / GRID_RESOLUTION_DEG
        fj = (lon_e - source.lon[0]) / GRID_RESOLUTION_DEG
        return _bilinear(source.ohc, fi, fj, wrap=False)
    values = source.values if isinstance(source, OhcField) else source
    if values.shape != (GRID_NLAT, GRID_NLON):
        raise ValueError(f"expected a ({GRID_NLAT}, {GRID_NLON}) field, got {values.shape}")
    # The lattice runs 90N first; read it south-first like the files.
    fi = (lat + 90.0) / GRID_RESOLUTION_DEG
    fj = (lon % 360.0) / GRID_RESOLUTION_DEG
    return _bilinear(values[::-1], fi, fj, wrap=True)
