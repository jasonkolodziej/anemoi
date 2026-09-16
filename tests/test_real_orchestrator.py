"""Wiring the real per-model Stage A/B runners into
training.orchestrator.run_schedule (#22).

The five real runners (training.real_run*) are already tested in depth in
their own test files -- what's new and worth testing here is purely the
dispatch/integration layer: does a Task route to the right model function,
does registry/promotion wiring happen correctly, do non-real tasks
(latents/diffusion/fusion) fail cleanly instead of silently no-op'ing. So
the five real curriculum functions are monkeypatched to fast, deterministic
stand-ins here rather than actually training anything -- real torch
training of that wiring correctness is what the per-model test files are
for.
"""

from __future__ import annotations

import pytest

from anemoi.data.sources import Flavor
from anemoi.tracking.registry import ModelRegistry
from anemoi.tracking.tags import ExecutionMode
from anemoi.training.curriculum import Curriculum, CurriculumRun, StageResult
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


def _fake_curriculum_run(model_name: str) -> tuple[CurriculumRun, MetricSet]:
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
    return run, metrics


@pytest.fixture
def runner(tmp_path, monkeypatch) -> RealOrchestratorRunner:
    for name, module in (
        ("run_lstm_curriculum", "anemoi.training.real_run"),
        ("run_cnn_curriculum", "anemoi.training.real_run_cnn"),
        ("run_transformer_curriculum", "anemoi.training.real_run_transformer"),
        ("run_gnn_curriculum", "anemoi.training.real_run_gnn"),
        ("run_pinn_curriculum", "anemoi.training.real_run_pinn"),
    ):
        model_name = name.removeprefix("run_").removesuffix("_curriculum")

        def make_fake(model_name=model_name):
            def fake(*args, **kwargs):
                return _fake_curriculum_run(model_name)

            return fake

        monkeypatch.setattr(f"{module}.{name}", make_fake())

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


def test_second_run_compares_against_the_first_as_incumbent(runner):
    task = Task(
        name="lstm", kind="train", depends_on=(), execution_mode=ExecutionMode.SEQUENTIAL,
        gpu_memory_gb=8, hours_low=1.0, hours_high=2.0,
    )
    runner(task)
    runner(task)
    assert runner.registry.latest("lstm").version == 2
    assert "no incumbent" not in " ".join(runner.promotions["lstm"].reasons)


def test_non_train_tasks_report_not_implemented_without_crashing(runner):
    task = Task(
        name="latents", kind="latents", depends_on=("lstm",),
        execution_mode=ExecutionMode.SEQUENTIAL,
        gpu_memory_gb=24, hours_low=1.5, hours_high=3.0,
    )
    outcome = runner(task)
    assert not outcome.ok
    assert "no real implementation" in outcome.detail


def test_unimplemented_model_reports_not_implemented_without_crashing(runner):
    task = Task(
        name="diffusion", kind="train", depends_on=("latents",),
        execution_mode=ExecutionMode.SEQUENTIAL,
        gpu_memory_gb=48, hours_low=24.0, hours_high=36.0,
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


def test_sequential_schedule_trains_all_group1_and_cleanly_fails_downstream(runner):
    schedule = build_schedule(Mode.SEQUENTIAL)
    result = run_schedule(schedule, runner)

    for model in ("lstm", "cnn", "transformer", "gnn", "pinn"):
        assert model in result.succeeded

    # latents has no real implementation -- fails, and diffusion/fusion
    # (which depend on it) are skipped as a result, not silently run.
    assert "latents" in result.failed
    assert "diffusion" in result.skipped
    assert "fusion" in result.skipped
    assert not result.complete


def test_parallel_schedule_also_trains_all_group1_models(runner):
    schedule = build_schedule(Mode.PARALLEL)
    result = run_schedule(schedule, runner)

    for model in ("lstm", "cnn", "transformer", "gnn", "pinn"):
        assert model in result.succeeded
    assert "latents" in result.failed
