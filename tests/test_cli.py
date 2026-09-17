"""CLI wiring for era5-cache/gdas-cache (#22): each must select the right
data.splits boundary scheme -- ERA5 keeps the default (Stage A wants the
full 1980-2025 window), GDAS uses STAGE_B_BOUNDARIES (its real archive only
starts 2021, with zero overlap against the default train window). Exercised
directly against the cmd_* functions with monkeypatched fetch/parse so no
real network or HURDAT2 file is needed.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

import pytest

from anemoi import cli
from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.gridded_cache import FetchCacheReport
from anemoi.data.sources import Flavor
from anemoi.data.splits import STAGE_B_BOUNDARIES
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
def test_cmd_train_passes_streaming_and_batch_size_through(
    tmp_path, monkeypatch, model_name, module
):
    """--streaming/--batch-size (docs/streaming_dataloader.md) must reach
    the real run_*_curriculum call, not silently stay full-batch."""
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
    )
    assert cli.cmd_train(args) == 0
    assert captured["streaming"] is True
    assert captured["batch_size"] == 8


# --- cmd_train_schedule dispatch ---------------------------------------------


def test_cmd_train_schedule_passes_streaming_and_batch_size_to_runner(tmp_path, monkeypatch):
    """--streaming/--batch-size (docs/streaming_dataloader.md) must reach
    RealOrchestratorRunner's construction, not silently stay full-batch."""
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
    )
    assert cli.cmd_train_schedule(args) == 0
    assert captured["streaming"] is True
    assert captured["batch_size"] == 16
