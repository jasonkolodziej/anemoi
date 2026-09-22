"""Real GOES-18/19 ABI imagery + derived products -> storm-relative
``SatelliteCrop`` (the ``goes`` source, #146).

``data.satellite`` defines the target shape (``CHANNEL_NAMES``,
``SatelliteCrop``) and is synthetic-only; this module fills it with real
data. Five real NOAA products map onto the five channels, each verified
live (real file, real variable name, real units) before writing any
fetch code -- no guessed field semantics, unlike RSS's TC-winds
(``data.real_microwave``'s docstring covers that earlier decision):

======================  =======  =========  =====================  =========================
Channel                 Product  Variable   Real units              Notes
======================  =======  =========  =====================  =========================
ir_brightness_temp_k    CMIPF    CMI (C14)  K                       11.2 um clean LW IR window
water_vapor_..._k       CMIPF    CMI (C09)  K                       6.9 um mid-level WV
visible_reflectance     CMIPF    CMI (C02)  1 (albedo, 0-1)         0.64 um red visible
sst_c                   SSTF     SST        K (converted to C)      Sea surface skin temp
rain_rate_mm_hr         RRQPEF   RRQPE      mm h-1                  Quantitative precip est.
======================  =======  =========  =====================  =========================

**Full-object download is not viable** -- a full-disk CMIPF channel 2
file is ~430 MB (confirmed live). Instead this reads lazily via
``fsspec``'s HTTP filesystem + ``h5netcdf``'s chunked access: confirmed
live that slicing a real 64x64 storm-relative crop out of a real 430 MB
file only transfers ~8 MB over HTTP, not the full object -- the
"partial HTTP-range reads via fsspec/h5netcdf" option the wiki's own
Data-Sources page flagged as unconfirmed is now confirmed to work.

**Real geolocation, not approximated.** GOES imagery is stored in the
ABI Fixed Grid (a geostationary projection, scan angles in radians, not
a lat/lon grid) -- converting a storm's real lat/lon into the correct
pixel index needs the real projection math NOAA's own metadata
describes (``goes_imager_projection``: perspective height, ellipsoid,
sub-satellite longitude). Uses ``pyproj`` (added as a new dependency --
safer than hand-rolling geostationary-projection trigonometry) rather
than approximating with a flat lat/lon grid, which would silently
misplace every crop. Verified live against a real currently-active
storm's real position (AL062026 "Fay"): the projected pixel index
landed on 100% real, non-missing reflectance data in the physically
sane 0-1 range.

**Quality-flagged pixels are masked, not presented as good data.**
Every product carries a real ``DQF`` (data quality flag) variable;
``DQF != 0`` (not "good_pixel_qf") becomes NaN here rather than being
silently included.

Satellite selection is the caller's choice, not auto-detected --
GOES-19 ("G19", GOES-East, sub-satellite longitude -75.0) is the real
default since this project's only trained basin is Atlantic; GOES-18
("G18", GOES-West, -137.2) covers the Pacific for a caller that wants
it. No basin-based auto-selection is built here since nothing calls
this with a basin yet -- same "don't invent an interface nobody's
using" restraint as the other #147 sources.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

import numpy as np

from .satellite import SatelliteCrop

_S3_NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

#: G18 = GOES-West (Pacific view), G19 = GOES-East (Atlantic/CONUS view,
#: the real default -- this project's only trained basin is Atlantic).
GOES_BUCKETS: dict[str, str] = {"G18": "noaa-goes18", "G19": "noaa-goes19"}

#: Real ABI band assignments (NOAA GOES-R Product User Guide, a public,
#: documented instrument spec -- not guessed).
GOES_IR_CHANNEL = 14
GOES_WV_CHANNEL = 9
GOES_VIS_CHANNEL = 2

_GOES_HINT = "real GOES fetch needs the 'gridded' extra: uv sync --extra gridded"

_TIMEOUT_S = 30.0


class GoesFetchError(RuntimeError):
    """A real fetch, listing, or decode failure talking to NOAA's GOES archive."""


def require_goes_deps() -> None:
    try:
        import h5netcdf  # noqa: F401, PLC0415
        import pyproj  # noqa: F401, PLC0415
        import requests  # noqa: F401, PLC0415
        import xarray  # noqa: F401, PLC0415
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(_GOES_HINT) from exc


def _list_scan_keys(bucket: str, prefix: str, *, timeout: float = _TIMEOUT_S) -> list[str]:
    """Real S3 ``ListObjectsV2`` keys under ``prefix`` -- exact scan
    start/end/created timestamps aren't purely formulaic (confirmed live:
    the trailing millisecond field isn't a fixed constant to rely on), so
    this lists real objects rather than guessing a filename."""
    import requests  # noqa: PLC0415

    resp = requests.get(
        f"https://{bucket}.s3.amazonaws.com/",
        params={"list-type": "2", "prefix": prefix},
        timeout=timeout,
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.text)  # noqa: S314 - trusted AWS response, not user input
    return [el.text for el in root.findall(".//s3:Contents/s3:Key", _S3_NS) if el.text]


def _parse_scan_start(key: str) -> datetime:
    """Real scan start time from a real GOES filename's ``sYYYYDDDHHMMSSf`` field."""
    marker = "_s"
    idx = key.index(marker) + len(marker)
    field = key[idx : idx + 13]  # YYYYDDDHHMMSS
    return datetime.strptime(field, "%Y%j%H%M%S")


def _nearest_scan_key(keys: list[str], valid_time: datetime) -> str:
    if not keys:
        raise GoesFetchError("no real scans found for the requested hour")
    target = valid_time.replace(tzinfo=None)
    return min(keys, key=lambda k: abs((_parse_scan_start(k) - target).total_seconds()))


