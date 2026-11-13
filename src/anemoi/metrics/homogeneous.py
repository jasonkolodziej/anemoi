"""Homogeneous comparison of several forecasts on the same cases.

Two mean errors are comparable only if they are means over the same cases:
a technique that issues no forecast for the hard cases looks better for
that alone. NHC's verification therefore compares techniques on a
*homogeneous* sample, the cases every one of them forecast, and so does
this module.

`score_homogeneous` takes each member's forecasts for one list of cases
(`Member`: absolute positions and winds, NaN where it has none), the
truth, and the cases that are eligible, and returns one `HomogeneousRow`
per basin, lead and quantity:

* **The sample.** For a basin, lead and quantity (track, intensity) a case
  counts when it is eligible and every compared member has that quantity
  for it. Track and intensity are separate samples, so a technique with no
  wind forecast does not shrink the intensity comparison; it is simply not
  an intensity member. A member with no forecast at all in a basin is left
  out of that basin's comparison and named in ``absent``.
* **The error.** `metrics.track.verify` over `metrics.basin.absolute_pairs`:
  the code that computes every registered ``{basin}/track_error_{lead}h_nm``,
  so a number here is the registry's statistic on a different sample and
  nothing else differs.
* **How much to trust it.** Six-hourly cases of one storm are not
  independent, so each row gives the number of storms, the largest storm's
  share of the cases, and each member's mean over storms beside its mean
  over cases. Against each reference member it gives the paired mean
  difference with a storm-block bootstrap interval, the beat rate and a
  Diebold-Mariano p-value on one case per storm
  (`metrics.track.aggregate_by_storm`). Below `MIN_STORMS` storms a row
  keeps its means and drops skill, beat rate, interval and p-value: it
  describes those storms and supports no claim beyond them.

Basins are never pooled. NHC does not pool them, and a pooled row is
undefined when a member is absent from one basin.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace

import numpy as np

from ..data.atcf import storm_basin
from ..geo import haversine_nm
from .basin import absolute_pairs
from .track import aggregate_by_storm, beat_rate, diebold_mariano, verify

TRACK = "track_nm"
INTENSITY = "intensity_kt"
QUANTITIES: tuple[str, ...] = (TRACK, INTENSITY)

#: Fewest storms a row needs before anything is inferred from it: the floor
#: `metrics.track.diebold_mariano` puts on independent cases.
MIN_STORMS = 8

#: An interval's endpoint is itself estimated from the resamples, and the
#: decision rules read whether it excludes zero. At 2,000 the 97.5% point
#: moved by about 0.2 nm between seeds on the 2024 Atlantic 48 h sample
#: (15 storms), enough to put an endpoint on either side of zero; at 10,000
#: it moves by under 0.1 nm, for a few milliseconds a comparison.
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20260806


@dataclass(frozen=True, slots=True)
class Member:
    """One forecast source's forecasts for a list of cases.

    ``pred_abs`` is ``(n_cases, n_leads, 3)`` absolute (lat, lon, wind_kt),
    NaN wherever the member has no forecast: the whole point for a case it
    did not forecast, the wind alone for a track-only technique.
    """

    name: str
    #: What kind of source it is (``official``, ``early``, ``late``,
    #: ``baseline``, ``model``...): carried into reports, not used here.
    kind: str
    pred_abs: np.ndarray
    description: str = ""

    @property
    def has_track(self) -> np.ndarray:
        return np.isfinite(self.pred_abs[..., 0]) & np.isfinite(self.pred_abs[..., 1])

    @property
    def has_intensity(self) -> np.ndarray:
        return np.isfinite(self.pred_abs[..., 2])

    def has(self, quantity: str) -> np.ndarray:
        return self.has_track if quantity == TRACK else self.has_intensity


def case_errors(member: Member, obs_abs: np.ndarray, quantity: str) -> np.ndarray:
    """Each case's error, ``(n_cases, n_leads)``, NaN where the member has
    no forecast: great-circle distance in nm (`geo.haversine_nm`, as
    `metrics.track.verify`), or the absolute wind error in kt."""
    pred = member.pred_abs
    if quantity == TRACK:
        return np.asarray(
            haversine_nm(obs_abs[..., 0], obs_abs[..., 1], pred[..., 0], pred[..., 1]),
            dtype=float,
        )
    return np.abs(pred[..., 2] - obs_abs[..., 2])


@dataclass(frozen=True, slots=True)
class MemberScore:
    """One member on one row's homogeneous sample."""

    #: Mean over cases: the registry's statistic.
    mean_error: float
    #: Mean of the storms' own means: each storm counts once.
    storm_mean_error: float
    #: Mean signed wind error (positive: too strong). Intensity rows only.
    bias: float | None
    #: Percent improvement on the skill baseline; None without one, or
    #: with too few storms.
    skill_pct: float | None
    #: This member's own cases among the eligible ones, and its mean error
    #: on them: what it scores when nothing else has to exist.
    n_available: int
    available_mean_error: float | None

    def to_dict(self) -> dict:
        return {
            "mean_error": self.mean_error,
            "storm_mean_error": self.storm_mean_error,
            "bias": self.bias,
            "skill_pct": self.skill_pct,
            "n_available": self.n_available,
            "available_mean_error": self.available_mean_error,
        }


