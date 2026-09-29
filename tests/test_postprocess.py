"""Cone, intensity PDF, landfall and RI products (Scope v2.1 §6.1)."""

import numpy as np
import pytest

from anemoi.inference.postprocess import (
    EnsembleMember,
    build_cone,
    build_products,
    intensity_pdf,
    landfall_probability,
    rapid_intensification_probability,
)

LEADS = (12, 24, 48, 72, 120)


def members(n=20, spread=1.2, wind_gain=0.0, seed=0):
    """Ensemble whose spread grows with lead time, as a real one does."""
    rng = np.random.default_rng(seed)
    steps = np.arange(len(LEADS), dtype=float)
    growth = 1.0 + steps
    out = []
    for i in range(n):
        out.append(
            EnsembleMember(
                member_id=i,
                lead_hours=LEADS,
                lats=25.0 + steps + rng.normal(0, spread, len(LEADS)) * growth,
                lons=-70.0 - steps + rng.normal(0, spread, len(LEADS)) * growth,
                winds_kt=80.0 + wind_gain * steps + rng.normal(0, 3, len(LEADS)),
            )
        )
    return out


def test_cone_has_one_segment_per_lead_time():
    cone, _ = build_cone(members())
    assert len(cone) == len(LEADS)
    assert [c.lead_hours for c in cone] == list(LEADS)


def test_cone_radius_grows_with_lead_time():
    cone, _ = build_cone(members())
    radii = [c.radius_nm for c in cone]
    assert radii[-1] > radii[0]


def test_small_ensemble_falls_back_to_climatological_radii():
    cone, notes = build_cone(members(n=5))
    assert all(c.basis == "climatology" for c in cone)
    assert any("minimum" in n for n in notes)


def test_empty_ensemble_is_refused():
    with pytest.raises(ValueError, match="empty ensemble"):
        build_cone([])


def test_intensity_pdf_percentiles_are_ordered():
    pdf = intensity_pdf(members())
    for lead, percentiles in pdf.items():
        values = [percentiles[q] for q in sorted(percentiles)]
        assert values == sorted(values)


def test_cone_is_ensemble_based_when_spread_is_credible():
    cone, notes = build_cone(members())
    assert all(c.basis == "ensemble" for c in cone)
    assert not notes


def test_underdispersed_ensemble_falls_back_to_climatology():
    """The characteristic diffusion failure: spread far tighter than climatology."""
    cone, notes = build_cone(members(spread=0.05))
    assert all(c.basis == "climatology" for c in cone)
    assert any("climatology" in n for n in notes)


def test_landfall_probability_is_one_when_all_members_hit():
    prob = landfall_probability(members(spread=0.05), 26.0, -71.0, threshold_nm=200.0)
    assert prob == 1.0


def test_landfall_probability_is_zero_for_a_distant_point():
    assert landfall_probability(members(), 5.0, -140.0, threshold_nm=50.0) == 0.0


def test_rapid_intensification_is_detected_when_winds_surge():
    prob = rapid_intensification_probability(members(wind_gain=20.0, spread=0.05))
    assert prob > 0.8


def test_no_rapid_intensification_for_a_steady_storm():
    assert rapid_intensification_probability(members(wind_gain=0.0)) < 0.2


def test_wilson_interval_brackets_the_estimate_and_stays_in_the_unit_range():
    """#188: the normal approximation is worst exactly where this is used --
    small n, proportions near 0 or 1 -- where it returns bounds outside
    [0, 1]. Wilson must not."""
    from anemoi.inference.postprocess import wilson_interval

    for n in (5, 20, 50, 200):
        for k in range(n + 1):
            lo, hi = wilson_interval(k, n)
            assert 0.0 <= lo <= k / n <= hi <= 1.0

    # Nothing observed is not the same as impossible, and all-observed is
    # not the same as certain -- both keep a real interval at finite n.
    assert wilson_interval(0, 20)[1] > 0.0
    assert wilson_interval(20, 20)[0] < 1.0
    # The interval must actually narrow as the ensemble grows.
    width = lambda n: (lambda b: b[1] - b[0])(wilson_interval(round(0.27 * n), n))
    assert width(20) > width(50) > width(200)


def test_ri_uncertain_marks_an_ensemble_that_cannot_resolve_the_threshold():
    """The real defect behind #188: at 20 members a fraction near 0.3 could
    not distinguish "above the alert threshold" from "we cannot tell", and
    the banner presented it as a definite answer either way."""
    from anemoi.inference.postprocess import wilson_interval

    # 6/20 = 0.30 -- sitting exactly on the threshold, and at this ensemble
    # size the interval spans it, so the honest answer is "cannot tell".
    lo, hi = wilson_interval(6, 20)
    assert lo < 0.3 <= hi, "a 6/20 ensemble cannot resolve a 0.3 threshold"
    # A large, decisive ensemble can.
    lo2, hi2 = wilson_interval(300, 500)
    assert lo2 > 0.3, "300/500 is unambiguously above the threshold"


def test_products_flag_rapid_intensification_above_the_threshold():
    products = build_products(members(wind_gain=20.0))
    assert products.rapid_intensification
    # The point estimate always sits inside its own interval.
    assert products.ri_probability_lo <= products.ri_probability <= products.ri_probability_hi
    assert products.ri_uncertain == (
        products.ri_probability_lo < 0.3 <= products.ri_probability_hi
    )
    assert products.ri_probability > 0.3


def test_products_include_landfall_when_a_coastline_is_supplied():
    products = build_products(members(), coastline=(26.0, -71.0))
    assert products.landfall_probability is not None


def test_products_omit_landfall_without_a_coastline():
    assert build_products(members()).landfall_probability is None
