"""Real GriddedFields from public cloud archives: ERA5 (Zarr) and GDAS/GFS (GRIB2).

Scope v2.1 PLAN.md §4 "productionise" table -- Gridded fields row. Two
different real sources, two different formats, because that is what is
actually publicly available for each, not a design preference:

* **ERA5** has a fully pre-converted, analysis-ready Zarr store (Google's
  ARCO-ERA5), anonymous access, no account, no rate limit. Reading it needs
  no GRIB parsing at all -- the most performant path available for this
  source, and the one used here.
* **GDAS/GFS** has no equivalent public pressure-level Zarr. Verified before
  writing this: the dynamical.org Icechunk stores that *do* exist for GFS
  analysis/forecast are surface/near-surface only (2 m/10 m/80 m fields, no
  200/500/700/850 mb levels). The only public source with the pressure
  levels this module needs is NOAA's raw operational GRIB2 archive on AWS
  Open Data. Its ``.idx`` sidecar makes per-message byte-range HTTP fetches
  cheap, so this reads only the ~7 messages needed (a few MB) rather than
  the full ~450 MB file -- the most performant path available for *this*
  source, even though it is a different format from ERA5's.

Optional extra: ``uv sync --extra gridded``. All pure-Python wheels
(``eccodes``/``eccodeslib`` ship prebuilt binaries for common platforms) --
no system ``eccodes`` install (e.g. ``brew install eccodes``) required,
unlike a typical ``cfgrib`` setup.

**Neither source carries SST or OHC at these levels.** ERA5's store does
have ``sea_surface_temperature``, used here. GDAS's atmospheric ``pgrb2``
file does not carry SST at all (it is a separate NOAA product, e.g.
RTG_SST). Neither source has ocean heat content (that needs an ocean
reanalysis, e.g. GODAS/ORAS5). Where a value is a placeholder rather than a
real read, it is a named constant with a docstring saying so -- see
:func:`era5_to_gridded_fields` / :func:`gdas_to_gridded_fields`.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from typing import Any

import numpy as np

from ..time_utils import require_synoptic
from .features import GriddedFields
from .sources import Flavor

_GRIDDED_HINT = (
    "real GriddedFields need the 'gridded' extra: uv sync --extra gridded "
    "(or pip install anemoi[gridded])"
)


def require_era5_deps() -> None:
    """Import-check ERA5's dependency stack (xarray/zarr/gcsfs), or raise a
    clear message. Deliberately does not import ``eccodes``: ERA5 is a Zarr
    read and never touches GRIB parsing, so a broken/missing eccodes native
    library (a real, observed failure mode -- see ``gribapi.bindings``'s
    "Cannot find the ecCodes library" ``RuntimeError``, which isn't even a
    ``ModuleNotFoundError`` this can catch) must not block ERA5 access."""
    try:
        import xarray  # noqa: F401, PLC0415
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(_GRIDDED_HINT) from exc


def require_gdas_deps() -> None:
    """Import-check GDAS's dependency stack (eccodes/requests), or raise a
    clear message."""
    try:
        import eccodes  # noqa: F401, PLC0415
        import requests  # noqa: F401, PLC0415
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(_GRIDDED_HINT) from exc


def require_gridded_deps() -> None:
    """Import-check the full optional gridded-data stack (both sources)."""
    require_era5_deps()
    require_gdas_deps()


def gridded_deps_available() -> bool:
    try:
        require_gridded_deps()
        return True
    except ModuleNotFoundError:
        return False


def era5_deps_available() -> bool:
    try:
        require_era5_deps()
        return True
    except ModuleNotFoundError:
        return False


# --------------------------------------------------------------------------- #
# Shared: storm-relative box cropping on a global 0.25 deg grid
# --------------------------------------------------------------------------- #

#: Both sources below happen to share this grid: 0.25 deg, 90N->-90N,
#: 0->359.75E, row-major (north row first, longitude increasing eastward).
GRID_RESOLUTION_DEG = 0.25
GRID_NLAT = 721
GRID_NLON = 1440

#: Neither real source has OHC; neither GDAS's atmospheric product has SST.
#: Fixed placeholders, not measurements -- features derived from them
#: (potential_intensity's ohc_bonus, apply_cold_wake's ohc depression, or
#: GDAS's sst_c feature itself) will be systematically wrong until a real
#: ocean data source is wired in. Named and documented rather than silently
#: approximated with something that looks more precise than it is.
OHC_PLACEHOLDER_KJ_CM2 = 60.0
GDAS_SST_PLACEHOLDER_C = 28.0


def _crop_box(
    values: np.ndarray, center_lat: float, center_lon: float, box_deg: float
) -> np.ndarray:
    """Crop a (721, 1440) global 0.25 deg field to a storm-relative box,
    wrapping longitude at the 0/360 seam. Latitude is clamped, not wrapped --
    storms do not form near the poles, so this is a defensive edge only."""
    if values.shape != (GRID_NLAT, GRID_NLON):
        raise ValueError(f"expected a ({GRID_NLAT}, {GRID_NLON}) global grid, got {values.shape}")

    half = max(int(round(box_deg / 2.0 / GRID_RESOLUTION_DEG)), 1)
    center_lat_idx = int(round((90.0 - center_lat) / GRID_RESOLUTION_DEG))
    center_lon_idx = int(round((center_lon % 360.0) / GRID_RESOLUTION_DEG))

    lat_lo = int(np.clip(center_lat_idx - half, 0, GRID_NLAT - 1))
    lat_hi = int(np.clip(center_lat_idx + half + 1, 0, GRID_NLAT))
    lon_idx = np.arange(center_lon_idx - half, center_lon_idx + half + 1) % GRID_NLON

    return values[lat_lo:lat_hi, :][:, lon_idx]


def _saturation_vapor_pressure_hpa_array(temp_c: np.ndarray) -> np.ndarray:
    """Bolton (1980) saturation vapor pressure, vectorized. Same formula as
    ``features._saturation_vapor_pressure_hpa``, duplicated here because that
    one is deliberately scalar (used inside a scalar PI calculation)."""
    return 6.112 * np.exp(17.67 * temp_c / (temp_c + 243.5))


def _specific_humidity_to_rh_pct(
    specific_humidity_kg_kg: np.ndarray, temp_c: np.ndarray, pressure_hpa: float
) -> np.ndarray:
    """Invert specific humidity to relative humidity at a known pressure
    level -- for a pressure-LEVEL variable the ambient pressure is just the
    level itself (700 hPa here), not a surface pressure field."""
    q = specific_humidity_kg_kg
    e = q * pressure_hpa / (0.622 + 0.378 * q)
    es = _saturation_vapor_pressure_hpa_array(temp_c)
    return np.clip(e / es * 100.0, 0.0, 100.0)


# --------------------------------------------------------------------------- #
# ERA5 (ARCO-ERA5 Zarr, anonymous GCS access)
# --------------------------------------------------------------------------- #

ERA5_ZARR_PATH = "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"

#: Standard gravitational acceleration -- ERA5's raw "geopotential" is in
#: m^2 s^-2; dividing by this gives geopotential height in meters, which is
#: what GriddedFields.z500 and the rest of this codebase expect.
STANDARD_GRAVITY_M_S2 = 9.80665


def open_era5_store() -> Any:
    """Open the ARCO-ERA5 Zarr store itself, with no time selection.

    Network call against a public, anonymous-access Google Cloud Storage
    bucket -- no account, no API key, no rate limit. Opening the store costs
    ~1-2s (metadata read); reuse the returned handle across many
    :func:`open_era5` calls (e.g. via its ``store`` argument) rather than
    reopening it per sample -- see ``data.era5_cache``, which fetches
    thousands of samples and shares one store handle across worker threads.
    """
    require_era5_deps()
    import xarray as xr  # noqa: PLC0415

    return xr.open_zarr(ERA5_ZARR_PATH, chunks=None, storage_options={"token": "anon"})


def open_era5(valid_time: datetime, store: Any = None) -> Any:
    """Select one synoptic time from the ARCO-ERA5 store.

    ``store`` may be a Dataset from :func:`open_era5_store`, to avoid
    reopening the store on every call; if omitted, opens a fresh one (this
    is the original, backward-compatible single-sample behaviour). Returns
    an ``xarray.Dataset`` (import deferred; requires the ``gridded`` extra).
    """
    ds = store if store is not None else open_era5_store()
    return ds.sel(time=np.datetime64(valid_time.replace(tzinfo=None)))


def era5_to_gridded_fields(
    ds: Any,
    center_lat: float,
    center_lon: float,
    flavor: Flavor = Flavor.ERA5_PRETRAIN,
    *,
    box_deg: float = 10.0,
) -> GriddedFields:
    """Map one ERA5 time slice (from :func:`open_era5`, or any Dataset with
    the same variable/coordinate names -- see the test suite for a synthetic
    example) into a storm-relative :class:`GriddedFields`.

    Real fields: ``u200``/``v200``/``u850``/``v850`` (``u_component_of_wind``/
    ``v_component_of_wind`` at ``level=200``/``850``), ``z500``
    (``geopotential`` / g at ``level=500``), ``t700`` (``temperature`` at
    ``level=700``), ``mslp`` (``mean_sea_level_pressure``, Pa -> hPa), ``sst``
    (``sea_surface_temperature``, K -> degC).

    Derived, not directly stored: ``rh700``, from ``specific_humidity`` at
    ``level=700`` via :func:`_specific_humidity_to_rh_pct`.

    Not available from ERA5 at all: ``ohc`` -- see
    :data:`OHC_PLACEHOLDER_KJ_CM2`.
    """

    def crop(var: str, **sel) -> np.ndarray:
        arr = np.asarray(ds[var].sel(**sel).values, dtype=float)
        return _crop_box(arr, center_lat, center_lon, box_deg)

    u200 = crop("u_component_of_wind", level=200)
    v200 = crop("v_component_of_wind", level=200)
    u850 = crop("u_component_of_wind", level=850)
    v850 = crop("v_component_of_wind", level=850)
    z500 = crop("geopotential", level=500) / STANDARD_GRAVITY_M_S2
    t700_k = crop("temperature", level=700)
    q700 = crop("specific_humidity", level=700)
    mslp = crop("mean_sea_level_pressure") / 100.0
    sst_k = crop("sea_surface_temperature")

    t700_c = t700_k - 273.15
    rh700 = _specific_humidity_to_rh_pct(q700, t700_c, pressure_hpa=700.0)

    valid_time = datetime.fromisoformat(str(np.asarray(ds["time"].values))[:19])
    return GriddedFields(
        valid_time=valid_time,
        flavor=flavor,
        u200=u200, v200=v200, u850=u850, v850=v850, z500=z500,
        rh700=rh700, t700=t700_k, mslp=mslp, sst=sst_k - 273.15,
        ohc=np.full(u200.shape, OHC_PLACEHOLDER_KJ_CM2),
    )


# --------------------------------------------------------------------------- #
# GDAS/GFS analysis (raw GRIB2, byte-range fetch from AWS Open Data)
# --------------------------------------------------------------------------- #

GDAS_BUCKET_URL = "https://noaa-gfs-bdp-pds.s3.amazonaws.com"

#: (shortName, level in mb) for the pressure-level messages this module
#: reads. Verified against a real gfs.tHHz.pgrb2.0p25.anl.idx sidecar.
GDAS_LEVEL_MESSAGES: tuple[tuple[str, int], ...] = (
    ("UGRD", 200), ("VGRD", 200),
    ("UGRD", 850), ("VGRD", 850),
    ("HGT", 500),
    ("TMP", 700), ("RH", 700),
)
#: PRMSL (mean sea level pressure) has no numeric "level" in the .idx format.
GDAS_MSLP_KEY: tuple[str, str] = ("PRMSL", "mean sea level")


def _gdas_analysis_url(valid_time: datetime) -> str:
    require_synoptic(valid_time)
    return (
        f"{GDAS_BUCKET_URL}/gfs.{valid_time:%Y%m%d}/{valid_time:%H}/atmos/"
        f"gfs.t{valid_time:%H}z.pgrb2.0p25.anl"
    )


def _parse_grib2_index(idx_text: str) -> dict[tuple[str, str], tuple[int, int | None]]:
    """Parse a NOMADS/AWS ``.idx`` sidecar (``msgnum:offset:date:param:level:``)
    into ``{(shortName, level_label): (start_byte, end_byte)}``.
    ``end_byte`` is ``None`` for the file's last message (fetch to EOF)."""
    entries: list[tuple[str, str, int]] = []
    for line in idx_text.strip().splitlines():
        parts = line.split(":")
        if len(parts) < 5:
            continue
        entries.append((parts[3], parts[4], int(parts[1])))

    ranges: dict[tuple[str, str], tuple[int, int | None]] = {}
    for i, (short_name, level, offset) in enumerate(entries):
        end = entries[i + 1][2] if i + 1 < len(entries) else None
        ranges[(short_name, level)] = (offset, end)
    return ranges


