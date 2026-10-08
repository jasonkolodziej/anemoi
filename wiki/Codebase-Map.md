# Codebase Map

Reference implementation `anemoi` v2.1.0. Roughly 7,400 lines across source and tests. `src` layout, package `anemoi`.

```
src/anemoi/
├── __init__.py           version, Flavor, Role, cycle_label, select_nwp_cycle
├── time_utils.py         synoptic arithmetic; the t−6 NWP selection rule
├── geo.py                great-circle distance, bearings, cross/along-track
├── cli.py                schedule / sources / cycle / splits / ablation / era5-cache / gdas-cache / train (--model lstm|cnn|transformer|gnn|pinn) / train-schedule (all five as one orchestrator.run_schedule)
├── branding.py           wind-god registry: god <-> architecture, colours, modules
├── data/
│   ├── sources.py        source registry with latency + role; operational guard
│   ├── besttrack.py      working vs final tracks; Stage B noise emulator
│   ├── hurdat2.py        real HURDAT2 archive parser -> FINAL-quality Track
│   ├── atcf.py           real b-deck/TC-Vitals parsers -> WORKING-quality Fix/Track
│   ├── availability.py   what has actually published at cycle time t
│   ├── ingestion.py      fetch -> QC gate -> lake write; Fetcher/LakeWriter protocols
│   ├── features.py       one code path per flavor; flavor guards
│   ├── splits.py         storm-wise + chronological splits, leakage checks
│   ├── storm_relative.py storm-relative coordinate transform for track sequences
│   ├── synthetic.py      stand-in data generator with a deliberate GDAS bias
│   ├── satellite.py      synthetic GOES crops -> CNN channel stack (no torch dep)
│   ├── real_gridded.py   real ERA5 (Zarr) + GDAS/GFS (GRIB2) -> GriddedFields
│   ├── gridded_cache.py  source-agnostic concurrent fetch + disk cache engine, plus durable R2 archive sync (#22)
│   ├── era5_cache.py     era5-specific fetch fn over gridded_cache (Stage A)
│   └── gdas_cache.py     gdas-specific fetch fn over gridded_cache (Stage B)
├── models/
│   ├── base.py           lazy require_torch(), ModelSpec, DEFAULT_LEADS
│   ├── lstm.py cnn.py transformer.py gnn.py pinn.py
│   ├── diffusion.py      Anemoi-Spread, cosine schedule, sample()
│   └── fusion.py         context-conditioned consensus with a weight floor
├── training/
│   ├── curriculum.py     Stage A/B; assert_deployable
│   ├── promotion.py      validation-only gates; TestSetBudget
│   ├── orchestrator.py   sequential/parallel wave scheduling
│   ├── triggers.py       retrain triggers + derived-model cascade
│   ├── device.py         MPS/CUDA/CPU selection for local (non-cloud) runs
│   ├── capacity_ablation.py  #9 capacity-vs-sample-size ablation harness
│   ├── noise_sensitivity.py  #12 WorkingTrackNoise sensitivity harness
│   ├── real_run.py       real Stage A/B curriculum for the LSTM baseline (#22) -- track-only, no gridded cache needed
│   ├── real_run_cnn.py   real Stage A/B curriculum for the CNN baseline (#22) -- reads cached GriddedFields as its channel stack
│   ├── real_run_transformer.py  same for Transformer -- real 41x41 crop trimmed to the model's fixed 40x40 grid
│   ├── real_run_gnn.py   same for GNN -- cached grid treated as a lattice mesh, block-diagonal batched
│   ├── real_run_pinn.py  real Stage A/B curriculum for PINN -- corrects an internally-trained candidate LSTM's track
│   ├── real_latents.py   extracts real Anemoi-Spread/fusion conditioning latents + predictions + context from the five trained Group 1 models (#22, §5.7)
│   ├── real_run_diffusion.py  real DDPM training for Anemoi-Spread against real joint latents (#22)
│   ├── real_run_fusion.py     real masked-absolute-space training for the fusion consensus layer against real joint latents (#22)
│   └── real_orchestrator.py  wires all seven real tasks (five Group 1 + latents + diffusion + fusion) into orchestrator.run_schedule's injected runner callable
├── tracking/
│   ├── tags.py               run tags incl. input_flavor, nwp_cycle_lag
│   ├── registry.py           MLflow-optional registry; model-set pinning
│   └── checkpoint_store.py   S3/R2-compatible durable checkpoint storage
├── inference/
│   ├── scheduler.py      cycle timeline, vitals gating, load shedding
│   ├── cycle.py          execution with degraded modes
│   └── postprocess.py    cone, intensity PDF, landfall, RI
├── monitoring/
│   ├── skew.py           ERA5T paired-input audit
│   └── drift.py          feature and validation-loss drift
└── metrics/
    ├── track.py          verification, beat rate, Diebold–Mariano
    └── probabilistic.py  CRPS, Brier, spread-skill, rank histogram
```

