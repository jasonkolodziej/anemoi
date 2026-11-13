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
| `sst_ohc`: OHC half | None; 60 kJ/cm² placeholder in every stage | Nothing | Phase 2b, using OSPO's CoastWatch feed (archive from 2020) |
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
    - **Blank files.** `na14` 2025 day 199 is all zeros, coordinates included. Reject a file whose coordinates aren't the expected arrays or that has no fill cells.
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
- [ ] **Pull phase 1's spread-skill and rank histograms per lead.** This settles the GEFS question with data you already have.
  - Not a lookup: it needs one run. Nothing measures the v12 ensemble's spread. Diffusion training scores only the ensemble mean, so the registry, R2 and the live calibration endpoint hold point errors and cone containment, not spread-skill or rank histograms. Every per-lead table in the repo is for diffusion v6 or v7 (20 members, 637 Atlantic windows from 2023).
  - The run, on the CPU training job (about 10 minutes for the September runs):
    `gcloud run jobs execute anemoi-train-schedule --region us-central1 --task-timeout 3600s --args=spread-backtest,--hurdat2,/app/data/hurdat2-atl.txt,--gdas-cache-dir,/cache/gdas_cache_f006,--registry-root,/tmp/registry,--members,50,--out,/cache/spread-backtest-diffusion-v12-m50.json`
    then copy the JSON into `docs/backtests/`. `--out` under `/cache` and the timeout are untested additions to the documented command.
  - Read `dropout` in diffusion v12's `arch_params` tag first. `--diffusion-dropout` defaults to 0.0 and the documented GPU job doesn't set `DIFFUSION_DROPOUT`. Dropout 0.1 is what closed the long-lead under-dispersion in September (v7 0.45 to 0.73 at 72 to 120 h, v8 0.86 to 1.04). v12's training set is about three times that one, so dropout 0.0 need not reproduce v7's result.
  - Until the run exists the GEFS gate is undecided, so GEFS doesn't start. The last healthy model measured (v8, 50 members, 2026-09-29) read `not_warranted`. If v12's long-lead track ratios are below 0.8, try a derived-only retrain with dropout 0.1 before GEFS; GEFS is the live option only if under-dispersion survives that and sits in the recurving cases.
  - The backtest has no per-basin split, and validation is now the 2024 season pooled across AL, EP and CP, so one basin can hide another. `calibrate()` already takes a `case_filter`; a per-basin breakdown is a small code change.

## Phase 1: Track experiment and baseline

This phase answers one question fast: is the 231 nm error a missing-input problem or a model problem? The models only see one GDAS f006 snapshot, so nothing tells them how the steering flow evolves over 48–120 h. SHIPS switched to forecast-model predictors in 1997 for the same reason.

1. **Homogeneous baseline (do first).** Score fusion, the raw GFS track (AVNO) and NHC's official forecast (OFCL) on the same cases from the ATCF a-decks. If fusion can't beat GFS's own track, the ML layer is subtracting value.
   - **Done for guidance; fusion's per-case run is open.** `anemoi baseline-backtest` (`5ccaf90` and the commits around it; Decision Log 66) scores NHC's a-deck techniques on exactly the registry's 2024 validation windows: 607 windows, whose persistence reproduces the registered 335 / 253 / 186 nm. The OFCL join reproduces NHC's own 2024 errors case for case (Atlantic 48 h: 214 of 214, 45.44 against 45.41 nm). Result: `docs/backtests/2026-11-13-homogeneous-baseline-val2024.json`.
   - Atlantic, 48 h, on the cases every technique has (sample B: 242 cases, 15 storms): OFCL 57, AVNI (the GFS track a cycle has) 66, AVNO 58, EMXI/EMX2 59, CLIPER5 248 nm. On NHC's tropical-only sample C (190 cases): 44 / 53 / 48 / 48 / 206.
   - **Fusion's registered mean already answers most of it.** Fusion v12's 231 nm is a mean over all 255 Atlantic windows. To tie AVNI on sample B, the 13 windows B leaves out would need a mean error of 3,304 nm, where persistence scores 434. So on Atlantic B fusion is behind GFS's own track; its registered mean is 3.5× AVNI's. On C it would need 752 nm on 65 windows (persistence 470): very likely behind. East Pacific: 359 nm needed on 36 windows for B (persistence 283), so unlikely; C is open. Central Pacific is one storm (Hone) and decides nothing.
   - **The pre-registered test hasn't run.** It is fusion minus AVNI, Atlantic 48 h, on B and C, with a storm-block interval, and it needs fusion's per-case forecasts. That is an inference-only job on the training machine: it loads fusion v12 and its five Group 1 checkpoints, and trains, registers and promotes nothing. Once `5ccaf90` is on `main` and CI has rebuilt the image:
     `gcloud run jobs execute anemoi-train-schedule --region us-central1 --task-timeout 3600s --args=validation-forecasts,--hurdat2,/app/data/hurdat2-atl.txt,--gdas-cache-dir,/cache/gdas_cache_f006,--registry-root,/tmp/registry,--fusion-version,12,--out,/cache/backtests/validation-forecasts-fusion-v12-val2024.json`
     Then score it here with `anemoi baseline-backtest ... --model-forecasts <that file>` (docker/cloud-run-training/README.md, One-off commands). Check that the job reports the registered and recomputed metrics consistent and `n_without_forecast` = 0.
   - Also found: the training emulator's working track is noisier than NHC's real one. On these cases its 6 h motion error is 20.8 nm RMS against CARQ's 10.3, and its position is 13.0 nm from the best track against CARQ's 5.3. That is a case for re-calibrating `working_track_noise`, as a training decision of its own.
