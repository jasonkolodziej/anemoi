"""CLI wiring for era5-cache/gdas-cache (#22): each must select the right
data.splits boundary scheme -- ERA5 keeps the default (Stage A wants the
full 1980-2025 window), GDAS uses STAGE_B_BOUNDARIES (its real archive only
starts 2021, with zero overlap against the default train window). Exercised
directly against the cmd_* functions with monkeypatched fetch/parse so no
real network or HURDAT2 file is needed.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta

import pytest

from anemoi import cli
from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.gridded_cache import FetchCacheReport
from anemoi.data.sources import Flavor
from anemoi.data.splits import STAGE_B_BOUNDARIES
from anemoi.tracking.registry import ModelRegistry, Stage
from anemoi.training.curriculum import Curriculum, CurriculumRun, StageResult


def make_track(storm_id: str, season: int) -> Track:
    fix = Fix(
        storm_id=storm_id,
        valid_time=datetime(season, 8, 1, tzinfo=UTC),
        lat=20.0,
        lon=-60.0,
        max_wind_kt=60.0,
        min_pressure_mb=990.0,
        quality=TrackQuality.FINAL,
    )
    return Track(storm_id=storm_id, fixes=(fix,))


def make_args(tmp_path, **overrides) -> argparse.Namespace:
    defaults = dict(
        hurdat2="unused.txt",
        cache_dir=str(tmp_path),
        split="train",
        box_deg=10.0,
        max_workers=2,
        force=False,
        progress_every=0,
        sync_archive=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _empty_report() -> FetchCacheReport:
    return FetchCacheReport(n_total=0, n_fetched=0, n_skipped=0)


def _spy_assign_splits(monkeypatch, captured: dict) -> None:
    import anemoi.data.splits as splits_module

    real_assign_splits = splits_module.assign_splits

    def spy(tracks_, boundaries=None):
        captured["boundaries"] = boundaries
        return real_assign_splits(tracks_, boundaries)

    monkeypatch.setattr(splits_module, "assign_splits", spy)


def test_cmd_gdas_cache_selects_stage_b_boundaries(tmp_path, monkeypatch):
    tracks = [make_track("AL01", 2021)]
    monkeypatch.setattr("anemoi.data.hurdat2.parse_hurdat2_file", lambda path: tracks)
    monkeypatch.setattr(
        "anemoi.data.gdas_cache.run_fetch_cache", lambda tracks_, cache_dir, **kw: _empty_report()
    )
    captured: dict = {}
    _spy_assign_splits(monkeypatch, captured)

    assert cli.cmd_gdas_cache(make_args(tmp_path)) == 0
    assert captured["boundaries"] is STAGE_B_BOUNDARIES


def test_cmd_era5_cache_keeps_the_default_boundaries(tmp_path, monkeypatch):
    tracks = [make_track("AL01", 1985)]
    monkeypatch.setattr("anemoi.data.hurdat2.parse_hurdat2_file", lambda path: tracks)
    monkeypatch.setattr(
        "anemoi.data.era5_cache.run_fetch_cache", lambda tracks_, cache_dir, **kw: _empty_report()
    )
    captured: dict = {}
    _spy_assign_splits(monkeypatch, captured)

    assert cli.cmd_era5_cache(make_args(tmp_path)) == 0
    assert captured["boundaries"] is None  # cmd_era5_cache passes no override


# --- cmd_train dispatch -----------------------------------------------------
#
# Regression coverage for a real bug: #22's real-latent-extraction work
# (training.real_run.RunArtifacts) changed every run_*_curriculum from
# returning (run, val_metrics) to (run, val_metrics, artifacts), but
# cli.cmd_train's five call sites still unpacked the old 2-tuple -- a
# ValueError on every real `anemoi train --model X` invocation that no
# test caught, since cmd_train had no test coverage at all before this.

_FAKE_METRICS_VALUES = {
    "track_error_48h_nm": 40.0,
    "track_error_72h_nm": 60.0,
    "track_error_120h_nm": 100.0,
    "intensity_error_48h_kt": 5.0,
    "intensity_error_72h_kt": 6.0,
    "nhc_consensus_beat_rate_48h": 0.6,
    "track_error_12h_nm": 10.0,
}


def _fake_curriculum_run(model_name: str):
    from anemoi.training.promotion import MetricSet

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
    metrics = MetricSet(split="val", flavor=Flavor.GDAS_FINETUNE, values=dict(_FAKE_METRICS_VALUES))
    return run, metrics, object()  # 3rd element: RunArtifacts stand-in, unused by cmd_train


def _fake_checkpoint_store(monkeypatch) -> None:
    monkeypatch.setattr(
        "anemoi.tracking.checkpoint_store.S3Config",
        type("FakeS3Config", (), {"from_env": staticmethod(lambda: "fake-config")}),
    )
    monkeypatch.setattr(
        "anemoi.tracking.checkpoint_store.CheckpointStore", lambda config: "fake-store"
    )


@pytest.mark.parametrize(
    ("model_name", "module"),
    [
        ("lstm", "anemoi.training.real_run"),
        ("cnn", "anemoi.training.real_run_cnn"),
        ("transformer", "anemoi.training.real_run_transformer"),
        ("gnn", "anemoi.training.real_run_gnn"),
        ("pinn", "anemoi.training.real_run_pinn"),
    ],
)
def test_cmd_train_unpacks_the_real_three_tuple_for_every_model(
    tmp_path, monkeypatch, model_name, module
):
    monkeypatch.setattr(
        f"{module}.run_{model_name}_curriculum",
        lambda *args, **kwargs: _fake_curriculum_run(model_name),
    )
    _fake_checkpoint_store(monkeypatch)
    monkeypatch.setattr("anemoi.data.hurdat2.parse_hurdat2_file", lambda path: [])

    args = argparse.Namespace(
        model=model_name, hurdat2="unused.txt", seed=1, n_augment=1, hidden_dim=8,
        era5_cache_dir=str(tmp_path), gdas_cache_dir=str(tmp_path),
        registry_root=str(tmp_path / "registry"), streaming=False, batch_size=None,
        num_workers=0,
    )
    assert cli.cmd_train(args) == 0


@pytest.mark.parametrize(
    ("model_name", "module"),
    [
        ("lstm", "anemoi.training.real_run"),
        ("cnn", "anemoi.training.real_run_cnn"),
        ("transformer", "anemoi.training.real_run_transformer"),
        ("gnn", "anemoi.training.real_run_gnn"),
        ("pinn", "anemoi.training.real_run_pinn"),
    ],
)
def test_cmd_train_passes_streaming_batch_size_and_num_workers_through(
    tmp_path, monkeypatch, model_name, module
):
    """--streaming/--batch-size/--num-workers (docs/streaming_dataloader.md)
    must reach the real run_*_curriculum call, not silently stay
    full-batch or single-process."""
    captured: dict = {}

    def fake_curriculum(*args, **kwargs):
        captured.update(kwargs)
        return _fake_curriculum_run(model_name)

    monkeypatch.setattr(f"{module}.run_{model_name}_curriculum", fake_curriculum)
    _fake_checkpoint_store(monkeypatch)
    monkeypatch.setattr("anemoi.data.hurdat2.parse_hurdat2_file", lambda path: [])

    args = argparse.Namespace(
        model=model_name, hurdat2="unused.txt", seed=1, n_augment=1, hidden_dim=8,
        era5_cache_dir=str(tmp_path), gdas_cache_dir=str(tmp_path),
        registry_root=str(tmp_path / "registry"), streaming=True, batch_size=8,
        num_workers=2,
    )
    assert cli.cmd_train(args) == 0
    assert captured["streaming"] is True
    assert captured["batch_size"] == 8
    assert captured["num_workers"] == 2


def test_cmd_train_actually_transitions_a_promotable_candidate_to_staging(
    tmp_path, monkeypatch
):
    """A real, previously-undiscovered bug: `evaluate_promotion`'s decision
    was computed and printed but never applied -- every real version stayed
    Stage.NONE regardless of a `staging=True` print, so no real cycle could
    ever find an eligible model (#91's Cloudflare deployment work is what
    surfaced this: /v1/registry showed every version at stage=none despite
    training logs claiming otherwise)."""
    monkeypatch.setattr(
        "anemoi.training.real_run.run_lstm_curriculum",
        lambda *args, **kwargs: _fake_curriculum_run("lstm"),
    )
    _fake_checkpoint_store(monkeypatch)
    monkeypatch.setattr("anemoi.data.hurdat2.parse_hurdat2_file", lambda path: [])

    registry_root = tmp_path / "registry"
    args = argparse.Namespace(
        model="lstm", hurdat2="unused.txt", seed=1, n_augment=1, hidden_dim=8,
        era5_cache_dir=str(tmp_path), gdas_cache_dir=str(tmp_path),
        registry_root=str(registry_root), streaming=False, batch_size=None,
        num_workers=0,
    )
    assert cli.cmd_train(args) == 0

    registry = ModelRegistry(registry_root)  # a fresh read, not the same in-memory object
    assert registry.latest("lstm").version == 1
    assert registry.latest("lstm").stage is Stage.STAGING


# --- cmd_train_schedule dispatch ---------------------------------------------


def test_cmd_train_schedule_passes_streaming_batch_size_and_num_workers_to_runner(
    tmp_path, monkeypatch
):
    """--streaming/--batch-size/--num-workers (docs/streaming_dataloader.md)
    must reach RealOrchestratorRunner's construction, not silently stay
    full-batch or single-process."""
    captured: dict = {}

    class FakeRunner:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    class FakeResult:
        outcomes: list = []
        skipped: list = []
        succeeded: list = []
        failed: list = []

    monkeypatch.setattr("anemoi.training.real_orchestrator.RealOrchestratorRunner", FakeRunner)
    monkeypatch.setattr(
        "anemoi.training.orchestrator.run_schedule", lambda schedule, runner: FakeResult()
    )
    monkeypatch.setattr("anemoi.tracking.registry.ModelRegistry", lambda *a, **k: object())
    monkeypatch.setattr("anemoi.tracking.mlflow_client.mlflow_client_from_env", lambda: None)
    _fake_checkpoint_store(monkeypatch)
    monkeypatch.setattr("anemoi.data.hurdat2.parse_hurdat2_file", lambda path: [])

    args = argparse.Namespace(
        mode="sequential", hurdat2="unused.txt", models=None, seed=1, n_augment=1,
        era5_cache_dir=str(tmp_path), gdas_cache_dir=str(tmp_path),
        registry_root=str(tmp_path / "registry"), streaming=True, batch_size=16,
        num_workers=3,
    )
    assert cli.cmd_train_schedule(args) == 0
    assert captured["streaming"] is True
    assert captured["batch_size"] == 16
    assert captured["num_workers"] == 3


# --- cmd_retrain_check dispatch ----------------------------------------------
#
# `evaluate_all` (training.triggers) has been real and well-tested since #22,
# but nothing outside tests ever called it -- confirmed by grep. These cover
# the missing wiring: real signal-gathering (HURDAT2 data volume, a best-
# effort API query) feeding evaluate_all, and dispatch restricted to the
# three trigger shapes that actually match train-schedule's own schedule.


def _retrain_check_args(tmp_path, **overrides) -> argparse.Namespace:
    defaults = dict(
        hurdat2="unused.txt", api_url=None, api_key=None, dry_run=True, now=None,
        seed=1, n_augment=1, era5_cache_dir=str(tmp_path), gdas_cache_dir=str(tmp_path),
        registry_root=str(tmp_path / "registry"), streaming=False, batch_size=None,
        num_workers=0,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_retrain_check_reports_no_dispatchable_trigger_on_an_ordinary_day(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr("anemoi.data.hurdat2.parse_hurdat2_file", lambda path: [])
    monkeypatch.setattr("anemoi.tracking.mlflow_client.mlflow_client_from_env", lambda: None)
    _fake_checkpoint_store(monkeypatch)
    args = _retrain_check_args(tmp_path, now="2026-09-15T00:00:00+00:00")

    assert cli.cmd_retrain_check(args) == 0
    out = capsys.readouterr().out
    assert "0 real job(s)" in out
    assert "no dispatchable trigger fired" in out


def test_retrain_check_computes_real_data_volume_from_hurdat2(tmp_path, monkeypatch, capsys):
    """§5.5's data-volume trigger (>500 new synoptic times since last
    training) must be evaluated against a real count, not a stub -- register
    an old lstm version, then give it a HURDAT2 track with 501 fixes after
    that version's created_at."""
    registry = ModelRegistry(tmp_path / "registry")
    registry.register(
        "lstm", run_id="old", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 100.0},
    )
    old_version = registry.latest("lstm")
    old_version.created_at = "2020-01-01T00:00:00+00:00"
    registry._save()  # noqa: SLF001 - test-only, to backdate created_at realistically

    # 501 distinct, real, strictly-increasing synoptic times (6h apart).
    base = datetime(2020, 1, 2, tzinfo=UTC)
    fixes = tuple(
        Fix(
            storm_id="AL99", valid_time=base + timedelta(hours=6 * (i + 1)),
            lat=20.0, lon=-60.0, max_wind_kt=60.0, min_pressure_mb=990.0,
            quality=TrackQuality.FINAL,
        )
        for i in range(501)
    )
    track = Track(storm_id="AL99", fixes=fixes)
    monkeypatch.setattr("anemoi.data.hurdat2.parse_hurdat2_file", lambda path: [track])
    monkeypatch.setattr("anemoi.tracking.mlflow_client.mlflow_client_from_env", lambda: None)
    _fake_checkpoint_store(monkeypatch)

    args = _retrain_check_args(tmp_path, now="2026-09-15T00:00:00+00:00")
    assert cli.cmd_retrain_check(args) == 0
    out = capsys.readouterr().out
    assert "data_volume" in out
    assert "no dispatchable trigger fired" not in out
    assert "--dry-run" in out  # dry_run=True by default here -- must not dispatch


