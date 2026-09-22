"""Real NDBC buoy / C-MAN station observations (the ``ndbc`` source, #147).

Format reference: NOAA NDBC's own ``realtime2`` product -- confirmed live
against two real, structurally different station types (a moored buoy,
41002, and a coastal C-MAN station, CDRF1): identical 17-column layout,
whitespace-separated (fixed-width columns in principle, but NDBC's own
docs note the exact width can vary slightly, so this tokenizes on
whitespace like ``data.atcf``'s TC-Vitals parser does, for the same
reason). Two header rows (names, then units) precede the data -- this
parser reads the real header row rather than hardcoding column positions,
since NDBC's own web data guide notes some station types omit columns
(e.g. a land station with no wave sensor).

No credentials, no rate limit: a plain HTTPS GET, same "anonymous public
archive" tier as ``besttrack_working``/``gdas_gfs``. Real coverage is a
rolling 45 days per station (older data lives in NDBC's separate historical
archive, not fetched here).
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.error import URLError

_REALTIME2_URL = "https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt"

#: Real NDBC sentinel for a field that was not measured/reported.
MISSING = "MM"

#: Bounded, not arbitrary -- a hung request must not hang a cold start.
_TIMEOUT_S = 15.0

#: realtime2's own column -> attribute name mapping (its header row uses
#: these exact tokens, confirmed live 2026-09-22). Datetime columns
#: (YY/MM/DD/hh/mm) are handled separately, not through this map.
_COLUMN_TO_FIELD = {
    "WDIR": "wind_dir_deg",
    "WSPD": "wind_speed_mps",
    "GST": "gust_mps",
    "WVHT": "wave_height_m",
    "DPD": "dominant_wave_period_s",
    "APD": "avg_wave_period_s",
    "MWD": "wave_dir_deg",
    "PRES": "pressure_hpa",
    "ATMP": "air_temp_c",
    "WTMP": "water_temp_c",
    "DEWP": "dewpoint_c",
    "VIS": "visibility_nmi",
    "PTDY": "pressure_tendency_hpa",
    "TIDE": "tide_ft",
}


class NdbcFetchError(RuntimeError):
    """A real fetch or parse failure talking to NDBC's realtime2 archive."""


@dataclass(frozen=True, slots=True)
class NdbcObservation:
    """One real NDBC realtime2 row. Every field but ``station_id``/
    ``valid_time`` is ``None`` when NDBC reported it as missing (``MM``) or
    the station's column set doesn't include it at all."""

    station_id: str
    valid_time: datetime
    wind_dir_deg: float | None = None
    wind_speed_mps: float | None = None
    gust_mps: float | None = None
    wave_height_m: float | None = None
    dominant_wave_period_s: float | None = None
    avg_wave_period_s: float | None = None
    wave_dir_deg: float | None = None
    pressure_hpa: float | None = None
    air_temp_c: float | None = None
    water_temp_c: float | None = None
    dewpoint_c: float | None = None
    visibility_nmi: float | None = None
    pressure_tendency_hpa: float | None = None
    tide_ft: float | None = None


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "anemoi-api/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:  # noqa: S310
            return resp.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise NdbcFetchError(f"GET {url} failed: {exc}") from exc


def fetch_ndbc_realtime2(station_id: str) -> str:
    """Real realtime2 text for ``station_id`` (e.g. ``"41002"``)."""
    return _get(_REALTIME2_URL.format(station_id=station_id.lower()))


def parse_ndbc_realtime2(text: str, station_id: str) -> list[NdbcObservation]:
    """Parse real realtime2 text into observations, newest first (NDBC's
    own real ordering). Raises on a missing/malformed header rather than
    guessing at column positions; skips (does not raise on) a data row
    that doesn't match the header's column count, since a single
    malformed row must not drop every other real observation."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines or not lines[0].startswith("#"):
        raise NdbcFetchError(f"{station_id}: no header row found")
    header = lines[0].lstrip("#").split()

    observations: list[NdbcObservation] = []
    for line in lines[2:]:  # row 0 = names, row 1 = units
        parts = line.split()
        if len(parts) != len(header):
            continue
        row = dict(zip(header, parts, strict=True))
        try:
            valid_time = datetime(
                int(row["YY"]), int(row["MM"]), int(row["DD"]),
                int(row["hh"]), int(row["mm"]), tzinfo=UTC,
            )
        except (KeyError, ValueError):
            continue

        fields: dict[str, float] = {}
        for column, attr in _COLUMN_TO_FIELD.items():
            raw = row.get(column)
            if raw is not None and raw != MISSING:
                try:
                    fields[attr] = float(raw)
                except ValueError:
                    pass

        observations.append(NdbcObservation(station_id=station_id, valid_time=valid_time, **fields))

    return observations


def fetch_and_parse_ndbc(station_id: str) -> list[NdbcObservation]:
    """Convenience: fetch + parse in one call."""
    return parse_ndbc_realtime2(fetch_ndbc_realtime2(station_id), station_id)
