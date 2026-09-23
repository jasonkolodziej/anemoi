"""Wiring the real per-model Stage A/B runners into
training.orchestrator.run_schedule (#22).

The five Group 1 runners, real latent extraction (training.real_latents)
and the diffusion/fusion runners are already tested in depth in their own
test files -- what's new and worth testing here is purely the
dispatch/integration layer: does a Task route to the right function, does
registry/promotion wiring (including latent_signature for the two derived
models) happen correctly, do unknown tasks fail cleanly instead of
silently no-op'ing. So every real curriculum/extraction function is
monkeypatched to a fast, deterministic stand-in here rather than actually
training anything -- real torch training of that wiring correctness is
what the per-model test files are for.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from anemoi.data.sources import Flavor
from anemoi.tracking.registry import ModelRegistry, Stage
from anemoi.tracking.tags import ExecutionMode
from anemoi.training.curriculum import Curriculum, CurriculumRun, StageResult, stage_b
from anemoi.training.orchestrator import Mode, Task, build_schedule, run_schedule
from anemoi.training.promotion import MetricSet
from anemoi.training.real_orchestrator import RealOrchestratorRunner

FAKE_METRICS_VALUES = {
    "track_error_48h_nm": 40.0,
    "track_error_72h_nm": 60.0,
    "track_error_120h_nm": 100.0,
    "intensity_error_48h_kt": 5.0,
    "intensity_error_72h_kt": 6.0,
    "nhc_consensus_beat_rate_48h": 0.6,
    "track_error_12h_nm": 10.0,
}


def _fake_curriculum_run(model_name: str) -> tuple[CurriculumRun, MetricSet, object]:
    curriculum = Curriculum.standard(model_name)
    run = CurriculumRun(curriculum=curriculum)
    run.record(
        StageResult(
            stage_name="A", flavor=Flavor.ERA5_PRETRAIN, epochs_completed=1,
            final_train_loss=1.0, final_val_loss=1.0, checkpoint_uri="s3://fake/A.pt",
        )
    )
    run.record(
        StageResult(
            stage_name="B", flavor=Flavor.GDAS_FINETUNE, epochs_completed=1,
            final_train_loss=0.5, final_val_loss=0.5, checkpoint_uri="s3://fake/B.pt",
        )
    )
    metrics = MetricSet(split="val", flavor=Flavor.GDAS_FINETUNE, values=dict(FAKE_METRICS_VALUES))
    artifacts = SimpleNamespace(model=f"trained-{model_name}", arch_params={})
    return run, metrics, artifacts


def _fake_derived_curriculum_run(
    model_name: str,
) -> tuple[CurriculumRun, MetricSet, object, object]:
    """`run_diffusion_curriculum`/`run_fusion_curriculum`'s own 4-tuple
    return shape (#78: model, then a real artifacts object with
    arch_params, added alongside for a real inference loader) -- these
    two are single-stage (Stage B only), unlike every Group 1 model's
    two-stage `_fake_curriculum_run`."""
    curriculum = Curriculum(model_name=model_name, stages=(stage_b(),))
    run = CurriculumRun(curriculum=curriculum)
    run.record(
        StageResult(
            stage_name="B", flavor=Flavor.GDAS_FINETUNE, epochs_completed=1,
            final_train_loss=0.5, final_val_loss=0.5, checkpoint_uri="s3://fake/B.pt",
        )
    )
    metrics = MetricSet(split="val", flavor=Flavor.GDAS_FINETUNE, values=dict(FAKE_METRICS_VALUES))
    model = f"trained-{model_name}"
    artifacts = SimpleNamespace(model=model, arch_params={})
    return run, metrics, model, artifacts


class _FakeJointLatents:
    """Stand-in for `real_latents.JointLatentSamples` -- dispatch only
    cares that it exists and reports a length."""

    def __len__(self) -> int:
        return 7


@pytest.fixture
def runner(tmp_path, monkeypatch) -> RealOrchestratorRunner:
    for name, module in (
        ("run_lstm_curriculum", "anemoi.training.real_run"),
        ("run_cnn_curriculum", "anemoi.training.real_run_cnn"),
        ("run_transformer_curriculum", "anemoi.training.real_run_transformer"),
        ("run_gnn_curriculum", "anemoi.training.real_run_gnn"),
        ("run_pinn_curriculum", "anemoi.training.real_run_pinn"),
        ("run_diffusion_curriculum", "anemoi.training.real_run_diffusion"),
        ("run_fusion_curriculum", "anemoi.training.real_run_fusion"),
    ):
        model_name = name.removeprefix("run_").removesuffix("_curriculum")
        is_derived = model_name in ("diffusion", "fusion")

        def make_fake(model_name=model_name, is_derived=is_derived):
            def fake(*args, **kwargs):
                if is_derived:
                    return _fake_derived_curriculum_run(model_name)
                return _fake_curriculum_run(model_name)

            return fake

        monkeypatch.setattr(f"{module}.{name}", make_fake())

    def fake_extract_joint_latents(*args, **kwargs):
        return _FakeJointLatents()

    monkeypatch.setattr(
        "anemoi.training.real_latents.extract_joint_latents", fake_extract_joint_latents
    )

    registry = ModelRegistry(tmp_path / "registry")
    return RealOrchestratorRunner(
        tracks=[],
        checkpoint_store=None,
        era5_cache_dir=tmp_path / "era5_cache",
        gdas_cache_dir=tmp_path / "gdas_cache",
        registry=registry,
    )


# --- RealOrchestratorRunner dispatch ----------------------------------------


@pytest.mark.parametrize("model_name", ["lstm", "cnn", "transformer", "gnn", "pinn"])
def test_dispatches_each_group1_model_to_its_real_runner(runner, model_name):
    task = Task(
        name=model_name, kind="train", depends_on=(), execution_mode=ExecutionMode.SEQUENTIAL,
        gpu_memory_gb=8, hours_low=1.0, hours_high=2.0,
    )
    outcome = runner(task)

    assert outcome.ok
    assert model_name in runner.curriculum_runs
    assert model_name in runner.val_metrics
    assert model_name in runner.promotions
    assert runner.registry.versions(model_name)
    assert runner.trained_artifacts[model_name].model == f"trained-{model_name}"


def test_registers_the_result_with_the_real_promotion_decision(runner):
    task = Task(
        name="lstm", kind="train", depends_on=(), execution_mode=ExecutionMode.SEQUENTIAL,
        gpu_memory_gb=8, hours_low=1.0, hours_high=2.0,
    )
    runner(task)
    decision = runner.promotions["lstm"]
    assert decision.model_name == "lstm"
    assert decision.promote_to_staging  # no incumbent -- first version always stages
    assert runner.registry.latest("lstm").version == 1
    # The decision alone being True is not enough -- it must actually be
    # applied to the registry, or no real cycle can ever find an eligible
    # version (`real_inference_cycle.py`/`real_inference_ensemble.py` both
    # only ever look at `registry.production`/`registry.in_stage(STAGING)`).
    assert runner.registry.latest("lstm").stage is Stage.STAGING


def test_a_non_promotable_candidate_is_not_transitioned(runner, monkeypatch):
    """A worse-than-incumbent second run must stay Stage.NONE -- the
    registry's own `transition` must only ever be called when the real
    decision says to, not unconditionally."""
    task = Task(
        name="lstm", kind="train", depends_on=(), execution_mode=ExecutionMode.SEQUENTIAL,
        gpu_memory_gb=8, hours_low=1.0, hours_high=2.0,
    )
    runner(task)
    assert runner.registry.latest("lstm").stage is Stage.STAGING

    worse_metrics = dict(FAKE_METRICS_VALUES)
    worse_metrics["track_error_48h_nm"] = FAKE_METRICS_VALUES["track_error_48h_nm"] * 10

    def _worse_curriculum_run(*args, **kwargs):
        run, _metrics, artifacts = _fake_curriculum_run("lstm")
        metrics = MetricSet(split="val", flavor=Flavor.GDAS_FINETUNE, values=worse_metrics)
        return run, metrics, artifacts

    monkeypatch.setattr("anemoi.training.real_run.run_lstm_curriculum", _worse_curriculum_run)
    runner(task)

    assert runner.registry.latest("lstm").version == 2
    assert not runner.promotions["lstm"].promote_to_staging
    assert runner.registry.latest("lstm").stage is Stage.NONE
    # The real, already-staged v1 must be untouched by the failed v2 attempt.
    assert runner.registry.get("lstm", 1).stage is Stage.STAGING


def test_second_run_compares_against_the_first_as_incumbent(runner):
    task = Task(
        name="lstm", kind="train", depends_on=(), execution_mode=ExecutionMode.SEQUENTIAL,
        gpu_memory_gb=8, hours_low=1.0, hours_high=2.0,
    )
    runner(task)
    runner(task)
    assert runner.registry.latest("lstm").version == 2
    assert "no incumbent" not in " ".join(runner.promotions["lstm"].reasons)


def test_incumbent_is_the_champion_not_the_most_recently_registered_version(runner, monkeypatch):
    """The real bug this fixes, found live in the deployed registry: v1
    stages (no incumbent), v2 is worse than v1 and correctly stays NONE --
    but a v3 that's worse than the real champion (v1) yet *better than v2*
    must still be blocked. Comparing against `versions(...)[-1]` (v2, not
    itself a champion) would wrongly let v3 through."""
    task = Task(
        name="lstm", kind="train", depends_on=(), execution_mode=ExecutionMode.SEQUENTIAL,
        gpu_memory_gb=8, hours_low=1.0, hours_high=2.0,
    )
    runner(task)  # v1: no incumbent, stages
    assert runner.registry.latest("lstm").stage is Stage.STAGING

    def _metrics_run(value):
        def _run(*args, **kwargs):
            run, _metrics, artifacts = _fake_curriculum_run("lstm")
            m = dict(FAKE_METRICS_VALUES)
            m["track_error_48h_nm"] = value
            metrics = MetricSet(split="val", flavor=Flavor.GDAS_FINETUNE, values=m)
            return run, metrics, artifacts
        return _run

    base = FAKE_METRICS_VALUES["track_error_48h_nm"]
    monkeypatch.setattr(
        "anemoi.training.real_run.run_lstm_curriculum", _metrics_run(base * 10)
    )
    runner(task)  # v2: much worse than champion v1 -> blocked, stays NONE
    assert runner.registry.get("lstm", 2).stage is Stage.NONE

    monkeypatch.setattr(
        "anemoi.training.real_run.run_lstm_curriculum", _metrics_run(base * 5)
    )
    runner(task)  # v3: better than v2, but still worse than the real champion v1
    assert not runner.promotions["lstm"].promote_to_staging
    assert runner.registry.get("lstm", 3).stage is Stage.NONE
    assert runner.registry.champion("lstm").version == 1


def test_latents_task_fails_cleanly_if_group1_is_incomplete(runner):
    """`_run_latents` checks all five Group 1 models have actually run in
    THIS runner before extracting -- calling it standalone (no Group 1
    task run yet) must fail with a clear reason, not crash or silently
    extract latents from nothing."""
    task = Task(
        name="latents", kind="latents", depends_on=("lstm", "cnn", "transformer", "gnn", "pinn"),
        execution_mode=ExecutionMode.SEQUENTIAL,
        gpu_memory_gb=24, hours_low=1.5, hours_high=3.0,
    )
    outcome = runner(task)
    assert not outcome.ok
    assert "not yet trained" in outcome.detail


def test_latents_task_succeeds_once_group1_has_run(runner):
    for model_name in ("lstm", "cnn", "transformer", "gnn", "pinn"):
        runner(Task(
            name=model_name, kind="train", depends_on=(), execution_mode=ExecutionMode.SEQUENTIAL,
            gpu_memory_gb=8, hours_low=1.0, hours_high=2.0,
        ))
    task = Task(
        name="latents", kind="latents", depends_on=("lstm", "cnn", "transformer", "gnn", "pinn"),
        execution_mode=ExecutionMode.SEQUENTIAL,
        gpu_memory_gb=24, hours_low=1.5, hours_high=3.0,
    )
    outcome = runner(task)
    assert outcome.ok
    assert "7" in outcome.detail  # _FakeJointLatents.__len__
    assert runner.joint_latents is not None


def test_diffusion_and_fusion_require_latents_to_have_run_first(runner):
    for name in ("diffusion", "fusion"):
        task = Task(
            name=name, kind="train", depends_on=("latents",),
            execution_mode=ExecutionMode.SEQUENTIAL,
            gpu_memory_gb=48, hours_low=2.0, hours_high=4.0,
        )
        outcome = runner(task)
        assert not outcome.ok
        assert "latents have not been extracted" in outcome.detail


def test_diffusion_registers_with_a_latent_signature_from_group1_versions(runner):
    for model_name in ("lstm", "cnn", "transformer", "gnn", "pinn"):
        runner(Task(
            name=model_name, kind="train", depends_on=(), execution_mode=ExecutionMode.SEQUENTIAL,
            gpu_memory_gb=8, hours_low=1.0, hours_high=2.0,
        ))
    runner(Task(
        name="latents", kind="latents", depends_on=("lstm", "cnn", "transformer", "gnn", "pinn"),
        execution_mode=ExecutionMode.SEQUENTIAL, gpu_memory_gb=24, hours_low=1.5, hours_high=3.0,
    ))
    outcome = runner(Task(
        name="diffusion", kind="train", depends_on=("latents",),
        execution_mode=ExecutionMode.SEQUENTIAL,
        gpu_memory_gb=48, hours_low=2.0, hours_high=4.0,
    ))
    assert outcome.ok
    version = runner.registry.latest("diffusion")
    assert version.latent_signature == (
        "lstmv1-cnnv1-transformerv1-gnnv1-pinnv1"
    )


def test_unknown_train_task_reports_not_implemented_without_crashing(runner):
    """A model name outside ALL_MODELS (every real model has a runner now
    -- Group 1 plus diffusion/fusion) must still fail cleanly rather than
    KeyError, in case the schedule is ever extended with a new model
    before its runner exists."""
    task = Task(
        name="quality_control", kind="train", depends_on=(),
        execution_mode=ExecutionMode.SEQUENTIAL,
        gpu_memory_gb=8, hours_low=1.0, hours_high=2.0,
    )
    outcome = runner(task)
    assert not outcome.ok
    assert "no real training runner" in outcome.detail


def test_a_failing_model_is_reported_not_raised(runner, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("simulated real training failure")

    monkeypatch.setattr("anemoi.training.real_run.run_lstm_curriculum", boom)
    task = Task(
        name="lstm", kind="train", depends_on=(), execution_mode=ExecutionMode.SEQUENTIAL,
        gpu_memory_gb=8, hours_low=1.0, hours_high=2.0,
    )
    outcome = runner(task)
    assert not outcome.ok
    assert "simulated real training failure" in outcome.detail


# --- full orchestrator.run_schedule integration -----------------------------


def test_sequential_schedule_trains_every_task_through_diffusion_and_fusion(runner):
    schedule = build_schedule(Mode.SEQUENTIAL)
    result = run_schedule(schedule, runner)

    for name in ("lstm", "cnn", "transformer", "gnn", "pinn", "latents", "diffusion", "fusion"):
        assert name in result.succeeded
    assert result.complete


def test_parallel_schedule_also_trains_every_task(runner):
    schedule = build_schedule(Mode.PARALLEL)
    result = run_schedule(schedule, runner)

    for name in ("lstm", "cnn", "transformer", "gnn", "pinn", "latents", "diffusion", "fusion"):
        assert name in result.succeeded
    assert result.complete


# --- derived-only re-sync against current champions (§5.7, #149) -------------


def _register_group1_versions(registry, *, champion_version: int, n_versions: int) -> None:
    """Register ``n_versions`` of every Group 1 model and stage
    ``champion_version`` -- so ``latest`` and ``champion`` genuinely
    differ when champion_version < n_versions, the real production case
    (2026-09-23: lstm v9 latest, v8 champion)."""
    from anemoi.tracking.registry import GROUP1_MODELS

    for name in GROUP1_MODELS:
        for _ in range(n_versions):
            registry.register(
                name, run_id=f"run-{name}", input_flavor=Flavor.GDAS_FINETUNE,
                metrics=dict(FAKE_METRICS_VALUES),
            )
        registry.transition(name, champion_version, Stage.STAGING)


@pytest.fixture
def fake_load_run_artifacts(monkeypatch):
    loaded: list[tuple[str, int]] = []

    def fake(name, version, checkpoint_store):
        loaded.append((name, version.version))
        return SimpleNamespace(model=f"champion-{name}-v{version.version}", arch_params={})

    monkeypatch.setattr("anemoi.training.real_inference.load_run_artifacts", fake)
    return loaded


def test_seed_from_champions_loads_each_champion_not_the_latest(runner, fake_load_run_artifacts):
    _register_group1_versions(runner.registry, champion_version=1, n_versions=2)

    used = runner.seed_from_champions()

    assert used == {"lstm": 1, "cnn": 1, "transformer": 1, "gnn": 1, "pinn": 1}
    assert sorted(fake_load_run_artifacts) == sorted((m, 1) for m in used)
    assert runner.trained_artifacts["lstm"].model == "champion-lstm-v1"


def test_seed_from_champions_refuses_an_incomplete_champion_set(runner, fake_load_run_artifacts):
    from anemoi.training.orchestrator import OrchestrationError

    runner.registry.register(
        "lstm", run_id="r", input_flavor=Flavor.GDAS_FINETUNE, metrics=dict(FAKE_METRICS_VALUES),
    )
    runner.registry.transition("lstm", 1, Stage.STAGING)

    with pytest.raises(OrchestrationError, match="no staging/production champion"):
        runner.seed_from_champions()


def test_derived_resync_records_the_champion_signature_and_ends_in_sync(
    runner, fake_load_run_artifacts,
):
    """The real #149 fix end to end: diffusion/fusion retrained against the
    current champions record *those* versions in latent_signature (not
    `registry.latest`, which is what put `lstmv9-...` on the real fusion v5
    while lstm v8 stayed champion), get staged, and leave nothing desynced."""
    from anemoi.training.orchestrator import build_derived_schedule

    _register_group1_versions(runner.registry, champion_version=1, n_versions=2)
    runner.seed_from_champions()

    result = run_schedule(build_derived_schedule(Mode.SEQUENTIAL), runner)

    assert result.complete
    for name in ("diffusion", "fusion"):
        champion = runner.registry.champion(name)
        assert champion.latent_signature == "lstmv1-cnnv1-transformerv1-gnnv1-pinnv1"
    assert runner.registry.desynced_derived_models() == ()


def test_a_desynced_derived_champion_is_not_a_bar_a_servable_candidate_must_clear(
    runner, fake_load_run_artifacts,
):
    """A desynced derived champion can't serve at all (the inference path
    refuses it), so its better-looking val metric must not keep a
    servable, re-synced candidate out of staging -- otherwise the system
    stays stuck serving nothing learned."""
    from anemoi.training.orchestrator import build_derived_schedule

    _register_group1_versions(runner.registry, champion_version=1, n_versions=2)
    stale_but_better = dict(FAKE_METRICS_VALUES, track_error_48h_nm=1.0)  # beats the fake 40.0
    for name in ("diffusion", "fusion"):
        v = runner.registry.register(
            name, run_id=f"stale-{name}", input_flavor=Flavor.GDAS_FINETUNE,
            metrics=stale_but_better, latent_signature="lstmv2-cnnv2-transformerv2-gnnv2-pinnv2",
        )
        runner.registry.transition(name, v.version, Stage.STAGING)
    assert set(runner.registry.desynced_derived_models()) == {"diffusion", "fusion"}

    runner.seed_from_champions()
    run_schedule(build_derived_schedule(Mode.SEQUENTIAL), runner)

    assert runner.registry.desynced_derived_models() == ()
    assert runner.promotions["fusion"].promote_to_staging


def test_a_servable_derived_champion_is_still_a_real_bar(runner, fake_load_run_artifacts):
    """The flip side: a derived champion that IS in sync stays a real
    incumbent -- a worse re-trained candidate must not replace it."""
    from anemoi.training.orchestrator import build_derived_schedule

    _register_group1_versions(runner.registry, champion_version=1, n_versions=1)
    better = dict(FAKE_METRICS_VALUES, track_error_48h_nm=1.0)
    for name in ("diffusion", "fusion"):
        v = runner.registry.register(
            name, run_id=f"synced-{name}", input_flavor=Flavor.GDAS_FINETUNE,
            metrics=better, latent_signature="lstmv1-cnnv1-transformerv1-gnnv1-pinnv1",
        )
        runner.registry.transition(name, v.version, Stage.STAGING)

    runner.seed_from_champions()
    run_schedule(build_derived_schedule(Mode.SEQUENTIAL), runner)

    assert not runner.promotions["fusion"].promote_to_staging
    assert runner.registry.champion("fusion").run_id == "synced-fusion"