def fetch_gdas_grib2_fields(
    valid_time: datetime, *, timeout: float = 60.0
) -> dict[tuple[str, int | str], np.ndarray]:
    """Byte-range fetch the pressure-level messages this module needs from
    NOAA's public GDAS/GFS analysis GRIB2 file on AWS Open Data.

    Fetches only the target messages (a few MB total across ~7 requests),
    not the full ~450 MB file -- the ``.idx`` sidecar gives each message's
    exact byte range, and ``eccodes`` parses one small temp file per message.
    Returns ``{("UGRD", 200): (721, 1440) array, ..., ("PRMSL", "mean sea
    level"): array}``, the same keys :func:`gdas_to_gridded_fields` expects.
    """
    require_gdas_deps()
    import eccodes  # noqa: PLC0415
    import requests  # noqa: PLC0415

    url = _gdas_analysis_url(valid_time)
    idx_resp = requests.get(f"{url}.idx", timeout=timeout)
    idx_resp.raise_for_status()
    byte_ranges = _parse_grib2_index(idx_resp.text)

    targets = [(sn, f"{lvl} mb", (sn, lvl)) for sn, lvl in GDAS_LEVEL_MESSAGES]
    targets.append((*GDAS_MSLP_KEY, GDAS_MSLP_KEY))

    fields: dict[tuple[str, int | str], np.ndarray] = {}
    for short_name, level_label, out_key in targets:
        start, end = byte_ranges.get((short_name, level_label), (None, None))
        if start is None:
            raise KeyError(f"{short_name}:{level_label} not found in {url}.idx")
        range_header = f"bytes={start}-{end - 1}" if end is not None else f"bytes={start}-"
        resp = requests.get(url, headers={"Range": range_header}, timeout=timeout)
        resp.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".grib2") as tmp:
            tmp.write(resp.content)
            tmp.flush()
            with open(tmp.name, "rb") as fh:
                gid = eccodes.codes_grib_new_from_file(fh)
                try:
                    ni = eccodes.codes_get(gid, "Ni")
                    nj = eccodes.codes_get(gid, "Nj")
                    fields[out_key] = eccodes.codes_get_values(gid).reshape(nj, ni)
                finally:
                    eccodes.codes_release(gid)
    return fields


