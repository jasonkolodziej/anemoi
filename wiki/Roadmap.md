# Roadmap

What is synthetic, what is unwired, and what is genuinely unresolved.

---

## 1. Replace the synthetic data layer

The first production task. Interfaces to satisfy: `GriddedFields`, `Track`, `AvailabilityOracle`.

| Component | Current | To productionise |
|---|---|---|
| Storm archive | Parser done (`data.hurdat2.parse_hurdat2`), not yet wired as the default source | Point the CLI/API/demo at a real HURDAT2 file instead of `data.synthetic` |
| Working track | Parsers done (`data.atcf.parse_bdeck`, `parse_tcvitals`); `recalibrate_from_pairs` demonstrated on real-format parsed pairs | Point at a real archive; recalibrate Stage B's defaults from it |
| Gridded fields | Real readers done (`data.real_gridded`): ERA5 via public Zarr, GDAS/GFS via byte-range GRIB2; synthetic still the pipeline default | Point the CLI/API/demo at real reads; wire real SST/OHC sources |
| Satellite | Synthetic crops (`data.satellite`), matching `data.synthetic`'s role for `GriddedFields` | Real GOES-18/19 storm-relative crops from the already-registered `goes` source |
| Potential intensity | Regression proxy (pipeline default); real closed form implemented (`emanuel_potential_intensity`), not wired in | Real boundary-layer/outflow soundings, then swap the one call site |
| Deep-layer shear | Centred box mean | Operational 200–800 km annular sampling |
| Cone radii | Placeholder table | Current-season NHC error percentiles |
| Appendix B thresholds | Provisional | Re-baseline against the current NHC verification report |
| Models | Untrained | Stage A on ERA5, Stage B on GDAS |

`AvailabilityOracle` being a protocol means a **season replay harness** is a second implementation of that interface — a good early win, because it lets the whole timing layer be validated against real feed arrival times before any model is trained.

---

## 2. Wire load shedding through — done

