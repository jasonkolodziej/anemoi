"""Real RSS SSMIS microwave radiometer data (DMSP F16/F17/F18 satellites).

The ``microwave`` source registered in :mod:`anemoi.data.sources` had no
real fetch implementation at all before this -- see the wiki's Data-Sources
"Implementation status" table and GitHub #147. RSS's anonymous FTP access
was discontinued (``220 Anonymous access discontinued. See
www.remss.com/register``, confirmed live); a real account is required --
register at https://register.remss.com/, then set ``RSS_FTP_USERNAME`` /
``RSS_FTP_PASSWORD`` (see ``example.env``).

**Byte layout verified two independent ways, not guessed:** RSS's own
reference Python reader (``ftp.remss.com:/ssmi/ssmi_support/python/
ssmis_daily_v7.py`` + ``bytemaps.py``, fetched and read directly), and
cross-checked against their public documentation
(https://remss.com/missions/ssmi/, "Gridded Binary Files" section) -- both
agree exactly on every scale/offset/grid value below. A gzip'd file is a
headerless ``uint8`` array shaped ``(2, 5, 720, 1440)``: (ascending/
descending pass, variable, latitude, longitude), 0.25-degree global grid,
cell (0, 0) centred at -89.875 lat / 0.125 lon. Five variables in file
order: time (fractional GMT hour), 10 m wind speed, columnar water vapor,
cloud liquid water, rain rate. Byte value ``v <= 250`` is real data
(``v * scale + offset``); ``v > 250`` is a real flag (251 = missing due to
rain, 252 = sea ice, 253 = bad observation, 254 = no observation, 255 =
land) -- this module treats all of those as missing (NaN) rather than
distinguishing land/ice from a true gap, since nothing here needs that
distinction yet; a caller that does can be built without re-deriving the
byte layout.

Confirmed live against the real 2026 hurricane season (2026-09-22): F18's
``bmaps_v08/y2026/m09/`` updates same-day, and RSS's storm-specific
``TC-winds`` product (a separate, ATCF-fix-format-derived dataset, not
implemented here -- its exact field semantics beyond the leading basin/
cyclone/time/sensor/lat/lon columns aren't documented anywhere RSS
publishes, so guessing at the wind-radii columns risked mislabelling real
data) has real live fix records for the exact storms this system already
tracks (confirmed: EP172026's real lat/lon from RSS's SMAP fix matched the
live API's own value almost exactly).
"""

from __future__ import annotations

import gzip
import io
import os
from dataclasses import dataclass
from datetime import date
from ftplib import FTP, error_perm

import numpy as np

_RSS_FTP_HOST = "ftp.remss.com"
_TIMEOUT_S = 30.0

_ENV_VARS = {"username": "RSS_FTP_USERNAME", "password": "RSS_FTP_PASSWORD"}

#: Real SSMIS satellites RSS currently distributes daily bytemaps for.
SSMIS_SATELLITES: tuple[str, ...] = ("f16", "f17", "f18")

#: (byte-array index, scale, offset) per variable, in the file's real
#: on-disk order.
_VARIABLES: dict[str, tuple[int, float, float]] = {
    "time_hours_gmt": (0, 0.1, 0.0),
    "wind_speed_mps": (1, 0.2, 0.0),
    "vapor_mm": (2, 0.3, 0.0),
    "cloud_mm": (3, 0.01, -0.05),
    "rain_mm_hr": (4, 0.1, 0.0),
}

_N_LAT = 720
_N_LON = 1440
_GRID_LAT = np.array([0.25 * i - 89.875 for i in range(_N_LAT)])
_GRID_LON = np.array([0.25 * i + 0.125 for i in range(_N_LON)])

#: Byte codes above this are all real flags (missing/ice/bad/land), never
#: real data -- see the module docstring for what each one means.
_MAX_VALID_BYTE = 250


class MicrowaveFetchError(RuntimeError):
    """A real fetch, auth, or decode failure talking to RSS's FTP archive."""


@dataclass(frozen=True, slots=True)
class RSSFtpCredentials:
    username: str
    password: str

    @classmethod
    def from_env(cls) -> RSSFtpCredentials:
        missing = [env for env in _ENV_VARS.values() if not os.environ.get(env)]
        if missing:
            raise MicrowaveFetchError(
                f"missing environment variable(s) {missing} -- copy example.env to "
                ".env and fill in RSS's real FTP credentials (anonymous access was "
                "discontinued; register at https://register.remss.com/)"
            )
        return cls(
            username=os.environ[_ENV_VARS["username"]],
            password=os.environ[_ENV_VARS["password"]],
        )


