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
    """The commit this code was built from (`anemoi.provenance`, #214/#216).
    Training runs in the Cloud Run image, which has no ``.git`` -- `git
    rev-parse` there returned nothing, so `build_run_tags` returned None and
    no MLflow stage run was ever logged. The image's ``build-info.json``
    now carries the commit."""
    try:
        from ..provenance import git_sha

        return git_sha()
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


def _storm_split(stage: StageSpec, latest_season: int | None = None) -> str:
    from ..data.splits import Split
    from ..training.real_run import boundaries_for_flavor

    boundaries = boundaries_for_flavor(stage.flavor, latest_season)
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


#: Every real standardisation-stat field any RunArtifacts/DiffusionArtifacts
#: variant carries -- FusionArtifacts has none (its inputs/outputs are
#: already absolute, no standardisation needed).
STANDARDIZATION_STAT_FIELDS: tuple[str, ...] = (
    "x_mean", "x_std", "y_mean", "y_std", "env_mean", "env_std", "z_mean", "z_std",
)


#: Registry tag naming the GFS forecast hour a model's gridded inputs were
#: trained on (#215). Absent on versions registered before it: analyses (0).
NWP_LEAD_TAG = "nwp_lead_hours"


#: Registry tag: the newest season of the HURDAT2 a version trained on
#: (#216) -- what `anemoi retrain-check`'s data-volume trigger counts newer
#: seasons against. Absent on versions before it: the pinned 2023 file.
HURDAT2_LAST_SEASON_TAG = "hurdat2_last_season"
PINNED_HURDAT2_LAST_SEASON = 2023

#: Registry tag: the ATCF basins a version had training samples from,
#: sorted and comma-separated ("AL", "AL,CP,EP"), read by `ModelRegistry
#: .trained_basins` (docs/multi_basin.md). It must come from the examples
#: training consumed -- not the archive it was given, which also holds the
#: held-out seasons and storms a model may skip -- so it is set from the
#: runners' per-basin sample counts (`training.basin_gates.basin_tags`; a
#: gridded model has none where no field was cached), never by
#: `training_data_tags`.
TRAINED_BASINS_TAG = "trained_basins"
#: What a version without `TRAINED_BASINS_TAG` trained on: every one before
#: it was trained on NHC's Atlantic HURDAT2 file alone, the only one
#: `data.hurdat2_source` fetched then.
LEGACY_TRAINED_BASINS = frozenset({"AL"})

#: Registry tag: of the basins a version trained on, the ones where it beat
#: persistence on validation (`training.basin_gates`), sorted and
#: comma-separated; empty when it beat it nowhere. What `ModelRegistry
#: .verified_basins` reads to say which storms a forecast is in
#: distribution for. Absent on versions before it: `LEGACY_TRAINED_BASINS`,
#: which is what they were served as.
VERIFIED_BASINS_TAG = "verified_basins"


#: Registry tag: a version's basin input columns, in order, comma-separated
#: (`training.basin_input`), as resolved by `training.basin_gates
#: .resolve_basin_inputs` -- a column for a basin it had no training
#: samples from is blank ("AL,EP," is three columns, the last never on).
#: What the serving side builds its inputs with, exactly as the joint
#: latents were built. Absent on versions before the basin input: no
#: such columns.
BASIN_INPUTS_TAG = "basin_inputs"
#: The same for PINN's candidate-generator LSTM, which trains on the track
#: archive rather than the field cache, so its columns can differ.
CANDIDATE_BASIN_INPUTS_TAG = "candidate_basin_inputs"


def basin_input_tags(artifacts: object) -> dict[str, str]:
    """``artifacts``' basin input columns (`real_run.RunArtifacts.basins`,
    and ``candidate_basins`` for PINN) as registry tags. Set only for a
    model that has columns -- so a version without the tag is
    unambiguously one with none; one with columns, all blank, still gets
    it ("," is two)."""
    tags: dict[str, str] = {}
    for tag, field_name in (
        (BASIN_INPUTS_TAG, "basins"), (CANDIDATE_BASIN_INPUTS_TAG, "candidate_basins"),
    ):
        columns = tuple(getattr(artifacts, field_name, ()) or ())
        if columns:
            tags[tag] = ",".join(columns)
    return tags


#: A Transformer version that reads forecast-lead steering (Decision Log 68):
#: the `data.steering.steering_meta` it was trained with, JSON. Serving
#: refuses to feed it features computed with other settings.
STEERING_INPUTS_TAG = "steering_inputs"


