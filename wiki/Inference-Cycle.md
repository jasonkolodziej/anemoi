# Inference Cycle

Scope v2.1 §6. Implemented in `inference/scheduler.py` and `inference/cycle.py`.

---

## The v2 problem

v2's schedule had Anemoi-Core products ready at **t+0:45**, consuming the GFS cycle named `t`. GFS 0.25° publishes roughly 3.5–4 hours after its cycle time. At t+0:45 that data does not exist.

The schedule was not tight. It was impossible.

---

## The v2.1 cycle

```
t+0:00   prefetch begins against already-staged t−6 NWP fields
t+0:45   TC-Vitals nominally arrives → cycle formally starts
t+1:20   vitals timeout: run on an extrapolated fix, flag vitals=estimated
t+1:40   products ready (nominal path)
t+2:27   products ready (worst case, standard profile)
t+3:00   NHC public advisory  ← the operative deadline
```

Two changes carry it.

### Cycle `t` consumes the `t−6` NWP cycle

The `t−6` cycle's 6-hour forecast is valid at `t` and published well before `t`.

```python
from anemoi.time_utils import select_nwp_cycle
sel = select_nwp_cycle(t, available_cycles={t, t - timedelta(hours=6)})
sel.nwp_cycle    # t − 6h, even though t was offered
sel.lag_hours    # 6
```

`select_nwp_cycle` **will not select the cycle named `t`** even if it appears in the available set. At `t` it does not exist, and selecting it silently is precisely the v2 error. Selection walks back in 6-hour steps from `t−6` to `t − max_lag_hours`.

> This matches operational reality at forecast centres: "current-cycle" NWP guidance in an NHC advisory package is itself from the previous synoptic run. Anemoi-Core makes the same trade explicitly rather than accidentally.

### The cycle is gated on the working fix, not the clock

The storm's current position is what the whole forecast is anchored to. Starting without it produces a forecast of a storm that is not where you think it is.

---

## What is actually available at `t`

§6.2.1, encoded in `data/availability.py`.

| Input | Available by | Used at cycle `t` |
|---|---|---|
| GOES imagery | t + ~5 min | Current, up to `t` |
| Buoy / C-MAN | t + ~15 min | Current, up to `t` |
| TC-Vitals / working fix | t + ~45–90 min | **Gating input — cycle starts when this lands** |
| GDAS/GFS 0.25° for cycle `t` | t + ~3.5–4 h | **Not used at `t`.** Cycle `t` uses the `t−6` analysis + its 6 h forecast valid at `t` |
| GEFS/EPS perturbations | t + ~4–6 h | `t−6` members valid at `t` |
| SST / OHC | ~1 day | Persisted from the previous day |

Availability is a **queryable model**, not an assumption. `AvailabilityOracle` is a protocol; `LatencyOracle` implements it from the registry's latency table with per-source overrides and outage injection:

```python
oracle = LatencyOracle()
oracle.set_arrival("besttrack_working", t, t + timedelta(hours=3))  # late fix
oracle.set_missing("gdas_gfs", t - timedelta(hours=6))              # outage
```

Every timing test is written against a configured oracle rather than a mocked clock, so an outage scenario is three lines — and a replay harness for a real season is a second implementation of the same protocol.

---

## Stage budgets

§6.2.2. Measured from **cycle start**, not from `t`.

### Standard profile

| Stage | Target | Max |
|---|---|---|
| Data assembly & QC gate | 10 min | 20 min |
| Preprocessing (regrid, storm-relative, features) | 15 min | 25 min |
| Deterministic inference (LSTM ∥ Transformer ∥ GNN ∥ CNN, then PINN) | 10 min | 18 min |
| Fusion → **Anemoi-Core out** | 2 min | 4 min |
| Anemoi-Spread diffusion (50 members) | 13 min | 25 min |
| Post-processing (cone, PDFs, RI flag) → **Anemoi-Spread out** | 5 min | 10 min |
| **Total** | **55 min** | **102 min** |

