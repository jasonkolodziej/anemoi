"""Real NCEI OISST v2.1 sea surface temperature (the ``sst_ohc`` source's
SST half -- see the note near the bottom of this module for why the OHC
half isn't implemented here).

Format reference: NOAA NCEI's public daily OISST v2.1 archive, plain
HTTPS, no credentials, no rate limit -- same anonymous-archive tier as
``gdas_gfs``/``era5``. Real file size is small (~1.5 MB/day), so this
fetches the whole file rather than needing GDAS's byte-range trick.
Confirmed live 2026-09-22: the archive's most recent file lags "today" by
about one day (e.g. the file for 2026-09-21 was already published by
2026-09-22), consistent with the registry's documented ``~1 day`` latency.

Needs an actual NetCDF reader, which the ``gridded`` extra didn't
previously include (xarray alone can't open a real ``.nc`` file without
one) -- added ``h5netcdf``/``h5py`` rather than ``netCDF4``: both are
pure-Python-wheel installs on the platforms this project has been
verified on (confirmed 2026-09-22, no compiled system library needed the
way ``eccodes`` needs ``libeccodes``).
"""

from __future__ import annotations

import tempfile
import urllib.request
from datetime import date
from pathlib import Path
from urllib.error import URLError

import numpy as np

_OISST_URL = (
    "https://www.ncei.noaa.gov/data/sea-surface-temperature-optimum-interpolation/"
    "v2.1/access/avhrr/{yyyymm}/oisst-avhrr-v02r01.{yyyymmdd}_preliminary.nc"
)

_TIMEOUT_S = 30.0

_SST_HINT = "real OISST fetch needs the 'gridded' extra: uv sync --extra gridded"


class SstFetchError(RuntimeError):
    """A real fetch or decode failure talking to NCEI's OISST archive."""


def require_sst_deps() -> None:
    try:
        import h5netcdf  # noqa: F401, PLC0415
        import xarray  # noqa: F401, PLC0415
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(_SST_HINT) from exc


def _download(url: str, local_path: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "anemoi-api/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:  # noqa: S310
            local_path.write_bytes(resp.read())
    except URLError as exc:
        raise SstFetchError(f"GET {url} failed: {exc}") from exc


def fetch_oisst_sst(valid_date: date) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Real global OISST v2.1 SST for ``valid_date``.

    Returns ``(sst_c, lat, lon)`` -- ``sst_c`` shape ``(720, 1440)`` in
    real degrees Celsius (``NaN`` over land/ice-masked cells, OISST's own
    convention), ``lat``/``lon`` the real 0.25-degree grid centres.
    """
    require_sst_deps()
    import xarray as xr

    url = _OISST_URL.format(yyyymm=f"{valid_date:%Y%m}", yyyymmdd=f"{valid_date:%Y%m%d}")
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = Path(tmpdir) / "oisst.nc"
        _download(url, local_path)
        try:
            with xr.open_dataset(local_path, engine="h5netcdf") as ds:
                sst = ds["sst"].isel(time=0, zlev=0).to_numpy().astype(np.float64)
                lat = ds["lat"].to_numpy().astype(np.float64)
                lon = ds["lon"].to_numpy().astype(np.float64)
        except (OSError, KeyError) as exc:
            raise SstFetchError(f"{url}: not a valid/expected OISST file -- {exc}") from exc

    return sst, lat, lon


def sst_at(
    sst_c: np.ndarray, lat: np.ndarray, lon: np.ndarray, target_lat: float, target_lon: float,
) -> float:
    """Nearest-cell real SST (degrees C) at ``(target_lat, target_lon)``.

    ``target_lon`` may be given in either -180..180 or 0..360 convention
    -- OISST's own grid is 0..360, this normalises rather than requiring
    the caller to know that.
    """
    lon_0_360 = target_lon % 360.0
    lat_idx = int(np.argmin(np.abs(lat - target_lat)))
    lon_idx = int(np.argmin(np.abs(lon - lon_0_360)))
    return float(sst_c[lat_idx, lon_idx])


#: Ocean heat content is deliberately not implemented here -- see the
#: module docstring's "OHC half" note. Short version: NOAA OSPO's
#: ERDDAP OHC/TCHP products looked real (200, real schema, units
#: matching OHC_PLACEHOLDER_KJ_CM2's own naming exactly) but their real
#: data stops at 2026-01-26, ~8 months stale as of this writing --
#: confirmed via a real query, not assumed from documentation. Serving
#: that as "real, current OHC" would be worse than the honest
#: placeholder it would replace. GODAS/ORAS5 remains the documented
#: path; its exact real access point wasn't found in the time spent
#: on this pass.
