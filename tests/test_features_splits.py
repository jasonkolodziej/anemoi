"""Dual-flavor features and storm-wise splits (Scope v2.1 §4.3, §4.4, §4.6.1)."""

from datetime import UTC, datetime

import numpy as np
import pytest

from anemoi.data.features import (
    FEATURE_NAMES,
    FlavorMismatchError,
    GriddedFields,
    Normalizer,
    apply_cold_wake,
    area_mean,
    assert_flavor,
    cold_wake_sst_depression_c,
    compare_potential_intensity_estimates,
    compute_environment_features,
    deep_layer_shear,
    emanuel_potential_intensity,
    inner_core_moisture,
    potential_intensity,
)
from anemoi.data.features import _saturation_vapor_pressure_hpa
from anemoi.data.sources import Flavor
from anemoi.data.splits import (
    LeakageError,
    Split,
    assert_no_leakage,
    assign_splits,
    filter_tracks,
)
from anemoi.data.synthetic import generate_archive, generate_fields, paired_fields

T = datetime(2026, 8, 6, 6, tzinfo=UTC)


def test_features_carry_their_flavor():
    fields = generate_fields(T, Flavor.GDAS_FINETUNE, seed=0)
    assert compute_environment_features(fields).flavor is Flavor.GDAS_FINETUNE


def test_feature_vector_length_matches_the_names():
    fs = compute_environment_features(generate_fields(T, Flavor.ERA5_PRETRAIN, seed=0))
    assert fs.values.size == len(FEATURE_NAMES)
    assert set(fs.as_dict()) == set(FEATURE_NAMES)


def test_flavor_guard_rejects_a_pretrain_feature_on_the_operational_path():
    fs = compute_environment_features(generate_fields(T, Flavor.ERA5_PRETRAIN, seed=0))
    with pytest.raises(FlavorMismatchError, match="must not mix"):
        assert_flavor(fs, Flavor.GDAS_FINETUNE)


def test_the_same_code_path_computes_both_flavors():
    """Any ERA5/GDAS difference must come from the data, not the arithmetic."""
    era5, gdas = paired_fields(T, seed=7)
    a = compute_environment_features(era5)
    b = compute_environment_features(gdas)
    assert a.values.shape == b.values.shape
    assert not np.allclose(a.values, b.values)


def test_synthetic_gdas_carries_a_measurable_offset_from_era5():
    """Without this the skew audit would have nothing to detect."""
    deltas = []
    for i in range(20):
        era5, gdas = paired_fields(T, seed=i)
        deltas.append(
            compute_environment_features(gdas)["rh700_pct"]
            - compute_environment_features(era5)["rh700_pct"]
        )
    assert abs(float(np.mean(deltas))) > 0.5


def test_shear_increases_when_the_upper_flow_strengthens():
    low = deep_layer_shear(generate_fields(T, Flavor.ERA5_PRETRAIN, seed=0, shear_kt=5.0))[0]
    high = deep_layer_shear(generate_fields(T, Flavor.ERA5_PRETRAIN, seed=0, shear_kt=40.0))[0]
    assert high > low


def test_potential_intensity_falls_as_shear_rises():
    warm = compute_environment_features(
        generate_fields(T, Flavor.ERA5_PRETRAIN, seed=0, shear_kt=5.0)
    )
    sheared = compute_environment_features(
        generate_fields(T, Flavor.ERA5_PRETRAIN, seed=0, shear_kt=45.0)
    )
    assert sheared["potential_intensity_kt"] < warm["potential_intensity_kt"]


def _radial_gradient_fields(*, center_rh: float, edge_rh: float, shape=(41, 41)) -> GriddedFields:
    """A GriddedFields with a clean (noise-free) radial rh700 gradient, so
    inner-core vs. environmental sampling can be compared deterministically."""
    nlat, nlon = shape
    y, x = np.mgrid[0:nlat, 0:nlon]
    cy, cx = nlat / 2.0, nlon / 2.0
    r = np.clip(np.hypot(y - cy, x - cx) / max(cy, 1.0), 0.0, 1.0)
    rh700 = center_rh + (edge_rh - center_rh) * r
    flat = np.full(shape, 1.0)
    return GriddedFields(
        valid_time=T,
        flavor=Flavor.ERA5_PRETRAIN,
        u200=flat, v200=flat, u850=flat, v850=flat, z500=flat,
        rh700=rh700, t700=flat, mslp=flat,
        sst=np.full(shape, 28.0), ohc=np.full(shape, 60.0),
    )


