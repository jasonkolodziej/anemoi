# Stage B noise-emulator sensitivity

PLAN.md §5 "Noise-emulator recalibration is a prerequisite, not a refinement"
(#12). Recorded run, 2026-09-16.

## The question

`WorkingTrackNoise`'s scope-era defaults (15 nm / 5 kt / 3 mb) are
placeholders, not measured values. Torn and Snyder (2012) put satellite-only
intensity uncertainty near 10-12 kt and pressure at 7-12 mb -- roughly double
the defaults -- via `WorkingTrackNoise.from_literature()`. Before real paired
working/final data exists to recalibrate against directly
(`recalibrate_from_pairs()`, blocked on #17's data becoming available at
scale), the question is whether this gap is even worth worrying about: does
switching from the defaults to the literature values change Stage B
fine-tuned performance enough to matter?

## What this run measures, and what it does not

Same honest substitute #9 used for capacity: no trained Stage A checkpoint
exists yet (#22), so this is a track-only LSTM trained from scratch, reusing
`training.capacity_ablation.build_samples`/`train_cell` unchanged. Capacity
is held fixed at `hidden_dim=64`, informed by `docs/capacity_ablation.md`'s
own finding that capacity keeps helping through 128 -- a smaller capacity
would risk the *capacity* gap swamping the *noise* gap this comparison is
trying to isolate.

**Evaluation noise is held fixed** at `WorkingTrackNoise.from_literature()`
for both runs (the better-evidenced candidate, standing in for real paired
data until it exists); only the **training-input** noise varies between the
scope defaults and the literature values. That isolates "does the
training-time noise assumption change performance against the best available
estimate of real conditions" rather than "which noise level wins when train
and eval match."

Note that `LITERATURE_POSITION_RMS_NM` and `DEFAULT_POSITION_RMS_NM` are both
15.0 nm -- identical. Only `intensity_rms_kt` (5.0 vs 12.0 kt) and
`pressure_rms_mb` (3.0 vs 10.0 mb) actually differ between the two
candidates, and the model's position target (`dx_east_nm`, `dy_north_nm`) is
computed from the current *working* fix, so any sensitivity this comparison
can detect is necessarily concentrated in the wind/pressure-adjacent signal,
not position.

## Data and method

- **Archive:** same real NHC HURDAT2 file as `docs/capacity_ablation.md`
  (`hurdat2-atl-1851-2023-042624.txt`).
- **Split:** `data.splits.DEFAULT_BOUNDARIES` -- train 1980-2019 (561 storms),
  val 2020-2022 (68 storms). Test split untouched.
- **Training:** full-batch Adam, 30 epochs, `hidden_dim=64`, `n_augment=3`,
  standardised inputs/targets, ran on Apple Silicon MPS.

Reproduce with `training.noise_sensitivity.run_noise_sensitivity(tracks)`
given a real `list[Track]` from `parse_hurdat2_file`.

## Results

| noise | position_rms_nm | intensity_rms_kt | pressure_rms_mb | train_loss | val_loss |
|---|---|---|---|---|---|
| default | 15.0 | 5.0 | 3.0 | 0.2555 | 0.2783 |
| literature | 15.0 | 12.0 | 10.0 | 0.2665 | 0.2789 |

**Relative change (default -> literature): +0.21%.**

A per-target-dimension breakdown (checked manually, not part of the recorded
API, to confirm the combined metric isn't diluting a larger effect in one
channel) shows the same picture: `dx_east_nm` −0.14%, `dy_north_nm` −0.003%,
`max_wind_kt` +1.2%. The wind channel -- the one target most plausibly
affected by intensity-input noise -- moves the most, as expected, but still
far short of anything practically significant.

Total wall-clock: ~5s on an M4 Max (MPS), no cloud compute.

## Decision

**NOT LOAD-BEARING at this precision.** Switching the Stage B training-input
noise assumption from the scope's defaults to the literature values does not
materially change fine-tuned performance in this experiment --
`NoiseSensitivityReport.is_load_bearing(threshold=0.05)` returns `False`,
and the per-dimension check confirms no channel is being diluted by the
aggregate metric. Recalibration can reasonably wait for real paired
working/final data (#17-scale) rather than being treated as a Stage B
blocker.

This is measured on the LSTM proxy task, at one capacity, with a scalar-RMS
noise model on both sides of the comparison -- it says the *choice between
two specific scalar-RMS candidates* isn't load-bearing, not that observation
error is irrelevant to Stage B. The known structural gap remains open per
the issue's own "at minimum as a follow-up": both candidates are a single
constant RMS, while Torn and Snyder's own numbers are intensity-*dependent*
(position uncertainty falls with intensity, intensity uncertainty rises).
Representing that -- e.g. `WorkingTrackNoise` keyed on Saffir-Simpson
category rather than one constant -- is a `besttrack` module change that
needs real paired data to fit against regardless, and is not something this
sensitivity comparison can retrofit.
