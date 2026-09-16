"""Wires the five real per-model Stage A/B runners (`training.real_run*`,
#22) into `training.orchestrator.run_schedule`'s injected ``runner``
callable.

`orchestrator.py` was already built backend-agnostic specifically for
this -- "computes the schedule and calls a runner callable... testable
without Kubernetes, Slurm, or a GPU" -- so nothing there needed to change.
This module is that runner, for real: `RealOrchestratorRunner.__call__`
dispatches a `Task` to the matching `real_run*.run_*_curriculum` function,
registers the result in `ModelRegistry`, and evaluates promotion, exactly
the sequence `cli.cmd_train` already does for one model at a time -- this
generalises it across a whole schedule.

Only Group 1 (lstm/cnn/transformer/gnn/pinn) has real implementations.
`orchestrator.build_schedule` always appends latents/diffusion/fusion
waves regardless of which Group 1 models are requested (Anemoi-Spread
diffusion and the fusion consensus have no real runner yet) -- those tasks
report a clear "not implemented yet" failure rather than silently
no-op'ing or pretending to succeed. `run_schedule`'s own dependency
semantics (a Group 1 failure only skips *its* dependents, §10.1) handle
the rest correctly: every Group 1 model still trains for real, only the
genuinely-unbuilt downstream stages report as not done.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ..data.besttrack import Track
from ..data.sources import Flavor
from ..tracking.checkpoint_store import CheckpointStore
from ..tracking.registry import ModelRegistry
from .curriculum import CurriculumRun
from .orchestrator import RunOutcome, Task
from .promotion import MetricSet, PromotionDecision, evaluate_promotion


def _run_lstm(r: RealOrchestratorRunner) -> tuple[CurriculumRun, MetricSet]:
    from .real_run import run_lstm_curriculum

    return run_lstm_curriculum(r.tracks, r.checkpoint_store, seed=r.seed, n_augment=r.n_augment)


def _run_cnn(r: RealOrchestratorRunner) -> tuple[CurriculumRun, MetricSet]:
    from .real_run_cnn import run_cnn_curriculum

    return run_cnn_curriculum(
        r.tracks, r.checkpoint_store, r.era5_cache_dir, r.gdas_cache_dir,
        seed=r.seed, n_augment=r.n_augment,
    )


def _run_transformer(r: RealOrchestratorRunner) -> tuple[CurriculumRun, MetricSet]:
    from .real_run_transformer import run_transformer_curriculum

    return run_transformer_curriculum(
        r.tracks, r.checkpoint_store, r.era5_cache_dir, r.gdas_cache_dir,
        seed=r.seed, n_augment=r.n_augment,
    )


def _run_gnn(r: RealOrchestratorRunner) -> tuple[CurriculumRun, MetricSet]:
    from .real_run_gnn import run_gnn_curriculum

    return run_gnn_curriculum(
        r.tracks, r.checkpoint_store, r.era5_cache_dir, r.gdas_cache_dir,
        seed=r.seed, n_augment=r.n_augment,
    )


def _run_pinn(r: RealOrchestratorRunner) -> tuple[CurriculumRun, MetricSet]:
    from .real_run_pinn import run_pinn_curriculum

    return run_pinn_curriculum(
        r.tracks, r.checkpoint_store, r.era5_cache_dir, r.gdas_cache_dir,
        seed=r.seed, n_augment=r.n_augment,
    )


#: One entry per model with a real runner (#22). Extend this, not
#: `RealOrchestratorRunner.__call__`, when a new model gets a real
#: training loop -- e.g. diffusion/fusion once those exist.
_MODEL_RUNNERS: dict[str, Callable[[RealOrchestratorRunner], tuple[CurriculumRun, MetricSet]]] = {
    "lstm": _run_lstm,
    "cnn": _run_cnn,
    "transformer": _run_transformer,
    "gnn": _run_gnn,
    "pinn": _run_pinn,
}


@dataclass(slots=True)
class RealOrchestratorRunner:
    """``Task -> RunOutcome`` for `orchestrator.run_schedule`, backed by
    the real per-model Stage A/B runners.

    Holds the config every real runner needs (tracks, durable checkpoint
    store, gridded-field cache dirs, model registry) once, rather than the
    caller threading it through every task by hand. After a `run_schedule`
    call, ``curriculum_runs``/``val_metrics``/``promotions`` hold each
    completed model's full detail, keyed by model name -- `RunOutcome`
    itself only carries a one-line summary string, not enough to inspect
    a promotion decision's reasons afterward.
    """

    tracks: list[Track]
    checkpoint_store: CheckpointStore
    era5_cache_dir: Path | str
    gdas_cache_dir: Path | str
    registry: ModelRegistry
    seed: int = 20260806
    n_augment: int = 3

    curriculum_runs: dict[str, CurriculumRun] = field(default_factory=dict, init=False)
    val_metrics: dict[str, MetricSet] = field(default_factory=dict, init=False)
    promotions: dict[str, PromotionDecision] = field(default_factory=dict, init=False)

    def __call__(self, task: Task) -> RunOutcome:
        if task.kind != "train":
            return RunOutcome(
                task=task.name, ok=False,
                detail=f"{task.kind!r} tasks have no real implementation yet (#22)",
            )

        run_fn = _MODEL_RUNNERS.get(task.name)
        if run_fn is None:
            return RunOutcome(
                task=task.name, ok=False,
                detail=f"no real training runner yet for {task.name!r} (#22)",
            )

        try:
            run, val_metrics = run_fn(self)
        except Exception as exc:  # noqa: BLE001 - one model's failure must not crash the schedule
            return RunOutcome(task=task.name, ok=False, detail=f"{type(exc).__name__}: {exc}")

        self.curriculum_runs[task.name] = run
        self.val_metrics[task.name] = val_metrics

        existing = self.registry.versions(task.name)
        incumbent = (
            MetricSet(split="val", flavor=existing[-1].input_flavor, values=existing[-1].metrics)
            if existing
            else None
        )
        version = self.registry.register(
            task.name,
            run_id=f"orchestrator-{datetime.now(UTC):%Y%m%dT%H%M%S}",
            input_flavor=Flavor.GDAS_FINETUNE,
            metrics=val_metrics.values,
        )
        decision = evaluate_promotion(task.name, run, val_metrics, incumbent_val_metrics=incumbent)
        self.promotions[task.name] = decision

        return RunOutcome(
            task=task.name, ok=True,
            detail=(
                f"registered v{version.version}; staging={decision.promote_to_staging} "
                f"production={decision.promote_to_production}"
            ),
        )
