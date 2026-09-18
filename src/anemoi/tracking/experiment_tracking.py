"""Real MLflow experiment tracking and tagging (Scope v2.1 §7.2-7.3, wiki
Experiment-Tracking.md) -- the documented intended use of MLflow this
project's wiki describes: one run per completed curriculum stage, under
the wind-god experiment name (`branding.experiment_name`), tagged with the
validated `tags.RunTags` schema, carrying the real per-run verification
metrics `metrics.track.to_metric_dict()` already computes.

Built for both the MLflow and non-MLflow use cases, not just the former:
`build_run_tags()` (real git commit, real storm split from `data.splits`
boundaries, real GPU type, the real `nhc_consensus_beat_rate_48h` threshold
`training.promotion` already uses) has nothing MLflow-specific about it --
callers pass its `RunTags.to_dict()` to `ModelRegistry.register(tags=...)`
regardless of whether a real MLflow client is configured, so the local
JSON store gains real, validated tags either way. Only `log_stage_run()`
(and its `log_curriculum_stages()` wrapper) touch MLflow itself, and both
take `mlflow_client: MlflowClient | None`, returning `None` immediately
when it is -- exactly `ModelRegistry`'s own "MLflow absent/unreachable/
unconfigured must never fail a training run" contract (§10.1). Every real
MLflow call is also individually wrapped, for the same reason: a real
server going flaky mid-run must degrade silently, not discard a result
that has already been produced and locally registered.

Deliberately does not attempt per-epoch metric logging (`train_loss` per
epoch, `gpu_utilization`, `gpu_memory_gb`) -- that needs changes inside
every `train_*_stage`'s epoch loop (the five Group 1 runners plus
diffusion/fusion, seven files), a much larger and more invasive change
than this module's real value -- real per-stage metrics, real tags, a real
run to link a registered model version to -- justifies on its own. This
logs what is already computed and sitting in memory once a stage
completes, not more.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ..branding import experiment_name
from .tags import ExecutionMode, RunTags, Trigger

if TYPE_CHECKING:
    from mlflow.tracking import MlflowClient

    from ..training.curriculum import CurriculumRun, StageResult, StageSpec
    from ..training.promotion import MetricSet

#: DVC isn't built yet (wiki: Storage-and-Versioning.md's "DVC... remains
#: the target architecture, not yet built") -- there is no real dataset
#: version to report. This sentinel satisfies RunTags' vN.N.N[-suffix]
#: validation while staying unambiguous that it is NOT real dataset
#: versioning, unlike every other value this module builds.
NO_DVC_VERSION = "v0.0.0-no-dvc-yet"

#: promotion.py's own nhc_consensus_beat_rate_48h threshold, reused rather
#: than a new number invented for this tag -- "baseline_beaten" means
#: exactly what the production promotion gate already means.
_BASELINE_BEATEN_THRESHOLD = 0.50


def _git_commit() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return completed.stdout.strip()
    except Exception:  # noqa: BLE001 - tagging must never fail a training run
        return None


def _gpu_type() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0)
        if torch.backends.mps.is_available():
            return "Apple-MPS"
    except Exception:  # noqa: BLE001 - torch may not be installed at all
        pass
    return "cpu"


def _storm_split(stage: StageSpec) -> str:
    from ..data.sources import Flavor
    from ..data.splits import DEFAULT_BOUNDARIES, STAGE_B_BOUNDARIES, Split

    boundaries = STAGE_B_BOUNDARIES if stage.flavor is Flavor.GDAS_FINETUNE else DEFAULT_BOUNDARIES
    train_lo, train_hi = boundaries[Split.TRAIN]
    val_lo, val_hi = boundaries[Split.VAL]
    return f"train-{train_lo}-{train_hi}_val-{val_lo}-{val_hi}"


def arch_params_tag(artifacts: object) -> str | None:
    """JSON-encode ``artifacts.arch_params`` (`training.real_run
    .RunArtifacts`/`training.real_run_diffusion.DiffusionArtifacts`/
    `training.real_run_fusion.FusionArtifacts`, whichever this model has)
    for storage as a registry tag -- tags are ``dict[str, str]``
    (`tracking.registry.ModelVersion.tags`), so a plain dict can't be
    stored directly.

    Real motivation (#78): checkpoints only ever save
    ``model.state_dict()``, never the architecture that produced it
    (every `run_*_curriculum`'s upload step). Real inference needs to
    reconstruct an identical, untrained skeleton before
    ``load_state_dict`` can put real weights into it, and this tag is the
    only place that information survives after the training process that
    built the model exits.

    ``None`` if there's nothing real to record (``artifacts`` is ``None``,
    or its ``arch_params`` is empty) -- a real inference loader treats a
    missing tag as "this version predates arch_params tracking," not as
    an empty-but-present dict.
    """
    arch_params = getattr(artifacts, "arch_params", None)
    if not arch_params:
        return None
    return json.dumps(arch_params, sort_keys=True)


def candidate_tags(artifacts: object) -> dict[str, str]:
    """PINN-only tags for its candidate-generator LSTM (`training.real_run
    .RunArtifacts.candidate_arch_params`/``.candidate_checkpoint_uri``) --
    the second real model a real PINN inference loader needs, since
    `models.pinn.PhysicsCorrector.encode` takes both the environment
    vector AND the candidate's own forecast (#78). Empty dict (not a
    tag with an empty value) for every other model, or a PINN version
    that predates this being persisted.
    """
    tags: dict[str, str] = {}
    candidate_arch_params = getattr(artifacts, "candidate_arch_params", None)
    if candidate_arch_params:
        tags["candidate_arch_params"] = json.dumps(candidate_arch_params, sort_keys=True)
    candidate_checkpoint_uri = getattr(artifacts, "candidate_checkpoint_uri", None)
    if candidate_checkpoint_uri:
        tags["candidate_checkpoint_uri"] = candidate_checkpoint_uri
    return tags


def baseline_beaten(val_metrics: MetricSet | None) -> bool | None:
    """Real, threshold-derived (not invented) `RunTags.baseline_beaten`:
    whether this stage's real `nhc_consensus_beat_rate_48h` clears
    `training.promotion.TRACK_THRESHOLDS`' own 0.50 gate. None if the
    metric isn't available (e.g. no val_metrics for this stage)."""
    if val_metrics is None:
        return None
    rate = val_metrics.values.get("nhc_consensus_beat_rate_48h")
    if rate is None:
        return None
    return rate >= _BASELINE_BEATEN_THRESHOLD


