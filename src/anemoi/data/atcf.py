"""ATCF b-deck, a-deck and TC-Vitals parsers (working-quality best track,
and the operational guidance it is verified against).

Scope v2.1 PLAN.md §4 "productionise" table -- working track row. These are
the real-time products the model actually sees in production, as opposed to
``data.hurdat2``'s post-season FINAL reanalysis: b-deck is issued within
hours of each synoptic time and is what NHC operationally calls the
"working" best track, so it parses into ``TrackQuality.WORKING`` fixes.
TC-Vitals is the raw per-cycle bulletin many downstream systems (including
the vitals gating this repo's scheduler models) actually consume.

Together with ``data.hurdat2`` and ``besttrack.recalibrate_from_pairs``,
:func:`pair_by_valid_time` closes the loop PLAN.md §5 "Noise-emulator
recalibration" describes: pair a b-deck WORKING track against the matching
HURDAT2 FINAL track and measure the emulator's real error, instead of
relying on the scope's placeholder constants or the literature estimate in
``WorkingTrackNoise.from_literature()``.

`parse_adeck` reads the a-deck: every forecast technique's guidance for
one storm (NHC's official forecast, the GFS tracker, CLIPER...), in the
b-deck's row layout. It is read for verification only
(`training.baseline_backtest`), never as a model input: a technique's row
for cycle ``t`` is written hours after ``t``.

Format references:

* b-deck and a-deck: NRL ATCF ``abdeck.txt`` (comma-separated; basin/
  cyclone-number/date-time-group/technum/tech/tau/lat/lon/vmax/mslp/.../
  stormname).
* TC-Vitals: NCEP "Format of Tropical Cyclone Records (TCVITALS)"
  (fixed-column, whitespace-separated in practice since no field embeds a
  space). The field *order* below is verified against that spec; exact
  column widths can vary slightly by NCEP archive vintage, so this parser
  tokenizes on whitespace rather than slicing fixed columns -- validate
  against a live sample before relying on it in production.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from ..geo import wrap_longitude
from ..time_utils import SYNOPTIC_HOURS
from .besttrack import Fix, Track, TrackQuality

#: ATCF's sentinel for an unreported MSLP.
BDECK_MISSING_MSLP = 9999

#: TC-Vitals single-letter basin -> the two-letter ATCF basin this codebase
#: uses elsewhere (storm_id convention: e.g. "AL092020"). Only the codes we
#: can confirm are mapped; an unrecognised code raises rather than guesses.
TCVITALS_BASIN_MAP = {
    "L": "AL",  # Atlantic
    "E": "EP",  # Eastern Pacific
    "C": "CP",  # Central Pacific
    "W": "WP",  # Western Pacific
    "S": "SH",  # Southern Hemisphere
}

def storm_basin(storm_id: str) -> str:
    """The two-letter ATCF basin code a storm_id was minted with.

    Every storm_id in this codebase is built as ``basin + cyclone_number +
    year`` (see the parsers below), so this is a direct slice, not a lookup
    -- basin is already encoded in the id.

    Which basins the served models trained on is the registry's to say
    (`tracking.registry.ModelRegistry.trained_basins`), not a constant: a
    storm from any other basin is real data, but out of distribution -- an
    Atlantic-trained model learns "coastal storms curve toward increasing
    longitude", true in the Atlantic and backwards in the Eastern Pacific.
    """
    return storm_id[:2]


#: 1 m/s = this many knots. TC-Vitals reports wind in whole m/s; every other
#: source in this codebase (ATCF, HURDAT2) uses knots.
MPS_TO_KT = 1.943844


class AtcfError(ValueError):
    """Malformed ATCF b-deck input."""


class TcVitalsError(ValueError):
    """Malformed TC-Vitals input."""


def _parse_latlon(lat_field: str, lon_field: str) -> tuple[float, float]:
    lat_field, lon_field = lat_field.strip(), lon_field.strip()
    if len(lat_field) < 2 or lat_field[-1] not in "NS":
        raise AtcfError(f"malformed latitude: {lat_field!r}")
    if len(lon_field) < 2 or lon_field[-1] not in "EW":
        raise AtcfError(f"malformed longitude: {lon_field!r}")
    lat = (float(lat_field[:-1]) / 10.0) * (1.0 if lat_field[-1] == "N" else -1.0)
    lon = (float(lon_field[:-1]) / 10.0) * (1.0 if lon_field[-1] == "E" else -1.0)
    return lat, lon


def parse_bdeck(text: str) -> list[Track]:
    """Parse b-deck (working best track) text into WORKING-quality Tracks.

    Keeps only ``TECH == BEST`` rows at ``TAU == 0`` on a synoptic hour --
    the actual best-track analyses, not forecast-guidance rows (which share
    the same comma-separated shape at other TECH values) and not any
    off-synoptic interpolated entries. Rows with a missing (``9999``) MSLP
    are dropped, matching how ``data.hurdat2`` handles HURDAT2's ``-999``.

    One Track per basin+cyclone-number+year, entries in file order (b-deck
    files are normally one storm each, but concatenated multi-storm text is
    handled the same way as :func:`anemoi.data.hurdat2.parse_hurdat2`).
    """
    fixes_by_storm: dict[str, list[Fix]] = {}
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.rstrip(",").split(",")]
        if len(parts) < 10:
            raise AtcfError(f"line {lineno}: malformed b-deck record: {raw_line!r}")

        basin, cy, dtg, _technum, tech, tau = parts[0:6]
        lat_s, lon_s, vmax_s, mslp_s = parts[6:10]

        if tech != "BEST" or int(tau) != 0:
            continue
        if len(dtg) != 10 or not dtg.isdigit():
            raise AtcfError(f"line {lineno}: malformed date-time-group: {dtg!r}")
        hour = int(dtg[8:10])
        if hour not in SYNOPTIC_HOURS:
            continue

        mslp = float(mslp_s)
        vmax = float(vmax_s)
        if mslp == BDECK_MISSING_MSLP or not mslp_s:
            continue

        valid_time = datetime.strptime(dtg, "%Y%m%d%H").replace(tzinfo=UTC)
        lat, lon = _parse_latlon(lat_s, lon_s)
        storm_id = f"{basin.upper()}{int(cy):02d}{valid_time.year}"

        fix = Fix(
            storm_id=storm_id,
            valid_time=valid_time,
            lat=lat,
            lon=lon,
            max_wind_kt=vmax,
            min_pressure_mb=mslp,
            quality=TrackQuality.WORKING,
        )
        fixes_by_storm.setdefault(storm_id, []).append(fix)

    tracks: list[Track] = []
    for storm_id, fixes in fixes_by_storm.items():
        fixes.sort(key=lambda f: f.valid_time)
        deduped = [f for i, f in enumerate(fixes) if i == 0 or f.valid_time != fixes[i - 1].valid_time]
        tracks.append(Track(storm_id=storm_id, fixes=tuple(deduped)))
    return tracks


#: ``AL092024``: two-letter basin, two-digit cyclone number, four-digit season.
STORM_ID_RE = re.compile(r"[A-Z]{2}\d{6}")

#: Fields an a-deck row needs to carry a forecast point: through VMAX.
_ADECK_FIELDS = 9


@dataclass(frozen=True, slots=True)
class AdeckPoint:
    """One technique's forecast for one lead. Not every technique forecasts
    everything: CLP5, TVCN and XTRP give a track and no wind; IVCN and SHF5
    give a wind and no position. What a row does not give is None, never
    the file's zero."""

    lat: float | None
    lon: float | None
    max_wind_kt: float | None
    min_pressure_mb: float | None = None

    @property
    def has_position(self) -> bool:
        return self.lat is not None and self.lon is not None


