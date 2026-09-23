"""Per-lead ensemble calibration: the #10 backtest's measurement core.

Pure numpy over absolute (lat, lon, wind) ensemble members and the real
observed track -- no model, no I/O -- so the calibration logic is testable
against synthetic ensembles whose true calibration is known by construction.
`training.spread_backtest` supplies the real Anemoi-Spread members.

Reuses `metrics.probabilistic`'s `rank_histogram`/`spread_skill` unchanged.
Both need one scalar per member and one per observation, so track position
is decomposed into along-track and cross-track components
(`geo.cross_along_track_nm`, the decomposition `inference.postprocess`'s
module docstring already names). Each member's error is taken relative to
the observed position, so the truth sits at exactly (0, 0): "where does the
truth rank among the members" becomes "where does 0 rank among each
member's projected error". Intensity is a scalar already (``wind_kt``).

**The projection frame is the forecast's own motion (ensemble-mean track),
not the observed motion** -- a real flaw caught by this module's own test
against a synthetic ensemble calibrated by construction. An observed-motion
frame is computed *from the verifying observation*, so the truth's own
error partly defines the axes it's ranked along: it read a calibrated
ensemble as cross-track *overdispersed* (ratio 1.28). A calibration frame
must be independent of the thing being ranked. The ensemble-mean motion is
(and still means "along-track" physically, including for a recurving storm,
where a fixed forecast-time heading would not). The observed motion is
still used where it belongs: labeling what actually happened
(`recurving_cases`).

Read the rank histogram with `rank_histogram`'s own Hamill (2001) caveat in
hand: a U shape doesn't uniquely mean underdispersion. That's why every
result carries the spread-skill ratio alongside it, and why cases can be
stratified by regime (``recurving``) before concluding anything.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..geo import bearing_deg, cross_along_track_nm
from .probabilistic import SpreadSkill, rank_histogram, spread_skill

#: The three scalar quantities calibration is measured on.
QUANTITIES: tuple[str, ...] = ("along_track_nm", "cross_track_nm", "wind_kt")


@dataclass(frozen=True, slots=True)
class LeadCalibration:
    lead_hours: int
    quantity: str
    n_cases: int
    rank_counts: tuple[int, ...]
    spread_skill: SpreadSkill

    @property
    def ratio(self) -> float:
        return self.spread_skill.ratio

    @property
    def verdict(self) -> str:
        if self.spread_skill.underdispersed:
            return "underdispersed"
        if self.spread_skill.overdispersed:
            return "overdispersed"
        return "calibrated"

    @property
    def outer_rank_fraction(self) -> float:
        """Fraction of cases where the truth fell outside every member (the
        two extreme bins). For a calibrated M-member ensemble this is about
        2/(M+1); much higher is the U-shape underdispersion looks like."""
        counts = np.asarray(self.rank_counts)
        total = counts.sum()
        return float((counts[0] + counts[-1]) / total) if total else float("nan")

    def to_dict(self) -> dict:
        return {
            "lead_hours": self.lead_hours,
            "quantity": self.quantity,
            "n_cases": self.n_cases,
            "rank_counts": list(self.rank_counts),
            "spread": self.spread_skill.spread,
            "rmse": self.spread_skill.skill,
            "ratio": self.ratio,
            "outer_rank_fraction": self.outer_rank_fraction,
            "verdict": self.verdict,
        }


def observed_motion_bearings(true_abs: np.ndarray, base: np.ndarray) -> np.ndarray:
    """Observed storm-motion bearing arriving at each lead: from the previous
    lead's real position (or the base fix, for the first lead) to this one.
    Shape (n_cases, n_leads). ``true_abs`` is (n_cases, n_leads, 3) absolute
    (lat, lon, wind); ``base`` is (n_cases, 2) (lat, lon)."""
    n_cases, n_leads, _ = true_abs.shape
    out = np.zeros((n_cases, n_leads))
    for ci in range(n_cases):
        prev_lat, prev_lon = base[ci]
        for li in range(n_leads):
            lat, lon = true_abs[ci, li, 0], true_abs[ci, li, 1]
            out[ci, li] = bearing_deg(prev_lat, prev_lon, lat, lon)
            prev_lat, prev_lon = lat, lon
    return out


def forecast_motion_bearings(members_abs: np.ndarray, base: np.ndarray) -> np.ndarray:
    """The forecast's own motion arriving at each lead: bearing from the
    ensemble-mean position at the previous lead (or the base fix) to the
    ensemble-mean position at this lead, (n_cases, n_leads). Uses no
    observation -- see the module docstring for why that matters. Plain
    lat/lon averaging, the same as `inference.postprocess.deterministic_
    center` (fine for ensemble spreads far from the antimeridian)."""
    mean_track = members_abs[..., :2].mean(axis=1)  # (n_cases, n_leads, 2)
    padded = np.concatenate([np.zeros_like(mean_track[:, :1]), mean_track], axis=1)
    padded[:, 0] = base
    n_cases, n_leads = mean_track.shape[:2]
    out = np.zeros((n_cases, n_leads))
    for ci in range(n_cases):
        for li in range(n_leads):
            out[ci, li] = bearing_deg(*padded[ci, li], *padded[ci, li + 1])
    return out


def recurving_cases(true_abs: np.ndarray, base: np.ndarray, base_bearing: np.ndarray) -> np.ndarray:
    """(n_cases, n_leads) bool: the storm was moving with a westward
    component at forecast time, and the observed motion arriving at this
    lead has an eastward component -- it recurved into the westerlies within
    the forecast window. The bimodal "out to sea or not" regime #10 is
    specifically about; ``base_bearing`` is the real motion at forecast time.
    """
    bearings = observed_motion_bearings(true_abs, base)
    westward_at_start = np.sin(np.radians(base_bearing)) < 0
    eastward_at_lead = np.sin(np.radians(bearings)) > 0
    return westward_at_start[:, None] & eastward_at_lead


def _scalar_errors(
    members_abs: np.ndarray, true_abs: np.ndarray, bearings: np.ndarray, ci: int, li: int,
) -> dict[str, tuple[np.ndarray, float]]:
    """Each quantity's per-member values and the observation to rank them
    against, for one case at one lead."""
    obs_lat, obs_lon, obs_wind = true_abs[ci, li]
    cross = np.empty(members_abs.shape[1])
    along = np.empty(members_abs.shape[1])
    for mi, (lat, lon, _wind) in enumerate(members_abs[ci, :, li]):
        cross[mi], along[mi] = cross_along_track_nm(lat, lon, obs_lat, obs_lon, bearings[ci, li])
    return {
        "along_track_nm": (along, 0.0),
        "cross_track_nm": (cross, 0.0),
        "wind_kt": (members_abs[ci, :, li, 2].astype(float), float(obs_wind)),
    }


def calibrate(
    members_abs: np.ndarray,
    true_abs: np.ndarray,
    mask: np.ndarray,
    base: np.ndarray,
    lead_hours: tuple[int, ...],
    *,
    case_filter: np.ndarray | None = None,
    min_cases: int = 10,
) -> list[LeadCalibration]:
    """Rank histogram + spread-skill per lead, per `QUANTITIES`.

    ``members_abs`` is (n_cases, n_members, n_leads, 3) absolute (lat, lon,
    wind); ``true_abs`` (n_cases, n_leads, 3); ``mask`` (n_cases, n_leads)
    marks leads with a real verifying observation (a short real track has
    none past its own end -- the same mask training uses); ``base`` is
    (n_cases, 2). ``case_filter`` is an optional (n_cases, n_leads) bool to
    stratify (e.g. `recurving_cases`). A lead with fewer than ``min_cases``
    verifying cases is omitted rather than reported as a noisy estimate --
    the same restraint `monitoring.skew.SkewMonitor.report` uses.
    """
    members_abs = np.asarray(members_abs, dtype=float)
    true_abs = np.asarray(true_abs, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    if members_abs.ndim != 4 or members_abs.shape[-1] != 3:
        raise ValueError("members_abs must be (n_cases, n_members, n_leads, 3)")
    if members_abs.shape[1] < 2:
        raise ValueError("calibration needs at least 2 members")
    if true_abs.shape != (members_abs.shape[0], members_abs.shape[2], 3):
        raise ValueError("true_abs must be (n_cases, n_leads, 3) matching members_abs")
    if len(lead_hours) != members_abs.shape[2]:
        raise ValueError("lead_hours must have one entry per lead")

    selected = mask if case_filter is None else (mask & np.asarray(case_filter, dtype=bool))
    bearings = forecast_motion_bearings(members_abs, np.asarray(base, dtype=float))

    results: list[LeadCalibration] = []
    for li, lead in enumerate(lead_hours):
        cases = np.flatnonzero(selected[:, li])
        if len(cases) < min_cases:
            continue
        per_quantity: dict[str, tuple[list, list]] = {q: ([], []) for q in QUANTITIES}
        for ci in cases:
            for quantity, (values, obs) in _scalar_errors(
                members_abs, true_abs, bearings, ci, li,
            ).items():
                per_quantity[quantity][0].append(values)
                per_quantity[quantity][1].append(obs)
        for quantity in QUANTITIES:
            member_rows = np.asarray(per_quantity[quantity][0])
            observations = np.asarray(per_quantity[quantity][1])
            results.append(
                LeadCalibration(
                    lead_hours=int(lead),
                    quantity=quantity,
                    n_cases=len(cases),
                    rank_counts=tuple(int(c) for c in rank_histogram(member_rows, observations)),
                    spread_skill=spread_skill(member_rows, observations),
                )
            )
    return results
