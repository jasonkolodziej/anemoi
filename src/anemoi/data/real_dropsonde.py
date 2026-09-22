"""Real NOAA/AFRC dropsonde profiles (the ``dropsonde`` source, #147).

Format reference: NOAA HRD's real, anonymous FTP archive
(``ftp://ftp.aoml.noaa.gov/hrd/pub/data/dropsonde/``), organised
``HURR{yy}/operproc/{mission_id}_BUFR.tar.gz`` -- confirmed live
2026-09-22 against a real 2026-season mission (storm "Lowell",
``20260904I1_BUFR.tar.gz``). Each tarball holds one real WMO-standard
BUFR message per sonde (``{mission_id}-{drop_time}-{seq}-HX_{storm}-
{seq}_prof_trimQC.bfr``), decoded here via ``eccodes`` (the same
optional dependency GDAS's GRIB2 path already needs) -- no proprietary
format to reverse-engineer, unlike RSS's undocumented TC-winds fix
records (see ``data.real_microwave``'s docstring for that decision).

**Level ordering, verified against a real profile, not assumed:**
pressure decreases monotonically through the array -- surface first
(~1001 hPa in the real sample checked), release altitude last (~696 hPa,
consistent with a real aircraft dropsonde release near flight level).
Missing values use eccodes' own named sentinels
(``CODES_MISSING_DOUBLE``/``CODES_MISSING_LONG``), not a guessed magic
number -- confirmed these are exactly the raw values a real decode
returns before this module's own NaN-masking.
"""

from __future__ import annotations

import io
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from ftplib import FTP, error_perm

import numpy as np

_FTP_HOST = "ftp.aoml.noaa.gov"
_MISSION_DIR = "/hrd/pub/data/dropsonde/HURR{yy}/operproc"
_TIMEOUT_S = 30.0

_DROPSONDE_HINT = "real dropsonde decode needs the 'gridded' extra: uv sync --extra gridded"

#: Real BUFR keys read from each sonde profile -- names verified via a
#: real decode, not guessed (all standard WMO BUFR descriptors).
_PROFILE_KEYS = (
    "pressure", "airTemperature", "dewpointTemperature",
    "windSpeed", "windDirection", "nonCoordinateGeopotentialHeight",
)


class DropsondeFetchError(RuntimeError):
    """A real fetch, extraction, or decode failure for dropsonde data."""


def require_bufr_deps() -> None:
    try:
        import eccodes  # noqa: F401, PLC0415
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(_DROPSONDE_HINT) from exc


@dataclass(frozen=True, slots=True)
class DropsondeProfile:
    """One real dropsonde's decoded vertical profile.

    Per-level arrays are ordered surface-first (see module docstring);
    ``NaN`` where the real BUFR message reported a level as missing.
    """

    mission_id: str
    sonde_filename: str
    release_time: datetime
    release_lat: float
    release_lon: float
    pressure_pa: np.ndarray
    temperature_k: np.ndarray
    dewpoint_k: np.ndarray
    wind_speed_mps: np.ndarray
    wind_dir_deg: np.ndarray
    geopotential_height_m: np.ndarray


def _mission_dir(year: int) -> str:
    return _MISSION_DIR.format(yy=f"{year % 100:02d}")


def _ftp_connect() -> FTP:
    try:
        ftp = FTP(_FTP_HOST, timeout=_TIMEOUT_S)  # noqa: S321
        ftp.login()  # real anonymous access -- HRD's dropsonde archive needs no account
        return ftp
    except OSError as exc:
        raise DropsondeFetchError(f"FTP connection to {_FTP_HOST} failed: {exc}") from exc


def list_dropsonde_missions(year: int) -> list[str]:
    """Real available mission ids (e.g. ``"20260904I1"``) for ``year``'s
    hurricane season, newest-listing-order as the FTP server returns it."""
    ftp = _ftp_connect()
    try:
        try:
            names = ftp.nlst(_mission_dir(year))
        except error_perm as exc:
            raise DropsondeFetchError(f"{_mission_dir(year)}: {exc}") from exc
    finally:
        ftp.quit()
    return sorted(
        {
            name.split("/")[-1].removesuffix("_BUFR.tar.gz")
            for name in names
            if name.endswith("_BUFR.tar.gz")
        }
    )


def fetch_dropsonde_mission_tarball(year: int, mission_id: str) -> bytes:
    """Real gzip'd tar bytes for one mission -- the caller decodes them
    with :func:`parse_dropsonde_mission_tarball`."""
    path = f"{_mission_dir(year)}/{mission_id}_BUFR.tar.gz"
    ftp = _ftp_connect()
    buf = io.BytesIO()
    try:
        try:
            ftp.retrbinary(f"RETR {path}", buf.write)
        except error_perm as exc:
            raise DropsondeFetchError(f"{path}: {exc}") from exc
    finally:
        ftp.quit()
    return buf.getvalue()


