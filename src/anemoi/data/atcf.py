"""ATCF b-deck and TC-Vitals parsers (working-quality best track).

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

Format references:

* b-deck: NRL ATCF ``abdeck.txt`` (comma-separated; basin/cyclone-number/
  date-time-group/tech/tau/lat/lon/vmax/mslp/.../stormname).
* TC-Vitals: NCEP "Format of Tropical Cyclone Records (TCVITALS)"
  (fixed-column, whitespace-separated in practice since no field embeds a
  space). The field *order* below is verified against that spec; exact
  column widths can vary slightly by NCEP archive vintage, so this parser
  tokenizes on whitespace rather than slicing fixed columns -- validate
  against a live sample before relying on it in production.
"""

from __future__ import annotations

from datetime import UTC, datetime

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