@dataclass(frozen=True, slots=True)
class PairedComparison:
    """One member against one reference member.

    ``mean_diff`` to ``dm_p_value`` are on the row's homogeneous sample;
    ``pairwise_*`` are on the cases the two alone share, which shows what
    requiring every other member cost.
    """

    #: Member minus reference, mean over cases: negative favours the member.
    mean_diff: float
    #: 95% interval of ``mean_diff`` from resampling whole storms.
    ci95: tuple[float, float] | None
    #: Fraction of cases the member's error is strictly smaller.
    beat_rate: float | None
    #: Diebold-Mariano p-value on absolute-error loss, one case per storm.
    dm_p_value: float | None
    pairwise_n_cases: int
    pairwise_n_storms: int
    pairwise_mean_error: float | None
    pairwise_reference_mean_error: float | None

    def to_dict(self) -> dict:
        return {
            "mean_diff": self.mean_diff,
            "ci95": None if self.ci95 is None else list(self.ci95),
            "beat_rate": self.beat_rate,
            "dm_p_value": self.dm_p_value,
            "pairwise_n_cases": self.pairwise_n_cases,
            "pairwise_n_storms": self.pairwise_n_storms,
            "pairwise_mean_error": self.pairwise_mean_error,
            "pairwise_reference_mean_error": self.pairwise_reference_mean_error,
        }


@dataclass(frozen=True, slots=True)
class HomogeneousRow:
    """Every compared member's error for one basin, lead and quantity."""

    sample: str
    basin: str
    lead_hours: int
    quantity: str
    #: Cases every compared member forecast, and the storms they come from.
    n_cases: int
    n_storms: int
    #: Eligible cases, before any member had to exist.
    n_eligible: int
    #: The storm with the most cases, and its share of them.
    largest_storm: str | None
    largest_storm_share: float | None
    #: The compared member with the fewest cases of its own.
    limited_by: str | None
    #: Members with this quantity elsewhere and no forecast in this basin.
    absent: tuple[str, ...]
    #: Fewer than `MIN_STORMS` storms: means only.
    too_few_storms: bool
    scores: dict[str, MemberScore] = field(default_factory=dict)
    #: member -> reference -> comparison, on this row's cases.
    paired: dict[str, dict[str, PairedComparison]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "sample": self.sample,
            "basin": self.basin,
            "lead_hours": self.lead_hours,
            "quantity": self.quantity,
            "n_cases": self.n_cases,
            "n_storms": self.n_storms,
            "n_eligible": self.n_eligible,
            "largest_storm": self.largest_storm,
            "largest_storm_share": self.largest_storm_share,
            "limited_by": self.limited_by,
            "absent": list(self.absent),
            "too_few_storms": self.too_few_storms,
            "scores": {name: score.to_dict() for name, score in self.scores.items()},
            "paired": {
                name: {ref: cmp.to_dict() for ref, cmp in refs.items()}
                for name, refs in self.paired.items()
            },
        }