### Reduced profile — load shedding

| Stage | Target | Max |
|---|---|---|
| Data assembly | 8 min | 14 min |
| Preprocessing | 12 min | 18 min |
| Deterministic inference | 10 min | 16 min |
| Fusion | 2 min | 4 min |
| Anemoi-Spread diffusion (~10 members) | 6 min | 10 min |
| Post-processing | 4 min | 8 min |
| **Total** | **42 min** | **70 min** |

The saving is almost entirely Anemoi-Spread. A smaller ensemble is a real loss of tail resolution — it is a smaller loss than delivering nothing before the advisory goes out.

---

## Deriving the vitals timeout

The scope wrote the timeout as a flat **t+1:30**. That does not survive the arithmetic:

```
1:30 start + 1:10 reduced worst case = 2:40 finish
3:00 advisory − 2:40 = 20 min margin.  Required: 30.  Short by 10.
```

`derive_vitals_timeout()` computes it from the budget instead:

```
timeout = advisory_offset − reduced_worst_case − margin
        = 3:00 − 1:10 − 0:30
        = 1:20
```

Deriving rather than asserting keeps the three numbers consistent when any one is retuned. Change a stage budget and the timeout follows. `test_vitals_timeout_is_derived_not_asserted` pins it.

---

## Load shedding

When the cycle starts late enough that the standard profile would breach the margin, `plan_cycle` switches to `REDUCED_BUDGETS` and sets `load_shed`:

```python
plan = plan_cycle(t, oracle)
plan.load_shed                   # True after a late fix
plan.meets_advisory_deadline     # True — shedding restored the margin
plan.degraded                    # True
```

`allow_load_shedding=False` disables it. `test_load_shedding_can_be_disabled_and_then_the_deadline_is_missed` documents the trade explicitly rather than leaving it implied.

`plan.requested_ensemble_members` is what actually makes the reduction real: `DEFAULT_ENSEMBLE_MEMBERS` (20) normally, `REDUCED_ENSEMBLE_MEMBERS` (10) once `load_shed` is set. `run_cycle` passes the *effective* count (below) to the ensemble generator on every call, and to the climatological fallback if the generator raises — so a shed cycle actually runs a smaller ensemble rather than just carrying a flag that nothing downstream reads. A shed cycle also gets `load_shed:members=N` appended to `CycleOutput.flags`, consistent with "degradation is always flagged, never silent."

---

## Running a cycle

```python
from anemoi.inference.scheduler import plan_cycle
from anemoi.inference.cycle import run_cycle

plan = plan_cycle(t, oracle)
output = run_cycle(plan, initial_fix, deterministic_fn, ensemble_fn)
output.payload()
```

`ensemble_fn` takes the deterministic forecast **and** the effective member count: `Callable[[DeterministicForecast, int], list[EnsembleMember]]`. A caller that also accepts a user-requested size (the CLI's `--members`, the API's `members` field) passes it as `run_cycle`'s own `requested_members` keyword argument, not by wrapping `ensemble_fn` itself — `run_cycle` computes `effective_members = min(plan.requested_ensemble_members, requested_members)` once, internally, and uses that same number for **both** `ensemble_fn` and the climatological fallback below it.

This wasn't always true: a real bug, found via the deployed console (a user set `members=10` and still saw `ensemble_size: 20` in the response), shipped for a while where only a caller-side `lambda det, n: ensemble_fn(det, min(user_requested, n))` wrapper ever saw the user's request — which meant it only ever took effect on the happy path. The moment `ensemble_fn` raised and `run_cycle`'s own internal `climatological_ensemble(deterministic, n_members=requested_members, ...)` fallback took over (the common case in practice today, see #100/PINN's live-ensemble gap below), that fallback used `plan.requested_ensemble_members` directly, silently discarding whatever the caller had actually asked for. There was no flag for this — from `run_cycle`'s own point of view, respecting the scheduler's number *is* the correct, non-degraded behavior, so nothing about it looked like a failure. Fixed by moving the clamp into `run_cycle` itself, applied identically on both paths.

