"""The array forms of the geodesy, verification and product maths agree with
the per-point formulas they replaced (#218).

Numba was evaluated for these loops and not adopted (Decision Log 55):
vectorised NumPy was as fast or faster, with no compile step on a cold
start and no new dependency. What that rewrite must not do is change a
number, so each array form is checked here against an independent
per-point reference written with `math`, the way the loops computed it --
including the edges a vectorised rewrite gets wrong (zero displacement,
the antimeridian, tied members, an RNG draw order).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np
import pytest

from anemoi.geo import (
    EARTH_RADIUS_KM,
    KM_PER_NM,
    bearings_deg,
    cross_along_track_nm,
    cross_along_track_nms,
    offset_positions,
)
from anemoi.inference.cycle import DeterministicForecast, climatological_ensemble
from anemoi.inference.postprocess import (
    CLIMATOLOGICAL_CONE_NM,
    CONE_PERCENTILE,
    LEAD_HOURS,
    EnsembleMember,
    cone_radius_from_spread,
    landfall_probability,
)
from anemoi.metrics.ensemble_calibration import (
    _scalar_errors,
    forecast_motion_bearings,
    observed_motion_bearings,
)
from anemoi.metrics.probabilistic import crps_ensemble, crps_series, rank_histogram
from anemoi.metrics.track import ForecastPoint, VerificationPair, verify
from anemoi.training.real_run import (
    displacement_to_latlon,
    displacements_to_absolute,
    displacements_to_latlon,
    verification_pairs,
)

TOL = 1e-9


# --- per-point references, in plain `math` -----------------------------------


def ref_haversine(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(max(a, 0.0), 1.0))) / KM_PER_NM


def ref_bearing(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def ref_offset(lat, lon, dist_nm, bearing):
    ang = dist_nm * KM_PER_NM / EARTH_RADIUS_KM
    p1, l1, th = math.radians(lat), math.radians(lon), math.radians(bearing)
    p2 = math.asin(math.sin(p1) * math.cos(ang) + math.cos(p1) * math.sin(ang) * math.cos(th))
    l2 = l1 + math.atan2(
        math.sin(th) * math.sin(ang) * math.cos(p1), math.cos(ang) - math.sin(p1) * math.sin(p2)
    )
    return math.degrees(p2), (math.degrees(l2) + 180.0) % 360.0 - 180.0


def ref_displacement(base_lat, base_lon, dx, dy):
    d = math.hypot(dx, dy)
    if d < 1e-9:
        return base_lat, base_lon
    return ref_offset(base_lat, base_lon, d, math.degrees(math.atan2(dx, dy)) % 360.0)


def ref_crps(x, y):
    x = np.asarray(x, dtype=float)
    return float(np.abs(x - y).mean() - 0.5 * np.abs(x[:, None] - x[None, :]).mean())


@pytest.fixture
def rng():
    return np.random.default_rng(218)


def _lon_close(a, b):
    """Longitudes equal modulo the wrap (-180 and 180 are one meridian)."""
    return np.allclose((np.asarray(a) - np.asarray(b) + 180.0) % 360.0 - 180.0, 0.0, atol=TOL)


# --- geo ------------------------------------------------------------------


def test_array_geodesy_matches_the_per_point_formulas(rng):
    lat1, lat2 = rng.uniform(-85, 85, 500), rng.uniform(-85, 85, 500)
    lon1, lon2 = rng.uniform(-180, 180, 500), rng.uniform(-180, 180, 500)
    dist, brg = rng.uniform(0, 3000, 500), rng.uniform(0, 360, 500)

    got = bearings_deg(lat1, lon1, lat2, lon2)
    want = [ref_bearing(*p) for p in zip(lat1, lon1, lat2, lon2, strict=True)]
    assert np.allclose(got, want, atol=TOL)

    lat, lon = offset_positions(lat1, lon1, dist, brg)
    want = np.array([ref_offset(*p) for p in zip(lat1, lon1, dist, brg, strict=True)])
    assert np.allclose(lat, want[:, 0], atol=TOL)
    assert _lon_close(lon, want[:, 1])

    motion = rng.uniform(0, 360, 500)
    cross, along = cross_along_track_nms(lat2, lon2, lat1, lon1, motion)
    for i in range(0, 500, 37):
        assert (cross[i], along[i]) == pytest.approx(
            cross_along_track_nm(lat2[i], lon2[i], lat1[i], lon1[i], motion[i]), abs=TOL
        )
        d = ref_haversine(lat1[i], lon1[i], lat2[i], lon2[i])
        delta = math.radians(ref_bearing(lat1[i], lon1[i], lat2[i], lon2[i]) - motion[i])
        assert cross[i] == pytest.approx(d * math.sin(delta), abs=1e-6)


def test_displacements_convert_like_the_scalar_inverse_including_the_edges(rng):
    base_lat = rng.uniform(5, 45, 300)
    base_lon = rng.uniform(-100, -10, 300)
    disp = rng.normal(0, 250, (300, 7, 2))
    disp[0, :] = 0.0  # a sample that hasn't moved at all
    base_lon[1] = 179.5  # crosses the antimeridian eastward
    disp[1, :, 0] = 120.0

    lat, lon = displacements_to_latlon(
        base_lat[:, None], base_lon[:, None], disp[..., 0], disp[..., 1]
    )
    assert lat.shape == lon.shape == (300, 7)
    for si in range(300):
        for li in range(7):
            want = ref_displacement(base_lat[si], base_lon[si], *disp[si, li])
            assert lat[si, li] == pytest.approx(want[0], abs=TOL)
            assert _lon_close(lon[si, li], want[1])
            assert (lat[si, li], lon[si, li]) == pytest.approx(
                displacement_to_latlon(base_lat[si], base_lon[si], *disp[si, li]), abs=TOL
            )
    # Zero displacement hands back the base itself, not a re-derived point.
    assert np.array_equal(lat[0], np.full(7, base_lat[0]))
    assert np.array_equal(lon[0], np.full(7, base_lon[0]))
    assert np.all((lon[1] >= -180.0) & (lon[1] < 180.0))


def test_displacements_to_absolute_keeps_wind_shape_and_dtype(rng):
    disp = rng.normal(0, 100, (4, 5, 3)).astype(np.float32)
    out = displacements_to_absolute(disp, np.full((4, 1), 25.0), np.full((4, 1), -70.0))
    assert out.shape == disp.shape
    assert np.array_equal(out[..., 2], disp[..., 2].astype(np.float64))
    # One base for a whole (members, leads) block, as the ensemble paths use.
    one = displacements_to_absolute(disp[0], 25.0, -70.0)
    assert np.allclose(one, out[0])


# --- verification -----------------------------------------------------------


def test_verification_pairs_are_the_loops_pairs_in_the_same_order(rng):
    n, leads = 40, (12, 24, 36, 48, 72, 96, 120)
    base_lat, base_lon = rng.uniform(10, 35, n), rng.uniform(-90, -30, n)
    pred = np.dstack(
        [rng.normal(0, 200, (n, 7)), rng.normal(0, 200, (n, 7)), rng.uniform(30, 140, (n, 7))]
    )
    obs = np.dstack(
        [rng.normal(0, 200, (n, 7)), rng.normal(0, 200, (n, 7)), rng.uniform(30, 140, (n, 7))]
    )
    mask = rng.random((n, 7)) > 0.3

    got = verification_pairs(base_lat, base_lon, pred, obs, mask, leads)
    want = []
    for si in range(n):
        for li, lead in enumerate(leads):
            if not mask[si, li]:
                continue
            plat, plon = ref_displacement(base_lat[si], base_lon[si], *pred[si, li, :2])
            olat, olon = ref_displacement(base_lat[si], base_lon[si], *obs[si, li, :2])
            want.append((lead, plat, plon, pred[si, li, 2], olat, olon, obs[si, li, 2]))
    assert len(got) == len(want) == int(mask.sum())
    for p, w in zip(got, want, strict=True):
        assert p.forecast.lead_hours == w[0]
        assert (p.forecast.lat, p.forecast.lon, p.forecast.max_wind_kt) == pytest.approx(
            w[1:4], abs=TOL
        )
        assert (p.obs_lat, p.obs_lon, p.obs_wind_kt) == pytest.approx(w[4:], abs=TOL)


def test_verify_matches_per_pair_errors_with_and_without_motion_bearings(rng):
    pairs = []
    for i in range(300):
        lead = (12, 48, 120)[i % 3]
        pairs.append(
            VerificationPair(
                forecast=ForecastPoint(
                    lead, *rng.uniform(15, 35, 1), *rng.uniform(-90, -40, 1), 80.0 + i % 7
                ),
                obs_lat=float(rng.uniform(15, 35)),
                obs_lon=float(rng.uniform(-90, -40)),
                obs_wind_kt=75.0,
                # Only some pairs carry a motion bearing: only those decompose.
                obs_motion_bearing=float(rng.uniform(0, 360)) if i % 4 else None,
            )
        )
    stats = verify(pairs)
    for lead, s in stats.items():
        group = [p for p in pairs if p.forecast.lead_hours == lead]
        track = np.array(
            [ref_haversine(p.obs_lat, p.obs_lon, p.forecast.lat, p.forecast.lon) for p in group]
        )
        assert s.n == len(group)
        assert s.track_mae_nm == pytest.approx(track.mean(), abs=1e-6)
        assert s.track_rmse_nm == pytest.approx(math.sqrt((track**2).mean()), abs=1e-6)
        dec = np.array([p.decomposed_nm() for p in group if p.obs_motion_bearing is not None])
        assert s.cross_track_bias_nm == pytest.approx(dec[:, 0].mean(), abs=1e-6)
        assert s.along_track_bias_nm == pytest.approx(dec[:, 1].mean(), abs=1e-6)

    no_motion = [VerificationPair(ForecastPoint(24, 20.0, -60.0, 50.0), 20.5, -60.5, 55.0)]
    only = verify(no_motion)[24]
    assert only.cross_track_bias_nm is None and only.along_track_bias_nm is None


# --- probabilistic -----------------------------------------------------------


def test_crps_matches_the_pairwise_kernel_form(rng):
    for m in (1, 2, 5, 50):
        x = rng.normal(0, 3, m)
        assert crps_ensemble(x, 0.7) == pytest.approx(ref_crps(x, 0.7), abs=1e-12)
    # Ties, the case a sorted-rank formula gets wrong if it miscounts.
    tied = np.array([1.0, 1.0, 1.0, 2.0, 2.0])
    assert crps_ensemble(tied, 1.5) == pytest.approx(ref_crps(tied, 1.5), abs=1e-12)

    members, obs = rng.normal(0, 1, (400, 50)), rng.normal(0, 1, 400)
    want = np.mean([ref_crps(r, o) for r, o in zip(members, obs, strict=True)])
    assert crps_series(members, obs) == pytest.approx(want, abs=1e-12)
    with pytest.raises(ValueError, match="empty ensemble"):
        crps_series(np.empty((3, 0)), np.zeros(3))
    with pytest.raises(ValueError, match="empty ensemble"):
        crps_ensemble([], 1.0)


def test_rank_histogram_counts_like_the_loop_including_ties(rng):
    members = np.round(rng.normal(0, 1, (500, 20)), 1)  # rounding makes ties common
    obs = np.round(rng.normal(0, 1, 500), 1)
    want = np.zeros(21, dtype=int)
    for row, o in zip(members, obs, strict=True):
        want[int(np.sum(np.sort(row) < o))] += 1
    got = rank_histogram(members, obs)
    assert np.array_equal(got, want)
    assert got.sum() == 500
    with pytest.raises(ValueError, match="case count mismatch"):
        rank_histogram(members, obs[:-1])


# --- ensemble calibration ----------------------------------------------------


def test_motion_bearings_and_member_errors_match_the_loops(rng):
    n, m, leads = 30, 12, 7
    base = np.column_stack([rng.uniform(10, 30, n), rng.uniform(-80, -30, n)])
    true_abs = np.dstack(
        [
            rng.uniform(10, 40, (n, leads)),
            rng.uniform(-85, -25, (n, leads)),
            rng.uniform(30, 120, (n, leads)),
        ]
    )
    members_abs = np.stack(
        [
            np.dstack(
                [
                    rng.uniform(10, 40, (n, leads)),
                    rng.uniform(-85, -25, (n, leads)),
                    rng.uniform(30, 120, (n, leads)),
                ]
            )
            for _ in range(m)
        ],
        axis=1,
    )

    observed = observed_motion_bearings(true_abs, base)
    forecast = forecast_motion_bearings(members_abs, base)
    mean_track = members_abs[..., :2].mean(axis=1)
    for ci in range(n):
        prev = base[ci]
        prev_mean = base[ci]
        for li in range(leads):
            assert observed[ci, li] == pytest.approx(
                ref_bearing(*prev, *true_abs[ci, li, :2]), abs=TOL
            )
            assert forecast[ci, li] == pytest.approx(
                ref_bearing(*prev_mean, *mean_track[ci, li]), abs=TOL
            )
            prev, prev_mean = true_abs[ci, li, :2], mean_track[ci, li]

    errors = _scalar_errors(members_abs, true_abs, forecast, 3, 4)
    for mi in range(m):
        want = cross_along_track_nm(*members_abs[3, mi, 4, :2], *true_abs[3, 4, :2], forecast[3, 4])
        assert (errors["cross_track_nm"][0][mi], errors["along_track_nm"][0][mi]) == pytest.approx(
            want, abs=TOL
        )


# --- products -----------------------------------------------------------------


def _members(rng, n=50):
    k = len(LEAD_HOURS)
    return [
        EnsembleMember(
            i, LEAD_HOURS, rng.uniform(22, 30, k), rng.uniform(-92, -80, k), rng.uniform(40, 130, k)
        )
        for i in range(n)
    ]


def test_cone_and_landfall_match_the_per_member_loops(rng):
    members = _members(rng)
    for lead in LEAD_HOURS:
        lats = np.array([m.at(lead)[0] for m in members])
        lons = np.array([m.at(lead)[1] for m in members])
        dists = [
            ref_haversine(lats.mean(), lons.mean(), a, b) for a, b in zip(lats, lons, strict=True)
        ]
        assert cone_radius_from_spread(members, lead) == pytest.approx(
            np.percentile(dists, CONE_PERCENTILE), abs=1e-6
        )
        assert cone_radius_from_spread(members, lead, 90.0) == pytest.approx(
            np.percentile(dists, 90.0), abs=1e-6
        )

    coast = (29.3, -94.8)
    for threshold in (60.0, 200.0, 400.0):
        hits = sum(
            min(ref_haversine(*coast, *m.at(lead)[:2]) for lead in LEAD_HOURS) <= threshold
            for m in members
        )
        assert landfall_probability(members, *coast, threshold_nm=threshold) == hits / len(members)
    one_lead = sum(ref_haversine(*coast, *m.at(48)[:2]) <= 200.0 for m in members) / len(members)
    assert landfall_probability(members, *coast, threshold_nm=200.0, lead=48) == one_lead


def test_the_climatological_ensemble_is_unchanged_for_a_seed():
    """Same draws in the same order, so a seed still gives the members it
    always gave -- the fallback cycle stays reproducible."""
    leads = LEAD_HOURS
    det = DeterministicForecast(
        target_time=datetime(2026, 10, 15, 12, tzinfo=UTC),
        lead_hours=leads,
        lats=np.linspace(24.0, 31.0, len(leads)),
        lons=np.linspace(-80.0, -92.0, len(leads)),
        winds_kt=np.linspace(70.0, 110.0, len(leads)),
    )
    got = climatological_ensemble(det, n_members=8, seed=5)

    rng = np.random.default_rng(5)
    for member in got:
        for k, lead in enumerate(leads):
            sigma = CLIMATOLOGICAL_CONE_NM.get(lead, 60.0) / np.sqrt(-2.0 * np.log(1.0 - 0.67))
            dist = float(abs(rng.normal(0.0, sigma)))
            bearing = float(rng.uniform(0.0, 360.0))
            wind = float(det.winds_kt[k] + rng.normal(0.0, 8.0))
            lat, lon = ref_offset(float(det.lats[k]), float(det.lons[k]), dist, bearing)
            assert member.lats[k] == pytest.approx(lat, abs=TOL)
            assert member.lons[k] == pytest.approx(lon, abs=TOL)
            assert member.winds_kt[k] == pytest.approx(max(wind, 0.0), abs=TOL)


def test_haversine_broadcasts_a_single_point_against_many():
    """It returned a float when the *first* point was a scalar -- and so
    raised for one point against an array of others (#218)."""
    from anemoi.geo import haversine_nm

    lats, lons = np.array([25.0, 26.0, 27.0]), np.array([-80.0, -81.0, -82.0])
    got = haversine_nm(25.0, -80.0, lats, lons)
    assert isinstance(got, np.ndarray) and got.shape == (3,)
    assert got == pytest.approx([ref_haversine(25.0, -80.0, a, b) for a, b in zip(lats, lons, strict=True)])
    assert isinstance(haversine_nm(25.0, -80.0, 26.0, -81.0), float)
    assert isinstance(haversine_nm(np.float64(25.0), -80.0, 26.0, -81.0), float)
