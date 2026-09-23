"""Promotion gates on validation, operational flavor only (Scope v2.1 §5.3)."""

from datetime import date

import pytest

from anemoi.data.sources import Flavor
from anemoi.training.curriculum import Curriculum, CurriculumRun, StageResult
from anemoi.training.promotion import (
    DEFAULT_THRESHOLDS,
    INTENSITY_THRESHOLDS,
    TRACK_THRESHOLDS,
    MetricSet,
    PromotionError,
    TestSetBudget,
    Threshold,
    evaluate_promotion,
)


def good_metrics(split="val", flavor=Flavor.GDAS_FINETUNE, **overrides):
    values = {
        "track_error_48h_nm": 70.0,
        "track_error_72h_nm": 120.0,
        "track_error_120h_nm": 210.0,
        "intensity_error_48h_kt": 11.0,
        "intensity_error_72h_kt": 16.0,
        "nhc_consensus_beat_rate_48h": 0.56,
    }
    values.update(overrides)
    return MetricSet(split=split, flavor=flavor, values=values)


def complete_run():
    run = CurriculumRun(Curriculum.standard("lstm"))
    for name, flavor in (("A", Flavor.ERA5_PRETRAIN), ("B", Flavor.GDAS_FINETUNE)):
        run.record(
            StageResult(name, flavor, 10, 0.4, 0.5, f"s3://ckpt/{name}")
        )
    return run


def test_first_candidate_is_staged():
    decision = evaluate_promotion("lstm", complete_run(), good_metrics())
    assert decision.promote_to_staging


def test_production_requires_a_manual_gate_by_default():
    decision = evaluate_promotion("lstm", complete_run(), good_metrics())
    assert not decision.promote_to_production
    assert any("manual gate" in r for r in decision.reasons)


def test_production_promotes_when_the_manual_gate_is_cleared():
    decision = evaluate_promotion(
        "lstm", complete_run(), good_metrics(), require_manual_gate=False
    )
    assert decision.promote_to_production


def test_test_split_metrics_cannot_gate_promotion():
    with pytest.raises(PromotionError, match="validation split"):
        evaluate_promotion("lstm", complete_run(), good_metrics(split="test"))


def test_era5_flavor_metrics_cannot_gate_promotion():
    with pytest.raises(PromotionError, match="operational-flavor"):
        evaluate_promotion(
            "lstm", complete_run(), good_metrics(flavor=Flavor.ERA5_PRETRAIN)
        )


def test_incomplete_curriculum_blocks_promotion():
    run = CurriculumRun(Curriculum.standard("lstm"))
    run.record(StageResult("A", Flavor.ERA5_PRETRAIN, 10, 0.4, 0.5, "s3://a"))
    with pytest.raises(Exception, match="incomplete"):
        evaluate_promotion("lstm", run, good_metrics())


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_non_finite_first_candidate_is_not_staged(bad):
    """Real, previously-documented gap: with no incumbent, staging used to
    be unconditional, so NaN diffusion/fusion runs auto-staged."""
    decision = evaluate_promotion("fusion", complete_run(), good_metrics(track_error_48h_nm=bad))
    assert not decision.promote_to_staging
    assert any("non-finite" in r for r in decision.reasons)


def test_non_finite_candidate_does_not_beat_an_incumbent_either():
    decision = evaluate_promotion(
        "lstm", complete_run(), good_metrics(track_error_48h_nm=float("nan")),
        incumbent_val_metrics=good_metrics(track_error_48h_nm=500.0),
    )
    assert not decision.promote_to_staging


def test_candidate_worse_than_incumbent_is_not_staged():
    incumbent = good_metrics(track_error_48h_nm=60.0)
    decision = evaluate_promotion(
        "lstm", complete_run(), good_metrics(), incumbent_val_metrics=incumbent
    )
    assert not decision.promote_to_staging
    assert decision.blocked


def test_threshold_failure_blocks_production_but_not_staging():
    metrics = good_metrics(track_error_48h_nm=95.0)
    decision = evaluate_promotion(
        "lstm", complete_run(), metrics, require_manual_gate=False
    )
    assert decision.promote_to_staging
    assert not decision.promote_to_production


def test_missing_metric_is_reported_as_a_failure():
    values = dict(good_metrics().values)
    values.pop("intensity_error_48h_kt")
    metrics = MetricSet("val", Flavor.GDAS_FINETUNE, values)
    decision = evaluate_promotion(
        "lstm", complete_run(), metrics, require_manual_gate=False
    )
    assert not decision.promote_to_production
    assert any("missing" in r for r in decision.reasons)


def test_beat_rate_threshold_is_higher_is_better():
    th = Threshold("nhc_consensus_beat_rate_48h", 0.5, lower_is_better=False)
    assert th.passes(0.55)
    assert not th.passes(0.45)


def test_track_and_intensity_thresholds_are_separate_tables():
    """PLAN.md/Roadmap: intensity skill improves far more slowly than track
    skill, so the two should not share a re-derivation schedule or a table."""
    track_metrics = {th.metric for th in TRACK_THRESHOLDS}
    intensity_metrics = {th.metric for th in INTENSITY_THRESHOLDS}
    assert track_metrics.isdisjoint(intensity_metrics)
    assert all("track" in m or "beat_rate" in m for m in track_metrics)
    assert all("intensity" in m for m in intensity_metrics)


def test_default_thresholds_is_the_union_of_both_tables():
    assert set(DEFAULT_THRESHOLDS) == set(TRACK_THRESHOLDS) | set(INTENSITY_THRESHOLDS)


def test_track_48h_threshold_is_rebaselined_against_the_gpra_record():
    """45.4 nm (2024) / 53.4 nm (2025) realized, 51.0 nm 2026 GPRA target --
    https://www.nhc.noaa.gov/verification/pdfs/GPRA_history.pdf. The old 90.0
    nm backstop admitted a system roughly twice as bad as that baseline."""
    (track_48h,) = (th for th in TRACK_THRESHOLDS if th.metric == "track_error_48h_nm")
    assert track_48h.limit == pytest.approx(70.0)
    assert track_48h.limit < 90.0
    assert track_48h.limit > 53.4  # still a backstop, not parity with NHC


# --- test-set budget -------------------------------------------------------


def test_budget_allows_a_limited_number_of_looks():
    budget = TestSetBudget(max_evaluations_per_season=2)
    budget.spend("lstm", "pre-season verification", date(2026, 5, 1))
    budget.spend("gnn", "pre-season verification", date(2026, 5, 1))
    assert budget.remaining(2026) == 0


def test_budget_exhaustion_raises():
    budget = TestSetBudget(max_evaluations_per_season=1)
    budget.spend("lstm", "annual check", date(2026, 5, 1))
    with pytest.raises(PromotionError, match="budget"):
        budget.spend("gnn", "another look", date(2026, 6, 1))


def test_budget_requires_a_justification():
    with pytest.raises(PromotionError, match="justification"):
        TestSetBudget().spend("lstm", "   ", date(2026, 5, 1))


def test_budget_resets_across_seasons():
    budget = TestSetBudget(max_evaluations_per_season=1)
    budget.spend("lstm", "2026 check", date(2026, 5, 1))
    budget.spend("lstm", "2027 check", date(2027, 5, 1))
    assert budget.evaluations_in(2027) == 1
