# Storage and Versioning

Scope v2.1 §9.

---

## Checkpoint store (implemented)

`tracking/checkpoint_store.py` implements the real, working slice of this
page's "Warm" tier and `checkpoints/` hierarchy entry: durable upload/download
against an S3-compatible endpoint — Cloudflare R2 or AWS S3 — behind a small
duck-typed client surface, the same pattern `ModelRegistry` uses for its
MLflow client (see [Model Registry](Model-Registry)). The PostgreSQL-backed
MLflow server (below) is now real too (`docker/mlflow/`), with an optional
real client wired into `cli.cmd_train`/`cmd_train_schedule` — see
[Model Registry](Model-Registry)'s "Real MLflow server and client" section.
DVC and the ZFS NAS hot tier remain the target architecture, not yet built.

```python
from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config

store = CheckpointStore(S3Config.from_env())   # reads S3_ARTIFACT_* -- see example.env
uri = store.upload("stage_a_lstm.pt", "lstm/stage_a/v1.pt")   # -> s3://<bucket>/lstm/stage_a/v1.pt
store.download(uri, "restored.pt")
```

`S3Config.from_env()` reads `S3_ARTIFACT_API_ENDPOINT`, `S3_ARTIFACT_BUCKET`,
`S3_ARTIFACT_ACCESS_KEYID` and `S3_ARTIFACT_SECRET_ACCESS_KEY` — copy
`example.env` to `.env` (gitignored) and fill in real R2/S3 credentials.
Needs the optional `storage` extra (`uv sync --extra storage`, boto3).

This is what `training.curriculum.StageResult.checkpoint_uri` is meant to
hold once a real training run exists — see the Models row of PLAN.md §4.

---

## Hierarchy

```
storage/
├── raw_data/                    # DVC-tracked, immutable
│   ├── nhc_atcf/
│   ├── era5_reanalysis/
│   ├── gfs_analysis/
│   ├── goes_imagery/
│   └── ndbc_buoy/
├── processed_data/              # DVC-tracked, versioned
│   ├── lstm_datasets/
│   ├── transformer_datasets/
│   ├── gnn_datasets/
│   ├── cnn_datasets/
│   ├── diffusion_datasets/      # latents from Group 1 checkpoints
│   └── pinn_datasets/
├── models/                      # MLflow registry + local backup
│   ├── staging/
│   ├── production/
│   └── archived/
├── checkpoints/                 # ephemeral, 30-day TTL
├── inference_outputs/
│   └── 2026/
│       └── beryl/
│           ├── 20260806_00Z/
│           └── 20260806_06Z/
└── logs/
```

Inference output paths use the canonical cycle label, produced by `time_utils.cycle_label()` and parsed back by `parse_cycle_label()`:

```python
cycle_label(datetime(2026, 8, 6, 6, tzinfo=UTC))   # '20260806_06Z'
```

---

## Backup tiers

| Tier | Location | Retention | Purpose |
|---|---|---|---|
| **Hot** | Local ZFS NAS (SSD pool) | 90 days | Fast training data access, checkpoint recovery |
| **Warm** | Cloudflare R2 | 2 years | Model artifacts, processed datasets, inference outputs |
| **Cold** | AWS Glacier / Backblaze B2 | Permanent | Raw historical data, final model versions |

---

## Retention vs the training plan

v2's retention policy contradicted its own training plan: 1-year GOES retention and 2-year GFS retention against 1980–2025 splits. The v2.1 resolution:

| Product | Raw | Derived |
|---|---|---|
| GOES imagery | Rolling 1 year | **Storm-relative crops retained permanently** |
| Microwave | Rolling 2 years | Storm crops permanent |
| ERA5 | Rolling 10 years | Storm-relative extracts permanent (cold copy) |
| GDAS/GFS | Rolling 2 years hot | 2015–present archived |
| Best-track (both products) | Permanent | — |

Raw imagery retention stays rolling for cost. The storm-relative crops are what training actually consumes, and they are small, so they are kept forever. The CNN training archive therefore grows beyond the rolling window.

---

## MLflow artifact store

| Component | Choice |
|---|---|
| Backend store | PostgreSQL — experiment metadata, params, metrics, tags |
| Artifact store | R2 bucket — model files, checkpoints, plots, datasets |
| Tracking URI | Internal MLflow server with authentication |
| Model registry | Staging → Production → Archived |

The reference implementation's `ModelRegistry` writes a local `registry.json` first and mirrors to MLflow best-effort, so an MLflow outage never fails a training run. See [Model Registry](Model-Registry).

---

## DVC

- Tracks every preprocessing run, feature-engineering script version and raw data snapshot
- Each training run references a DVC commit hash, giving full reproducibility
- MLflow links to DVC via the `dvc_version` tag, validated against `vN.N.N[-suffix]` — see [Experiment Tracking](Experiment-Tracking)

Data rollback is a `dvc checkout` of the previous known-good version, followed by a retrain from that checkpoint. See [Operations Runbook](Operations-Runbook).

---

Related: [Data Pipeline](Data-Pipeline) · [Model Registry](Model-Registry) · [Operations Runbook](Operations-Runbook)
