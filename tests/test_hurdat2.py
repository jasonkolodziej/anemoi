"""HURDAT2 parser (PLAN.md §4 productionization: storm archive).

The fixture text below is format-compliant HURDAT2 (matching the public NHC
spec) but is a constructed storm, not a transcription of a real archive
entry -- what's under test is the parser, not any specific storm's history.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from anemoi.data.besttrack import TrackQuality
from anemoi.data.hurdat2 import Hurdat2Error, parse_hurdat2, parse_hurdat2_file

RADII = ", ".join(["-999"] * 12)

# Storm 1: four clean synoptic entries.
STORM_ONE = f"""\
AL011999,           ONE,     4,
19990825, 0000,  , TS, 12.0N,  35.0W,  40, 1005, {RADII},
19990825, 0600,  , TS, 12.5N,  36.0W,  45, 1002, {RADII},
19990825, 1200,  , TS, 13.0N,  37.0W,  50,  995, {RADII},
19990825, 1800,  , HU, 13.6N,  38.2W,  65,  985, {RADII},
"""

# Storm 2: an off-synoptic landfall entry (0300, record id L) and a
# missing-pressure entry (1200) should both be dropped, leaving 4 of 6.
STORM_TWO = f"""\
AL022005,     TESTSTORM,     6,
20050901, 0000,  , TD, 20.0N,  60.0W,  30, 1008, {RADII},
20050901, 0300, L, TD, 20.2N,  60.3W,  30, 1007, {RADII},
20050901, 0600,  , TS, 20.5N,  60.8W,  35, 1005, {RADII},
20050901, 1200,  , TS, 21.2N,  61.5W,  40, -999, {RADII},
20050901, 1800,  , TS, 21.8N,  62.0W,  45,  998, {RADII},
20050902, 0000,  , TS, 22.4N,  62.6W,  50,  995, {RADII},
"""


def test_parses_synoptic_entries_into_final_quality_track():
    tracks = parse_hurdat2(STORM_ONE)
    assert len(tracks) == 1
    track = tracks[0]
    assert track.storm_id == "AL011999"
    assert track.quality is TrackQuality.FINAL
    assert len(track.fixes) == 4

    first = track.fixes[0]
    assert first.valid_time == datetime(1999, 8, 25, 0, tzinfo=UTC)
    assert first.lat == pytest.approx(12.0)
    assert first.lon == pytest.approx(-35.0)
    assert first.max_wind_kt == pytest.approx(40.0)
    assert first.min_pressure_mb == pytest.approx(1005.0)


def test_southern_and_eastern_hemispheres_are_negated():
    text = f"""\
SH012020,         TESTSH,     1,
20200101, 0000,  , TS, 15.0S,  80.0E,  40, 1000, {RADII},
"""
    (track,) = parse_hurdat2(text)
    assert track.fixes[0].lat == pytest.approx(-15.0)
    assert track.fixes[0].lon == pytest.approx(80.0)


def test_off_synoptic_and_missing_pressure_entries_are_dropped():
    tracks = parse_hurdat2(STORM_TWO)
    assert len(tracks) == 1
    track = tracks[0]
    assert len(track.fixes) == 4
    hours = [f.valid_time.hour for f in track.fixes]
    assert hours == [0, 6, 18, 0]  # 0300 (off-synoptic) and 1200 (missing pressure) dropped


def test_multi_storm_file_produces_one_track_per_storm():
    tracks = parse_hurdat2(STORM_ONE + STORM_TWO)
    assert {t.storm_id for t in tracks} == {"AL011999", "AL022005"}


def test_storm_with_no_representable_fixes_is_skipped_entirely():
    text = f"""\
AL031999,      ALLMISSING,     1,
19990825, 0300, L, TD, 12.0N,  35.0W,  30, -999, {RADII},
"""
    assert parse_hurdat2(text) == []


def test_entry_count_mismatch_raises():
    text = f"""\
AL041999,         SHORT,     4,
19990825, 0000,  , TS, 12.0N,  35.0W,  40, 1005, {RADII},
"""
    with pytest.raises(Hurdat2Error, match="declares 4 entries"):
        parse_hurdat2(text)


def test_malformed_header_raises():
    with pytest.raises(Hurdat2Error, match="malformed header"):
        parse_hurdat2("not,a\n")


def test_non_numeric_entry_count_raises():
    with pytest.raises(Hurdat2Error, match="malformed entry count"):
        parse_hurdat2("AL011999,ONE,many,\n")


def test_malformed_latitude_raises():
    text = f"""\
AL051999,          BAD,     1,
19990825, 0000,  , TS, 12.0X,  35.0W,  40, 1005, {RADII},
"""
    with pytest.raises(Hurdat2Error, match="malformed latitude"):
        parse_hurdat2(text)


def test_parse_hurdat2_file_reads_from_disk(tmp_path):
    path = tmp_path / "hurdat2.txt"
    path.write_text(STORM_ONE)
    tracks = parse_hurdat2_file(path)
    assert len(tracks) == 1
    assert tracks[0].storm_id == "AL011999"


def test_west_longitude_past_180_wraps_into_range():
    """Real HURDAT2 entries: an extratropical remnant tracked across the prime
    meridian (into the Norwegian Sea) is recorded as e.g. ``354.5W`` -- degrees
    west counted past 180 rather than switching to "E" -- which is
    ``354.5 - 360 = -5.5``, i.e. ~5.5 degrees *east*. Found parsing the real
    1851-2023 Atlantic archive (AL grep '354.5W'); a constructed fixture below
    reproduces the same field format without transcribing the real storm."""
    text = f"""\
AL011969,          TEST,     1,
19690827, 1200,  , EX, 64.5N, 354.5W,  35,  997, {RADII},
"""
    tracks = parse_hurdat2(text)
    assert len(tracks) == 1
    fix = tracks[0].fixes[0]
    assert fix.lon == pytest.approx(5.5)
    assert -180.0 <= fix.lon < 180.0
