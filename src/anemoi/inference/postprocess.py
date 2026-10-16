"""Post-processing of the Anemoi-Spread ensemble into forecast products.

Scope v2.1 §6.1. Cone of uncertainty, intensity PDF, landfall probability and
the rapid-intensification flag.

Note on the cone: NHC's official cone is built from *historical* official-forecast
error percentiles, not from the current ensemble spread. A cone drawn from a
model's own spread is only honest if that spread is calibrated, which is exactly
what :func:`anemoi.metrics.probabilistic.spread_skill` measures. This module
therefore computes both and refuses to emit an ensemble-derived cone when the
ensemble is underdispersed -- falling back to the climatological radii instead.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .. import config
from ..geo import haversine_nm
from ..metrics.probabilistic import ensemble_percentiles
from ..models.base import DEFAULT_LEADS

#: Product lead times. Fixed, not tunable: they are the trained models'
#: output heads (models.base.DEFAULT_LEADS), so a different list would ask
#: every checkpoint for leads it doesn't produce.
LEAD_HOURS: tuple[int, ...] = tuple(
    config.fixed(
        "inference", "products.lead_hours", list(DEFAULT_LEADS),
        "these are the trained models' output leads (models.base.DEFAULT_LEADS)",
    )
)

#: NHC-style 2/3-probability circle radii (nm) by lead time, current-season
#: Atlantic basin values (https://www.nhc.noaa.gov/aboutcone.shtml).
#:
#: NHC sizes each circle so that two-thirds of official forecast errors over the
#: previous five years fall within it, and re-derives the table annually --
#: these are the 2026 radii (based on 2021-2025 error statistics; NHC's page
#: also lists 60h, which this module's ``products.lead_hours`` does not use).
#: Read from ``configs/inference.yaml`` (``ensemble.climatological_cone_nm``).
#: Re-baseline it there every season rather than assuming it stays reasonable.
#:
#: Note for the 2026 season NHC is trialling a cone built from **ellipses** rather
#: than circles, separating the along-track (speed) and cross-track (directional)
#: error components. That is the decomposition metrics.track.cross_along_track_nm
#: already computes, so an elliptical ConeSegment -- semi-major, semi-minor and
#: orientation in place of a single radius -- is a natural extension here.
CLIMATOLOGICAL_CONE_NM: dict[int, float] = {
    int(lead): float(radius)
    for lead, radius in config.get("inference", "ensemble.climatological_cone_nm", dict).items()
}
if set(CLIMATOLOGICAL_CONE_NM) != set(LEAD_HOURS):
    raise config.ConfigError(
        "inference.yaml: ensemble.climatological_cone_nm needs exactly one radius per "
        f"product lead {list(LEAD_HOURS)}, got {sorted(CLIMATOLOGICAL_CONE_NM)}"
    )

#: Rapid intensification: >=30 kt increase in 24 h.
#:
#: Kaplan and DeMaria (2003, doi:10.1175/1520-0434(2003)018<1093:LCORIT>2.0.CO;2)
#: define RI as roughly the 95th percentile of over-water 24 h intensity changes
#: for Atlantic storms developing 1989-2000, which works out to 30 kt. It is a
#: percentile of a continuous distribution, not a physical discontinuity -- later
#: work finds no gap in the distribution near 30 kt. Treat both this and the
#: alert probability in build_products() as tunable conventions, not physics.
RI_THRESHOLD_KT: float = config.get("inference", "products.ri_threshold_kt", float)
RI_WINDOW_HOURS: int = config.get("inference", "products.ri_window_hours", int)
#: Ensemble fraction at or above which the RI flag is raised.
RI_ALERT_PROBABILITY: float = config.get("inference", "products.ri_alert_probability", float)

#: Ensemble cone radius: this percentile of member distance from the mean.
CONE_PERCENTILE: float = config.get("inference", "products.cone_percentile", float)
#: Landfall: members passing within this many nm of the coastal point.
LANDFALL_THRESHOLD_NM: float = config.get("inference", "products.landfall_threshold_nm", float)
#: Fewer members than this, and the cone falls back to climatology.
MIN_MEMBERS_FOR_ENSEMBLE_CONE: int = config.get(
    "inference", "ensemble.min_members_for_ensemble_cone", int
)
#: Below this fraction of the climatological radius at the longest lead, the
#: ensemble is judged underdispersed and the cone falls back to climatology.
UNDERDISPERSION_FRACTION: float = config.get(
    "inference", "ensemble.underdispersion_fraction", float
)


@dataclass(frozen=True, slots=True)
class EnsembleMember:
    """One member's track and intensity at a set of lead times."""

    member_id: int
    lead_hours: tuple[int, ...]
    lats: np.ndarray
    lons: np.ndarray
    winds_kt: np.ndarray

    def __post_init__(self) -> None:
        n = len(self.lead_hours)
        if not (self.lats.size == self.lons.size == self.winds_kt.size == n):
            raise ValueError("member arrays must match lead_hours length")

    def at(self, lead: int) -> tuple[float, float, float]:
        i = self.lead_hours.index(lead)
        return float(self.lats[i]), float(self.lons[i]), float(self.winds_kt[i])


