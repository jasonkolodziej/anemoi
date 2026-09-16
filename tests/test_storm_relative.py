"""Storm-relative coordinate transform for track-sequence model inputs (#9)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from anemoi.data.besttrack import Fix, TrackQuality
from anemoi.data.storm_relative import (
    STORM_RELATIVE_COLUMNS,
    displacement_nm,
    storm_relative_sequence,
)
from anemoi.geo import bearing_deg, haversine_nm

T = datetime(2026, 8, 6, 6, tzinfo=UTC)


def make_fix(hour_offset=0, **kw):
    params = dict(
        storm_id="AL092026",
        valid_time=T + timedelta(hours=hour_offset),
        lat=20.0,
        lon=-60.0,
        max_wind_kt=85.0,
        min_pressure_mb=968.0,
        quality=TrackQuality.FINAL,
    )
    params.update(kw)
    return Fix(**params)


def test_output_shape_is_one_row_shorter_than_the_input_window():
    fixes = tuple(
        make_fix(hour_offset=6 * i, lat=20.0 + 0.3 * i, lon=-60.0 - 0.4 * i) for i in range(5)
    )
    seq = storm_relative_sequence(fixes)
    assert seq.shape == (4, len(STORM_RELATIVE_COLUMNS))


def test_stationary_storm_has_zero_displacement():
    fixes = (make_fix(hour_offset=0), make_fix(hour_offset=6))
    seq = storm_relative_sequence(fixes)
    assert seq[0, 0] == pytest.approx(0.0, abs=1e-9)  # dx_east_nm
    assert seq[0, 1] == pytest.approx(0.0, abs=1e-9)  # dy_north_nm


def test_eastward_motion_is_positive_dx_with_a_small_northward_component():
    """A great-circle route between two points on the same latitude circle
    (other than the equator) bulges slightly poleward -- constant-latitude
    isn't a geodesic -- so dy isn't exactly zero, just small relative to dx."""
    prev = make_fix(hour_offset=0, lat=20.0, lon=-60.0)
    cur = make_fix(hour_offset=6, lat=20.0, lon=-59.0)  # due east, same latitude
    seq = storm_relative_sequence((prev, cur))
    assert seq[0, 0] > 0.0  # dx_east_nm
    assert abs(seq[0, 1]) < 0.01 * seq[0, 0]  # dy_north_nm: small relative to dx


def test_northward_motion_is_positive_dy_and_zero_dx():
    prev = make_fix(hour_offset=0, lat=20.0, lon=-60.0)
    cur = make_fix(hour_offset=6, lat=21.0, lon=-60.0)  # due north
    seq = storm_relative_sequence((prev, cur))
    assert seq[0, 0] == pytest.approx(0.0, abs=1e-6)  # dx_east_nm
    assert seq[0, 1] > 0.0  # dy_north_nm


def test_displacement_magnitude_matches_haversine_distance():
    prev = make_fix(hour_offset=0, lat=18.0, lon=-55.0)
    cur = make_fix(hour_offset=6, lat=19.4, lon=-56.7)
    seq = storm_relative_sequence((prev, cur))
    expected = haversine_nm(prev.lat, prev.lon, cur.lat, cur.lon)
    magnitude = float(np.hypot(seq[0, 0], seq[0, 1]))
    assert magnitude == pytest.approx(expected, rel=1e-6)


def test_displacement_direction_matches_bearing():
    prev = make_fix(hour_offset=0, lat=18.0, lon=-55.0)
    cur = make_fix(hour_offset=6, lat=19.4, lon=-56.7)
    seq = storm_relative_sequence((prev, cur))
    expected_brg = bearing_deg(prev.lat, prev.lon, cur.lat, cur.lon)
    got_brg = (np.degrees(np.arctan2(seq[0, 0], seq[0, 1])) + 360.0) % 360.0
    assert got_brg == pytest.approx(expected_brg, abs=1e-4)


def test_wind_pressure_and_latitude_are_the_current_fixs_absolute_values():
    prev = make_fix(hour_offset=0, max_wind_kt=70.0, min_pressure_mb=985.0, lat=18.0)
    cur = make_fix(hour_offset=6, max_wind_kt=80.0, min_pressure_mb=978.0, lat=18.6)
    seq = storm_relative_sequence((prev, cur))
    assert seq[0, 2] == pytest.approx(80.0)  # max_wind_kt
    assert seq[0, 3] == pytest.approx(978.0)  # min_pressure_mb
    assert seq[0, 4] == pytest.approx(18.6)  # latitude_deg


def test_single_fix_raises():
    with pytest.raises(ValueError, match="at least 2 fixes"):
        storm_relative_sequence((make_fix(),))


def test_mixed_storm_ids_raises():
    a = make_fix(hour_offset=0, storm_id="AL092026")
    b = make_fix(hour_offset=6, storm_id="AL102026")
    with pytest.raises(ValueError, match="multiple storms"):
        storm_relative_sequence((a, b))


def test_displacement_nm_matches_storm_relative_sequence():
    prev = make_fix(hour_offset=0, lat=18.0, lon=-55.0)
    cur = make_fix(hour_offset=6, lat=19.4, lon=-56.7)
    dx, dy = displacement_nm(prev, cur)
    seq = storm_relative_sequence((prev, cur))
    assert dx == pytest.approx(seq[0, 0])
    assert dy == pytest.approx(seq[0, 1])
