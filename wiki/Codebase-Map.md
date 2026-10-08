# Codebase Map

Reference implementation `anemoi` v2.2.0. Roughly 22,000 lines of Python under `src/` and 16,000 in `tests/` (68 files), plus the TypeScript Worker in `docker/api` and the SvelteKit console in `console/`. `src` layout, package `anemoi`.

```
src/anemoi/
├── __init__.py           version, Flavor, Role, cycle_label, select_nwp_cycle
├── time_utils.py         synoptic arithmetic; the t−6 NWP selection rule
├── geo.py                great-circle distance, bearings, cross/along-track
├── branding.py           wind-god registry: god <-> architecture, colours, modules
├── cli.py                schedule · sources · cycle · splits · ablation · era5-cache · gdas-cache ·
│                         train · train-schedule · retrain-check · registry-pull · registry-reconcile ·
│                         drift-reference-fit · spread-backtest · consistency-distill · skew-audit
├── api/                  Anemoi-API (FastAPI; `uv sync --extra api`)
│   ├── main.py           app factory, CORS, error handlers; builds RealState at startup
│   ├── deps.py           DemoState vs RealState selection; optional API-key gate
│   ├── demo_state.py     synthetic storms + seeded registry/drift/skew
│   ├── real_state.py     real HURDAT2 archive + live NHC storms, real cycles, monitoring
│   ├── cycle_store.py    served CycleResults + drift window persisted to R2 (#175)
│   ├── schemas.py        Pydantic request/response models; CyclePayload is a persisted shape
│   ├── convert.py        dataclass -> Pydantic conversion
│   ├── docs.py           Anemoi-themed /redoc
│   ├── stream.py         WS /v1/storms/{id}/stream
│   └── routers/          meta · schedule · storms · registry · monitoring · retraining ·
│                         internal (operator-only, e.g. POST /v1/internal/calibration-audit)
├── data/
│   ├── sources.py        source registry with latency + role; operational guard
│   ├── besttrack.py      working vs final tracks; Stage B noise emulator
│   ├── hurdat2.py        real HURDAT2 archive parser -> FINAL-quality Track
│   ├── atcf.py           real b-deck/TC-Vitals parsers -> WORKING-quality Fix/Track
│   ├── live_atcf.py      live NHC feed: CurrentStorms.json + per-storm TC-Vitals (fetched concurrently)
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
│   ├── gdas_cache.py     gdas-specific fetch fn over gridded_cache (Stage B)
│   ├── real_goes.py      GOES-18/19 ABI imagery + derived products -> SatelliteCrop (#146)
│   ├── real_microwave.py RSS SSMIS microwave radiometer data (#147)
│   ├── real_dropsonde.py NOAA/AFRC dropsonde profiles (#147)
│   ├── real_ndbc.py      NDBC buoy / C-MAN observations (#147)
│   ├── real_sst.py       NCEI OISST v2.1 sea surface temperature (#147)
│   └── real_ensemble.py  NOAA GEFS ensemble perturbation members (#147)
├── models/
│   ├── base.py           lazy require_torch(), ModelSpec, DEFAULT_LEADS
│   ├── lstm.py cnn.py transformer.py gnn.py pinn.py
│   ├── diffusion.py      Anemoi-Spread, cosine schedule, sample()
│   ├── consistency.py    consistency model distilled from the diffusion model (#15, evaluated, not adopted)
│   └── fusion.py         context-conditioned consensus with a weight floor
├── training/
│   ├── curriculum.py     Stage A/B; assert_deployable
│   ├── promotion.py      validation-only gates; TestSetBudget
│   ├── orchestrator.py   sequential/parallel wave scheduling
│   ├── triggers.py       retrain triggers + derived-model cascade
│   ├── device.py         MPS/CUDA/CPU selection for local (non-cloud) runs
│   ├── streaming.py      per-batch torch DataLoader for large cached datasets (#22)
│   ├── capacity_ablation.py  #9 capacity-vs-sample-size ablation harness
│   ├── noise_sensitivity.py  #12 WorkingTrackNoise sensitivity harness
│   ├── real_run.py       real Stage A/B curriculum for the LSTM baseline (#22) -- track-only, no gridded cache needed
│   ├── real_run_cnn.py   same for CNN -- reads cached GriddedFields as its channel stack
│   ├── real_run_transformer.py  same for Transformer -- real 41x41 crop trimmed to the model's fixed 40x40 grid
│   ├── real_run_gnn.py   same for GNN -- cached grid treated as a lattice mesh, block-diagonal batched
│   ├── real_run_pinn.py  same for PINN -- corrects an internally-trained candidate LSTM's track
│   ├── real_latents.py   real Anemoi-Spread/fusion conditioning latents from the five trained Group 1 models (#22, §5.7)
│   ├── real_run_diffusion.py  real DDPM training for Anemoi-Spread against real joint latents (#22)
│   ├── real_run_fusion.py     real masked-absolute-space training for the fusion layer (#22)
│   ├── real_orchestrator.py   all seven real tasks wired into orchestrator.run_schedule
│   ├── real_inference.py      rebuild a trained model from its registered checkpoint (#78)
│   ├── real_inference_live.py real-time feature building for live inference (#78)
│   ├── real_inference_cycle.py    real deterministic_fn for inference.cycle.run_cycle (#78, #85)
│   ├── real_inference_ensemble.py real ensemble_fn (seeded per cycle) for run_cycle (#78, #85, #188)
│   ├── spread_backtest.py     Anemoi-Spread calibration backtest (#10)
│   └── consistency_distillation.py  consistency distillation for Anemoi-Spread (#15)
├── tracking/
│   ├── tags.py               run tags incl. input_flavor, nwp_cycle_lag
│   ├── registry.py           MLflow-optional registry; model-set pinning
│   ├── checkpoint_store.py   S3/R2-compatible durable checkpoint storage
│   ├── experiment_tracking.py  real MLflow experiment tracking and tagging (§7.2–7.3)
│   ├── mlflow_client.py      optional real MLflow client construction
│   └── cloudflare_access.py  Cloudflare Access service-token headers for the MLflow client
├── inference/
│   ├── scheduler.py      cycle timeline, vitals gating, load shedding
│   ├── cycle.py          execution with degraded modes
│   └── postprocess.py    cone, intensity PDF, landfall, RI (with Wilson interval)
├── monitoring/
│   ├── skew.py           ERA5T paired-input audit
│   ├── skew_audit.py     real ERA5T-vs-operational replay of served cycles (#148)
│   ├── drift.py          feature and validation-loss drift
│   ├── reference_store.py    durable ReferenceDistribution persistence (#148)
│   └── calibration_audit.py  served cone/intensity containment against later fixes (#184)
└── metrics/
    ├── track.py          verification, beat rate, Diebold–Mariano
    ├── probabilistic.py  CRPS, Brier, spread-skill, rank histogram
    └── ensemble_calibration.py  per-lead ensemble calibration (#10's measurement core)
```