2. **Steering-along-track spike.** Use `gfs_url(valid_time, lead_hours)` to fetch the 850–200 mb steering layer at f006–f120, sampled along the GFS forecast track. Add it as Transformer conditioning in a throwaway branch, retrain Stage B only, and compare 48 h error per basin.
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

- [ ] Write a `real_ohc` adapter for `ohc_{na,np}QG3_{yyyy}_{ddd}.nc` (2020–2024) and `ohc_{na,np}14QG3_{yyyy}_{ddd}.nc` (2024 on), with the D−2 date rule. It must read NetCDF-3 and HDF5 (add scipy to the `gridded` extra), index v1r1 files by creation day, reject blank files, place NP then NA on the global grid, and mask the 2022 outage days (Phase 0, version comparison).
- [ ] Regression-test it against SHIPS' SOHC: on 557 open-ocean Atlantic cases of 2021–2022, SOHC equals the bilinear value at the best-track centre of the file named for the day before, within 0.5 kJ/cm² (Phase 3).
- [ ] Stage A has no OHC before 2012, so mask OHC in Stage A or feed it in Stage B only.
- [ ] SH, NI and WP-west storms fall outside the products' coverage: mask them and flag `missing:sst_ohc`.
- [ ] Retrain and compare against 2a's run. PI's `ohc_bonus` and `apply_cold_wake` start using real values here.

**Done when:** intensity skill improves or holds in AL and EP, and no basin's track gate regresses.

## Phase 3: More training data (desk research, start now)

Stage B trains on 2021–2023 (116 storms: 58 Atlantic, 58 Eastern Pacific), validates on 2024 (33 storms) and tests on 2025 (33), because `GDAS_ARCHIVE_START` is 2021-03-22 18Z (the first valid time whose f006 the reader can fetch; no 2021 fix comes earlier) and the splits move with the newest HURDAT2 season (`data.splits.season_boundaries`, N = 2025). The plan first said 21 Atlantic storms from 2021–2022, copied from `docs/multi_basin.md`; the split in the code says otherwise. That still limits how much any new input can show. This research needs no GPU time, so it runs from day one.

