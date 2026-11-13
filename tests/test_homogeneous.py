"""Homogeneous comparison of several forecasts (`metrics.homogeneous`).

Hand-built arrays: two Atlantic storms with eight cases each and one East
Pacific storm, one lead or two, forecasts a fixed distance off the truth so
every mean is known in advance.
"""

from __future__ import annotations

import numpy as np
import pytest

from anemoi.metrics.basin import per_basin_scores
from anemoi.metrics.homogeneous import (
    INTENSITY,
    MIN_STORMS,
    TRACK,
    Member,
    homogeneous_mask,
    score_homogeneous,
    storm_block_interval,
)

#: One degree of latitude, in nm, on the sphere `geo.haversine_nm` uses.
NM_PER_DEG = 6371.0088 / 1.852 * np.pi / 180.0

STORMS = ["AL011999"] * 8 + ["AL021999"] * 8 + ["EP011999"] * 4
LEADS = (12, 24)


def _truth() -> np.ndarray:
    n = len(STORMS)
    obs = np.zeros((n, len(LEADS), 3))
    obs[..., 0] = 20.0
    obs[..., 1] = -60.0
    obs[..., 2] = 50.0
    return obs


def _offset(lat_deg: float, wind_kt: float, *, track: bool = True, wind: bool = True):
    pred = _truth()
    pred[..., 0] += lat_deg
    pred[..., 2] += wind_kt
    if not track:
        pred[..., :2] = np.nan
    if not wind:
        pred[..., 2] = np.nan
    return pred


def _row(rows, basin, lead, quantity, sample=""):
    (row,) = [
        r for r in rows
        if (r.sample, r.basin, r.lead_hours, r.quantity) == (sample, basin, lead, quantity)
    ]
    return row


def test_the_sample_is_the_intersection_and_one_missing_case_removes_it_for_all():
    a = _offset(0.1, 2.0)
    b = _offset(0.2, -4.0)
    b[3, 0, :2] = np.nan  # b has no position for case 3 at 12 h, only a wind
    members = [Member("A", "x", a), Member("B", "x", b)]
    eligible = np.ones((len(STORMS), len(LEADS)), dtype=bool)
    rows = score_homogeneous(members, _truth(), eligible, STORMS, LEADS)
    track12 = _row(rows, "AL", 12, TRACK)
    assert track12.n_cases == 15 and track12.n_eligible == 16
    assert track12.limited_by == "B"
    assert track12.scores["A"].n_available == 16
    assert track12.scores["B"].n_available == 15
    assert track12.scores["A"].mean_error == pytest.approx(0.1 * NM_PER_DEG, rel=1e-6)
    # Lead 24 and the intensity sample are untouched by b's missing position.
    assert _row(rows, "AL", 24, TRACK).n_cases == 16
    assert _row(rows, "AL", 12, INTENSITY).n_cases == 16
    assert _row(rows, "AL", 12, INTENSITY).scores["B"].bias == pytest.approx(-4.0)
    mask = homogeneous_mask(members, eligible, STORMS, TRACK)
    assert not mask[3, 0] and mask[3, 1] and mask.sum() == 2 * len(STORMS) - 1


def test_a_track_only_member_does_not_shrink_the_intensity_sample():
    full = _offset(0.1, 3.0)
    full[0, :, 2] = np.nan  # one case without a wind
    track_only = _offset(0.3, 0.0, wind=False)
    members = [Member("FULL", "x", full), Member("CLP5", "baseline", track_only)]
    eligible = np.ones((len(STORMS), len(LEADS)), dtype=bool)
    rows = score_homogeneous(members, _truth(), eligible, STORMS, LEADS)
    intensity = _row(rows, "AL", 12, INTENSITY)
    assert set(intensity.scores) == {"FULL"}
    assert intensity.n_cases == 15
    assert intensity.absent == ()  # not absent: it never forecasts a wind
    assert set(_row(rows, "AL", 12, TRACK).scores) == {"FULL", "CLP5"}


def test_a_member_absent_from_one_basin_is_named_and_does_not_empty_it():
    atlantic_only = _offset(0.2, 1.0)
    atlantic_only[16:] = np.nan
    members = [Member("A", "x", _offset(0.1, 1.0)), Member("AL_ONLY", "x", atlantic_only)]
    eligible = np.ones((len(STORMS), len(LEADS)), dtype=bool)
    rows = score_homogeneous(members, _truth(), eligible, STORMS, LEADS)
    east = _row(rows, "EP", 12, TRACK)
    assert east.n_cases == 4 and east.absent == ("AL_ONLY",)
    assert set(east.scores) == {"A"}
    assert _row(rows, "AL", 12, TRACK).absent == ()
    assert {r.basin for r in rows} == {"AL", "EP"}  # basins are never pooled