def _bytemap_path(satellite: str, valid_date: date) -> str:
    if satellite not in SSMIS_SATELLITES:
        raise MicrowaveFetchError(
            f"unknown SSMIS satellite {satellite!r}; expected one of {SSMIS_SATELLITES}"
        )
    return (
        f"/ssmi/{satellite}/bmaps_v08/y{valid_date:%Y}/m{valid_date:%m}/"
        f"{satellite}_{valid_date:%Y%m%d}v8.gz"
    )


def fetch_ssmis_daily_bytemap(
    satellite: str, valid_date: date, credentials: RSSFtpCredentials | None = None,
) -> bytes:
    """Real gzip'd bytemap bytes for ``satellite`` on ``valid_date`` -- the
    caller decodes them with :func:`decode_ssmis_bytemap`. Kept separate
    (matching ``real_gridded``'s fetch/decode split) so a decode can be
    tested against a small real or constructed fixture without a real FTP
    round trip every time.
    """
    creds = credentials or RSSFtpCredentials.from_env()
    path = _bytemap_path(satellite, valid_date)
    buf = io.BytesIO()
    try:
        ftp = FTP(_RSS_FTP_HOST, timeout=_TIMEOUT_S)  # noqa: S321
        try:
            ftp.login(user=creds.username, passwd=creds.password)
            ftp.retrbinary(f"RETR {path}", buf.write)
        finally:
            ftp.quit()
    except error_perm as exc:
        raise MicrowaveFetchError(
            f"{path}: FTP permission error (bad credentials or no such file) -- {exc}"
        ) from exc
    except OSError as exc:
        raise MicrowaveFetchError(f"{path}: FTP connection failed -- {exc}") from exc
    return buf.getvalue()


@dataclass(frozen=True, slots=True)
class SSMISDaily:
    """One real day's SSMIS bytemap -- ascending and descending passes.

    Each array in ``variables`` is shape ``(2, 720, 1440)`` -- (pass, lat,
    lon), pass 0 = ascending (local AM), pass 1 = descending (local PM),
    per RSS's real file layout. NaN where the source byte was a
    missing/bad/ice/land code (see module docstring).
    """

    satellite: str
    valid_date: date
    variables: dict[str, np.ndarray]
    lat: np.ndarray
    lon: np.ndarray


def decode_ssmis_bytemap(raw_gzip_bytes: bytes, satellite: str, valid_date: date) -> SSMISDaily:
    """Decode real gzip'd SSMIS bytemap bytes into real geophysical arrays.

    Raises :class:`MicrowaveFetchError` on a malformed/truncated file
    (wrong byte count for the real ``(2, 5, 720, 1440)`` shape) rather than
    silently reshaping into something wrong.
    """
    try:
        raw = gzip.decompress(raw_gzip_bytes)
    except gzip.BadGzipFile as exc:
        raise MicrowaveFetchError(f"{satellite} {valid_date}: not a valid gzip file") from exc

    expected = 2 * len(_VARIABLES) * _N_LAT * _N_LON
    if len(raw) != expected:
        raise MicrowaveFetchError(
            f"{satellite} {valid_date}: decompressed to {len(raw)} bytes, "
            f"expected {expected} for a (2, {len(_VARIABLES)}, {_N_LAT}, {_N_LON}) bytemap"
        )
    bmap = np.frombuffer(raw, dtype=np.uint8).reshape(2, len(_VARIABLES), _N_LAT, _N_LON)

    variables: dict[str, np.ndarray] = {}
    for name, (index, scale, offset) in _VARIABLES.items():
        byte_values = bmap[:, index, :, :]
        real = byte_values.astype(np.float64) * scale + offset
        real[byte_values > _MAX_VALID_BYTE] = np.nan
        variables[name] = real

    return SSMISDaily(
        satellite=satellite, valid_date=valid_date, variables=variables,
        lat=_GRID_LAT, lon=_GRID_LON,
    )


def fetch_and_decode_ssmis_daily(
    satellite: str, valid_date: date, credentials: RSSFtpCredentials | None = None,
) -> SSMISDaily:
    """Convenience: fetch + decode in one call."""
    raw = fetch_ssmis_daily_bytemap(satellite, valid_date, credentials)
    return decode_ssmis_bytemap(raw, satellite, valid_date)
