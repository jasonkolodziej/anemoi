# Branding and Naming

The canonical reference for what things are called and why. If you are adding a model, an experiment, a service, or a colour, this page is the authority — not whatever the nearest existing file happens to do.

Source: **Anemoi Branding Brief v3.0**. Enforced in code by `src/anemoi/branding.py` and `tests/test_branding.py`.

---

## The platform

**Anemoi** — the Greek wind gods. Many winds, one forecast: six models, each reading the storm differently, resolving to a single track with an honest spread around it.

- **Primary domain:** `anemoi.systems`
- **Tagline:** *Many winds. One forecast.*
- **Package / CLI:** `anemoi`

## Product modules

| Module | What it is |
|---|---|
| **Anemoi-Core** | Deterministic engine — the five Group 1 models fused into one track and intensity forecast |
| **Anemoi-Spread** | Probabilistic ensemble generator (Skiron diffusion) — cone, intensity PDF, landfall probability, RI flag |
| **Anemoi-Fusion** | Consensus weighting layer, blending Group 1 by rolling validation skill |
| **Anemoi-API** | Developer interface |
| **Anemoi-Stream** | Real-time data ingestion pipeline |

Hyphenated, both parts capitalised. Not "Anemoi Core", not "anemoi-core" outside code identifiers.

---

## The Anemoi

Each architecture is personified as a wind god. **The god name is the identifier**; the architecture name is an implementation detail that stays in the module name.

| God | Direction | Architecture | Module | Colour | Character |
|---|---|---|---|---|---|
| **Boreas** | N | LSTM / GRU | Core | `#06B6D4` | Fast, violent, first to arrive. The sprinter |
| **Notus** | S | Transformer | Core | `#F59E0B` | Heavy, deliberate, sees the whole sky. The strategist |
| **Eurus** | E | GNN | Core | `#EF4444` | Unpredictable, turbulent, inner-core specialist. The maverick |
| **Zephyrus** | W | CNN / ViT | Core | `#10B981` | Gentle, visual, spring-like. The observer |
| **Kaikias** | NE | PINN / Neural ODE | Core | `#8B5CF6` | Rigid, constrained, unyielding. The disciplinarian |
| **Skiron** | NW | Diffusion | Spread | `#EC4899` | Generative, spreading, mist-like. The oracle |

**Anemoi-Fusion** is a model but not a god — it is the consensus of all six, so it takes the neutral Eye colour `#F8FAFC` rather than a direction.

### Where the god name is used

- MLflow experiment names: `boreas/`, `notus/`, `eurus/`, `zephyrus/`, `kaikias/`, `skiron/`, `fusion/`
- Run tags, model-status badges, API path segments
- Track-line colour in the console — each model's line is its god colour
- Anywhere a human reads which model did something

### Where the architecture name is used

- Module names: `models/lstm.py`, `models/gnn.py`
- Builder functions: `build_lstm()`, `build_diffusion()`
- Technical prose explaining *how* a model works

Do not mix the two in one identifier. There is no `boreas_lstm`.

---

## Resolving between them

`anemoi.branding` is the only place the mapping lives. Never hard-code it a second time.

```python
from anemoi.branding import god, experiment_name, color_for, GODS

god("lstm").name            # 'Boreas'
god("boreas").architecture  # 'lstm'
god("BOREAS").direction     # 'N'   — lookup is case-insensitive
experiment_name("gnn")      # 'eurus'
color_for("diffusion")      # '#EC4899'

[g.name for g in GODS]      # north, south, east, west, then diagonals
```

Unknown names raise `KeyError` rather than falling back to a default. A mistyped experiment name is a run that cannot be found again during a post-mortem, which is exactly what the tagging convention in [Experiment Tracking](Experiment-Tracking) exists to prevent.

---

## Colour rules

The six god colours are **data colours**. If a colour appears on a track line, a status badge, or a run tag, it maps to exactly one model — that is the whole point of the system.

Two further colours exist for the eight-point wind rose, which needs southeast and southwest to close:

| Wind | Direction | Hex | Use |
|---|---|---|---|
| **Euronotus** | SE | `#FB923C` | Structural only — logo glyph, radial layout scaffolding |
| **Lips** | SW | `#A3E635` | Structural only — logo glyph, radial layout scaffolding |

**Never assign these to a model**, a track line, or a run tag. `test_structural_colors_are_never_model_colors` asserts the sets stay disjoint.

At icon sizes below ~48 px, drop the four diagonal petals and render the four cardinals only — Lips sits close enough to Zephyrus emerald to flatten when small.