@dataclass(frozen=True, slots=True)
class ConeSegment:
    lead_hours: int
    center_lat: float
    center_lon: float
    radius_nm: float
    #: "ensemble" when derived from spread, "climatology" when fallen back.
    basis: str


@dataclass(frozen=True, slots=True)
class ForecastProducts:
    cone: tuple[ConeSegment, ...]
    intensity_pdf: dict[int, dict[int, float]]
    landfall_probability: float | None
    rapid_intensification: bool
    ri_probability: float
    #: 95% Wilson interval on ``ri_probability`` (#188). ``ri_probability``
    #: is a fraction of a finite ensemble, not a known probability, and the
    #: alert threshold is a hard cut at 0.3 -- without the interval there is
    #: no way to tell "clearly above" from "we cannot resolve this".
    ri_probability_lo: float
    ri_probability_hi: float
    #: True when the interval spans ``ri_alert_threshold``, i.e. the ensemble
    #: is too small to say which side of the line this storm is on.
    ri_uncertain: bool
    ensemble_size: int
    degraded: bool = False
    notes: tuple[str, ...] = ()


def _positions(members: list[EnsembleMember], leads: tuple[int, ...]) -> np.ndarray:
    """Every member's (lat, lon) at ``leads``: ``(n_members, len(leads), 2)``.
    Distances are then taken over the whole array in one call -- one
    `haversine_nm` per member and lead was most of a cycle's product time
    (#218)."""
    return np.array([[m.at(lead)[:2] for lead in leads] for m in members], dtype=float)


def deterministic_center(members: list[EnsembleMember], lead: int) -> tuple[float, float]:
    """Ensemble-mean position at a lead time."""
    pts = _positions(members, (lead,))[:, 0]
    return float(pts[:, 0].mean()), float(pts[:, 1].mean())


def cone_radius_from_spread(
    members: list[EnsembleMember], lead: int, percentile: float = CONE_PERCENTILE
) -> float:
    """Radius containing ``percentile``% of members around the ensemble mean."""
    pts = _positions(members, (lead,))[:, 0]
    clat, clon = float(pts[:, 0].mean()), float(pts[:, 1].mean())
    dists = np.asarray(haversine_nm(clat, clon, pts[:, 0], pts[:, 1]), dtype=float)
    return float(np.percentile(dists, percentile))


def build_cone(
    members: list[EnsembleMember],
    lead_times: tuple[int, ...] | None = None,
    *,
    min_members: int = MIN_MEMBERS_FOR_ENSEMBLE_CONE,
    underdispersion_fraction: float = UNDERDISPERSION_FRACTION,
) -> tuple[tuple[ConeSegment, ...], tuple[str, ...]]:
    """Build the cone, falling back to climatology when spread is untrustworthy.

    At forecast time there is no observation to verify against, so calibration
    cannot be measured directly -- :func:`spread_skill` is the post-hoc check,
    run in verification. The real-time proxy used here is the ensemble radius
    against the climatological radius at the longest lead: an ensemble
    dramatically tighter than climatology five days out is displaying the
    underdispersion signature of a diffusion model over-anchored to its
    deterministic conditioning, and a cone drawn from it would understate risk.
    """
    if not members:
        raise ValueError("cannot build a cone from an empty ensemble")
    leads = lead_times or members[0].lead_hours
    notes: list[str] = []

    use_ensemble = len(members) >= min_members
    if not use_ensemble:
        notes.append(
            f"ensemble of {len(members)} below the {min_members}-member minimum; "
            "cone drawn from climatological radii"
        )

    if use_ensemble:
        long_lead = leads[-1]
        ensemble_radius = cone_radius_from_spread(members, long_lead)
        climo_radius = CLIMATOLOGICAL_CONE_NM.get(long_lead, _interpolate_climo(long_lead))
        if ensemble_radius < underdispersion_fraction * climo_radius:
            use_ensemble = False
            notes.append(
                f"ensemble radius at {long_lead}h ({ensemble_radius:.0f} nm) is under "
                f"{underdispersion_fraction:.0%} of climatology ({climo_radius:.0f} nm); "
                "cone drawn from climatological radii instead"
            )

    segments: list[ConeSegment] = []
    for lead in leads:
        clat, clon = deterministic_center(members, lead)
        if use_ensemble:
            radius = cone_radius_from_spread(members, lead)
            basis = "ensemble"
        else:
            radius = CLIMATOLOGICAL_CONE_NM.get(lead, _interpolate_climo(lead))
            basis = "climatology"
        segments.append(ConeSegment(lead, clat, clon, radius, basis))
    return tuple(segments), tuple(notes)


def _interpolate_climo(lead: int) -> float:
    leads = np.array(sorted(CLIMATOLOGICAL_CONE_NM))
    radii = np.array([CLIMATOLOGICAL_CONE_NM[int(k)] for k in leads], dtype=float)
    return float(np.interp(lead, leads, radii))