@dataclass(frozen=True, slots=True)
class Adeck:
    """One storm's a-deck: each technique's forecast points, by
    ``(technique, initial time, tau in hours)``, with what was left out."""

    storm_id: str
    points: dict[tuple[str, datetime, int], AdeckPoint]
    #: Non-blank rows in the file, whatever their technique.
    n_rows: int
    #: Rows of a wanted technique that could not be read (too short, a
    #: malformed field, an off-synoptic initial time).
    n_skipped: int
    #: Rows of a wanted technique for another cyclone number.
    n_other_storm: int
    #: Rows kept whose BASIN column is not the storm id's (a storm keeps its
    #: number, and usually its column, when it crosses into another basin).
    n_basin_mismatch: int
    #: technique -> repeats of a (initial time, tau) that disagree with the
    #: row kept. A point normally repeats only for its 34/50/64 kt wind radii.
    conflicts: dict[str, int]

    def get(self, technique: str, init_time: datetime, tau_hours: int) -> AdeckPoint | None:
        return self.points.get((technique, init_time, tau_hours))

    def techniques(self) -> tuple[str, ...]:
        return tuple(sorted({tech for tech, _init, _tau in self.points}))

    def init_times(self, technique: str) -> frozenset[datetime]:
        """The initial times ``technique`` has any row for."""
        return frozenset(init for tech, init, _tau in self.points if tech == technique)