def test_retrain_check_dispatches_the_real_schedule_when_a_trigger_fires(
    tmp_path, monkeypatch, capsys
):
    """A dispatchable trigger (here: data volume) must invoke the exact same
    real machinery `train-schedule` uses -- RealOrchestratorRunner +
    orchestrator.run_schedule -- not a parallel, untested dispatch path."""
    registry = ModelRegistry(tmp_path / "registry")
    registry.register(
        "lstm", run_id="old", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 100.0},
    )
    old_version = registry.latest("lstm")
    old_version.created_at = "2020-01-01T00:00:00+00:00"
    registry._save()  # noqa: SLF001

    base = datetime(2020, 1, 2, tzinfo=UTC)
    fixes = tuple(
        Fix(
            storm_id="AL99", valid_time=base + timedelta(hours=6 * (i + 1)),
            lat=20.0, lon=-60.0, max_wind_kt=60.0, min_pressure_mb=990.0,
            quality=TrackQuality.FINAL,
        )
        for i in range(501)
    )
    track = Track(storm_id="AL99", fixes=fixes)
    monkeypatch.setattr("anemoi.data.hurdat2.parse_hurdat2_file", lambda path: [track])

    captured: dict = {}

    class FakeRunner:
        def __init__(self, **kwargs):
            captured["runner_kwargs"] = kwargs

    class FakeResult:
        outcomes: list = []
        skipped: list = []
        succeeded: list = ["lstm", "cnn", "transformer", "gnn", "pinn", "diffusion", "fusion"]
        failed: list = []

    def fake_run_schedule(schedule, runner):
        captured["schedule_models"] = sorted(
            t.name for wave in schedule.waves for t in wave.tasks if t.kind == "train"
            and t.name in {"lstm", "cnn", "transformer", "gnn", "pinn"}
        )
        return FakeResult()

    monkeypatch.setattr("anemoi.training.real_orchestrator.RealOrchestratorRunner", FakeRunner)
    monkeypatch.setattr("anemoi.training.orchestrator.run_schedule", fake_run_schedule)
    monkeypatch.setattr("anemoi.tracking.mlflow_client.mlflow_client_from_env", lambda: None)
    _fake_checkpoint_store(monkeypatch)

    args = _retrain_check_args(tmp_path, now="2026-09-15T00:00:00+00:00", dry_run=False)
    assert cli.cmd_retrain_check(args) == 0
    assert captured["schedule_models"] == ["cnn", "gnn", "lstm", "pinn", "transformer"]
    out = capsys.readouterr().out
    assert "succeeded:" in out