def gdas_to_gridded_fields(
    fields: dict[tuple[str, int | str], np.ndarray],
    center_lat: float,
    center_lon: float,
    valid_time: datetime,
    flavor: Flavor = Flavor.GDAS_FINETUNE,
    *,
    box_deg: float = 10.0,
) -> GriddedFields:
    """Map fetched GDAS/GFS GRIB2 messages (from :func:`fetch_gdas_grib2_fields`,
    or a matching dict built in a test) into a storm-relative :class:`GriddedFields`.

    Real fields: ``u200``/``v200``/``u850``/``v850`` (UGRD/VGRD at 200/850 mb),
    ``z500`` (HGT at 500 mb -- already geopotential HEIGHT in meters, no
    g-conversion needed, unlike ERA5's raw geopotential), ``t700`` (TMP at
    700 mb, K), ``rh700`` (RH at 700 mb, reported directly -- no
    specific-humidity conversion needed here, unlike the ERA5 path), ``mslp``
    (PRMSL, Pa -> hPa).

    Not available in GDAS/GFS's atmospheric ``pgrb2`` file at all: ``sst``,
    ``ohc`` -- see :data:`GDAS_SST_PLACEHOLDER_C` / :data:`OHC_PLACEHOLDER_KJ_CM2`.
    """

    def crop(key: tuple[str, int | str]) -> np.ndarray:
        return _crop_box(fields[key], center_lat, center_lon, box_deg)

    u200 = crop(("UGRD", 200))
    v200 = crop(("VGRD", 200))
    u850 = crop(("UGRD", 850))
    v850 = crop(("VGRD", 850))
    z500 = crop(("HGT", 500))
    t700 = crop(("TMP", 700))
    rh700 = crop(("RH", 700))
    mslp = crop(GDAS_MSLP_KEY) / 100.0

    return GriddedFields(
        valid_time=valid_time,
        flavor=flavor,
        u200=u200, v200=v200, u850=u850, v850=v850, z500=z500,
        rh700=rh700, t700=t700, mslp=mslp,
        sst=np.full(u200.shape, GDAS_SST_PLACEHOLDER_C),
        ohc=np.full(u200.shape, OHC_PLACEHOLDER_KJ_CM2),
    )
