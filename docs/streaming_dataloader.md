# Streaming DataLoader: scope for a future fix (not yet built)

PLAN.md §5 "Sample size" / #22. Recorded here because it's real, scoped
design work discovered during a real production run, not because any of
it exists yet -- **nothing in this document is implemented**. See
`docs/train_infrastructure.md`'s training-run sections for what *is* real
today.

## The problem this solves

Training a real CUDA OOM on the VM (2026-09-17): `train_transformer_stage`
tried to allocate 1.84 GiB more with 20.87 GiB already in use on a 22.03
GiB L4. Root cause, confirmed by reading the actual code, not assumed:
every `train_*_stage` function trains **full-batch** -- the entire
training set as one GPU tensor, one forward/backward per "epoch," no
mini-batching at all. Per-step VRAM use is therefore `O(dataset size)`,
not `O(batch size)`. As the real ERA5/GDAS cache keeps growing (the whole
point of `data.era5_cache`/`data.gdas_cache`'s ongoing backfill), this
wall moves closer regardless of which GPU it's run on -- a bigger GPU
buys headroom, not a fix; the same OOM recurs once enough real data is
cached, on any fixed-size accelerator.

Cutting `n_augment` is a real, working stopgap (proportionally reduces
the batch), not a fix either -- it delays hitting the wall, it doesn't
remove it.

There are actually **two** materialization points, and a real fix needs
both addressed, not just the GPU-visible one:

1. **CPU-side** (`build_cnn_samples`/`build_transformer_samples`/
   `build_gnn_samples`/`build_pinn_samples`/`build_stage_samples`):
   each of these iterates `real_run.iter_stage_windows` (already a real
   generator -- one `StageWindow` at a time, cheap) but then loads every
   window's real cached `GriddedFields`, builds its model-specific `x`,
   and appends to a Python list before a single `np.stack(...)` at the
   end. The **entire** windowed dataset ends up materialized as one numpy
   array in host RAM before training even starts.
2. **GPU-side** (`train_*_stage`): the fully-materialized numpy array is
   converted to **one** `torch.as_tensor(..., device=device)` and trained
   full-batch. This is where the actual OOM happened.

Fixing only #2 (mini-batch the GPU tensor) removes today's OOM and is
durable against real dataset growth for a good while -- per-batch VRAM
becomes constant regardless of total cache size. But #1 doesn't go away:
at a large enough real archive (this project's own stated direction --
decades-deep ERA5, more seasons over time), the CPU-side array becomes
the next wall, just measured in host RAM instead of VRAM. A true
"never revisit this regardless of archive size" architecture needs both
layers to stop materializing the whole dataset at once.

## What actually needs to change, file by file

### 1. Standardization statistics (all five `_standardize_x`/`_standardize_y` pairs)

`real_run.py`, `real_run_cnn.py`, `real_run_gnn.py`,
`real_run_transformer.py` each compute `x.mean(axis=...)`/`x.std(axis=...)`
in a single pass over the fully-materialized array. A streaming design
can't do this -- there's no single array to call `.mean()` on. Needs a
real online/incremental algorithm (e.g. Welford's algorithm for mean+
variance in one pass, or a deliberate two-pass design: one streaming pass
to accumulate statistics, a second to actually train). The *output*
contract (`x_mean`/`x_std`/`y_mean`/`y_std` arrays of the same shapes,
what `real_run.RunArtifacts` already carries and `real_latents.py` already
consumes) doesn't need to change -- only how they get computed.

PINN additionally standardizes its environment vector the same
single-pass way in `train_pinn_stage` -- same fix needed there.

### 2. A real `torch.utils.data.Dataset`/`IterableDataset`, one per model family

Replace "build the whole array, then slice it" with a dataset object whose
`__getitem__`/iteration loads **one window's** real cached fields from
disk on demand:

- CNN/Transformer: look up the cached `.npz` (`data.gridded_cache
  .cache_path`/`load_cached_fields`, exactly what `build_cnn_samples`/
  `build_transformer_samples` already do per-row), stack the channel/crop
  for that one window, standardize with precomputed stats, return the
  tensor.
- GNN: same real cached fields, but node-featurized
  (`real_run_gnn._node_features`) per window. `batch_graph`'s
  block-diagonal batching (concatenate node blocks, offset edge indices)
  already operates on an arbitrary-sized `x` array against a shared
  `MeshTopology` -- it doesn't need to change, just needs to be called
  per-`DataLoader`-batch instead of once over the whole dataset. This is
  the one piece of the whole design that's already shaped right.
- PINN: needs both the real environment vector
  (`data.features.compute_environment_features`) and a candidate
  trajectory from the candidate-generator LSTM per window -- see #4 below,
  since the candidate model itself has the same full-batch problem.
- LSTM: `storm_relative_sequence` per window; no gridded cache read at
  all, so this is the cheapest of the five to convert, but still trains
  full-batch today (`train_lstm_stage`) and would still hit the same wall
  eventually against a large enough real track archive, independent of
  gridded-field size.

True random-access `__getitem__` needs an *indexable* enumeration of
windows (storm, augmentation variant, window start) rather than
`iter_stage_windows`'s current plain generator -- either materialize just
that lightweight index (storm_id/timestamp tuples, not field data) or use
`IterableDataset` with a bounded shuffle buffer, the standard pattern for
"can't fully randomize a stream, but don't want strict sequential order
either."

### 3. `torch.utils.data.DataLoader` wiring

`DataLoader(dataset, batch_size=N, shuffle=True, num_workers=k)` for real
batched loading with prefetch -- also gets multi-worker parallelism on the
disk I/O (reading cached `.npz` files) essentially for free, which today's
single-threaded `build_*_samples` loop doesn't have.

### 4. Every `train_*_stage`'s training loop

Currently: one `masked_mse(model(xt), yt, mt)` call per "epoch" against
the whole materialized tensor. Needs: a real per-batch loop
(zero_grad/forward/backward/step per batch, loss accumulated/averaged
across batches per epoch). The validation pass and the
`metrics.track.verify` pair-building loop (currently iterating the fully
materialized `val_samples` array) need the same treatment -- accumulate
predictions across val batches rather than one val forward pass.

### 5. PINN's candidate-generator LSTM (`real_run_pinn._train_candidate_lstm`)

Trains full-batch against `build_stage_samples`' fully-materialized output
today -- the same problem, one level removed. `_candidate_and_true_absolute`
also runs the already-trained candidate over the *whole* train/val array
in one forward call. Both need the same streaming/batching treatment for
full consistency, or PINN just moves the OOM wall from its main model to
its candidate generator instead of removing it.

### 6. `training/real_latents.py`'s `_extract_for_tracks`

Also a single-pass materialize-everything-then-batch design (collects
every window's five models' `x`'s into lists, `np.stack`s, then runs each
model's `.encode()` once over the whole thing). Lower urgency than the
main training loops -- it runs once per orchestrator schedule, over
whatever's cached for latent extraction, and each model here is already
*trained* (frozen, eval-mode, no gradients to hold) so its real memory
footprint is smaller than a training step's. Still real, still eventually
a wall at large enough scale, still worth listing for completeness.

### 7. Tests

`tests/test_real_run*.py` construct small in-memory fixtures and assert
directly on fully-materialized sample objects (`samples.x.shape`, etc.) --
this is legitimate, useful, fast test coverage that shouldn't be thrown
away. The safe path is **additive, not a rewrite**: keep the existing
`build_*_samples`/`train_*_stage` full-batch path as-is (correct, tested,
fine for small real runs and for CI), and add a new streaming path
alongside it, selected explicitly (e.g. a `streaming: bool` /
`batch_size: int | None` parameter, or a size heuristic) rather than
silently swapping behavior under existing callers.

### 8. A real side benefit, not required but worth having in view

A real per-batch loop naturally enables real mid-stage checkpointing
(save every N batches/epochs, resume from the last checkpoint) --
independently useful for the Spot-preemption-loses-a-whole-stage problem
`docs/train_infrastructure.md`'s "Training VM" section already documents
as the reason this project moved off Spot provisioning. Not part of this
scope on its own, but the same refactor that fixes the OOM wall is also
what would make that resumability real, if it's ever wanted.

## What this document is not

Not a commitment to build this now, not a timeline, not a scope
recommendation on when to do it -- just an accurate record of what
changes so a future decision to build it starts from a real map of the
work rather than rediscovering it from scratch. The immediate real fix
for the 2026-09-17 OOM was `--n-augment 1` (real, working, not covered by
this document) plus, if needed, #2/#3/#4 above for the durable version.
