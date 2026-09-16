# Anemoi

> **Many winds. One forecast.**

Reference implementation of the **Anemoi** hurricane forecast platform, built to
**Project Scope v2.1**.

Six model architectures each read the storm differently. **Anemoi-Core** fuses
five of them into a single deterministic track and intensity forecast;
**Anemoi-Spread** conditions a diffusion model on Core's latents to generate a
structurally diverse ensemble, from which the cone, intensity PDF, landfall
probability and rapid-intensification flag are derived.

Each architecture carries the name of a Greek wind god. The name — not the
architecture — is what appears in MLflow experiments, run tags, status badges
and API paths; `anemoi.branding` is the single place the two are mapped.

| God | Direction | Architecture | Module | Role |
|-----|-----------|--------------|--------|------|
| **Boreas** | N | LSTM / GRU | Anemoi-Core | Fast baseline; warm-starts every cycle |
| **Notus** | S | Transformer | Anemoi-Core | Global steering from gridded fields |
| **Eurus** | E | GNN | Anemoi-Core | Inner-core mesh; rapid intensification |
| **Zephyrus** | W | CNN / ViT | Anemoi-Core | Satellite feature extraction |
| **Kaikias** | NE | PINN / Neural ODE | Anemoi-Core | Physics constraints |
| **Skiron** | NW | Diffusion | Anemoi-Spread | Ensemble generation |

**Anemoi-Fusion** is the consensus weighting layer that blends the five Core
models by rolling validation skill.

---

## Getting started

```bash
uv sync                      # core: numpy + pyyaml
uv sync --extra torch        # add the model implementations
uv sync --extra all          # everything, including pytest and ruff

uv run pytest                # torch-marked tests skip automatically without torch
uv run anemoi schedule 2026-08-06
```

Four things worth running first:

```bash
uv run anemoi schedule 2026-08-06     # the real cycle timeline for a day
uv run anemoi schedule 2026-08-06 --worst-case
uv run anemoi sources                 # which feeds may be read in production
uv run anemoi cycle 20260806_06Z      # one demo cycle, JSON payload out
uv run anemoi splits                  # storm-wise split summary
```

`anemoi schedule` is the fastest way to see what v2.1 changed. It prints cycle
start gated on the working fix, the six stage budgets, and the worst-case
margin against the advisory deadline.

---

## What this implementation is, and is not

**It is** a complete, tested implementation of the *operational logic*: cycle
timing and input availability, the pretrain/fine-tune curriculum, promotion
gates, model-set pinning, retraining triggers, degraded modes, skew and drift
monitoring, and verification metrics. That logic is where v2.1's corrections
live, and it is fully covered by the test suite.

**It is not** connected to real data. HURDAT2, ERA5, GDAS/GFS and GOES are not
available offline, so `anemoi.data.synthetic` generates archives with the same
shape and statistics — including a deliberate ERA5-vs-GDAS offset, without which
the skew machinery would have nothing to detect. The ingestion layer is the
first thing to replace; the interfaces it must satisfy are `GriddedFields`,
`Track` and `AvailabilityOracle`.

The models are real PyTorch modules with correct shapes and latent contracts,
but they are untrained. Nothing here has forecast skill.

---

## Package layout

```
src/anemoi/
├── time_utils.py         synoptic arithmetic; the t-6 NWP selection rule
├── geo.py                great-circle distance, bearings, cross/along-track
├── cli.py                schedule / sources / cycle / splits
├── data/
│   ├── sources.py        source registry with latency + role; operational guard
│   ├── besttrack.py      working vs final tracks; Stage B noise emulator
│   ├── availability.py   what has actually published at cycle time t
│   ├── features.py       one code path per flavor; flavor guards
│   ├── splits.py         storm-wise + chronological splits, leakage checks
│   └── synthetic.py      stand-in data generator
├── models/               lstm, cnn, transformer, gnn, pinn, diffusion, fusion
├── training/
│   ├── curriculum.py     Stage A/B; assert_deployable
│   ├── promotion.py      validation-only gates; test-set budget
│   ├── orchestrator.py   sequential/parallel wave scheduling
│   └── triggers.py       retrain triggers + derived-model cascade
├── tracking/
│   ├── tags.py           run tags incl. input_flavor, nwp_cycle_lag
│   └── registry.py       MLflow-optional registry; model-set pinning
├── inference/
│   ├── scheduler.py      cycle timeline, vitals gating, load shedding
│   ├── cycle.py          execution with degraded modes
│   └── postprocess.py    cone, intensity PDF, landfall, RI
├── monitoring/
│   ├── skew.py           ERA5T paired-input audit
│   └── drift.py          feature and validation-loss drift
├── metrics/
│   ├── track.py          track/intensity verification, beat rate, DM test
│   └── probabilistic.py  CRPS, Brier, spread-skill, rank histogram
└── api/                  Anemoi-API: FastAPI developer interface (uv sync --extra api)
    ├── main.py           app factory, CORS, exception handlers
    ├── schemas.py         Pydantic models; CyclePayload mirrors payload() exactly
    ├── demo_state.py      synthetic storms + seeded registry/drift/skew (swap first)
    ├── stream.py          WS /v1/storms/{id}/stream
    └── routers/           meta, schedule, storms, registry, monitoring, retraining
```

