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

All seven tasks the schedule can contain now have real implementations:
the five Group 1 models, `training.real_latents.extract_joint_latents` for
the "latents" task, and `training.real_run_diffusion`/`real_run_fusion` for
the two models derived from those latents (§5.7). A Group 1 model's
failure still only skips *its* dependents (`run_schedule`'s own dependency
semantics, §10.1) -- every model that can train, does.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ..data.besttrack import Track
from ..data.sources import Flavor
from ..tracking.checkpoint_store import CheckpointStore
from ..tracking.experiment_tracking import build_run_tags, log_curriculum_stages
from ..tracking.registry import DERIVED_MODELS, GROUP1_MODELS, ModelRegistry, latent_signature
from .curriculum import CurriculumRun
from .orchestrator import OrchestrationError, RunOutcome, Task
from .promotion import MetricSet, PromotionDecision, evaluate_promotion


def _streaming_kwargs(r: RealOrchestratorRunner) -> dict:
    """``streaming=False`` and ``num_workers`` are always passed explicitly
    (``num_workers=0`` matches every `run_*_curriculum`'s own default, so
    this is a no-op unless the caller set one). ``batch_size`` is only
    passed when the caller set one -- otherwise each model keeps its own
    tuned default (`train_lstm_stage_streaming`'s 64 vs.
    `train_transformer_stage_streaming`'s 16, etc.) instead of every model
    in a schedule silently collapsing onto one shared number."""
    kwargs: dict = {"streaming": r.streaming, "num_workers": r.num_workers}
    if r.batch_size is not None:
        kwargs["batch_size"] = r.batch_size
    return kwargs


def _run_lstm(r: RealOrchestratorRunner) -> tuple[CurriculumRun, MetricSet]:
    from .real_run import run_lstm_curriculum

    run, val_metrics, artifacts = run_lstm_curriculum(
        r.tracks, r.checkpoint_store, seed=r.seed, n_augment=r.n_augment,
        **_streaming_kwargs(r),
    )
    r.trained_artifacts["lstm"] = artifacts
    return run, val_metrics


def _run_cnn(r: RealOrchestratorRunner) -> tuple[CurriculumRun, MetricSet]:
    from .real_run_cnn import run_cnn_curriculum

    run, val_metrics, artifacts = run_cnn_curriculum(
        r.tracks, r.checkpoint_store, r.era5_cache_dir, r.gdas_cache_dir,
        seed=r.seed, n_augment=r.n_augment, **_streaming_kwargs(r),
    )
    r.trained_artifacts["cnn"] = artifacts
    return run, val_metrics


def _run_transformer(r: RealOrchestratorRunner) -> tuple[CurriculumRun, MetricSet]:
    from .real_run_transformer import run_transformer_curriculum

    run, val_metrics, artifacts = run_transformer_curriculum(
        r.tracks, r.checkpoint_store, r.era5_cache_dir, r.gdas_cache_dir,
        seed=r.seed, n_augment=r.n_augment, **_streaming_kwargs(r),
    )
    r.trained_artifacts["transformer"] = artifacts
    return run, val_metrics


def _run_gnn(r: RealOrchestratorRunner) -> tuple[CurriculumRun, MetricSet]:
    from .real_run_gnn import run_gnn_curriculum

    run, val_metrics, artifacts = run_gnn_curriculum(
        r.tracks, r.checkpoint_store, r.era5_cache_dir, r.gdas_cache_dir,
        seed=r.seed, n_augment=r.n_augment, **_streaming_kwargs(r),
    )
    r.trained_artifacts["gnn"] = artifacts
    return run, val_metrics


def _run_pinn(r: RealOrchestratorRunner) -> tuple[CurriculumRun, MetricSet]:
    from .real_run_pinn import run_pinn_curriculum

    run, val_metrics, artifacts = run_pinn_curriculum(
        r.tracks, r.checkpoint_store, r.era5_cache_dir, r.gdas_cache_dir,
        seed=r.seed, n_augment=r.n_augment, **_streaming_kwargs(r),
    )
    r.trained_artifacts["pinn"] = artifacts
    return run, val_metrics


def _run_latents(r: RealOrchestratorRunner) -> tuple[None, None]:
    """Not a model -- extracts real Anemoi-Spread/fusion conditioning
    latents from the five just-trained Group 1 models (`training
    .real_latents`). Raises (caught by ``__call__``, same as every other
    task) if a Group 1 model hasn't actually run yet in this schedule --
    `orchestrator.build_schedule` guarantees the dependency ordering, but
    this runner is deliberately still checked rather than trusted, since a
    caller could invoke it directly."""
    from .real_latents import extract_joint_latents

    missing = [m for m in GROUP1_MODELS if m not in r.trained_artifacts]
    if missing:
        raise OrchestrationError(f"latents: Group 1 model(s) not yet trained: {missing}")

    r.joint_latents = extract_joint_latents(
        r.tracks, r.trained_artifacts, r.gdas_cache_dir, seed=r.seed, n_augment=1,
    )
    return None, None


