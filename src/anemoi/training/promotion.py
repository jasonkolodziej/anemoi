"""Promotion gates.

Scope v2.1 §5.3 Stage 6, revised. Two changes from v2, both about not lying to
ourselves:

1. **Promotion is decided on validation, not test.** v2 promoted on test metrics.
   Selecting repeatedly against a held-out set converts it into a validation set
   and the "unbiased evaluation vs NHC consensus" it was reserved for stops
   being unbiased. The test set is touched on an explicit budget
   (:class:`TestSetBudget`) and never as a promotion criterion.
2. **Metrics must come from the operational flavor.** A candidate evaluated on
   ERA5 inputs is not evidence about production behaviour (§4.6.1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from .. import config
from ..data.sources import Flavor
from ..metrics.basin import basin_value, scored_basins, verified_basins
from .curriculum import CurriculumRun, assert_deployable


class PromotionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MetricSet:
    """Evaluation results for one candidate on one split."""

    split: str
    flavor: Flavor
    values: dict[str, float]

    def __post_init__(self) -> None:
        if self.split not in {"train", "val", "test"}:
            raise ValueError(f"unknown split {self.split!r}")
        if not self.values:
            raise ValueError("empty metric set")

    def get(self, key: str) -> float:
        try:
            return self.values[key]
        except KeyError as exc:
            raise PromotionError(f"metric {key!r} was not computed") from exc


@dataclass(frozen=True, slots=True)
class Threshold:
    """One promotion criterion."""

    metric: str
    limit: float
    #: True when lower values are better (errors); False for rates.
    lower_is_better: bool = True

    def passes(self, value: float) -> bool:
        return value <= self.limit if self.lower_is_better else value >= self.limit

    def describe(self, value: float) -> str:
        op = "<=" if self.lower_is_better else ">="
        verdict = "pass" if self.passes(value) else "FAIL"
        return f"{self.metric}={value:.3f} {op} {self.limit:.3f} [{verdict}]"


#: Appendix B production thresholds, split into separate track and intensity
#: tables rather than one shared structure. Intensity skill has improved far
#: more slowly than track skill (Emanuel and Zhang 2016,
#: doi:10.1175/JAS-D-16-0100.1; DeMaria et al. 2014,
#: doi:10.1175/BAMS-D-12-00240.1), so a beat rate or absolute limit on
#: intensity is a claim about a nearly static baseline near an intrinsic
#: predictability limit, while the same kind of number on track is a claim
#: about a rapidly improving one. They are not equivalent achievements, they
#: should not be re-derived on the same schedule, and keeping them in separate
#: tables is what makes re-deriving one without touching the other possible.
#:
#: The beat-rate gate is the real claim in both tables -- it is measured
#: against the live baseline, not a number written down once and trusted
#: forever. The absolute limits below are a backstop against a badly broken
#: candidate, not a claim of parity with an operational center that has
#: decades of consensus guidance behind it.
#: See https://www.nhc.noaa.gov/verification/

#: NHC's official GPRA performance-measures table
#: (https://www.nhc.noaa.gov/verification/pdfs/GPRA_history.pdf) is the
#: current verification source for the 48 h numbers below: realized 48 h
#: Atlantic track error was 45.4 n mi in 2024 and 53.4 n mi in 2025 (NOAA's
#: own 2026 GPRA target: 51.0 n mi); realized 48 h intensity error was 11.4 kt
#: in 2024 and 13.7 kt in 2025 (2026 target: 10.0 kt) -- 2025 intensity error
#: was elevated by an unusually difficult season (NHC's 2025 verification
#: preview: storms "about 50% harder to predict than average"), not a skill
#: regression.
#:
#: track_error_48h_nm re-baselined: 90.0 -> 70.0, roughly 1.4x the 2026 GPRA
#: target rather than roughly 1.8x -- enough backstop margin not to gate a
#: competitive candidate on a bad case, not so loose it admits a system
#: roughly twice as bad as the incumbent, which is what 90.0 nm did.
#: intensity_error_48h_kt is left unchanged: 15.0 kt already sits close to
#: (just above) the worse of the two realized years above, unlike the track
#: number it was never the badly-miscalibrated one.
#:
#: track_error_72h_nm / track_error_120h_nm / intensity_error_72h_kt remain
#: unrederived -- the GPRA table only publishes the 48 h figure, and no other
#: lead time here has a verified current-season source behind it yet. Do not
#: extrapolate a lead-time curve from a single verified point; pull the
#: lead-time breakdown from the full spring Verification Report instead.
#:
#: The values live in monitoring.yaml ``promotion.thresholds``; an
#: ``intensity_*`` metric goes in the intensity table, anything else in track.
def _thresholds() -> tuple[Threshold, ...]:
    out = []
    for metric in config.get("monitoring", "promotion.thresholds", dict):
        out.append(
            Threshold(
                metric,
                config.get("monitoring", f"promotion.thresholds.{metric}.limit", float),
                lower_is_better=config.get(
                    "monitoring", f"promotion.thresholds.{metric}.lower_is_better", bool
                ),
            )
        )
    return tuple(out)


_ALL_THRESHOLDS = _thresholds()
TRACK_THRESHOLDS: tuple[Threshold, ...] = tuple(
    t for t in _ALL_THRESHOLDS if not t.metric.startswith("intensity_")
)
INTENSITY_THRESHOLDS: tuple[Threshold, ...] = tuple(
    t for t in _ALL_THRESHOLDS if t.metric.startswith("intensity_")
)
DEFAULT_THRESHOLDS: tuple[Threshold, ...] = TRACK_THRESHOLDS + INTENSITY_THRESHOLDS

config.fixed(
    "monitoring", "promotion.split", "val",
    "promotion is decided on validation; the test set is never a criterion (§5.3)",
)
config.fixed(
    "monitoring", "promotion.flavor", Flavor.GDAS_FINETUNE.value,
    "only a model fine-tuned on the operational flavor can be promoted (§4.6.1)",
)
PRIMARY_METRIC: str = config.get("monitoring", "promotion.primary_metric", str)
REQUIRE_MANUAL_GATE: bool = config.get("monitoring", "promotion.require_manual_gate", bool)
#: The basin a candidate is compared with the incumbent on, and the
#: thresholds are read on (docs/multi_basin.md): one model serves every
#: basin, and an error over a different mix of basins isn't comparable.
REFERENCE_BASIN: str = config.get("monitoring", "promotion.reference_basin", str)
#: How much worse on the reference basin a candidate may be when it is
#: verified in a basin the incumbent isn't, as a fraction.
NEW_BASIN_TOLERANCE: float = config.get("monitoring", "promotion.new_basin_tolerance", float)
if not 0.0 <= NEW_BASIN_TOLERANCE < 1.0:
    raise config.ConfigError(
        "monitoring.yaml: promotion.new_basin_tolerance must be a fraction in [0, 1), "
        f"got {NEW_BASIN_TOLERANCE}"
    )


def reference_value(values: dict[str, float], metric: str, basin: str) -> float | None:
    """``metric`` on ``basin``'s storms alone when the run scored basins
    separately -- ``None`` if it has none there, never another basin's
    number -- else its overall value, which, for a run from before basins
    were scored separately, *is* the reference basin: every one of those
    trained and validated on the Atlantic alone."""
    if scored_basins(values):
        return basin_value(values, basin, metric)
    return values.get(metric)


@dataclass(frozen=True, slots=True)
class PromotionDecision:
    model_name: str
    promote_to_staging: bool
    promote_to_production: bool
    reasons: tuple[str, ...]

    @property
    def blocked(self) -> bool:
        return not self.promote_to_staging


def evaluate_promotion(
    model_name: str,
    run: CurriculumRun,
    val_metrics: MetricSet,
    *,
    incumbent_val_metrics: MetricSet | None = None,
    thresholds: tuple[Threshold, ...] = DEFAULT_THRESHOLDS,
    primary_metric: str = PRIMARY_METRIC,
    require_manual_gate: bool = REQUIRE_MANUAL_GATE,
    reference_basin: str = REFERENCE_BASIN,
    new_basin_tolerance: float = NEW_BASIN_TOLERANCE,
) -> PromotionDecision:
    """Decide staging and production promotion for a candidate.

    Staging requires the candidate to beat the incumbent on ``primary_metric``.
    Production additionally requires every threshold to pass -- and, unless
    ``require_manual_gate`` is cleared, a human. §5.3 kept a manual gate on
    production and this preserves it: an automated pipeline that can put a model
    in front of an emergency manager without anyone looking at it is a hazard,
    not a feature.

    One model serves every basin (docs/multi_basin.md), so for a candidate
    that scored basins separately (`metrics.basin`):

    * the comparison with the incumbent, and the thresholds, are read on
      ``reference_basin``'s storms alone (`reference_value`);
    * it must stay verified -- better than persistence -- in every basin
      the incumbent is verified in. One that isn't would quietly take a
      basin out of distribution;
    * if it is verified in a basin the incumbent isn't, it may be up to
      ``new_basin_tolerance`` worse on the reference basin rather than
      having to beat the incumbent outright.
    """
    reasons: list[str] = []

    assert_deployable(run)

    if val_metrics.split != "val":
        raise PromotionError(
            f"promotion must be decided on the validation split, got {val_metrics.split!r} "
            "(Scope v2.1 §5.3: the test set is not a promotion criterion)"
        )
    if val_metrics.flavor is not Flavor.GDAS_FINETUNE:
        raise PromotionError(
            f"promotion metrics have flavor {val_metrics.flavor.value}; only "
            "operational-flavor evaluation gates promotion (§4.6.1)"
        )

    candidate_primary = val_metrics.values.get(primary_metric)
    if candidate_primary is not None and not math.isfinite(candidate_primary):
        # A real, previously-documented gap (wiki Training-Architecture: NaN
        # CNN/Transformer/GNN/diffusion/fusion runs auto-staged): with no
        # incumbent, `beats_incumbent` used to be True unconditionally, so a
        # candidate with a NaN/inf primary metric reached staging.
        beats_incumbent = False
        reasons.append(f"{primary_metric}: candidate is non-finite ({candidate_primary}) [FAIL]")
    elif incumbent_val_metrics is None:
        beats_incumbent = True
        reasons.append("no incumbent; candidate is the first registered version")
    else:
        # `.get` first: a metric that was never computed is an error, as before.
        val_metrics.get(primary_metric)
        incumbent_val_metrics.get(primary_metric)
        cand = reference_value(val_metrics.values, primary_metric, reference_basin)
        inc = reference_value(incumbent_val_metrics.values, primary_metric, reference_basin)
        if cand is None or inc is None:
            # Scored by basin, but no reference-basin storms to compare on:
            # nothing to promote on, never another basin's number.
            beats_incumbent = False
            missing = "candidate" if cand is None else "incumbent"
            reasons.append(
                f"{primary_metric} ({reference_basin}): the {missing} has no "
                f"{reference_basin} validation storms to compare on [FAIL]"
            )
        else:
            by_basin = bool(scored_basins(val_metrics.values))
            where = f"{primary_metric} ({reference_basin})" if by_basin else primary_metric

            allowed = 0.0
            dropped: list[str] = []
            if by_basin:
                cand_verified = set(verified_basins(val_metrics.values, primary_metric))
                # An incumbent from before basins were scored separately was
                # served as in distribution for the reference basin alone.
                inc_verified = (
                    set(verified_basins(incumbent_val_metrics.values, primary_metric))
                    if scored_basins(incumbent_val_metrics.values)
                    else {reference_basin}
                )
                dropped = sorted(inc_verified - cand_verified)
                added = sorted(cand_verified - inc_verified)
                if dropped:
                    reasons.append(
                        f"no longer better than persistence in {dropped}, "
                        "where the incumbent is [FAIL]"
                    )
                elif added:
                    allowed = new_basin_tolerance
                    reasons.append(
                        f"newly verified in {added}: may be up to {allowed:.0%} worse on "
                        f"{reference_basin}"
                    )

            beats_incumbent = not dropped and (
                cand <= inc * (1.0 + allowed) if allowed else cand < inc
            )
            if allowed and inc <= cand <= inc * (1.0 + allowed):
                verdict = "within the allowance"
            else:
                verdict = "better" if cand < inc else "not better"
            reasons.append(f"{where}: candidate {cand:.2f} vs incumbent {inc:.2f} [{verdict}]")

    threshold_results = []
    for th in thresholds:
        value = reference_value(val_metrics.values, th.metric, reference_basin)
        if value is None:
            reasons.append(f"{th.metric}: missing [FAIL]")
            threshold_results.append(False)
            continue
        threshold_results.append(th.passes(value))
        reasons.append(th.describe(value))

    all_thresholds_pass = all(threshold_results)
    promote_production = beats_incumbent and all_thresholds_pass and not require_manual_gate
    if beats_incumbent and all_thresholds_pass and require_manual_gate:
        reasons.append("production promotion awaiting manual gate (§5.3 Stage 6)")

    return PromotionDecision(
        model_name=model_name,
        promote_to_staging=beats_incumbent,
        promote_to_production=promote_production,
        reasons=tuple(reasons),
    )


@dataclass(slots=True)
class TestSetBudget:
    """Rate-limits access to the held-out test set.

    The test set is a finite resource: every look spends a little of its power
    to say anything unbiased. §4.4 reserves 2023-2025 for an unbiased comparison
    against NHC consensus, so evaluations are metered and logged rather than run
    on every candidate.
    """

    max_evaluations_per_season: int = config.get(
        "monitoring", "test_set_budget.max_evaluations_per_season", int
    )
    log: list[tuple[date, str, str]] = field(default_factory=list)

    def evaluations_in(self, season: int) -> int:
        return sum(1 for when, _, _ in self.log if when.year == season)

    def remaining(self, season: int) -> int:
        return max(self.max_evaluations_per_season - self.evaluations_in(season), 0)

    def spend(self, model_name: str, justification: str, when: date | None = None) -> None:
        when = when or datetime.now(UTC).date()
        if not justification.strip():
            raise PromotionError("test-set evaluation requires a written justification")
        if self.remaining(when.year) == 0:
            raise PromotionError(
                f"test-set evaluation budget for {when.year} is exhausted "
                f"({self.max_evaluations_per_season} used). Evaluate on validation, "
                "or raise the budget deliberately and record why."
            )
        self.log.append((when, model_name, justification.strip()))

    # -- persistence: the log is only a budget if it outlives one job --------

    def to_json(self) -> list[dict]:
        return [
            {"date": when.isoformat(), "model": model, "justification": why}
            for when, model, why in self.log
        ]

    @classmethod
    def from_json(cls, entries: list[dict]) -> TestSetBudget:
        budget = cls()
        budget.log = [
            (date.fromisoformat(e["date"]), str(e["model"]), str(e["justification"]))
            for e in entries
        ]
        return budget


#: Where the test-set budget's log is kept in the durable store, beside the
#: registry's mirror: one object per spend under this prefix, so jobs that
#: spend at the same time each add their own entry instead of overwriting a
#: shared file.
TEST_SET_BUDGET_PREFIX = "test_set_budget/"


def _budget_entries(checkpoint_store, workdir) -> list[tuple[str, dict]]:
    """Every logged spend, ``(key, entry)``, in key (spend) order."""
    import json
    from pathlib import Path

    bucket = checkpoint_store.config.bucket
    out = []
    for key in sorted(checkpoint_store.list(TEST_SET_BUDGET_PREFIX)):
        path = Path(workdir) / key.replace("/", "_")
        checkpoint_store.download(f"s3://{bucket}/{key}", path)
        out.append((key, json.loads(path.read_text())))
    return out


def spend_test_set_budget(
    checkpoint_store, model_name: str, justification: str, when: date | None = None,
) -> dict:
    """Spend one test-set evaluation from the durable budget and return the
    record of it. Raises `PromotionError` when the justification is blank,
    when there is no durable store to keep the log in, or when the season's
    budget is used up.

    The log is append-only (`TEST_SET_BUDGET_PREFIX`): this spend writes its
    own entry, then counts the season's entries in key order, and goes ahead
    only if its own is within the budget. Two jobs spending at once therefore
    both stay in the log, and at most the budget's worth of them proceed; one
    refused this way keeps its entry, which counts as spent.
    """
    import json
    import tempfile
    import uuid
    from pathlib import Path

    if checkpoint_store is None:
        raise PromotionError("test-set evaluation needs the durable store to log it in")
    if not justification.strip():
        raise PromotionError("test-set evaluation requires a written justification")
    when = when or datetime.now(UTC).date()
    with tempfile.TemporaryDirectory() as tmp:
        limit = TestSetBudget().max_evaluations_per_season

        def season_keys() -> list[str]:
            return [
                key for key, entry in _budget_entries(checkpoint_store, tmp)
                if date.fromisoformat(entry["date"]).year == when.year
            ]

        if len(season_keys()) >= limit:
            raise PromotionError(
                f"test-set evaluation budget for {when.year} is exhausted ({limit} used). "
                "Evaluate on validation, or raise the budget deliberately and record why."
            )
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        key = f"{TEST_SET_BUDGET_PREFIX}{stamp}-{uuid.uuid4().hex[:8]}.json"
        entry = {"date": when.isoformat(), "model": model_name,
                 "justification": justification.strip()}
        path = Path(tmp) / "entry.json"
        path.write_text(json.dumps(entry, indent=2))
        checkpoint_store.upload(path, key)
        keys = season_keys()
        if key not in keys[:limit]:
            raise PromotionError(
                f"test-set evaluation budget for {when.year} was used up by another job "
                f"spending at the same time; this attempt is logged ({key}) and counts"
            )
        used = keys.index(key) + 1
    return {**entry, "key": key, "used_this_season": used, "max_per_season": limit}
