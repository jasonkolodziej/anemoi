# Training and forecasting beyond the Atlantic

**Status:** phase 1 done for the Eastern Pacific (2026-11-12): every Group 1
champion is trained and verified in AL and EP, none regressed on the
Atlantic, and EP storms are served in distribution. The Central Pacific
waits for Stage B training storms (phase 1 below). Storms from any other
basin are forecast, but out of distribution, and flagged
`basin_untrained:<basin>` until models trained on them pass their gates.

First multi-basin champions (48 h track error, nm; persistence in brackets):

| Model | AL | EP | CP (36 windows) |
|---|---|---|---|
| lstm v12 | 271 (338) | 176 (252) | 88 (186) |
| cnn v8 | 225 (338) | 152 (252) | 121 (186) |
| transformer v8 | 261 (338) | 139 (252) | 118 (186) |
| gnn v7 | 291 (338) | 164 (252) | 111 (186) |
| pinn v7 | 299 (334) | 197 (257) | 418 (222) |
| diffusion v12 | 293 (335) | 191 (253) | 152 (186) |
| fusion v12 | 231 (335) | 136 (253) | 69 (186) |

**Recommendation in one line:** keep **one model per architecture**, train it
on every basin with storms mirrored into one hemisphere and the basin given as
an input, and gate promotion **per basin**. Bring the basins in by agency and
hemisphere: Eastern/Central Pacific first, then the Western Pacific and North
Indian Ocean, then the Southern Hemisphere.

## Where the Atlantic assumption lives today

| Layer | Today | Where |
|---|---|---|
| Final labels | NHC's Atlantic HURDAT2 only. The listing picker skips `hurdat2-nepac-…` on purpose. | `data/hurdat2_source.py` (`_NAME_RE`) |
| Which storms the API lists | HURDAT2 plus NHC's live feed: AL, EP and CP. Western Pacific, North Indian and Southern Hemisphere storms are never listed. | `data/live_atcf.py`, `api/real_state.py` |
| "Trained basin" | Was the constant `{"AL"}`. **Now read from the registry** (phase 0, below). | `tracking/registry.py` (`trained_basins`) |
| Track inputs | Storm-relative displacements, which carry no basin, but north displacement and latitude carry the hemisphere's sign. | `data/storm_relative.py` |
| Environment inputs | 850 mb relative vorticity is positive for a northern cyclone and negative for a southern one. Fields are cropped north-up. | `data/features.py`, `data/real_gridded.py` |
| Gridded fields | ERA5 and GFS are global. The crop wraps at the 0/360 seam, so the dateline is already handled there. | `data/real_gridded.py` (`_crop_box`) |
| Physics loss | Kaikias's hemisphere residual uses the sign of the Coriolis parameter, so it is already correct in both hemispheres. | `models/pinn.py` |
| Splits | By season. Southern Hemisphere seasons run July to June, so "season" needs the agency's own label there. | `data/splits.py` |
| Cone | NHC's Atlantic two-thirds radii. | `configs/inference.yaml` (`ensemble.climatological_cone_nm`) |
| Satellite | GOES-East by default; GOES-West on request. | `data/real_goes.py` |
| Console | One badge for an untrained basin. The map isn't checked for tracks that cross the dateline. | `StormCard.svelte`, `ConeMap.svelte` |

## Decision: one model per architecture, not one per basin

**Per basin** would mean 5 Group 1 models, plus fusion and diffusion, for each
of 6 basins: 42 registered models. Each basin's fusion and diffusion would be
pinned to that basin's five through `latent_signature`. Each basin would also
be trained on its own fraction of an already thin archive. Stage B, the GDAS
fine-tune, trains on the 2021–2022 seasons: 21 Atlantic storms. The Eastern
Pacific, Western Pacific and Southern Hemisphere each add as many or more a
season.

**One global model** shares what is the same everywhere: beta drift, steering
by the environmental flow, recurvature, and the response of intensity to SST,
shear and moisture. It keeps the registry, pinning and fusion as they are.
What differs by basin, mostly climatology and land, goes in as an input and
is checked by a per-basin gate rather than by separate models.

**Revisit if** a per-basin gate shows one basin regressing in a way an input
can't fix. The fallback is then a per-basin head on the shared model, not
separate models.