def _run_diffusion(r: RealOrchestratorRunner) -> tuple[CurriculumRun, MetricSet]:
    from .real_run_diffusion import run_diffusion_curriculum

    if r.joint_latents is None:
        raise OrchestrationError("diffusion: latents have not been extracted yet")
    run, val_metrics, _model = run_diffusion_curriculum(
        r.joint_latents, r.checkpoint_store, seed=r.seed,
    )
    return run, val_metrics


def _run_fusion(r: RealOrchestratorRunner) -> tuple[CurriculumRun, MetricSet]:
    from .real_run_fusion import run_fusion_curriculum

    if r.joint_latents is None:
        raise OrchestrationError("fusion: latents have not been extracted yet")
    run, val_metrics, _model = run_fusion_curriculum(
        r.joint_latents, r.checkpoint_store, seed=r.seed,
    )
    return run, val_metrics


#: One entry per model with a real runner (#22). Extend this, not
#: `RealOrchestratorRunner.__call__`, when a new model gets a real
#: training loop.
_MODEL_RUNNERS: dict[str, Callable[[RealOrchestratorRunner], tuple[CurriculumRun, MetricSet]]] = {
    "lstm": _run_lstm,
    "cnn": _run_cnn,
    "transformer": _run_transformer,
    "gnn": _run_gnn,
    "pinn": _run_pinn,
    "diffusion": _run_diffusion,
    "fusion": _run_fusion,
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
    #: Opt-in streaming training (`docs/streaming_dataloader.md`, #60-#63)
    #: -- real per-batch DataLoader training with O(batch_size) VRAM
    #: instead of one full-dataset GPU tensor, for the five Group 1
    #: models. Diffusion/fusion train against already-small in-memory
    #: joint latents, not the growing gridded cache, so they have no
    #: streaming path and ignore this. ``batch_size=None`` keeps each
    #: model's own tuned default (see `_streaming_kwargs`).
    streaming: bool = False
    batch_size: int | None = None
    #: Real `DataLoader` worker processes (streaming only, default 0 --
    #: matches every `run_*_curriculum`'s own default). See
    #: `streaming.make_dataloader`'s docstring for what this actually does
    #: and why it forces `multiprocessing_context="fork"`.
    num_workers: int = 0

    curriculum_runs: dict[str, CurriculumRun] = field(default_factory=dict, init=False)
    val_metrics: dict[str, MetricSet] = field(default_factory=dict, init=False)
    promotions: dict[str, PromotionDecision] = field(default_factory=dict, init=False)
    #: Trained Stage B `real_run.RunArtifacts`, keyed by Group 1 model
    #: name -- kept in memory rather than reloaded from checkpoint storage,
    #: since `tracking.registry.ModelVersion` doesn't record a
    #: checkpoint_uri today (#22). Populated by each `_run_*` dispatcher as
    #: it completes; PINN's bundle also carries its candidate-generator
    #: LSTM, never uploaded to checkpoint storage on its own.
    trained_artifacts: dict[str, object] = field(default_factory=dict, init=False)
    #: Set by the "latents" task once all five Group 1 models have run;
    #: consumed by the diffusion/fusion tasks that depend on it.
    joint_latents: object | None = field(default=None, init=False)

    def __call__(self, task: Task) -> RunOutcome:
        if task.kind == "latents":
            try:
                _run_latents(self)
            except Exception as exc:  # noqa: BLE001 - one task's failure must not crash the schedule
                return RunOutcome(task=task.name, ok=False, detail=f"{type(exc).__name__}: {exc}")
            n = len(self.joint_latents) if self.joint_latents is not None else 0
            return RunOutcome(task=task.name, ok=True, detail=f"extracted {n} joint latent samples")

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

        sig: str | None = None
        if task.name in DERIVED_MODELS:
            group1_versions = {m: self.registry.latest(m).version for m in GROUP1_MODELS}
            sig = latent_signature(group1_versions)

        existing = self.registry.versions(task.name)
        incumbent = (
            MetricSet(split="val", flavor=existing[-1].input_flavor, values=existing[-1].metrics)
            if existing
            else None
        )

        tags = build_run_tags(
            task.name, run.curriculum.stages[-1], execution_mode=task.execution_mode,
        )
        mlflow_run_id = log_curriculum_stages(
            self.registry.mlflow_client, task.name, run, val_metrics,
            execution_mode=task.execution_mode,
        )
        version = self.registry.register(
            task.name,
            run_id=f"orchestrator-{datetime.now(UTC):%Y%m%dT%H%M%S}",
            input_flavor=Flavor.GDAS_FINETUNE,
            metrics=val_metrics.values,
            tags=tags.to_dict() if tags else None,
            latent_signature=sig,
            checkpoint_uri=run.results[-1].checkpoint_uri,
            mlflow_run_id=mlflow_run_id,
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
