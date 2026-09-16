"""ATCF b-deck and TC-Vitals parsers (PLAN.md §4 productionization: working track).

Fixture lines are format-compliant (per the NRL ATCF and NCEP TC-Vitals
specs) but describe a constructed storm, not a transcription of a real
archive -- what's under test is the parser and the recalibration pipeline,
not any specific storm's history. The working-side fixtures deliberately
perturb the final-track values from ``test_hurdat2.py``'s ``STORM_ONE`` so
``pair_by_valid_time`` + ``recalibrate_from_pairs`` has real, nonzero error
to measure.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from anemoi.data.atcf import (
    AtcfError,
    TcVitalsError,
    pair_by_valid_time,
    parse_bdeck,
    parse_tcvitals,
)
from anemoi.data.besttrack import Fix, Track, TrackQuality, recalibrate_from_pairs
from anemoi.data.hurdat2 import parse_hurdat2

# Perturbed versions of test_hurdat2.STORM_ONE's four fixes.
BDECK_ONE = """\
AL, 01, 1999082500,   , BEST,   0, 121N,  351W,  35, 1008, TS,   0,    ,    0,    0,    0,    0, 1008,  180,   0,   0,    ,   0,    ,   0,   0, ONE,   M,    ,   0,    ,    0,    0,    0,    0,
AL, 01, 1999082506,   , BEST,   0, 126N,  362W,  45, 1000, TS,   0,    ,    0,    0,    0,    0, 1008,  180,   0,   0,    ,   0,    ,   0,   0, ONE,   M,    ,   0,    ,    0,    0,    0,    0,
AL, 01, 1999082512,   , BEST,   0, 132N,  371W,  55,  992, TS,   0,    ,    0,    0,    0,    0, 1008,  180,   0,   0,    ,   0,    ,   0,   0, ONE,   M,    ,   0,    ,    0,    0,    0,    0,
AL, 01, 1999082518,   , BEST,   0, 135N,  380W,  60,  988, HU,   0,    ,    0,    0,    0,    0, 1008,  180,   0,   0,    ,   0,    ,   0,   0, ONE,   M,    ,   0,    ,    0,    0,    0,    0,
AL, 01, 1999082509,   , OFCL,   6, 140N,  390W,  60,  985, HU,   0,    ,    0,    0,    0,    0, 1008,  180,   0,   0,    ,   0,    ,   0,   0, ONE,   M,    ,   0,    ,    0,    0,    0,    0,
AL, 01, 1999082521,   , BEST,   0, 137N,  385W,  60, 9999, HU,   0,    ,    0,    0,    0,    0, 1008,  180,   0,   0,    ,   0,    ,   0,   0, ONE,   M,    ,   0,    ,    0,    0,    0,    0,
AL, 01, 1999082503,   , BEST,   0, 123N,  355W,  40, 1003, TS,   0,    ,    0,    0,    0,    0, 1008,  180,   0,   0,    ,   0,    ,   0,   0, ONE,   M,    ,   0,    ,    0,    0,    0,    0,
"""

RADII = ", ".join(["-999"] * 12)
HURDAT2_ONE = f"""\
AL011999,           ONE,     4,
19990825, 0000,  , TS, 12.0N,  35.0W,  40, 1005, {RADII},
19990825, 0600,  , TS, 12.5N,  36.0W,  45, 1002, {RADII},
19990825, 1200,  , TS, 13.0N,  37.0W,  50,  995, {RADII},
19990825, 1800,  , HU, 13.6N,  38.2W,  65,  985, {RADII},
"""

TCVITALS_ONE = (
    "NHC 01L ONE       19990825 0000 121N 0351W 270 046 1008 1012 0300 18 050\n"
    "NHC 01L ONE       19990825 0300 122N 0353W 270 046 1007 1012 0300 18 050\n"  # off-synoptic
)


def test_bdeck_parses_best_track_rows_only():
    tracks = parse_bdeck(BDECK_ONE)
    assert len(tracks) == 1
    track = tracks[0]
    assert track.storm_id == "AL011999"
    assert track.quality is TrackQuality.WORKING
    # OFCL row, the missing-MSLP (9999) row, and the off-synoptic (03Z) BEST
    # row are all excluded, leaving the 4 clean synoptic BEST rows.
    assert len(track.fixes) == 4
    assert track.fixes[0].valid_time == datetime(1999, 8, 25, 0, tzinfo=UTC)
    assert track.fixes[0].lat == pytest.approx(12.1)
    assert track.fixes[0].lon == pytest.approx(-35.1)
    assert track.fixes[0].max_wind_kt == pytest.approx(35.0)
    assert track.fixes[0].min_pressure_mb == pytest.approx(1008.0)


def test_bdeck_malformed_line_raises():
    with pytest.raises(AtcfError, match="malformed b-deck record"):
        parse_bdeck("not enough fields\n")


def test_tcvitals_parses_synoptic_rows_and_converts_wind_to_knots():
    fixes = parse_tcvitals(TCVITALS_ONE)
    assert len(fixes) == 1  # off-synoptic and unknown-basin rows dropped
    fix = fixes[0]
    assert fix.storm_id == "AL011999"
    assert fix.quality is TrackQuality.WORKING
    assert fix.lat == pytest.approx(12.1)
    assert fix.lon == pytest.approx(-35.1)
    assert fix.max_wind_kt == pytest.approx(round(18 * 1.943844, 1))
    assert fix.min_pressure_mb == pytest.approx(1008.0)


def test_tcvitals_unknown_basin_raises_rather_than_silently_dropping_a_storm():
    """Silently dropping a storm from a warning-system pipeline is worse than
    failing loudly on a basin code this parser doesn't yet map."""
    with pytest.raises(TcVitalsError, match="unrecognised TC-Vitals basin code 'Z'"):
        parse_tcvitals("NHC 99Z BAD 19990825 0600 121N 0351W 270 046 1008 1012 0300 18 050\n")