#: eccodes' own named missing-value sentinels for a double/long BUFR
#: field -- not a guessed magic number, confirmed these are exactly what
#: a real decode returns for an unreported level.
_CODES_MISSING_DOUBLE = -1e100
_CODES_MISSING_LONG = 2147483647


def _mask_missing(raw: np.ndarray) -> np.ndarray:
    """Real eccodes missing-value sentinels -> NaN, everything else
    unchanged. Pulled out of ``_decode_one_sonde`` so the masking logic
    is testable without a real BUFR decode."""
    out = raw.astype(np.float64).copy()
    missing = np.isclose(out, _CODES_MISSING_DOUBLE) | (out == float(_CODES_MISSING_LONG))
    out[missing] = np.nan
    return out


def _decode_one_sonde(mission_id: str, filename: str, bufr_bytes: bytes) -> DropsondeProfile | None:
    import eccodes  # noqa: PLC0415

    # eccodes' BUFR reader needs a real file descriptor (codes_bufr_new_from_
    # file), unlike codes_new_from_message -- confirmed live: the latter
    # assumes GRIB framing ("No final 7777 in message!") and can't read a
    # real BUFR message directly from bytes. Same real tempfile pattern
    # real_gridded.py's GDAS GRIB2 decode already uses.
    with tempfile.NamedTemporaryFile(suffix=".bfr") as tmp:
        tmp.write(bufr_bytes)
        tmp.flush()
        with open(tmp.name, "rb") as fh:
            msg = eccodes.codes_bufr_new_from_file(fh)
    if msg is None:
        return None
    try:
        eccodes.codes_set(msg, "unpack", 1)
        release_time = datetime(
            eccodes.codes_get(msg, "#1#year"), eccodes.codes_get(msg, "#1#month"),
            eccodes.codes_get(msg, "#1#day"), eccodes.codes_get(msg, "#1#hour"),
            eccodes.codes_get(msg, "#1#minute"), eccodes.codes_get(msg, "#1#second"),
            tzinfo=UTC,
        )
        release_lat = float(eccodes.codes_get(msg, "latitude"))
        release_lon = float(eccodes.codes_get(msg, "longitude"))

        profile: dict[str, np.ndarray] = {}
        for key in _PROFILE_KEYS:
            raw = np.array(eccodes.codes_get_array(msg, key), dtype=np.float64)
            profile[key] = _mask_missing(raw)
    finally:
        eccodes.codes_release(msg)

    return DropsondeProfile(
        mission_id=mission_id,
        sonde_filename=filename,
        release_time=release_time,
        release_lat=release_lat,
        release_lon=release_lon,
        pressure_pa=profile["pressure"],
        temperature_k=profile["airTemperature"],
        dewpoint_k=profile["dewpointTemperature"],
        wind_speed_mps=profile["windSpeed"],
        wind_dir_deg=profile["windDirection"],
        geopotential_height_m=profile["nonCoordinateGeopotentialHeight"],
    )


def parse_dropsonde_mission_tarball(
    mission_id: str, tarball_bytes: bytes,
) -> list[DropsondeProfile]:
    """Decode every real ``.bfr`` sonde in a mission tarball. A single
    sonde's own decode failure (a real, occasionally corrupt file) is
    skipped rather than dropping every other real sonde in the mission."""
    require_bufr_deps()
    profiles: list[DropsondeProfile] = []
    try:
        with tarfile.open(fileobj=io.BytesIO(tarball_bytes), mode="r:gz") as tar:
            for member in tar.getmembers():
                if not member.name.endswith(".bfr"):
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                try:
                    profile = _decode_one_sonde(mission_id, member.name, extracted.read())
                except Exception:  # noqa: BLE001 - one bad sonde must not drop the rest
                    continue
                if profile is not None:
                    profiles.append(profile)
    except tarfile.TarError as exc:
        raise DropsondeFetchError(f"{mission_id}: not a valid tar.gz bundle -- {exc}") from exc
    return profiles


def fetch_and_parse_dropsonde_mission(year: int, mission_id: str) -> list[DropsondeProfile]:
    """Convenience: fetch + parse an entire mission in one call."""
    tarball = fetch_dropsonde_mission_tarball(year, mission_id)
    return parse_dropsonde_mission_tarball(mission_id, tarball)
