# Decision Log

What changed between scope v2 and v2.1, and what changed again during implementation. Each entry names the defect, the fix, and where the fix is enforced.

---

## v2 → v2.1

### 1. Train/serve skew (§4.6) — *major*

**Defect.** Models trained on ERA5 reanalysis and final HURDAT2, served on GFS analyses and real-time ATCF. Permanent distribution shift presented as a fallback.

**Fix.** Two-stage curriculum: ERA5 pretrains, GDAS fine-tunes and serves. Roles on every source. Promotion evaluated on Stage B only.

**Enforced by** `sources.assert_not_operational`, `curriculum.assert_deployable`, `registry.register`, `promotion.evaluate_promotion`.

### 2. Best-track leakage (§4.1, §4.6.2) — *major*

**Defect.** HURDAT2 is post-season reanalysed and smoothed; models fed operational ATCF would degrade against it.

**Fix.** Working and final treated as distinct products. Working is a model input; final is labels only. A noise emulator reconstructs working-quality inputs for historical Stage B.

**Enforced by** `besttrack.assert_input_safe`, `TrackQuality`, `StageSpec.__post_init__`.

### 3. Test-set contamination (§5.3, §8.1) — *major*

**Defect.** §5.3 Stage 6 promoted on **test** metrics; §8.1 re-validated on test storms pre-season. Repeated selection against a held-out set destroys the unbiasedness it was reserved for.

**Fix.** Promotion decided on validation. The test set is metered by an explicit budget requiring written justification.

**Enforced by** `promotion.evaluate_promotion`, `promotion.TestSetBudget`.

### 4. Fragile latent coupling (§5.5, §5.7) — *major*

**Defect.** The drift trigger said "retrain affected model only," silently invalidating diffusion and fusion, which train on Group 1 latents. Nothing errors — the ensemble just gets worse in an unattributable way.

**Fix.** Latent signatures on the Group 1 set. Derived models record what they trained against. Pinning refuses an incoherent set; triggers cascade automatically.

**Enforced by** `registry.latent_signature`, `registry.pin_set`, `triggers.expand_jobs`.

### 5. Infeasible cycle timing (§6.2) — *major*

**Defect.** "00:45 Anemoi-Core ready" assumed same-cycle GFS. GFS 0.25° publishes ~3.5–4 h after cycle time. Not tight — impossible.

**Fix.** Cycle `t` consumes the `t−6` cycle. Cycle gated on TC-Vitals arrival. Delivery targeted ahead of the t+3:00 advisory, which is the operative deadline.

**Enforced by** `time_utils.select_nwp_cycle`, `data.availability`, `inference.scheduler`.

### 6. Retention contradicted the training plan (§4.1, §9.2) — *moderate*

**Defect.** 1-year GOES and 2-year GFS retention against 1980–2025 splits. Also GOES-16/17 named, outdated for 2026.

**Fix.** Raw imagery stays rolling for cost; storm-relative crops retained permanently. GOES-18/19 operational, older satellites in the archive.

### 7. Split criteria contradicted themselves (§4.4) — *moderate*

**Defect.** "Storm-wise, not time-wise" while defining splits by year ranges.

**Fix.** It is in fact both, and both properties are worth keeping. `assert_no_leakage` asserts storm-wise disjointness **and** chronological ordering.

### 8. Pipeline-order omissions (§5.1, §6.1, §3.6) — *moderate*

**Defects.** Fusion missing from the sequential order. PINN missing from the inference flow. PINN's "Input" listed governing equations — they are loss constraints.

**Fix.** Fusion added to both orders; PINN placed as the corrector before fusion output; `physics_residuals()` separated from the forward pass, with the corrector zero-initialised so it starts as the identity.

### 9. Version mismatch — *minor*

Filename said v2, header said v1.1. Now consistent at v2.1.

### 10. Absolute targets may trail the baseline (Appendix B) — *flagged, not fixed*

v2's `<75 nm @ 48 h` may already be behind current NHC official performance (~55–65 nm). Flagged for re-baselining; **beat-rate metrics remain the primary criteria** because they measure against a live baseline.

---

## Raised in review, still open

These were not defects with a clean fix. They are risks worth tracking. See [Roadmap](Roadmap).

- **Sample size.** ~10–15k synoptic fixes total is thin for a 6-layer transformer and a diffusion model.
- **Ensemble underdispersion.** Anemoi-Spread conditioned on Anemoi-Core latents will tend to underdisperse at recurvature, where the distribution is bimodal.
- **Mid-storm model churn.** Addressed for the nightly refresh; the general principle (pin during storms) is worth extending.
- **HPA scales pods, not nodes.** Autoscaling a training job on a fixed-size cluster accomplishes nothing.

---

## Found during implementation

Both are places where the arithmetic did not agree with the v2.1 text.

### 11. The vitals timeout is ~10 minutes too generous

**Defect.** §6.2.2 wrote the timeout as a flat `t+1:30`. With the reduced-ensemble profile's 70-minute worst case and a 30-minute advisory margin, a cycle starting at t+1:30 finishes at t+2:40 — a **20**-minute margin.

**Fix.** Derive it: `advisory_offset − reduced_worst_case − margin` = 3:00 − 1:10 − 0:30 = **t+1:20**. Deriving rather than asserting keeps the three numbers consistent when any one is retuned; change a stage budget and the timeout follows.

Also added the reduced-ensemble **load-shedding** profile so a late fix sheds members rather than missing the advisory.

**Enforced by** `scheduler.derive_vitals_timeout`, `test_vitals_timeout_is_derived_not_asserted`.

### 12. `spread_skill` cannot gate a cone at forecast time

**Defect.** The natural implementation of "only draw an ensemble cone if the spread is calibrated" calls `spread_skill`. But calibration requires an observation, and at forecast time there is none. `spread_skill` is a **post-hoc verification tool only**.

**Fix.** `build_cone` uses a real-time proxy: ensemble radius at the longest lead versus the climatological radius. Below 50% of climatology it falls back to climatological radii and records why in the notes.

An ensemble dramatically tighter than climatology five days out is displaying the underdispersion signature of a diffusion model over-anchored to its conditioning — and that is exactly when under-drawing the cone matters most.

### 14. The Appendix B absolute targets are further off than v2.1 admits

**Defect.** v2.1's Appendix B note said recent NHC 48 h track errors of "~55–65 nm" suggest the absolute targets "may trail" the baseline. The verification record is harsher: NHC official 48 h Atlantic track error was **45.4 n mi in 2024** (a record) and **53.4 n mi in 2025**, with NOAA's own GPRA target for 2026 at 51.0 n mi.

Against a 45–55 nm baseline, a production threshold of 90 nm would admit a system roughly twice as bad as the incumbent.

**Status: flagged, not fixed.** The beat-rate gate is what prevents that admission, which is why it is the primary criterion. The absolute thresholds should be re-derived from the verification database rather than adjusted by intuition. Two related points belong in the verification layer: the baseline has moved ~75% over twenty years, so a fixed threshold is meaningless across a multi-decade backtest; and NHC normalises by season difficulty using CLIPER5, which beat rate alone does not capture. See [References](References).

### 13. Flag inflation from opportunistic feeds — *minor*

**Defect.** Treating dropsonde and microwave as "optional" meant every cycle without aircraft recon shipped marked degraded, which destroys the flag's information content.

**Fix.** A third tier. `InputStatus.opportunistic` separates "normally missing" from "unexpectedly missing"; only the latter flags.

---

## Found live in the deployed registry (2026-09-22)

Four related defects, found investigating why the deployed lstm's staging pick was worse than two older, unstaged versions — the underlying cause of all four is the same: staging was never actually being protected against regression.

### 15. Promotion compared against the wrong incumbent (§5.3, §5.7) — *major*

**Defect.** `real_orchestrator.py`/`cli.cmd_train` computed a candidate's promotion incumbent as `registry.versions(name)[-1]` — whichever version was registered *last*, regardless of stage. A candidate only ever had to beat its immediate predecessor, not the version real inference was actually using. Confirmed live: lstm's staging pick (`track_error_48h_nm=300.5`) was worse than two older, never-staged versions (274.3, 274.6) that had simply never been compared against each other.

**Fix.** `ModelRegistry.champion(name)` — production, else staging, else `None` — the same lookup `real_inference_cycle.py` already used to pick which checkpoint to serve. Both call sites now compare against it instead of `versions(...)[-1]`.

**Enforced by** `ModelRegistry.champion`, `test_registry.py`'s champion tests, `test_real_orchestrator.py::test_incumbent_is_the_champion_not_the_most_recently_registered_version`.

### 16. `transition` never archived a staging incumbent (§5.3) — *moderate*

**Defect.** `ModelRegistry.transition`'s own docstring always promised "archiving any incumbent in that stage," but the code only ever did it for `Stage.PRODUCTION`. Two versions promoted to staging in sequence could both end up marked `staging` simultaneously — the on-disk state was inconsistent even though `in_stage`'s `reversed()` search papered over it by always returning the newest match.

**Fix.** Generalised the archiving check to `Stage.PRODUCTION` and `Stage.STAGING` alike.

**Enforced by** `test_promoting_a_new_staging_version_archives_the_incumbent`.

### 17. Fusion never checked whether its latent signature still matched what was being served (§5.7) — *major*