def test_retrain_check_degrades_to_an_empty_season_when_the_api_is_unreachable(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr("anemoi.data.hurdat2.parse_hurdat2_file", lambda path: [])
    monkeypatch.setattr("anemoi.tracking.mlflow_client.mlflow_client_from_env", lambda: None)
    _fake_checkpoint_store(monkeypatch)
    args = _retrain_check_args(
        tmp_path, now="2026-09-15T00:00:00+00:00", api_url="http://127.0.0.1:1",
    )
    assert cli.cmd_retrain_check(args) == 0
    out = capsys.readouterr().out
    assert "warning:" in out
    assert "no dispatchable trigger fired" in out


# --- cmd_registry_reconcile --------------------------------------------------


def _reconcile_args(tmp_path, **overrides) -> argparse.Namespace:
    defaults = dict(
        registry_root=str(tmp_path / "registry"), primary_metric="track_error_48h_nm",
        dry_run=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_registry_reconcile_re_stages_the_real_best_existing_version(tmp_path, monkeypatch, capsys):
    """The exact live bug this closes: a worse v3 reached staging (comparing
    against v2, not the true champion v1) while a better v1 sat unstaged.
    Reconcile must find v1 and re-stage it, without retraining anything."""
    monkeypatch.setattr("anemoi.tracking.mlflow_client.mlflow_client_from_env", lambda: None)
    _fake_checkpoint_store(monkeypatch)

    registry = ModelRegistry(tmp_path / "registry")
    v1 = registry.register(
        "lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 274.3},
    )
    registry.register(
        "lstm", run_id="b", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 274.6},
    )
    v3 = registry.register(
        "lstm", run_id="c", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 300.0},
    )
    registry.transition("lstm", v3.version, Stage.STAGING)

    args = _reconcile_args(tmp_path)
    assert cli.cmd_registry_reconcile(args) == 0
    out = capsys.readouterr().out
    assert "lstm: re-staged v1" in out

    fresh = ModelRegistry(tmp_path / "registry")  # a fresh read, not the same in-memory object
    assert fresh.in_stage("lstm", Stage.STAGING).version == v1.version
    assert fresh.get("lstm", v3.version).stage is Stage.ARCHIVED


