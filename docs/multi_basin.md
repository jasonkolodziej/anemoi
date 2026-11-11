# Training and forecasting beyond the Atlantic

**Status:** proposal, with phase 0 in this change. Every model today is
trained on the Atlantic alone. Storms from other basins are forecast, but
out of distribution, and flagged `basin_untrained:<basin>`.

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

- **Per-basin metrics on every version.** Record track and intensity error at
  each lead, per basin (`track_error_48h_nm:EP`, …), next to today's overall
  metrics.
- **Gates.**
  - No regression in the Atlantic against the current champion. The Atlantic
    stays the reference basin.
  - Each newly enabled basin must beat a persistence/climatology baseline at
    48 h on its own test seasons.
  - A basin enters `trained_basins` only through a run that trained on it. In
    phase 1 the console badge moves from "trained on" to "passed its gate"
    (`verified_basins`), so a basin the models saw but don't yet forecast well
    stays flagged.
- **Test seasons per basin.** Split boundaries are derived per basin from its
  own newest final season, as `season_boundaries` already does from HURDAT2.

## Products

- **Cone radii per basin.** `ensemble.climatological_cone_nm` becomes keyed by
  basin. NHC publishes Atlantic and Eastern Pacific radii. For the others,
  use the two-thirds quantile of this system's own verified errors, which the
  calibration audit (#166) already measures.
- RI (≥ 30 kt in 24 h) and landfall need no change.

## Phases

**0 (this change).**
- Training records the basins it used (`trained_basins` tag).
- The API's `trained_basin` and the cycle's `basin_untrained:<basin>` flag
  come from what every Group 1 champion trained on (`ModelRegistry
  .trained_basins`). A champion registered before the tag counts as
  Atlantic-only.
- Nothing changes for today's Atlantic-only models. Once phase 1's models
  are promoted, Eastern Pacific storms lose the badge with no code change.

**1: Eastern and Central Pacific (NHC, Northern Hemisphere).**
- `anemoi hurdat2-fetch` also fetches the newest NE/N-Central Pacific file;
  training reads both.
- Add `data.basins` in `configs/curriculum.yaml` to choose them.
- Basin input (rule 2), per-basin metrics and gates, per-basin cone radii.
- **Done when** every champion is tagged `AL,CP,EP`, the Eastern Pacific gate
  passes, and the Atlantic gate shows no regression.

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