def test_inner_core_moisture_reflects_the_core_not_the_environment():
    """rh700_pct (large box) and the new inner-core feature (small box) must
    diverge when the storm has a real inner-core-vs-environment gradient --
    otherwise the inner-core feature is redundant with the environmental one."""
    fields = _radial_gradient_fields(center_rh=90.0, edge_rh=40.0)
    fs = compute_environment_features(fields)
    assert fs["rh700_inner_core_pct"] > fs["rh700_pct"]
    assert fs["rh700_inner_core_pct"] == pytest.approx(inner_core_moisture(fields))


def test_cold_wake_depression_grows_with_wind_and_shrinks_with_translation_speed():
    weak_fast = cold_wake_sst_depression_c(max_wind_kt=50.0, translation_speed_kt=15.0)
    strong_fast = cold_wake_sst_depression_c(max_wind_kt=130.0, translation_speed_kt=15.0)
    strong_slow = cold_wake_sst_depression_c(max_wind_kt=130.0, translation_speed_kt=3.0)
    assert 0.0 < weak_fast < strong_fast < strong_slow
    assert strong_slow <= 6.0  # clamped to the documented extreme-case ceiling


def test_cold_wake_is_a_noop_for_zero_wind():
    assert cold_wake_sst_depression_c(max_wind_kt=0.0, translation_speed_kt=10.0) == 0.0


def test_apply_cold_wake_depresses_sst_and_ohc_without_touching_other_fields():
    fields = generate_fields(T, Flavor.ERA5_PRETRAIN, seed=0)
    waked = apply_cold_wake(fields, max_wind_kt=120.0, translation_speed_kt=4.0)

    assert np.mean(waked.sst) < np.mean(fields.sst)
    assert np.mean(waked.ohc) < np.mean(fields.ohc)
    assert waked.valid_time == fields.valid_time
    assert waked.flavor == fields.flavor
    np.testing.assert_array_equal(waked.u850, fields.u850)
    np.testing.assert_array_equal(waked.rh700, fields.rh700)


def test_apply_cold_wake_is_a_noop_for_a_calm_storm():
    fields = generate_fields(T, Flavor.ERA5_PRETRAIN, seed=0)
    waked = apply_cold_wake(fields, max_wind_kt=0.0, translation_speed_kt=10.0)
    np.testing.assert_array_equal(waked.sst, fields.sst)
    np.testing.assert_array_equal(waked.ohc, fields.ohc)


def test_saturation_vapor_pressure_matches_known_bolton_values():
    """External sanity check against commonly-cited values, not just internal
    consistency: es(0 degC) = 6.112 hPa by construction; es(25 degC) ~ 31.7 hPa
    is the standard textbook figure."""
    assert _saturation_vapor_pressure_hpa(0.0) == pytest.approx(6.112, abs=0.01)
    assert _saturation_vapor_pressure_hpa(25.0) == pytest.approx(31.7, abs=0.2)


def test_emanuel_pi_increases_with_warmer_sst():
    cool = emanuel_potential_intensity(24.0, 24.0 + 273.15 - 1.0, 80.0, 1012.0)
    warm = emanuel_potential_intensity(30.0, 30.0 + 273.15 - 1.0, 80.0, 1012.0)
    assert warm > cool


def test_emanuel_pi_is_reduced_above_the_shear_onset():
    calm = emanuel_potential_intensity(29.0, 29.0 + 273.15 - 1.0, 80.0, 1012.0, shear_kt=5.0)
    sheared = emanuel_potential_intensity(29.0, 29.0 + 273.15 - 1.0, 80.0, 1012.0, shear_kt=40.0)
    assert sheared < calm


def test_emanuel_pi_is_zero_when_the_boundary_layer_is_warmer_and_moister_than_the_surface():
    """A stable/inverted setup has no thermodynamic potential intensity --
    delta_k is floored at zero rather than going negative."""
    pi = emanuel_potential_intensity(
        sst_c=15.0, boundary_layer_temp_k=320.0, boundary_layer_rh_pct=99.0,
        surface_pressure_mb=1012.0,
    )
    assert pi == 0.0


