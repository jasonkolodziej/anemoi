"""Dual-flavor features and storm-wise splits (Scope v2.1 §4.3, §4.4, §4.6.1)."""

from datetime import UTC, datetime

import numpy as np
import pytest

from anemoi.data.features import (
    FEATURE_NAMES,
    FlavorMismatchError,
    GriddedFields,
    Normalizer,
    _saturation_vapor_pressure_hpa,
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
    sanitize_field_pixels,
)
from anemoi.data.sources import Flavor
from anemoi.data.splits import (
    DEFAULT_BOUNDARIES,
    STAGE_B_BOUNDARIES,
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


# --- area_mean over land-masked (NaN) real ERA5 SST --------------------------
#
# Real bug found training PINN for real on the VM against the actual growing
# ERA5 cache (#67): real ERA5 sea_surface_temperature is NaN over land, and a
# storm-centred box near the coast or making landfall routinely overlaps land
# pixels. area_mean used a plain np.mean, so a single land pixel poisoned the
# whole box to NaN -- the first real end-to-end run to reach PINN (every
# earlier one OOM'd at Transformer first) crashed on a genuine near-coast
# storm with ValueError("non-finite feature value"). These tests pin the
# nanmean fix's real, deliberate behavior change (area_mean's own docstring
# has the full physical-meaning discussion).


def test_area_mean_ignores_nan_pixels_from_partial_land_coverage():
    """A storm box straddling the coast must produce a real mean over its
    ocean pixels, not be poisoned to NaN by the land pixels alongside them."""
    field = np.full((41, 41), 28.0)
    field[:20, :] = np.nan  # the box's northern half is "land"
    result = area_mean(field)
    assert np.isfinite(result)
    # area_mean's default radius_frac=0.5 box for a 41x41 field is rows/cols
    # 10:31 -- partially inside the NaN region, partially not
    box = field[10:31, 10:31]
    assert result == pytest.approx(np.nanmean(box))


def test_area_mean_matches_plain_mean_when_nothing_is_nan():
    """The fix must be a no-op for the atmospheric fields (never land-masked
    in ERA5) -- nanmean over an all-finite array equals mean exactly."""
    rng = np.random.default_rng(3)
    field = rng.normal(loc=10.0, scale=3.0, size=(41, 41))
    box = field[10:31, 10:31]  # area_mean's own default radius_frac=0.5 box
    assert area_mean(field) == pytest.approx(float(np.mean(box)))


def test_area_mean_returns_nan_when_the_whole_box_is_land():
    """A box entirely over land has no real ocean pixels to average -- NaN
    is the correct, honest answer (not a fabricated land-SST value), and
    callers (build_pinn_samples/train_pinn_stage_streaming) must treat this
    as "skip this window", not crash the whole run."""
    field = np.full((41, 41), np.nan)
    assert np.isnan(area_mean(field))


def test_compute_environment_features_raises_when_storm_is_entirely_over_land():
    import dataclasses

    fields = generate_fields(T, Flavor.ERA5_PRETRAIN, seed=0)
    land_fields = dataclasses.replace(fields, sst=np.full(fields.sst.shape, np.nan))
    with pytest.raises(ValueError, match="non-finite"):
        compute_environment_features(land_fields)


def test_compute_environment_features_succeeds_with_partial_land_coverage():
    """The real case the fix closes: a storm near the coast, box only
    partially over land, must produce a real finite feature vector instead
    of crashing -- confirms the area_mean fix actually reaches
    compute_environment_features's real call site, not just area_mean in
    isolation."""
    import dataclasses

    fields = generate_fields(T, Flavor.ERA5_PRETRAIN, seed=0)
    sst = fields.sst.copy()
    sst[:5, :] = np.nan  # a strip of land at one edge -- box still mostly ocean
    coastal_fields = dataclasses.replace(fields, sst=sst)
    fs = compute_environment_features(coastal_fields)  # must not raise
    assert np.all(np.isfinite(fs.values))
    assert fs["sst_c"] == pytest.approx(area_mean(sst))


# --- sanitize_field_pixels: CNN/Transformer/GNN's raw-pixel NaN fix ----------
#
# area_mean's fix (above) only helps PINN, which reduces a box to one scalar.
# CNN/Transformer/GNN feed every pixel directly into the model -- a real,
# separate bug found re-verifying the num_workers fix on the VM (2026-09-17):
# a real full-schedule run produced `nan` train/val loss for CNN, Transformer,
# GNN, and diffusion (conditioned on their now NaN-weighted latents), while
# LSTM/PINN (neither touches raw pixels the same way) came back with real
# finite numbers in the same run -- confirmed via a real MLflow metrics query,
# not assumed. Root cause: a NaN pixel reaches `training.streaming
# .OnlineMeanStd`'s plain (non-NaN-aware) running mean during the online
# standardization pass, which corrupts x_mean/x_std *permanently* for that
# whole stage, not just the one window that touched land.


def test_sanitize_field_pixels_fills_nan_with_the_fields_own_spatial_mean():
    field = np.full((41, 41), 28.0)
    field[:20, :] = np.nan  # "land" strip
    result = sanitize_field_pixels(field)
    assert result is not None
    assert np.all(np.isfinite(result))
    assert result[0, 0] == pytest.approx(np.nanmean(field))  # land pixel filled
    assert result[40, 40] == pytest.approx(28.0)  # real ocean pixel untouched


def test_sanitize_field_pixels_is_a_no_op_when_nothing_is_nan():
    rng = np.random.default_rng(3)
    field = rng.normal(loc=10.0, scale=3.0, size=(41, 41))
    result = sanitize_field_pixels(field)
    assert result is field  # returned unchanged, not merely equal


def test_sanitize_field_pixels_returns_none_when_the_whole_field_is_nan():
    field = np.full((41, 41), np.nan)
    assert sanitize_field_pixels(field) is None


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


def test_stage_b_boundaries_are_valid_and_disjoint_from_the_default_train_window():
    """STAGE_B_BOUNDARIES exists because GDAS's real archive (2021-present)
    has zero overlap with DEFAULT_BOUNDARIES' train window (1980-2019) --
    assign_splits with it must not raise, and its train window must sit
    entirely within GDAS's real-data floor."""
    tracks = generate_archive(2021, 2025, storms_per_season=4, seed=7)
    assignment = assign_splits(tracks, STAGE_B_BOUNDARIES)  # must not raise
    assert_no_leakage(assignment, tracks)

    train_lo, _ = STAGE_B_BOUNDARIES[Split.TRAIN]
    default_train_lo, default_train_hi = DEFAULT_BOUNDARIES[Split.TRAIN]
    assert train_lo > default_train_hi  # no season is real-GDAS-train under both schemes


def test_stage_b_boundaries_assign_the_expected_split_per_season():
    tracks = generate_archive(2021, 2025, storms_per_season=3, seed=8)
    assignment = assign_splits(tracks, STAGE_B_BOUNDARIES)
    for track in tracks:
        split = assignment.of(track.storm_id)
        if track.season <= 2022:
            assert split is Split.TRAIN
        elif track.season == 2023:
            assert split is Split.VAL
        else:
            assert split is Split.TEST


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