**The other direction is refused, not capped (#187).** Because this is a `min`, a request *larger* than the scheduler's own number can never be honoured — and for a long time it was accepted and then quietly reduced. `RunCycleRequest.members` advertised `le=100`, so the console offered up to 100, and a cycle run with `members=30` came back as a normal 20-member cycle with nothing anywhere recording that the request had been changed. Confirmed in production on EP172026 (2026-09-29): form `members: 30`, cycle status `ensemble: 20 members`, empty `flags`.

The fix is a bound, not a flag. Flagging it was the obvious move and is wrong here: `build_products(degraded=bool(flags))` means *any* flag marks the whole cycle degraded, and a full 20-member ensemble is not a degraded cycle merely because somebody asked for 30. So `members` is now bounded by `DEFAULT_ENSEMBLE_MEMBERS` at the schema, and an over-large request gets a `422` instead of a silent substitution. Load shedding keeps its flag, because that one *is* real degradation.

### Reproducibility: the served sampler is seeded (#188)

Re-running one cycle label returns the same forecast. That sounds like it should never have needed saying, but the served path drew from torch's global RNG: `real_inference_ensemble` called `model.sample(z_t, n_members=n_members)` with no `generator`, so every call was a fresh draw. Every *other* caller already passed one — `spread_backtest`, `real_run_diffusion` — and `run_cycle`'s own climatological fallback is seeded too (`ensemble_seed=0`), which left the real production path as the only non-reproducible one.

Observed in production on EP172026, cycle `20260929_00Z`, four runs inside ~70 seconds: RI fractions of 20%, 30%, 35%, 25% — straddling the 30% alert threshold, so the banner flipped between "no rapid intensification signal" and "rapid intensification flagged" while nothing about the storm or its inputs had changed.

The seed is **derived, not configured**: `cycle_sample_seed(storm_id, target_time)`, a SHA-256 of the cycle's own identity. `hashlib` rather than the builtin `hash()` specifically because Python salts string hashing per process — `hash()` would be stable inside one container and differ across restarts and replicas, which is precisely the reproducibility this exists to provide. There is no operational knob here to get wrong, and two different cycles still get independent noise.

Worth keeping separate in your head: this makes the served product *reproducible*, it does not make it *precise*. That second half is addressed below.

### Ensemble size sets the precision of every §6.1 product (#188)

The RI flag was only the most *visible* symptom, because it is the one with a hard threshold. Every product in the suite is a quantile or a fraction estimated from the same draws: the cone radius is `np.percentile(distances, 67)`, the intensity band is p10/p90, landfall and RI are member fractions. The member count therefore sets the precision of all four at once, and the smallest probability expressible at all is `1/n`.

At 20 members, with no model error and no input change whatsoever, the served numbers moved this much across repeated draws (90% range):

| n | cone radius (true 62 nm) | intensity p90 (true 109 kt) | RI fraction (true 27%) |
|---|---|---|---|
| 20 | 48–76 nm | 99–116 kt | 10–45 % |
| 50 | 53–71 nm | 103–114 kt | 18–38 % |
| 100 | 55–68 nm | 105–113 kt | 20–34 % |

Two consequences worth naming. A true p90 of 109 kt is Cat 3 (96–112), but the *served* value at n=20 ranged 99–116 kt — so the category badge `IntensityPDFChart` draws could flip between consecutive cycles with nothing real having changed. And a 20-member ensemble cannot express any probability below 5%, so a reported `0%` landfall probability meant "below our resolution", not "will not happen", with nothing in the payload distinguishing the two.

**It also biased the calibration audit.** A *perfectly* calibrated ensemble — truth drawn from exactly the distribution the members come from — measures only 62.1% containment at n=20 against the 67% nominal, because `cone_radius_from_spread` centres the cone on the ensemble mean (itself off by ~σ/√n) and takes a 20-sample percentile. That −4.9 point error is a third of `calibration_audit._VERDICT_MARGIN`, and it leans "too narrow", the same direction #166 has been chasing. At 50 it falls to −2.3.

`DEFAULT_ENSEMBLE_MEMBERS` is therefore **50**, and `REDUCED_ENSEMBLE_MEMBERS` 25 (preserving the 2:1 shed ratio #8 chose). This is affordable because `TrajectoryDenoiser.sample` carries members as a *batch dimension* — one forward pass per denoising step regardless of count. Measured at the production architecture, 20 → 50 members costs 0.06 s → 0.09 s; even at 16× the model size it stays under 2 s against the 13-minute budget. The budget is spent on Group 1 forward passes and input fetches, not on ensemble size.

A corollary worth flagging: this means load shedding's member reduction buys far less wall time than its design assumed. Recorded in #188, not changed here.

### The flag is three-state, because two states cannot be honest (#188)

More members narrows the estimate; it does not make a point estimate honest about its own uncertainty. `ForecastProducts` now carries a 95% Wilson interval (`ri_probability_lo`/`_hi`) and `ri_uncertain`, true when that interval spans the alert threshold. `RIFlagBanner` renders three states accordingly: **flagged**, **undetermined**, and **no signal**. Wilson rather than the normal approximation because the latter is worst exactly where this is used — small `n`, proportions near 0 or 1 — where it returns bounds outside [0, 1].

These three fields are optional on `CyclePayload`. That shape is *persisted*, not just served (#175), so every cycle written before this is still in R2 without them — including the ones `calibration_audit` reads back. `None` means "this cycle predates the interval", which is true; the alternative was failing to parse the system's own history.

Guardrails run before any model:

- the initial fix must not be `FINAL` quality
- the fix's valid time must match the cycle
- every source the plan resolved must be operational-role
- if the plan expects an extrapolated fix, the supplied fix must actually be `ESTIMATED`

### A real `deterministic_fn` and `ensemble_fn`, not just the synthetic demo ones (#78, #85)

`run_cycle`'s own `deterministic_fn(plan, initial_fix)` signature has no room for a real `Track` (only the current `Fix`), so `training.real_inference_cycle.build_real_deterministic_fn(track, registry, checkpoint_store, cache_dir)` closes over the storm's real known history and returns a real closure matching that signature. For each of the five Group 1 models it loads the registered staging/production checkpoint (`training.real_inference.load_trained_model`, reconstructing the exact architecture from a real `arch_params` registry tag — checkpoints only ever save `state_dict()`, never the architecture that produced it), builds its real live feature (`training.real_inference_live.build_live_<model>_x` — every existing training-time builder is built on `iter_stage_windows`, which discards exactly the kind of window live inference always is: one with no future fix to compute a target from), runs a real forward pass, and un-standardizes back to real units using the version's own `x_mean`/`x_std`/`y_mean`/`y_std` tags (also only ever recorded starting with #78 — real inference is mathematically wrong without the exact stats a specific checkpoint's weights were trained against). PINN's own live feature builder additionally needs its candidate-generator LSTM's own forecast converted to absolute coordinates first, mirroring `real_run_pinn._candidate_and_true_absolute`'s training-time conversion.

When all five real predictions are available and `fusion` has a registered version, the five combine via the real, **learned** `ConsensusFusion` model (the actual §6.1 fusion layer) rather than an approximation of it. Whenever fewer than five are real (a missing registered version, a live feature that couldn't be built, PINN's storm entirely over land...), falls back to the real, existing non-learned inverse-error consensus (`fusion_weights` above) using each contributing model's own recorded validation error — `ConsensusFusion` has a fixed `n_models=5` and cannot run at all with fewer.

Each contributing model's own absolute `(lat, lon, wind_kt)` prediction is computed here too, before fusion combines them into the single track above -- `DeterministicForecast.per_model_tracks` (keyed by architecture slug, same keys as `contributors`) carries it through rather than discarding it once fusion has what it needs. `api.convert.cycle_products_out` surfaces it as `CycleProducts.per_model_tracks` (see API.md), and the console draws one line per contributing model in that model's own brand color, hover-isolated from the Model Pantheon panel. Empty for the synthetic fallback and `DemoState` -- neither runs a real per-model forward pass to have one.

The same function also builds `reasons: dict[str, str]` -- why each Group 1 model that *didn't* contribute was skipped ("no registered staging/production version", "no real live feature (no cache, on-demand fetch failed)", an `InferenceLoadError`, missing standardisation stats...). Before, this was only ever surfaced in `InferenceCycleError`'s message, and only when *every* model failed -- the far more common case of some models contributing and others not had its own real reasons silently discarded the instant at least one succeeded. `DeterministicForecast.missing_model_reasons` / `CycleProducts.missing_model_reasons` carries it through unconditionally now, and the console's Model Pantheon panel renders a "Not weighing in" section from it. Real example, a real cycle on an archived Atlantic storm: `cnn`/`transformer`/`gnn` contributed; `lstm` was skipped with `"no real live feature (no cache, on-demand fetch failed)"`, `pinn` with `"no real live feature, checkpoint, or env standardisation stats"` -- both real, specific, and previously invisible anywhere in the response.

The storm detail page's header also derives a real "N/M models contributing" badge from these same two fields (`N = |contributors|`, `M = N + |missing_model_reasons|`) -- no new API surface, just `contributors.length` vs. the union of both dicts' keys, styled with the `--color-status-online` token (Branding.md's "Status tokens") when every model is contributing and a neutral tone otherwise. Each Model Pantheon row also carries an always-visible architecture-family subtitle (`WindGod.role` in `console/src/lib/branding.ts` -- "LSTM / GRU", "Transformer", etc., taken verbatim from this catalog's own section headings below) beneath the god name, separate from the hover-only persona line.

`training.real_inference_ensemble.build_real_ensemble_fn` is the real `ensemble_fn` counterpart: encodes the current live window through all five models' own `.encode()` (the same real standardized inputs the forward-pass path builds, stopped one layer earlier), concatenates in `real_latents.GROUP1_ORDER` (the order the real diffusion model's own `latent_dim` was trained against), then runs the real, trained `TrajectoryDenoiser.sample()`. Unlike the deterministic path, there's no non-learned fallback here — an ensemble *is* the diffusion model's real product, not an approximation of one; when it can't run for real, it raises and `run_cycle`'s own existing degradation to `climatological_ensemble` (§10.1) takes over.

`api.real_state.RealState` wires both of these into the API itself, as a real, parallel implementation of `demo_state.DemoState`'s exact public surface — `api.routers.storms`'s own docstring already promised "swap `DemoState` for a real ingestion-backed store and every route below is unchanged." Real storms come from two real sources, merged: a real HURDAT2 archive (the most recent seasons — historical, not live) plus `data.live_atcf.fetch_live_tracks`, a genuinely live "current storm right now" feed — NHC's real `CurrentStorms.json` index (the same one nhc.noaa.gov's own site renders "Active storms" from) plus each active storm's real TC-Vitals bulletin history (`ftp.nhc.noaa.gov/atcf/com/{id}-tcvitals-arch.dat`), parsed by the same `data.atcf.parse_tcvitals` the working-track productionization row above already built. Live storms are re-fetched on a 30-minute TTL (`RealState._LIVE_STORMS_TTL`) rather than once at process start, since the Cloudflare Containers deployment (`docker/api/`) runs as a long-lived singleton that can stay warm for hours. A live storm's `latest_fix.quality` is `working` (the console renders this as "working fix," distinct from an archive storm's "final (archive)" badge — no frontend change was needed, `StormCard.svelte` already had the label for it). Opt in via `ANEMOI_API_REAL_STATE`; `DemoState` stays the default, fully unchanged. `/v1/health`'s `state_mode` field reports which is active, and the console frontend labels itself accordingly instead of always claiming "demo."

Validated against a real live sample (2026-09-22): Atlantic storm AL062026 "Fay," TC-Vitals' 18 m/s wind converts to 35.0kt, matching the concurrent real b-deck BEST row's 35kt exactly.

**Running a cycle against an archived (no-longer-active) storm is not a separate "backtest mode" — it's the same code path, and that's correct, not a gap.** `run_cycle`/`build_real_deterministic_fn` have no concept of wall-clock "is this happening right now"; a cycle is just "forecast forward from this fix at this target time," using whatever real trained models are currently registered. Running it against, say, `AL172023` genuinely exercises the real models exactly as if that storm were active today. This is also honestly meaningful, not just mechanically possible: `data.splits.SPLIT_BOUNDARIES` puts full seasons 1980–2019 in train, 2020–2022 in val, 2023–2025 in test (the GDAS-constrained real-data boundaries used for the actual real training runs are narrower — 2021–2022 train, 2023 val, 2024–2025 test — but 2023 lands in the held-out set either way). A real cycle against a 2023 storm is inference against data no real training run has memorized, the same real generalization test validation metrics already rely on — not a storm the models have "seen before" in any sense that would make the result suspect.

### A future-dated cycle is rejected, not silently estimated

`LatencyOracle`/`plan_cycle` have no built-in concept of real wall-clock "now" — by design, since a replay harness needs to plan a hypothetical cycle before it happens. Found live: `POST /v1/storms/EP172026/cycles {"cycle": "20260923_00Z"}` a full day ahead of real UTC time returned `vitals: observed`, using the storm's stale last-known position simply relabeled with the future timestamp — because `LatencyOracle.published_at` always returns `valid_time + latency`, regardless of whether that time has actually elapsed. `api.real_state.RealState.run_cycle` is the one real call site running against real wall-clock time, so it now rejects (`CycleError`, HTTP 400) any `cycle` label whose synoptic time hasn't begun yet (`target > datetime.now(UTC)`). A cycle whose target time has already begun — including the one currently in progress, before its real vitals have landed — is unaffected; that's exactly the existing, honest `vitals_estimated` degraded mode. `DemoState` is deliberately left untouched (it's a synthetic sandbox with no real wall-clock claim to honor).

