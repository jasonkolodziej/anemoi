"""Real MLflow experiment tracking and tagging (tracking.experiment_tracking,
Scope v2.1 §7.2-7.3, wiki Experiment-Tracking.md)."""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pytest

from anemoi.data.sources import Flavor
from anemoi.tracking import experiment_tracking as et
from anemoi.tracking.tags import ExecutionMode, Trigger
from anemoi.training.curriculum import StageResult, stage_a, stage_b
from anemoi.training.promotion import MetricSet

_HEX_SHA = re.compile(r"^[0-9a-f]{7,40}$")


# --- helpers that don't need mlflow installed -------------------------------


def test_git_commit_returns_a_real_hex_sha():
    commit = et._git_commit()
    assert commit is not None
    assert _HEX_SHA.match(commit)


def test_gpu_type_returns_a_non_empty_string():
    assert isinstance(et._gpu_type(), str)
    assert et._gpu_type()


def test_storm_split_uses_default_boundaries_for_era5_pretrain():
    from anemoi.data.splits import DEFAULT_BOUNDARIES, Split

    stage = stage_a()
    split = et._storm_split(stage)
    train_lo, train_hi = DEFAULT_BOUNDARIES[Split.TRAIN]
    val_lo, val_hi = DEFAULT_BOUNDARIES[Split.VAL]
    assert split == f"train-{train_lo}-{train_hi}_val-{val_lo}-{val_hi}"


def test_storm_split_uses_stage_b_boundaries_for_gdas_finetune():
    from anemoi.data.splits import STAGE_B_BOUNDARIES, Split

    stage = stage_b()
    split = et._storm_split(stage)
    train_lo, train_hi = STAGE_B_BOUNDARIES[Split.TRAIN]
    val_lo, val_hi = STAGE_B_BOUNDARIES[Split.VAL]
    assert split == f"train-{train_lo}-{train_hi}_val-{val_lo}-{val_hi}"


def test_baseline_beaten_is_none_without_val_metrics():
    assert et.baseline_beaten(None) is None


def test_baseline_beaten_is_none_when_metric_is_missing():
    metrics = MetricSet(
        split="val", flavor=Flavor.GDAS_FINETUNE, values={"track_error_48h_nm": 40.0},
    )
    assert et.baseline_beaten(metrics) is None


def test_baseline_beaten_matches_promotions_own_threshold():
    from anemoi.training.promotion import TRACK_THRESHOLDS

    threshold = next(t for t in TRACK_THRESHOLDS if t.metric == "nhc_consensus_beat_rate_48h")
    assert threshold.limit == et._BASELINE_BEATEN_THRESHOLD  # same number, not reinvented

    above = MetricSet(
        split="val", flavor=Flavor.GDAS_FINETUNE,
        values={"nhc_consensus_beat_rate_48h": threshold.limit + 0.01},
    )
    below = MetricSet(
        split="val", flavor=Flavor.GDAS_FINETUNE,
        values={"nhc_consensus_beat_rate_48h": threshold.limit - 0.01},
    )
    assert et.baseline_beaten(above) is True
    assert et.baseline_beaten(below) is False


def test_build_run_tags_constructs_a_real_validated_runtags():
    stage = stage_b()
    tags = et.build_run_tags("lstm", stage, execution_mode=ExecutionMode.PARALLEL_GROUP1)

    assert tags is not None
    assert tags.model_type == "lstm"
    assert _HEX_SHA.match(tags.git_commit)
    assert tags.dvc_version == et.NO_DVC_VERSION
    assert tags.trigger is Trigger.MANUAL_SWEEP
    assert tags.execution_mode is ExecutionMode.PARALLEL_GROUP1
    assert tags.input_flavor is Flavor.GDAS_FINETUNE
    assert tags.stage_name == "B"
    # to_dict() must actually be usable as a real MLflow/registry tag dict
    as_dict = tags.to_dict()
    assert as_dict["model_type"] == "lstm"
    assert as_dict["dvc_version"] == et.NO_DVC_VERSION


def test_log_stage_run_returns_none_without_a_client():
    stage = stage_a()
    result = StageResult(
        stage_name="A", flavor=Flavor.ERA5_PRETRAIN, epochs_completed=1,
        final_train_loss=1.0, final_val_loss=1.0, checkpoint_uri="s3://fake/A.pt",
    )
    assert et.log_stage_run(None, "lstm", stage, result) is None


def test_log_curriculum_stages_returns_none_without_a_client():
    from anemoi.training.curriculum import Curriculum, CurriculumRun

    curriculum = Curriculum.standard("lstm")
    run = CurriculumRun(curriculum=curriculum)
    val_metrics = MetricSet(
        split="val", flavor=Flavor.GDAS_FINETUNE, values={"track_error_48h_nm": 40.0},
    )
    assert et.log_curriculum_stages(None, "lstm", run, val_metrics) is None


