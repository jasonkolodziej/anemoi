# Input sources after multi-basin training

**Status:** planned. It starts once the multi-basin phase 1 run
(`docs/multi_basin.md`) has trained and been evaluated per basin. That run is
the baseline every step below is measured against.

## Where things stand

Eight sources have real, tested adapters in `src/anemoi/data/`. Two of them
feed the models today:

| Source | Adapter | Used by |
|---|---|---|
| Best track (HURDAT2, TC-Vitals) | `hurdat2`, `live_atcf` | LSTM input; labels for every model |
| GDAS/GFS f006 (ERA5 in Stage A) | `real_gridded`, `gdas_cache`, `era5_cache` | CNN, transformer, GNN, PINN |
| OISST v2.1 (SST) | `real_sst` | nothing |
| GOES-18/19 imagery | `real_goes` | nothing |
| GEFS perturbations | `real_ensemble` | nothing |
| SSMIS microwave | `real_microwave` | nothing |
| Dropsonde | `real_dropsonde` | nothing |
| NDBC buoys | `real_ndbc` | nothing |

`Role.OPERATIONAL` in `data/sources.py` means a source is *allowed* to be read
during a forecast cycle. It doesn't mean a model reads it, and the console's
Sources page currently shows the role as if it were a status (step 0).

A source is worth adding as a model input only if it meets both conditions:

1. **It exists for the storms we train on.** If it's missing in training, the
   model never learns to use it.
2. **It arrives in time for a live cycle.** If it's late in serving, the model
   is fed something different from what it trained on
   (`docs/train_serve_consistency.md`).

## Known gap: no real ocean signal in Stage B or serving

GDAS's atmospheric file has no SST or OHC. `gdas_to_gridded_fields` fills
`sst` with `GDAS_SST_PLACEHOLDER_C` and `ohc` with `OHC_PLACEHOLDER_KJ_CM2`,
both constants (`data/real_gridded.py`). ERA5 has real SST, so the pipeline is
inconsistent:

- **Stage A** pretrains on real SST.
- **Stage B** fine-tunes on a constant SST.
- **Live cycles** serve on that same constant.

Stage B and serving agree with each other, so nothing is broken. But none of
the models gets an ocean signal where it matters most: intensity, and the
cold wake `features.apply_cold_wake` models. OHC is a placeholder in every
stage.

## Order

### 0. Make the console say what's used (small, any time)

Partly done in #239 (2026-11-12): the storm badge reads "not verified" with
a title saying what verified means, and the storm list filters by basin.
Still open: the Sources page's Role / Used-by columns, the Architecture
page listing every unused source, and the phone layout.

- **Sources page.** Label the column **Role** and add **Used by**, served by
  `/v1/sources` from the same input mapping the system view draws (e.g.
  "LSTM · labels", "verification", "not used by a model yet").
- **Architecture page.** Show every unused source, not only GOES and
  buoy/dropsonde, or say it shows a subset.
- **Phone layout.** The system graph cuts off the model cards' right edge on
  narrow screens. Let it scroll sideways or scale to fit.

### 1. OISST into the SST field (first)

- **Why first.** Daily, global, back to 1981, about a day's latency: it
  passes both tests. It replaces a constant with real data in Stage B and
  serving, and the adapter is already written and was verified live on
  2026-09-22.
- **Work.**
  - Fill `GriddedFields.sst` from `real_sst.sst_at` in
    `gdas_to_gridded_fields`, using the day before the valid time (what a live
    cycle can actually have).
  - Add the field to the GDAS cache. Either rebuild `gdas_cache_f006` (5,095
    fixes, cheap), or add an SST side cache keyed by date so the GRIB crops
    are kept.
  - Have the live cycle read the same date rule, and flag a cycle whose
    OISST is late instead of falling back silently.
  - Leave OHC as a placeholder. OSPO's OHC product isn't implemented, and
    it's a separate step if SST pays off.
- **Measure.** Retrain and compare with the phase 1 baseline per basin and per
  lead. Expect the change to show in intensity, especially in the Eastern
  Pacific (sharp SST gradients, cold upwelling), more than in track.
- **Done when:** intensity skill improves or holds in every trained basin, and
  no basin's track gate regresses.

### 2. GOES imagery into the CNN (second, larger)

- **Why.** Cloud-top structure is the strongest real-time intensity signal we
  don't use. The CNN was designed as a satellite feature extractor
  (`models/cnn.py`), and PLAN.md §4 already lists real GOES crops as the step
  that replaces `data.satellite`'s synthetic ones.
- **Catches.**
  - The archive starts in 2017 (GOES-16/17), so it can't cover Stage A's
    1980–2025 ERA5 years. GOES goes into **Stage B only**, or as its own
    branch that's masked in Stage A.
  - East and Central Pacific storms need GOES-West, and the satellite changes
    over the archive (GOES-17 → 18, GOES-16 → 19). Calibrate across that
    handover.
  - It needs a new cache (storm-relative crops per fix), and the CNN's
    `in_channels` changes, so `arch_params` change and existing versions keep
    serving until a new one is promoted.
- **Done when:** the CNN with GOES beats the CNN without it on Stage B
  validation in each basin, at a cycle time inside `docs/cycle_timing.md`'s
  budget.

### 3. GEFS as diffusion conditioning (only if needed)

- `build_diffusion(extra_conditioning_dim=...)` already exists for this
  (PLAN.md §5, "Ensemble dispersion at recurvature").
- **Gate.** Do it only if the phase 1 run's per-lead spread-skill ratio and
  rank histograms show the ensemble is under-dispersed, at recurvature in
  particular. If spread is already calibrated, GEFS is cost without a
  benefit.

### 4. Microwave as an optional input (later)

- It gives high-value inner-core structure for rapid intensification, but
  it's opportunistic: an overpass misses most cycles (PLAN.md §3,
  `InputStatus.opportunistic`).
- Only as a masked, optional input with a missing-data path trained in. A
  model must never depend on it being there.

### Not model inputs: dropsonde and NDBC buoys

- **Dropsonde** only exists where recon flies: mostly Atlantic storms near
  land. It's too sparse and too biased by where planes go to train on.
- **NDBC buoys** are sparse and coastal. The GNN was framed for station and
  buoy networks, but it learns from the regular gridded crop today, and a
  handful of buoys wouldn't change that.
- **Use them for verification.** Check analysed and forecast intensity near
  landfall, and sanity-check TC-Vitals. Show that role on the Sources page
  (step 0).

## Each step is its own change

Each source lands with its own PR and retrain, compared with the run before
it, so a gain or regression traces back to one input. Promotion goes through
the same per-basin gates as phase 1 (`docs/multi_basin.md`, "Evaluation and
promotion").