def steering_input_tags(artifacts: object) -> dict[str, str]:
    """``{STEERING_INPUTS_TAG: ...}`` for a run whose ``arch_params`` has
    ``n_steering`` > 0 (the settings it trained with, ``steering_inputs``),
    else nothing."""
    arch = getattr(artifacts, "arch_params", None) or {}
    if not int(arch.get("n_steering", 0)):
        return {}
    meta = getattr(artifacts, "steering_inputs", None)
    if meta is None:
        raise ValueError("a run that reads steering must record the settings it trained with")
    return {STEERING_INPUTS_TAG: json.dumps(meta, sort_keys=True)}


def steering_inputs(tags: dict[str, str]) -> dict | None:
    """A version's recorded steering settings (`STEERING_INPUTS_TAG`), or
    ``None``."""
    raw = tags.get(STEERING_INPUTS_TAG)
    return None if raw is None else json.loads(raw)


def basin_inputs(tags: dict[str, str], tag: str = BASIN_INPUTS_TAG) -> tuple[str, ...]:
    """A registered version's basin input columns, from its tags, for
    building the inputs it is served with. ``()`` for a version without
    them."""
    raw = tags.get(tag)
    return () if raw is None else tuple(raw.split(","))


def training_data_tags(hurdat2_path: object, tracks: list) -> dict[str, str]:
    """Which labels a run trained on (#216): the HURDAT2 file's name and
    sha256 (`data.hurdat2_source.describe`), its newest season, and the
    sha256 of `configs/` -- the dataset version `dvc_version` can't give
    yet. Best-effort per field: tagging never fails a training run."""
    tags: dict[str, str] = {}
    if hurdat2_path:
        try:
            from ..data.hurdat2_source import describe

            tags.update(describe(hurdat2_path))
        except OSError:
            pass
    if tracks:
        from ..data.splits import latest_final_season

        tags[HURDAT2_LAST_SEASON_TAG] = str(latest_final_season(tracks))
    try:
        from ..provenance import config_digest

        tags["config_sha256"] = config_digest()
    except Exception:  # noqa: BLE001
        pass
    return tags


def gridded_input_tags(gdas_cache_dir: object) -> dict[str, str]:
    """The forecast hour of the GDAS cache a Stage B run trained from, as a
    registry tag -- what inference compares the fields it feeds a model
    against (`training.real_inference_cycle`, #215)."""
    if not gdas_cache_dir:
        return {}
    from ..data.gdas_cache import cache_nwp_lead_hours

    return {NWP_LEAD_TAG: str(cache_nwp_lead_hours(gdas_cache_dir))}


def standardization_tags(artifacts: object) -> dict[str, str]:
    """JSON-encode whichever of ``artifacts``' real standardisation stats
    are actually present (#78) -- a real inference process needs the
    EXACT same mean/std training fit its inputs/targets with to
    standardise a live input correctly and un-standardise a prediction
    back to real units. These numpy arrays only ever lived in memory for
    the training process that produced them until now; a value refit
    independently later (even from the same tracks) would only
    approximate the real ones a specific checkpoint's weights were
    actually trained against.
    """
    tags: dict[str, str] = {}
    for field_name in STANDARDIZATION_STAT_FIELDS:
        value = getattr(artifacts, field_name, None)
        if value is not None:
            tags[field_name] = json.dumps(value.tolist())
    return tags


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
    latest_season: int | None = None,
    trigger: Trigger = Trigger.MANUAL_SWEEP,
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
        storm_split=_storm_split(stage, latest_season),
        trigger=trigger,
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
    latest_season: int | None = None,
    trigger: Trigger = Trigger.MANUAL_SWEEP,
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

    tags = build_run_tags(
        model_name, stage, execution_mode=execution_mode, val_metrics=val_metrics,
        latest_season=latest_season, trigger=trigger,
    )
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


#: Durable-storage prefix for stage-run records: one JSON per curriculum run,
#: ``runs/<model>/<UTC timestamp>.json``. They hold what each MLflow run
#: holds, so MLflow being down or unconfigured loses nothing.
STAGE_RUNS_PREFIX = "runs"


