# Anemoi — Input Sources & Skill-Gap Plan

Nov 13, 2026 · Jason Kolodziej

**Status:** in progress. This is the working plan for what follows multi-basin
phase 1 (`docs/multi_basin.md`). Why the sources come in this order is in
[`input_sources_plan.md`](input_sources_plan.md); this file adds the track
experiment, the checks, the schedule, and the record of what's done. A box is
ticked when its work has landed, with what was found written under it. The
[progress log](#progress-log) at the end lists the changes by date.

## Where things stand

The track gap is the priority: fusion v12's 48 h Atlantic track error is 231 nm, against a 70 nm promotion gate and NHC's 51 nm 2026 target. Ocean inputs mainly improve intensity, so they run alongside the track work instead of ahead of it.

Only two of the ten registry sources feed a model today (commit `3838fcc`, 2026-11-12). `Role.OPERATIONAL` means a source is allowed to be read, not that a model reads it. Since `b672fca` the registry
records the second fact too: `data.sources.used_by`, served as `used_by` by
`/v1/sources` and printed by `anemoi sources`.

| Source | Adapter | Used by a model today | Plan |
| --- | --- | --- | --- |
| `besttrack_working` / `besttrack_final` | `live_atcf`, `hurdat2` | LSTM and PINN input; labels for all models | Keep |
| `gdas_gfs` (ERA5 in Stage A) | `real_gridded` | CNN, Transformer, GNN, PINN, but SST is a 28 °C constant | Add GFS forecast leads (Phase 1) |
| `sst_ohc`: SST half | `real_sst` (OISST v2.1) | Nothing | Phase 2a |
| `sst_ohc`: OHC half | `real_ohc` (CoastWatch, fetch + decode, not yet wired); 60 kJ/cm² placeholder in every stage | Nothing | Phase 2b, using OSPO's CoastWatch feed (archive from 2020) |
| `goes` | `real_goes` | Nothing (matches CNN input shape) | Phase 4 |
| `ensemble_perturbations` | `real_ensemble` (GEFS) | Nothing. The spread backtest measures the diffusion ensemble's own spread and reads no GEFS | Phase 4, only if spread is too narrow |
| `microwave` | `real_microwave` | Nothing | Phase 4, as an optional masked input |
| `dropsonde`, `ndbc` | `real_dropsonde`, `real_ndbc` | Nothing. Verification only by designation: no verification code reads them yet | Verification only |

## Phase 0: Same-day fixes and checks

These answer the questions every later phase depends on, and each takes hours, not days.

- [x] **Check the OHC training archive.** Look for `na`/`np` files for 2021–2022 (Stage B years) in CoastWatch THREDDS or NCEI. The `na14/` tree lists only 2024–2026, and the old `na/2025` and `na/2026` folders were empty. If the files aren't there, OHC either waits for Phase 3 or trains from SHIPS predictors.
  - The files are there. The older chain covers the training years in full: `na/` and `np/` hold 365 daily files for 2021, 365 for 2022 and 363 for 2023 (listings, 2026-11-13). The older chain runs from 2020 day 121 to 2024 day 18; `na14`/`np14` take over from 2024 day 15. So every Stage B season (2021–2023 train, 2024 val, 2025 test; see Phase 3) has OHC, and the SHIPS fallback isn't needed.
  - f481ff1 recorded the opposite ("OHC still waits on the 2021–2022 training archive") in `data/sources.py`, wiki Data-Sources and Decision Log #30. Corrected in `72ef2c1`.
- [x] **Compare the `na` and `na14` versions.** Diff one overlapping day for grid, units and value range before training across the switch.
  - They are one product, so train across the switch as one input with one normalisation. Grid, units, fill and land mask are identical in 2021, 2024 and 2025 files: 0.25°, NA 0–60N 100W–0, NP 0–60N 100E–80W, kJ cm⁻², fill −999, and 0.0 is a real value (water below 26 °C). Every node is an exact node of `GriddedFields`' 721×1440 grid, so OHC is placed (flip latitude, wrap longitude), not interpolated. On a clean day (2023 day 291) the old file and `na14` v1r0 differ by RMS 0.0016 kJ/cm² (NP 0.0024), max 0.18.
  - What the adapter has to handle (Phase 2b):
    - **Two formats.** The old chain and `na14` up to 2025 day 84 are NetCDF-3; v1r1 from 2025 day 85 is HDF5. NetCDF-3 needs scipy, which the `gridded` extra doesn't declare (it comes in only through `tracking`), so a gridded-only install can't open any 2021–2024 file.
    - **v1r1 shifts the name by a day.** From 2025 day 85 a file is named for the day before it was made and holds data through its creation day. Under the D−2 name rule, 2025 and live inputs are a day fresher than 2021–2024 inputs (about one day's change, RMS 3.3–3.6 kJ/cm² over warm water). Not leakage, but a skew between train and test; indexing by creation day (v1r1 name ≤ D−3) removes it.
    - **Blank files.** `na14` 2025 days 197–201 and 2026 day 7 are all zeros, coordinates included (day 199 was the first found). Reject a file whose coordinates aren't the expected arrays or that has no fill cells.
    - **Two basins.** Write NP first, then NA where NA is valid: NP holds 0.0, not fill, in the 80W column. 14 of the 5,095 fixes of 2021–2025 (all extratropical, above 48N) fall off both grids.
    - **Missing days.** 22 fix–basin pairs read a D−2 file CoastWatch doesn't have; the day before exists every time.
  - **Quality.** The January 2024 outage (old-chain days 10–22) reaches no Stage B storm sample. A worse one sits inside the training years with no replacement: 2022 days 201–204 and 208–216 (altimeter error peaking at 0.65 against a normal 0.29), read by 69 EP training fixes (Estelle, Frank, Georgette, Howard). Mask or flag those days.
- [x] **Correct the stale OHC claim.** Update the `sst_ohc` provider/notes in `data/sources.py`, Decision-Log #30 and wiki Data-Sources. The "stops 2026-01-26" result came from AOML's HDB ERDDAP. OSPO's CoastWatch `na14/2026/` has day 316 (Nov 12) posted Nov 13, with no gaps since Jul 17.
  - Done. `data/sources.py` `sst_ohc` provider/notes now name the OSPO CoastWatch feed and the AOML endpoint mix-up; wiki Data-Sources (the status row, the registry row and the prose note) and Decision-Log #30 carry the correction.
- [x] **Set the OHC date rule.** Files post about 11:30 the day after their valid date (about 36 h latency), so a live cycle uses the file from D−2. Put that rule in `data.availability`.
  - Done as `OHC_VALID_LAG` (2 days) in `data.availability`, documented beside `_valid_time_for`. The combined `sst_ohc` source still resolves on the SST D−1 rule, because OHC isn't a model input yet; the D−2 rule applies when OHC is wired (Phase 2b).
  - Measured from the `na14/2026/` listing: for days 198–316, files posted a median 35.5 h after 00 UTC of their name day, the earliest at 33.3 h and the latest at 47.8 h (day 313, posted 23:47 UTC the next day). Across 2026, 264 of 315 files posted between 11:00 and 11:59 UTC. So D−2 is available to every cycle, and D−1 is never available to 00 and 06 UTC cycles and not reliably to 12 and 18 UTC ones.
- [x] **Ship the Sources page fix** (input_sources_plan step 0). Rename the column to **Role** and add **Used by** from `/v1/sources`.
  - API (`b672fca`, reviewed in `7fe6207`–`5986802`): `/v1/sources` returns `used_by` per source from one mapping in `data/sources.py`, and `role` as the `Role` enum. `tests/test_sources.py` holds the mapping to the code: an adapter imported outside its own file must be in `used_by`, and each model's entry must match its training runner's and live builder's signature.
  - Console (`64714de`–`5189e29`): the Sources page shows Role and Used by, and the system graph draws every registered source from `used_by` in three states (feeds a model, labels or verification only, not used yet). The console keeps no copy of the mapping; the e2e specs feed both pages a `used_by` rewired from today's, so a hard-coded table fails them. A missing `used_by` shows as "use not reported". The graph scrolls inside its card on a phone and below about 1146 px.
  - Found on the way, left open (Decision Log 67): the cycle planner flags `missing:sst_ohc` and marks a cycle degraded though nothing reads `sst_ohc`; training crops are centred on the HURDAT2 final fix but live crops on the working fix; `curriculum.yaml`'s Stage B `input_sources` lists `goes` and `sst_ohc`.
- [x] **Pull phase 1's spread-skill and rank histograms per lead.** This settles the GEFS question with data you already have.
  - Not a lookup: it needs one run. Nothing measures the v12 ensemble's spread. Diffusion training scores only the ensemble mean, so the registry, R2 and the live calibration endpoint hold point errors and cone containment, not spread-skill or rank histograms. Every per-lead table in the repo is for diffusion v6 or v7 (20 members, 637 Atlantic windows from 2023).
  - The run, on the CPU training job (about 10 minutes for the September runs):
    `gcloud run jobs execute anemoi-train-schedule --region us-central1 --task-timeout 3600s --args=spread-backtest,--hurdat2,/app/data/hurdat2-atl.txt,--gdas-cache-dir,/cache/gdas_cache_f006,--registry-root,/tmp/registry,--members,50,--out,/cache/spread-backtest-diffusion-v12-m50.json`
    then copy the JSON into `docs/backtests/`. `--out` under `/cache` and the timeout are untested additions to the documented command.
  - Read `dropout` in diffusion v12's `arch_params` tag first. `--diffusion-dropout` defaults to 0.0 and the documented GPU job doesn't set `DIFFUSION_DROPOUT`. Dropout 0.1 is what closed the long-lead under-dispersion in September (v7 0.45 to 0.73 at 72 to 120 h, v8 0.86 to 1.04). v12's training set is about three times that one, so dropout 0.0 need not reproduce v7's result.
  - Until the run exists the GEFS gate is undecided, so GEFS doesn't start. The last healthy model measured (v8, 50 members, 2026-09-29) read `not_warranted`. If v12's long-lead track ratios are below 0.8, try a derived-only retrain with dropout 0.1 before GEFS; GEFS is the live option only if under-dispersion survives that and sits in the recurving cases.
  - **Done (2026-11-13, local agent): `docs/backtests/2026-11-13-spread-backtest-diffusion-v12-m50.json`.** Diffusion v12, 50 members, 607 validation windows, against lstm v12, cnn v8, transformer v8, gnn v7, pinn v7. Verdict: `extra_conditioning_dim: warranted`, the opposite of v8's `not_warranted`.
    - Track, overall (spread/RMSE): 72 h 0.84 along / 0.86 cross, 96 h **0.76** / 0.83, 120 h 0.87 / 0.83. Recurving (n = 43–44): 72 h 1.10 / **0.77**, 96 h 0.80 / 0.81, 120 h 0.97 / **0.73**. Three long-lead track ratios are under the 0.8 gate, two of them cross-track on recurving storms: the case GEFS conditioning is meant for.
    - Intensity is under-dispersed from 48 h at every lead (wind 0.73 to 0.63 overall), which GEFS track conditioning doesn't address.
    - The served 120 h cone uses the ensemble on all 172 cases and misses the truth 45% of the time against the ~33% a calibrated 2/3 circle should.
    - v12's `arch_params` (read 2026-11-13 from `GET /v1/registry/diffusion/architecture?version=12`): `dropout` 0.0, `extra_conditioning_dim` 0. v12 was trained without the dropout that closed September's long-lead under-dispersion (v7 → v8), so by this item's rule the next step is a derived-only retrain with `DIFFUSION_DROPOUT=0.1`, measured with this command, before GEFS. No retrain was run here.
    - **Dropout-0.1 retrain done (2026-11-13, `anemoi-train-schedule-kqgcz`, derived-only from lstm v12, cnn v8, transformer v8, gnn v7, pinn v7):** diffusion v13 and fusion v13 registered and auto-staged on the point gate (v12s archived; production unchanged). Point error moved slightly: diffusion 48/72/120 h 250/378/537 → 245/354/520 nm, fusion 189/293/609 → 188/292/604. Spread (`docs/backtests/2026-11-13-spread-backtest-diffusion-v13-m50.json`, same 607 windows, 50 members):
      - Overall track is now calibrated at every lead from 48 h (along 0.93/0.93/0.80/0.92 at 48/72/96/120 h; cross 0.89/0.80/0.87/0.90). 96 h along-track sits exactly on 0.80.
      - Recurving long lead is still under the gate: 96 h along 0.80 → 0.71, cross 0.81 → 0.79; 120 h cross 0.73 → 0.70 (72 h cross improved 0.77 → 0.92). n = 43–44 cases from few storms, so these move with a handful of storms.
      - Intensity didn't improve (overall wind 0.59–0.68 from 48 h), and the 120 h served cone still misses 45%.
      - Verdict still `warranted`. By this item's rule the under-dispersion survived dropout 0.1 and sits in the recurving cases, so **GEFS conditioning (Phase 4) is now the live option** for track; intensity spread needs its own fix, which GEFS track conditioning doesn't address.
  - The backtest has no per-basin split, and validation is now the 2024 season pooled across AL, EP and CP, so one basin can hide another. `calibrate()` already takes a `case_filter`; a per-basin breakdown is a small code change.

## Phase 1: Track experiment and baseline

This phase answers one question fast: is the 231 nm error a missing-input problem or a model problem? The models only see one GDAS f006 snapshot, so nothing tells them how the steering flow evolves over 48–120 h. SHIPS switched to forecast-model predictors in 1997 for the same reason.

1. **Homogeneous baseline (do first).** Score fusion, the raw GFS track (AVNO) and NHC's official forecast (OFCL) on the same cases from the ATCF a-decks. If fusion can't beat GFS's own track, the ML layer is subtracting value.
   - **Done: guidance and fusion's paired test.** `anemoi baseline-backtest` (`5ccaf90` and the commits around it; Decision Log 66) scores NHC's a-deck techniques on exactly the registry's 2024 validation windows: 607 windows, whose persistence reproduces the registered 335 / 253 / 186 nm. The OFCL join reproduces NHC's own 2024 errors case for case (Atlantic 48 h: 214 of 214, 45.44 against 45.41 nm). Result: `docs/backtests/2026-11-13-homogeneous-baseline-val2024.json`.
   - Atlantic, 48 h, on the cases every technique has (sample B: 242 cases, 15 storms): OFCL 57, AVNI (the GFS track a cycle has) 66, AVNO 58, EMXI/EMX2 59, CLIPER5 248 nm. On NHC's tropical-only sample C (190 cases): 44 / 53 / 48 / 48 / 206.
   - **Fusion's registered mean already answers most of it.** Fusion v12's 231 nm is a mean over all 255 Atlantic windows. To tie AVNI on sample B, the 13 windows B leaves out would need a mean error of 3,304 nm, where persistence scores 434. So on Atlantic B fusion is behind GFS's own track; its registered mean is 3.5× AVNI's. On C it would need 752 nm on 65 windows (persistence 470): very likely behind. East Pacific: 359 nm needed on 36 windows for B (persistence 283), so unlikely; C is open. Central Pacific is one storm (Hone) and decides nothing.
   - **The pre-registered test: decided, against fusion** (2026-11-13, `docs/backtests/2026-11-13-homogeneous-baseline-val2024-fusion-v12.json`). Fusion minus AVNI, Atlantic 48 h: sample B **+154 nm**, 95% storm-block interval [112, 202] (242 cases, 15 storms); sample C **+122 nm** [89, 164] (190 cases, 15 storms). Fusion beats AVNI on 12% of cases in both. Every figure here is on the sample's homogeneous cases; the report's `pairwise_n_*` fields are a separate diagnostic (the cases the two members alone share). Both intervals exclude zero on the positive side, so by Decision Log 66's rule the ML layer subtracts value against the GFS track it could have read. Fusion's own means: AL B 220 nm against AVNI 66, AVNO-6 67, OFCL 57, OCD5 248 (11% skill over CLIPER). East Pacific B points the same way: +64 nm [18, 119] (102 cases, 9 storms); EP C has 70 cases from 7 storms, under the 8-storm threshold, so it gets a mean (+59 nm) but no interval. Inputs: fusion v12 with lstm v12, cnn v8, transformer v8, gnn v7, pinn v7; all 607 windows forecast; the job's 115 recomputed metrics match the registry; same HURDAT2 bytes (sha256 `d1debf35…`).
   - How it was run: it is fusion minus AVNI, Atlantic 48 h, on B and C, with a storm-block interval, and it needs fusion's per-case forecasts. That is an inference-only job on the training machine: it loads fusion v12 and its five Group 1 checkpoints, and trains, registers and promotes nothing. Once `5ccaf90` is on `main` and CI has rebuilt the image:
     `gcloud run jobs execute anemoi-train-schedule --region us-central1 --task-timeout 3600s --args=validation-forecasts,--hurdat2,/app/data/hurdat2-atl.txt,--gdas-cache-dir,/cache/gdas_cache_f006,--registry-root,/tmp/registry,--fusion-version,12,--out,/cache/backtests/validation-forecasts-fusion-v12-val2024.json`
     Then score it here with `anemoi baseline-backtest ... --model-forecasts <that file>` (docker/cloud-run-training/README.md, One-off commands). Check that the job reports the registered and recomputed metrics consistent and `n_without_forecast` = 0.
   - Also found: the training emulator's working track is noisier than NHC's real one. On these cases its 6 h motion error is 20.8 nm RMS against CARQ's 10.3, and its position is 13.0 nm from the best track against CARQ's 5.3. That is a case for re-calibrating `working_track_noise`, as a training decision of its own.
2. **Steering-along-track spike.** Use `gfs_url(valid_time, lead_hours)` to fetch the 850–200 mb steering layer at f006–f120, sampled along the GFS forecast track. Add it as Transformer conditioning in a throwaway branch, retrain Stage B only, and compare 48 h error per basin.
   - **Built (2026-11-13), not yet run.** Choices made with the user: the track is advected through the same GFS fields, not NHC's AVNO (Decision Log 66 keeps a-decks verification-only, and train and serve then compute it the same way); leads to 48 h, the gate's lead; the retrain runs against no registry.
   - `data/steering.py`: from the t−6 run that Stage B's crops already come from, f006–f054 (valid t … t+48 h), the 850–200 hPa pressure-weighted deep-layer-mean wind and the 850–200 hPa shear, each averaged over a 5° disc. The disc follows a beta-advection track: every 6 h, move with the disc-mean DLM wind plus a 2 m/s northwestward beta drift. That gives 9 leads × (u, v, shear u, shear v, track dx, dy) = 54 features per window, cached per (storm, time) like the crops, by `anemoi steering-cache` (one fetch per valid time, shared across storms; sharded across Cloud Run tasks). On Idalia at 2023-08-29 12Z the track runs 361 nm north and 9 nm east at 24 h, against the real 325 nm and 70 nm: BAM-quality placement.
   - `training/steering_spike.py` (`anemoi steering-spike`): Stage A once, then for each seed two Stage B arms from the same weights, on the same windows (those with steering), with the same window draw and shuffle seed. *Baseline* uses the usual channels; *steering* adds the 54 features as constant channels through their own zero-initialised conv beside the patch embedding, so both arms start as the same function. Stage B's freezing (everything outside the head) holds in both arms; the steering conv is the one extra trainable part, and both arms are reseeded so they see the same batch order. It reports each basin's 48 h mean error per arm, the paired difference (steering − baseline) with a storm-block interval, and the baseline's difference across seeds as the noise floor. Nothing is registered or uploaded.
   - **Read it as:** a gain on Atlantic 48 h whose interval excludes zero and that is larger than the seed-to-seed noise means forecast-lead steering is a missing input (the exit rule's "make it a registry input"); no gain means the architectures come next, with AVNO as the one stronger retry.
3. **AIFS feasibility check (in parallel).** Check how far back archived AIFS forecasts go, in what format, and their latency. ECMWF reports AIFS cuts TC position error substantially versus IFS but has a weak-intensity bias, so treat it as a track input only.
   - **Done: a baseline now, not a trained input.** Operational AIFS Single starts with the 06 UTC run of 2025-02-25 (v1.1 from 2025-08-27, v2 from 2026-05-12); AIFS ENS with 06 UTC 2025-07-01. The AWS open-data mirror also keeps experimental AIFS for every cycle from 06 UTC 2024-02-28 to 2025-02-25. So nothing covers the 2021–2023 training years, experimental AIFS covers the 2024 validation season and operational AIFS the 2025 test season. AIFS v2 was itself fine-tuned on 2018–2024 analyses, so every Stage B year is inside some version's training data.
   - Format: 0.25° GRIB2, one file per 6 h step to 360 h, with a JSON index for byte-range reads; u and v at 850–200 hPa and mean sea-level pressure in every version checked; AIFS Single also issues track BUFR.
   - Latency: the schedule says step 0 at T+5:45 and step 360 at T+7:34, but those are schedule stamps. Every step is actually out together at about T+5:05 to T+6:15 (median T+5:24 over 82 cycles), so the t−6 cycle is complete before the t+1:30 production run and the GFS t−6 rule carries over unchanged.
   - Skill (ECMWF Newsletter 187, Tech Memos 931 and 938; global, against the IFS control): position error better by about 0.5 forecast days (Jul 2024–Jun 2025) and 0.5–1 days (Jul 2025–Jun 2026); a pronounced weak-intensity bias already present at step 0. Never use AIFS intensity without bias correction.
   - As a baseline: NHC's archived 2025 a-decks carry EAIO/EAII (252 cycles, 00/12 UTC only); none of the 2024 decks or the 2026 public decks do (real-time access is restricted). For 2024, tracks would come from the open-data BUFR or fields. Revisit AIFS as an input only if Stage B can train on the AIFS era or handle a missing AIFS input for earlier years.

**Exit:** If step 2 moves 48 h AL error clearly toward the 70 nm gate, make forecast-lead steering a registry input (train/serve: GFS f-leads from the t−6 cycle). If not, go back to the architectures before adding more sources.

## Phase 2: Ocean inputs (runs alongside Phase 1)

This replaces the two constants with real ocean data, in two separate PRs and retrains so any intensity change traces back to one input.

**2a. OISST into `GriddedFields.sst`** (input_sources_plan step 1)

- [ ] Fill `sst` from `real_sst.sst_at` in `gdas_to_gridded_fields`, using the day before the valid time.
- [ ] Add a date-keyed SST side cache so the 5,095 GDAS GRIB crops don't need re-fetching.
- [ ] In the live cycle, flag late OISST instead of silently falling back.
- [ ] Retrain and compare per basin and lead. Expect gains mainly in EP intensity.

**2b. OSPO OHC into `GriddedFields.ohc`** (Phase 0 confirmed the archive and compared the versions)

- [x] Write a `real_ohc` adapter for `ohc_{na,np}QG3_{yyyy}_{ddd}.nc` (2020–2024) and `ohc_{na,np}14QG3_{yyyy}_{ddd}.nc` (2024 on), with the D−2 date rule. It must read NetCDF-3 and HDF5 (add scipy to the `gridded` extra), index v1r1 files by creation day, reject blank files, place NP then NA on the global grid, and mask the 2022 outage days (Phase 0, version comparison).
  - **Built and reviewed** (`267b8ca`–`6763b70`). `data/real_ohc.py` is fetch + decode only. Nothing imports it, and `tests/test_sources.py`'s `ADAPTERS` map enforces that.
  - It reads the newest file created on or before date(t)−2. It steps back at most 3 days over a 404, a rejected file or the 2025-03-26 switch gap, and records each step-back.
  - Format is sniffed from the first bytes. It rejects files whose coordinates, units, fill or `date_created` are wrong. It places NP then NA on the 721×1440 lattice. `ohc_at` is bilinear and needs all four corners. It flags a file degraded when its median `sshaE` is more than 1.12 times the median of its basin's files from the 30 days before (one every 5 days).
  - 51 offline tests and 8 network tests. A data review reproduced the decode bit for bit on 20 real files across all three chains.
  - Two reviews (code, real data) found 2 major and 12 minor issues. Fixed in `4712f1e`–`6763b70`:
    - a cut-off download is now a fetch error instead of a silent fall-back to an older file;
    - `http_get` is tested against a local server;
    - cycle times must be synoptic UTC;
    - NP's lone 0.0 at 8.0N 80.0W is no longer placed;
    - test gaps and docs are closed.
  - The last two review items are closed (Handoff, item 4). The degraded flag is relative to a trailing 30-day baseline, calibrated on 1,081 real files: it catches every documented outage day (36 of 36) and flags 27 of 373 2026 files where the fixed 0.32 flagged 134. The SHIPS test finds the newest edition on CIRA's development-data page and the 2021–2022 records by bisection, and skips on a 404.
- [x] Regression-test it against SHIPS' SOHC: on 557 open-ocean Atlantic cases of 2021–2022, SOHC equals the bilinear value at the best-track centre of the file named for the day before, within 0.5 kJ/cm² (Phase 3).
  - Done (`1e480ad`, `354a109`): it matches at all 555 cases whose cell doesn't touch 80.0W (max |d| 0.498), using the real files. Two of the 557 sit where NA and NP meet: one, Lisa, reads 85.10 against SOHC 33 from NA but 33.45 from NP. So the test excludes cells touching 80.0W.
- [ ] Stage A has no OHC before 2012, so mask OHC in Stage A or feed it in Stage B only.
- [ ] SH, NI and WP-west storms fall outside the products' coverage: mask them and flag `missing:sst_ohc`.
- [ ] Retrain and compare against 2a's run. PI's `ohc_bonus` and `apply_cold_wake` start using real values here.

**Done when:** intensity skill improves or holds in AL and EP, and no basin's track gate regresses.

## Phase 3: More training data (desk research, start now)

Stage B trains on 2021–2023 (116 storms: 58 Atlantic, 58 Eastern Pacific), validates on 2024 (33 storms) and tests on 2025 (33), because `GDAS_ARCHIVE_START` is 2021-03-22 18Z (the first valid time whose f006 the reader can fetch; no 2021 fix comes earlier) and the splits move with the newest HURDAT2 season (`data.splits.season_boundaries`, N = 2025). The plan first said 21 Atlantic storms from 2021–2022, copied from `docs/multi_basin.md`; the split in the code says otherwise. That still limits how much any new input can show. This research needs no GPU time, so it runs from day one.

| Dataset | What it gives | Covers | Constraint | First step |
| --- | --- | --- | --- | --- |
| Older GFS/GDAS analyses | A longer Stage B, same flavor as serving | `noaa-gfs-bdp-pds` `gdas.*`: 0.25° f006 from 2015-06-22 12Z, `.idx` from 2017-07-01, FV3 usable from 2019-06-15 00Z | The GDAS cycle on GFS v15 (64 levels), not serving's GFS cycle on v16 (127 levels). Needs a gdas URL builder: prefix `gdas1.` until 2017-07-19 06Z, and no `atmos/` before 2021-03-22 12Z. Its training floor must be kept apart from `GDAS_ARCHIVE_START` | **Done (research, verified).** The `.idx` files carry all 8 messages Stage B reads, under the same labels, on the same 1440×721 grid. 2019–2020 adds 91 AL+EP storms (39 + 52) whose t−6 h f006 and `.idx` exist (2,237 of 2,242 fixes), taking Stage B training from 116 to 207 storms (208 with CP012019). The bucket has no f006 from 2019-04-25 06Z to 2019-06-14 18Z. July 2017–2018 (spectral v14): 72 storms in the window, 70 with indexed fields; at most an ablation. 2015–2016 has no `.idx`. NCEI holds only 0.5° and 1°; NCAR GDEX is unreachable from here (TLS). Using it is a retrain decision, not taken here. Side fix: `GDAS_ARCHIVE_START` was 11 weeks early (`8e5d9d3`) |
| [SHIPS developmental data](https://rammb2.cira.colostate.edu/?p=8297) | Per-fix intensity predictors incl. ocean heat content | AL, CP, EP 1982–2025 (7-day files, posted 2026-10) | Predictors come from the operational analysis used at the time; no forecasts in the files | **Done.** Not needed as an OHC fallback. Its SOHC is the same CoastWatch product, so it becomes the OHC adapter's regression test (2b). It joins on (storm, synoptic time): 407 of 583 Atlantic fixes in 2021, 295 of 449 in 2022; every miss is EX/LO/DB. NOHC ends 2024-09-17. The DSHP/LGEM baseline is in the a-decks (SHIP, DSHP, LGEM every cycle, 0–168 h) and RI probabilities in the e-decks, so the intensity baseline reads those |
| [TC PRIMED](https://rammb2.cira.colostate.edu/research/ai/tcprimed) | Storm-centred microwave, IR and ERA5 diagnostics | Final v01r01 files: AL, EP, IO and WP 1987–2024; SH from the 1988 season; CP in 25 seasons (2024 CP is preliminary only); plus 2025 AL and CP. 3,657 storms | ERA5 diagnostics along the post-season best track; no OHC; nothing before 1987 | **Done (verified).** ERA5 diagnostics are a go for Stage A for 1987–2019 of its 1980–2019 window, with conditions: mask 1980–1986. Drop `intensity_change`, which looks up to 24 h ahead and is future truth. Pair each cycle with the latest pass at or before it: nearest-synoptic pairing puts 46.7% of passes after the cycle, median 90 min. Pad the SST diagnostic to `diagnostics/time`, since AL032022 has no SST records. IR comes only attached to a pass (within 3 h), not at synoptic times. Microwave is a no-go. `real_microwave` only fetches RSS's daily 0.25° SSMIS F16–F18 retrievals, while TC PRIMED has 1C XCAL and GPROF V07A on swaths. NASA moved to V08 on 2026-02-28, and CIRA stopped preliminary files on 2026-03-01. Verification: go for final seasons. Size: 73.3 GB for 2022 across all basins; 96.5 GB for AL+EP+CP 2021–2023 |
| AIFS forecast archive | Track baseline (Phase 1, step 3) | Experimental from 2024-02-28, operational from 2025-02-25 | Nothing for 2021–2023 | **Done.** A baseline now (EAIO/EAII in NHC's 2025 decks), not a trained input |

## Phase 4: Later, each gated on evidence

- **GOES into the CNN.** Stage B only, since the archive starts in 2017. Needs a crop cache and a new `in_channels`, so it's a new model version. Gate: CNN with GOES beats CNN without it on Stage B validation per basin, within the cycle-time budget.
- **GEFS as diffusion conditioning.** Only if Phase 0's spread-skill check shows the ensemble is under-dispersed at recurvature. **Gate met (2026-11-13):** with dropout 0.1 (v13) recurving 96 h along-track is 0.71 and 120 h cross-track 0.70.
- **Microwave.** Only as a masked optional input with a trained missing-data path. TC PRIMED (Phase 3) supplies the training years.
- **Gate re-derivation.** Set `track_error_72h_nm`, `track_error_120h_nm` and both intensity thresholds from NHC's verification report, and add a rapid-intensification metric (≥ 30 kt in 24 h).
- **New basins.** WP needs JTWC best track and Himawari imagery. NI and SH have no OSPO OHC product, so they use the masked OHC path from 2b.

## Console changes

Each phase that adds or changes an input changes what the console shows, so these ship in the same PR as the data change. Since phase 0 the console draws who reads each source from `/v1/sources`' `used_by` and keeps no copy, so a data change that updates `used_by` updates the console with it.

| Phase | Change | Files | API |
| --- | --- | --- | --- |
| 0 ✓ | Sources page: rename the column to **Role**, add **Used by** ("LSTM · labels", "verification", "not used yet"), and reword the subtitle so the badge reads as permission, not status | `routes/sources/+page.svelte` | Add `used_by: string[]` to `SourceOut` and `/v1/sources` |
| 0 ✓ | System graph: drive `FEEDS` from the same `used_by` mapping, and show every unused source (OISST, OHC, GEFS, microwave), not only GOES and buoy/dropsonde; let it scroll sideways on phones | `system/SystemGraph.svelte` | Same field |
| 0 ✓ | Mark dropsonde and NDBC as verification-only rather than unused | Sources page, graph | `used_by: ["verification"]` |
| 1 | Storm page: show fusion beside the GFS track (AVNO) and NHC's official forecast, per lead, for verified cycles | `routes/storms/[stormId]/+page.svelte` | Baseline errors per lead |
| 1 | Models/registry: per-basin 48 h track error against the 70 nm gate | `routes/models`, `routes/registry` | Already in tags (`EP/track_error_48h_nm`) |
| 1 | Graph: GFS node title from "t−6" to "t−6 + forecast leads" once leads are an input | `SystemGraph.svelte` | None |
| 2 | SST/OHC source drawn as feeding CNN, Transformer, GNN and PINN. No console change: the node exists and follows `used_by` | None | `used_by` |
| 2 | Flag text for a late OISST file and for OHC outside product coverage (exact flag names TBD in `docs/api.md`) | `FlagsList.svelte` | New flags in the fixed vocabulary |
| 4 | Monitoring: rapid-intensification hit rate and per-lead spread-skill / rank histograms | `routes/monitoring/+page.svelte` | New metric endpoints |

The Phase 0 rows (✓) are the console half of input_sources_plan step 0, done in `64714de`–`5189e29` after #239.

## Schedule

The fastest route runs the tracks in parallel. Phase 0 and Phase 3 research start on day 1, and track and ocean retrains share the GPU in weeks 1–2.

| Phase | Day 1 | Week 1 | Week 2 | Weeks 3–4 |
| --- | --- | --- | --- | --- |
| 0 · checks | Archive, version, notes, date rule | | | |
| 1 · track | | Homogeneous baseline | Steering-lead spike → **48 h gate** | Leads as input, or rework models |
| 2 · ocean | | 2a OISST into SST, retrain | (2a cont.) compare per basin | 2b OSPO OHC, if archive found |
| 3 · data | Older GDAS, SHIPS, TC PRIMED, AIFS archive (desk research) | (cont.) | (cont.) | Extend Stage B and retrain |
| 4 · later | | | | GOES, GEFS, microwave, gates |

Timeboxes are proposed. Each input lands as its own PR and retrain.

The critical path is Phase 1: its week 2 result decides whether weeks 3–4 go to forecast-lead inputs or back to the architectures. Phase 0 found the OHC files for every Stage B season, so 2b can start whenever 2a has its result.

## Handoff to a local agent

The cloud session stopped here on 2026-11-13; PR #243 carries a comment with the same list. Items 1–3 need the training machine or write access to the wiki repository, so a local agent with `gcloud` and wiki access takes them. Both training-machine jobs load existing checkpoints only: they don't train, register or promote anything.

1. ~~**Fusion's per-case forecasts** (Phase 1, step 1).~~ **Done** (2026-11-13, `anemoi-train-schedule-w2kr2`, image `0f721c18f899`): fusion behind AVNI on Atlantic B and C; see Phase 1, step 1.
   - Needs: this branch merged to `main` (for `5ccaf90`) and the training image rebuilt by CI.
   - Run the `validation-forecasts` command in Phase 1, step 1.
   - Check that the job reports the registered and recomputed metrics as consistent, and that `n_without_forecast` = 0.
   - Score it with `anemoi baseline-backtest ... --model-forecasts <file>`, using the decision rule in Decision Log 66: fusion − AVNI, Atlantic 48 h, samples B and C, storm-block bootstrap.
   - Commit the JSON under `docs/backtests/` and record the result in Phase 1, step 1 and the progress log.
2. ~~**Spread-skill for diffusion v12** (Phase 0).~~ **Done** (2026-11-13, `anemoi-train-schedule-wf2d2`); results under Phase 0. v12's `dropout` is 0.0, so the dropout-0.1 retrain comes before GEFS.
   - First read `dropout` in v12's `arch_params` tag.
   - Run the 50-member `spread-backtest` command in Phase 0.
   - Copy the JSON into `docs/backtests/` and record the long-lead track ratios against the 0.8 gate.
3. ~~**Unblock the wiki.**~~ **Done** (2026-11-13): wiki commit `8545d05` reverts `af8e4ac`…`2717b8f`; *Publish wiki* published `0f721c1` and the wiki now equals `wiki/`.
   - Needs: this branch merged to `main`.
   - In the wiki repository, revert `af8e4ac` through `2717b8f`, then run *Publish wiki*. The full reasoning is in the wiki entry under Risks.
4. ~~**Close `real_ohc`'s last review items**~~ **Done** (local agent, 2026-11-13; see Phase 2b).
   - **Degraded flag.** Now relative: a file is degraded when its median `sshaE` is more than `DEGRADED_SSHAE_RATIO` (1.12) times the median of its basin's files made over the 30 days before it, one every 5 days (`sshae_baseline`, six extra fetches per basin). The flag is `None` when there's no baseline, not `False`. Calibrated on 1,081 real files: every documented outage day reads 1.13× or more; outside them most flagged files are multi-day excursions in both basins at once (2026 days 049–054, 120–123, 262–268; 2024 days 312–318), which look like outages the docs didn't list.
   - **SHIPS regression.** The test reads the newest `lsdiaga_1982_*_sat_ts_7day.txt` linked from CIRA's development-data page (the data directory has no listing), finds AL 2021–2022 by bisecting record HEAD years, and skips with a message on a 404 or a missing link.
   - Not a fix, a choice to keep: the late-file check uses `date_created` and does nothing on the old chain, which has none. The reasons are in `decode_ohc`.

## Risks and open questions

- ~~**No OHC for 2021–2022.**~~ Not a risk: CoastWatch's older `na`/`np` chain covers 2021–2023 in full (Phase 0).
- **The forecast-lead input breaks train/serve parity.** Training must use GFS leads from the t−6 cycle, the same as serving. AWS `noaa-gfs-bdp-pds` holds 2021 onward, so this is covered.
- ~~**Version switch.**~~ The grid, units and values didn't change (Phase 0). What did: the file format (NetCDF-3 → HDF5) and, from 2025 day 85, the name's date, which makes test and live inputs a day fresher than training ones unless files are indexed by creation day.
- **Fusion trails GFS's own track: confirmed.** The pre-registered paired test (Phase 1, step 1) puts fusion 154 nm [112, 202] behind AVNI on Atlantic B at 48 h and 122 nm [89, 164] on C. So the steering spike (step 2) is the next test and the architectures are the fallback, as the exit rule says.
- **Training crops are centred on the final best track.** Live crops are centred on the working fix, so in serving the storm sits off the centre pixel by the working-fix error, which training never shows (Decision Log 67). Sizing it is inference-only: score the champions on validation crops re-centred on emulated positions.
- **An OHC outage inside the training years.** 2022 days 201–204 and 208–216 have degraded altimetry and no replacement; 69 EP training fixes read them (Phase 0).
- **Small samples.** With 58 Atlantic training storms and 18 in validation, per-basin gains can be noise. Report them per lead, with storm-level bootstrap intervals, before promoting.
- ~~**The wiki can't publish.**~~ Fixed 2026-11-13 (Handoff, item 3). Kept for the lasting fix below. The GitHub wiki was edited directly after its last publish (from `3bae888`), and `publish-wiki.sh` compares the wiki with `wiki/` at that commit, so it refuses every publish, including after the edits are copied into `wiki/` (done in `e83ee7b`). To unblock: once this branch is on `main`, revert the five direct commits in the wiki repository (`af8e4ac` through `2717b8f`) so it matches `wiki/` at `3bae888`, then run *Publish wiki*. Nothing is lost, because `wiki/` contains every one of those edits. A lasting fix is for the script to accept a wiki whose edits are already contained in `wiki/`.
- ~~**Open:** How far back does the AIFS open-data archive go?~~ Experimental AIFS to 2024-02-28 on AWS, operational from 2025-02-25 (Phase 1, step 3).
- **Open:** Is the CoastWatch latency stable during busy seasons? So far it's only been seen in Jul–Nov 2026.

## Sources

- [CoastWatch: Oceanic Heat Content product](https://coastwatch.noaa.gov/cwn/products/oceanic-heat-content-mixed-layer-depth-and-depths-20degc-and-26degc-isotherms.html)
- [CoastWatch: na14/2026 OHC files](https://coastwatch.noaa.gov/data/pub0012/coastwatch/ocean_heat/na14/2026/)
- [CIRA: SHIPS](https://rammb2.cira.colostate.edu/research/tropical_cyclones/ships/)
- [CIRA: SHIPS developmental data](https://rammb2.cira.colostate.edu/?p=8297)
- [CIRA: TC PRIMED](https://rammb2.cira.colostate.edu/research/ai/tcprimed)
- [ECMWF Newsletter #187: forecast performance 2025](https://www.ecmwf.int/node/37987)
- [jasonkolodziej/anemoi](https://github.com/jasonkolodziej/anemoi): `src/anemoi/data/sources.py`, `real_gridded.py`, `docs/input_sources_plan.md`, `docs/multi_basin.md`, `PLAN.md` §5

## Progress log

Newest first. Each entry names the commit or PR that carries the work.

- **2026-11-13.** Steering-along-track spike built (Phase 1, step 2):
  `data/steering.py`, `anemoi steering-cache`, `anemoi steering-spike`.
  Track advected through the GFS fields, leads to 48 h, no registry.
  Waiting on the cache job and the GPU run.
- **2026-11-13.** Dropout-0.1 retrain (Phase 0 spread item): diffusion and
  fusion v13 staged. Overall track spread now calibrated from 48 h; the
  recurving long-lead cases are still under 0.8 (96 h along 0.71, 120 h
  cross 0.70), so GEFS conditioning is the live option. Intensity spread
  and the 45% cone miss rate unchanged.
- **2026-11-13.** Fusion's pre-registered paired test (Phase 1, step 1),
  after #243 merged and CI rebuilt the image: fusion minus AVNI, Atlantic
  48 h, +154 nm [112, 202] on B and +122 nm [89, 164] on C. The ML layer
  subtracts value against GFS's own track; the steering spike (step 2) is
  next. Wiki unblocked and published from `0f721c1` (Handoff, item 3).
  Diffusion v12's `dropout` read: 0.0, so the spread fix to try first is a
  derived-only retrain with dropout 0.1, not GEFS.
- **2026-11-13.** Spread-skill for diffusion v12 measured (Phase 0): 50
  members, 607 windows. Under-dispersed at long lead (overall along-track
  96 h 0.76; recurving cross-track 72 h 0.77, 120 h 0.73) and in intensity
  from 48 h; the 120 h served cone misses 45%. Verdict `warranted`; the
  dropout-0.1 retrain comes before GEFS. JSON in `docs/backtests/`.
- **2026-11-13.** Local agent: `real_ohc`'s last two review items closed
  (Handoff, item 4). The degraded flag is relative to a trailing 30-day
  `sshaE` baseline, calibrated on 1,081 real files; the SHIPS test finds its
  edition and record window itself. Copilot's microwave finding on
  wiki Model-Catalog fixed (`8d07396`).
- **2026-11-13.** Cloud session stopped; open work handed to a local agent
  (Handoff, and a comment on PR #243). Older GFS and TC PRIMED research
  checked by independent skeptics: conclusions hold, details corrected
  (Phase 3). `GDAS_ARCHIVE_START` moved to 2021-03-22 18Z, the first valid
  time whose f006 `gfs_url` can fetch; no training fix changes (`8e5d9d3`).
  `real_ohc` built, matched to SHIPS SOHC at 555 cases, reviewed twice
  and fixed (`267b8ca`–`6763b70`); the degraded-flag calibration and the
  SHIPS test's edition name are open.

- **2026-11-13.** Desk research verified (Phase 0 version comparison,
  Phase 1 step 3, Phase 3): `na` and `na14` are one product; SHIPS becomes
  the OHC adapter's regression test, and its intensity baseline is in the
  a-decks; TC PRIMED is a go for Stage A diagnostics and verification, not
  yet for microwave; AIFS is a baseline, not an input. The OHC claim in
  `data/sources.py`, wiki Data-Sources and Decision Log #30 corrected
  (`72ef2c1`). Decision Log 66 and 67 (`58bc07e`).
- **2026-11-13.** Homogeneous baseline (Phase 1, step 1): `anemoi
  baseline-backtest` and the 2024 guidance numbers (`9431b9c`–`09fa1eb`).
  The OFCL join reproduces NHC's 2024 errors case for case. Fusion v12's
  registered mean puts it behind GFS's own track on Atlantic sample B; the
  paired test waits on an inference-only run of `validation-forecasts`.
- **2026-11-13.** Sources page and system graph read `used_by` (Phase 0,
  console half, `64714de`–`5189e29`), after the API review fixes
  (`7fe6207`–`5986802`).

- **2026-11-13.** OHC archive checked (Phase 0): 2021–2023 are complete in
  CoastWatch's older `na`/`np` chain, so OHC doesn't wait on a training
  archive. Posting delay measured: the D−2 rule holds for every cycle.
  Stage B corrected to 2021–2023, 116 storms (Phase 3).
- **2026-11-13.** OHC claim corrected and the date rule set (Phase 0). The
  "stops 2026-01-26" finding was AOML's HDB ERDDAP, not the state of the
  product; `data/sources.py` `sst_ohc`, wiki Data-Sources and Decision-Log #30
  now name OSPO's live CoastWatch feed. The ~36 h latency (read D−2) is
  `OHC_VALID_LAG` in `data.availability`.
- **2026-11-13.** Spread-skill check: the v12 ensemble's spread has never
  been measured, so the phase 0 item is a backtest run, not a lookup. The
  command and how to read it are under that item.
- **2026-11-13.** `wiki/` brought level with the published wiki (`e83ee7b`):
  Decision Log 61 to 65 and nine pages had been edited directly in the wiki
  and were missing here. Publishing stays blocked until the wiki is reset to
  its last published state (see "Risks and open questions").
- **2026-11-13.** `used_by` on the source registry and `/v1/sources`
  (`b672fca`), the API half of the Sources page fix. Reading the code for it
  corrected two rows of the table above: GEFS is read by nothing, and
  dropsonde and NDBC are verification-only by designation.
- **2026-11-13.** Plan added to the repo, written against `main` at `3838fcc`
  (#242). Phase 0 and the Phase 3 desk research started the same day.