### Three rules that make one model work

1. **Mirror the Southern Hemisphere into the Northern.** At the input, set
   latitude to −latitude and the north displacement to −north. Flip gridded
   fields north to south, and negate meridional wind and vorticity. Negate
   the model's predicted north displacement before turning it back into
   positions. Do this once, in the feature builders that both training and
   live inference use (`real_run_*` and `real_inference_live`), so training
   and serving can't drift apart. Northern storms are unchanged.
2. **Give the basin as an input.** Add a one-hot of the six ATCF basins to
   each model's static features: the LSTM's sequence, a constant channel for
   the CNN/Transformer, a node feature for the GNN, and fusion's context. An
   unknown basin is all zeros, never an error.
3. **One wind convention: 1-minute sustained.** NHC (HURDAT2) and JTWC both
   report 1-minute winds. The other regional centres (JMA, BoM, IMD,
   Météo-France) report 10-minute winds, roughly 7–12% lower depending on the
   conversion used. Labels outside
   NHC's basins come from JTWC's columns in IBTrACS (`USA_*`) and never from
   the regional centres' columns. Otherwise the same storm would be "weaker"
   in one basin.

## Data by basin

| Basin | Final labels | Live (working) fixes | Notes |
|---|---|---|---|
| AL | HURDAT2 Atlantic (NHC) | NHC `CurrentStorms.json` + TC-Vitals | Today. |
| EP, CP | HURDAT2 NE/N-Central Pacific (NHC) | Same NHC feed, already live | Same agency, format and storm ids. The parser already reads them. |
| WP, IO | IBTrACS v04, `USA_*` columns (JTWC) | NCEP's global TC-Vitals, which relays JTWC | Verify the feed's path and terms before phase 2. `USA_ATCF_ID` gives ATCF ids like `WP022024`. |
| SH | IBTrACS v04, `USA_*` (JTWC) | Same | Season July–June. Mirrored (rule 1). |

IBTrACS is NOAA/NCEI's public-domain merge of every agency's best tracks.
JTWC's final tracks reach it about a year after a season, with provisional
positions before that. The newest season used for labels must be one JTWC has
finalised, as `hurdat2_last_season` already is for NHC.

GDAS/GFS and ERA5 cover the globe, so no new gridded source is needed. The
gridded caches grow with the storm count. The streaming dataloader
(`docs/streaming_dataloader.md`) already bounds memory.

## Evaluation and promotion

- **Per-basin metrics on every version** (`metrics/basin.py`). Each basin's
  own track and intensity error at each lead (`EP/track_error_48h_nm`), its
  training and validation sample counts (`EP/train_samples`), and what
  persistence scores (`EP/persistence_track_error_48h_nm`) on exactly the
  windows and leads the model was scored on -- a gridded model skips windows
  with no cached field, and persistence skips the same ones
  (`real_run.StageWindow.persistence`).
- **Verified.** A model is verified in a basin when it trained there and
  beats persistence -- holding the storm's last motion and wind -- there on
  the promotion metric (`metrics.basin.verified_basins`; the tags and the
  promotion rules both read it). Registered as the `verified_basins` tag. The
  console badge and the `basin_untrained` flag read it: a basin is in
  distribution once every Group 1 champion is verified in it
  (`ModelRegistry.verified_basins`).
- **Promotion** (`monitoring.yaml` `promotion.reference_basin: AL`,
  `new_basin_tolerance: 0.05`):
  - The candidate is compared with the incumbent on the Atlantic's storms
    alone, and the thresholds are read there.
  - It must stay verified in every basin the incumbent is verified in.
  - If it is verified in a basin the incumbent isn't, it may be up to 5%
    worse on the Atlantic; otherwise it must beat the incumbent outright.
    5% is a starting value: re-derive it from the spread of repeat runs.
- **Test seasons per basin.** Split boundaries are derived per basin from its
  own newest final season, as `season_boundaries` already does from HURDAT2.

## Products