| Dataset | What it gives | Covers | Constraint | First step |
| --- | --- | --- | --- | --- |
| Older GFS/GDAS analyses (NCAR RDA, NCEI) | A longer Stage B, same flavor as serving | To confirm | Check it's the same 0.25° pgrb2 fields | Find the earliest year with matching messages |
| [SHIPS developmental data](https://rammb2.cira.colostate.edu/?p=8297) | Per-fix intensity predictors incl. ocean heat content | AL, CP, EP 1982–2025 (7-day files, posted 2026-10) | Predictors come from the operational analysis used at the time; no forecasts in the files | **Done.** Not needed as an OHC fallback. Its SOHC is the same CoastWatch product, so it becomes the OHC adapter's regression test (2b). It joins on (storm, synoptic time): 407 of 583 Atlantic fixes in 2021, 295 of 449 in 2022; every miss is EX/LO/DB. NOHC ends 2024-09-17. The DSHP/LGEM baseline is in the a-decks (SHIP, DSHP, LGEM every cycle, 0–168 h) and RI probabilities in the e-decks, so the intensity baseline reads those |
| [TC PRIMED](https://rammb2.cira.colostate.edu/research/ai/tcprimed) | Storm-centred microwave, IR and ERA5 diagnostics | Final 1987–2024 all basins, 2025 AL and CP; 3,657 storms | ERA5-based diagnostics; no OHC | **Done.** ERA5 diagnostics and IR: go for Stage A. Microwave: no-go for now, because `real_microwave` serves RSS's retrieved wind, vapour, cloud and rain on a daily grid, while TC PRIMED has calibrated brightness temperatures and GPROF on swaths; only SSMIS F16–F18 are in both. Its preliminary files can't be a live feed. Verification: go for final seasons. 2022 is 73 GB for all basins |
| AIFS forecast archive | Track baseline (Phase 1, step 3) | Experimental from 2024-02-28, operational from 2025-02-25 | Nothing for 2021–2023 | **Done.** A baseline now (EAIO/EAII in NHC's 2025 decks), not a trained input |

## Phase 4: Later, each gated on evidence

- **GOES into the CNN.** Stage B only, since the archive starts in 2017. Needs a crop cache and a new `in_channels`, so it's a new model version. Gate: CNN with GOES beats CNN without it on Stage B validation per basin, within the cycle-time budget.
- **GEFS as diffusion conditioning.** Only if Phase 0's spread-skill check shows the ensemble is under-dispersed at recurvature.
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

The cloud session can't do these three tasks: two need the training machine and one needs write access to the wiki repository. A local agent with `gcloud` and wiki access takes them. Both training-machine jobs load existing checkpoints only: they don't train, register or promote anything.

1. **Fusion's per-case forecasts** (Phase 1, step 1).
   - Needs: this branch merged to `main` (for `5ccaf90`) and the training image rebuilt by CI.
   - Run the `validation-forecasts` command in Phase 1, step 1.
   - Check that the job reports the registered and recomputed metrics as consistent, and that `n_without_forecast` = 0.
   - Score it with `anemoi baseline-backtest ... --model-forecasts <file>`, using the decision rule in Decision Log 66: fusion − AVNI, Atlantic 48 h, samples B and C, storm-block bootstrap.
   - Commit the JSON under `docs/backtests/` and record the result in Phase 1, step 1 and the progress log.
2. **Spread-skill for diffusion v12** (Phase 0).
   - First read `dropout` in v12's `arch_params` tag.
   - Run the 50-member `spread-backtest` command in Phase 0.
   - Copy the JSON into `docs/backtests/` and record the long-lead track ratios against the 0.8 gate.
3. **Unblock the wiki.**
   - Needs: this branch merged to `main`.
   - In the wiki repository, revert `af8e4ac` through `2717b8f`, then run *Publish wiki*. The full reasoning is in the wiki entry under Risks.

## Risks and open questions

- ~~**No OHC for 2021–2022.**~~ Not a risk: CoastWatch's older `na`/`np` chain covers 2021–2023 in full (Phase 0).
- **The forecast-lead input breaks train/serve parity.** Training must use GFS leads from the t−6 cycle, the same as serving. AWS `noaa-gfs-bdp-pds` holds 2021 onward, so this is covered.
- ~~**Version switch.**~~ The grid, units and values didn't change (Phase 0). What did: the file format (NetCDF-3 → HDF5) and, from 2025 day 85, the name's date, which makes test and live inputs a day fresher than training ones unless files are indexed by creation day.
- **Fusion trails GFS's own track.** Its registered Atlantic 48 h error (231 nm) is about 3.5× AVNI's 66 nm on the same validation cases (Phase 1, step 1). The pre-registered paired test still needs fusion's per-case forecasts, an inference-only run on the training machine. If it confirms, the steering spike (step 2) is the next test and the architectures are the fallback, as the exit rule says.
- **Training crops are centred on the final best track.** Live crops are centred on the working fix, so in serving the storm sits off the centre pixel by the working-fix error, which training never shows (Decision Log 67). Sizing it is inference-only: score the champions on validation crops re-centred on emulated positions.
- **An OHC outage inside the training years.** 2022 days 201–204 and 208–216 have degraded altimetry and no replacement; 69 EP training fixes read them (Phase 0).
- **Small samples.** With 58 Atlantic training storms and 18 in validation, per-basin gains can be noise. Report them per lead, with storm-level bootstrap intervals, before promoting.
- **The wiki can't publish.** The GitHub wiki was edited directly after its last publish (from `3bae888`), and `publish-wiki.sh` compares the wiki with `wiki/` at that commit, so it refuses every publish, including after the edits are copied into `wiki/` (done in `e83ee7b`). To unblock: once this branch is on `main`, revert the five direct commits in the wiki repository (`af8e4ac` through `2717b8f`) so it matches `wiki/` at `3bae888`, then run *Publish wiki*. Nothing is lost, because `wiki/` contains every one of those edits. A lasting fix is for the script to accept a wiki whose edits are already contained in `wiki/`.
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
