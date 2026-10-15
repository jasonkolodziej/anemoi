# API

Scope v2.1, Branding Brief §2.3. `Anemoi-API` — the developer interface,
implemented in `anemoi.api`. See [docs/api.md](https://github.com/jasonkolodziej/anemoi/blob/main/docs/api.md)
for the design policy this page's contract is bound to.

---

## What it is, and is not

A FastAPI service over the operational logic documented elsewhere on this
wiki — [Inference Cycle](Inference-Cycle),
[Model Registry](Model-Registry),
[Monitoring](Monitoring),
[Retraining Triggers](Retraining-Triggers).
It disseminates what `anemoi.inference` already computes over HTTP instead of
stdout; it adds no data source and no forecast skill. Storms are synthetic
(`anemoi.data.synthetic`) until real ingestion is wired — see
[Roadmap](Roadmap).

---

## Running it

```
uv sync --extra api
uv run python -m anemoi.api --reload     # http://127.0.0.1:8000/docs
```

CORS defaults to `http://localhost:5173` (a SvelteKit dev server); override
with `ANEMOI_API_CORS_ORIGINS`. Auth is a single header,
`X-Anemoi-Api-Key`, checked only when `ANEMOI_API_KEY` is set.

`/docs` is FastAPI's stock Swagger UI, unstyled, unchanged. `/redoc` is a
real Anemoi-branded ReDoc (#159) — see below.

---

## `/redoc`: a real Anemoi theme, not a CSS file that would have done nothing

`fastapi.openapi.docs.get_redoc_html` has no styling hook at all (its own
docstring: "you would only call this function yourself if you needed to
override some parts") — it renders the open-source `redoc` npm package
(pinned to the same `@2` major FastAPI's own default CDN URL already uses)
via a bare `<redoc spec-url="...">` element with no theme.

**A real correction, not assumed:** #159's own two reference links looked
like they pointed at the same mechanism, but only one does. Redocly's
[customize-styles](https://redocly.com/docs/realm/branding/customize-styles)
guide — a plain `@theme/styles.css` of CSS custom properties like
`--color-primary` — is for **Redocly Realm**, a separate paid product,
confirmed by fetching that page directly. It has no effect on the
open-source bundle FastAPI actually embeds here; a `:root { --color-primary:
... }` file declared per that guide would load and silently do nothing. The
real mechanism (confirmed against `Redocly/redoc`'s own `src/theme.ts`) is a
nested JS object passed to `Redoc.init(specUrl, {theme}, element)` — that's
what `anemoi.api.docs.REDOC_THEME` is, and `main.py` replaces the default
`/redoc` route (`redoc_url=None` on the `FastAPI(...)` constructor) with one
that calls `Redoc.init` directly instead of using the declarative element,
since a nested theme object can't be serialized into an HTML attribute.

A real, small `static/redoc-theme.css` is still declared and served (the
issue's own literal deliverable) — it covers what the JS theme object does
not: the `<body>` background before `redoc.standalone.js` finishes loading
and mounts (otherwise a white flash against this app's dark-only palette),
and the scrollbar.

Every colour traces to `anemoi.branding` — Branding.md's "never hard-code it
a second time" rule applies here exactly as it does to the console.
`test_theme_never_uses_a_god_color` (`tests/test_api_docs.py`) asserts no
`WindGod.color` leaks into the theme; HTTP method badges instead draw from
`STATUS_COLORS`/`FUNCTIONAL_COLORS` — GET → Clear (`#22D3EE`), POST →
`--color-action` (`#60A5FA`), PUT → Euronotus, PATCH → Lips, DELETE →
Landfall — the same non-god, semantic tier the console's own Model Pantheon
status badges use. Verified live (2026-09-23) with a real Playwright
screenshot of `/redoc`, not just the embedded JSON: dark chrome throughout,
cyan GET / blue POST badges, blue active-sidebar highlight, no unstyled
flash.

The neutral scale (background/surface/border/text) has no `branding.py`
equivalent yet — it lives only in the console's `app.css`/`branding.ts`
today — so those few hex values are named constants in `api/docs.py`
itself, each commented with the exact console token they mirror.

---

## Endpoints

All paths are prefixed `/v1`.

### Meta

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Status, API version, anemoi version, whether torch is installed |
| GET | `/models` | The six wind gods + Fusion — a console's design-token source |
| GET | `/sources` | The §4.1 data source registry, same rows as `anemoi sources` |

### Schedule

| Method | Path | What it does |
|---|---|---|
| GET | `/schedule?date=YYYY-MM-DD&worst_case=false` | The day's four cycles with full stage timelines — HTTP form of `anemoi schedule` |

### Storms

| Method | Path | What it does |
|---|---|---|
| GET | `/storms` | Every storm the demo state knows about |
| GET | `/storms/{id}` | Storm detail: latest fix, full history, cycles already run |
| POST | `/storms/{id}/cycles` | Runs one forecast cycle — the only mutating route in v1; see **Who may run a cycle** below |
| GET | `/storms/{id}/cycles/{cycle}` | Retrieves a previously run cycle; `404` if it hasn't been run |

**Who may run a cycle** (real deployment; [Decision Log #49](Decision-Log#49-anyone-signed-in-could-overwrite-the-official-forecast-212--security-bugfix)). A cycle label is one shared forecast, so `RealState` enforces `api.cycle_policy`:

- The **scheduled** run (the `anemoi-cycle` Workflow) is the official cycle. A manual run only fills a label nothing has run; the next scheduled run of that label replaces it.
- A manual run of a label that already exists → `409` `exists`, unless an operator (`ANEMOI_OPERATOR_USER_IDS`) sends `"replace": true`.
- A manual run of an active storm's label before its scheduled run time (t+1:30) → `409` `not_scheduled_yet`, naming the time.
- A second run of a label while one is executing → `409` `in_progress`.
- A label before the storm's first fix, or more than 12 h after its latest → `400`.
- The API image requires a signed-in caller (`X-Anemoi-User-Id`, set by the Worker) on manual runs (`ANEMOI_REQUIRE_CALLER`); the demo state runs anything.

A `409` body is `{"detail": "<message>", "code": "<code>"}`. Every result carries `run`: `{"source": "scheduled" | "manual", "overrides": [...]}`, naming the request fields that moved its inputs off the operational defaults (`lat`, `lon`, `wind_kt`, `members`, `worst_case`, `coastline`). `run` is `null` on results stored before #212.

**Served from a cache in production.** On the deployed `anemoi-api-real` Worker, these three `GET`s are answered from a KV read cache without waking the container ([Decision Log #44](Decision-Log#44-every-console-view-woke-the-api-container----storm-reads-now-served-from-kv-206--bugfix-performance)). Every successful cycle run (scheduled or `POST`) writes to it. The storm list and a storm's detail can be up to 30 minutes old before a background refresh; a stored cycle result never changes. Each response says how it was served:

| `X-Anemoi-Cache` | Meaning |
|---|---|
| `hit` | From KV, fresh |
| `stale` | From KV, older than 30 min; refreshed in the background |
| `miss` | Not cached yet; answered by the container, then cached |
| `bypass` | A signed-in request sent `Cache-Control: no-cache` |

`GET /v1/health`, `/v1/schedule?date=…&worst_case=…` and `/v1/monitoring/skew?lead_hours=…` are cached the same way (30-minute refresh): the console polls them every minute, and uncached they kept the container awake (#212). A query with any other parameter is passed through.

A signed-in caller can send `Cache-Control: no-cache` when a read must reflect a write they just made: KV reads can lag a write by up to a minute. An anonymous `no-cache` is served from the cache like any other read; otherwise anyone could wake the container at will. A `404` is never cached. `/v1/internal/*` (operator routes the cron calls, e.g. `POST /v1/internal/calibration-audit`) is not part of the public API and returns `404` from outside.

### Registry

| Method | Path | What it does |
|---|---|---|
| GET | `/registry` | One entry per tracked model, with version history |
| GET | `/registry/{model}` | Scoped to one model |
| GET | `/registry/pins/active` | The currently pinned model set (§5.7) — `null` if nothing's pinned |

### Monitoring

| Method | Path | What it does |
|---|---|---|
| GET | `/monitoring/drift` | Feature drift for all seven tracked models in one call |
| GET | `/monitoring/drift/{model}` | Scoped to one model |
| GET | `/monitoring/skew?lead_hours=48` | The ERA5T-vs-operational paired audit (§4.6.3) |
| GET | `/monitoring/calibration` | Served cone/intensity-band containment per (lead, product) — was what we actually served right, once truth arrived ([Monitoring](Monitoring#calibration-audit)) |

### Retraining

| Method | Path | What it does |
|---|---|---|
| GET | `/retraining/triggers` | What `evaluate_all()` would schedule right now, cascade included. Read-only — see [docs/api.md](https://github.com/jasonkolodziej/anemoi/blob/main/docs/api.md) for why |

### Stream

| Method | Path | What it does |
|---|---|---|
| WS | `/storms/{id}/stream` | Pushes each cycle result as it's run, in-process polling reference implementation |

---

## The dissemination payload

Every cycle response's `payload` field is exactly `CycleOutput.payload()` —
the same shape documented on [Inference Cycle](Inference-Cycle#dissemination-payload):

```json
{
  "cycle": "20260806_06Z",
  "issued_at": "2026-08-06T07:40:00+00:00",
  "advisory_deadline": "2026-08-06T09:00:00+00:00",
  "nwp_cycle_lag_hours": 6,
  "vitals": "observed",
  "ensemble_size": 20,
  "rapid_intensification": false,
  "ri_probability": 0.0,
  "cone": [{"lead_hours": 12, "lat": 23.347, "lon": -73.127, "radius_nm": 13.4, "basis": "ensemble"}],
  "flags": []
}
```

### Running a cycle

`POST /storms/{id}/cycles` takes a `RunCycleRequest`. Two fields are worth stating explicitly:

- **`members`** is bounded by the real full ensemble the scheduler runs, `DEFAULT_ENSEMBLE_MEMBERS` (50, raised from 20 in #188) — **not** an arbitrary API limit. `run_cycle` only ever applies a request as a *cap* (`min(plan.requested_ensemble_members, requested_members)`), so it can lower the count and never raise it. The field used to advertise `le=100` and then silently substitute 20, which the console showed as `members: 30` in the form beside `ensemble: 20 members` in the cycle status (#187). A larger value is now refused with `422` rather than quietly changed. Under load shedding the served count can still be *lower* than what was asked for; that case is real degradation and is flagged on the cycle itself (`load_shed:members=N`).
- **`coastline_lat`/`coastline_lon`** are optional and jointly required — `landfall_probability` stays `null` unless both are given, since `postprocess.landfall_probability` needs a reference point to measure closest approach against.

Re-running the same cycle label returns the same forecast: the served diffusion sampler is seeded from the cycle's own identity (#188, see [Inference Cycle](Inference-Cycle#reproducibility-the-served-sampler-is-seeded-188)).

### Extended products

`ForecastProducts` computes more than `payload()` sends. v1 exposes the rest
as a sibling `products` field on the same response:

```json
{
  "deterministic_track": [{"lead_hours": 12, "lat": 23.35, "lon": -73.13, "wind_kt": 88.6}],
  "contributors": {"lstm": 0.2, "transformer": 0.35, "gnn": 0.25, "cnn": 0.2},
  "per_model_tracks": {
    "lstm": [{"lead_hours": 12, "lat": 23.41, "lon": -73.20, "wind_kt": 86.9}]
  },
  "missing_model_reasons": {
    "pinn": "no real live feature, checkpoint, or env standardisation stats"
  },
  "intensity_pdf": [{"lead_hours": 12, "p10": 74.2, "p25": 81.0, "p50": 88.6, "p75": 95.1, "p90": 102.3}],
  "landfall_probability": null,
  "notes": [],
  "degraded": false
}
```

`per_model_tracks` is each contributing model's own track before fusion, keyed the same as `contributors` — real, not derived after the fact (see [Inference Cycle](Inference-Cycle#a-real-deterministic_fn-and-ensemble_fn-not-just-the-synthetic-demo-ones-78-85)). Empty (`{}`) for the synthetic fallback and demo cycles.

`missing_model_reasons` is the mirror image — why each Group 1 model that *isn't* in `contributors`/`per_model_tracks` was skipped, keyed the same way. Real, not derived after the fact: also previously computed and then discarded unless every model failed. Empty (`{}`) for the synthetic fallback and demo cycles, same as `per_model_tracks`.

### Flag vocabulary

See [docs/api.md](https://github.com/jasonkolodziej/anemoi/blob/main/docs/api.md#the-flag-vocabulary)
for the full table — `vitals=estimated`, `nwp_stale={n}h`, `missing:{source}`,
`spread_fallback:{type}`, `load_shed:members={n}`, and since #214
`deterministic_fallback:synthetic`, `input:final_best_track`,
`vitals_source:persisted` and `basin_untrained:{basin}`, and since #215
`nwp_unavailable` and `input_skew:{models}`, plus two
ensemble-quality notes. Treat an unrecognised flag as "degraded, reason
opaque," not as an error.

### Provenance

Since #214 every real cycle result carries `provenance` — what the cycle actually ran on, stored with it in R2:

```json
{
  "fix_source": "extrapolated",
  "fix": {"valid_time": "2026-10-15T06:00:00Z", "lat": 21.8, "lon": -63.0, "max_wind_kt": 65.0, "min_pressure_mb": 985.0, "quality": "estimated"},
  "model_versions": {"lstm": 7, "cnn": 6, "transformer": 5, "gnn": 5},
  "fusion": "inverse_error",
  "gridded_source": "https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.20261015/00/atmos/gfs.t00z.pgrb2.0p25.f006",
  "nwp_cycle": "2026-10-15T00:00:00Z", "nwp_forecast_hour": 6,
  "input_skew": {"cnn": "trained on f000, fed f006"},
  "basin": "AL", "trained_basin": true,
  "started_at": "2026-10-15T07:30:04Z",
  "git_sha": "3dbfc98…", "config_sha256": "9f2c…"
}
```

- **`fix_source`**: the storm's own fix at the cycle time (`tcvitals`), an archive storm's `final_best_track`, `extrapolated` from the last motion vector, or `persisted`. Before #214 every cycle used the storm's *latest* fix relabelled as the cycle time — for a past label, a position from later — and said `vitals: observed` regardless.
- **`fusion`**: `learned` (all five models and the learned fusion), `inverse_error` (fewer than five), `synthetic` (no model ran), `demo`.
- **`issued_at`/`on_time`** in the payload are now when the cycle really finished, not the plan's target.

`provenance` is `null` on cycles stored before #214 and on demo cycles.

---

## Errors

| Condition | Status |
|---|---|
| Unknown storm, cycle, or model | `404` |
| Bad input (`CycleError`, malformed date) | `400` / `422` |
| Missing/bad API key (when enabled) | `401` |

Errors are the same exception messages `anemoi`'s own guardrails raise —
`CycleError`, `RegistryError`, `KeyError` from `branding.god()` — not
re-worded for the API.

---

Related: [Inference Cycle](Inference-Cycle) · [Model Registry](Model-Registry) · [Monitoring](Monitoring) · [Retraining Triggers](Retraining-Triggers) · [Getting Started](Getting-Started)

---

**Anemoi** · [anemoi.systems](https://anemoi.systems) · Scope v2.1 · Reference implementation `anemoi` v2.1.0