def test_compare_potential_intensity_estimates_documents_the_closed_form_running_hot():
    """The closed-form model, fed a guessed climatological boundary layer
    (GriddedFields has no real near-surface sounding), runs systematically
    higher than the regression proxy -- this is *why* potential_intensity()
    keeps the proxy as the pipeline default rather than switching to the
    real equation with fabricated inputs. If this stops being true, the
    docstrings in features.py making that argument need revisiting too."""
    fields = generate_fields(T, Flavor.ERA5_PRETRAIN, seed=0)
    estimates = compare_potential_intensity_estimates(fields, shear_kt=12.0)
    assert estimates["closed_form_kt"] > estimates["proxy_kt"]


def test_potential_intensity_proxy_is_unaffected_by_the_closed_form_addition():
    """Regression guard: compute_environment_features must still call the
    proxy, not the closed form, for its production feature values."""
    fields = generate_fields(T, Flavor.ERA5_PRETRAIN, seed=0)
    sst_c = area_mean(fields.sst)
    ohc = area_mean(fields.ohc)
    shear_mag = deep_layer_shear(fields)[0]
    expected = potential_intensity(sst_c, ohc, shear_mag)
    fs = compute_environment_features(fields)
    assert fs["potential_intensity_kt"] == pytest.approx(expected)


def test_normalizer_refuses_to_fit_across_flavors():
    era5, gdas = paired_fields(T, seed=1)
    with pytest.raises(FlavorMismatchError, match="mixed flavors"):
        Normalizer.fit(
            [compute_environment_features(era5), compute_environment_features(gdas)]
        )


def test_normalizer_rejects_the_wrong_flavor_at_apply_time():
    sets = [
        compute_environment_features(generate_fields(T, Flavor.GDAS_FINETUNE, seed=i))
        for i in range(10)
    ]
    norm = Normalizer.fit(sets)
    era5 = compute_environment_features(generate_fields(T, Flavor.ERA5_PRETRAIN, seed=0))
    with pytest.raises(FlavorMismatchError):
        norm.apply(era5)


# --- splits ----------------------------------------------------------------


def test_splits_follow_the_scope_season_boundaries():
    tracks = generate_archive(2018, 2026, storms_per_season=4, seed=1)
    assignment = assign_splits(tracks)
    for track in tracks:
        split = assignment.of(track.storm_id)
        if track.season <= 2019:
            assert split is Split.TRAIN
        elif track.season <= 2022:
            assert split is Split.VAL
        elif track.season <= 2025:
            assert split is Split.TEST
        else:
            assert split is Split.OPERATIONAL


def test_no_storm_appears_in_two_splits():
    tracks = generate_archive(2015, 2026, storms_per_season=5, seed=2)
    assignment = assign_splits(tracks)
    assert_no_leakage(assignment, tracks)
    ids = [set(assignment.ids(s)) for s in Split]
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            assert not (a & b)


def test_splits_are_also_chronologically_ordered():
    tracks = generate_archive(2015, 2026, storms_per_season=5, seed=3)
    assignment = assign_splits(tracks)
    train = filter_tracks(tracks, assignment, Split.TRAIN)
    test = filter_tracks(tracks, assignment, Split.TEST)
    assert max(t.season for t in train) < min(t.season for t in test)


def test_overlapping_boundaries_are_rejected():
    boundaries = {
        Split.TRAIN: (1980, 2020),
        Split.VAL: (2020, 2022),
        Split.TEST: (2023, 2025),
        Split.OPERATIONAL: (2026, 2100),
    }
    with pytest.raises(ValueError, match="overlapping"):
        assign_splits(generate_archive(2019, 2021, 3, seed=4), boundaries)


def test_leakage_is_detected_when_a_storm_id_repeats_across_seasons():
    tracks = generate_archive(2019, 2021, storms_per_season=3, seed=5)
    duplicate = tracks[0]
    later = [t for t in tracks if t.season >= 2021][0]
    forged = type(duplicate)(
        storm_id=duplicate.storm_id,
        fixes=tuple(
            type(f)(
                storm_id=duplicate.storm_id,
                valid_time=f.valid_time,
                lat=f.lat,
                lon=f.lon,
                max_wind_kt=f.max_wind_kt,
                min_pressure_mb=f.min_pressure_mb,
                quality=f.quality,
            )
            for f in later.fixes
        ),
    )
    with pytest.raises(LeakageError):
        assign_splits([duplicate, forged])
