"""Per-lead ensemble calibration core (metrics.ensemble_calibration, #10).

Synthetic ensembles with calibration known by construction: members and
truth drawn from the same distribution must read as calibrated; members
drawn too tightly must read as underdispersed. That's the property the real
Anemoi-Spread backtest relies on this module to measure correctly.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from anemoi.geo import offset_position
from anemoi.metrics.ensemble_calibration import (
    QUANTITIES,
    calibrate,
    forecast_motion_bearings,
    observed_motion_bearings,
    recurving_cases,
)

LEADS = (24, 48)
BASE = (20.0, -60.0)


def _centre(li: int) -> tuple[float, float]:
    # A real-looking NW-moving storm: ~1 deg per lead.
    return BASE[0] + 1.0 * (li + 1), BASE[1] - 1.0 * (li + 1)


def _jitter(lat, lon, rng, sigma_nm):
    east, north = rng.normal(0.0, sigma_nm, size=2)
    return offset_position(lat, lon, math.hypot(east, north), math.degrees(math.atan2(east, north)))


def _synthetic(n_cases=400, n_members=20, truth_sigma=60.0, member_sigma=60.0, seed=0):
    rng = np.random.default_rng(seed)
    n_leads = len(LEADS)
    members = np.zeros((n_cases, n_members, n_leads, 3))
    truth = np.zeros((n_cases, n_leads, 3))
    for ci in range(n_cases):
        for li in range(n_leads):
            clat, clon = _centre(li)
            truth[ci, li, :2] = _jitter(clat, clon, rng, truth_sigma)
            truth[ci, li, 2] = 80.0 + rng.normal(0.0, truth_sigma / 6)
            for mi in range(n_members):
                members[ci, mi, li, :2] = _jitter(clat, clon, rng, member_sigma)
                members[ci, mi, li, 2] = 80.0 + rng.normal(0.0, member_sigma / 6)
    mask = np.ones((n_cases, n_leads), dtype=bool)
    base = np.tile(np.array(BASE), (n_cases, 1))
    return members, truth, mask, base


def test_a_calibrated_ensemble_reads_as_calibrated():
    """Also the regression guard for a real flaw it caught: projecting onto
    the *observed* motion (a frame built from the verifying observation)
    read this calibrated-by-construction ensemble as cross-track
    overdispersed (ratio 1.28)."""
    members, truth, mask, base = _synthetic(truth_sigma=60.0, member_sigma=60.0)
    results = calibrate(members, truth, mask, base, LEADS)

    expected = {(lead, q) for lead in LEADS for q in QUANTITIES}
    assert {(r.lead_hours, r.quantity) for r in results} == expected
    for r in results:
        assert r.verdict == "calibrated", (r.lead_hours, r.quantity, r.ratio)
        # 20 members -> 21 rank bins; a flat histogram puts ~2/21 in the extremes.
        assert r.outer_rank_fraction < 0.2, (r.quantity, r.outer_rank_fraction)


def test_an_underdispersed_ensemble_reads_as_underdispersed():
    """The failure #10 exists to detect: members far tighter than the real
    uncertainty. Must show both signals -- a ratio well under 1 *and* the
    truth routinely landing outside every member (the U shape)."""
    members, truth, mask, base = _synthetic(truth_sigma=60.0, member_sigma=15.0)
    for r in calibrate(members, truth, mask, base, LEADS):
        assert r.verdict == "underdispersed", (r.lead_hours, r.quantity, r.ratio)
        assert r.ratio < 0.5
        assert r.outer_rank_fraction > 0.5


def test_leads_without_enough_verifying_cases_are_omitted_not_estimated():
    members, truth, mask, base = _synthetic(n_cases=30)
    mask[:, 1] = False
    mask[:5, 1] = True  # only 5 real verifying cases at 48h
    results = calibrate(members, truth, mask, base, LEADS, min_cases=10)
    assert {r.lead_hours for r in results} == {24}


def test_case_filter_stratifies():
    members, truth, mask, base = _synthetic(n_cases=40)
    only_first_half = np.zeros_like(mask)
    only_first_half[:20] = True
    results = calibrate(members, truth, mask, base, LEADS, case_filter=only_first_half)
    assert all(r.n_cases == 20 for r in results)


def test_observed_motion_bearing_uses_the_previous_real_position():
    truth = np.array([[[21.0, -60.0, 50.0], [21.0, -59.0, 50.0]]])  # due north, then due east
    bearings = observed_motion_bearings(truth, np.array([[20.0, -60.0]]))
    assert bearings[0, 0] == pytest.approx(0.0, abs=0.5)
    assert bearings[0, 1] == pytest.approx(90.0, abs=1.0)


def test_recurving_flags_a_westward_storm_that_turns_east():
    truth = np.array([
        [[21.0, -61.0, 50.0], [22.0, -60.0, 50.0]],  # recurves: NW then NE
        [[21.0, -61.0, 50.0], [22.0, -62.0, 50.0]],  # keeps heading NW
    ])
    base = np.array([[20.0, -60.0], [20.0, -60.0]])
    base_bearing = np.array([315.0, 315.0])  # both moving NW at forecast time
    flags = recurving_cases(truth, base, base_bearing)
    assert flags[0].tolist() == [False, True]
    assert flags[1].tolist() == [False, False]


def test_shape_validation():
    members, truth, mask, base = _synthetic(n_cases=12, n_members=3)
    with pytest.raises(ValueError, match="at least 2 members"):
        calibrate(members[:, :1], truth, mask, base, LEADS)
    with pytest.raises(ValueError, match="one entry per lead"):
        calibrate(members, truth, mask, base, (24,))
    with pytest.raises(ValueError, match="true_abs"):
        calibrate(members, truth[:, :1], mask, base, LEADS)


def test_forecast_motion_follows_the_ensemble_mean_track():
    # Two identical members moving due north then due east.
    track = np.array([[21.0, -60.0, 50.0], [21.0, -59.0, 50.0]])
    members = np.stack([track, track])[None]  # (1 case, 2 members, 2 leads, 3)
    bearings = forecast_motion_bearings(members, np.array([[20.0, -60.0]]))
    assert bearings[0, 0] == pytest.approx(0.0, abs=0.5)
    assert bearings[0, 1] == pytest.approx(90.0, abs=1.0)
