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

Only two of the ten registry sources feed a model today (commit `3838fcc`, 2026-11-12). `Role.OPERATIONAL` means a source is allowed to be read, not that a model reads it.

| Source | Adapter | Used by a model today | Plan |
| --- | --- | --- | --- |
| `besttrack_working` / `besttrack_final` | `live_atcf`, `hurdat2` | LSTM input; labels for all models | Keep |
| `gdas_gfs` (ERA5 in Stage A) | `real_gridded` | CNN, Transformer, GNN, PINN, but SST is a 28 °C constant | Add GFS forecast leads (Phase 1) |
| `sst_ohc`: SST half | `real_sst` (OISST v2.1) | Nothing | Phase 2a |
| `sst_ohc`: OHC half | None; 60 kJ/cm² placeholder in every stage | Nothing | Phase 2b, using OSPO's CoastWatch feed |
| `goes` | `real_goes` | Nothing (matches CNN input shape) | Phase 4 |
| `ensemble_perturbations` | `real_ensemble` (GEFS) | Spread backtest only | Phase 4, only if spread is too narrow |
| `microwave` | `real_microwave` | Nothing | Phase 4, as an optional masked input |
| `dropsonde`, `ndbc` | `real_dropsonde`, `real_ndbc` | Nothing | Verification only |

## Phase 0: Same-day fixes and checks

These answer the questions every later phase depends on, and each takes hours, not days.

- [ ] **Check the OHC training archive.** Look for `na`/`np` files for 2021–2022 (Stage B years) in CoastWatch THREDDS or NCEI. The `na14/` tree lists only 2024–2026, and the old `na/2025` and `na/2026` folders were empty. If the files aren't there, OHC either waits for Phase 3 or trains from SHIPS predictors.
- [ ] **Compare the `na` and `na14` versions.** Diff one overlapping day for grid, units and value range before training across the switch.
- [ ] **Correct the stale OHC claim.** Update the `sst_ohc` provider/notes in `data/sources.py`, Decision-Log #30 and wiki Data-Sources. The "stops 2026-01-26" result came from AOML's HDB ERDDAP. OSPO's CoastWatch `na14/2026/` has day 316 (Nov 12) posted Nov 13, with no gaps since Jul 17.
- [ ] **Set the OHC date rule.** Files post about 11:30 the day after their valid date (about 36 h latency), so a live cycle uses the file from D−2. Put that rule in `data.availability`.
- [ ] **Ship the Sources page fix** (input_sources_plan step 0). Rename the column to **Role** and add **Used by** from `/v1/sources`.
- [ ] **Pull phase 1's spread-skill and rank histograms per lead.** This settles the GEFS question with data you already have.

## Phase 1: Track experiment and baseline

This phase answers one question fast: is the 231 nm error a missing-input problem or a model problem? The models only see one GDAS f006 snapshot, so nothing tells them how the steering flow evolves over 48–120 h. SHIPS switched to forecast-model predictors in 1997 for the same reason.

1. **Homogeneous baseline (do first).** Score fusion, the raw GFS track (AVNO) and NHC's official forecast (OFCL) on the same cases from the ATCF a-decks. If fusion can't beat GFS's own track, the ML layer is subtracting value.
2. **Steering-along-track spike.** Use `gfs_url(valid_time, lead_hours)` to fetch the 850–200 mb steering layer at f006–f120, sampled along the GFS forecast track. Add it as Transformer conditioning in a throwaway branch, retrain Stage B only, and compare 48 h error per basin.
3. **AIFS feasibility check (in parallel).** Check how far back archived AIFS forecasts go, in what format, and their latency. ECMWF reports AIFS cuts TC position error substantially versus IFS but has a weak-intensity bias, so treat it as a track input only.

**Exit:** If step 2 moves 48 h AL error clearly toward the 70 nm gate, make forecast-lead steering a registry input (train/serve: GFS f-leads from the t−6 cycle). If not, go back to the architectures before adding more sources.

## Phase 2: Ocean inputs (runs alongside Phase 1)

This replaces the two constants with real ocean data, in two separate PRs and retrains so any intensity change traces back to one input.

**2a. OISST into `GriddedFields.sst`** (input_sources_plan step 1)

- [ ] Fill `sst` from `real_sst.sst_at` in `gdas_to_gridded_fields`, using the day before the valid time.
- [ ] Add a date-keyed SST side cache so the 5,095 GDAS GRIB crops don't need re-fetching.
- [ ] In the live cycle, flag late OISST instead of silently falling back.
- [ ] Retrain and compare per basin and lead. Expect gains mainly in EP intensity.

**2b. OSPO OHC into `GriddedFields.ohc`** (only after Phase 0 confirms the archive)

- [ ] Write a `real_ohc` adapter for `ohc_{na,np}14QG3_{yyyy}_{ddd}.nc` (0.25°, same grid as `GriddedFields`), with the D−2 date rule.
- [ ] Stage A has no OHC before 2012, so mask OHC in Stage A or feed it in Stage B only.
- [ ] SH, NI and WP-west storms fall outside the products' coverage: mask them and flag `missing:sst_ohc`.
- [ ] Retrain and compare against 2a's run. PI's `ohc_bonus` and `apply_cold_wake` start using real values here.

**Done when:** intensity skill improves or holds in AL and EP, and no basin's track gate regresses.