**Defect.** `tracking.registry` has recorded a real `latent_signature` per derived model since #22 (decision #4 above), but `real_inference_cycle._real_fusion_forecast` never checked it — `production`/`in_stage` were looked up independently per model, with zero cross-model consistency check before combining their outputs through a learned `ConsensusFusion`. A Group 1 model's staging pick changing (including via #15's own fix, or #18's remediation below) could silently desync it from what fusion was actually trained on, with nothing erroring or even flagging it.

**Fix.** `_real_fusion_forecast` now computes the real signature of the Group 1 versions actually in use and refuses (degrades to the honest non-learned consensus, the same fallback already used for "fewer than five real") whenever it doesn't match the champion fusion version's own recorded `latent_signature`.

**Enforced by** `test_real_fusion_forecast_refuses_a_stale_latent_signature`.

### 18. Remediation: `anemoi registry-reconcile` — *operational*

A real, safe (no training, no GPU — `registry.transition` is the only state it touches) command that re-evaluates staging for every model's already-registered versions against the corrected comparison, for versions mis-staged by #15 before the fix landed. Skips any model with a production version (§5.3's manual gate stays manual). Excludes non-finite (`NaN`) metrics from consideration — found while building this tool: several models' early real runs (v1, sometimes v2/v3) had a `NaN` `track_error_48h_nm`, and Python's `min()` over values including `NaN` is unreliable (`NaN` never compares less than anything). Warns when re-staging a Group 1 model desyncs a derived model's `latent_signature` — see #17.

Applied live 2026-09-22: lstm v1 (274.3), cnn v5 (248.3), gnn v4 (284.7), and pinn v3 (298.1) replaced worse, more-recently-registered staging picks; transformer/diffusion/fusion were already correctly staged.

### 19. Applying #18 live surfaced one more real gap: registry routes never refreshed — *moderate*

**Defect.** `RealState._refresh_registry` (renamed `refresh_registry_if_stale`, now public) was only ever called from `run_cycle`. `/v1/registry`, `/v1/registry/{model}`, and `/v1/registry/pins/active` read `state.registry` directly with no refresh at all — found applying #18 live: the real `registry-reconcile` write landed in R2 immediately (confirmed via a fresh `anemoi registry-pull`), but the deployed API's warm in-memory copy kept serving the old, worse staging picks (`/v1/registry/lstm` still showed v7 staging) until an unrelated `run_cycle` call happened to both occur and find the 15-minute TTL already expired.

**Fix.** `refresh_registry_if_stale` called at the top of all three registry routes now, same TTL-gated best-effort semantics `run_cycle` already had. `DemoState` gained a real no-op of the same name (nothing external ever writes to the demo registry, so there is nothing to refresh) rather than a per-caller `hasattr` check, matching the "exact same public surface" contract every other real/demo state method already keeps.

**Enforced by** `test_registry_route_refreshes_a_stale_registry`.

### 20. The same class of gap, one layer up: the console never refreshed either — *moderate*

**Defect.** `console/src/routes/+page.svelte` (storms + today's schedule) and the storm detail page both fetched their real data exactly once, in `onMount`, with no refresh at all — found responding to a real question ("does this properly update?") about the homepage's cycle-schedule section. `getSchedule`'s own `plan_day` is a pure function of the date (confirmed against its real implementation, no wall-clock dependency once a date is picked), so the actual bug wasn't the schedule *content* going stale — it was `today` itself only ever being computed once at mount. A tab left open past 00:00 UTC would keep showing the previous day's plan under a "Today's cycle schedule" header. The storm detail page had the same one-shot pattern for `storm`/`cycle`/`skew` — the page someone watching a live storm would leave open the longest.

**Fix.** Both pages now poll every 60s, re-deriving `today` fresh each time rather than caching it. The storm detail page's poll skips itself entirely while a cycle run (`running`) is in flight, so a poll can never land mid-run and clobber the result `handleRunCycle` just produced; it also never touches `cycleInput`/`members`/`coastlineLat`/`coastlineLon`, so an in-progress form edit is never overwritten by a background refresh.

**Enforced by** `e2e/periodic-refresh.spec.ts`, using Playwright's virtual clock (`page.clock`) to prove a real second fetch fires without the test waiting 60 real seconds.

### 21. The footer's own version was hardcoded and never moved — *minor*

**Defect.** The sidebar/mobile-drawer footer said "Scope v2.1 · Reference implementation" as a plain string literal — found asking why it didn't change when the package moved to v2.2.0. It couldn't have: nothing in the UI ever read `/v1/health`'s real `anemoi_version` field at all (defined in `api/types.ts`, never consumed anywhere). Two genuinely separate facts were being conflated: "Scope v2.1" names the external spec this implementation targets, which this session's own amendment didn't change (recorded as Decision-Log deviations *within* v2.1, not a new scope version — see #15-20) — that part of the string is correctly still v2.1, not stale. The package version is the part that was actually wrong to hardcode.

**Fix.** `+layout.svelte` fetches `/v1/health` once and appends the real `anemoi_version` ("Scope v2.1 · Reference implementation · v2.2.0"), passed down to `MobileNav`'s own copy of the same footer rather than fetched twice. Self-correcting for every future version bump — nothing to remember to update by hand next time.

### 22. #20's own fix introduced a real regression: the map reset itself mid-interaction — *moderate*

**Defect.** `ConeMap.svelte`'s `fitBounds` effect guarded against re-fitting by comparing `JSON.stringify(bounds)` against the last value it fitted — correct for the infinite-loop bug it was built to close (§ Decision Log's earlier ConeMap entry), but it only skips re-fitting when the bounds *value* is byte-identical. #20's periodic-refresh fix made that a real problem: a live storm's real `history`/`latest_fix` genuinely shifts a little between some 60s polls, which changes `bounds`'s real value even though the user is still looking at the exact same cycle — so the map silently recentered/rezoomed on its own, discarding the user's pan/zoom, roughly every 60 seconds. Reported live against `EP172026`, an active storm, described as "after every so often, or during scroll or map touch" — the poll firing mid-interaction isn't caused by the interaction, it just happens to land then, which is what made it read as the touch itself triggering a reset.

**Fix.** The guard now keys on `CyclePayload.cycle` (a new `cycleLabel` prop) instead of the bounds value — the map re-fits exactly once per cycle the user actually loaded (first view, running a new one, clicking a past-cycle button), and never again while a background poll quietly refreshes the same cycle's storm history underneath them. Still closes the original infinite-loop bug: `cycleLabel` doesn't change across the camera-sync feedback's repeated re-invocations of this effect either, so every re-schedule after the first is still a no-op.

**Enforced by** `cone-map.spec.ts`'s new pan/zoom-preservation test — confirmed to actually catch the regression (not just pass vacuously) by re-running it against the pre-fix code and watching it fail on a real, if small (1px), camera shift before restoring the fix.

### 23. `registry-reconcile`'s candidacy was metrics-only, and staged three unloadable checkpoints live — *major*

**Defect.** #18's `registry-reconcile` compared candidates purely on `track_error_48h_nm`, with no check that a candidate was actually servable. `#78` introduced the `arch_params` tag every real checkpoint needs so `training.real_inference.load_trained_model` can reconstruct its architecture — every version registered before #78 lacks it and can never be loaded, regardless of how good its metric looks on paper. Found live, queuing a diffusion/fusion retrain and then running a real cycle to confirm fusion would actually be used afterward: `lstm v1`, `cnn v5`, and `gnn v4` — all pre-#78, all staged by #18's own reconcile run — produced `InferenceLoadError` on every real cycle. Only `transformer`/`pinn` could serve at all; `fusion` (needs all five Group 1 models) never engaged.

**Fix.** Candidacy in `anemoi registry-reconcile` now also requires a real `arch_params` tag and `checkpoint_uri` — actually loadable, not just well-scored. Re-run live afterward: `lstm` → v8, `cnn` → v7, `gnn` → v5 (the best *loadable* version of each), restoring real 5-model Group 1 serving.

**Enforced by** `test_registry_reconcile_skips_an_unloadable_version_even_with_better_metrics`.

### 24. Storm names were parsed and then discarded — *enhancement*

Both real sources carry a storm's public name — HURDAT2's header line (`AL092020, LAURA, ...`) and NHC's `CurrentStorms.json` (`{"id": "AL062026", "name": "Fay"}`) — but `Track` had no field for it, so every route downstream only ever exposed `storm_id`. Added `Track.name: str | None`, threaded through `data.hurdat2`'s header parsing (HURDAT2's own `UNNAMED` sentinel becomes `None`, not the literal string) and `data.live_atcf.fetch_current_storms` (TC-Vitals bulletins carry no name, so it's captured from `CurrentStorms.json` and passed in separately), into `StormSummary.name` and the console's storm card / detail header. `None` for an unnamed archive storm or a fully synthetic demo storm — never a fabricated name.

### 25. `torch.load` without `weights_only` — *security*

`training.real_inference._download_state_dict`'s `torch.load` defaulted to `weights_only=False`, which deserializes via pickle and can execute arbitrary code from a malicious checkpoint. Flagged by a security scanner. Every real save site in this codebase (`real_run.py`/`real_run_cnn.py`/`real_run_transformer.py`/`real_run_gnn.py`/`real_run_pinn.py`/`real_run_diffusion.py`/`real_run_fusion.py`) only ever writes `torch.save(model.state_dict(), ...)` — a plain tensor dict — so `weights_only=True` is a pure hardening with no functional change. Verified against all 14 `test_real_inference.py` tests (a real `load_trained_model` round-trip for all 7 architectures) unchanged.