def test_registry_reconcile_dry_run_reports_without_transitioning(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("anemoi.tracking.mlflow_client.mlflow_client_from_env", lambda: None)
    _fake_checkpoint_store(monkeypatch)

    registry = ModelRegistry(tmp_path / "registry")
    registry.register(
        "lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 274.3},
    )
    v2 = registry.register(
        "lstm", run_id="b", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 300.0},
    )
    registry.transition("lstm", v2.version, Stage.STAGING)

    args = _reconcile_args(tmp_path, dry_run=True)
    assert cli.cmd_registry_reconcile(args) == 0
    out = capsys.readouterr().out
    assert "would re-stage v1" in out

    fresh = ModelRegistry(tmp_path / "registry")
    assert fresh.in_stage("lstm", Stage.STAGING).version == v2.version  # unchanged


def test_registry_reconcile_ignores_nan_metrics(tmp_path, monkeypatch, capsys):
    """A real found bug in the reconcile logic itself: `min()` over values
    including NaN is unreliable (NaN never compares less than anything),
    so a real early/degenerate run with a NaN metric could get picked as
    'best' purely by iteration order. Confirmed live: several deployed
    models' v1 had a NaN track_error_48h_nm. NaN candidates must be
    excluded outright, not merely deprioritised."""
    monkeypatch.setattr("anemoi.tracking.mlflow_client.mlflow_client_from_env", lambda: None)
    _fake_checkpoint_store(monkeypatch)

    registry = ModelRegistry(tmp_path / "registry")
    registry.register(
        "cnn", run_id="a", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": float("nan")},
    )
    v2 = registry.register(
        "cnn", run_id="b", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 250.0},
    )
    registry.transition("cnn", v2.version, Stage.STAGING)

    args = _reconcile_args(tmp_path)
    assert cli.cmd_registry_reconcile(args) == 0
    out = capsys.readouterr().out
    assert "cnn: v2 already staging" in out

    fresh = ModelRegistry(tmp_path / "registry")
    assert fresh.in_stage("cnn", Stage.STAGING).version == v2.version


