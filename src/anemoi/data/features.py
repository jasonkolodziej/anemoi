"""Derived environmental features, computed through one code path per flavor.

Scope v2.1 §4.3 Stage 3 and §4.6.1. Every derived field exists in an ERA5
flavor (Stage A) and a GDAS flavor (Stage B / production). The requirement that
matters is that the *same function* computes both: if shear is computed one way
for pretraining and another for production, the fine-tuning stage is correcting
for a code difference as well as a data difference, and neither is diagnosable.

:class:`FeatureSet` therefore carries its flavor, and :func:`assert_flavor`
is called at every boundary where a flavor mismatch would be silent.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, replace
from datetime import datetime

import numpy as np

from .sources import Flavor

# Two structural gaps in this feature set, both affecting intensity rather than
# track. Both now have a minimum-viable closing, named here rather than left
# to be discovered during a backtest -- neither is the full treatment.
#
# 1. Inner-core moisture. Emanuel and Zhang (2017, doi:10.1175/JAS-D-17-0008.1)
#    find intensity error growth is at least as sensitive to inner-core
#    moisture specification as to the wind field. ``rh700_pct`` is an area
#    mean over the *whole* storm-relative box -- an environmental quantity.
#    ``rh700_inner_core_pct`` below samples the same field over a much
#    tighter inner radius (see ``INNER_CORE_RADIUS_FRAC``), which is the
#    inner-core signal this box can actually resolve. A dedicated
#    higher-resolution inner-core product (e.g. from satellite; see #19) is a
#    further step, not a prerequisite for this one.
#
# 2. Ocean feedback. ``sst_c`` and ``ohc_kj_cm2`` were static area means from a
#    daily product persisted from the previous day (see data.availability). A
#    storm's own cold wake -- the upwelling and mixing it induces, which then
#    limits its own intensification -- was nowhere in this system, despite
#    being a first-order intensity feedback. :func:`apply_cold_wake` is the
#    minimum viable version PLAN.md/Roadmap describe: an empirical SST/OHC
#    depression from the storm's own wind speed and translation speed, applied
#    to ``GriddedFields`` before feature computation. It is not two-way
#    atmosphere-ocean coupling (Lai et al. 2025 driving UWIN-CM; FuXi-TC on a
#    coupled base) -- that remains a separate, larger effort.

#: Radius (as a fraction of the domain, see :func:`area_mean`) used to sample
#: the inner-core moisture feature -- much tighter than the default 0.5 used
#: for environmental sampling elsewhere in this module.
INNER_CORE_RADIUS_FRAC = 0.15

#: Names produced by :func:`compute_environment_features`, in output order.
#: New features are appended, never inserted -- several call sites (the drift
#: monitor's reference distribution, test fixtures) index into this tuple.
FEATURE_NAMES: tuple[str, ...] = (
    "shear_magnitude_kt",
    "shear_direction_deg",
    "steering_u_kt",
    "steering_v_kt",
    "sst_c",
    "ohc_kj_cm2",
    "rh700_pct",
    "vorticity850_1e5s",
    "potential_intensity_kt",
    "ivt_kg_ms",
    "rh700_inner_core_pct",
)


@dataclass(frozen=True, slots=True)
class GriddedFields:
    """Storm-centred environmental fields on a common 0.25 degree grid.

    A deliberately small subset of §4.3 Stage 1 output: enough to compute the
    derived fields the deterministic models consume, without pretending to be a
    full NWP state vector.
    """

    valid_time: datetime
    flavor: Flavor
    #: All arrays share shape (nlat, nlon) over the storm-relative box.
    u200: np.ndarray
    v200: np.ndarray
    u850: np.ndarray
    v850: np.ndarray
    z500: np.ndarray
    rh700: np.ndarray
    t700: np.ndarray
    mslp: np.ndarray
    sst: np.ndarray
    ohc: np.ndarray

    def __post_init__(self) -> None:
        shapes = {a.shape for a in self._arrays()}
        if len(shapes) != 1:
            raise ValueError(f"ragged field shapes: {sorted(shapes)}")
        if len(next(iter(shapes))) != 2:
            raise ValueError("fields must be 2-D (nlat, nlon)")

    def _arrays(self) -> tuple[np.ndarray, ...]:
        return (
            self.u200, self.v200, self.u850, self.v850, self.z500,
            self.rh700, self.t700, self.mslp, self.sst, self.ohc,
        )

    @property
    def shape(self) -> tuple[int, int]:
        return self.u200.shape


@dataclass(frozen=True, slots=True)
class FeatureSet:
    """Derived scalar features for one storm at one time, tagged with flavor."""

    valid_time: datetime
    flavor: Flavor
    values: np.ndarray

    def __post_init__(self) -> None:
        if self.values.shape != (len(FEATURE_NAMES),):
            raise ValueError(
                f"expected {len(FEATURE_NAMES)} features, got {self.values.shape}"
            )
        if not np.all(np.isfinite(self.values)):
            raise ValueError("non-finite feature value")

    def as_dict(self) -> dict[str, float]:
        return dict(zip(FEATURE_NAMES, (float(v) for v in self.values), strict=True))

    def __getitem__(self, name: str) -> float:
        return float(self.values[FEATURE_NAMES.index(name)])


class FlavorMismatchError(ValueError):
    """A feature computed from one input distribution reached the other path."""


def assert_flavor(obj: FeatureSet | GriddedFields, expected: Flavor) -> None:
    """Guard against mixing ERA5-derived and GDAS-derived features.

    Called by the Stage A/B dataset builders and by the inference path. In
    production ``expected`` is always ``GDAS_FINETUNE``.
    """
    if obj.flavor is not expected:
        raise FlavorMismatchError(
            f"expected {expected.value} features, got {obj.flavor.value} "
            "(Scope v2.1 §4.6.1: pretrain and operational flavors must not mix)"
        )


def area_mean(field: np.ndarray, radius_frac: float = 0.5) -> float:
    """Mean over a centred sub-box, used for environmental sampling (§4.3).

    Uses ``np.nanmean``, not ``np.mean`` -- real ERA5's ``sea_surface_
    temperature`` is NaN over land (GDAS's sst/ohc are constant placeholders,
    never NaN -- see ``real_gridded.gdas_to_gridded_fields``, so this only
    matters for Stage A / ``ERA5_PRETRAIN``). A storm-centred box near the
    coast or making landfall routinely overlaps land pixels; with a plain
    ``mean`` a single land pixel poisons the whole box to NaN, which is what
    surfaced this (a real ``non-finite feature value`` failure training
    PINN, the only model that calls ``compute_environment_features`` --
    CNN/Transformer/GNN consume raw field pixels directly instead and need
    their own fix, ``sanitize_field_pixels`` below; LSTM never touches
    gridded fields at all).

    **This is a real, deliberate change to what "SST near this storm"
    physically means, not a value-neutral bug fix** -- worth understanding
    before trusting a PINN environment vector for a landfalling or
    near-coast storm:

    - For a box that is PARTIALLY land, the returned mean is now over
      *whatever fraction of the box is ocean* -- not the full box's
      footprint. As land coverage grows, the effective sampling area
      shrinks and drifts toward whatever ocean remains, and that drift is
      invisible in the returned scalar: two boxes with very different
      ocean fractions can return numbers of similar magnitude, one a mean
      over most of the box, the other over a sliver of it near one edge.
    - For a box that is ENTIRELY land, ``nanmean`` itself returns NaN (its
      documented behaviour on an all-NaN slice; the resulting
      "Mean of empty slice" ``RuntimeWarning`` is expected here and
      suppressed, not a bug). ``FeatureSet.__post_init__`` still catches
      that as non-finite, and callers (``real_run_pinn.build_pinn_samples``/
      ``train_pinn_stage_streaming``) skip that window entirely -- the same
      "skip, don't crash" contract already used for a window with no
      cached file, not a fabricated land-SST value standing in for open
      water.
    - Atmospheric fields (u200/v200/u850/v850/z500/rh700/t700/mslp) are not
      land-masked in ERA5, so ``nanmean`` is numerically identical to
      ``mean`` for them -- this only changes behaviour for sst/ohc.

    Net effect: PINN training loses some real windows for storms very close
    to or over land (where the box is entirely land), and for storms with
    partial land coverage, its SST/OHC-derived features are computed over a
    smaller, ocean-only footprint whose exact extent isn't recorded
    anywhere -- a real, accepted limitation of not having a true land/sea
    mask to reason about coverage fraction explicitly, not a hidden one.
    """
    if not 0.0 < radius_frac <= 1.0:
        raise ValueError("radius_frac must be in (0, 1]")
    nlat, nlon = field.shape
    hlat = max(int(nlat * radius_frac / 2), 1)
    hlon = max(int(nlon * radius_frac / 2), 1)
    clat, clon = nlat // 2, nlon // 2
    box = field[
        max(clat - hlat, 0) : clat + hlat + 1,
        max(clon - hlon, 0) : clon + hlon + 1,
    ]
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Mean of empty slice")
        return float(np.nanmean(box))


def sanitize_field_pixels(field: np.ndarray) -> np.ndarray | None:
    """Real NaN handling for CNN/Transformer/GNN's raw-pixel input path --
    the gap ``area_mean``'s own docstring names ("CNN/Transformer/GNN
    consume raw field pixels directly and never hit this validation").

    Unlike ``area_mean``, which reduces a box to one scalar, these three
    models feed every pixel of a cached field directly into the network,
    so a single NaN pixel (real ERA5's ``sea_surface_temperature`` is NaN
    over land; other fields may be too, depending on how they're derived)
    isn't just one bad value -- it corrupts `training.streaming
    .OnlineMeanStd`, a plain, non-NaN-aware running mean fit once per
    stage across every window's raw channel stack. The first NaN pixel any
    window contributes turns ``x_mean``/``x_std`` NaN *permanently* for
    that stage (`OnlineMeanStd.update`'s running-aggregate math has no way
    to recover once ``self.mean`` is NaN), which then poisons
    ``(x - x_mean) / x_std`` standardization for *every* window, not just
    the ones that actually touch land -- this is why real CNN/Transformer/
    GNN training against the real ERA5 cache produced ``nan`` loss for
    every single batch, confirmed via a real MLflow query
    (2026-09-17 full-schedule run), not something a per-window skip alone
    would have caught.

    Same "sample from remaining ocean" semantics ``area_mean`` already
    uses, applied per-pixel instead of per-box-average: every NaN pixel is
    replaced with that field's own real spatial mean over its still-valid
    (non-NaN) pixels, so a land pixel reads as "about what the surrounding
    real ocean reads" rather than an arbitrary sentinel like 0 the model
    would otherwise have to learn to treat as meaningless. Returns
    ``None`` if the whole field is NaN (the box is entirely land) -- the
    caller must skip that window, the same "skip, don't corrupt" contract
    ``area_mean``'s own callers already use for an all-NaN box.
    """
    if not np.isnan(field).any():
        return field
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Mean of empty slice")
        fill = np.nanmean(field)
    if np.isnan(fill):
        return None
    return np.where(np.isnan(field), fill, field)


def deep_layer_shear(fields: GriddedFields) -> tuple[float, float]:
    """200-850 mb shear magnitude (kt) and direction (deg from north).

    Annular sampling (the 200-800 km ring) is the operational convention; here
    we use the centred box mean, which is adequate for the synthetic data this
    reference implementation ships with and is the single place to change when
    real fields are wired in.
    """
    du = area_mean(fields.u200) - area_mean(fields.u850)
    dv = area_mean(fields.v200) - area_mean(fields.v850)
    magnitude = float(np.hypot(du, dv))
    direction = float((np.degrees(np.arctan2(du, dv)) + 360.0) % 360.0)
    return magnitude, direction


def steering_flow(fields: GriddedFields) -> tuple[float, float]:
    """Deep-layer-mean steering wind (u, v) in knots.

    A 850/200 mb mass-weighted mean stands in for the full 850-250 mb integral.
    """
    u = 0.7 * area_mean(fields.u850) + 0.3 * area_mean(fields.u200)
    v = 0.7 * area_mean(fields.v850) + 0.3 * area_mean(fields.v200)
    return float(u), float(v)


def relative_vorticity_850(fields: GriddedFields, dx_km: float = 27.75) -> float:
    """Centred-difference relative vorticity at 850 mb, in 1e-5 s^-1.

    ``dx_km`` defaults to the meridional spacing of a 0.25 degree grid.
    """
    dvdx = np.gradient(fields.v850, axis=1) / (dx_km * 1000.0)
    dudy = np.gradient(fields.u850, axis=0) / (dx_km * 1000.0)
    kt_to_ms = 0.514444
    return float(area_mean((dvdx - dudy) * kt_to_ms) * 1e5)


#: Bister & Emanuel (1998) take Ck/Cd close to 1 (their surface-exchange
#: coefficients for enthalpy and momentum); observations suggest both vary at
#: extreme wind speeds, but a constant ratio is the standard simplification.
CK_OVER_CD = 1.0

#: Outflow-layer (tropopause) temperature. The real algorithm derives this
#: from a full vertical sounding (the parcel's saturation point at its
#: outflow level); GriddedFields does not carry one, so this is a fixed
#: climatological value for the deep tropics rather than a computed one.
OUTFLOW_TEMPERATURE_K = 200.0

#: Standard thermodynamic constants used by the enthalpy-disequilibrium term.
LATENT_HEAT_VAPORIZATION_J_KG = 2.5e6
SPECIFIC_HEAT_DRY_AIR_J_KG_K = 1005.0

#: Above this shear (kt), potential intensity is reduced below the
#: thermodynamic ceiling. Shear disruption is a well-established empirical
#: effect (e.g. DeMaria 1996, doi:10.1175/1520-0469(1996)053<2076:TEOVWS>2.0.CO;2)
#: applied on top of PI, not part of Emanuel's Carnot-cycle theory itself --
#: PI is inherently a shear-free ceiling.
SHEAR_PENALTY_ONSET_KT = 10.0
SHEAR_PENALTY_KT_PER_KT = 1.8


def _saturation_vapor_pressure_hpa(temp_c: float) -> float:
    """Bolton (1980, doi:10.1175/1520-0493(1980)108<1046:TCOEPT>2.0.CO;2),
    accurate to within ~0.3% over -35 to 35 degC -- the standard closed-form
    substitute for integrating the Clausius-Clapeyron relation."""
    return 6.112 * float(np.exp(17.67 * temp_c / (temp_c + 243.5)))


def _specific_humidity_kg_kg(vapor_pressure_hpa: float, pressure_hpa: float) -> float:
    denom = max(pressure_hpa - 0.378 * vapor_pressure_hpa, 1.0)
    return 0.622 * vapor_pressure_hpa / denom


def emanuel_potential_intensity(
    sst_c: float,
    boundary_layer_temp_k: float,
    boundary_layer_rh_pct: float,
    surface_pressure_mb: float,
    shear_kt: float = 0.0,
    *,
    ck_over_cd: float = CK_OVER_CD,
    outflow_temp_k: float = OUTFLOW_TEMPERATURE_K,
) -> float:
    """Potential intensity (kt) from Bister & Emanuel's (1998) closed form.

    ``Vmax^2 = (Ck/Cd) * (Ts - T0)/T0 * dk``, where ``dk`` is the enthalpy
    disequilibrium between air saturated at the sea surface and the actual
    boundary-layer air (doi:10.1175/1520-0469(1995)052<3969:SOTCTS>2.0.CO;2,
    as extended by doi:10.1007/BF01030791 for dissipative heating -- citing
    the 1995 paper alone understates what is actually implemented here,
    matching the operational ``pcmin`` code's formulation). This is the real
    equation, not a regression standing in for it.

    A shear penalty is applied afterward, not folded into ``dk`` -- PI theory
    is inherently a shear-free ceiling; shear is a separate, well-established
    reduction below that ceiling (see ``SHEAR_PENALTY_ONSET_KT``).
    """
    sst_k = sst_c + 273.15

    es_sst = _saturation_vapor_pressure_hpa(sst_c)
    qs_sst = _specific_humidity_kg_kg(es_sst, surface_pressure_mb)

    boundary_layer_temp_c = boundary_layer_temp_k - 273.15
    es_bl = _saturation_vapor_pressure_hpa(boundary_layer_temp_c)
    e_bl = np.clip(boundary_layer_rh_pct, 0.0, 100.0) / 100.0 * es_bl
    q_bl = _specific_humidity_kg_kg(e_bl, surface_pressure_mb)

    delta_k = SPECIFIC_HEAT_DRY_AIR_J_KG_K * (sst_k - boundary_layer_temp_k) + (
        LATENT_HEAT_VAPORIZATION_J_KG * (qs_sst - q_bl)
    )
    delta_k = max(delta_k, 0.0)  # a stable/inverted boundary layer has no PI, not a negative one

    v_max_ms_sq = ck_over_cd * (sst_k - outflow_temp_k) / outflow_temp_k * delta_k
    v_max_kt = np.sqrt(max(v_max_ms_sq, 0.0)) * 1.943844

    shear_penalty = SHEAR_PENALTY_KT_PER_KT * max(shear_kt - SHEAR_PENALTY_ONSET_KT, 0.0)
    return float(np.clip(v_max_kt - shear_penalty, 0.0, 200.0))


def potential_intensity(sst_c: float, ohc: float, shear_kt: float) -> float:
    """Empirical potential-intensity proxy in knots. Still the pipeline default.

    An SST/OHC/shear regression standing in for :func:`emanuel_potential_intensity`,
    the real algorithm implemented above. The interface is the one the real
    implementation will keep; swapping it out changes this function's one
    call site in :func:`compute_environment_features`.

    Deliberately not swapped in yet: :func:`emanuel_potential_intensity` needs
    a real boundary-layer/outflow sounding to be trustworthy, and
    ``GriddedFields`` only has 700 mb-level fields, not a near-surface one.
    Feeding it a guessed boundary layer close to SST produces PI estimates
    that stay implausibly high across the full SST range this proxy covers
    (see :func:`compare_potential_intensity_estimates` and
    ``test_emanuel_pi_needs_real_soundings_before_replacing_the_proxy``) --
    swapping a regression for a real equation fed fabricated inputs is not
    an improvement, it just moves the uncertainty somewhere less visible.
    Wiring this in for real is tracked with real GriddedFields (#18).
    """
    base = 15.0 * max(sst_c - 26.0, 0.0)
    ohc_bonus = 0.25 * max(ohc, 0.0)
    shear_penalty = 1.8 * max(shear_kt - 10.0, 0.0)
    return float(np.clip(35.0 + base + ohc_bonus - shear_penalty, 0.0, 200.0))


def compare_potential_intensity_estimates(
    fields: GriddedFields, shear_kt: float
) -> dict[str, float]:
    """Run both PI estimates on the same case, for inspection and testing.

    The closed-form estimate approximates the boundary layer GriddedFields
    doesn't carry as a well-mixed marine layer close to SST, humidity
    modulated by 700 mb RH as the best available moisture signal -- a
    climatological stand-in, not measured data. Compare the two rather than
    trusting either in isolation until real soundings exist.
    """
    sst_c = area_mean(fields.sst)
    ohc = area_mean(fields.ohc)
    surface_pressure_mb = area_mean(fields.mslp)
    boundary_layer_temp_k = sst_c + 273.15 - 1.0
    boundary_layer_rh_pct = np.clip(80.0 * (area_mean(fields.rh700) / 70.0), 50.0, 95.0)

    return {
        "proxy_kt": potential_intensity(sst_c, ohc, shear_kt),
        "closed_form_kt": emanuel_potential_intensity(
            sst_c,
            boundary_layer_temp_k,
            boundary_layer_rh_pct,
            surface_pressure_mb,
            shear_kt,
        ),
    }


def integrated_vapor_transport(fields: GriddedFields) -> float:
    """IVT proxy (kg m^-1 s^-1) from 850 mb wind and 700 mb humidity."""
    speed_ms = np.hypot(fields.u850, fields.v850) * 0.514444
    q = np.clip(fields.rh700, 0.0, 100.0) / 100.0 * 0.018
    return float(area_mean(speed_ms * q) * 9806.65 / 9.81)


def inner_core_moisture(fields: GriddedFields) -> float:
    """700 mb relative humidity sampled over the inner core, not the environment.

    Same field as ``rh700_pct``, sampled over ``INNER_CORE_RADIUS_FRAC``
    instead of the default environmental box -- see the module-level note on
    why this is the minimum-viable closing of the inner-core moisture gap.
    """
    return area_mean(fields.rh700, radius_frac=INNER_CORE_RADIUS_FRAC)


def cold_wake_sst_depression_c(
    max_wind_kt: float, translation_speed_kt: float, *, max_depression_c: float = 6.0
) -> float:
    """Empirical SST depression (°C) from a storm's own wind-driven mixing.

    Not a mixed-layer model -- a minimum-viable parameterisation capturing the
    two dominant, well-documented dependencies (e.g. Cione and Uhlhorn 2003,
    Mei and Pasquero 2013): cooling grows roughly with the cube of wind speed
    (wind-stress-driven mixing) and falls off with translation speed (a fast
    mover spends less time over any one patch of ocean). Clamped to
    ``max_depression_c``, matching the upper end of documented extreme cases
    (e.g. Hurricane Igor, ~6 degC).
    """
    if max_wind_kt <= 0.0:
        return 0.0
    speed_floor_kt = 2.0  # avoids a near-stationary storm producing unbounded cooling
    speed = max(translation_speed_kt, speed_floor_kt)
    depression = 0.35 * (max_wind_kt / 50.0) ** 3 * (10.0 / speed)
    return float(np.clip(depression, 0.0, max_depression_c))


def apply_cold_wake(
    fields: GriddedFields, max_wind_kt: float, translation_speed_kt: float
) -> GriddedFields:
    """Return ``fields`` with SST/OHC depressed by the storm's own cold wake.

    Minimum viable version of PLAN.md/Roadmap's "make SST/OHC vary along the
    forecast track with a wake parameterisation, rather than freezing them at
    t-1 day": applied once, to the fields for a given cycle/lead, using that
    cycle's own wind and translation speed -- not an ocean model, and not
    persisted across cycles. OHC is depressed less than SST in relative terms
    (it integrates a deeper layer than the skin temperature does).
    """
    depression_c = cold_wake_sst_depression_c(max_wind_kt, translation_speed_kt)
    if depression_c <= 0.0:
        return fields
    ohc_factor = 1.0 - 0.6 * (depression_c / 6.0)
    return replace(
        fields,
        sst=np.clip(fields.sst - depression_c, -2.0, None),
        ohc=np.clip(fields.ohc * ohc_factor, 0.0, None),
    )


def compute_environment_features(fields: GriddedFields) -> FeatureSet:
    """The single code path used for both Stage A and Stage B (§4.6.1).

    The only thing that differs between flavors is the ``fields`` handed in;
    the arithmetic is identical, so any train/serve gap that shows up in the
    skew audit is attributable to the data rather than to the code.
    """
    shear_mag, shear_dir = deep_layer_shear(fields)
    steer_u, steer_v = steering_flow(fields)
    sst_c = area_mean(fields.sst)
    ohc = area_mean(fields.ohc)
    values = np.array(
        [
            shear_mag,
            shear_dir,
            steer_u,
            steer_v,
            sst_c,
            ohc,
            area_mean(fields.rh700),
            relative_vorticity_850(fields),
            potential_intensity(sst_c, ohc, shear_mag),
            integrated_vapor_transport(fields),
            inner_core_moisture(fields),
        ],
        dtype=float,
    )
    return FeatureSet(
        valid_time=fields.valid_time, flavor=fields.flavor, values=values
    )


@dataclass(frozen=True, slots=True)
class Normalizer:
    """Per-feature standardisation fitted on the training split only.

    Fitted statistics are flavor-specific: GDAS analyses have a different mean
    and spread from ERA5, so a normaliser fitted on Stage A must not be reused
    at inference. The flavor travels with the object and is checked on apply.
    """

    flavor: Flavor
    mean: np.ndarray
    std: np.ndarray

    @classmethod
    def fit(cls, feature_sets: list[FeatureSet]) -> Normalizer:
        if not feature_sets:
            raise ValueError("cannot fit a normalizer on an empty set")
        flavors = {fs.flavor for fs in feature_sets}
        if len(flavors) > 1:
            raise FlavorMismatchError(
                f"cannot fit across mixed flavors: {sorted(f.value for f in flavors)}"
            )
        stacked = np.stack([fs.values for fs in feature_sets])
        std = stacked.std(axis=0)
        std[std < 1e-8] = 1.0
        return cls(flavor=flavors.pop(), mean=stacked.mean(axis=0), std=std)

    def apply(self, fs: FeatureSet) -> np.ndarray:
        assert_flavor(fs, self.flavor)
        return (fs.values - self.mean) / self.std