def _adeck_position(lat_field: str, lon_field: str) -> tuple[float | None, float | None]:
    if not lat_field or not lon_field:
        return None, None
    lat, lon = _parse_latlon(lat_field, lon_field)
    if lat == 0.0 and lon == 0.0:
        return None, None  # ``0N, 0W``: the technique gives no position
    if not -90.0 <= lat <= 90.0:
        raise AtcfError(f"latitude out of range: {lat_field!r}")
    return lat, float(wrap_longitude(lon))


def _adeck_positive(field: str) -> float | None:
    """A VMAX or MSLP field: blank or zero means not forecast."""
    if not field:
        return None
    value = float(field)
    return value if value > 0.0 else None


def parse_adeck(text: str, storm_id: str, techniques: Iterable[str] | None = None) -> Adeck:
    """Parse one storm's a-deck text into its techniques' forecast points.

    ``techniques`` limits what is read (a season's a-deck holds some 270
    techniques and hundreds of thousands of rows; a row of any other
    technique is dropped on its technique column alone). Rows are matched
    to ``storm_id`` by cyclone number, within the storm's own file -- not
    by the BASIN column, which is counted when it differs.

    A point repeats once per wind-radii threshold; the first row is kept
    and a repeat that disagrees with it is counted (`Adeck.conflicts`).
    Longitudes are wrapped into [-180, 180). Rows that cannot be read are
    counted, not raised on: an a-deck is a working file with rows from
    dozens of centres. Raises `AtcfError` only when ``storm_id`` is not an
    ATCF id or the text holds no a-deck row at all.
    """
    if not STORM_ID_RE.fullmatch(storm_id):
        raise AtcfError(f"not an ATCF storm id: {storm_id!r}")
    basin, number = storm_id[:2], int(storm_id[2:4])
    wanted = None if techniques is None else frozenset(techniques)

    points: dict[tuple[str, datetime, int], AdeckPoint] = {}
    conflicts: dict[str, int] = {}
    n_rows = n_records = n_skipped = n_other_storm = n_basin_mismatch = 0
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        n_rows += 1
        head = raw_line.split(",", 5)
        if len(head) < 5:
            continue  # no technique column: not a guidance row
        n_records += 1
        tech = head[4].strip()
        if wanted is not None and tech not in wanted:
            continue
        parts = [p.strip() for p in raw_line.split(",")]
        try:
            if len(parts) < _ADECK_FIELDS:
                raise AtcfError("too few fields")
            cyclone, tau = int(parts[1]), int(parts[5])
            init_time = datetime.strptime(parts[2], "%Y%m%d%H").replace(tzinfo=UTC)
            if len(parts[2]) != 10 or init_time.hour not in SYNOPTIC_HOURS:
                raise AtcfError("not a synoptic date-time-group")
            lat, lon = _adeck_position(parts[6], parts[7])
            wind = _adeck_positive(parts[8])
            mslp = _adeck_positive(parts[9]) if len(parts) > 9 else None
        except ValueError:  # AtcfError is one
            n_skipped += 1
            continue
        if cyclone != number:
            n_other_storm += 1
            continue
        if parts[0].upper() != basin:
            n_basin_mismatch += 1

        key = (tech, init_time, tau)
        kept = points.get(key)
        if kept is None:
            points[key] = AdeckPoint(lat=lat, lon=lon, max_wind_kt=wind, min_pressure_mb=mslp)
        elif (kept.lat, kept.lon, kept.max_wind_kt) != (lat, lon, wind):
            conflicts[tech] = conflicts.get(tech, 0) + 1

    if n_records == 0:
        raise AtcfError(f"no a-deck record in the text for {storm_id}")
    return Adeck(
        storm_id=storm_id, points=points, n_rows=n_rows, n_skipped=n_skipped,
        n_other_storm=n_other_storm, n_basin_mismatch=n_basin_mismatch, conflicts=conflicts,
    )


