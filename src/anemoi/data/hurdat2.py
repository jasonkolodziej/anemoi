"""HURDAT2 best-track archive parser (final quality).

Scope v2.1 PLAN.md §4 "productionise" table -- storm archive row. Parses the
public NHC HURDAT2 format into ``TrackQuality.FINAL`` :class:`Track` objects,
replacing ``data.synthetic``'s role as the storm-archive source. It does not
replace the emulator: ``besttrack.emulate_working_track`` still degrades a
parsed FINAL track into WORKING-equivalent fixes for Stage B input, and
``besttrack.recalibrate_from_pairs`` still needs real *paired* working/final
data (a-/b-deck against this) to measure the emulator's true error -- see
``data.atcf`` for the working-side parser.

Format reference: NHC, "HURDAT2 Format" (https://www.nhc.noaa.gov/data/hurdat/).
Each storm is a header line followed by its best-track entries::

    AL092020,         LAURA,     41,
    20200827, 1800,  , HU, 29.2N,  93.4W, 130, 950, ...
    ...

Only synoptic-hour (00/06/12/18Z) entries become a :class:`Fix` -- HURDAT2
also carries intermediate/special entries (landfall, peak intensity) at
off-synoptic times, and rows with a missing (``-999``) wind or pressure,
neither of which the ``Fix``/``Track`` contract can represent. Those rows are
skipped rather than guessed at; a storm left with no representable fixes is
skipped entirely.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ..geo import wrap_longitude
from ..time_utils import SYNOPTIC_HOURS
from .besttrack import Fix, Track, TrackQuality

#: HURDAT2's sentinel for a field that was not measured/reported.
MISSING = -999.0

#: Minimum comma-separated fields on a header / data line before we consider
#: the line malformed rather than just short on trailing (optional) columns.
_HEADER_FIELDS = 3
_DATA_FIELDS = 8


class Hurdat2Error(ValueError):
    """Malformed HURDAT2 input."""


def _parse_latlon(lat_field: str, lon_field: str) -> tuple[float, float]:
    """Parse HURDAT2's ``28.0N`` / ``93.4W``-style fields.

    A handful of real entries -- extratropical remnants tracked across the
    prime meridian (e.g. into the Norwegian Sea) -- carry a "W" longitude
    magnitude past 180 (``354.5W``) rather than switching to "E", counting
    degrees west all the way around instead of wrapping. ``wrap_longitude``
    normalises that (and any ordinary value) into [-180, 180).
    """
    lat_field, lon_field = lat_field.strip(), lon_field.strip()
    if len(lat_field) < 2 or lat_field[-1] not in "NS":
        raise Hurdat2Error(f"malformed latitude: {lat_field!r}")
    if len(lon_field) < 2 or lon_field[-1] not in "EW":
        raise Hurdat2Error(f"malformed longitude: {lon_field!r}")
    lat = float(lat_field[:-1]) * (1.0 if lat_field[-1] == "N" else -1.0)
    lon = float(lon_field[:-1]) * (1.0 if lon_field[-1] == "E" else -1.0)
    return lat, float(wrap_longitude(lon))


def _parse_header(line: str) -> tuple[str, int]:
    parts = [p.strip() for p in line.strip().rstrip(",").split(",")]
    if len(parts) < _HEADER_FIELDS:
        raise Hurdat2Error(f"malformed header line: {line!r}")
    storm_id = parts[0]
    if not storm_id:
        raise Hurdat2Error(f"empty storm id in header line: {line!r}")
    try:
        n_entries = int(parts[2])
    except ValueError as exc:
        raise Hurdat2Error(f"malformed entry count in header line: {line!r}") from exc
    return storm_id, n_entries


def _parse_data_line(storm_id: str, line: str) -> Fix | None:
    parts = [p.strip() for p in line.strip().rstrip(",").split(",")]
    if len(parts) < _DATA_FIELDS:
        raise Hurdat2Error(f"malformed data line: {line!r}")
    date_s, time_s = parts[0], parts[1]
    lat_s, lon_s, wind_s, pres_s = parts[4], parts[5], parts[6], parts[7]

    if len(time_s) != 4 or not time_s.isdigit():
        raise Hurdat2Error(f"malformed time field: {line!r}")
    hour = int(time_s[:2])
    if hour not in SYNOPTIC_HOURS or time_s[2:] != "00":
        return None  # off-synoptic / special (e.g. landfall) entry

    wind = float(wind_s)
    pressure = float(pres_s)
    if wind == MISSING or pressure == MISSING:
        return None  # not representable without guessing a value

    valid_time = datetime.strptime(date_s + time_s, "%Y%m%d%H%M").replace(tzinfo=UTC)
    lat, lon = _parse_latlon(lat_s, lon_s)

    return Fix(
        storm_id=storm_id,
        valid_time=valid_time,
        lat=lat,
        lon=lon,
        max_wind_kt=wind,
        min_pressure_mb=pressure,
        quality=TrackQuality.FINAL,
    )


def parse_hurdat2(text: str) -> list[Track]:
    """Parse a full HURDAT2 file's text into FINAL-quality :class:`Track` objects.

    One :class:`Track` per storm header block, in file order. A storm with no
    synoptic-hour, fully-reported entries after filtering is skipped rather
    than raised on -- it carries no fix the rest of the pipeline can use.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    tracks: list[Track] = []
    i = 0
    while i < len(lines):
        storm_id, n_entries = _parse_header(lines[i])
        i += 1
        raw_rows, i = lines[i : i + n_entries], i + n_entries
        if len(raw_rows) < n_entries:
            raise Hurdat2Error(
                f"storm {storm_id}: header declares {n_entries} entries, "
                f"only {len(raw_rows)} remain in the file"
            )

        fixes = [f for row in raw_rows if (f := _parse_data_line(storm_id, row)) is not None]
        if fixes:
            tracks.append(Track(storm_id=storm_id, fixes=tuple(fixes)))
    return tracks


def parse_hurdat2_file(path: str | Path) -> list[Track]:
    """Convenience wrapper: parse a HURDAT2 archive file from disk."""
    return parse_hurdat2(Path(path).read_text())