~~`CyclePlan.load_shed` is set and flagged, but `run_cycle` does not yet reduce the requested member count.~~ Done: `CyclePlan.requested_ensemble_members` carries the reduced count, and `run_cycle` passes it to both the ensemble generator and the climatological fallback, with `load_shed:members=N` appended to `CycleOutput.flags` so the reduction is visible on the payload rather than only on the plan. See [Inference-Cycle § Load shedding](Inference-Cycle#load-shedding) and `jasonkolodziej/anemoi#8`.

---

## 3. Recalibrate the working-track noise model — measured, not load-bearing at this precision

`WorkingTrackNoise` defaults (15 nm, 5 kt, 3 mb) are documented placeholders from the scope. `recalibrate_from_pairs()` measures the real values from archived working/final pairs, but needs real paired data at #17-scale to run against.

The published estimates said the guess might be optimistic. Torn & Snyder (2012) put satellite-only intensity uncertainty near 10–12 kt and pressure at 7–12 mb — roughly double the defaults. They also find the error is **intensity-dependent**, which the scalar-RMS emulator cannot express — that gap is real and still open (see below), independent of the sensitivity finding.

> Emanuel & Zhang (2016) find that intensity error growth over the first few days is dominated by **initial-intensity error** — precisely what the emulator perturbs, at precisely the leads the promotion gates score. This is why the question was worth measuring rather than assuming. See [References](References).

`training.noise_sensitivity.run_noise_sensitivity()` measured it on real HURDAT2 data (same LSTM-proxy methodology as the [capacity ablation](#4-open-technical-questions)): training a fixed architecture on default- vs. literature-noise emulated inputs, evaluated against a fixed literature-noise validation set, moved validation loss by **+0.21%** — not load-bearing at a 5% threshold, confirmed by a per-target-dimension breakdown so the aggregate metric isn't hiding a larger effect in one channel. Full results: [docs/noise_sensitivity.md](https://github.com/jasonkolodziej/anemoi/blob/main/docs/noise_sensitivity.md).

**Decision: recalibration can reasonably wait** for real paired working/final data rather than being treated as a Stage B blocker. The intensity-dependence gap is unaffected by this finding and remains open: `WorkingTrackNoise` is still a single scalar RMS on both sides of the comparison, and representing category-dependent error is a `besttrack` change that needs real paired data to fit against regardless.

---

## 4. Open technical questions

These have no clean fix. They need measurement.

### Sample size — measured (LSTM proxy); transformer itself still open

The real HURDAT2 archive gives 561 training-split storms / 16,474 synoptic fixes (1980–2019) — confirms the original ~10–15k estimate. Augmentation (`data.besttrack.augment_track`) and storm-relative coordinates (`data.storm_relative`) are both implemented, and both are exercised by `training.capacity_ablation.run_capacity_ablation()`, which swept LSTM hidden width (8–128) against training-storm fraction (10%–100%) on the real archive. Full results and method: [docs/capacity_ablation.md](https://github.com/jasonkolodziej/anemoi/blob/main/docs/capacity_ablation.md) in the main repo.

**Decision: GO on capacity.** Validation loss keeps improving substantially through hidden_dim=128 with no sign of flattening — nothing here justifies capping the transformer's size on capacity grounds. The sample-size axis is **inconclusive, not "no effect"**: fixed-epoch full-batch training confounds "more data doesn't help" with "the training procedure under-trains the large-data cells" — needs a mini-batch re-run before trusting that axis. And this is an LSTM proxy: it does not by itself clear the transformer's gridded-field capacity for Stage A/B — that needs the same experiment against real ERA5/GDAS fields.

### Ensemble dispersion at recurvature

Anemoi-Spread conditioned on Anemoi-Core latents will tend to underdisperse precisely where the distribution is bimodal — a recurving storm that might go out to sea or might not.

`build_diffusion(extra_conditioning_dim=...)` exists so raw fields or GEFS/EPS perturbations can be added to the conditioning vector. The **rank histogram and spread-skill ratio are how you find out whether that was enough**, and both should be tracked per-lead from the first backtest, not after deployment.

### Ocean feedback — minimum-viable version done

~~`sst_ohc` is a daily product persisted from the previous day... A storm's own cold wake... is nowhere in the system.~~ `features.apply_cold_wake(fields, max_wind_kt, translation_speed_kt)` now depresses `GriddedFields.sst`/`.ohc` by an empirical amount before feature computation — cooling grows with the cube of wind speed and falls off with translation speed, clamped to 6 °C (documented extreme-case ceiling). Applied per cycle/lead from that cycle's own wind and translation speed; not persisted across cycles and not an ocean model.

Real two-way coupling (Lai et al. 2025 driving UWIN-CM; FuXi-TC on a coupled ocean–atmosphere base) remains a separate, larger effort — this closes the "nowhere in the system" gap, not the full physics.

### Inner-core moisture — minimum-viable version done

~~Emanuel & Zhang (2017) find intensity error growth is at least as sensitive to inner-core moisture specification as to the wind field. `FEATURE_NAMES` has `rh700_pct` as an area mean over the storm-relative box — an environmental quantity, not an inner-core one.~~ `FEATURE_NAMES` now also carries `rh700_inner_core_pct`: the same 700 mb field, sampled over a tight inner radius (`INNER_CORE_RADIUS_FRAC = 0.15`) instead of the large environmental box `rh700_pct` uses. A dedicated higher-resolution inner-core product (e.g. from satellite — see §1's Satellite row) is a further step, not a prerequisite for this one.

### Absolute skill targets — 48h track re-baselined, others still open

~~Appendix B's `<75 nm @ 48 h` may already trail current NHC official performance (~55–65 nm).~~ `track_error_48h_nm` is now 70.0 nm (was 90.0), sourced from NHC's [GPRA performance-measures table](https://www.nhc.noaa.gov/verification/pdfs/GPRA_history.pdf): 45.4 nm realized 2024, 53.4 nm realized 2025, 51.0 nm 2026 target. The beat-rate gates remain the real claim because they measure against a live baseline; this is a backstop, not NHC parity. `track_error_72h_nm`, `track_error_120h_nm`, and both intensity thresholds are **not** re-baselined — the GPRA table only publishes the 48h figure, and the full lead-time breakdown needs the spring Verification Report, not extrapolation from one point. `training/promotion.py` also now splits `TRACK_THRESHOLDS` from `INTENSITY_THRESHOLDS` — see [Verification Metrics](Verification-Metrics).

### Cluster autoscaling

HPA scales pods, not nodes. On a fixed-size cluster, autoscaling a training job accomplishes nothing. Either cluster autoscaling or an explicit queue is needed for the parallel mode's 6–7 GPU peak.

---

### ~~Consistency distillation for the diffusion budget~~ — evaluated, not adopted (#15, [Decision Log #37](Decision-Log#37-consistency-distillation-evaluated-for-anemoi-spread----not-yet-warranted-15--evaluation))

The 13-minute Anemoi-Spread stage budget is what forces [load shedding](Inference-Cycle), and shedding members is a blunt response — it trades tail resolution for punctuality with no middle setting. Consistency models (Song et al. 2023) support one-step generation by design while still allowing multistep sampling to trade compute for quality, and can be **distilled from an already-trained diffusion model** — a graded response instead of a binary drop, if it works.

Prototyped (`models/consistency.py`, `training/consistency_distillation.py`, `anemoi consistency-distill`) and run for real against the production diffusion v7 champion, 637 real validation windows. The compute story is exactly what the theory promised (~100x fewer network evaluations, real wall-clock to match). The quality story is not: every tested student step count (1/2/4) came back with `track_error_48h_nm` 37-46% worse than the teacher's, a consistent point-accuracy regression even where calibration held up or improved. **Not adopted** — load shedding remains the sole real response to diffusion-stage time pressure. This is a first-pass distillation with no schedule/EMA-decay tuning, so the gap is plausibly closeable with more effort later; the tooling makes re-measuring cheap whenever that's worth revisiting.

### Elliptical cone segments

For the 2026 season NHC is issuing an **experimental cone built from ellipses rather than circles**, separating the speed and directional components of forecast error. The codebase already computes exactly that decomposition in `metrics/track.cross_along_track_nm`, so an elliptical `ConeSegment` is a natural extension and would align the product with where the official graphic is heading. Lower priority than the items above, but cheap.

---

## 5. Smaller items

- **Config loader.** `configs/*.yaml` currently document the parameters; module constants carry them. A loader would remove the duplication — and should validate `vitals_timeout_minutes` against `derive_vitals_timeout()` rather than trusting the file.
- ~~**Cone radii into YAML.**~~ Documented — `CLIMATOLOGICAL_CONE_NM` now carries the real current-season (2026) NHC radii, mirrored in `configs/inference.yaml`'s `ensemble.climatological_cone_nm`. Still a module constant kept in sync by hand, not loaded from the file — that's the **Config loader** item above, which this would benefit from along with everything else.
- ~~**Per-storm aggregation for Diebold–Mariano.**~~ Done — `metrics.track.aggregate_by_storm()`. The DM test uses a lag-0 variance estimate valid only for independent cases; Coroneo & Iacone (2024) show that with dependent losses it loses power entirely and can reject a correct null. Nothing in the code can *detect* dependence, so calling the helper remains the analyst's responsibility.
- **PyTorch Geometric.** The GNN uses `index_add_` scatter to avoid the dependency. Swapping in PyG is a local change if the mesh grows.
- **Great Expectations gates.** `data/ingestion.py` has the gate's shape — `QCCheck` protocol, `run_qc_gate()`, pass/warn/fail severities — but the default checks (`ChecksumCheck`, `NonEmptyCheck`) are structural, not the distributional rules GE/Pandera would add. Swapping in real checks is additive against the existing contract.

---

## 6. Suggested sequence

1. ~~HURDAT2 + ATCF ingestion → real `Track` objects. Run `recalibrate_from_pairs`.~~ Parsers done (`data.hurdat2`, `data.atcf`); `recalibrate_from_pairs` demonstrated on real-format parsed pairs. Not yet pointed at a real downloaded archive.
2. ~~GRIB2 readers for GDAS → real `GriddedFields`.~~ Readers done (`data.real_gridded`, ERA5 via Zarr + GDAS via byte-range GRIB2). Verify dual-flavor parity holds on real data -- not yet done, since neither is wired as the default source yet.
3. Season replay harness against the `AvailabilityOracle` protocol. Validate the timing layer on real arrival times.
4. ~~Wire load shedding through to the ensemble generator.~~ Done — see §2 above.
5. Stage A pretrain on ERA5. Measure whether the transformer's capacity is justified before scaling up.
6. Stage B fine-tune. Stand up the skew audit immediately — it is meaningless without both flavors running.
7. Backtest with rank histograms and spread-skill per lead. Decide on `extra_conditioning_dim` from that evidence.
8. Re-baseline Appendix B against the current NHC verification report.

---

## 7. Autonomous retraining orchestration — calendar/data-volume/drift/skew/latent-desync detected; only calendar/data-volume auto-dispatch

`training.triggers.evaluate_all` (§5.5) has been real and well-tested since #22, but nothing outside tests ever called it — confirmed by grep, zero real callers in `src/` before `anemoi retrain-check` existed. **Done:** `anemoi retrain-check` gathers real signals (calendar, a real HURDAT2 data-volume count, a best-effort live-storm/drift query against a running API) and dispatches the real `train-schedule` machinery when `scheduled_monthly`/`preseason`/`data_volume` fires — the one entry point meant to run unattended (a cron/systemd timer, a GCP instance-schedule startup script), not watched by a human. See [Retraining Triggers](Retraining-Triggers).

**Drift and skew are real now (2026-09-22/23, closing #148), and detection was the actual blocker, not dispatch policy.** `api.real_state.RealState.drift_report`/`skew_report` were the honest stubs this section used to describe; both are real end to end now (see [Monitoring](Monitoring)'s "Production wiring" section, and Decision Log #32/#33). `RealState.pending_retrain_jobs()` (previously a hardcoded `[]`) now genuinely surfaces both, plus a third real signal:

- **Per-model drift alerts** — `drift_report(model).alert` for every model that has contributed to a real cycle this process's lifetime.
- **Champion/latent desync** (§5.7, GitHub #149, closed 2026-09-23) — `tracking.registry.ModelRegistry.desynced_derived_models()` detects, in real time, when fusion/diffusion's recorded `latent_signature` no longer matches the *current* Group 1 champion set. This closes the actual gap #149 documented: `_real_fusion_forecast`'s consistency check (the §5.7 item above) already refused to *serve* a desynced combination, but nothing previously noticed or surfaced *that a desync had happened* — confirmed live three times in one day (2026-09-22), twice caused not by a fresh retrain but by `registry-reconcile` re-staging an already-registered version, a path `pin_set`'s own consistency gate never sees at all. `training.triggers.on_latent_desync`/`Reason.LATENT_DESYNC` shapes it into the same `RetrainJob` contract every other trigger uses.
- **Which model a system-wide skew alert should re-fine-tune remains undefined.** The audit measures "the deterministic stack" collectively; `training.triggers.on_skew(model)` needs one specific model. Nothing in the scope or this codebase resolves that mapping — `pending_retrain_jobs()` deliberately does not guess one (real skew is still visible directly via `GET /v1/monitoring/skew`), the same restraint `anemoi retrain-check` already documented for itself.
- **A deliberate scope decision, not an oversight: none of drift/skew/`LATENT_DESYNC` auto-dispatch a retrain.** `anemoi retrain-check` only ever auto-dispatches `scheduled_monthly`/`preseason`/`data_volume` — all three produce the identical "Group 1 + full derived chain" shape `train-schedule` already runs. The other triggers are *reported*, not dispatched, because none of them fit that shape (`nightly_latent` is diffusion-only; an isolated drift/skew/desync retrain is a single model). Building a real dispatcher for that shape is separate, genuinely future work — surfacing the real signal (this section) was the load-bearing half of "closes the loop automatically," and is done.

"Little human intervention" is honestly true for the calendar/data-volume triggers (auto-dispatched) and now honestly *visible* rather than silently missing for drift/skew/latent-desync (surfaced via `GET /v1/retraining/triggers`, still human-actioned). See [Retraining Triggers](Retraining-Triggers) and the GCP operations note in [Operations Runbook](Operations-Runbook).

### A real, previously-unenforced §5.7 gap: latent-signature consistency at inference time — done

`tracking.registry` has recorded a real `latent_signature` per derived model since #22, but nothing in the real inference path (`training.real_inference_cycle._real_fusion_forecast`) ever checked it before a version's Group 1 checkpoints were actually loaded and combined. Confirmed live: the deployed registry's fusion recorded `latent_signature="lstmv7-cnnv6-transformerv5-gnnv5-pinnv5"` with zero code anywhere verifying the Group 1 versions currently in `production`/`staging` still matched that set. `_real_fusion_forecast` now refuses (degrades to the honest non-learned consensus, the same fallback every other real fusion gap already uses) whenever they don't.

### A real registry bug found live: staging never actually beat the best candidate — done

`real_orchestrator.py`/`cli.cmd_train` compared each new candidate against `versions(name)[-1]` (whichever version was registered last) instead of `registry.champion(name)` (production, else staging — what real inference actually uses). Confirmed live: lstm's staging pick was a version with `track_error_48h_nm=300.5`, worse than two older, unstaged versions (274.3 and 274.6) that had simply never been compared against each other directly. Both call sites now use `ModelRegistry.champion`; `anemoi registry-reconcile` is the real, safe (no training, no GPU) remediation for versions already mis-staged by the old comparison. `ModelRegistry.transition` also gained the staging-incumbent archiving its own docstring always promised but never did for anything but production.

---

## 8. Considered and declined: Cloudflare Workers AI / ONNX for real inference

Investigated 2026-09-22 in response to a real question about whether the deployed Container-based inference path (the one this whole doc's own §1/§2 work productionised) could move to Cloudflare Workers, motivated by a real, recurring pain point this session: the Container is a long-lived singleton that does not restart on redeploy, so verifying a deploy took effect means waiting out a real 45–90s+ cold start every time. Workers don't have that problem.

**Decision: not worth it, at least not now.** Two real findings closed this quickly:

1. **Cloudflare's actual "Workers AI" product (the `env.AI` binding) doesn't support custom models without going through Cloudflare's own "Custom Requirements" enterprise process** — it's a curated catalog (Llama, Whisper, embeddings) running on Cloudflare's own GPU fleet, not a self-serve custom-ONNX runtime. The real, self-serve alternative is bundling `onnxruntime-web`'s WASM execution provider directly inside a plain Worker — meaningfully different from what "Workers AI" usually implies, CPU-only, and subject to real Worker bundle-size/CPU-time limits.
2. **Even under that alternative, only the raw neural-net forward pass would ever move.** Real feature engineering, standardisation, scheduling, registry/promotion, and storm ingestion (`inference.cycle`, `data.availability`, `tracking.registry`, `data.live_atcf`, all real, substantial, already-tested Python) would stay exactly where they are — this was never going to replace the Container, only add a second, parallel path for part of the pipeline, for a narrower benefit (faster cold start, edge distribution) than it first sounded like.

Reading the real seven architectures in `anemoi.models` for ONNX/WASM-specific risk (not just "does PyTorch's ONNX exporter accept it," but "does `onnxruntime-web`'s more restrictive WASM backend actually run it") also surfaced three real, specific blockers that would need solving before a full port was even possible, independent of the cost/benefit call above:

- **GNN** uses `index_add_` scatter-add over a dynamically-sized real mesh (node/edge counts vary per cached-field grid) — scatter-reduce plus dynamic shapes are exactly the combination WASM ONNX runtimes support least reliably.
- **PINN**'s real candidate-generator LSTM is never persisted at all (retrained fresh every training run — `training.real_run_pinn`'s own docstring) — there is no real checkpoint to export for that half of its inference pipeline until that's fixed separately.
- **Diffusion**'s real product is `TrajectoryDenoiser.sample()`, a 200-step ancestral-sampling loop with per-step RNG and data dependencies between steps. ONNX only captures a single `forward()` call (one denoising step); the loop itself would need a real reimplementation in JS, called sequentially thousands of times per cycle even under load shedding.

LSTM, CNN, and Fusion are all real, low-risk exports (standard ops throughout) if this is ever revisited — Transformer is moderate risk (exportable, needs a real numerical check). If the *actual* motivating problem (Container cold-start latency on redeploy) becomes acute enough to revisit, that's a real, separate, much smaller question worth asking on its own terms, rather than reaching for a full inference-runtime migration to solve it.

---

Related: [References](References) · [Decision Log](Decision-Log) · [Configuration Reference](Configuration-Reference) · [Getting Started](Getting-Started) · [Retraining Triggers](Retraining-Triggers)