def _find_real_scan(
    satellite: str, product: str, valid_time: datetime, *, channel: int | None = None,
) -> str:
    if satellite not in GOES_BUCKETS:
        raise GoesFetchError(
            f"unknown satellite {satellite!r}; expected one of {tuple(GOES_BUCKETS)}"
        )
    bucket = GOES_BUCKETS[satellite]
    prefix = f"{product}/{valid_time:%Y}/{valid_time:%j}/{valid_time:%H}/"
    if channel is not None:
        prefix += f"OR_{product}-M6C{channel:02d}"
    keys = _list_scan_keys(bucket, prefix)
    key = _nearest_scan_key(keys, valid_time)
    return f"https://{bucket}.s3.amazonaws.com/{key}"


def _lazy_open(url: str) -> Any:
    require_goes_deps()
    import fsspec  # noqa: PLC0415
    import xarray as xr  # noqa: PLC0415

    fs = fsspec.filesystem("https")
    fh = fs.open(url, "rb")
    try:
        return xr.open_dataset(fh, engine="h5netcdf")
    except Exception as exc:
        raise GoesFetchError(f"{url}: not a valid/expected GOES product file -- {exc}") from exc


def _pixel_index(ds: Any, center_lat: float, center_lon: float) -> tuple[int, int]:
    """Real ABI Fixed Grid geostationary projection -> nearest pixel
    index for ``(center_lat, center_lon)``. Verified live against a real
    active storm's real position before trusting this for a crop."""
    import pyproj  # noqa: PLC0415

    proj_attrs = ds["goes_imager_projection"].attrs
    geos = pyproj.CRS.from_dict(
        {
            "proj": "geos",
            "h": proj_attrs["perspective_point_height"],
            "a": proj_attrs["semi_major_axis"],
            "b": proj_attrs["semi_minor_axis"],
            "lon_0": proj_attrs["longitude_of_projection_origin"],
            "sweep": proj_attrs["sweep_angle_axis"],
        }
    )
    transformer = pyproj.Transformer.from_crs("EPSG:4326", geos, always_xy=True)
    x_m, y_m = transformer.transform(center_lon, center_lat)
    height = proj_attrs["perspective_point_height"]
    x_rad, y_rad = x_m / height, y_m / height

    x_coords = ds["x"].to_numpy()
    y_coords = ds["y"].to_numpy()
    xi = int(np.argmin(np.abs(x_coords - x_rad)))
    yi = int(np.argmin(np.abs(y_coords - y_rad)))
    return yi, xi


def _crop_variable(
    ds: Any, var_name: str, center_lat: float, center_lon: float, size: int,
) -> np.ndarray:
    """Real ``size x size`` crop of ``var_name`` centred on
    ``(center_lat, center_lon)``, with real ``DQF``-flagged pixels
    masked to NaN rather than presented as good data."""
    yi, xi = _pixel_index(ds, center_lat, center_lon)
    half = size // 2
    y_slice = slice(yi - half, yi - half + size)
    x_slice = slice(xi - half, xi - half + size)

    values = ds[var_name].isel(y=y_slice, x=x_slice).to_numpy().astype(np.float64)
    if "DQF" in ds:
        dqf = ds["DQF"].isel(y=y_slice, x=x_slice).to_numpy()
        values[dqf != 0] = np.nan
    if values.shape != (size, size):
        raise GoesFetchError(
            f"{var_name}: crop landed off the real image edge -- got shape {values.shape}, "
            f"expected ({size}, {size}); center_lat/center_lon may be too close to the disk limb"
        )
    return values


def fetch_real_satellite_crop(
    storm_id: str, valid_time: datetime, center_lat: float, center_lon: float,
    *, satellite: str = "G19", size: int = 64,
) -> SatelliteCrop:
    """Real storm-relative ``SatelliteCrop``, same shape/channel order
    ``data.satellite.generate_satellite_crop`` produces synthetically --
    fetches and combines five real NOAA products (see module docstring).

    Each product is a separate real fetch (different files, different
    real cadences); a fetch/crop failure for any one channel raises
    rather than silently zero-filling it, so a caller never trains on a
    channel that looks real but silently isn't.
    """
    require_goes_deps()

    ir_url = _find_real_scan(satellite, "ABI-L2-CMIPF", valid_time, channel=GOES_IR_CHANNEL)
    wv_url = _find_real_scan(satellite, "ABI-L2-CMIPF", valid_time, channel=GOES_WV_CHANNEL)
    vis_url = _find_real_scan(satellite, "ABI-L2-CMIPF", valid_time, channel=GOES_VIS_CHANNEL)
    sst_url = _find_real_scan(satellite, "ABI-L2-SSTF", valid_time)
    rain_url = _find_real_scan(satellite, "ABI-L2-RRQPEF", valid_time)

    ir = _crop_variable(_lazy_open(ir_url), "CMI", center_lat, center_lon, size)
    wv = _crop_variable(_lazy_open(wv_url), "CMI", center_lat, center_lon, size)
    vis = _crop_variable(_lazy_open(vis_url), "CMI", center_lat, center_lon, size)
    sst_k = _crop_variable(_lazy_open(sst_url), "SST", center_lat, center_lon, size)
    rain = _crop_variable(_lazy_open(rain_url), "RRQPE", center_lat, center_lon, size)

    # Stack order must match CHANNEL_NAMES exactly -- SatelliteCrop.__post_init__
    # already validates the channel count, no need to assert it again here.
    channels = np.stack([ir, wv, vis, sst_k - 273.15, rain], axis=0)
    return SatelliteCrop(storm_id=storm_id, valid_time=valid_time, channels=channels)
