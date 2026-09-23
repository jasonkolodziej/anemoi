"""Retraining triggers and the derived-model cascade (Scope v2.1 §5.5, §5.7)."""

from datetime import UTC, date, datetime

from anemoi.tracking.tags import ExecutionMode, Trigger
from anemoi.training.triggers import (
    Reason,
    RetrainJob,
    SeasonState,
    evaluate_all,
    expand_jobs,
    nightly_latent,
    on_data_volume,
    on_drift,
    on_latent_desync,
    on_skew,
    preseason,
    scheduled_monthly,
)


def test_monthly_trigger_fires_only_on_the_first():
    assert scheduled_monthly(date(2026, 9, 1))
    assert not scheduled_monthly(date(2026, 9, 2))


def test_preseason_trigger_fires_on_may_first():
    assert preseason(date(2026, 5, 1))
    assert not preseason(date(2026, 6, 1))


def test_data_volume_trigger_respects_its_threshold():
    assert not on_data_volume(499)
    assert on_data_volume(500)


def test_group1_retrain_cascades_to_diffusion_and_fusion():
    """v2 said 'retrain the affected model only'; §5.7 says that is not enough."""
    jobs = on_drift("lstm")
    names = [j.model for j in jobs]
    assert names == ["lstm", "diffusion", "fusion"]
    assert all(j.cascaded for j in jobs if j.model != "lstm")


def test_cascade_orders_group1_before_derived_models():
    jobs = expand_jobs([RetrainJob("gnn", Reason.DRIFT, ExecutionMode.SEQUENTIAL)])
    assert jobs[0].model == "gnn"
    assert [j.model for j in jobs[1:]] == ["diffusion", "fusion"]


def test_retraining_a_derived_model_cascades_no_further():
    jobs = expand_jobs([RetrainJob("diffusion", Reason.MANUAL, ExecutionMode.SEQUENTIAL)])
    assert [j.model for j in jobs] == ["diffusion"]


def test_cascade_does_not_duplicate_an_explicitly_requested_model():
    jobs = expand_jobs(
        [
            RetrainJob("lstm", Reason.DRIFT, ExecutionMode.SEQUENTIAL),
            RetrainJob("diffusion", Reason.MANUAL, ExecutionMode.SEQUENTIAL),
        ]
    )
    assert [j.model for j in jobs].count("diffusion") == 1


def test_skew_trigger_notes_that_only_stage_b_reruns():
    jobs = on_skew("transformer")
    assert jobs[0].reason is Reason.SKEW
    assert "Stage B" in jobs[0].note
    assert jobs[0].trigger_tag is Trigger.SKEW_DETECTED


def test_nightly_latent_runs_at_0200_when_no_storms_are_active():
    now = datetime(2026, 2, 3, 2, tzinfo=UTC)
    assert nightly_latent(now, SeasonState())


def test_nightly_latent_is_suppressed_while_a_storm_is_active():
    """Swapping the ensemble generator mid-storm makes advisories incomparable."""
    now = datetime(2026, 9, 3, 2, tzinfo=UTC)
    assert not nightly_latent(now, SeasonState(active_storms=("AL092026",)))


def test_nightly_latent_does_not_run_at_other_hours():
    assert not nightly_latent(datetime(2026, 2, 3, 5, tzinfo=UTC), SeasonState())


def test_evaluate_all_combines_and_deduplicates():
    now = datetime(2026, 9, 1, 2, tzinfo=UTC)
    jobs = evaluate_all(now, SeasonState(), drifted_models=("lstm",), new_synoptic_times=600)
    names = [j.model for j in jobs]
    assert len(names) == len(set(names))
    assert "diffusion" in names


def test_latent_desync_trigger_fires_on_its_own_with_no_group1_retrain():
    """The real #149 gap: a desync can exist with no Group 1 retrain
    happening at all (a `registry-reconcile` re-stage is the real,
    documented cause) -- on_latent_desync must not depend on expand_jobs's
    Group1-cascade machinery to fire."""
    jobs = on_latent_desync("fusion")
    assert len(jobs) == 1
    assert jobs[0].model == "fusion"
    assert jobs[0].reason is Reason.LATENT_DESYNC
    assert jobs[0].trigger_tag is Trigger.LATENT_DESYNC
    assert "latent_signature" in jobs[0].note


def test_latent_desync_trigger_does_not_cascade_further():
    """Retraining a derived model invalidates nothing else -- expand_jobs's
    own invalidated_by("fusion") == () already guarantees this; asserted
    here as the real, specific #149 contract."""
    jobs = expand_jobs(on_latent_desync("diffusion"))
    assert [j.model for j in jobs] == ["diffusion"]


def test_evaluate_all_surfaces_a_real_latent_desync():
    now = datetime(2026, 9, 15, 4, tzinfo=UTC)  # not the 1st/5th/preseason, off 02:00Z
    jobs = evaluate_all(now, SeasonState(), desynced_models=("fusion",))
    assert [j.model for j in jobs] == ["fusion"]
    assert jobs[0].reason is Reason.LATENT_DESYNC


def test_evaluate_all_prefers_a_real_drift_reason_over_a_generic_cascade():
    """When the same model is both explicitly drifted and would otherwise
    only get a generic CASCADE placeholder, the specific real reason must
    win -- expand_jobs's own seen-first dedup already guarantees this;
    asserted here as the real #149-adjacent contract (LATENT_DESYNC is
    exactly this kind of specific reason)."""
    now = datetime(2026, 9, 15, 4, tzinfo=UTC)
    jobs = evaluate_all(now, SeasonState(), drifted_models=("lstm",), desynced_models=("fusion",))
    fusion_jobs = [j for j in jobs if j.model == "fusion"]
    assert len(fusion_jobs) == 1
    assert fusion_jobs[0].reason is Reason.LATENT_DESYNC
    assert fusion_jobs[0].cascaded is False