def intensity_pdf(
    members: list[EnsembleMember], lead_times: tuple[int, ...] | None = None
) -> dict[int, dict[int, float]]:
    """Per-lead-time intensity percentiles (10/25/50/75/90)."""
    leads = lead_times or members[0].lead_hours
    return {
        lead: ensemble_percentiles(
            np.array([m.at(lead)[2] for m in members]), percentiles=(10, 25, 50, 75, 90)
        )
        for lead in leads
    }


def landfall_probability(
    members: list[EnsembleMember],
    coastline_lat: float,
    coastline_lon: float,
    threshold_nm: float = LANDFALL_THRESHOLD_NM,
    lead: int | None = None,
) -> float:
    """Fraction of members passing within ``threshold_nm`` of a coastal point."""
    if not members:
        raise ValueError("empty ensemble")
    leads = (lead,) if lead is not None else members[0].lead_hours
    pts = _positions(members, leads)
    dists = np.asarray(
        haversine_nm(coastline_lat, coastline_lon, pts[..., 0], pts[..., 1]), dtype=float
    )
    hits = int((dists.min(axis=1) <= threshold_nm).sum())
    return hits / len(members)


def rapid_intensification_probability(
    members: list[EnsembleMember],
    *,
    threshold_kt: float = RI_THRESHOLD_KT,
    window_hours: int = RI_WINDOW_HOURS,
) -> float:
    """Fraction of members showing a >=threshold intensity gain in any
    ``window_hours`` window.

    The window has to be *exactly* ``window_hours`` long (#193). This
    previously took the first lead at or beyond ``lead_i + window_hours``,
    which is only the same thing when that lead exists -- and `DEFAULT_LEADS`
    is unevenly spaced, so at the 36 h lead it landed on 72 h and measured a
    **36-hour** gain against a threshold defined per 24 hours. A storm got
    50% more time to clear it, inflating the fraction and pushing cycles
    across `build_products`' 0.3 alert cut on the most safety-critical
    signal served, in the over-warning direction.

    Rejected alternatives, both of which look cheaper and are worse:
    interpolating a wind at ``lead_i + window_hours`` invents a value the
    model never produced, and linear interpolation cannot represent a spike
    so it understates exactly the peak rates this metric exists to catch;
    scaling the threshold to the real window length (30 kt/24 h ->
    45 kt/36 h) is a *rate* criterion, and RI is a threshold on a window --
    45 kt over 36 h need not contain 30 kt in any 24-hour sub-window.

    The cost is one unobservable slice, not a lead: with `DEFAULT_LEADS`
    every lead still contributes to some window (12->36, 24->48, 48->72,
    72->96, 96->120). Only a window *starting* at 36 h is dropped, and it
    ends at 60 h where there is no prediction at all, so it was never
    measurable.
    """
    if not members:
        raise ValueError("empty ensemble")
    count = 0
    for m in members:
        leads = np.array(m.lead_hours, dtype=float)
        winds = np.asarray(m.winds_kt, dtype=float)
        gained = False
        for i, lead_i in enumerate(leads):
            j = np.searchsorted(leads, lead_i + window_hours)
            # An exact match, not merely the next lead beyond it.
            if j >= len(leads) or leads[j] != lead_i + window_hours:
                continue
            if winds[j] - winds[i] >= threshold_kt:
                gained = True
                break
        count += int(gained)
    return count / len(members)


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion.

    Wilson rather than the textbook normal approximation because the normal
    one is worst exactly where this is used: small ``n``, and proportions
    near 0 or 1, where it happily returns bounds outside [0, 1]. Wilson stays
    inside the unit interval and keeps usable coverage at the ensemble sizes
    this system actually runs.
    """
    if n <= 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z / denom) * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, centre - half), min(1.0, centre + half))


def build_products(
    members: list[EnsembleMember],
    *,
    coastline: tuple[float, float] | None = None,
    ri_alert_threshold: float = RI_ALERT_PROBABILITY,
    degraded: bool = False,
) -> ForecastProducts:
    """Assemble the §6.1 product suite from an ensemble."""
    cone, notes = build_cone(members)
    ri_prob = rapid_intensification_probability(members)
    # The count back out of the fraction: `rapid_intensification_probability`
    # returns count/len, and the interval needs the integer it came from.
    lo, hi = wilson_interval(round(ri_prob * len(members)), len(members))
    return ForecastProducts(
        cone=cone,
        intensity_pdf=intensity_pdf(members),
        landfall_probability=(
            landfall_probability(members, *coastline) if coastline else None
        ),
        rapid_intensification=ri_prob >= ri_alert_threshold,
        ri_probability=ri_prob,
        ri_probability_lo=lo,
        ri_probability_hi=hi,
        ri_uncertain=lo < ri_alert_threshold <= hi,
        ensemble_size=len(members),
        degraded=degraded or any("climatological" in n for n in notes),
        notes=notes,
    )
