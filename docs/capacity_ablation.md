# Capacity-vs-sample-size ablation

PLAN.md §5 "Sample size" (#9). Recorded run, 2026-09-16.

## The question

Roughly 1,200 storms / ~16k training-split synoptic fixes exist in the real
HURDAT2 Atlantic archive (1980-2019, per `data.splits.DEFAULT_BOUNDARIES`).
That's thin for a 6-layer, 256-dim transformer. Before committing GPU-months
to Stage A/B training at that capacity, PLAN.md calls for measuring whether
the capacity is justified rather than assuming it.

## What this run measures, and what it does not

This is a **track-only, single 6h-ahead step, LSTM-capacity** ablation --
not a direct measurement of the transformer's gridded-field, multi-lead
task. The LSTM is architecturally the closest fit to a storm-relative track
sequence and by far the cheapest model to sweep a capacity/data grid on; a
transformer-specific version of this experiment needs a real per-fix
gridded-field training set (ERA5/GDAS), which is a heavier data-assembly
task tracked separately. Treat this as a real, honest measurement of the
thin-archive concern on the model it was cheapest to run it on -- not a
transformer verdict by proxy.

## Data and method

- **Archive:** real NHC HURDAT2, `hurdat2-atl-1851-2023-042624.txt`
  (<https://www.nhc.noaa.gov/data/hurdat/>), parsed with
  `data.hurdat2.parse_hurdat2_file`. Parsing this file surfaced and fixed a
  real bug: a handful of extratropical-remnant entries record longitude past
  180 degrees west (e.g. `354.5W`, tracked into the Norwegian Sea) rather
  than switching to "E"; `_parse_latlon` now wraps through
  `geo.wrap_longitude`.
- **Split:** `data.splits.DEFAULT_BOUNDARIES` storm-wise, chronological --
  train 1980-2019 (561 storms, 16,474 fixes), val 2020-2022 (68 storms, 1,884
  fixes). The test split (2023-2025) was never touched, per the project's
  metered test-set policy.
- **Input:** `data.storm_relative.storm_relative_sequence` -- 4 x 6h (24h) of
  storm-relative history (east/north displacement in nm, wind, pressure,
  absolute latitude) per sample.
- **Augmentation:** `data.besttrack.augment_track` -- each training storm is
  independently re-emulated (`WorkingTrackNoise` defaults) 3 times
  (`n_augment=3`), multiplying effective training sample count without
  inventing storms that didn't happen. The label always comes from the real
  FINAL track, never the noisy input (`test_build_samples_wind_label_...`
  in `tests/test_capacity_ablation.py` locks this in).
- **Target:** east/north displacement (nm) and wind (kt) from the window's
  last known (working-quality) fix to the true next fix, 6h later.
- **Training:** full-batch Adam, 30 epochs, standardised (z-scored) inputs
  and targets, `training.device.get_device()` (ran on Apple Silicon MPS).
- **Grid:** `hidden_dim in {8, 16, 32, 64, 128}` x
  `sample_fraction in {0.10, 0.25, 0.50, 1.00}` of the training storms.

Reproduce with `training.capacity_ablation.run_capacity_ablation(tracks)`
given a real `list[Track]` from `parse_hurdat2_file`, or
`anemoi ablation --hurdat2 <path>` (see `cli.py`).

## Results

| hidden_dim | sample_fraction | n_storms | n_train | n_val | train_loss | val_loss |
|---|---|---|---|---|---|---|
| 8 | 0.10 | 56 | 4455 | 1544 | 0.7962 | 0.8163 |
| 16 | 0.10 | 56 | 4455 | 1544 | 0.6799 | 0.6767 |
| 32 | 0.10 | 56 | 4455 | 1544 | 0.3554 | 0.4049 |
| 64 | 0.10 | 56 | 4455 | 1544 | 0.2383 | 0.2915 |
| 128 | 0.10 | 56 | 4455 | 1544 | 0.2133 | 0.2633 |
| 8 | 0.25 | 140 | 10764 | 1544 | 0.8108 | 0.7836 |
| 16 | 0.25 | 140 | 10764 | 1544 | 0.6831 | 0.6498 |
| 32 | 0.25 | 140 | 10764 | 1544 | 0.3666 | 0.3895 |
| 64 | 0.25 | 140 | 10764 | 1544 | 0.2515 | 0.2785 |
| 128 | 0.25 | 140 | 10764 | 1544 | 0.2227 | 0.2532 |
| 8 | 0.50 | 280 | 20283 | 1544 | 0.8161 | 0.7954 |
| 16 | 0.50 | 280 | 20283 | 1544 | 0.6802 | 0.6531 |
| 32 | 0.50 | 280 | 20283 | 1544 | 0.3717 | 0.3878 |
| 64 | 0.50 | 280 | 20283 | 1544 | 0.2530 | 0.2698 |
| 128 | 0.50 | 280 | 20283 | 1544 | 0.2238 | 0.2424 |
| 8 | 1.00 | 561 | 41037 | 1544 | 0.8192 | 0.7903 |
| 16 | 1.00 | 561 | 41037 | 1544 | 0.6787 | 0.6533 |
| 32 | 1.00 | 561 | 41037 | 1544 | 0.3734 | 0.3858 |
| 64 | 1.00 | 561 | 41037 | 1544 | 0.2549 | 0.2697 |
| 128 | 1.00 | 561 | 41037 | 1544 | 0.2262 | 0.2426 |

Total wall-clock: ~16s on an M4 Max (MPS), no cloud compute.

## Findings

**Capacity: GO.** At full training data, validation loss keeps dropping
substantially as `hidden_dim` grows (0.79 -> 0.24, hidden_dim 8 -> 128), with
no sign of flattening out by 128. LSTM capacity in this range is not yet the
bottleneck -- `AblationReport.capacity_helps_at_full_data()` returns `True`.
Train and validation loss stay close to each other at every cell (no
overfitting gap), which is itself informative: the model isn't yet fitting
the training set tightly enough for capacity, at this range, to be a
liability.

**Sample size: inconclusive, not "no effect."** Validation loss is
strikingly flat across the sample-fraction axis at fixed capacity -- e.g.
hidden_dim=128 scores 0.263 / 0.253 / 0.242 / 0.243 at 10% / 25% / 50% / 100%
of the training storms. Read naively this says data volume doesn't matter in
this range, which would undercut the whole premise of PLAN.md's "sample size"
concern. **Don't read it that way yet**: training is full-batch (one gradient
update per epoch, fixed at 30 epochs for every cell), so a fraction=1.0 cell
gets the same *number* of parameter updates as fraction=0.1, just larger
batches per update -- this run cannot cleanly separate "more data doesn't
help" from "fixed-epoch full-batch training under-trains the large-data
cells relative to what mini-batch SGD with proportionally more steps would
achieve." Re-run with mini-batching (steps scaled with dataset size, or a
fixed step count with shuffled mini-batches) before treating the
sample-size axis of this result as a real finding.

## Decision

**GO on continuing to invest in model capacity** for the track/intensity
group -- nothing here justifies capping the transformer's size on capacity
grounds alone. The honest open item is the sample-size axis, which this run
could not resolve cleanly; re-run with mini-batch training before drawing a
conclusion there, and treat any future "the archive is too thin, stop
scaling" claim as unproven until that re-run exists. Continuing to invest in
augmentation (already wired in `data.besttrack.augment_track`) and, per
PLAN.md, storm-relative coordinates (`data.storm_relative`, also wired in
this run) remains the right posture regardless.

This does not, by itself, clear the transformer's gridded-field capacity for
a full Stage A/B run (#22) -- that needs the transformer-specific version of
this experiment against real ERA5/GDAS fields, not this LSTM proxy.
