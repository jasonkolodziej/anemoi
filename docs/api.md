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
| `vitals=estimated` | Cycle ran on an extrapolated fix past the derived vitals timeout |
| `nwp_stale={n}h` | Selected NWP cycle is staler than the nominal t-6 |
| `missing:{source_key}` | A source the plan expected was unexpectedly absent |
| `spread_fallback:{ExceptionType}` | Anemoi-Spread failed; climatological ensemble substituted |
| *(in `notes`)* ensemble below minimum members | Cone drawn from climatological radii |
| *(in `notes`)* ensemble underdispersion guard | Cone drawn from climatological radii instead |

An unrecognised flag should render as "degraded, reason opaque" rather than
being dropped — new flags can ship in `anemoi.inference` without a client
release as long as consumers treat the prefix match as best-effort.

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
