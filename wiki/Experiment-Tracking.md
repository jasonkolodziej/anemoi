# Experiment Tracking

Experiment and run names follow the wind-god convention — see [Branding and Naming](Branding).

Scope v2.1 §7.2–7.3. Implemented in `tracking/tags.py` (the validated tag schema) and `tracking/experiment_tracking.py` (real, running: what actually builds a `RunTags` from a completed training run and, when MLflow is configured, logs a real run for it).

Tags are **validated**, not free-form. An untagged or mistagged run is one that cannot be found again when a forecast goes wrong, and the §10.3 post-mortem requirement depends on every run being locatable.

**This is now real, for both the MLflow and non-MLflow paths.** `experiment_tracking.build_run_tags()` constructs a real `RunTags` per completed curriculum stage — real `git_commit` (`git rev-parse HEAD`), a real `storm_split` derived from `data.splits`' own season boundaries, real `gpu_type`, `baseline_beaten` derived from the exact `nhc_consensus_beat_rate_48h` threshold `training.promotion` already gates production on. Only `dvc_version` is a placeholder (`NO_DVC_VERSION`) — DVC isn't built yet, so there's no real dataset version to report, and this stays honestly labeled as such. Every real training run (`training.real_orchestrator`, `cli.cmd_train`) builds these tags and passes them to `ModelRegistry.register(tags=...)` regardless of whether MLflow is configured — the local-JSON-only path gets real validated tags too, not just MLflow deployments.

When a real `mlflow_client` is configured (`tracking.mlflow_client.mlflow_client_from_env()`, `MLFLOW_TRACKING_URI`), `experiment_tracking.log_curriculum_stages()` also creates one real MLflow run per completed curriculum stage (Stage A and Stage B each get their own run, matching `RunTags`' own per-stage `stage_name` field) under the correct wind-god experiment name, logging the per-run verification metrics below for the deployable stage. Per-epoch metrics (`train_loss` per epoch, `gpu_utilization`, `gpu_memory_gb`) are **not** logged -- that needs changes inside every `train_*_stage`'s own epoch loop (seven files), judged more invasive than the value justifies for now; what's logged is the per-stage final loss and the full verification dict, already computed and sitting in memory once a stage completes.

---

## Run tags

| Tag | Description | Example |
|---|---|---|
| `model_type` | Architecture family | `lstm`, `transformer`, `gnn` |
| `git_commit` | Code version | `a3f7d2e` |
| `dvc_version` | Data version | `v2.4.1-storms-1980-2022` |
| `storm_split` | Which storms used | `train-1980-2019_val-2020-2022` |
| `trigger` | Why trained | `scheduled_monthly`, `drift_detected` |
| `gpu_type` | Hardware | `A100-80GB`, `RTX4090` |
| `execution_mode` | Sequential or parallel group | `sequential`, `parallel_group1` |
| **`input_flavor`** | **v2.1** — training input distribution | `era5_pretrain`, `gdas_finetune` |
| **`nwp_cycle_lag`** | **v2.1** — NWP offset at inference | `6h`, `12h` |
| `baseline_beaten` | Did it beat NHC? | `true`, `false` |
| `stage_name` | Curriculum stage | `A`, `B` |

The two v2.1 additions are what make the train/serve policy auditable after the fact. Without `input_flavor` you cannot tell from the tracking store whether a given set of weights ever saw the operational distribution.

```python
from anemoi.tracking.tags import RunTags, Trigger, ExecutionMode, validate
from anemoi.data.sources import Flavor

tags = RunTags(
    model_type="lstm",
    git_commit="a3f7d2e",
    dvc_version="v2.4.1-storms-1980-2022",
    storm_split="train-1980-2019_val-2020-2022",
    trigger=Trigger.SCHEDULED_MONTHLY,
    gpu_type="A100-80GB",
    execution_mode=ExecutionMode.PARALLEL_GROUP1,
    input_flavor=Flavor.GDAS_FINETUNE,
)
validate(tags.to_dict())
```

Validation is regex-backed: `git_commit` must be a 7–40 character hex sha, `dvc_version` must match `vN.N.N[-suffix]`, `nwp_cycle_lag` must match `\d+h`. Unknown `input_flavor` values are rejected.

---

## Metrics

### Per-epoch

`train_loss`, `val_loss`, `train_mae`, `val_mae`, `learning_rate`, `gpu_utilization`, `gpu_memory_gb`

### Per-run

Deterministic verification, per lead time (12/24/36/48/72/96/120 h) — produced by `metrics/track.to_metric_dict()`:

- `track_error_{lead}h_nm`, `track_rmse_{lead}h_nm`
- `intensity_error_{lead}h_kt`, `intensity_bias_{lead}h_kt`
- `cross_track_bias_{lead}h_nm`, `along_track_bias_{lead}h_nm`
- `nhc_consensus_beaten_{lead}h`, `ecmwf_beaten_{lead}h`
- `diebold_mariano_pvalue_{lead}h`

### v2.1 additions

- `skew_track_delta_nm_48h`, `skew_intensity_delta_kt_48h` — the paired ERA5T-vs-GDAS audit. See [Monitoring](Monitoring).

### Anemoi-Spread-specific

`ensemble_spread_{lead}h_nm`, `crps_{lead}h`, `brier_score_landfall`, `reliability_diagram_auc`

Definitions and interpretation in [Verification Metrics](Verification-Metrics).

---

## Cross/along-track decomposition

Track error is also decomposed into cross-track and along-track components, because a bias is only diagnosable once it is separated:

- **positive cross-track** — forecast lies to the right of observed storm motion
- **positive along-track** — forecast is ahead of the storm

A fast bias and a rightward bias have completely different causes. A single averaged track error hides both.

---

Related: [Model Registry](Model-Registry) · [Verification Metrics](Verification-Metrics) · [Monitoring](Monitoring)