### The console's v1.2 styling pass: Wind Rose Projection, intensity indication, landfall projection, verification

A second real-data comparison against the Branding Brief v1.2 concept mock (this time its `WindRoseMap`/`IntensityChart`/`Landfall Probability`/`Verification` panels), the same "adopt what's real, dismiss what isn't with reasoning" pass the Model Pantheon/panel-typography round used.

**Map (renamed "Wind Rose Projection," not replaced).** The real interactive MapLibre map stays — the concept's own SVG mockup has no real geography (a fixed illustrative coastline, hardcoded pixel coordinates), so it was never a real alternative to a real basemap. What *was* adopted: each forecast point's dot is now colored by its own real `wind_kt` via the real, external NHC Saffir-Simpson classification (`console/src/lib/utils.ts`'s `SAFFIR_SIMPSON`/`saffirSimpson`, see Branding.md's colour rules for why it's a deliberately separate axis from god/status colours), its label carries the real category (originally `+48h · 35kt · TS`; since #209 the point's valid time instead of its lead, `08/12Z · 35kt · TS`, because a lead counted from the cycle sat beside a current-fix marker from a later synoptic time and read as "hours from now" -- [Decision Log #47](Decision-Log#47-the-storm-page-never-said-which-cycle-it-was-showing-209--bugfix)), and the current-fix marker's pulse rate now scales with the real `max_wind_kt` (stronger storm, faster pulse). Deliberately **not** adopted: the concept's concentric fixed-radius "lead time" rings around the current fix — on a real geographic map a storm's real ground speed varies, so a static ring at some radius doesn't correspond to "reachable by hour N" in any honest way; drawing one would be a real, if subtle, fabrication that only worked in the concept's own stylized, non-geographic SVG space.

**Intensity indication.** `IntensityPDFChart` gained a real "peak intensity" readout — the fused p50 track's own maximum plus the lead hour it occurs at, with its own Saffir-Simpson category badge. Its fan-chart line/band, previously `--color-boreas` (a real, found-in-passing branding bug: the fused/consensus intensity has never been Boreas-specific), now correctly uses `--color-fusion`, matching how the map's own fused track is coloured. RI probability was **not** duplicated here — `RIFlagBanner` at the top of the page already surfaces the real `ri_probability`/`rapid_intensification` fields, and repeating it would just be the same real number rendered twice. The concept's "Skiron CRPS: 0.27" metric was **not** adopted — no real CRPS computation exists anywhere in this codebase.

**Landfall projection, now actually reachable.** `postprocess.landfall_probability` (fraction of real ensemble members passing within 60nm of a real coastal reference point, across all leads) has existed since the §6.1 product suite shipped, and `RunCycleRequest` has always accepted `coastline_lat`/`coastline_lon` — but the console's run-cycle form never had a field to set them, so `landfall_probability` was `null` on every cycle ever run from the UI. Fixed: a "coastline lat/lon" input pair next to `members`, `CycleOutput`/`CyclePayload` now echo back the real reference point that was actually used (`coastline_lat`/`coastline_lon`, `None` when not supplied), and a dedicated Landfall Projection panel shows the real probability, the real reference point, and the real 60nm threshold — plus a marker on the map at that point. The concept's own five-segment "TX Upper Coast 9% / SW Louisiana 31% / …" breakdown was **not** adopted — `landfall_probability` is one aggregate float across the whole ensemble/all leads, there is no real per-coastal-segment computation anywhere in this codebase to back a breakdown like that.

**Verification, honestly scoped.** `monitoring.skew.SkewReport` (the real §4.6.3 ERA5T-vs-operational audit, already surfaced on `/monitoring`) is a system-wide rolling 14-day window — not scoped to any one storm or cycle. The storm page's new Verification panel shows it anyway (mean track delta, mean |intensity delta|, intensity bias, sample count, alert badge), but says so explicitly ("system-wide … not specific to {storm_id}, the same rolling window every storm's page shows") rather than implying it's this storm's own verification — the same number would render identically on any other storm's page. The concept's "NHC beat rate: 57%" metric was **not** adopted — no comparison against real NHC official forecasts is computed or stored anywhere in this codebase (a one-off manual comparison was done earlier this session via a direct `curl` against NHC's real ATCF archive, but that was ad hoc analysis, not a persisted, queryable system feature).

### The storm page says which cycle it shows (#209)

A panel under the storm name states the forecast cycle on screen ("the latest run", or "an older run; the latest is X" with **Show latest**), that map times count from that cycle rather than from the latest fix, and -- for an active storm -- whether the current synoptic cycle is still to come: scheduled (t+1:30, shown in UTC and the viewer's local time), should appear within a few minutes, or overdue. The header's fix line is labelled **latest fix**, and the run form is a separate **Run a new cycle** group whose input defaults to the current synoptic time. Between t+0:00 and t+1:30 those two times routinely differ from the newest cycle, which is what made the page misleading before.

### Live storms refresh single-flight (#206)

Since #206: one request fetches NHC's feed, concurrent requests serve the storms already known, and per-storm TC-Vitals bulletins are fetched in parallel.

### Basin flag: real storm data outside the Atlantic is real, but untrained

Every `StormSummary`/`StormDetail` now carries `basin` (the real two-letter ATCF basin code, a direct slice of `storm_id` — `data.atcf.storm_basin`) and `trained_basin` (`basin in data.atcf.TRAINED_BASINS`, currently `{"AL"}` only). `docs/train_infrastructure.md` curls only the Atlantic HURDAT2 archive for both Stage A and Stage B — confirmed by grep, zero reference anywhere in this codebase to NHC's separate Eastern/Central Pacific archives. The live feed and HURDAT2 both cover more than the Atlantic, so a Pacific storm (e.g. `EP172026`) is real data, not fabricated — but genuine out-of-distribution inference for every currently trained model (see the quantitative Hurricane Polo comparison above: latitude tracked NHC's real forecast closely, longitude diverged in a structured, explicable way consistent with an Atlantic-only recurvature bias). The console surfaces this as a small badge (`{basin} basin — untrained`) on `StormCard.svelte` and the storm detail page header rather than restricting the feed — the live feed's value (seeing every real currently-active storm) outweighs hiding non-Atlantic storms, as long as the forecast is honestly labeled.

### A live cycle's missing-model reason distinguishes real GDAS publish lag from a real failure

`training.real_inference_live._current_fields` fetches the real GDAS analysis GRIB2 file valid at the model's own current fix time (`data.gdas_cache.fetch_one`), not a forecast-hour product from an earlier base cycle — the CNN/Transformer/GNN/PINN live features are trained on real analysis fields matched to each fix's own synoptic time, so substituting an older cycle's field would be a real correctness regression, not a legitimate degrade. GDAS's own real publish latency (`data.sources.get("gdas_gfs")`, ~3.5h typical) means a live cycle run soon after its own synoptic time can hit a real "the file doesn't exist yet" 404 — found live against `AL062026` at `20260922_06Z`, requested ~3h after its own synoptic time. `training.real_inference_live.gdas_likely_unpublished(valid_time)` (real wall-clock-aware, compares against `data.sources`' own typical latency) doesn't skip the fetch attempt — real GDAS timing has genuine variance, and giving up a real chance to contribute for a marginal hygiene win would be a real capability regression — but when the fetch does come back empty and this returns `True`, `missing_model_reasons` gets a specific, honest "likely hasn't published yet, should resolve on a later cycle" message instead of the generic "on-demand fetch failed," the same operator-transparency goal `missing_model_reasons` itself exists for.

### Dissemination payload

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
  "cone": [
    {"lead_hours": 12, "lat": 23.347, "lon": -73.127,
     "radius_nm": 13.4, "basis": "ensemble"}
  ],
  "flags": []
}
```

`basis` tells a consumer whether a cone segment came from ensemble spread or fell back to climatology. `flags` is empty on a clean cycle — see [Degraded Modes](Degraded-Modes).

---

## Post-processing

`inference/postprocess.py` produces the §6.1 product suite: cone, intensity PDF (10/25/50/75/90 percentiles per lead), landfall probability, rapid-intensification flag (≥30 kt gain in 24 h; alert at ≥30% of members).

### The cone guard

NHC's official cone is built from *historical* official-forecast error percentiles, not from current ensemble spread. A cone drawn from a model's own spread is only honest if that spread is calibrated.

Calibration **cannot be measured at forecast time** — there is no observation yet. `spread_skill` is a post-hoc verification tool only.

`build_cone` uses a real-time proxy instead: the ensemble radius at the longest lead against the climatological radius. Below 50% of climatology, it falls back to climatological radii and says so in the notes.

> An ensemble dramatically tighter than climatology five days out is displaying the underdispersion signature of a diffusion model over-anchored to its deterministic conditioning — and that is exactly when under-drawing the cone would matter most.

Also falls back when fewer than 10 members are available.

---

Related: [Degraded Modes](Degraded-Modes) · [Operations Runbook](Operations-Runbook) · [Data Sources](Data-Sources) · [Decision Log](Decision-Log)
