# Implementation plan

How this codebase maps onto Scope v2.1, what is real, and what has to be built
next. Read `README.md` first for orientation.

---

## 1. Design stance

The scope describes an ML system, but the parts most likely to produce a wrong
forecast are not the models. They are the boundaries: which data may be read
when, which artifact is allowed to be promoted, what happens when a feed is
late. v2 had defects in exactly those boundaries — same-cycle GFS that does not
exist yet, final best-track used as an input, promotion on the test set, a
single-model retrain silently invalidating the ensemble generator.

So this implementation puts the effort there. Every boundary rule from v2.1 is a
function that raises, called at the point where violating it would be a one-line
change. The models are honest implementations with correct shapes and latent
contracts, but they are the replaceable part.

The practical consequence: `uv sync` without the torch extra gives you a
package where all the policy logic is importable and testable. Model code is
opt-in.

---

## 2. Build order

Each layer was built and tested before the next, since each depends on the
guarantees below it.

**Layer 1 — time and geometry.** `time_utils`, `geo`. Synoptic arithmetic and
the t-6 selection rule. Everything downstream assumes cycle t never reads the
cycle named t, so that is enforced here rather than remembered everywhere else.

**Layer 2 — data contracts.** `data/sources` (role registry), `data/besttrack`
(working vs final, noise emulator, augmentation), `data/storm_relative`
(storm-relative coordinate transform for track-sequence inputs),
`data/availability` (what has published), `data/features` (one code path per
flavor), `data/splits` (storm-wise + chronological). This layer is where the
train/serve policy is mechanised.

**Layer 3 — training policy.** `training/curriculum` (Stage A/B),
`training/promotion` (validation-only gates, test-set budget),
`training/orchestrator` (wave scheduling), `training/triggers` (cascade).

**Layer 4 — tracking.** `tracking/tags` (validated tag set),
`tracking/registry` (MLflow-optional, model-set pinning), `tracking/checkpoint_store`
(S3/R2-compatible durable checkpoint storage, duck-typed the same way as the
MLflow client so tests need no real credentials).

**Layer 5 — inference.** `inference/scheduler` (timeline, gating, load
shedding), `inference/cycle` (execution, degraded modes),
`inference/postprocess` (products).

**Layer 6 — monitoring and metrics.** `monitoring/skew`, `monitoring/drift`,
`metrics/track`, `metrics/probabilistic`.

**Layer 7 — models.** Seven PyTorch builders, all returning `(module, spec)`.
`training/device` picks MPS/CUDA/CPU for local (non-cloud) runs.
`training/capacity_ablation` and `training/noise_sensitivity` are diagnostic
harnesses built on the same LSTM-proxy methodology (see `docs/`), not
production training code.

---

## 3. Design decisions worth stating

**Availability is a queryable model, not an assumption.** `AvailabilityOracle`
is a protocol; `LatencyOracle` implements it from the registry's latency table,
with per-source overrides and outage injection. Every timing test is written
against a configured oracle rather than a mocked clock, so an outage scenario is
three lines and a replay harness for a real season is a second implementation of
the same protocol.

**Degradation is always flagged, never silent.** Every fallback path appends to
`CycleOutput.flags` and surfaces in the dissemination payload: `vitals=estimated`,
`nwp_stale=12h`, `spread_fallback:RuntimeError`. A forecaster who cannot tell
a full-ensemble cycle from a climatological-fallback cycle will eventually treat
both the same way, and the second is much weaker.

**Opportunistic feeds are distinguished from optional ones.** Aircraft recon and
microwave overpasses are absent from most cycles by nature. Flagging their
absence would mark every cycle degraded and destroy the flag's meaning, so
`InputStatus.opportunistic` separates "normally missing" from "unexpectedly
missing".

**The fusion weight floor.** Both the learned fusion layer and the fallback
`fusion_weights` clamp weights above a floor. Mid-season there may be only a
handful of verifying storms; a model zeroed out on three cases is unrecoverable
for the rest of the season.

**The test set is metered.** `TestSetBudget` rate-limits evaluations and demands
a written justification. §4.4 reserves 2023-2025 for an unbiased comparison
against NHC consensus, and that reservation is only worth anything if looks are
counted.

**Latent coupling is a signature.** `latent_signature()` hashes the Group 1
version set; derived models record the signature they trained against, and
`pin_set` refuses a set whose signatures disagree. This is what makes "retrain
the affected model only" impossible to do accidentally.