def storm_block_interval(
    storm_ids: np.ndarray, diffs: np.ndarray,
    *, n_resamples: int = BOOTSTRAP_RESAMPLES, seed: int = BOOTSTRAP_SEED,
) -> tuple[float, float]:
    """95% bootstrap interval of the mean of ``diffs``, resampling whole
    storms with replacement: a storm's cases stay together, because they
    share its track and its synoptic setting and are not independent
    draws. Each resample's mean is over its cases, as the point estimate is.
    """
    ids = np.asarray(storm_ids)
    diffs = np.asarray(diffs, dtype=float)
    if ids.shape != diffs.shape or diffs.size == 0:
        raise ValueError("storm_ids and diffs must be the same non-empty shape")
    _unique, inverse = np.unique(ids, return_inverse=True)
    sums = np.bincount(inverse, weights=diffs)
    counts = np.bincount(inverse).astype(float)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(sums), size=(n_resamples, len(sums)))
    means = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    low, high = np.percentile(means, [2.5, 97.5])
    return float(low), float(high)


def _mean(values: np.ndarray) -> float | None:
    return float(values.mean()) if values.size else None


def _paired(
    ids: np.ndarray, member_err: np.ndarray, reference_err: np.ndarray, *,
    homogeneous: np.ndarray, eligible: np.ndarray, too_few: bool,
) -> PairedComparison | None:
    """``member_err``/``reference_err`` are one lead's errors for a basin's
    cases; ``homogeneous`` and ``eligible`` select among them."""
    both = eligible & np.isfinite(member_err) & np.isfinite(reference_err)
    if not homogeneous.any():
        return None
    cand, base, storms = member_err[homogeneous], reference_err[homogeneous], ids[homogeneous]
    ci95 = rate = p_value = None
    if not too_few:
        ci95 = storm_block_interval(storms, cand - base)
        rate = beat_rate(cand, base)
        _stat, p_value = diebold_mariano(*aggregate_by_storm(storms, cand, base), power=1)
    return PairedComparison(
        mean_diff=float((cand - base).mean()),
        ci95=ci95,
        beat_rate=rate,
        dm_p_value=p_value,
        pairwise_n_cases=int(both.sum()),
        pairwise_n_storms=len(set(ids[both].tolist())),
        pairwise_mean_error=_mean(member_err[both]),
        pairwise_reference_mean_error=_mean(reference_err[both]),
    )


def compared_members(
    members: Sequence[Member], eligible: np.ndarray, in_basin: np.ndarray, quantity: str,
) -> tuple[list[Member], tuple[str, ...]]:
    """The members compared for ``quantity`` in one basin (``in_basin``
    selects its cases), and the names of those left out as absent: a
    member is in a quantity's comparison if it forecasts the quantity for
    any eligible case, and absent from a basin where it does so for none."""
    forecasting = [m for m in members if (m.has(quantity) & eligible).any()]
    present = [m for m in forecasting if (m.has(quantity) & eligible)[in_basin].any()]
    absent = tuple(m.name for m in forecasting if m not in present)
    return present, absent


def homogeneous_mask(
    members: Sequence[Member], eligible: np.ndarray, storm_ids: Sequence[str], quantity: str,
) -> np.ndarray:
    """``(n_cases, n_leads)``: the eligible cases that every member compared
    in the case's own basin forecast ``quantity`` for. All False in a basin
    where no member forecasts it."""
    eligible = np.asarray(eligible, dtype=bool)
    basins = np.array([storm_basin(s) for s in storm_ids])
    out = np.zeros_like(eligible)
    for basin in set(basins.tolist()):
        in_basin = basins == basin
        present, _absent = compared_members(members, eligible, in_basin, quantity)
        if not present:
            continue
        mask = eligible.copy()
        for member in present:
            mask &= member.has(quantity)
        out[in_basin] = mask[in_basin]
    return out