---

## Beyond `src/`

```
docker/
├── multistage.Dockerfile  one image, two final stages: Cloud Run training, and the API container
├── api/                   anemoi-api-real: Cloudflare Worker + Container (wrangler.jsonc)
│   └── src/
│       ├── index.ts         front door: API-key/console auth, rate limit, KV read-through, cron
│       ├── readCache.ts     KV read cache for storms, storm detail and cycle results (#206)
│       ├── cycleWorkflow.ts anemoi-cycle Workflow: one durable step per storm's cycle (#208)
│       ├── auth.ts          console-issued API key verification against D1
│       └── metering.ts      cycle_runs audit rows
├── cloud-run-training/    Cloud Run job + Workflows definition for real training runs
└── mlflow/                MLflow tracking server (Postgres backend, R2 artifacts)
console/                   SvelteKit console on Cloudflare Workers (anemoi.systems)
├── src/routes/            storms, storms/[stormId], models, sources, registry, monitoring,
│                          retraining, docs, auth, profile; api/[...path] proxies to anemoi-api-real
├── src/lib/               api client, components/anemoi (ConeMap, RIFlagBanner, …),
│                          lastKnown.ts (last-seen data per page, #207), poll.ts, utils.ts
├── scripts/sync-wiki.mjs  renders ../wiki into /docs at build time
├── migrations/            D1 schema (auth, API keys, cycle_runs)
└── e2e/                   Playwright suites
wiki/                      source of the GitHub wiki, published on merge by .github/workflows/wiki.yml
.github/
├── workflows/             ci · deploy (tests + one-approval production deploy) · wiki ·
│                          publish-cloud-run-training · sync-issue-to-project
└── scripts/               deploy-plan.sh (what to test/deploy), publish-wiki.sh
```

Also at the repo root: `configs/` (three YAML files, see [Configuration Reference](Configuration-Reference)), `tests/` (68 files, see [Testing](Testing)), `docs/`, `slurm/` (SLURM-equivalent job scripts for data-ingest and real training jobs -- `#SBATCH`-headered, `sbatch`-submittable on a real cluster; `run_local.sh` emulates `sbatch` via `tmux` on the current single-VM setup, see `slurm/README.md`), `README.md`, `PLAN.md`, `PROJECT.md`.

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
| `DemoState`, `RealState`, `RealStormState` | `api.demo_state`, `api.real_state` | The API's state behind every route: synthetic, or real archive + live storms |
| `CycleHistory` | `api.cycle_store` | A storm's cycles: run in this process, or stored in R2 and loaded on first read |
| `CycleResult`, `CyclePayload`, `CycleProducts` | `api.schemas` | The served (and persisted) cycle shape |
| `CalibrationSample`, `LeadProductCalibration` | `monitoring.calibration_audit` | Served-product containment samples and per-lead verdicts |
| `AnemoiRealApi` | `docker/api/src/index.ts` | Container class: sleep timing persisted across Durable Object restarts (#172) |
| `CycleWorkflow` | `docker/api/src/cycleWorkflow.ts` | The `anemoi-cycle` Workflow the cron starts per cycle label |
| `readThrough()`, `refreshStormSnapshot()` | `docker/api/src/readCache.ts` | KV read-through for storm reads; post-cycle snapshot |

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
| `Hurdat2Error`, `AtcfError`, `TcVitalsError` | `data.hurdat2`, `data.atcf` | A best-track or vitals record doesn't parse |
| `LiveAtcfError` | `data.live_atcf` | NHC's live feed couldn't be fetched or parsed (per storm; the feed as a whole degrades to no live storms) |
| `FetchError` | `data.ingestion` | A raw fetch failed QC or transport |
| `GoesFetchError`, `MicrowaveFetchError`, `DropsondeFetchError`, `NdbcFetchError`, `SstFetchError` | `data.real_*` | A real source fetch failed |
| `InferenceLoadError` | `training.real_inference` | A registered checkpoint can't be rebuilt into a model |
| `InferenceCycleError` | `training.real_inference_cycle` | No Group 1 model could contribute; the cycle falls back to the synthetic deterministic path |
| `InferenceEnsembleError` | `training.real_inference_ensemble` | Anemoi-Spread couldn't run; the cycle falls back to the climatological ensemble |
| `SpreadBacktestError` | `training.spread_backtest` | Backtest inputs missing or inconsistent |

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