**A third, deliberately separate axis: storm severity.** `console/src/lib/utils.ts`'s `SAFFIR_SIMPSON` is the real, external, standard NHC wind-speed classification (TD/TS/CAT 1–5, the same 34/64/83/96/113/137 kt boundaries NHC itself uses) — not this app's invention, and not a god or status colour. Every hex in it is chosen to avoid colliding with a god or `--color-status-*` hex, so a colour-coded intensity dot on the map or the intensity chart is never mistakable for a specific model's track line or a health status. It answers "how strong is the storm at this point," a real property of a real `wind_kt` value, independent of which model produced the forecast or how healthy the pipeline is.

---

## Console theme

The console (`console/`) is dark-only — no light mode to branch on. Tokens live in `console/src/app.css` as a single OKLCH `@theme` block; this section is the authority for what they should be, the same role this page plays for the god colours above.

**Typography** — self-hosted via `@fontsource-variable`, except the mono face:

| Role | Token | Face |
|---|---|---|
| Body | `--font-sans` | Geist Variable |
| Display / headings | `--font-display` (aliased to shadcn-svelte's `--font-heading`) | Inter Variable |
| Data — coordinates, cycle labels, durations | `--font-mono` / `.font-data` | Geist Mono (Google Fonts `<link>`, not self-hosted — no `@fontsource-variable/geist-mono` package exists) |

**Neutral scale** — "Storm Dark", blue-slate rather than pure black so the (often cool) god colours don't fight the background:

| Token | Hex | OKLCH | Role |
|---|---|---|---|
| `--color-bg` | `#0A0E17` | `oklch(16.43% 0.0202 265.75)` | Page background |
| `--color-surface` | `#111827` | `oklch(21.01% 0.0318 264.66)` | Card / panel fill |
| `--color-surface-raised` | interpolated | interpolated | Elevated chip / hover fill |
| `--color-border` | `#1E293B` | `oklch(27.95% 0.0368 260.03)` | Default hairline |
| `--color-border-strong` | extrapolated | extrapolated | Emphasized hairline, input borders |
| `--color-text` | `#E7ECF3` | `oklch(94.1% 0.011 256.70)` | Body text — kept distinct from Fusion's `#F8FAFC`; see the colour rule above, a data colour never doubles as UI chrome |
| `--color-text-muted` | `#94A3B8` | `oklch(71.07% 0.0351 256.79)` | Secondary text |
| `--color-text-faint` | `#64748B` | `oklch(55.44% 0.0407 257.42)` | Tertiary / meta text |
| `--color-action` | `#60A5FA` | `oklch(71.4% 0.143 254.62)` | The one interactive hue outside the god palette — links, focus rings, primary buttons |

**Status tokens** — `--color-status-online/training/degraded/offline` alias onto existing tokens rather than introducing new hues (`online` → Clear, `training` → Euronotus, `degraded` → Lips, `offline` → not yet decided). These exist specifically so a "how healthy is this model/cycle right now" signal (e.g. the storm page's "N/M models contributing" badge, keyed off the real `contributors`/`missing_model_reasons` cycle data) never has to reach for a god colour to say it — a status is not a data colour and must stay visually distinct from the six-god set per the colour rule above.

| State | Hex | OKLCH | Meaning |
|---|---|---|---|
| Online | `#22D3EE` | `oklch(79.71% 0.1339 211.53)` | Healthy / contributing |
| Training | `#FB923C` | `oklch(75.76% 0.1590 55.93)` | Model active but still training |
| Degraded | `#A3E635` | `oklch(84.93% 0.2073 128.85)` | Reduced capability / degraded quality |
| Offline | `#64748B` | `oklch(55.44% 0.0407 257.42)` | Not yet decided; muted neutral fallback |

**Panel headers** (`CardTitle`/`CardHeader`) — uppercase, `--color-text-muted`, `0.08em` tracking, `13px`, medium weight, with a `--color-border` bottom hairline separating the header from body. Applies to every `Card` in the console (Model Pantheon, Cycle status, Flags & notes, registry/monitoring cards, etc.) — one shared component, so this is enforced structurally rather than by convention.

**Surfaces** — flat fills, not translucent. `Card` and app chrome (sidebar, mobile header, nav drawer) use `--color-surface` directly with a `--color-border` hairline. A glass ("bubble") treatment — a tinted radial gradient over a translucent background plus a soft layered shadow, ported from [getarcaneapp/arcane](https://github.com/getarcaneapp/arcane)'s `frontend/src/routes/layout.css` — shipped briefly and was removed; flat reads cleaner against this app's own dense data surfaces (`Table`, tables inside wiki content, code blocks) than a gradient does.

**Docs nav** (`console/src/routes/docs`) — this wiki, rendered inside the console. Categories (Concepts/Data/Training/etc, parsed at build time from this page's own "Page index" below) nest under "Docs" in the main app sidebar, not a separate middle column. The right-hand "On This Page" rail lists the pages within the current page's category, with the active page's own subsections nested and scroll-spied underneath it — one rail doing both jobs shadcn-svelte's docs reference (`/docs/forms`) splits across two ("Sections" + "On This Page").

**shadcn-svelte** — `pnpm run shad:add`/`shad:apply` pull components from shadcn-svelte's own registry, which expects its own token names (`background`, `card`, `primary`, `chart-1..5`, `sidebar-*`, etc.), not this file's `--color-*` names. Every one of those is aliased onto the Anemoi token it corresponds to (`--color-primary: var(--color-action)`, `--color-chart-1..5` onto the six gods in listing order, etc.) — a future `shad:add <component>` pull renders in Anemoi's actual theme, not a stock shadcn palette. Don't let a CLI `apply`/`add` reintroduce shadcn's own generic light/dark grays alongside this; reconcile onto the tokens above instead, the same way this section itself got written.

---

## Motion and animation

Source: Branding Brief v3.0, Section 9.

### Principles

- Motion conveys physics. Transitions should feel like wind, pressure, and fluid dynamics rather than generic UI movement.
- No decorative motion. Every animation should communicate state, progress, or data change.
- Respect reduced motion. Animations must defer to `prefers-reduced-motion`.

### Standard animation specs

| Element | Animation | Duration | Easing |
|---|---|---|---|
| Storm marker pulse | Radial pulse outward with opacity decay | 2s continuous | Ease-out |
| Track line draw | SVG stroke-dashoffset from start to end | 1.5s | Ease-in-out |
| Ensemble cone spread | Radial gradient expand from center | 2s | Ease-out-cubic |
| Model card status change | Border color transition + subtle glow | 0.3s | Ease |
| Cycle progress bar | Width expansion, stage-by-stage | 0.5s per stage | Linear |
| Data update flash | Brief brightness increase on changed value | 0.2s | Ease-out |
| Panel collapse/expand | Height + opacity (not slide) | 0.3s | Ease-in-out |

### Loading-state motion

- Data fetch: a thin sweep line across the map (radar scan behavior).
- Model inference: the relevant model glyph uses a wind-rose spin state (not a generic spinner).
- Diffusion generation: the ensemble cone "breathes" while members are being generated.

### Console implementation note

The console now exposes named Hurricane icon motion modes through `spinning`:

- `"spin"` for generic continuous rotation
- `"teeter"` for oscillating directional sway
- `"teeter-spin"` for a continuous spin with directional wobble
- `"inference-spin"` for model-inference loading
- `"storm-marker-pulse"` for storm position emphasis
- `true` maps to `"inference-spin"` for backward compatibility

`"inference-spin"` remains as a semantic alias for `"spin"` in loading contexts.

Section 9 motions are now backed by reusable console CSS utilities in `console/src/app.css`:

- Storm marker pulse: `.hurricane-motion-storm-marker-pulse`
- Track line draw: `@keyframes cone-draw`
- Ensemble cone spread: `.motion-ensemble-cone-spread`
- Model card status change and glow: `.motion-model-status-change` + `.motion-model-status-glow`
- Cycle progress stage fill: `.motion-cycle-stage-fill`
- Data update flash: `.motion-data-update-flash`
- Panel expand and collapse: `.motion-panel-expand` + `.motion-panel-collapse`
- Data fetch radar sweep: `.motion-radar-sweep-line`

---

## Adding a seventh model

The rose has two free structural points, but they are structural by rule, not placeholders. If a genuinely new architecture joins:

1. Decide whether it belongs to Core, Spread, or a new module.
2. If it needs a god name, take a classical wind not yet used (Euronotus and Lips are available, but promoting one to a data colour means picking a new structural colour for that petal and updating §5.3 of the brief).
3. Add a `WindGod` record to `GODS` in `branding.py`. The tests covering uniqueness of slugs, architectures and colours will fail if the new entry collides.
4. Add the row to [Model Catalog](Model-Catalog) and the [Glossary](Glossary).

---

## History

Named **AEOLUS / MERIDIAN** through Scope v2.1. Renamed to Anemoi during implementation — see [Decision Log](Decision-Log) for what the old names got wrong and what the rename is enforced by.

---

Related: [Model Catalog](Model-Catalog) · [Glossary](Glossary) · [Experiment Tracking](Experiment-Tracking) · [Decision Log](Decision-Log)