def parse_tcvitals(text: str) -> list[Fix]:
    """Parse TC-Vitals bulletin text into individual WORKING-quality fixes.

    Unlike b-deck/HURDAT2, a TC-Vitals file is normally one bulletin per
    synoptic cycle covering every active storm, not one storm's full
    history -- so this returns a flat ``list[Fix]``, not ``Track`` objects.
    Group by ``storm_id`` and sort by ``valid_time`` yourself if you need a
    ``Track`` (e.g. to feed :func:`pair_by_valid_time`).

    Off-synoptic records are dropped, matching the other two parsers.
    """
    fixes: list[Fix] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        tokens = line.split()
        if len(tokens) < 13:
            raise TcVitalsError(f"line {lineno}: too few fields: {raw_line!r}")

        storm_num_basin = tokens[1]
        date_s, time_s = tokens[3], tokens[4]
        lat_s, lon_s = tokens[5], tokens[6]
        mslp_s = tokens[9]
        wind_mps_s = tokens[12]

        if len(storm_num_basin) < 3:
            raise TcVitalsError(f"line {lineno}: malformed storm id: {storm_num_basin!r}")
        storm_num, basin_code = storm_num_basin[:-1], storm_num_basin[-1]
        basin = TCVITALS_BASIN_MAP.get(basin_code)
        if basin is None:
            raise TcVitalsError(
                f"line {lineno}: unrecognised TC-Vitals basin code {basin_code!r} "
                f"(known: {sorted(TCVITALS_BASIN_MAP)})"
            )

        if len(time_s) != 4 or not time_s.isdigit():
            raise TcVitalsError(f"line {lineno}: malformed time field: {time_s!r}")
        hour = int(time_s[:2])
        if hour not in SYNOPTIC_HOURS or time_s[2:] != "00":
            continue

        mslp = float(mslp_s)
        wind_mps = float(wind_mps_s)
        if mslp <= 0 or wind_mps < 0:
            continue  # NCEP uses implausible sentinels (e.g. 0/9999) for "unreported"

        valid_time = datetime.strptime(date_s + time_s, "%Y%m%d%H%M").replace(tzinfo=UTC)
        lat, lon = _parse_latlon(lat_s, lon_s)
        storm_id = f"{basin}{int(storm_num):02d}{valid_time.year}"

        fixes.append(
            Fix(
                storm_id=storm_id,
                valid_time=valid_time,
                lat=lat,
                lon=lon,
                max_wind_kt=round(wind_mps * MPS_TO_KT, 1),
                min_pressure_mb=mslp,
                quality=TrackQuality.WORKING,
            )
        )
    return fixes


def pair_by_valid_time(working: Track, final: Track) -> list[tuple[Fix, Fix]]:
    """Pair a WORKING track's fixes against a FINAL track's, by storm_id + valid_time.

    Feeds directly into ``besttrack.recalibrate_from_pairs`` -- this is the
    "real paired working/final data" PLAN.md §5's noise-emulator item and
    §4's working-track productionisation row are both waiting on.
    """
    if working.storm_id != final.storm_id:
        raise ValueError(
            f"storm_id mismatch: working={working.storm_id!r} final={final.storm_id!r}"
        )
    final_by_time = {f.valid_time: f for f in final.fixes}
    return [(w, final_by_time[w.valid_time]) for w in working.fixes if w.valid_time in final_by_time]