---

## 4. What is synthetic, and what replacing it involves

| Component | Status | To productionise |
|---|---|---|
| Storm archive | Parser done (`data.hurdat2.parse_hurdat2`); exercised against the real 1851-2023 Atlantic archive by the #9 capacity ablation (`anemoi ablation --hurdat2 <path>`), not yet wired as the CLI/API/demo default source | Point the CLI/API/demo at a real HURDAT2 file |
| Working track | Parsers done (`data.atcf.parse_bdeck`, `parse_tcvitals`); `pair_by_valid_time` + `recalibrate_from_pairs` demonstrated on parsed data | Point at a real archive; recalibrate Stage B's noise defaults from it |
| Gridded fields | Real readers done (`data.real_gridded`): ERA5 via public Zarr, GDAS/GFS via byte-range GRIB2; synthetic still the pipeline default. `data.era5_cache`/`data.gdas_cache` (shared engine: `data.gridded_cache`) fetch+cache real fields concurrently for Stage A/B; run as `slurm/` job scripts (see `docs/train_infrastructure.md`). GDAS's real archive only goes back to 2021-01-01 (undocumented retention -- see `data.gdas_cache.GDAS_ARCHIVE_START`), so fetch auto-filters fixes before it and `--sync-archive` backfills what's fetched into durable R2 storage rather than depending on NOAA's bucket as the system of record | Point the CLI/API/demo at real reads; wire real SST/OHC sources |
| Satellite | Synthetic crops (`data.satellite`), matching `data.synthetic`'s role for `GriddedFields` | Real GOES-18/19 storm-relative crops from the already-registered `goes` source |
| Potential intensity | SST/OHC/shear regression (still the pipeline default); real Bister-Emanuel (1998) closed form implemented separately (`emanuel_potential_intensity`), not yet wired in | Real boundary-layer/outflow soundings, then swap the one call site in `compute_environment_features` |
| Cone radii | Current-season (2026) NHC 2/3-probability radii, documented in `configs/inference.yaml` | Re-baseline each season against nhc.noaa.gov/aboutcone.shtml |
| Appendix B thresholds | Provisional | Re-baseline against the current NHC verification report |
| Models | LSTM: real Stage A/B runner exists (`training.real_run.run_lstm_curriculum`, `anemoi train --model lstm`, #22) -- track-only architecture, so it needs no gridded-field cache, trains against real HURDAT2 tracks with real multi-lead verification and durable checkpoint upload. CNN: real runner exists too (`training.real_run_cnn.run_cnn_curriculum`, `anemoi train --model cnn`) -- reads real cached GriddedFields (all 10 fields) as its channel stack in place of not-yet-fetched real GOES imagery, works with however much of the era5_cache/gdas_cache is cached so far. Transformer/GNN/PINN: untrained, no real runner yet (field-variable stack at a fixed real grid size, graph construction over the grid, environment vector + a base model's candidate track respectively) | Real runners for Transformer/GNN/PINN; wire `training.orchestrator.run_schedule`'s injected `runner` to call each real per-model runner instead of a hand-invoked CLI per model |

The synthetic generator's ERA5/GDAS offset (`synthetic.GDAS_BIAS`) is
deliberate and load-bearing for the tests. It is not a claim about the real
offset between those analysis systems.

---

## 5. Open items

Citations for everything below are in `docs/references.md`.


**Sample size -- measured (LSTM proxy); transformer itself still open.** The
real HURDAT2 archive gives 561 training-split storms / 16,474 synoptic fixes
(1980-2019, `data.splits.DEFAULT_BOUNDARIES`) -- confirms the "thin" concern
at roughly the scale this section originally estimated. `data.storm_relative`
(storm-relative coordinate transform) and `data.besttrack.augment_track`
(augmentation strategy: independently re-emulated working-quality realisations
per storm) are both implemented and used by the ablation.
`training.capacity_ablation.run_capacity_ablation()` swept LSTM hidden width
(8-128) against training-storm fraction (10%-100%) on real data; full
results, method and caveats in `docs/capacity_ablation.md`. **Decision: GO on
capacity** -- validation loss keeps improving substantially through
hidden_dim=128 with no sign of flattening, so nothing here justifies capping
the transformer's size on capacity grounds. The sample-size axis of that run
is **inconclusive, not "no effect"**: fixed-epoch full-batch training gives
every fraction the same number of gradient updates, which confounds "more
data doesn't help" with "the training procedure under-trains the large-data
cells" -- re-run with mini-batching before trusting that axis. This LSTM
result does not by itself clear the transformer's gridded-field capacity for
Stage A/B (#22); that needs the same experiment against real ERA5/GDAS
fields. The ablation runs entirely on a local machine (Apple Silicon MPS via
`training.device.get_device()`, ~16s wall-clock for the full grid), no
rented compute needed.

**Ensemble dispersion at recurvature.** Anemoi-Spread conditioned on Anemoi-Core latents
will tend to underdisperse precisely where the distribution is bimodal.
`build_diffusion(extra_conditioning_dim=...)` exists so raw fields or GEFS/EPS
perturbations can be added to the conditioning vector. The rank histogram and
spread-skill ratio in verification are how you find out whether that was enough,
and both should be tracked per-lead from the first backtest.

**Absolute skill targets — 48h track re-baselined, others still open.**
`training.promotion.TRACK_THRESHOLDS`'s `track_error_48h_nm` moved from 90.0
to 70.0 nm, grounded in NHC's GPRA performance-measures table (45.4 n mi
realized 2024, 53.4 n mi 2025, 51.0 n mi 2026 target) rather than the
scope-era placeholder. The beat-rate gates remain the real claim because they
measure against a live baseline; this absolute number is a backstop, not a
claim of parity with NHC. `track_error_72h_nm`, `track_error_120h_nm`, and
both intensity thresholds are **not** re-baselined — the GPRA table only
publishes the 48h figure, and extrapolating a lead-time curve from one
verified point would be fabricating precision. Pull the full lead-time
breakdown from the spring Verification Report before touching those.

**Noise-emulator recalibration — measured, not load-bearing at this
precision.** Emanuel and Zhang (2016) find intensity error growth over the
first few days is dominated by initial-intensity error — exactly what
`emulate_working_fix()` perturbs, at exactly the leads the promotion gates
score. The scope's 5 kt / 3 mb defaults are roughly half the published
estimates (Torn and Snyder 2012), and the real error is intensity-dependent,
which the scalar-RMS emulator cannot express.
`training.noise_sensitivity.run_noise_sensitivity()` measured the sensitivity
on real HURDAT2 data (same LSTM-proxy methodology as the capacity ablation,
§ above): training a fixed architecture on default- vs. literature-noise
emulated inputs, evaluated against a fixed literature-noise validation set,
moves validation loss by **+0.21%** — not load-bearing at a 5% threshold.
Full results, method and the per-dimension robustness check in
`docs/noise_sensitivity.md`. **Decision: recalibration can reasonably wait**
for real paired working/final data (#17-scale) rather than being treated as
a Stage B blocker. The structural gap remains open regardless: both noise
candidates are a single scalar RMS, while the literature's own numbers are
intensity-*dependent* — representing that (e.g. `WorkingTrackNoise` keyed on
category rather than one constant) is a `besttrack` change that needs real
paired data to fit against, tracked as a follow-up, not attempted here.

**Two structural gaps in the feature set, both intensity-side — minimum-viable
versions closed.** Inner-core moisture (Emanuel and Zhang 2017 find it matters
as much as the wind field) now has `rh700_inner_core_pct`, sampling the same
700 mb field over a tight inner radius rather than the large environmental box
`rh700_pct` uses. Ocean feedback — SST/OHC were static daily values persisted
from the previous day, so a storm's own cold wake was nowhere in the system —
now has `features.apply_cold_wake()`, an empirical SST/OHC depression from the
storm's own wind and translation speed, applied to `GriddedFields` before
feature computation. Neither is the full treatment: a dedicated higher-resolution
inner-core product (satellite; see the productionization table) and real
two-way atmosphere-ocean coupling both remain further, larger work.

**Track and intensity thresholds should not share a table — done.** Intensity
skill has improved far more slowly than track skill, so a beat rate on
intensity is a claim about a near-static baseline close to an intrinsic
predictability limit. `training.promotion` now exposes `TRACK_THRESHOLDS` and
`INTENSITY_THRESHOLDS` as separate tuples (`DEFAULT_THRESHOLDS` is their
union, so `evaluate_promotion`'s default is unchanged), so each can be
re-derived on its own schedule instead of one shared table.

**Consistency distillation beats load shedding if the diffusion budget binds.**
Song et al. (2023): one-step generation by design, multistep still available,
distillable from an already-trained diffusion model — a graded response to time
pressure rather than dropping members. Evaluate before relying on the shedding
path in production.

---

## 6. Test suite map

| File | Covers |
|---|---|
| `test_time_utils.py` | Synoptic arithmetic; t-6 selection; t-12 fallback |
| `test_sources.py` | Role assignment; operational guard |
| `test_besttrack.py` | Working/final separation; emulator statistics; recalibration; augmentation |
| `test_hurdat2.py` | HURDAT2 parsing; synoptic-hour filtering; missing-field handling; longitude wrap |
| `test_storm_relative.py` | Storm-relative displacement geometry; sequence shape and column contract |
| `test_atcf.py` | b-deck/TC-Vitals parsing; unit conversion; working/final pairing + recalibration |
| `test_availability.py` | Publication timing; outages; opportunistic feeds |
| `test_scheduler.py` | Cycle timeline; vitals gating; load shedding; deadlines |
| `test_curriculum.py` | Stage A/B ordering; flavor rules; deployability |
| `test_promotion.py` | Validation-only gates; manual gate; test-set budget; track/intensity threshold split |
| `test_registry.py` | Versioning; model-set pinning; rollback; MLflow degradation |
| `test_checkpoint_store.py` | S3/R2 upload/download round-trip; bucket-mismatch rejection; env-var config; boto3 adapter wiring |
| `test_triggers.py` | Trigger conditions; cascade; nightly-latent suppression |
| `test_orchestrator.py` | Wave schedules; dependency handling; failure isolation |
| `test_skew.py` | ERA5T audit; alert thresholds; windowing |
| `test_drift.py` | Feature drift; reference flavor; validation-loss trigger |
| `test_metrics.py` | Track/intensity errors; beat rate; DM test; CRPS; spread-skill |
| `test_features_splits.py` | Dual-flavor parity; flavor guards; split leakage; inner-core moisture; cold wake; Emanuel PI closed form; `STAGE_B_BOUNDARIES` validity and per-season assignment |
| `test_cycle.py` | End-to-end cycle; every degraded mode; extrapolation |
| `test_postprocess.py` | Cone construction and fallback; PDF; landfall; RI |
| `test_tags.py` | Tag validation; v2.1 additions |
| `test_synthetic.py` | Generator reproducibility and statistics |
| `test_satellite.py` | Synthetic GOES crop shape/channels; intensity-dependent structure; CNN integration |
| `test_real_gridded.py` | ERA5/GDAS unit conversion and cropping (synthetic-schema); real endpoints behind `ANEMOI_RUN_NETWORK_TESTS=1` |
| `test_era5_cache.py` | Fetch-task building; cache round-trip; resumable skip logic; concurrent execution; failure isolation (fake fetcher, no network) |
| `test_gdas_cache.py` | Same coverage as test_era5_cache.py for the GDAS/Stage B analog; shared-session wiring; default filtering of fixes before `GDAS_ARCHIVE_START` |
| `test_gridded_cache.py` | Shared-engine pieces not covered via the era5/gdas wrappers: `filter_tracks_by_min_valid_time`, durable archive sync (`sync_cache_to_archive`) against an in-memory fake archive client |
| `test_cli.py` | `era5-cache`/`gdas-cache` select the right `data.splits` boundary scheme (default vs. `STAGE_B_BOUNDARIES`) |
| `test_real_run.py` | Multi-lead sample building and masking; displacement/lat-lon round trip; masked-loss LSTM training reduces loss; encoder freezing; full Stage A->B curriculum against a fake checkpoint store, including that Stage B starts from Stage A's trained (not fresh) weights |
| `test_real_run_cnn.py` | Same coverage as test_real_run.py for the CNN baseline, plus: channel stack built from all 10 cached fields, a fix with no cached file is skipped not errored, ragged cached shapes are rejected |
| `test_models.py` | Architecture shapes and latent contracts (needs torch) |
| `test_device.py` | MPS/CUDA/CPU selection priority; torch.compile skip on MPS (needs torch) |
| `test_capacity_ablation.py` | Sample-building (storm-relative + augmentation); go/no-go logic; end-to-end training grid (needs torch) |
| `test_noise_sensitivity.py` | Load-bearing/not-load-bearing logic; end-to-end default-vs-literature noise comparison (needs torch) |