def test_registry_reconcile_warns_when_it_desyncs_a_derived_models_signature(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr("anemoi.tracking.mlflow_client.mlflow_client_from_env", lambda: None)
    _fake_checkpoint_store(monkeypatch)

    registry = ModelRegistry(tmp_path / "registry")
    v1 = registry.register(
        "lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 274.3},
    )
    v2 = registry.register(
        "lstm", run_id="b", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 300.0},
    )
    registry.transition("lstm", v2.version, Stage.STAGING)
    fusion = registry.register(
        "fusion", run_id="c", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 250.0},
        latent_signature=f"lstmv{v2.version}-cnnv1-transformerv1-gnnv1-pinnv1",
    )
    registry.transition("fusion", fusion.version, Stage.STAGING)

    args = _reconcile_args(tmp_path)
    assert cli.cmd_registry_reconcile(args) == 0
    out = capsys.readouterr().out
    assert f"lstm: re-staged v{v1.version}" in out
    assert "fusion v" in out and "latent_signature" in out and "no longer includes lstm" in out


def test_registry_reconcile_never_touches_a_model_with_a_production_version(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr("anemoi.tracking.mlflow_client.mlflow_client_from_env", lambda: None)
    _fake_checkpoint_store(monkeypatch)

    registry = ModelRegistry(tmp_path / "registry")
    v1 = registry.register(
        "lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 300.0},
    )
    registry.register(
        "lstm", run_id="b", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={"track_error_48h_nm": 274.3},
    )
    registry.transition("lstm", v1.version, Stage.PRODUCTION)  # the worse one, deliberately

    args = _reconcile_args(tmp_path)
    assert cli.cmd_registry_reconcile(args) == 0
    out = capsys.readouterr().out
    assert "skipped (§5.3 manual gate)" in out

    fresh = ModelRegistry(tmp_path / "registry")
    assert fresh.production("lstm").version == v1.version  # untouched


def test_cmd_registry_pull_hydrates_from_durable_storage(tmp_path, monkeypatch, capsys):
    """#91: a fresh Cloudflare Container's ephemeral disk has no local
    registry.json -- this command is the bootstrap step that pulls one
    from durable storage before the API starts."""
    import json

    remote = json.dumps(
        {
            "versions": {
                "lstm": [
                    {
                        "name": "lstm", "version": 1, "stage": "staging", "run_id": "r1",
                        "input_flavor": "gdas_finetune",
                        "metrics": {"track_error_48h_nm": 40.0}, "tags": {},
                        "latent_signature": None,
                        "created_at": "2026-01-01T00:00:00+00:00",
                        "checkpoint_uri": "s3://bucket/lstm.pt",
                    }
                ]
            },
            "pins": {},
        }
    )

    class FakeStore:
        config = type("Cfg", (), {"bucket": "fake-bucket"})()

        def exists(self, key):
            return True

        def download(self, uri, local_path):
            local_path.write_text(remote)

    monkeypatch.setattr(
        "anemoi.tracking.checkpoint_store.S3Config",
        type("FakeS3Config", (), {"from_env": staticmethod(lambda: "fake-config")}),
    )
    monkeypatch.setattr(
        "anemoi.tracking.checkpoint_store.CheckpointStore", lambda config: FakeStore()
    )

    args = argparse.Namespace(registry_root=str(tmp_path / "registry"))
    assert cli.cmd_registry_pull(args) == 0

    out = capsys.readouterr().out
    assert "1 registered version(s) across 7 models" in out
    assert (tmp_path / "registry" / "registry.json").exists()