---

## Anemoi-API

[#anemoi-api](#anemoi-api)

A FastAPI service over the operational logic above — the developer interface
named in the branding brief's product module table (§2.3) but not built until
now. It disseminates what `anemoi.inference` already computes over HTTP
instead of stdout; it adds no data source and no forecast skill.

```
uv sync --extra api
uv run python -m anemoi.api --reload     # http://127.0.0.1:8000/docs
```

`GET /v1/storms`, `POST /v1/storms/{id}/cycles`, `GET /v1/schedule`,
`GET /v1/models` (the six wind gods, for a console's design tokens),
`GET /v1/monitoring/drift`, `GET /v1/retraining/triggers` — endpoint
reference on the wiki's [API](https://github.com/jasonkolodziej/anemoi/wiki/API)
page, design policy in [`docs/api.md`](docs/api.md). Storms are synthetic
(`anemoi.data.synthetic`, same generator the test suite uses) until real
ingestion is wired; see `docs/api.md`'s "What production replaces" for
exactly what to swap.

```
uv run pytest -m api      # smoke tests; skip automatically without the api extra
```

---

## The v2.1 invariants, and where they are enforced

Six rules are enforced at runtime rather than left to convention. Each has tests
named after the failure it prevents.

| Invariant | Enforced by |
|---|---|
| Reanalysis and final best-track are never read during a cycle | `sources.assert_not_operational` |
| Final best-track is never a model input | `besttrack.assert_input_safe` |
| Every model ends on the operational flavor before promotion | `curriculum.assert_deployable` |
| Promotion is decided on validation, never on test | `promotion.evaluate_promotion` |
| Cycle t uses the t-6 NWP cycle, never t | `time_utils.select_nwp_cycle` |
| A Group 1 retrain invalidates diffusion and fusion | `registry.pin_set`, `triggers.expand_jobs` |

---

## Two findings from building it

Both are places where the arithmetic did not agree with the scope text.

**The t+1:30 vitals timeout is about ten minutes too generous.** With the
reduced-ensemble profile's 70-minute worst case and a 30-minute advisory margin,
a cycle starting at t+1:30 finishes at t+2:40 — a 20-minute margin, not 30. The
timeout is therefore derived (`derive_vitals_timeout`) rather than written down,
which yields t+1:20 and keeps the three numbers consistent when any of them is
retuned. See `test_scheduler.py::test_vitals_timeout_is_derived_not_asserted`.

**A cone drawn from ensemble spread needs a real-time guard.** Calibration
cannot be measured at forecast time — there is no observation yet — so
`spread_skill` is a post-hoc verification tool only. `build_cone` instead
compares the ensemble radius at the longest lead against the climatological
radius, and falls back to climatological radii when the ensemble is
dramatically tighter. That is the underdispersion signature of a diffusion model
over-anchored to its deterministic conditioning, and it is exactly when
under-drawing the cone would matter most.

---

## Testing

```bash
uv run pytest                      # full suite
uv run pytest -m "not torch"       # skip model tests explicitly
uv run pytest tests/test_scheduler.py -v
```

241 tests cover the operational logic and run without torch; a further 15 cover
the model architectures and require the `torch` extra.

Tests are named after the behaviour they protect, not the function they call —
`test_same_cycle_nwp_is_never_selected_even_when_offered` rather than
`test_select_nwp_cycle_2`. When one fails, the name should tell you what broke.

See `PLAN.md` for the build order and what to replace first.