def test_with_every_member_present_the_errors_are_the_registrys_per_basin_scores():
    rng = np.random.default_rng(3)
    obs = _truth() + rng.normal(0.0, 0.5, size=_truth().shape)
    pred = obs + rng.normal(0.0, 1.0, size=obs.shape)
    eligible = rng.random((len(STORMS), len(LEADS))) > 0.2
    rows = score_homogeneous([Member("M", "model", pred)], obs, eligible, STORMS, LEADS)
    expected = per_basin_scores(pred, obs, eligible, STORMS, LEADS)
    for basin in ("AL", "EP"):
        for lead in LEADS:
            assert _row(rows, basin, lead, TRACK).scores["M"].mean_error == pytest.approx(
                expected[f"{basin}/track_error_{lead}h_nm"]
            )
            assert _row(rows, basin, lead, INTENSITY).scores["M"].mean_error == pytest.approx(
                expected[f"{basin}/intensity_error_{lead}h_kt"]
            )


def _many_storms(n_storms: int) -> list[str]:
    return [f"AL{s:02d}1999" for s in range(1, n_storms + 1) for _ in range(3)]


def test_skill_beat_rate_and_paired_difference_by_hand():
    storms = _many_storms(MIN_STORMS)
    n = len(storms)
    obs = np.zeros((n, 1, 3))
    obs[..., 0], obs[..., 1], obs[..., 2] = 20.0, -60.0, 50.0
    cand = obs.copy()
    base = obs.copy()
    cand[:, 0, 0] += 0.5
    base[:, 0, 0] += 1.0
    cand[0, 0, 0] = obs[0, 0, 0] + 2.0  # one case where the candidate loses
    members = [Member("CAND", "x", cand), Member("OCD5", "baseline", base)]
    rows = score_homogeneous(
        members, obs, np.ones((n, 1), dtype=bool), storms, (48,),
        references=("OCD5",), skill_baseline="OCD5", sample="B",
    )
    row = _row(rows, "AL", 48, TRACK, sample="B")
    assert not row.too_few_storms and row.n_storms == MIN_STORMS
    cand_mean = (0.5 * (n - 1) + 2.0) / n * NM_PER_DEG
    assert row.scores["CAND"].mean_error == pytest.approx(cand_mean, rel=1e-6)
    assert row.scores["CAND"].skill_pct == pytest.approx(
        100.0 * (1.0 - cand_mean / NM_PER_DEG), rel=1e-6,
    )
    assert row.scores["OCD5"].skill_pct == pytest.approx(0.0)
    paired = row.paired["CAND"]["OCD5"]
    assert paired.beat_rate == pytest.approx((n - 1) / n)
    assert paired.mean_diff == pytest.approx(cand_mean - NM_PER_DEG, rel=1e-6)
    low, high = paired.ci95
    assert low <= paired.mean_diff <= high
    assert paired.dm_p_value is not None
    assert paired.pairwise_n_cases == n and paired.pairwise_n_storms == MIN_STORMS
    # storm-weighted: the first storm's mean carries the outlier
    first = (2.0 + 0.5 + 0.5) / 3 * NM_PER_DEG
    rest = 0.5 * NM_PER_DEG
    assert row.scores["CAND"].storm_mean_error == pytest.approx(
        (first + rest * (MIN_STORMS - 1)) / MIN_STORMS, rel=1e-6,
    )
    assert row.largest_storm_share == pytest.approx(1 / MIN_STORMS)


def test_below_the_storm_floor_a_row_keeps_its_means_and_infers_nothing():
    storms = _many_storms(MIN_STORMS - 1)
    n = len(storms)
    obs = np.zeros((n, 1, 3))
    obs[..., 0], obs[..., 1], obs[..., 2] = 20.0, -60.0, 50.0
    members = [Member("CAND", "x", obs + 0.1), Member("OCD5", "baseline", obs + 0.2)]
    rows = score_homogeneous(
        members, obs, np.ones((n, 1), dtype=bool), storms, (48,),
        references=("OCD5",), skill_baseline="OCD5",
    )
    row = _row(rows, "AL", 48, TRACK)
    assert row.too_few_storms
    assert row.scores["CAND"].mean_error > 0 and row.scores["CAND"].skill_pct is None
    paired = row.paired["CAND"]["OCD5"]
    assert paired.mean_diff < 0
    assert paired.ci95 is None and paired.beat_rate is None and paired.dm_p_value is None


def test_score_homogeneous_rejects_duplicate_names_and_misshapen_forecasts():
    eligible = np.ones((len(STORMS), len(LEADS)), dtype=bool)
    with pytest.raises(ValueError):
        score_homogeneous(
            [Member("A", "x", _truth()), Member("A", "y", _truth())],
            _truth(), eligible, STORMS, LEADS,
        )
    with pytest.raises(ValueError):
        score_homogeneous([Member("A", "x", _truth()[:, :1])], _truth(), eligible, STORMS, LEADS)


def test_storm_block_interval_resamples_whole_storms():
    ids = np.array(["A"] * 5 + ["B"] * 5)
    assert storm_block_interval(ids, np.full(10, 3.0)) == pytest.approx((3.0, 3.0))
    # Two storms with means 0 and 10: every resample's mean is 0, 5 or 10.
    diffs = np.array([0.0] * 5 + [10.0] * 5)
    low, high = storm_block_interval(ids, diffs)
    assert low == 0.0 and high == 10.0
    with pytest.raises(ValueError):
        storm_block_interval(ids, np.zeros(3))
