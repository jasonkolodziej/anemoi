"""Command-line interface.

``anemoi schedule`` is the one to reach for first: it prints the real cycle
timeline for a given day, which is the fastest way to see the v2.1 timing change
against v2's assumed t+0:45 delivery.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import __version__
from .data.availability import LatencyOracle
from .data.besttrack import TrackQuality
from .data.sources import REGISTRY, Role
from .data.splits import assign_splits
from .data.synthetic import generate_archive
from .inference.cycle import climatological_ensemble, run_cycle
from .inference.scheduler import plan_cycle, plan_day
from .time_utils import parse_cycle_label


def _parse_day(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)


def cmd_schedule(args: argparse.Namespace) -> int:
    oracle = LatencyOracle(use_max_latency=args.worst_case)
    plans = plan_day(_parse_day(args.date), oracle)
    if not plans:
        print("no cycles could be planned for that day")
        return 1
    for plan in plans:
        print(plan.describe())
        status = "OK" if plan.meets_advisory_deadline else "MISSES ADVISORY DEADLINE"
        print(f"  advisory margin check: {status}\n")
    return 0


def cmd_sources(args: argparse.Namespace) -> int:
    rows = sorted(REGISTRY.values(), key=lambda s: (s.role.value, s.key))
    width = max(len(s.key) for s in rows)
    for src in rows:
        marker = " " if src.role is Role.OPERATIONAL else "*"
        hours = src.typical_latency.total_seconds() / 3600.0
        print(f"{marker} {src.key:<{width}}  {src.role.value:<14} ~{hours:>6.1f}h  {src.provider}")
    print("\n* not readable during a forecast cycle (Scope v2.1 §4.6)")
    return 0


def cmd_cycle(args: argparse.Namespace) -> int:
    import numpy as np

    from .data.besttrack import Fix
    from .inference.cycle import DeterministicForecast

    target = parse_cycle_label(args.cycle)
    oracle = LatencyOracle(use_max_latency=args.worst_case)
    plan = plan_cycle(target, oracle)

    fix = Fix(
        storm_id=args.storm,
        valid_time=target,
        lat=args.lat,
        lon=args.lon,
        max_wind_kt=args.wind,
        min_pressure_mb=990.0,
        quality=TrackQuality.ESTIMATED if plan.vitals_estimated else TrackQuality.WORKING,
    )

    leads = (12, 24, 36, 48, 72, 96, 120)

    def deterministic(plan_, fix_):
        steps = np.arange(1, len(leads) + 1, dtype=float)
        return DeterministicForecast(
            target_time=plan_.target_time,
            lead_hours=leads,
            lats=fix_.lat + 0.9 * steps,
            lons=fix_.lon - 1.1 * steps,
            winds_kt=np.clip(fix_.max_wind_kt + 4.0 * steps - 0.4 * steps**2, 15.0, None),
            contributors={"lstm": 0.2, "transformer": 0.35, "gnn": 0.25, "cnn": 0.2},
        )

    output = run_cycle(
        plan,
        fix,
        deterministic,
        lambda det, n: climatological_ensemble(det, n_members=n, seed=1),
        requested_members=args.members,
    )
    print(json.dumps(output.payload(), indent=2))
    return 0


def cmd_ablation(args: argparse.Namespace) -> int:
    """Run the #9 capacity-vs-sample-size ablation against a real HURDAT2 file.

    Needs the torch extra (uv sync --extra torch). See docs/capacity_ablation.md
    for the recorded run and what it does/does not measure.
    """
    from .data.hurdat2 import parse_hurdat2_file
    from .training.capacity_ablation import run_capacity_ablation

    tracks = parse_hurdat2_file(args.hurdat2)
    report = run_capacity_ablation(
        tracks,
        hidden_dims=tuple(args.hidden_dims),
        sample_fractions=tuple(args.sample_fractions),
        n_augment=args.n_augment,
        epochs=args.epochs,
        seed=args.seed,
    )
    print(report.to_markdown())
    print()
    print(report.recommend())
    return 0


def _cmd_gridded_cache(
    args: argparse.Namespace,
    run_fetch_cache,
    *,
    archive_prefix: str,
    boundaries: dict | None = None,
) -> int:
    """Shared body for cmd_era5_cache/cmd_gdas_cache -- same split-selection,
    reporting and exit-code behaviour, different underlying fetch pipeline.

    ``boundaries`` overrides ``data.splits.DEFAULT_BOUNDARIES`` -- GDAS uses
    ``data.splits.STAGE_B_BOUNDARIES`` instead, since GDAS's real archive
    doesn't overlap the default `train` window at all (see that constant's
    docstring); ERA5 keeps the default.
    """
    from .data.gridded_cache import build_fetch_tasks
    from .data.hurdat2 import parse_hurdat2_file
    from .data.splits import Split, assign_splits, filter_tracks

    tracks = parse_hurdat2_file(args.hurdat2)
    assignment = assign_splits(tracks, boundaries=boundaries)
    split_tracks = filter_tracks(tracks, assignment, Split(args.split))
    print(f"{args.split}: {len(split_tracks)} storms, "
          f"{sum(len(t.fixes) for t in split_tracks)} fixes")

    report = run_fetch_cache(
        split_tracks,
        args.cache_dir,
        box_deg=args.box_deg,
        max_workers=args.max_workers,
        skip_existing=not args.force,
        progress_every=args.progress_every,
    )
    print(
        f"done: {report.n_fetched} fetched, {report.n_skipped} skipped, "
        f"{report.n_failed} failed, {report.elapsed_s:.0f}s"
    )
    for task, error in report.failures[:20]:
        print(f"  FAILED {task.storm_id} {task.valid_time}: {error}")
    exit_code = 1 if report.n_failed else 0

    if args.sync_archive:
        from .data.gridded_cache import sync_cache_to_archive
        from .tracking.checkpoint_store import CheckpointStore, S3Config

        store = CheckpointStore(S3Config.from_env())
        sync_report = sync_cache_to_archive(
            build_fetch_tasks(split_tracks),
            args.cache_dir,
            store,
            prefix=archive_prefix,
            max_workers=args.max_workers,
            progress_every=args.progress_every,
        )
        print(
            f"archive sync: {sync_report.n_uploaded} uploaded, "
            f"{sync_report.n_already_archived} already archived, "
            f"{sync_report.n_missing_local} not yet cached locally, "
            f"{sync_report.n_failed} failed, {sync_report.elapsed_s:.0f}s"
        )
        for task, error in sync_report.failures[:20]:
            print(f"  ARCHIVE FAILED {task.storm_id} {task.valid_time}: {error}")
        if sync_report.n_failed:
            exit_code = 1

    return exit_code


def cmd_era5_cache(args: argparse.Namespace) -> int:
    """Concurrently fetch and locally cache real ERA5 GriddedFields for one
    data.splits split, from a real HURDAT2 file. Needs the gridded extra
    (uv sync --extra gridded). See docs/train_infrastructure.md.
    """
    from .data.era5_cache import run_fetch_cache

    return _cmd_gridded_cache(args, run_fetch_cache, archive_prefix="era5_archive")


def cmd_gdas_cache(args: argparse.Namespace) -> int:
    """Concurrently fetch and locally cache real GDAS GriddedFields for one
    data.splits split, from a real HURDAT2 file (Stage B analog of
    cmd_era5_cache). Needs the gridded extra's eccodes -- which, unlike
    xarray for ERA5, has a real broken-native-library failure mode on some
    machines; see real_gridded.require_gdas_deps's docstring.

    Uses data.splits.STAGE_B_BOUNDARIES, not the default train/val/test
    boundaries -- those were set for Stage A/ERA5's 1980-2025 pretraining
    window and have zero overlap with GDAS's real 2021-present archive.
    """
    from .data.gdas_cache import run_fetch_cache
    from .data.splits import STAGE_B_BOUNDARIES

    return _cmd_gridded_cache(
        args, run_fetch_cache, archive_prefix="gdas_archive", boundaries=STAGE_B_BOUNDARIES
    )


def cmd_train(args: argparse.Namespace) -> int:
    """Run a real Stage A/B curriculum against a real HURDAT2 file (#22).

    Needs the torch and storage extras (uv sync --extra torch --extra
    storage) and real R2/S3 credentials (S3_ARTIFACT_* in .env) -- every
    stage's checkpoint is uploaded durably, not just left on local disk.

    'lstm' needs no gridded-field cache (its input is storm-history
    sequences, not pixels). 'cnn'/'transformer'/'gnn'/'pinn' read real
    cached GriddedFields from --era5-cache-dir/--gdas-cache-dir
    (data.era5_cache/data.gdas_cache's own --cache-dir) -- cnn/transformer
    as a channel stack, gnn as a lattice-graph mesh built from the same
    grid, pinn as a real environment-feature vector plus a candidate track
    from an internally-trained LSTM to correct -- see
    training.real_run_cnn/real_run_transformer/real_run_gnn/real_run_pinn's
    module docstrings for why (and, for transformer, the real-crop-size
    trim; for pinn, the candidate-generator design).

    Registers to a real MLflow server, alongside the always-written local
    JSON store, if MLFLOW_TRACKING_URI is set and the tracking extra
    (mlflow) is installed -- tracking.mlflow_client.mlflow_client_from_env()
    returns None otherwise, which ModelRegistry already treats exactly like
    "no MLflow configured" (Scope v2.1 §10.1: never fails a training run).

    --streaming trains via a real per-batch torch DataLoader instead of
    the default full-batch path (docs/streaming_dataloader.md) -- durable
    fix for a real CUDA OOM training against a large enough cached
    dataset (per-step VRAM becomes O(batch_size), not O(dataset size)).

    --num-workers (--streaming only) spawns real DataLoader worker
    processes to overlap cached-field disk reads with GPU compute instead
    of blocking each training step on them -- see
    training.streaming.make_dataloader's docstring for why it defaults to
    0 and forces "fork" when set.
    """
    from .data.hurdat2 import parse_hurdat2_file
    from .data.sources import Flavor
    from .tracking.checkpoint_store import CheckpointStore, S3Config
    from .tracking.experiment_tracking import (
        arch_params_tag,
        build_run_tags,
        candidate_tags,
        log_curriculum_stages,
        standardization_tags,
    )
    from .tracking.mlflow_client import mlflow_client_from_env
    from .tracking.registry import ModelRegistry, Stage
    from .training.promotion import MetricSet, evaluate_promotion

    tracks = parse_hurdat2_file(args.hurdat2)
    store = CheckpointStore(S3Config.from_env())

    streaming_kwargs: dict = {"streaming": args.streaming, "num_workers": args.num_workers}
    if args.batch_size is not None:
        streaming_kwargs["batch_size"] = args.batch_size

    if args.model == "lstm":
        from .training.real_run import run_lstm_curriculum

        run, val_metrics, artifacts = run_lstm_curriculum(
            tracks, store, seed=args.seed, n_augment=args.n_augment, hidden_dim=args.hidden_dim,
            **streaming_kwargs,
        )
    elif args.model == "cnn":
        from .training.real_run_cnn import run_cnn_curriculum

        if not args.era5_cache_dir or not args.gdas_cache_dir:
            print("cnn needs --era5-cache-dir and --gdas-cache-dir")
            return 1
        run, val_metrics, artifacts = run_cnn_curriculum(
            tracks, store, args.era5_cache_dir, args.gdas_cache_dir,
            seed=args.seed, n_augment=args.n_augment, **streaming_kwargs,
        )
    elif args.model == "transformer":
        from .training.real_run_transformer import run_transformer_curriculum

        if not args.era5_cache_dir or not args.gdas_cache_dir:
            print("transformer needs --era5-cache-dir and --gdas-cache-dir")
            return 1
        run, val_metrics, artifacts = run_transformer_curriculum(
            tracks, store, args.era5_cache_dir, args.gdas_cache_dir,
            seed=args.seed, n_augment=args.n_augment, **streaming_kwargs,
        )
    elif args.model == "gnn":
        from .training.real_run_gnn import run_gnn_curriculum

        if not args.era5_cache_dir or not args.gdas_cache_dir:
            print("gnn needs --era5-cache-dir and --gdas-cache-dir")
            return 1
        run, val_metrics, artifacts = run_gnn_curriculum(
            tracks, store, args.era5_cache_dir, args.gdas_cache_dir,
            seed=args.seed, n_augment=args.n_augment, hidden_dim=args.hidden_dim,
            **streaming_kwargs,
        )
    elif args.model == "pinn":
        from .training.real_run_pinn import run_pinn_curriculum

        if not args.era5_cache_dir or not args.gdas_cache_dir:
            print("pinn needs --era5-cache-dir and --gdas-cache-dir")
            return 1
        run, val_metrics, artifacts = run_pinn_curriculum(
            tracks, store, args.era5_cache_dir, args.gdas_cache_dir,
            seed=args.seed, n_augment=args.n_augment, hidden_dim=args.hidden_dim,
            **streaming_kwargs,
        )
    else:
        print(f"no real training runner yet for {args.model!r} -- see cmd_train's docstring")
        return 1

    print(f"curriculum complete: {[r.stage_name for r in run.results]}")
    for r in run.results:
        print(
            f"  stage {r.stage_name} ({r.flavor.value}): train_loss={r.final_train_loss:.4f} "
            f"val_loss={r.final_val_loss:.4f} -> {r.checkpoint_uri}"
        )
    for key in sorted(val_metrics.values):
        print(f"  {key}: {val_metrics.values[key]:.3f}")

    registry = ModelRegistry(
        args.registry_root, mlflow_client=mlflow_client_from_env(), checkpoint_store=store,
    )
    # The incumbent is whichever version real inference is actually using
    # (production, else staging), not `versions(...)[-1]` -- see
    # `ModelRegistry.champion`'s own docstring for the real bug this closes.
    champion = registry.champion(args.model)
    incumbent_metrics = (
        MetricSet(split="val", flavor=champion.input_flavor, values=champion.metrics)
        if champion
        else None
    )

    tags = build_run_tags(args.model, run.curriculum.stages[-1])
    mlflow_run_id = log_curriculum_stages(registry.mlflow_client, args.model, run, val_metrics)
    tag_dict = tags.to_dict() if tags else {}
    arch_params = arch_params_tag(artifacts)
    if arch_params is not None:
        tag_dict["arch_params"] = arch_params
    tag_dict.update(candidate_tags(artifacts))
    tag_dict.update(standardization_tags(artifacts))
    version = registry.register(
        args.model,
        run_id=f"cli-{datetime.now(UTC):%Y%m%dT%H%M%S}",
        input_flavor=Flavor.GDAS_FINETUNE,
        metrics=val_metrics.values,
        tags=tag_dict or None,
        checkpoint_uri=run.results[-1].checkpoint_uri,
        mlflow_run_id=mlflow_run_id,
    )
    print(f"registered {args.model} v{version.version} in {args.registry_root}")

    decision = evaluate_promotion(
        args.model, run, val_metrics, incumbent_val_metrics=incumbent_metrics
    )
    print(
        f"promotion: staging={decision.promote_to_staging} "
        f"production={decision.promote_to_production}"
    )
    for reason in decision.reasons:
        print(f"  {reason}")
    # The decision alone was computed and printed but never actually applied
    # -- every real version stayed Stage.NONE regardless of what this line
    # printed. Production stays deliberately unapplied: evaluate_promotion's
    # own require_manual_gate=True default (unchanged here) means
    # promote_to_production is always False by construction; only an
    # explicit, human-run promotion should move a version to production
    # (Scope v2.1 SS5.3 Stage 6).
    if decision.promote_to_staging:
        registry.transition(args.model, version.version, Stage.STAGING)
        print(f"  -> transitioned {args.model} v{version.version} to staging")
    return 0


def cmd_train_schedule(args: argparse.Namespace) -> int:
    """Run the full multi-model wave schedule via training.orchestrator,
    backed by the real per-model runners (training.real_orchestrator, #22).

    All seven tasks the schedule can contain have real implementations:
    the five Group 1 models, real latent extraction for "latents"
    (training.real_latents), and diffusion/fusion trained against those
    latents (training.real_run_diffusion/real_run_fusion). run_schedule's
    own dependency semantics still apply -- if a Group 1 model's real
    training fails, whatever depends on it is skipped, not silently
    no-op'd.

    Needs the torch and storage extras and real R2/S3 credentials
    (S3_ARTIFACT_* in .env), same as `anemoi train`; cnn/transformer/gnn/
    pinn additionally need --era5-cache-dir/--gdas-cache-dir.

    --streaming applies to the five Group 1 models only (same durable
    full-batch-OOM fix as `anemoi train --streaming`,
    docs/streaming_dataloader.md); diffusion/fusion have no streaming path
    since they train against small in-memory joint latents, not the
    growing gridded cache. --num-workers (--streaming only) is the same
    real DataLoader worker-process option as `anemoi train`'s.
    """
    from .data.hurdat2 import parse_hurdat2_file
    from .tracking.checkpoint_store import CheckpointStore, S3Config
    from .tracking.mlflow_client import mlflow_client_from_env
    from .tracking.registry import ModelRegistry
    from .training.orchestrator import Mode, build_schedule, run_schedule
    from .training.real_orchestrator import RealOrchestratorRunner

    tracks = parse_hurdat2_file(args.hurdat2)
    store = CheckpointStore(S3Config.from_env())
    registry = ModelRegistry(
        args.registry_root, mlflow_client=mlflow_client_from_env(), checkpoint_store=store,
    )

    mode = Mode(args.mode)
    default_models = ("lstm", "cnn", "transformer", "gnn", "pinn")
    models = tuple(args.models.split(",")) if args.models else default_models
    schedule = build_schedule(mode, models=models)

    runner = RealOrchestratorRunner(
        tracks=tracks,
        checkpoint_store=store,
        era5_cache_dir=args.era5_cache_dir,
        gdas_cache_dir=args.gdas_cache_dir,
        registry=registry,
        seed=args.seed,
        n_augment=args.n_augment,
        streaming=args.streaming,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
    )
    result = run_schedule(schedule, runner)

    print(f"schedule: {mode.value}, {len(schedule.task_names())} tasks")
    for outcome in result.outcomes:
        status = "OK" if outcome.ok else "FAILED"
        print(f"  [{status}] {outcome.task}: {outcome.detail}")
    if result.skipped:
        print(f"  SKIPPED (unmet dependencies): {', '.join(result.skipped)}")
    print(f"succeeded: {list(result.succeeded)}")
    print(f"failed: {list(result.failed)}")
    return 0 if not result.failed else 1


def cmd_retrain_check(args: argparse.Namespace) -> int:
    """Evaluate real retraining triggers (Retraining-Triggers wiki, §5.5)
    against real signals and, if any calendar/data-volume trigger fires,
    run the real training wave `train-schedule` runs.

    The one entry point this system has for autonomous retraining -- meant
    to run on an unattended schedule (a cron/systemd timer, a GCP
    instance-schedule startup script), not to be watched by a human.
    `evaluate_all` itself has been real and well-tested since #22; what was
    missing was anything that actually called it with real signals and
    acted on the result -- confirmed by grep: nothing in `src/` outside
    tests ever called it before this command existed.

    Real signals gathered here:

    * ``now`` -- real wall-clock time (calendar/nightly triggers).
    * ``new_synoptic_times`` -- real count of HURDAT2 fixes newer than the
      most recently *registered* Group 1 version (any stage), i.e. "how
      much real data has accumulated since we last tried training at all."
    * Active storms and per-model drift -- a real query against a running
      API's `/v1/storms` and `/v1/monitoring/drift/{model}` (best-effort:
      a network failure degrades to an empty/no-drift signal with a
      printed warning, never a crash -- this check must be safe to run
      unattended every day).

    **Drift/skew will not fire against a real deployment today.**
    `api.real_state.RealState.drift_report`/`skew_report` are honestly
    stubbed (no real reference distribution or ERA5T pipeline exists yet
    -- see the Roadmap), so a real query always comes back non-alerting.
    Wired anyway so the day real drift/skew detection lands, this command
    needs no further changes to act on it.

    **Only `scheduled_monthly`/`preseason`/`data_volume` are dispatched.**
    All three produce the identical job shape -- every Group 1 model plus
    the derived cascade -- which is exactly `train-schedule`'s own default
    schedule, so dispatch is just invoking that same real machinery.
    `nightly_latent` (diffusion-only, keeping existing Group 1 checkpoints)
    and isolated drift/skew retrains don't fit that "Group 1 + full
    derived chain" shape -- a real dispatcher for those is separate, scoped
    future work (see the Roadmap), so they are reported, not silently
    dropped, but not dispatched here.
    """
    import urllib.error
    import urllib.request

    from .data.hurdat2 import parse_hurdat2_file
    from .tracking.checkpoint_store import CheckpointStore, S3Config
    from .tracking.mlflow_client import mlflow_client_from_env
    from .tracking.registry import ALL_MODELS, GROUP1_MODELS, ModelRegistry, RegistryError
    from .training.orchestrator import Mode, build_schedule, run_schedule
    from .training.real_orchestrator import RealOrchestratorRunner
    from .training.triggers import Reason, SeasonState, evaluate_all

    now = datetime.fromisoformat(args.now) if args.now else datetime.now(UTC)
    store = CheckpointStore(S3Config.from_env())
    registry = ModelRegistry(
        args.registry_root, mlflow_client=mlflow_client_from_env(), checkpoint_store=store,
    )

    def _api_get(path: str) -> dict | list | None:
        if not args.api_url:
            return None
        req = urllib.request.Request(f"{args.api_url.rstrip('/')}{path}")
        if args.api_key:
            req.add_header("X-Anemoi-Api-Key", args.api_key)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                return json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            print(f"warning: {path} unreachable ({exc}); degrading that signal to empty")
            return None

    active_storms: tuple[str, ...] = ()
    storms = _api_get("/v1/storms")
    if isinstance(storms, list):
        active_storms = tuple(s["storm_id"] for s in storms if s.get("active"))

    drifted_models: list[str] = []
    for model in ALL_MODELS:
        report = _api_get(f"/v1/monitoring/drift/{model}")
        if isinstance(report, dict) and report.get("alert"):
            drifted_models.append(model)

    skew = _api_get("/v1/monitoring/skew")
    if isinstance(skew, dict) and skew.get("alert"):
        # Real, but not acted on here: the skew audit is system-wide (one
        # paired ERA5T-vs-operational comparison of "the deterministic
        # stack"), while `on_skew(model)` needs one specific model to
        # re-fine-tune -- nothing in the scope or this codebase says which
        # model(s) a system-wide skew alert should map to. Flagged loudly
        # rather than guessed at.
        print(
            "SKEW ALERT (system-wide, §4.6.3) -- which model(s) this should "
            "re-fine-tune is not yet defined; not dispatched. See the Roadmap."
        )

    tracks = parse_hurdat2_file(args.hurdat2)
    last_trained: datetime | None = None
    for model in GROUP1_MODELS:
        try:
            created = datetime.fromisoformat(registry.latest(model).created_at)
        except RegistryError:
            continue
        if last_trained is None or created > last_trained:
            last_trained = created
    new_synoptic_times = (
        0
        if last_trained is None
        else sum(1 for t in tracks for f in t.fixes if f.valid_time > last_trained)
    )

    jobs = evaluate_all(
        now,
        SeasonState(active_storms=active_storms),
        drifted_models=tuple(drifted_models),
        new_synoptic_times=new_synoptic_times,
    )

    print(f"retrain-check: {now:%Y-%m-%d %H:%MZ}, {len(jobs)} real job(s) from evaluate_all")
    for job in jobs:
        note = f" -- {job.note}" if job.note else ""
        print(f"  {job.model:12s} {job.reason.value:18s} cascaded={job.cascaded}{note}")

    dispatchable = {Reason.SCHEDULED_MONTHLY, Reason.PRESEASON, Reason.DATA_VOLUME}
    if not any(j.reason in dispatchable for j in jobs):
        print("no dispatchable trigger fired; nothing to train")
        return 0

    other = [j.reason.value for j in jobs if j.reason not in dispatchable and j.reason != Reason.CASCADE]
    if other:
        print(f"note: also reported but not dispatched (out of this command's scope): {sorted(set(other))}")

    if args.dry_run:
        print("--dry-run: a dispatchable trigger fired, but not running training")
        return 0

    schedule = build_schedule(Mode.PARALLEL, models=GROUP1_MODELS)
    runner = RealOrchestratorRunner(
        tracks=tracks,
        checkpoint_store=store,
        era5_cache_dir=args.era5_cache_dir,
        gdas_cache_dir=args.gdas_cache_dir,
        registry=registry,
        seed=args.seed,
        n_augment=args.n_augment,
        streaming=args.streaming,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
    )
    result = run_schedule(schedule, runner)
    for outcome in result.outcomes:
        status = "OK" if outcome.ok else "FAILED"
        print(f"  [{status}] {outcome.task}: {outcome.detail}")
    print(f"succeeded: {list(result.succeeded)}")
    print(f"failed: {list(result.failed)}")
    return 0 if not result.failed else 1


def cmd_registry_pull(args: argparse.Namespace) -> int:
    """Hydrate a local registry.json from durable storage (R2/S3) when
    there's no local copy yet.

    A thin wrapper around `ModelRegistry`'s own pull-on-construction
    behavior (`tracking.registry.ModelRegistry._pull_from_checkpoint_store`)
    -- the real bootstrap step a fresh Cloudflare Container's ephemeral
    disk needs before `anemoi.api.real_state.RealState` can see any
    registered model versions at all (issue #91). Reusable both as a
    container startup step and for an operator to run by hand; unlike the
    registry's own never-fail-the-caller mirror contract, this command
    itself surfaces a real S3/R2 misconfiguration loudly (a missing/wrong
    credential run manually deserves a clear error) -- callers that want
    "never block startup over this" wrap the invocation themselves (see
    docker/api/Dockerfile's CMD).
    """
    from .tracking.checkpoint_store import CheckpointStore, S3Config
    from .tracking.registry import ALL_MODELS, ModelRegistry

    store = CheckpointStore(S3Config.from_env())
    registry = ModelRegistry(args.registry_root, checkpoint_store=store)
    total = sum(len(registry.versions(name)) for name in ALL_MODELS)
    print(
        f"registry-pull: {total} registered version(s) across {len(ALL_MODELS)} "
        f"models at {args.registry_root}"
    )
    return 0


def cmd_registry_reconcile(args: argparse.Namespace) -> int:
    """Re-evaluate staging for every model's already-registered versions
    against the real champion-vs-candidate comparison `ModelRegistry.
    champion` now uses, and correct any staging pick that isn't actually
    the best on record.

    The real, safe remediation for a real bug: `real_orchestrator.py`/
    `cli.cmd_train` used to compare each new candidate against
    `versions(...)[-1]` (whatever was registered last) instead of the
    actual current champion -- both are fixed now, but that only protects
    *future* registrations. Confirmed live against the deployed registry:
    lstm's staging pick (v7, track_error_48h_nm=300.5) was worse than two
    older, unstaged versions (v1=274.3, v2=274.6) -- exactly the failure
    mode the old comparison allowed. This command re-runs the corrected
    comparison against versions that already exist -- no training, no GPU,
    no new checkpoints, `registry.transition()` is the only state it
    touches, so it is as reversible as any other stage transition.

    Production is never touched (§5.3's manual gate stays exactly that --
    manual): a model with a production version is skipped entirely,
    win or lose.

    Re-staging a **Group 1** model can desync it from a derived model's
    recorded `latent_signature` (§5.7) -- fusion/diffusion were trained
    against a *specific* Group 1 checkpoint set, and this command doesn't
    retrain them. That's now safe rather than silently wrong:
    `training.real_inference_cycle._real_fusion_forecast` refuses a stale
    signature and degrades to the honest non-learned consensus instead of
    combining mismatched representations. This command still prints a note
    when it desyncs a signature a derived model is relying on, since
    regaining the learned combination's real benefit needs a real
    diffusion/fusion retrain (§5.7's cascade), which is genuinely out of
    this command's scope (no training, no GPU, by design).

    A second real gap this closes, found live: candidacy used to be
    metrics-only, so a version registered before #78 (no ``arch_params``
    tag -- `training.real_inference.load_trained_model` can't reconstruct
    its architecture at all) could out-score every real, loadable version
    on the metric alone and get staged anyway. Confirmed live: this
    command had staged lstm v1, cnn v5 and gnn v4 -- all pre-#78, all
    `InferenceLoadError` on every real cycle -- over newer versions that
    actually serve. Candidacy now requires a real ``arch_params`` tag and
    a real ``checkpoint_uri``, i.e. actually loadable, not just well-scored
    on paper.
    """
    import math

    from .tracking.checkpoint_store import CheckpointStore, S3Config
    from .tracking.mlflow_client import mlflow_client_from_env
    from .tracking.registry import ALL_MODELS, DERIVED_MODELS, ModelRegistry, Stage

    store = CheckpointStore(S3Config.from_env())
    registry = ModelRegistry(
        args.registry_root, mlflow_client=mlflow_client_from_env(), checkpoint_store=store,
    )

    def _finite(v) -> float | None:
        value = v.metrics.get(args.primary_metric)
        return value if isinstance(value, int | float) and math.isfinite(value) else None

    def _loadable(v) -> bool:
        return "arch_params" in v.tags and bool(v.checkpoint_uri)

    changed: list[str] = []
    for model in ALL_MODELS:
        if registry.production(model) is not None:
            print(f"{model}: has a production version -- skipped (§5.3 manual gate)")
            continue
        candidates = [v for v in registry.versions(model) if _finite(v) is not None and _loadable(v)]
        if not candidates:
            print(
                f"{model}: no version has a real, finite {args.primary_metric!r} "
                "and is actually loadable (arch_params + checkpoint_uri) -- skipped"
            )
            continue
        best = min(candidates, key=_finite)
        current = registry.in_stage(model, Stage.STAGING)
        if current is not None and current.version == best.version:
            print(f"{model}: v{best.version} already staging ({args.primary_metric}={_finite(best):.2f})")
            continue
        was = f"v{current.version}" if current is not None else "nothing"
        if args.dry_run:
            print(
                f"{model}: would re-stage v{best.version} "
                f"({args.primary_metric}={_finite(best):.2f}) in place of {was}"
            )
            continue
        registry.transition(model, best.version, Stage.STAGING)
        changed.append(model)
        print(
            f"{model}: re-staged v{best.version} "
            f"({args.primary_metric}={_finite(best):.2f}) in place of {was}"
        )
        for derived in DERIVED_MODELS:
            derived_champion = registry.champion(derived)
            if derived_champion is not None and derived_champion.latent_signature and (
                f"{model}v{best.version}" not in derived_champion.latent_signature
            ):
                print(
                    f"  note: {derived} v{derived_champion.version}'s latent_signature "
                    f"({derived_champion.latent_signature!r}) no longer includes {model} "
                    f"v{best.version} -- its learned combination will degrade to the "
                    "non-learned consensus until it's retrained against this set (§5.7)"
                )

    print(f"reconciled {len(changed)} model(s): {changed}")
    return 0


def cmd_splits(args: argparse.Namespace) -> int:
    tracks = generate_archive(args.start, args.end, seed=args.seed)
    assignment = assign_splits(tracks)
    for split, count in assignment.counts().items():
        lo, hi = assignment.boundaries[split]
        print(f"{split.value:<12} {count:>5} storms   seasons {lo}-{hi}")
    print(f"\n{len(tracks)} synthetic storms generated")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="anemoi", description=__doc__)
    parser.add_argument("--version", action="version", version=f"anemoi {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("schedule", help="print the cycle timeline for a day")
    p.add_argument("date", help="UTC date, YYYY-MM-DD")
    p.add_argument("--worst-case", action="store_true", help="use max latencies")
    p.set_defaults(func=cmd_schedule)

    p = sub.add_parser("sources", help="list data sources and their roles")
    p.set_defaults(func=cmd_sources)

    p = sub.add_parser("cycle", help="run one demo forecast cycle")
    p.add_argument("cycle", help="cycle label, e.g. 20260806_06Z")
    p.add_argument("--storm", default="AL092026")
    p.add_argument("--lat", type=float, default=22.4)
    p.add_argument("--lon", type=float, default=-72.1)
    p.add_argument("--wind", type=float, default=85.0)
    p.add_argument("--members", type=int, default=20)
    p.add_argument("--worst-case", action="store_true")
    p.set_defaults(func=cmd_cycle)

    p = sub.add_parser("splits", help="summarise synthetic archive splits")
    p.add_argument("--start", type=int, default=2015)
    p.add_argument("--end", type=int, default=2026)
    p.add_argument("--seed", type=int, default=20260806)
    p.set_defaults(func=cmd_splits)

    p = sub.add_parser(
        "registry-pull",
        help="hydrate a local registry.json from durable storage (R2/S3) if missing (#91)",
    )
    p.add_argument(
        "--registry-root", dest="registry_root",
        default=str(Path.home() / ".anemoi" / "registry"),
    )
    p.set_defaults(func=cmd_registry_pull)

    p = sub.add_parser(
        "registry-reconcile",
        help="re-stage the real best existing version per model (fixes a stale/wrong staging pick)",
    )
    p.add_argument(
        "--registry-root", dest="registry_root",
        default=str(Path.home() / ".anemoi" / "registry"),
    )
    p.add_argument("--primary-metric", dest="primary_metric", default="track_error_48h_nm")
    p.add_argument(
        "--dry-run", action="store_true", help="report what would change, without transitioning",
    )
    p.set_defaults(func=cmd_registry_reconcile)

    p = sub.add_parser("ablation", help="run the #9 capacity-vs-sample-size ablation")
    p.add_argument("--hurdat2", required=True, help="path to a real HURDAT2 archive file")
    p.add_argument(
        "--hidden-dims", dest="hidden_dims", type=int, nargs="+", default=[8, 16, 32, 64, 128]
    )
    p.add_argument(
        "--sample-fractions", dest="sample_fractions", type=float, nargs="+",
        default=[0.1, 0.25, 0.5, 1.0],
    )
    p.add_argument("--n-augment", dest="n_augment", type=int, default=3)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--seed", type=int, default=20260806)
    p.set_defaults(func=cmd_ablation)

    def _add_gridded_cache_args(p: argparse.ArgumentParser, *, default_max_workers: int) -> None:
        p.add_argument("--hurdat2", required=True, help="path to a real HURDAT2 archive file")
        p.add_argument(
            "--cache-dir", dest="cache_dir", required=True, help="local dir to cache into"
        )
        p.add_argument("--split", default="train", choices=["train", "val", "test", "operational"])
        p.add_argument("--box-deg", dest="box_deg", type=float, default=10.0)
        p.add_argument("--max-workers", dest="max_workers", type=int, default=default_max_workers)
        p.add_argument("--force", action="store_true", help="refetch even if already cached")
        p.add_argument("--progress-every", dest="progress_every", type=int, default=50)
        p.add_argument(
            "--sync-archive", dest="sync_archive", action="store_true",
            help="after fetching, upload any newly-cached files not yet in the durable "
                 "R2 archive (needs the storage extra and S3_ARTIFACT_* env vars)",
        )

    p = sub.add_parser("era5-cache", help="fetch+cache real ERA5 fields for a data.splits split")
    _add_gridded_cache_args(p, default_max_workers=8)
    p.set_defaults(func=cmd_era5_cache)

    p = sub.add_parser("gdas-cache", help="fetch+cache real GDAS fields for a data.splits split")
    _add_gridded_cache_args(p, default_max_workers=4)
    p.set_defaults(func=cmd_gdas_cache)

    p = sub.add_parser("train", help="run a real Stage A/B curriculum (#22)")
    p.add_argument("--model", default="lstm", choices=["lstm", "cnn", "transformer", "gnn", "pinn"])
    p.add_argument("--hurdat2", required=True, help="path to a real HURDAT2 archive file")
    p.add_argument("--seed", type=int, default=20260806)
    p.add_argument("--n-augment", dest="n_augment", type=int, default=3)
    p.add_argument(
        "--hidden-dim", dest="hidden_dim", type=int, default=128, help="lstm/gnn/pinn only",
    )
    p.add_argument(
        "--era5-cache-dir", dest="era5_cache_dir", default=None,
        help="cnn/transformer/gnn/pinn only: data.era5_cache's --cache-dir",
    )
    p.add_argument(
        "--gdas-cache-dir", dest="gdas_cache_dir", default=None,
        help="cnn/transformer/gnn/pinn only: data.gdas_cache's --cache-dir",
    )
    p.add_argument(
        "--registry-root", dest="registry_root",
        default=str(Path.home() / ".anemoi" / "registry"),
    )
    p.add_argument(
        "--streaming", action="store_true",
        help=(
            "train via a real per-batch DataLoader (O(batch_size) VRAM) instead of the "
            "default full-batch path (O(dataset size) VRAM) -- docs/streaming_dataloader.md"
        ),
    )
    p.add_argument(
        "--batch-size", dest="batch_size", type=int, default=None,
        help="--streaming only; default: each model's own tuned default if unset",
    )
    p.add_argument(
        "--num-workers", dest="num_workers", type=int, default=0,
        help=(
            "--streaming only; real DataLoader worker processes (default: 0, "
            "main-process loading) -- training.streaming.make_dataloader"
        ),
    )
    p.set_defaults(func=cmd_train)

    p = sub.add_parser(
        "train-schedule", help="run the full multi-model wave schedule (#22)"
    )
    p.add_argument(
        "--mode", default="sequential", choices=["sequential", "parallel"],
    )
    p.add_argument("--hurdat2", required=True, help="path to a real HURDAT2 archive file")
    p.add_argument(
        "--models", default=None,
        help="comma-separated Group 1 models to schedule (default: all five)",
    )
    p.add_argument("--seed", type=int, default=20260806)
    p.add_argument("--n-augment", dest="n_augment", type=int, default=3)
    p.add_argument("--era5-cache-dir", dest="era5_cache_dir", default=None)
    p.add_argument("--gdas-cache-dir", dest="gdas_cache_dir", default=None)
    p.add_argument(
        "--registry-root", dest="registry_root",
        default=str(Path.home() / ".anemoi" / "registry"),
    )
    p.add_argument(
        "--streaming", action="store_true",
        help=(
            "train the five Group 1 models via a real per-batch DataLoader "
            "(O(batch_size) VRAM) instead of the default full-batch path -- "
            "docs/streaming_dataloader.md. Diffusion/fusion are unaffected (no "
            "streaming path -- they train against small in-memory joint latents)."
        ),
    )
    p.add_argument(
        "--batch-size", dest="batch_size", type=int, default=None,
        help="--streaming only; default: each model's own tuned default if unset",
    )
    p.add_argument(
        "--num-workers", dest="num_workers", type=int, default=0,
        help=(
            "--streaming only; real DataLoader worker processes (default: 0, "
            "main-process loading) -- training.streaming.make_dataloader"
        ),
    )
    p.set_defaults(func=cmd_train_schedule)

    p = sub.add_parser(
        "retrain-check",
        help="evaluate real retraining triggers and dispatch training if one fires (§5.5)",
    )
    p.add_argument("--hurdat2", required=True, help="path to a real HURDAT2 archive file")
    p.add_argument(
        "--api-url", default=None,
        help="a running Anemoi API base URL, for real active-storm/drift signals "
             "(e.g. https://anemoi-api-real.<account>.workers.dev); omit to skip those "
             "signals and evaluate calendar/data-volume triggers only",
    )
    p.add_argument("--api-key", default=None, help="X-Anemoi-Api-Key, if the API requires one")
    p.add_argument(
        "--dry-run", action="store_true",
        help="evaluate and print real triggers, but never dispatch training",
    )
    p.add_argument(
        "--now", default=None,
        help="ISO datetime to evaluate triggers as-of, instead of the real current time "
             "(debugging/backtesting a specific date; unset uses real wall-clock UTC now)",
    )
    p.add_argument("--seed", type=int, default=20260806)
    p.add_argument("--n-augment", dest="n_augment", type=int, default=3)
    p.add_argument("--era5-cache-dir", dest="era5_cache_dir", default=None)
    p.add_argument("--gdas-cache-dir", dest="gdas_cache_dir", default=None)
    p.add_argument(
        "--registry-root", dest="registry_root",
        default=str(Path.home() / ".anemoi" / "registry"),
    )
    p.add_argument("--streaming", action="store_true")
    p.add_argument("--batch-size", dest="batch_size", type=int, default=None)
    p.add_argument("--num-workers", dest="num_workers", type=int, default=0)
    p.set_defaults(func=cmd_retrain_check)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


_ = timedelta  # re-exported for downstream scripts that import it from here