def build_run_tags(
    model_name: str,
    stage: StageSpec,
    *,
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
    val_metrics: MetricSet | None = None,
) -> RunTags | None:
    """Real `RunTags` for one completed curriculum stage -- every field a
    real, currently-derivable value (git commit, real season-boundary
    storm split, real GPU, the real promotion-gate-derived
    `baseline_beaten`), except `dvc_version` (`NO_DVC_VERSION`, see module
    docstring). Returns None only if a real git commit sha genuinely can't
    be determined (not a git checkout) -- the one field this refuses to
    fabricate a placeholder for, since `git_commit` is meant to make a run
    locatable in exactly the code state that produced it (§10.3).
    """
    git_commit = _git_commit()
    if git_commit is None:
        return None

    return RunTags(
        model_type=model_name,
        git_commit=git_commit,
        dvc_version=NO_DVC_VERSION,
        storm_split=_storm_split(stage),
        trigger=Trigger.MANUAL_SWEEP,
        gpu_type=_gpu_type(),
        execution_mode=execution_mode,
        input_flavor=stage.flavor,
        baseline_beaten=baseline_beaten(val_metrics),
        stage_name=stage.name,
    )


def log_stage_run(
    mlflow_client: MlflowClient | None,
    model_name: str,
    stage: StageSpec,
    result: StageResult,
    *,
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
    val_metrics: MetricSet | None = None,
) -> str | None:
    """Log one completed curriculum stage as a real MLflow run under this
    model's wind-god experiment (`branding.experiment_name`) -- the
    documented "one run, real tags, real per-run verification metrics"
    shape from wiki Experiment-Tracking.md. Returns the created run_id (so
    `ModelRegistry.register(mlflow_run_id=...)` can link a registered
    model version back to the run that actually produced it), or None if
    `mlflow_client` is None or anything about logging failed -- this must
    never be why a training run fails (§10.1).
    """
    if mlflow_client is None:
        return None

    tags = build_run_tags(model_name, stage, execution_mode=execution_mode, val_metrics=val_metrics)
    if tags is None:
        return None

    try:
        from mlflow.entities import Metric, Param
        from mlflow.exceptions import MlflowException

        exp_name = experiment_name(model_name)
        try:
            experiment = mlflow_client.get_experiment_by_name(exp_name)
        except MlflowException:
            experiment = None
        experiment_id = experiment.experiment_id if experiment else mlflow_client.create_experiment(
            exp_name
        )

        run = mlflow_client.create_run(
            experiment_id, tags=tags.to_dict(), run_name=f"{model_name}-{stage.name}",
        )
        run_id = run.info.run_id

        now_ms = int((result.completed_at or datetime.now(UTC)).timestamp() * 1000)
        metrics = [
            Metric("train_loss", result.final_train_loss, now_ms, 0),
            Metric("val_loss", result.final_val_loss, now_ms, 0),
        ]
        if val_metrics is not None:
            metrics += [Metric(k, v, now_ms, 0) for k, v in val_metrics.values.items()]
        params = [
            Param("epochs_completed", str(result.epochs_completed)),
            Param("checkpoint_uri", result.checkpoint_uri),
        ]
        mlflow_client.log_batch(run_id, metrics=metrics, params=params)
        mlflow_client.set_terminated(run_id, status="FINISHED")
        return run_id
    except Exception:  # noqa: BLE001 - tracking must never fail a training run
        return None


def log_curriculum_stages(
    mlflow_client: MlflowClient | None,
    model_name: str,
    run: CurriculumRun,
    val_metrics: MetricSet,
    *,
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
) -> str | None:
    """Log every completed stage in `run` as its own real MLflow run,
    attaching `val_metrics` (the deployable stage's real verification
    dict) only to the last one -- the only stage it was actually computed
    for (`run_*_curriculum` doesn't surface earlier stages' val_metrics to
    its caller). Returns the deployable stage's real MLflow run_id, or
    None if mlflow_client is None or nothing could be logged.
    """
    if mlflow_client is None:
        return None

    deployable_run_id: str | None = None
    n = len(run.results)
    for i, (stage, result) in enumerate(zip(run.curriculum.stages, run.results, strict=True)):
        is_deployable = i == n - 1
        run_id = log_stage_run(
            mlflow_client, model_name, stage, result,
            execution_mode=execution_mode, val_metrics=val_metrics if is_deployable else None,
        )
        if is_deployable:
            deployable_run_id = run_id
    return deployable_run_id