- **Cone radii per basin.** `ensemble.climatological_cone_nm` becomes keyed by
  basin. NHC publishes Atlantic and Eastern Pacific radii. For the others,
  use the two-thirds quantile of this system's own verified errors, which the
  calibration audit (#166) already measures.
- RI (≥ 30 kt in 24 h) and landfall need no change.

## Phases

**0 (built).**
- The registry reads which basins a version trained on from its
  `trained_basins` tag. Phase 1's runners set it from the examples training
  actually consumed, not the archive they were given (which also holds
  held-out seasons and storms a model may skip).
- The API's `trained_basin` and the cycle's `basin_untrained:<basin>` flag
  come from what every Group 1 champion trained on (`ModelRegistry
  .trained_basins`), re-read within the registry's refresh interval. A
  champion without the tag counts as Atlantic-only, as every version so far
  is.
- Nothing changes for today's Atlantic-only models. Once phase 1's models
  are promoted, Eastern Pacific storms lose the badge with no code change.

**1: Eastern and Central Pacific (NHC, Northern Hemisphere). Built.**
- `configs/curriculum.yaml` `data.basins: [AL, EP, CP]`.
- `anemoi hurdat2-fetch` fetches the Atlantic and the Northeast Pacific
  archives into one file (all or nothing); training reads the configured
  basins from it.
- Basin input (rule 2) on all five Group 1 models (`training/basin_input.py`).
  Its columns are recorded per version (`basin_inputs` tag), and serving
  builds inputs from that tag, so a version from before it -- no basin
  columns -- is served exactly as before.
- Per-basin metrics, persistence baseline, verified basins and the
  promotion rules above.
- Per-basin cone radii: a cycle draws its climatological cone (the fallback
  and the underdispersion check) from its storm's basin, NHC's one column
  for the Eastern and Central North Pacific (`configs/inference.yaml`
  `ensemble.climatological_cone_nm_by_basin`; 138 vs 200 nm at 120 h in
  2026). Other basins keep the Atlantic's until NHC-equivalent radii are
  chosen for them.
- **To run it:**
  1. `anemoi hurdat2-fetch --out <path>` (the images and the training job do
     this already).
  2. `anemoi gdas-cache` and `anemoi era5-cache` for the new storms. A
     gridded model trains only where fields are cached: without this step
     the CNN, Transformer, GNN and PINN train on the Atlantic alone, and say
     so (`trained_basins`).
  3. A full training run. The Atlantic-only champions stay until a
     candidate passes the rules above.
- **Done when** every champion is verified in `EP` (and `CP`, given enough
  storms) and none regressed on the Atlantic.
- **CP waits for its storms (decided 2026-11-12).** A basin counts as
  trained from Stage B's training samples, and Stage B's training seasons
  (2021-2023 for an archive ending in 2025) hold no storm with a CP id:
  CP ids go only to storms that form there, one in 2024 and two in 2025.
  Eleven EP storms in those seasons did track into Central Pacific waters,
  so the models see its geography, but they count as EP. Stage A's 1,148
  ERA5 CP fixes aren't counted: it's the stage the served weights are
  fine-tuned away from, and counting it would verify CP on 36 validation
  windows. Nothing to change: the boundaries roll with the newest final
  season, so the 2024 CP storm enters Stage B's training split once the
  2026 season is final, and CP is gated like any basin from then.

**2: Western Pacific and North Indian Ocean (JTWC via IBTrACS).**
- An IBTrACS loader using the `USA_*` columns only (rule 3).
- Global TC-Vitals in the live feed, deduplicated against NHC's.
- Verify feature builders and the console map on dateline-crossing tracks.
- Optionally Himawari for the Western Pacific.

**3: Southern Hemisphere.**
- Mirroring (rule 1), split boundaries using the July–June season, SH cone
  radii.

**4: Console.**
- Basin filter on the storm list, a dateline-safe map, per-basin cone, and
  the badge reading `verified_basins`.

## Risks and open questions

- **Atlantic dilution.** More Pacific data could cost Atlantic skill. This is
  why the Atlantic gate blocks promotion, and why basin is an input.
- **Live feed outside NHC's basins.** NCEP's global TC-Vitals path, latency
  and terms of use need checking before phase 2. JTWC has no JSON index like
  NHC's.
- **Compute.** Training samples grow about fivefold over the Atlantic alone
  by phase 3, and live cycles run most of the year (the Western Pacific peaks
  August–October, the Southern Hemisphere January–March).
- **For the maintainer to decide:**
  - Confirm one global model per architecture.
  - Confirm the Atlantic stays the basin that can block a promotion.