## Phase 3: More training data (desk research, start now)

Stage B trains on just 21 Atlantic storms (2021–2022), because `GDAS_ARCHIVE_START` is 2021-01-01. That limits how much any new input can show. This research needs no GPU time, so it runs from day one.

| Dataset | What it gives | Covers | Constraint | First step |
| --- | --- | --- | --- | --- |
| Older GFS/GDAS analyses (NCAR RDA, NCEI) | A longer Stage B, same flavor as serving | To confirm | Check it's the same 0.25° pgrb2 fields | Find the earliest year with matching messages |
| [SHIPS developmental data](https://rammb2.cira.colostate.edu/?p=8297) | Per-fix intensity predictors incl. ocean heat content; a DSHP/LGEM/RII baseline | AL, CP, EP through 2023 (7-day files) | Predictors come from the operational analysis used at the time | Load one basin file and join it to HURDAT2 fixes |
| [TC PRIMED](https://rammb2.cira.colostate.edu/research/ai/tcprimed) | Storm-centred microwave, IR and ERA5 diagnostics | 1987–2023, 3,552 storms | ERA5-based, so Stage A only | Size one season's download; map its microwave fields to `real_microwave`'s |
| AIFS forecast archive | Track input candidate (Phase 1, step 3) | To confirm | Archive length unknown | Find the open-data archive's start date |

## Phase 4: Later, each gated on evidence

- **GOES into the CNN.** Stage B only, since the archive starts in 2017. Needs a crop cache and a new `in_channels`, so it's a new model version. Gate: CNN with GOES beats CNN without it on Stage B validation per basin, within the cycle-time budget.
- **GEFS as diffusion conditioning.** Only if Phase 0's spread-skill check shows the ensemble is under-dispersed at recurvature.
- **Microwave.** Only as a masked optional input with a trained missing-data path. TC PRIMED (Phase 3) supplies the training years.
- **Gate re-derivation.** Set `track_error_72h_nm`, `track_error_120h_nm` and both intensity thresholds from NHC's verification report, and add a rapid-intensification metric (≥ 30 kt in 24 h).
- **New basins.** WP needs JTWC best track and Himawari imagery. NI and SH have no OSPO OHC product, so they use the masked OHC path from 2b.

## Console changes

Each phase that adds or changes an input changes what the console shows, so these ship in the same PR as the data change. Right now the console hard-codes which sources feed which model (`FEEDS` in `SystemGraph.svelte`), and the Sources page shows the role as if it were a status.

| Phase | Change | Files | API |
| --- | --- | --- | --- |
| 0 | Sources page: rename the column to **Role**, add **Used by** ("LSTM · labels", "verification", "not used yet"), and reword the subtitle so the badge reads as permission, not status | `routes/sources/+page.svelte` | Add `used_by: string[]` to `SourceOut` and `/v1/sources` |
| 0 | System graph: drive `FEEDS` from the same `used_by` mapping, and show every unused source (OISST, OHC, GEFS, microwave), not only GOES and buoy/dropsonde; let it scroll sideways on phones | `system/SystemGraph.svelte` | Same field |
| 0 | Mark dropsonde and NDBC as verification-only rather than unused | Sources page, graph | `used_by: ["verification"]` |
| 1 | Storm page: show fusion beside the GFS track (AVNO) and NHC's official forecast, per lead, for verified cycles | `routes/storms/[stormId]/+page.svelte` | Baseline errors per lead |
| 1 | Models/registry: per-basin 48 h track error against the 70 nm gate | `routes/models`, `routes/registry` | Already in tags (`EP/track_error_48h_nm`) |
| 1 | Graph: GFS node subtitle from "f006" to "f006 + forecast leads" once leads are an input | `SystemGraph.svelte` | None |
| 2 | New SST/OHC source node feeding CNN, Transformer, GNN and PINN | `SystemGraph.svelte` | `used_by` |
| 2 | Flag text for a late OISST file and for OHC outside product coverage (exact flag names TBD in `docs/api.md`) | `FlagsList.svelte` | New flags in the fixed vocabulary |
| 4 | Monitoring: rapid-intensification hit rate and per-lead spread-skill / rank histograms | `routes/monitoring/+page.svelte` | New metric endpoints |

The Phase 0 rows are the console half of input_sources_plan step 0 (partly done in #239).

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

The critical path is Phase 1: its week 2 result decides whether weeks 3–4 go to forecast-lead inputs or back to the architectures. OHC (2b) starts only once Phase 0 finds the 2021–2022 files.

## Risks and open questions

- **No OHC for 2021–2022.** Fallback: train with SHIPS OHC predictors, or keep OHC masked until Stage B reaches 2024+.
- **The forecast-lead input breaks train/serve parity.** Training must use GFS leads from the t−6 cycle, the same as serving. AWS `noaa-gfs-bdp-pds` holds 2021 onward, so this is covered.
- **Version switch.** If `na` → `na14` changed the grid or algorithm, training across it adds a distribution shift.
- **Small samples.** With 21 AL storms, per-basin gains can be noise. Report them per lead, with storm-level bootstrap intervals, before promoting.
- **Open:** How far back does the AIFS open-data archive go?
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

- **2026-11-13.** Plan added to the repo, written against `main` at `3838fcc`
  (#242). Phase 0 and the Phase 3 desk research started the same day.
