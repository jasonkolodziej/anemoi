# Anemoi-API

Branding Brief §2.3. Why a fifth product module exists and what it deliberately
does not do. The full endpoint-by-endpoint reference lives on the wiki
([API](https://github.com/jasonkolodziej/anemoi/wiki/API)) — this is the policy
this package is bound to, not the contract itself.

## The gap

Anemoi-API is named in the branding table alongside Core, Spread and Fusion,
but until `anemoi.api` the only interface was the CLI — `anemoi schedule`,
`sources`, `cycle`, `splits` — stdout only, one process per call. That is fine
for a developer at a terminal and unusable for a console or a downstream
advisory pipeline polling for the next cycle.

## What it is, and is not

`anemoi.api` disseminates what `anemoi.inference` already computes; it does
not decide anything the operational logic doesn't already decide. Every route
is parse request, call an `anemoi.*` function, convert the dataclass result to
JSON — no business logic lives in a router. It adds no data source and no
forecast skill: storms are synthetic (`anemoi.data.synthetic`, the same
generator the test suite uses) until real ingestion is wired, exactly as the
CLI's demo `cycle` command already is.

## The payload is a contract, not a convenience

`CycleOutput.payload()` — the shape already documented on the wiki's
[Inference Cycle](https://github.com/jasonkolodziej/anemoi/wiki/Inference-Cycle)
page — is disseminated byte-for-byte. A consumer parsing today's CLI stdout and
a consumer calling `GET /v1/storms/{id}/cycles/{cycle}` get the identical
`payload` field. `ForecastProducts` computes more than `payload()` sends
(intensity PDF, landfall probability, the per-lead deterministic track); v1
exposes those as a sibling `products` field rather than folding them in, so
`payload` stays stable under a diff regardless of what else the API grows.

## Authentication and versioning

A single static header, `X-Anemoi-Api-Key`, checked only when
`ANEMOI_API_KEY` is set — disabled by default for local development. `/v1` is
a path prefix, not a header negotiation, matching how the rest of the system
already treats a version as part of an identifier (MLflow experiment names,
run tags) rather than metadata. A breaking response-shape change ships as
`/v2`; additive fields do not.

## The flag vocabulary

`flags` and `products.notes` are free text but drawn from a fixed set,
produced directly by `inference/cycle.py` and `inference/postprocess.py` —
the same flags the CLI's JSON output already carries:

| Pattern | Meaning |
|---|---|
| `vitals=estimated` | Cycle ran on an extrapolated fix: the storm had no fix at the cycle time yet (or `worst_case` withheld it) |
| `nwp_stale={n}h` | Selected NWP cycle is staler than the nominal t-6 |
| `missing:{source_key}` | A source the plan expected was unexpectedly absent |
| `spread_fallback:{ExceptionType}` | Anemoi-Spread failed; climatological ensemble substituted |
| `load_shed:members={n}` | Reduced ensemble to hold the deadline |
| `deterministic_fallback:synthetic` | No trained model could run; the track is a straight-line placeholder (#214) |
| `input:final_best_track` | An archive storm: its inputs are the final best track (training labels), not as-issued vitals (#214) |
| `vitals_source:persisted` | Too little history to extrapolate; the last earlier fix was held in place (#214) |
| `basin_untrained:{basin}` | The storm's basin isn't one the models were trained on (#214) |
| `nwp_unavailable` | No GFS cycle within 12 h had fields for this time; gridded models sat out (#215) |
| `input_skew:{models}` | These gridded models were fed a GFS forecast hour other than the one they trained on (#215) |
| *(in `notes`)* ensemble below minimum members | Cone drawn from climatological radii |
| *(in `notes`)* ensemble underdispersion guard | Cone drawn from climatological radii instead |

An unrecognised flag should render as "degraded, reason opaque" rather than
being dropped — new flags can ship in `anemoi.inference` without a client
release as long as consumers treat the prefix match as best-effort.

## Role is permission, `used_by` is use

`GET /v1/sources` returns the data source registry. `role` says what a source
may be used for: eight of the ten sources are `operational`, which means a
cycle is allowed to read them, not that a model does. `used_by` says who uses
each source today, from a fixed vocabulary in a fixed order:

| Value | Meaning |
|---|---|
| `lstm`, `cnn`, `transformer`, `gnn`, `pinn` | That Group 1 model reads the source as an input, in training, in a forecast cycle or both. Listed in registry order (`tracking.registry.GROUP1_MODELS`), which is not the order `GET /v1/models` lists them in |
| `labels` | The source supplies the supervision targets |
| `verification` | The source is kept for verifying forecasts and is not a model input |

`role` tells training from serving. `era5` lists the four gridded models
because they pretrain on it in Stage A, and the ERA5T skew audit replays them
on it after a cycle; no cycle reads a `pretrain_only` source.

An empty list means no model, label or verification code reads the source
yet. The cycle planner can still track it: `goes`, `sst_ohc` and
`ensemble_perturbations` are in its optional tier (`data.availability`),
with `ndbc`, so a cycle that finds one late is flagged `missing:{source}`
and marked degraded, though no model would have read it. The tier says what
a cycle waits for, not what reads the source.

`used_by` names these uses, not every reader:

- Fusion reads `besttrack_working` too, as its context vector. The
  vocabulary is the five Group 1 models.
- Every model's forecast is placed from the storm's current working fix,
  and in a cycle the gridded crop is centred on it. In training the crop is
  centred on the HURDAT2 final fix, because the field caches are fetched at
  HURDAT2 positions and keyed by storm and time only.
- The served-product calibration monitor scores cones against the storm's
  later `besttrack_working` fixes.
- A cycle on an archive storm, whose vitals were never kept, takes
  `besttrack_final` as its track and is flagged `input:final_best_track`.
  So `verification` means not a model input in an as-issued cycle.

`verification` on `besttrack_final` has readers: validation metrics, the
promotion gates and the spread backtest score forecasts against it. On
`dropsonde` and `ndbc` it is only a designation
(`docs/input_sources_plan.md`, "Not model inputs"): they won't become model
inputs, and no verification code reads them yet. `anemoi sources` says so
under its table.

The mapping is next to the registry in `data/sources.py` (`MODEL_INPUTS`,
`LABEL_SOURCES`, `VERIFICATION_SOURCES`, `VERIFICATION_NOT_READ_YET`). Two
older lists name sources without saying a model reads them: the planner's
tiers, and `curriculum.yaml`'s per-stage `input_sources`, which is checked
for role only (Stage B lists `goes` and `sst_ohc`). `tests/test_sources.py`
holds the mapping to the code: it fails when a module names the adapter of a
source `used_by` calls unread, and when a model's entry disagrees with its
training runner's or live builder's signature. It reads names, not data
flow, so the `verification` entries still rest on review. The console's
Sources page and system graph are being moved onto this field from their
own copy.

## The one mutating route

`POST /v1/storms/{id}/cycles` is the only endpoint in v1 that writes anything,
and even it doesn't decide when to run — it mints a fresh `WORKING` (or
`ESTIMATED`) fix at the storm's latest known position and calls `run_cycle`
directly, subject to the same guardrails `anemoi cycle` already enforces
(`besttrack.assert_input_safe` first among them: the archive's `FINAL` fix is
never what gets fed in). Retraining triggers are read-only for the same
reason model registration is not exposed here — launching a training run is
an orchestration decision (cluster, budget, sign-off on a mid-season Group 1
swap), not a synchronous HTTP call.

## What production replaces

| Reference component | Production replacement |
|---|---|
| `demo_state.DemoState` (in-process, synthetic) | Real ingestion behind `GriddedFields`/`Track`/`AvailabilityOracle` — the interfaces the top-level README already names as the first thing to replace |
| `POST .../cycles` running inline | A queue: POST enqueues, a worker calls `run_cycle`, completion is published |
| Static header auth | OAuth2 / mTLS between internal consumers |
| In-process WebSocket poll | Subscription to a `CycleOutput` publish event |
| File-backed `ModelRegistry` | MLflow-backed — `ModelRegistry(root, mlflow_client=...)` already supports this; no route changes needed |

`demo_state.py` is the one file to replace first. Every router depends on it
only through its public methods, not on synthetic details directly.