Also at the repo root: `configs/` (three YAML files, see [Configuration Reference](Configuration-Reference)), `tests/` (36 files, see [Testing](Testing)), `docs/`, `slurm/` (SLURM-equivalent job scripts for data-ingest and real training jobs -- `#SBATCH`-headered, `sbatch`-submittable on a real cluster; `run_local.sh` emulates `sbatch` via `tmux` on the current single-VM setup, see `slurm/README.md`), `README.md`, `PLAN.md`.

---

## Key types

| Type | Module | Purpose |
|---|---|---|
| `Role`, `Flavor` | `data.sources` | What a source may be used for; which input distribution |
| `DataSource` | `data.sources` | Registry entry with latency and role |
| `Fix`, `Track`, `TrackQuality` | `data.besttrack` | Storm fixes; working/final/emulated/estimated |
| `WorkingTrackNoise` | `data.besttrack` | Measured working-vs-final error, for the emulator |
| `AvailabilityOracle` (protocol) | `data.availability` | "Has X, valid at V, published by N?" |
| `LatencyOracle` | `data.availability` | Default implementation with override and outage injection |
| `CycleInputs`, `InputStatus` | `data.availability` | Resolved input set; required/optional/opportunistic |
| `GriddedFields`, `FeatureSet` | `data.features` | Flavor-tagged fields and derived scalars |
| `FetchTask`, `FetchCacheReport`, `run_fetch_cache()`, `SyncReport`, `sync_cache_to_archive()` | `data.gridded_cache` | Source-agnostic concurrent fetch + disk cache engine, plus durable-archive sync (#22) |
| `run_fetch_cache()` | `data.era5_cache` | ERA5/Stage A fetch fn over `data.gridded_cache` |
| `run_fetch_cache()`, `GDAS_ARCHIVE_START` | `data.gdas_cache` | GDAS/Stage B fetch fn over `data.gridded_cache`; filters fixes before the real archive's verified 2021-01-01 start |
| `Normalizer` | `data.features` | Flavor-locked standardisation |
| `Split`, `SplitAssignment` | `data.splits` | Storm-wise split membership |
| `storm_relative_sequence()`, `displacement_nm()` | `data.storm_relative` | Storm-relative coordinate transform for track sequences |
| `augment_track()` | `data.besttrack` | Augmentation: independently re-emulated working tracks per FINAL storm |
| `AblationCell`, `AblationReport`, `run_capacity_ablation()` | `training.capacity_ablation` | #9 capacity-vs-sample-size ablation |
| `StageSamples`, `build_stage_samples()`, `run_lstm_curriculum()`, `boundaries_for_flavor()` | `training.real_run` | Real Stage A/B curriculum runner for the LSTM baseline (#22); durable checkpoint upload every stage |
| `CnnStageSamples`, `build_cnn_samples()`, `run_cnn_curriculum()` | `training.real_run_cnn` | CNN analog -- `x` is the real cached GriddedFields channel stack, not a track sequence |
| `TransformerStageSamples`, `build_transformer_samples()`, `run_transformer_curriculum()` | `training.real_run_transformer` | Transformer analog -- same channel stack, trimmed to the model's fixed grid size |
| `MeshTopology`, `build_mesh_topology()`, `batch_graph()`, `run_gnn_curriculum()` | `training.real_run_gnn` | GNN analog -- cached grid treated as a lattice mesh, block-diagonal batched across samples |
| `PinnStageSamples`, `build_pinn_samples()`, `run_pinn_curriculum()` | `training.real_run_pinn` | PINN analog -- corrects a candidate track from an internally-trained LSTM using a real environment vector + `physics_residuals` |
| `RunArtifacts` | `training.real_run` | Trained model + exact standardisation stats, returned by every Group 1 `run_*_curriculum()` for real latent extraction to consume (#22) |
| `JointLatentSamples`, `JointLatentBundle`, `extract_joint_latents()`, `CONTEXT_FEATURE_NAMES` | `training.real_latents` | Real per-window latents/predictions/context from the five trained Group 1 models, train/val split |
| `train_diffusion_stage()`, `run_diffusion_curriculum()` | `training.real_run_diffusion` | Real DDPM epsilon-prediction training for Anemoi-Spread against a `JointLatentBundle` |
| `train_fusion_stage()`, `run_fusion_curriculum()` | `training.real_run_fusion` | Real masked absolute-space consensus training against a `JointLatentBundle` |
| `RealOrchestratorRunner` | `training.real_orchestrator` | `Task -> RunOutcome` for `orchestrator.run_schedule`, dispatching to all seven real tasks (five Group 1 + latents + diffusion + fusion); registers + evaluates promotion, with `latent_signature` for the two derived models |
| `NoiseSensitivityReport`, `run_noise_sensitivity()` | `training.noise_sensitivity` | #12 WorkingTrackNoise sensitivity |
| `ModelSpec` | `models.base` | Architecture-independent I/O contract |
| `WindGod`, `GODS`, `god()` | `branding` | Sub-brand registry; architecture <-> god name and colour |
| `StageSpec`, `Curriculum`, `CurriculumRun` | `training.curriculum` | Two-stage training |
| `MetricSet`, `Threshold`, `TestSetBudget` | `training.promotion` | Promotion gating |
| `Mode`, `Task`, `Wave`, `Schedule` | `training.orchestrator` | Wave scheduling |
| `RetrainJob`, `Reason`, `SeasonState` | `training.triggers` | Trigger output |
| `RunTags` | `tracking.tags` | Validated MLflow tags |
| `ModelRegistry`, `ModelVersion`, `Stage` | `tracking.registry` | Versioning and pinning |
| `CheckpointStore`, `S3Config` | `tracking.checkpoint_store` | S3/R2-compatible durable checkpoint storage |
| `StageBudget`, `CyclePlan`, `ScheduledStage` | `inference.scheduler` | Cycle timeline |
| `DeterministicForecast`, `CycleOutput` | `inference.cycle` | Anemoi-Core output and payload |
| `EnsembleMember`, `ConeSegment`, `ForecastProducts` | `inference.postprocess` | Anemoi-Spread products |
| `SkewSample`, `SkewMonitor`, `SkewReport` | `monitoring.skew` | Paired audit |
| `ReferenceDistribution`, `DriftReport` | `monitoring.drift` | Drift detection |
| `VerificationPair`, `LeadTimeStats` | `metrics.track` | Scoring |
| `SpreadSkill` | `metrics.probabilistic` | Calibration diagnostic |

---

## Exceptions

Every one names the section it enforces, so a stack trace points at the policy.

| Exception | Module | Raised when |
|---|---|---|
| `NWPUnavailableError` | `time_utils` | No NWP cycle within the staleness budget |
| `OperationalUseError` | `data.sources` | A non-operational source was requested in the cycle |
| `FlavorMismatchError` | `data.features` | ERA5-derived features reached the operational path |
| `LeakageError` | `data.splits` | A storm spans splits, or ordering is violated |
| `CurriculumError` | `training.curriculum` | Curriculum misconfigured or incomplete |
| `PromotionError` | `training.promotion` | Wrong split, wrong flavor, or budget exhausted |
| `OrchestrationError` | `training.orchestrator` | Unknown model, or a dependency does not resolve |
| `RegistryError` | `tracking.registry` | Bad flavor, missing signature, or incoherent pin |
| `CheckpointStoreError` | `tracking.checkpoint_store` | Missing S3/R2 credentials, missing local file, or a URI outside the configured bucket |
| `CycleAbandoned` | `inference.scheduler` | A required input never arrived |
| `CycleError` | `inference.cycle` | Guardrail violated during execution |
| `DriftError` | `monitoring.drift` | Wrong reference flavor, or too few samples |

---

## Import cost

`import anemoi` pulls in numpy and pyyaml only. `models/__init__.py` uses lazy `__getattr__`, so torch is imported only when you actually call a builder:

```python
import anemoi                       # no torch
from anemoi.models import build_lstm  # still no torch — resolved lazily
model, spec = build_lstm()            # torch imported here
```

`require_torch()` raises a message naming the fix: `uv sync --extra torch`.

---

Related: [Getting Started](Getting-Started) · [Testing](Testing) · [Configuration Reference](Configuration-Reference)
