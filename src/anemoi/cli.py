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
        lambda det, n: climatological_ensemble(det, n_members=min(args.members, n), seed=1),
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
    """
    from .data.hurdat2 import parse_hurdat2_file
    from .data.sources import Flavor
    from .tracking.checkpoint_store import CheckpointStore, S3Config
    from .tracking.registry import ModelRegistry
    from .training.promotion import MetricSet, evaluate_promotion

    tracks = parse_hurdat2_file(args.hurdat2)
    store = CheckpointStore(S3Config.from_env())

    if args.model == "lstm":
        from .training.real_run import run_lstm_curriculum

        run, val_metrics, _artifacts = run_lstm_curriculum(
            tracks, store, seed=args.seed, n_augment=args.n_augment, hidden_dim=args.hidden_dim,
        )
    elif args.model == "cnn":
        from .training.real_run_cnn import run_cnn_curriculum

        if not args.era5_cache_dir or not args.gdas_cache_dir:
            print("cnn needs --era5-cache-dir and --gdas-cache-dir")
            return 1
        run, val_metrics, _artifacts = run_cnn_curriculum(
            tracks, store, args.era5_cache_dir, args.gdas_cache_dir,
            seed=args.seed, n_augment=args.n_augment,
        )
    elif args.model == "transformer":
        from .training.real_run_transformer import run_transformer_curriculum

        if not args.era5_cache_dir or not args.gdas_cache_dir:
            print("transformer needs --era5-cache-dir and --gdas-cache-dir")
            return 1
        run, val_metrics, _artifacts = run_transformer_curriculum(
            tracks, store, args.era5_cache_dir, args.gdas_cache_dir,
            seed=args.seed, n_augment=args.n_augment,
        )
    elif args.model == "gnn":
        from .training.real_run_gnn import run_gnn_curriculum

        if not args.era5_cache_dir or not args.gdas_cache_dir:
            print("gnn needs --era5-cache-dir and --gdas-cache-dir")
            return 1
        run, val_metrics, _artifacts = run_gnn_curriculum(
            tracks, store, args.era5_cache_dir, args.gdas_cache_dir,
            seed=args.seed, n_augment=args.n_augment, hidden_dim=args.hidden_dim,
        )
    elif args.model == "pinn":
        from .training.real_run_pinn import run_pinn_curriculum

        if not args.era5_cache_dir or not args.gdas_cache_dir:
            print("pinn needs --era5-cache-dir and --gdas-cache-dir")
            return 1
        run, val_metrics, _artifacts = run_pinn_curriculum(
            tracks, store, args.era5_cache_dir, args.gdas_cache_dir,
            seed=args.seed, n_augment=args.n_augment, hidden_dim=args.hidden_dim,
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

    registry = ModelRegistry(args.registry_root)
    existing = registry.versions(args.model)
    incumbent_metrics = (
        MetricSet(split="val", flavor=existing[-1].input_flavor, values=existing[-1].metrics)
        if existing
        else None
    )
    version = registry.register(
        args.model,
        run_id=f"cli-{datetime.now(UTC):%Y%m%dT%H%M%S}",
        input_flavor=Flavor.GDAS_FINETUNE,
        metrics=val_metrics.values,
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
    """
    from .data.hurdat2 import parse_hurdat2_file
    from .tracking.checkpoint_store import CheckpointStore, S3Config
    from .tracking.registry import ModelRegistry
    from .training.orchestrator import Mode, build_schedule, run_schedule
    from .training.real_orchestrator import RealOrchestratorRunner

    tracks = parse_hurdat2_file(args.hurdat2)
    store = CheckpointStore(S3Config.from_env())
    registry = ModelRegistry(args.registry_root)

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
    p.set_defaults(func=cmd_train_schedule)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


_ = timedelta  # re-exported for downstream scripts that import it from here