### 26. numpy's declared floor was stale, not the resolved version — *security, false positive*

A scanner flagged numpy for 3 vulnerabilities, recommending 2.5.3. Investigated rather than assumed: GitHub's numpy security advisories are empty, Snyk's vulnerability DB shows zero issues across 2.4.2-2.5.3, and `uv.lock` already resolved to numpy's newest installable release per Python version (2.4.6 for <3.12, 2.5.3 for >=3.12 -- 2.5.3 itself requires Python>=3.12, which this project's `>=3.11` floor can't universally satisfy). The real gap: `pyproject.toml` declared `numpy>=1.26`, a 2023-era floor a manifest-only scanner would read instead of the resolved lock. Raised to `numpy>=2.4.6` -- the real minimum across the whole supported Python range. The resolved lock was never vulnerable; only the declared constraint was stale.

### 27. `registry-reconcile`'s loadability fix, applied live, re-desynced fusion a third time in one day — *major, structural gap identified*

Applying #23's fix live (`lstm`→v8, `cnn`→v7, `gnn`→v5, all now loadable, closing GitHub #100) desynced `fusion` v5's `latent_signature` yet again -- the same class of event as #17/#23, now confirmed a third time in a single day. Root cause is structural, not a bug in any one fix: `training.real_latents` requires all 5 Group 1 models trained in the *same* session before fusion/diffusion can build at all, but each model's champion is independently metric-driven with no guarantee a fresh joint retrain's versions become every model's new champion -- so even the retrain queued specifically to fix a desync (#22's remediation) didn't fully fix it, and the very next correction (#23) desynced it again. Tracked as GitHub #149 rather than fixed ad hoc again -- needs a real design decision (pin fusion's dependency set independent of current champions vs. auto-triggering a retrain on any Group 1 champion change vs. accepting degradation as the norm), not another one-off re-stage.

### 28. Storm-detail Verification card silently rendered zeros -- the underlying feature was never built — *moderate*

**Defect.** `RealState.skew_report()`/`drift_report()` (`api/real_state.py`) are honest hardcoded stubs in production -- always `n=0`/all-zero, `skew_report` at least carrying a real `reasons` string ("not yet available for real-ingested storms, needs a real paired ERA5T dataset, not yet built"). The request succeeds (real 200), so the storm-detail page's "Verification" card always rendered -- just four meaningless zeros under a "nominal" badge, since (unlike `/monitoring`, which already rendered `reasons`) this copy of the panel never surfaced that explanation. Reported live as "nothing populates."

**Fix.** Storm-detail's Verification card now renders `skew.reasons`, matching `/monitoring`'s existing pattern.

**Enforced by** a new `landfall-and-verification.spec.ts` test faking the real stub response via `page.route` (the demo backend's synthetic skew never reliably has a non-empty `reasons` array to rely on for a deterministic test).

**Note.** This only fixes the console's honesty about the gap -- the real skew/drift audit itself is unbuilt, tracked as GitHub #148. Also surfaced two other real, previously-untracked gaps during the same review: GOES satellite ingestion is synthetic-only (GitHub #146) and five more registered data sources (`ndbc`/`dropsonde`/`microwave`/`sst_ohc`/`ensemble_perturbations`) have no real fetch implementation at all, only availability-simulation stand-ins (GitHub #147).

### 29. Real SSMIS microwave fetch/decode -- first of #147's five sources closed — *enhancement*

`data.real_microwave` implements real RSS SSMIS (DMSP F16/F17/F18) fetch and decode -- the first of #147's five unimplemented sources to close, prompted by the user registering a real RSS account and asking to verify FTP login before building anything.

**Two products exist at RSS; only one was implemented, deliberately.** `/TC-winds` (storm-specific ATCF-fix-format-derived records) was investigated first -- confirmed live against `EP172026`'s real position -- but RSS doesn't publish the exact wind-radii column semantics anywhere findable, and this codebase's standing rule against guessing at field meanings (real risk: mislabelling real data as something it isn't) ruled it out for now. `/ssmi/{sat}/bmaps_v08/` -- a fully-specified binary bytemap -- was implemented instead, verified two independent ways (RSS's own reference Python reader, fetched directly from their FTP support directory, and their public documentation) before any parsing code was written; both agreed exactly.

**Correctness verified beyond "didn't crash":** decoded real 2026-09-21 data end to end (physically sane value ranges for all five variables), then checked real coverage density by latitude band -- 11-17% in the tropics vs ~29% at -60°/-30°, matching expected single-polar-orbiter swath geometry. A real zero-coverage box directly over `EP172026` turned out to be a genuine same-day gap in that satellite's tropical coverage that day, not a decode bug -- worth recording since it's the kind of result that looks like a bug until checked.

**Deliberately fetch + decode only** -- no storm-relative crop contract the way `data.satellite` has for GOES, since no model architecture currently consumes this shape yet.

**Two stale things corrected along the way:** `sources.py`'s `microwave` entry claimed HDF5 (real format is a gzip'd raw uint8 bytemap); `real_gridded.py`'s SST placeholder comment still named RTG_SST (see #26's numpy entry for the "stale reference, not a resolved-state defect" pattern -- same class of issue, different source, second occurrence in one day).

**Enforced by** `tests/test_real_microwave.py` -- 11 unit tests (byte-layout decode, all 5 real flag codes, grid convention, error handling) plus 1 real network test against the live FTP endpoint (opt-in, needs real credentials).

### 30. #147 closed -- the remaining four sources, and OHC declined a second way — *enhancement*

`data.real_ndbc`, `data.real_sst`, `data.real_ensemble`, `data.real_dropsonde` close out the rest of #147, same session as #29. Each verified live before any parsing code was written, same standard as microwave:

- **NDBC**: header-driven parsing (reads the real header row rather than hardcoding column positions) after confirming live that a C-MAN land station's real column set can omit wave-sensor fields a moored buoy has.
- **SST**: NCEI OISST v2.1, a small (~1.5 MB/day) real NetCDF fetch -- needed a real NetCDF reader the `gridded` extra never had; added `h5netcdf`/`h5py` (pure-Python wheels, no compiled system library, unlike `eccodes`).
- **GEFS ensemble**: reused `real_gridded`'s `GDAS_LEVEL_MESSAGES`/`_parse_grib2_index` directly rather than duplicating, after confirming live that GEFS's `.idx` sidecar carries the exact same messages in the identical format GDAS already reads.
- **Dropsonde**: real WMO BUFR via `eccodes`, no proprietary format to reverse-engineer (unlike RSS's TC-winds in #29). Hit and fixed a real bug along the way: `eccodes.codes_new_from_message` (works for GRIB2 bytes, already used for GEFS) turned out to be GRIB-specific under the hood and can't read BUFR directly from bytes -- needs `codes_bufr_new_from_file` with a real file descriptor instead, same tempfile pattern GDAS's own decode already uses.

**OHC declined a second time, more thoroughly.** #4/#26's placeholder note pointed at "an ocean reanalysis, e.g. GODAS/ORAS5" as the real path; this pass additionally checked NOAA OSPO's ERDDAP `UOHC_2026`/`TCHP` products specifically, since they looked like a plausible live alternative (real 200, real schema, units matching the existing placeholder constant's naming exactly). They aren't: querying the actual data showed it stops at 2026-01-26, ~8 months stale as of this writing -- confirmed via a real query, not assumed from documentation looking current. Recorded so a future pass doesn't re-discover this the hard way; GODAS/ORAS5's exact access point still wasn't found in the time spent.

**Also corrects two more stale registry entries** (same pattern as #29's HDF5/RTG_SST fixes): `ndbc`'s format was claimed as JSON/NetCDF (real format is whitespace-separated text) with an unverified "rolling 3yr" retention (real is 45 days in the product actually fetched); `ensemble_perturbations`'s retention was claimed as "rolling 1yr" (real GEFS archive on `noaa-gefs-pds` goes back to 2017-01-01, verified via direct S3 listing).

None of the five sources from #147 are wired into a real model input contract -- fetch/decode only throughout, since nothing currently consumes any of these shapes. That's real, separate future work.

**Enforced by** `test_real_ndbc.py` (7 tests + 1 network), `test_real_sst.py` (3 tests + 1 network), `test_real_ensemble.py` (4 tests + 2 network), `test_real_dropsonde.py` (6 tests + 2 network) -- all network tests run locally against the real live endpoints during this pass, not just left to CI's default skip.

### 31. Real GOES-18/19 satellite ingestion -- #146 closed, the last unimplemented registered source — *enhancement*

`data.real_goes` implements the sixth and last unimplemented source, closing [GitHub #146](https://github.com/jasonkolodziej/anemoi/issues/146). Unlike #29/#30's five sources (fetch/decode only, nothing consumes the shape yet), this one is wired all the way to its real consumer: `models.cnn.build_cnn` already expects `data.satellite.SatelliteCrop`'s exact 5-channel shape, so this fills that shape with real data rather than inventing a new contract.

**Five real NOAA products, one per CNN channel** -- `ABI-L2-CMIPF` (channels 14/9/2 for IR/WV/VIS), `ABI-L2-SSTF` for SST, `ABI-L2-RRQPEF` for rain rate. Each verified live (real file, real variable name, real units) before writing any fetch code, same standard as every #147 source.

**Two real engineering problems solved, not just "fetch a file":**

1. **Full-object download isn't viable.** A real full-disk channel-2 file is ~430 MB -- too large to fetch per crop per cycle. Resolved a previously-open question on this page ("GOES imagery has no byte-range `.idx` trick"): confirmed live that lazy reads via `fsspec`'s HTTP filesystem + `h5netcdf`'s chunked HDF5 access transfer only ~8 MB for a real 64x64 storm-relative crop, not the full object.
2. **GOES imagery isn't on a lat/lon grid.** It's the ABI Fixed Grid, a geostationary projection (scan angles in radians from the sub-satellite point). Added `pyproj` -- deliberately not hand-rolled trigonometry, since a projection bug there would silently misplace every crop rather than raise anything loud. Verified against a real active storm's real position (`AL062026` "Fay") before trusting it for anything: the projected pixel index landed on 100% real, non-missing data in the physically sane range.

**Real `DQF` (data quality flag) is honoured.** Confirmed this matters in practice: a real SST crop near an active storm came back entirely `DQF=2` (out-of-range, 4095/4096 pixels) -- a real, physically plausible cloud-cover gap (SST retrieval needs clear sky), not a decode bug. Cross-checked the real DQF values directly rather than assuming a code path was broken.

**Satisfies all four of #146's acceptance criteria**, including the dual-source parity check against `data.satellite`'s synthetic-generator ranges, verified with a real network test rather than asserted without running it.

**Enforced by** `tests/test_real_goes.py` -- 8 unit tests (including a projection-correctness test: the real sub-satellite point must project to the exact centre of a constructed grid carrying the real projection attributes) plus 3 real network tests against the live NOAA archive.

### 32. Real drift detection for RealState -- #148's drift half closed — *enhancement*

`RealState.drift_report()` was a hardcoded stub (always `n_live=0`) since #78/#85 -- fabricating synthetic numbers the way `DemoState` does for demo purposes would be actively misleading under a real deployment, so it stayed honestly empty rather than fake. Real detection now runs, wiring three previously-disconnected pieces: a real live sample (`compute_environment_features` computed once per real cycle, independent of which Group 1 models contribute -- a new `DeterministicForecast.env_features` field), a real reference distribution (`anemoi drift-reference-fit`, a new CLI command, fits `ReferenceDistribution` from real cached GDAS fields and persists it via the new `monitoring.reference_store` module -- local JSON plus a durable mirror through the same `CheckpointStore` the registry already uses), and `RealState.drift_report(model)` itself, comparing a rolling in-memory window of real live samples against the real reference via the existing, unchanged `detect_feature_drift`.

**Investigated first, not assumed: does #148 depend on real ERA5T ingestion at all?** Confirmed live that `data.real_gridded.open_era5` already reads it -- ARCO-ERA5's own store (the same one already used for final ERA5) carries a real `valid_time_stop_era5t` attribute, confirmed running about 6 days behind real time when checked. That closes #148's stated "Depends On" for the skew half too, even though skew itself isn't wired yet (see below).

**A real bug the tests caught, not inspection.** The first implementation of the lazy reference loader accessed `self._checkpoint_store` -- a property that raises `CheckpointStoreError` when no real S3 credentials are configured -- as a direct argument to `load_reference(...)`. Python evaluates that before the call happens, so any deployment without durable-storage credentials would never even attempt to read a perfectly real *local* reference file: `load_reference` was never reached at all. Fixed to resolve the store separately, degrading to local-only rather than silently skipping the read entirely. Found because a test wrote a real local reference file and then asserted `drift_report` would see it -- it didn't, on the first pass.

**Skew (#148's other half) is not yet wired**, and deliberately not rushed to match drift's pace: it's a materially larger task than "fetch ERA5T" (already solved, see above) -- it means re-running the *entire* deterministic stack against ERA5T-sourced `GriddedFields` for a storm/time an operational cycle already ran days earlier, then pairing the two, which needs a way to look back at what operationally ran and to swap the input source through the existing inference path. Real, separate future work, tracked as the remainder of #148.

**A real gap recorded, not hidden:** the live-sample window is in-memory only, not durably persisted -- it resets on every cold start. A long-lived warm container accumulates real signal over its own lifetime; one that recycles often may rarely reach `detect_feature_drift`'s own 30-sample minimum. Cross-restart persistence of live samples is separate future work.

**Enforced by** `test_reference_store.py` (7 tests, including the durable round-trip and the unreachable-store degradation), `test_cli.py`'s 4 new `drift-reference-fit` tests, `test_real_inference_cycle.py`'s `env_features` coverage, and `test_api_real_state.py`'s 5 new tests exercising `RealState`'s real bookkeeping directly.

---

### 33. Real ERA5T-vs-operational skew audit for RealState -- #148 closed — *enhancement*

`RealState.skew_report()` was the last hardcoded stub in the monitoring surface (always `n=0`, `reasons=("... not yet built",)`). Closing it needed the two real pieces entry #32 named and deliberately deferred: a durable record of what operationally ran (a live process's in-memory `storm.cycles` doesn't survive the audit's own 5-day `AUDIT_DELAY`, let alone a Cloudflare Container cold start), and a way to swap the input source through the *existing* inference path rather than build a second, parallel one that could quietly drift out of sync with production.

**The swap.** `training.real_inference_cycle.build_real_deterministic_fn` and every `training.real_inference_live.build_live_*_x` builder now take an optional `fields_fetcher` override (default `None` -- unchanged real live/operational GDAS path via `_current_fields`). The one real caller that passes something else is the new `monitoring.skew_audit` module: `real_inference_live.era5t_fields`, backed by a new `data.real_gridded.fetch_era5t_one` (reuses the already-open `open_era5`/`era5_to_gridded_fields` ERA5T read entry #32 confirmed live). This re-runs the actual deterministic stack -- CNN/Transformer/GNN/PINN's real forward passes, the real learned fusion layer when all five Group 1 models contribute -- pointed at ERA5T instead of GDAS, not an approximation of it.

**The durable record.** `RealState.run_cycle` now calls `_record_skew_sample` (mirroring `_record_drift_sample`) right after a real, non-synthetic-fallback cycle completes: `monitoring.skew_audit.record_operational_cycle` persists the storm's trailing real fixes and the exact `Fix` the cycle ran against, plus the real fused output, as local JSON with a best-effort durable mirror (same `CheckpointStore` contract as the drift reference, a new `monitoring/skew_operational/{storm_id}/{label}.json` key). A new offline CLI command, `anemoi skew-audit`, is the real entry point: it lists every durably-recorded operational cycle old enough for ERA5T to have caught up with (`monitoring.skew.audit_due`) and not yet audited, replays each through `audit_one` (the swap above), and appends any resulting real `monitoring.skew.SkewSample`s to a durably-persisted corpus (`monitoring/skew_samples.json`) that `RealState.skew_report` reads and feeds to the real, unchanged `SkewMonitor`.

**A real cutoff, not an infinite retry.** A cycle whose ERA5T replay keeps coming back empty (a genuinely stale/missing hour, not just "not due yet") is still marked audited once it's more than twice `AUDIT_DELAY` past its own target time -- otherwise a permanently-unreachable cycle would be re-fetched from durable storage and re-attempted forever. Confirmed by test (`test_audit_run_replays_only_due_records_and_persists_the_result`).

**Enforced by** `test_skew_audit.py` (7 tests: JSON round-trips, the synthetic-fallback no-op, the local+durable persistence round-trip, and the full `audit_run` due-filtering/give-up/no-re-audit wiring), 4 new `test_api_real_state.py` tests exercising `RealState`'s own skew bookkeeping directly, and the unchanged `test_real_inference_cycle.py`/`test_real_inference_live.py` suites (23 tests) confirming the `fields_fetcher` plumbing didn't change any existing GDAS-path behaviour.

---

### 34. Anemoi-branded `/redoc` -- #159 closed — *enhancement*

FastAPI's default `/redoc` route (`fastapi.openapi.docs.get_redoc_html`) has no theming hook at all -- its own docstring says you'd only call it yourself "if you needed to override some parts." It renders the open-source `redoc` npm package via a bare `<redoc spec-url="...">` element, unstyled.

**A real correction to how #159 was scoped, found before writing any code, not after.** The issue's two reference links looked like they described the same mechanism; only one does. Redocly's [customize-styles](https://redocly.com/docs/realm/branding/customize-styles) guide -- a plain `@theme/styles.css` of CSS custom properties -- is for **Redocly Realm**, a separate paid product, confirmed by fetching the page directly rather than assumed from its URL. It has zero effect on the open-source bundle FastAPI actually embeds; declaring a `styles.css` per that guide would have loaded and silently done nothing. The real mechanism, confirmed against `Redocly/redoc`'s own `src/theme.ts` source, is a nested JS object passed to `Redoc.init(specUrl, {theme}, element)`.

**The fix.** `anemoi.api.docs.REDOC_THEME` is that object -- every colour traced to `anemoi.branding` (`STATUS_COLORS`/`FUNCTIONAL_COLORS`, never a `WindGod.color`; `test_theme_never_uses_a_god_color` asserts this structurally, mirroring `test_branding.py`'s own `test_structural_colors_are_never_model_colors`). `main.py` sets `redoc_url=None` on the `FastAPI(...)` constructor and replaces it with a route calling `get_custom_redoc_html`, which calls `Redoc.init` from a `<script>` instead of the declarative element (a nested theme object cannot be serialized into an HTML attribute). A real, small `static/redoc-theme.css` is still declared and served -- the issue's own literal deliverable -- covering what the JS theme object doesn't: the `<body>` background before `redoc.standalone.js` mounts (otherwise a white flash against this app's dark-only palette), and the scrollbar.

**Verified live, not just via the embedded JSON.** Started the API locally, fetched `/redoc` with a real Playwright `chromium` browser (the same tool the console's own e2e suite already depends on), and screenshotted it: dark chrome throughout, cyan GET / blue POST badges, blue active-sidebar highlight matching `--color-action`, zero console errors, no unstyled flash.

**Enforced by** `tests/test_api_docs.py` (7 tests: the custom route replaces the default, the theme JSON is actually embedded in the served HTML, the static CSS serves with the right content-type, the god-colour exclusion, HTTP-method-colour distinctness, and `/docs` staying untouched).

---

### 35. Real champion/latent-desync detection closes #149 — *enhancement*

**The decision, as #149's acceptance criteria required.** Three options were on the table: (1) decouple fusion/diffusion's training set from live Group 1 champions entirely (pin specific checkpoints, not "whatever's currently staged"), (2) auto-trigger a fusion/diffusion retrain whenever a Group 1 champion changes, (3) accept graceful degradation as the permanent steady state and only document it. **Chosen: option 2, scoped to real *detection and surfacing*, not real *auto-dispatch* of a retrain.** Auto-launching unattended GPU training specifically off this trigger is separate future work, deliberately -- `anemoi retrain-check` already draws this exact line for drift/skew (only `scheduled_monthly`/`preseason`/`data_volume` are ever dispatched; its own docstring: "a real dispatcher for [the rest] is separate, scoped future work"), and there was no real reason for a champion desync to get different treatment. Option 1 is architecturally the more complete long-term fix but touches `training.real_latents`'s joint-training requirement -- a real, separate, larger change, not this issue's scope. Option 3 was rejected outright: it would have left the actual reported problem (real desyncs going unnoticed) unfixed, documentation alone doesn't close a visibility gap.

**What was actually missing, confirmed by reading the code before writing any:** `_real_fusion_forecast`'s consistency check (§5.7, the "#17" fix) already refuses to *serve* a desynced combination -- that part worked. `pin_set` already refuses to *pin* a derived model whose recorded `latent_signature` doesn't match its pinned Group 1 set -- that part worked too. But `champion()` -- what a real cycle actually uses -- is looked up independently per model and never goes through `pin_set` at all, so a Group 1 champion changing via `registry-reconcile` re-staging an *already-registered* version (the real, repeated cause #149 documented -- confirmed three times in one day, 2026-09-22) produced a desync neither check ever saw. Nothing computed or compared the live signature outside a real fusion cycle actually running.

**The fix.** `ModelRegistry.desynced_derived_models()` -- a pure, real read of already-loaded registry state (no network, no training-time concept) -- computes the *current* signature from live `champion()` calls and compares it against each derived model's own recorded one. `training.triggers` gained `Reason.LATENT_DESYNC`/`on_latent_desync`/an `evaluate_all(desynced_models=...)` parameter, following the exact same shape `drifted_models`/`skewed_models` already use -- this module stays pure logic over caller-supplied values, not an I/O consumer of the registry. `api.real_state.RealState.pending_retrain_jobs()` -- a hardcoded `[]` since #148 closed drift/skew, the last real stub in the monitoring/retraining surface -- now calls it on every request and feeds real per-model drift alerts plus this new signal into `evaluate_all`. `api.demo_state.DemoState.pending_retrain_jobs()` gained the identical wiring for "same public surface" parity (always empty there by construction -- `_seed_registry` registers derived models with exactly the signature their seeded Group 1 set computes to -- but real, not synthetic, the same restraint this codebase's monitoring section already applies elsewhere).

**Real skew deliberately excluded from the model-specific list here**, the same restraint `cli.cmd_retrain_check`'s own docstring already explains for itself: a real skew alert is system-wide, and nothing in this codebase's scope says which model(s) it should retrigger. Guessing one here would be exactly the kind of fabrication `RealState`'s own monitoring section already refuses to do elsewhere; real skew stays visible directly via `GET /v1/monitoring/skew`.

**A real, pre-existing test flakiness this change surfaced, not caused.** `test_real_state_monitoring_and_retraining_routes_do_not_500` asserted `GET /v1/retraining/triggers == []` unconditionally -- true only because `pending_retrain_jobs()` was a hardcoded stub. `evaluate_all` calls real `datetime.now(UTC)` internally, and `nightly_latent` legitimately fires at 02:00 UTC with no active storms -- caught immediately because the suite happened to run at 02:07 UTC the same day. `DemoState.pending_retrain_jobs()` had this exact same real-time dependency already; nothing before this ever exercised it against a hardcoded-empty expectation. Fixed by loosening that one assertion to shape-only, with the real per-model desync/drift behaviour now covered precisely by dedicated tests using explicit `now` values instead.

**Enforced by** `tests/test_registry.py` (5 new tests: coherent-set/no-op, a real detected desync, incomplete-champion-set honesty, no-derived-model-registered honesty, and that only the *champion* derived version matters, not a stale archived one), `tests/test_triggers.py` (5 new tests: fires without any Group 1 job in the same pass, doesn't cascade further, `evaluate_all` wiring, and a specific reason winning over a generic `CASCADE` placeholder for the same model), and `tests/test_api_real_state.py` (3 new tests: RealState-level detection, and the real HTTP route round-tripping the new `Reason`/`Trigger` enum values end to end).

---

### 36. Real diffusion ensemble collapse found and fixed via #10's own backtest — *bugfix*

**Found by using the tool #10 just built, on real data, immediately.** The first real run of `anemoi spread-backtest` (against the champions #149 had just re-synced) showed the deployed diffusion model (v6) severely underdispersed at *every* lead and quantity -- real spread/skill ratio 0.10-0.19 where calibrated is ~1.0, truth outside every ensemble member in 74-89% of real validation cases, the served cone missing 100% of the cases it used its own spread for. Not the recurvature-specific failure #10 hypothesized -- a global collapse, evidence pointing at the model itself rather than a conditioning gap.

**Root cause, confirmed with a real per-epoch loss curve, not guessed from the architecture alone.** `TrajectoryDenoiser.sample`'s own docstring already recorded a real 2026-09-18 finding (`val_loss ≈ 8x train_loss`) -- this investigation logged the real curve behind that number for the first time: real val loss hit its minimum at epoch 35 of a fixed 200, then rose monotonically to 2.1x that minimum by epoch 199 while train loss kept falling. A real, clean overfitting curve. Three real, pre-existing facts explain why: no dropout or weight decay anywhere in the architecture/training loop, no early stopping, and ~1000 real training samples against a 6-layer, 256-hidden-dim model -- a real recipe for exactly this.

**The fix.** `train_diffusion_stage` now tracks every real epoch's val loss and stops after `patience` (default 20) epochs with no improvement, returning the real best-val-loss checkpoint rather than whichever epoch the fixed budget happened to land on (#167). `run_spread_backtest`/`anemoi spread-backtest` gained a `--diffusion-version` override (#168) -- a real, previously-missing need: `evaluate_promotion` only ever compares a candidate's `track_error_48h_nm` (the ensemble *mean*'s point accuracy) against the incumbent, with zero visibility into calibration, so a real candidate needs a way to be measured on the axis the gate can't see *before* a promotion decision.

**Real retrain, real validation, real promotion -- all three, not just the code.** Retrained (`train-schedule --derived-from-champions`) and backtested both the old and new checkpoint against the exact same real validation data:

| | v6 (overfit) | v7 (early-stopped) |
|---|---|---|
| spread/skill ratio, track, 12-120h | 0.11-0.17 | 0.44-0.94 |
| truth outside every member | 74-87% | 14-46% |
| served cone @120h: ensemble basis used | 52/346 cases | 346/346 cases |
| served cone @120h: miss rate | 100% | 81% (nominal ~33%) |

A real, deliberate trade-off: v7's point metric is 7% worse (295nm vs 276nm), which is why `evaluate_promotion` didn't auto-stage it -- but a collapsed-yet-accurate-on-average ensemble is worse for every real product that depends on spread (cone, intensity PDF, landfall probability) than a slightly-less-accurate, honestly-spread one. Staged manually; confirmed durably persisted via a fresh pull from R2 with no local cache.

**Not fully solved -- v7 is still underdispersed at 72-120h (ratio 0.4-0.7), just not *severely*.** #10's original `extra_conditioning_dim` question is real, live follow-up now, on a healthy baseline instead of a collapsed one. Tracked as the remainder of [GitHub #166](https://github.com/jasonkolodziej/anemoi/issues/166), left open.

**Enforced by** `test_real_run_diffusion.py` (a real overfitting scenario that must stop before the epoch cap; the real invariant that a longer epoch budget never returns a worse val_loss), `test_spread_backtest.py` (3 new tests for the version override: measures the given version, still enforces the real latent-signature check, raises cleanly for an unknown version).

### 36b. 2026-09-23 status update on #166 regularization follow-up — *status*

**Current status.** The original problem was real and is now effectively resolved at the root cause: diffusion was severely underdispersed at every lead, and the sequence of fixes proved the underlying issue was model overfit/regularization rather than a missing conditioning signal. Early stopping recovered most of the gap, but the remaining long-lead underdispersion was closed by the real regularization ablation, with dropout=0.1 emerging as the specific, effective fix.

**What is still open.** The remaining gap is not the original underdispersion bug. Diffusion v8 now calibrates well at the long leads, but it shows a mild short-lead overdispersion in a subset of cells and cross-track cases (spread/skill ratio 1.2-2.3 at 12-48h). That is a real calibration-tuning question, but it is materially different from the original issue and not a blocker for the main calibration fix.

**Current best live model set (staging only).** `lstm v8`, `cnn v7`, `transformer v5`, `gnn v5`, `pinn v6`, `diffusion v8`, and `fusion v8` are all at `staging`; no model is at `production` right now. The active latent signature is `lstmv8-cnnv7-transformerv5-gnnv5-pinnv6`, matching the live Group 1 set exactly.

**The real follow-up options, in order.** 1) re-check `extra_conditioning_dim` now that the baseline is healthy; 2) tune the short-lead overdispersion, likely with a value between 0.05 and 0.1 or a lead-dependent regularization if product impact matters; 3) evaluate `n_augment` for more real training data; 4) add a live calibration-monitoring surface so future de-calibration is caught automatically instead of requiring another one-off Cloud Run backtest.

**Decision.** This issue should stay open only for the remaining calibration-tuning question, not for the original underdispersion bug. The original root cause is no longer a live blocker on the current staging set; the remaining work is product-level tuning and monitoring, not a regression fix to the model family itself.

### 37. Consistency distillation evaluated for Anemoi-Spread -- not yet warranted (#15) — *evaluation*

**The question.** #15 asked whether distilling a consistency model (Song et al. 2023) from the trained Anemoi-Spread diffusion teacher could give the 13-minute diffusion-stage budget a graded one-step/multistep response, supplementing the existing binary load-shedding path (#8) instead of relying on it alone. Paused since it was filed, pending #22's trained model and then #166's real fix (distilling from an overfit, collapsed teacher would have measured nothing useful) -- resumed once v7 was live and healthy.

**Built and run for real, not simulated.** `models/consistency.py` (`TrajectoryConsistencyModel`, an exact boundary condition `f(x, 0) = x` via a skip-connection parametrisation anchored to the teacher's own cosine schedule) and `training/consistency_distillation.py` (discrete-time consistency distillation, Song et al. Algorithm 2, with an EMA target network) shipped in #170. `anemoi consistency-distill` then ran end to end on the training VM against the real production diffusion champion (v7) and its real 637-case validation split, mirroring #10's own measurement pipeline so the numbers are directly comparable.

| config | NFE | wall time | track_error_48h_nm | long-lead track ratio range |
|---|---|---|---|---|
| teacher (200-step ancestral) | 200 | 253.0s | 296.4nm | 0.45-0.73 |
| student, 1-step | 1 | 2.4s | 407.4nm | 0.43-0.69 |
| student, 2-step | 2 | 3.8s | 408.6nm | 0.41-0.69 |
| student, 4-step | 4 | 6.2s | 433.2nm | 0.59-0.87 |

**The compute story is exactly what the theory promised** (~100x fewer network evaluations, real wall-clock to match) **-- the quality story is not there yet.** Calibration is close to the teacher at most leads and even *better* for the 4-step student at several -- but every tested student configuration's `track_error_48h_nm` is 37-46% worse than the teacher's, consistently across step counts, not noise.

**Decision: not warranted as a production supplement to load shedding, load shedding (#8) remains the sole real response.** The applied bar (student long-lead calibration within 70% of the teacher's own, point error within 115%) fails at every step count, on the point-accuracy axis specifically. This is the real reason it matters for the replace-vs-supplement question #15 posed: load shedding's cost (20→10 members) never biases the point forecast, only tail resolution; this first-pass distillation's cost is the opposite shape -- fast and comparably calibrated, but a systematic point-accuracy regression, the one number `evaluate_promotion` and NHC advisories weight most. A worse trade for an operational track product. Recorded as a real, evidence-based "not yet" rather than pursued further -- a single training run with no schedule/EMA-decay tuning and no refinement stage beyond the base algorithm, so the gap is plausibly closeable later, and `anemoi consistency-distill` makes re-measuring it cheap whenever that's worth revisiting.

**Enforced by** `tests/test_models.py` (consistency model boundary condition, one-step/multistep sampling), `tests/test_consistency_distillation.py` (the distillation loop, a real device-mutation regression caught by Copilot review on #170, the tradeoff harness and decision rule). Full report: `docs/backtests/2026-09-23-consistency-distill-diffusion-v7.json`.

### 38. The API container never got to scale to zero -- #172 closed — *bugfix, cost*

**Found while pricing the service (#171).** Cloudflare's billed-usage analytics showed the real-mode API container (`standard-1`, 4 GiB, billed per awake second) awake 49% of the time over 2026-09-21 to 23, and 14.8 h on 2026-09-22 alone, while using just 1,671 CPU-seconds in total. With zero Worker requests after 12:09, it stayed up until 12:26, not the configured `sleepAfter = '5m'`.

**Root cause, confirmed with `wrangler tail`, not guessed.** The stop fired at 12:26:02, exactly 5 minutes after an alarm at 12:21:02 at which nothing else happened. `@cloudflare/containers` 0.3.7 (the latest release) keeps the idle deadline `sleepAfterMs` only in memory and resets it to now + `sleepAfter` in its constructor. Every time the runtime re-created the Durable Object that manages the container, the container got a fresh window no matter how long it had really been idle. Three plausible suspects were checked and ruled out first: the WebSocket stream (nothing opens it), background threads in the API (there are none), and SIGTERM handling (`exec uvicorn`; the container stopped within 1.8 s once asked to).

**Fix (#173).** `AnemoiRealApi` overrides `renewActivityTimeout()` to persist the deadline in the Durable Object's own SQLite storage (`ctx.storage.kv`). The first, constructor-driven call restores it instead of renewing. Separately, the console's 60 s refresh (shorter than the 5-minute timer, so any open tab kept the container awake) now pauses while the tab is hidden and refreshes when it becomes visible again (`console/src/lib/poll.ts`).

**Verified live after deploy.** The last request was at 12:52:45; `Activity expired` fired at 12:57:45 and the container stopped at 12:57:47. Billed usage shows it asleep from 12:58 onwards. That also gave the first real cold-start measurement: a cycle from a stopped container took 26.2 s vs. about 6 s warm, so a cold start adds about 20 s. Worth up to about $27/month, the gap between always-awake and scale-to-zero, roughly a third of the service's monthly cost.

**Enforced by** `console/e2e/periodic-refresh.spec.ts` (a hidden tab makes no requests across five poll intervals and refreshes on becoming visible). The Worker override has no automated test: the behaviour depends on the Containers runtime re-creating the Durable Object, which can't be reproduced locally. It was verified against production instead, as above.

### 39. Cycle results lived only in container memory -- #175 closed — *bugfix*

**Found asking "are the API and console out of sync?"** They were, and the console wasn't at fault: it showed exactly what the API returned, and the API forgot. `RealState` kept each storm's cycle results and the drift monitor's live samples only in the container's memory. Confirmed in production: 12 cycles run on `AL172023` earlier in the day, and `GET /v1/storms/AL172023` then returned `"cycles": []`. Container restarts (every deploy, and since #38/#172 every sleep, 5 minutes after the last request) wiped it all. A second, independent cause surfaced on the way: `_refresh_live_storms` rebuilt every live storm's state from scratch on each 30-minute feed refresh, dropping cycles on the storms people actually watch, even with the container warm.

**Fix (#176).** Each cycle's served `CycleResult` is saved to R2 (`api/cycles/{storm}/{label}.json`) when it runs. It stores the served shape rather than the internal `CycleOutput`, because the routers only ever serve the converted form and it's plain JSON with nothing to round-trip. A storm's `cycles` is now a `CycleHistory` that learns every stored label from one listing per process and downloads a result only when first read, so cold starts don't slow down as history grows. Live-feed refreshes carry history over. The drift window is saved and restored the same way, and never written back until the stored one has been merged in, so a failed read can't overwrite history. Copilot review caught a real cross-thread race on the label index (FastAPI serves sync handlers from a thread pool); fixed with locked copies and snapshot iteration.

**Verified live across a real sleep.** A cycle ran at 17:55:16, the container stopped at 18:00:17, and after the cold start the storm listed the cycle and `GET` returned a response identical to the original.

**Still open:** production has never had a drift reference fit (`monitoring/drift_reference_gdas_finetune.json` is absent from R2), so the drift page reports `n_live: 0` regardless of how many samples are saved.

**Enforced by** `tests/test_api_real_state.py`: cycles surviving a simulated restart through the real routes, a failed write never failing a cycle, a live storm keeping cycles across a feed refresh, drift samples surviving a restart, and an unrestored drift window never being written back.

### 40. Live served-product calibration monitoring — closes #166 follow-up item 4 — *enhancement*

**The gap.** #36b's real follow-up list (item 4) named it directly: "add a live calibration-monitoring surface so future de-calibration is caught automatically instead of requiring another one-off Cloud Run backtest." `training.spread_backtest` (#10) already answers that question offline, but only from raw ensemble-member positions, which are sampled and then discarded once the served cone/intensity-PDF aggregates are computed -- nothing durable keeps them, and threading them through `inference.cycle.run_cycle` just for monitoring would be an invasive change to the pipeline itself.

**Fix (#184).** `monitoring.calibration_audit` answers a narrower, product-facing question instead, using data that's already durably stored: was the cone and intensity band this system actually *served* right, once the real truth became known? It scores each already-persisted `CycleResult` (#175) against a storm's own real subsequent fixes -- the same live NHC feed poll `RealState._refresh_live_storms` already runs every 30 minutes, so no new slow data source or offline-replay machinery (`skew_audit`'s ERA5T-lag design) is needed. `GET /v1/monitoring/calibration` exposes per-(lead, product) containment rate, and the console's Monitoring page renders it as a real line chart against each product's own nominal rate (cone ~67%, intensity 80%), with an honest empty state until real cycles have actually been audited.

**Decision.** This closes follow-up item 4 from #36b. The remaining short-lead overdispersion (item 2) and `extra_conditioning_dim`/`n_augment` questions (items 1, 3) are unaffected and stay open on #166 -- this surface exists so *future* de-calibration (including a regression in the current fix) is caught from real production traffic rather than requiring another manual backtest.

**Enforced by** `tests/test_calibration_audit.py` (16 tests: due logic, hit/miss scoring, persistence, idempotency, aggregation verdicts), `tests/test_api_real_state.py` (a full simulated-restart integration test), `tests/test_api_smoke.py`, and `console/e2e/console-visuals.spec.ts`.

### 41. Four defects found by actually using the deployed console — *bugfix*

Reported together after real use of the live site, not from tests. Each had shipped as part of something that was itself correct, which is why none of them surfaced earlier.

**The served diffusion sampler was never seeded (#188).** `real_inference_ensemble` called `model.sample(z_t, n_members=n_members)` with no `generator`, so it drew from torch's global RNG and every re-run of one cycle was a fresh draw. `spread_backtest` and `real_run_diffusion` both already passed a generator, and `run_cycle`'s climatological fallback is seeded (`ensemble_seed=0`) — production serving was the only non-reproducible path. Real consequence on EP172026, cycle `20260929_00Z`: four runs in ~70 seconds returned RI fractions of 20 / 30 / 35 / 25 %, straddling the 30 % alert threshold, so the flag flipped while nothing about the storm had changed. Now seeded from `cycle_sample_seed(storm_id, target_time)` — SHA-256, not the builtin `hash()`, which Python salts per process and would therefore be stable inside one container and different across restarts and replicas. The underlying estimator noise (±10 points at 20 members, against a threshold at 30 %) is a real but separate question, deliberately not conflated with this fix.

**A `members` request above 20 was accepted and silently reduced (#187).** `run_cycle` only ever applies a caller's request as a cap (`min(plan.requested_ensemble_members, requested)`, entry 8's own design), but `RunCycleRequest` advertised `le=100` and the console offered it — so `members: 30` produced a normal 20-member cycle, with the form still reading 30 beside `ensemble: 20 members`. Fixed with a bound, not a flag: `build_products(degraded=bool(flags))` means any flag marks the entire cycle degraded, and a full ensemble is not degraded because somebody asked for more than exists. Load shedding keeps its flag, since that one genuinely is degradation.

**The 60 s poll pulled the view back to the newest cycle (#186).** `load()` always re-fetched `[...cycles].sort().at(-1)`, so selecting an older cycle from **Past cycles** was undone within a minute — usually landing on a climatology-fallback cycle nobody had asked to see. Only visible once #175/#176 made cycle history durable enough to be worth clicking and #178/#179 started generating new labels on their own. A `viewedLabel` now pins what the user is actually looking at; `null` still means "follow the newest", which is the right default on first open.

**The waiter fired on every background poll, with no backdrop (#185).** `load()` set the global waiter unconditionally, so a refresh nobody asked for threw a full-screen, click-blocking `Please wait...` over the page once a minute — and with no background of its own it rendered as text floating over a fully-lit map, reading as a glitch rather than a loading state. Background refreshes are now silent, and the overlay that does show sits on a translucent dim above the mobile header's stacking context.

**Why these four are one entry.** They share a cause worth naming: each addition was correct in isolation and wrong in combination. Polling (#173) was right. Durable history (#176) was right. Automatic cycles (#179) were right. A loading indicator was right. Nobody re-examined what the page does when all four are true at once and a person is sitting in front of it — which is only observable by using the thing, not by testing the parts.

**Enforced by** `tests/test_real_inference_ensemble.py` (re-running one cycle returns identical members, with the global RNG deliberately perturbed between the two calls, plus seed stability/cycle-specificity), `tests/test_api_smoke.py` (over-large `members` refused, exact sizes honoured), `console/e2e/periodic-refresh.spec.ts` (a background poll neither raises the waiter nor moves the selected cycle).

### 42. Ensemble size raised to 50, and the RI flag made three-state (#188) — *enhancement*

**Found by following the reproducibility fix to its actual root.** Entry 41 seeded the served sampler so re-running a cycle reproduces it. That removed the symptom the user reported, but not the cause underneath it: `ri_probability` is a fraction of a finite ensemble compared against a hard 0.3 threshold, so consecutive real cycles six hours apart would keep flipping for the same reason re-runs had.

**The scope was wider than RI.** Every §6.1 product is a quantile or fraction over the same draws — cone radius is the 67th percentile of member distance, the intensity band is p10/p90, landfall and RI are member fractions. At 20 members, with zero model error, a true 62 nm cone radius reads 48–76 nm and a true 109 kt p90 reads 99–116 kt, which crosses a Saffir-Simpson boundary. And the smallest probability representable at all is 1/n, so a reported `0%` landfall meant "below our resolution", indistinguishable in the payload from "will not happen". Nobody had complained about those two because neither has a threshold making the noise visible.

**It was also quietly biasing #184.** A perfectly calibrated ensemble — truth drawn from exactly the member distribution — measures 62.1% containment at n=20 against a 67% nominal, because the cone is centred on the ensemble mean (off by ~σ/√n) and its radius is a 20-sample percentile. That −4.9 point error is a third of `_VERDICT_MARGIN` and leans "too narrow", the direction #166 has been chasing. It does not retract #166, whose finding was far larger, but the residual tuning question sits where a 5-point structural bias matters.

**Measured before changing anything.** `TrajectoryDenoiser.sample` carries members as a batch dimension, so cost is sublinear: 20 → 50 members is 0.06 s → 0.09 s at production architecture, and under 2 s even at 16× the model size, against a 13-minute budget. The budget is spent on Group 1 forward passes and input fetches. `DEFAULT_ENSEMBLE_MEMBERS` 20 → 50, `REDUCED_ENSEMBLE_MEMBERS` 10 → 25 to preserve #8's 2:1 shed ratio.

**A corollary nobody asked for but which follows.** Load shedding's member reduction buys almost no wall time — roughly 0.02 s at production size. Recorded, deliberately not acted on here.

**Three states, because two cannot be honest.** More members narrows the estimate; it does not make a point estimate honest about itself. `ForecastProducts` carries a 95% Wilson interval and `ri_uncertain`, and the banner renders flagged / undetermined / no signal. Wilson over the normal approximation because the latter is worst exactly here — small n, proportions near 0 or 1, where it returns bounds outside [0, 1].

**The compatibility trap.** `CyclePayload` is a *persisted* shape, not just a response one (#175). Adding required fields would have broken every cycle already in R2 — including the ones `calibration_audit` reads back to score calibration. They are optional; `None` means "predates the interval", which is true.

**Enforced by** `tests/test_postprocess.py` (Wilson bounds bracket the estimate and stay in [0,1] across every k for n in 5..200, and narrow as n grows; the uncertain band resolves correctly), `tests/test_calibration_audit.py` (a pre-#188 stored cycle still parses), `tests/test_api_smoke.py` (the payload contract, and the point estimate inside its own interval), `tests/test_cycle.py` (member assertions bound to the scheduler constants rather than literals), and `console/e2e/ri-banner.spec.ts` (all three states plus the legacy-null fallback).

### 43. #166 re-measured at 50 members — original defect closed, residual split in two — *evaluation*

**Re-run deliberately at 50, not 20.** Entry 42 quantified a finite-member bias in exactly the estimators #166 is judged by, so re-measuring at the old ensemble size would have answered the residual question through the bias. `spread-backtest --diffusion-version 8 --members 50`, 637 validation windows, Cloud Run execution `anemoi-train-schedule-4f2bs` (2026-09-29).

**The original defect is resolved.** Long-lead spread/skill went 0.11–0.17 (v6, collapsed) → 0.44–0.94 (v7, early-stopped) → **0.86–1.04** (v8 @ 50). Every long lead reads `calibrated`; the backtest's own verdict on #10's founding question is `extra_conditioning_dim: not_warranted`; and the cone drew on the ensemble basis for 346/346 cases, so the underdispersion guard never tripped.

**The residual is real and narrower than entry 36b recorded.** 36b described "mild short-lead overdispersion in a subset of cells and cross-track cases (1.2–2.3 at 12–48h)". At 50 members it is specifically **cross-track at 12–36h** (1.54 / 1.70 / 1.43), with along-track and wind calibrated at those same leads; the recurving subset is worse (2.14 at 12h). I had suggested the 20-member bias might explain part of it -- it does not: that bias is ~0.025 on the ratio against a 0.5–0.7 effect. A genuine model property, not a measurement artifact.

**A separate defect fell out of the same run, now #192.** The served 120h cone misses 44% against a ~33% nominal *while both per-axis ratios read calibrated*. Simulating `build_cone`'s own estimator against the measured parameters decomposes it: ~1.7 points from finite members, ~0.7 from anisotropy, ~5.5 from mild per-axis underdispersion that passes the 0.8–1.25 band, ~3.5 unexplained.

**Worth recording that the obvious explanation was wrong.** The first reading was shape mismatch -- a circular cone fitted to an anisotropic ensemble. Measuring it put anisotropy at 0.7 points of the 11. An elliptical cone would not have fixed this, and building one on the strength of the hypothesis would have been wasted work. The real lesson is narrower and more useful: a per-axis verdict of "calibrated" does not imply the 2-D product built from it is calibrated, and ratios of 0.91/0.95 -- comfortably inside the band -- already cost ~5.5 points of containment.

**Scope call.** #166 keeps only the short-lead cross-track overdispersion. The per-axis-vs-2-D calibration gap is #192.

### 44. Every console view woke the API container -- storm reads now served from KV (#206) — *bugfix, performance*

**Reported from real use:** an absurd wait before the console showed current storms and which ones had cycles. Traced through the code, since the deployed site couldn't be timed from the investigating environment: every page view and every 60 s poll went console Worker → `anemoi-api-real` Worker → container, with no caching anywhere. The container sleeps 5 minutes after its last request (#38/#172), so most visits paid for, in one request:

1. a container cold start (~20 s measured in #38), with `RealState` (including a full HURDAT2 parse) built inside the first request;
2. a serial NHC fetch -- `CurrentStorms.json`, then one TC-Vitals bulletin per active storm, each with its own 10 s timeout -- repeated by every concurrent request that arrived while the first was in flight;
3. inside that same request, the calibration audit (#40/#184): `_refresh_live_storms` called `_audit_calibration_due`, which downloaded **every stored cycle of every live storm** from R2, one at a time, every 30 minutes. That cost grew with each cycle a storm accumulated.

**Fix.**
- **KV read cache in the Worker** (`docker/api/src/readCache.ts`, binding `READ_CACHE`). `GET /v1/storms`, `/v1/storms/{id}` and `/v1/storms/{id}/cycles/{label}` are answered from KV without waking the container. Storm list and storm entries are served for up to 30 minutes and then refreshed in the background (stale-while-revalidate); they expire after 7 h so a dead cron makes data disappear instead of look current. Cycle results don't change once run and are kept 90 days. A miss falls through to the container and fills the entry; a 404 is never cached. Every successful cycle run, cron or manual, writes the result and refreshes that storm's entries. Responses carry `X-Anemoi-Cache: hit|stale|miss|bypass`.
- **`Cache-Control: no-cache`** skips the lookup and refills. KV reads can lag a write by up to a minute, so the console sends it for the one read that must see a write it just caused: the storm, right after running a cycle on it.
- **Calibration audit off the request path.** It moved to `POST /v1/internal/calibration-audit`, called once per synoptic cycle after the cron's runs (entry 46). `audit_storm(lead_hours=...)` now skips downloading a stored cycle whose leads are all not yet due or already audited. `/v1/internal/*` returns 404 on the Worker's public route, checked on the percent-decoded path.
- **NHC refresh single-flight and parallel.** One request fetches; concurrent ones serve the storms already known rather than each fetching again (only a process's very first fetch makes callers wait). Per-storm bulletins are fetched concurrently.
- **`RealState` built at startup** on a background thread (FastAPI lifespan), not inside the first request.

**Behaviour change worth knowing:** calibration samples now land once per synoptic cycle, not up to every 30 minutes while someone had the console open.

**Found on the way:** `test_real_state_merges_a_live_storm` hardcoded a 2026-09-22 fix; once that fell outside the 14-day active window (2026-10-06) the test failed on `main` and every PR. It's now dated relative to now.

**Enforced by** `tests/test_api_real_state.py` (listing storms never runs the audit; concurrent requests share one NHC fetch; a stale refresh in flight doesn't block other readers; the internal route is absent from the public schema), `tests/test_calibration_audit.py` (no download for a cycle with no due lead, or with every lead audited), `tests/test_live_atcf.py` (bulletins fetched concurrently, index order kept). The Worker cache has no automated test (`docker/api` has no test runner); it was exercised against a fake KV and container for hit, miss, stale refresh, bypass, uncached 404 and snapshot.

### 45. Return visits drew a blank page until the API answered (#207) — *enhancement*

Even with entry 44, a cache miss still meant waiting on a cold container, behind the full-page waiter, with nothing on screen. Each console page now keeps its last API answer in `localStorage` (`console/src/lib/lastKnown.ts`, keys versioned `anemoi:last:v1:`), draws it at once on the next visit and refreshes behind it; the homepage shows **Updating…** until the fresh answer lands, and reuses the schedule only for the same UTC day. Per-browser convenience only: it never decides what's true, and unavailable or unparseable storage reads as nothing remembered. The storm page also fetches the storm and the cycle it is showing at the same time when that label is already known, instead of one after the other.

**Enforced by** `console/e2e/instant-load.spec.ts` (with the API request held open, a return visit still renders the homepage and the storm; a first visit loads normally). Both return-visit tests fail without the change.

### 46. The cron became a durable Workflow (#208) — *reliability*

`runDueCycles` (#178) ran every active storm's cycle one after another inside a single `scheduled()` invocation, with no retries: a storm whose cycle failed or timed out waited six hours for the next synoptic time, and a busy day risked outrunning the cron's own time limit before the last storms ran. Entry 44 added two more steps to that same invocation.

**Now** the cron (`30 1,7,13,19 * * *`, t+1:30) starts one instance of the `anemoi-cycle` Cloudflare Workflow (`docker/api/src/cycleWorkflow.ts`) per cycle label, with instance id `cycle-<label>` -- so an at-least-once duplicate cron firing finds the instance already exists rather than starting a second run. Steps: **find due storms** → **run cycle {storm}**, one durable step each (retried twice on a 5xx or unreachable container, 2 min exponential backoff, 20 min timeout) → **refresh read cache** → **calibration audit**. One storm's failure never stops the rest.

**Two decisions worth stating.** A 4xx is recorded as `refused`, not thrown as `NonRetryableError`: that error fails the whole instance, not just one storm's step. And a retry first checks the storm's own cycle list, so an attempt that ran but lost its response isn't run twice.

**Review finding fixed before merge (Copilot):** the Workflows runtime re-runs `run` from the top on every resume, replaying finished steps from stored results, so log lines outside step bodies repeated once per later step. Every log line now comes from inside its step; the instance output carries each storm's final outcome.

**Where to look:** Cloudflare dashboard → **Workers & Pages → Workflows → anemoi-cycle** (its own sidebar entry, not a tab on the Worker), or `wrangler workflows instances list anemoi-cycle`. Empty until the first cron after a deploy.

**Enforced by** `pnpm check` and a `wrangler deploy --dry-run` bundle; `CycleWorkflow.run` was exercised with the `cloudflare:*` modules stubbed (recovery on retry, refusal without retry, a permanently failing storm not stopping the next one or the audit, `already run` on retry, replay emitting no duplicate logs). Not runnable under real Workflows locally.

---

## Implementation → rebrand

### 14. Two product names for one platform — *naming*

**Defect.** "AEOLUS / MERIDIAN" named two engines and no platform. Every sentence had to carry both names or pick one and mislead; the package was `aeolus`, the project `aeolus-meridian`, and the ensemble generator was named after lines of longitude, which describes nothing it does. There was no word for the whole system.

**Fix.** The platform is **Anemoi** — the Greek wind gods, many winds producing one forecast. The engines become modules of it: `AEOLUS` → **Anemoi-Core**, `MERIDIAN` → **Anemoi-Spread**, the consensus layer → **Anemoi-Fusion**. Each model architecture is personified as one of the six wind gods, and that god name — not the architecture — is the identifier in MLflow experiments, run tags, status badges and API paths.

**Enforced by** `anemoi.branding` (the single god ↔ architecture mapping), `tests/test_branding.py`. Package renamed `aeolus` → `anemoi`; CLI `aeolus` → `anemoi`; MLflow experiments `aeolus_lstm/` → `boreas/`, `meridian_diffusion/` → `skiron/`, and so on.

**Why the mapping lives in code.** The god names are not decoration — they appear in experiment names that post-mortems search on. A naming convention that exists only in documentation drifts silently; `branding.god()` raises `KeyError` on an unknown name rather than guessing, so a typo fails at the point of use instead of producing an unfindable run.

**Migration note.** Anything importing `aeolus.*` or invoking the `aeolus` CLI breaks on upgrade. There is deliberately no compatibility shim: the rename happened before external consumers existed, and a shim would have kept both names alive in documentation indefinitely.

---

## Design decisions worth stating

Not corrections — choices made during implementation that a future reader might otherwise second-guess.

**Availability is a queryable model, not an assumption.** `AvailabilityOracle` is a protocol. Timing tests configure an oracle rather than mocking a clock, so an outage scenario is three lines and a real-season replay harness is a second implementation of the same interface.

**Degradation is always flagged.** Every fallback appends to `CycleOutput.flags` and surfaces in the payload. A forecaster who cannot distinguish a full-ensemble cycle from a climatological-fallback cycle will eventually treat both the same way.

**The fusion weight floor.** No model is ever fully zeroed. Mid-season there may be only a handful of verifying storms; a model discarded on three cases is unrecoverable for the season.

**Six checks for one policy.** Each guards a different entry point. Any one being bypassed still leaves the others.

**Torch is optional.** The policy logic must remain importable and testable without a GPU, because that is the layer most worth running in CI on every commit.

---

Related: [Branding and Naming](Branding) · [References](References) · [Train/Serve Consistency](Train-Serve-Consistency) · [Inference Cycle](Inference-Cycle) · [Roadmap](Roadmap)