# --- mlflow-dependent (real entities, stub client) --------------------------

pytest.importorskip("mlflow", reason="needs the tracking extra")


class _StubRunInfo:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id


class _StubRun:
    def __init__(self, run_id: str) -> None:
        self.info = _StubRunInfo(run_id)


class _StubMlflowClient:
    """Records every call it receives, matching the real MlflowClient
    surface `experiment_tracking` actually calls."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self._next_run_id = 0

    def get_experiment_by_name(self, name):
        self.calls.append(("get_experiment_by_name", name))
        return None

    def create_experiment(self, name):
        self.calls.append(("create_experiment", name))
        return "exp-1"

    def create_run(self, experiment_id, tags=None, run_name=None):
        self.calls.append(("create_run", experiment_id, tags, run_name))
        self._next_run_id += 1
        return _StubRun(f"run-{self._next_run_id}")

    def log_batch(self, run_id, metrics=(), params=(), tags=()):
        self.calls.append(("log_batch", run_id, list(metrics), list(params)))

    def set_terminated(self, run_id, status=None):
        self.calls.append(("set_terminated", run_id, status))


@pytest.mark.tracking
def test_log_stage_run_creates_a_real_run_under_the_wind_god_experiment_name():
    from anemoi.branding import experiment_name

    client = _StubMlflowClient()
    stage = stage_b()
    result = StageResult(
        stage_name="B", flavor=Flavor.GDAS_FINETUNE, epochs_completed=20,
        final_train_loss=0.5, final_val_loss=0.6, checkpoint_uri="s3://fake/B.pt",
        completed_at=datetime(2026, 8, 6, tzinfo=UTC),
    )
    val_metrics = MetricSet(
        split="val", flavor=Flavor.GDAS_FINETUNE, values={"track_error_48h_nm": 40.0},
    )

    run_id = et.log_stage_run(client, "lstm", stage, result, val_metrics=val_metrics)

    assert run_id == "run-1"
    create_run_call = next(c for c in client.calls if c[0] == "create_run")
    assert create_run_call[1] == "exp-1"  # from create_experiment's stubbed return
    assert create_run_call[3] == "lstm-B"
    tags = create_run_call[2]
    assert tags["model_type"] == "lstm"
    assert tags["stage_name"] == "B"

    log_batch_call = next(c for c in client.calls if c[0] == "log_batch")
    metric_keys = {m.key for m in log_batch_call[2]}
    assert {"train_loss", "val_loss", "track_error_48h_nm"} <= metric_keys
    param_dict = {p.key: p.value for p in log_batch_call[3]}
    assert param_dict["checkpoint_uri"] == "s3://fake/B.pt"
    assert param_dict["epochs_completed"] == "20"

    assert ("set_terminated", "run-1", "FINISHED") in client.calls
    assert experiment_name("lstm") == "boreas"  # sanity: the real branding mapping used above


@pytest.mark.tracking
def test_log_stage_run_degrades_silently_on_mlflow_failure():
    class BrokenClient:
        def get_experiment_by_name(self, name):
            raise RuntimeError("mlflow unreachable")

    stage = stage_a()
    result = StageResult(
        stage_name="A", flavor=Flavor.ERA5_PRETRAIN, epochs_completed=1,
        final_train_loss=1.0, final_val_loss=1.0, checkpoint_uri="s3://fake/A.pt",
    )
    assert et.log_stage_run(BrokenClient(), "lstm", stage, result) is None


@pytest.mark.tracking
def test_log_curriculum_stages_attaches_val_metrics_only_to_the_deployable_stage():
    from anemoi.training.curriculum import Curriculum, CurriculumRun

    client = _StubMlflowClient()
    curriculum = Curriculum.standard("lstm")
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
    val_metrics = MetricSet(
        split="val", flavor=Flavor.GDAS_FINETUNE, values={"track_error_48h_nm": 40.0},
    )

    deployable_run_id = et.log_curriculum_stages(client, "lstm", run, val_metrics)

    assert deployable_run_id == "run-2"  # the second (Stage B) run created
    log_batch_calls = [c for c in client.calls if c[0] == "log_batch"]
    assert len(log_batch_calls) == 2
    stage_a_metrics = {m.key for m in log_batch_calls[0][2]}
    stage_b_metrics = {m.key for m in log_batch_calls[1][2]}
    assert "track_error_48h_nm" not in stage_a_metrics
    assert "track_error_48h_nm" in stage_b_metrics