def test_tcvitals_too_few_fields_raises():
    with pytest.raises(TcVitalsError, match="too few fields"):
        parse_tcvitals("NHC 01L ONE\n")


def test_pair_by_valid_time_matches_shared_timestamps():
    (working,) = parse_bdeck(BDECK_ONE)
    (final,) = parse_hurdat2(HURDAT2_ONE)
    pairs = pair_by_valid_time(working, final)
    assert len(pairs) == 4
    for w, f in pairs:
        assert w.valid_time == f.valid_time
        assert w.quality is TrackQuality.WORKING
        assert f.quality is TrackQuality.FINAL


def test_pair_by_valid_time_rejects_mismatched_storms():
    (working,) = parse_bdeck(BDECK_ONE)
    other_final = Track(
        storm_id="AL022005",
        fixes=(
            Fix(
                storm_id="AL022005",
                valid_time=datetime(1999, 8, 25, 0, tzinfo=UTC),
                lat=20.0,
                lon=-60.0,
                max_wind_kt=30.0,
                min_pressure_mb=1008.0,
                quality=TrackQuality.FINAL,
            ),
        ),
    )
    with pytest.raises(ValueError, match="storm_id mismatch"):
        pair_by_valid_time(working, other_final)


def test_recalibration_from_real_parsed_pairs_measures_nonzero_error():
    """End-to-end: b-deck (working) + HURDAT2 (final) -> recalibrate_from_pairs.

    This is the real-data completion PLAN.md §5's noise-emulator item and
    §4's working-track row both describe -- previously only possible with
    synthetic pairs or the from_literature() literature estimate.
    """
    (working,) = parse_bdeck(BDECK_ONE)
    (final,) = parse_hurdat2(HURDAT2_ONE)
    pairs = pair_by_valid_time(working, final)

    noise = recalibrate_from_pairs(pairs)
    assert 0.0 < noise.position_rms_nm < 30.0
    assert 0.0 < noise.intensity_rms_kt < 20.0
    assert 0.0 < noise.pressure_rms_mb < 20.0