def stage_run_record(
    model_name: str,
    stage: StageSpec,
    result: StageResult,
    *,
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
    val_metrics: MetricSet | None = None,
    latest_season: int | None = None,
    trigger: Trigger = Trigger.MANUAL_SWEEP,
    mlflow_run_id: str | None = None,
) -> dict:
    """One completed stage as plain JSON: the tags, metrics and params
    `log_stage_run` sends to MLflow, plus the MLflow run id when there is
    one."""
    tags = build_run_tags(
        model_name, stage, execution_mode=execution_mode, val_metrics=val_metrics,
        latest_season=latest_season, trigger=trigger,
    )
    metrics = {"train_loss": result.final_train_loss, "val_loss": result.final_val_loss}
    if val_metrics is not None:
        metrics.update(val_metrics.values)
    return {
        "model": model_name,
        "stage": stage.name,
        "run_name": f"{model_name}-{stage.name}",
        "experiment": experiment_name(model_name),
        "completed_at": (result.completed_at or datetime.now(UTC)).isoformat(),
        "tags": tags.to_dict() if tags else {},
        "metrics": metrics,
        "params": {
            "epochs_completed": result.epochs_completed,
            "checkpoint_uri": result.checkpoint_uri,
        },
        "mlflow_run_id": mlflow_run_id,
    }


def write_stage_runs(
    checkpoint_store, model_name: str, records: list[dict], *, key: str | None = None,
) -> str | None:
    """Upload one curriculum run's stage records to durable storage; returns
    the key, or None if there's no store or the upload failed -- like
    every tracking write, this must never fail a training run. ``key``
    overwrites an earlier upload (adding MLflow run ids to it)."""
    if checkpoint_store is None or not records:
        return None
    import tempfile
    from pathlib import Path

    key = key or f"{STAGE_RUNS_PREFIX}/{model_name}/{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}.json"
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stage_runs.json"
            body = {"model": model_name, "stages": records}
            path.write_text(json.dumps(body, indent=2, default=str))
            checkpoint_store.upload(path, key)
        return key
    except Exception:  # noqa: BLE001 - tracking must never fail a training run
        return None


def log_curriculum_stages(
    mlflow_client: MlflowClient | None,
    model_name: str,
    run: CurriculumRun,
    val_metrics: MetricSet,
    *,
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
    latest_season: int | None = None,
    trigger: Trigger = Trigger.MANUAL_SWEEP,
    checkpoint_store=None,
) -> str | None:
    """Log every completed stage in `run` as its own real MLflow run,
    attaching `val_metrics` (the deployable stage's real verification
    dict) only to the last one -- the only stage it was actually computed
    for (`run_*_curriculum` doesn't surface earlier stages' val_metrics to
    its caller). Returns the deployable stage's real MLflow run_id, or
    None if mlflow_client is None or nothing could be logged.

    Every stage is also written to ``checkpoint_store`` (durable storage,
    `write_stage_runs`) whether or not MLflow is configured or reachable,
    so MLflow is optional: it's a view onto these records, not their only
    copy.
    """
    deployable_run_id: str | None = None
    # Only the stages that completed (a run can stop early, or hold none).
    # The deployable stage is the curriculum's, not whichever completed
    # last: a run that stopped after Stage A keeps its loss records, but
    # gets no final-stage verification metrics and no deployable run id.
    n = len(run.results)
    completed = list(zip(run.curriculum.stages[:n], run.results, strict=True))
    deployable = run.curriculum.deployable_stage.name
    stage_metrics = [val_metrics if s.name == deployable else None for s, _ in completed]

    # Durable first: the records reach storage before MLflow is contacted,
    # so an MLflow that hangs mid-run can't hold them back (or lose them if
    # the job is stopped meanwhile) -- the same order `ModelRegistry`
    # writes in. The MLflow run ids are added to the same object after.
    records: list[dict | None] = []
    for (stage, result), metrics in zip(completed, stage_metrics, strict=True):
        try:
            records.append(stage_run_record(
                model_name, stage, result, execution_mode=execution_mode,
                val_metrics=metrics, latest_season=latest_season, trigger=trigger,
            ))
        except Exception:  # noqa: BLE001 - tracking must never fail a training run
            records.append(None)
    key = write_stage_runs(checkpoint_store, model_name, [r for r in records if r])

    deployable_run_id: str | None = None
    any_run_id = False
    for (stage, result), metrics, record in zip(completed, stage_metrics, records, strict=True):
        run_id = log_stage_run(
            mlflow_client, model_name, stage, result,
            execution_mode=execution_mode, val_metrics=metrics,
            latest_season=latest_season, trigger=trigger,
        )
        if stage.name == deployable:
            deployable_run_id = run_id
        if run_id and record is not None:
            record["mlflow_run_id"] = run_id
            any_run_id = True
    if key and any_run_id:
        write_stage_runs(checkpoint_store, model_name, [r for r in records if r], key=key)
    return deployable_run_id