def score_homogeneous(
    members: Sequence[Member],
    obs_abs: np.ndarray,
    eligible: np.ndarray,
    storm_ids: Sequence[str],
    lead_hours: Sequence[int],
    *,
    sample: str = "",
    references: Sequence[str] = (),
    skill_baseline: str | None = None,
) -> list[HomogeneousRow]:
    """Score ``members`` against ``obs_abs`` on the cases of ``eligible``
    that all of them forecast. See the module docstring for the rules.

    ``obs_abs`` is ``(n_cases, n_leads, 3)`` absolute (lat, lon, wind_kt);
    ``eligible`` is ``(n_cases, n_leads)``; ``storm_ids`` names each
    case's storm. ``references`` are the members every other is compared
    with pairwise; ``skill_baseline`` is the member skill is measured
    against (NHC uses its climatology-and-persistence model). Rows come
    out by basin, then quantity, then lead.
    """
    names = [m.name for m in members]
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate member names: {names}")
    eligible = np.asarray(eligible, dtype=bool)
    n_cases, n_leads = eligible.shape
    if len(storm_ids) != n_cases or len(lead_hours) != n_leads:
        raise ValueError("storm_ids and lead_hours must match eligible's shape")
    for member in members:
        if member.pred_abs.shape != obs_abs.shape:
            raise ValueError(f"{member.name}: forecasts are not shaped like the truth")

    ids = np.asarray(storm_ids)
    basins = np.array([storm_basin(s) for s in storm_ids])
    masks = {q: homogeneous_mask(members, eligible, storm_ids, q) for q in QUANTITIES}
    all_errors = {(m.name, q): case_errors(m, obs_abs, q) for m in members for q in QUANTITIES}
    rows: list[HomogeneousRow] = []
    for basin in sorted(set(basins.tolist())):
        sel = basins == basin
        basin_ids, basin_obs, basin_eligible = ids[sel], obs_abs[sel], eligible[sel]
        for quantity in QUANTITIES:
            compared, absent = compared_members(members, eligible, sel, quantity)
            has = {m.name: m.has(quantity)[sel] & basin_eligible for m in compared}
            homogeneous = masks[quantity][sel]
            errors = {m.name: all_errors[m.name, quantity][sel] for m in compared}
            # The registry's own statistic, for every lead at once.
            stats = {
                m.name: verify(
                    absolute_pairs(m.pred_abs[sel], basin_obs, homogeneous, lead_hours)
                )
                for m in compared
            } if compared else {}
            for li, lead in enumerate(lead_hours):
                hom = homogeneous[:, li] if compared else np.zeros(sel.sum(), dtype=bool)
                storms = basin_ids[hom]
                n = int(hom.sum())
                unique, counts = np.unique(storms, return_counts=True)
                too_few = len(unique) < MIN_STORMS
                available = {m.name: int(has[m.name][:, li].sum()) for m in compared}
                row = HomogeneousRow(
                    sample=sample, basin=basin, lead_hours=int(lead), quantity=quantity,
                    n_cases=n, n_storms=len(unique), n_eligible=int(basin_eligible[:, li].sum()),
                    largest_storm=str(unique[counts.argmax()]) if n else None,
                    largest_storm_share=float(counts.max() / n) if n else None,
                    limited_by=_limiting(available, int(basin_eligible[:, li].sum())),
                    absent=absent, too_few_storms=too_few,
                )
                rows.append(row)
                if n == 0:
                    continue
                for member in compared:
                    err = errors[member.name][:, li]
                    lead_stats = stats[member.name][lead]
                    by_storm, _ = aggregate_by_storm(storms, err[hom], err[hom])
                    own = has[member.name][:, li]
                    row.scores[member.name] = MemberScore(
                        mean_error=(
                            lead_stats.track_mae_nm if quantity == TRACK
                            else lead_stats.intensity_mae_kt
                        ),
                        storm_mean_error=float(by_storm.mean()),
                        bias=lead_stats.intensity_bias_kt if quantity == INTENSITY else None,
                        skill_pct=None,
                        n_available=available[member.name],
                        available_mean_error=_mean(err[own]),
                    )
                if skill_baseline in row.scores and not too_few:
                    baseline = row.scores[skill_baseline].mean_error
                    for name, score in row.scores.items():
                        if baseline > 0.0:
                            row.scores[name] = replace(
                                score, skill_pct=100.0 * (1.0 - score.mean_error / baseline),
                            )
                for reference in references:
                    if reference not in errors:
                        continue
                    for member in compared:
                        if member.name == reference:
                            continue
                        comparison = _paired(
                            basin_ids, errors[member.name][:, li], errors[reference][:, li],
                            homogeneous=hom, eligible=basin_eligible[:, li], too_few=too_few,
                        )
                        if comparison is not None:
                            row.paired.setdefault(member.name, {})[reference] = comparison
    return rows


def _limiting(available: dict[str, int], n_eligible: int) -> str | None:
    """The member with the fewest cases of its own, or None when every
    member has every eligible case."""
    if not available:
        return None
    name = min(available, key=available.get)
    return name if available[name] < n_eligible else None
