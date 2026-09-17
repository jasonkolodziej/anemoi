# Streaming DataLoader: the durable fix for the full-batch OOM

PLAN.md §5 "Sample size" / #22. Originally recorded as scoped design work
before any of it existed; **as of 2026-09-16 all five models have a real,
tested, opt-in streaming training path** -- `training.streaming` (the
shared `OnlineMeanStd`/`OnlineMaskedLeadMeanStd`/`WindowDataset` infra) plus
`train_lstm_stage_streaming` (#60), `train_cnn_stage_streaming`/
`train_transformer_stage_streaming` (#61), `train_gnn_stage_streaming`
(#62), and `train_pinn_stage_streaming`/`_train_candidate_lstm_streaming`
(#63). Each `run_*_curriculum` takes `streaming: bool = False, batch_size:
int` -- default unchanged (the existing full-batch path is still there,
untouched, still what CI and small real runs use); pass `streaming=True`
for the durable, `O(batch_size)`-VRAM path. See `docs/train_infrastructure.md`'s
training-run sections for what's actually running on the VM at any given
time.

Only §6 (`real_latents.py`) below remains full-batch -- explicitly lower
urgency (see that section for why) and not yet converted.

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

## What changed, file by file

### 1. Standardization statistics (all five `_standardize_x`/`_standardize_y` pairs) -- done

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

PINN additionally standardizes its environment vector the same way;
`train_pinn_stage_streaming` fits it with the same `OnlineMeanStd`.

Built as `training.streaming.OnlineMeanStd`/`OnlineMaskedLeadMeanStd` --
Chan's parallel-batch generalization of Welford's algorithm, verified in
`tests/test_streaming.py` to match each real `_standardize_x`/
`_standardize_y` function to float32 precision, not just assumed correct.
The output contract (`x_mean`/`x_std`/`y_mean`/`y_std`, what
`RunArtifacts`/`real_latents.py` already consume) is unchanged.

### 2. A real `torch.utils.data.Dataset`, one per model family -- done

Each streaming `train_*_stage_streaming` builds a dataset whose
`__getitem__` loads **one window's** real cached fields from disk on
demand, instead of one materialized array:

- CNN/Transformer: `training.streaming.WindowDataset`, `build_x` looks up
  the cached `.npz` (`data.gridded_cache.cache_path`/`load_cached_fields`)
  and stacks the channel/crop for that one window. Windows with no cached
  file yet are dropped up front by `filter_windows_with_cache`, since
  `DataLoader` needs a fixed-length index.
- LSTM: also `WindowDataset`, `build_x` is `storm_relative_sequence` --
  no gridded cache read, so no filtering needed.
- GNN: also `WindowDataset` (module-shared, not GNN-specific), node-
  featurized (`real_run_gnn._node_features`) per window against a
  `MeshTopology` built once, lazily, on the first window loaded.
  `batch_graph`'s block-diagonal batching turned out to need no changes
  at all, as predicted below -- it's called per-`DataLoader`-batch inside
  the training loop instead of once over the whole dataset.
- PINN: needed its own `_PinnWindowDataset` rather than `WindowDataset`
  -- each item needs the environment vector, the raw track window (for
  the candidate LSTM), and the window's base `(lat, lon)` the absolute-
  coordinate conversion is anchored to, three things `WindowDataset`'s
  single-array contract can't carry together.

One correction found the hard way, not anticipated by the original scope
below: `OnlineMeanStd` fit with `keepdims=True` over a *batched* array
(e.g. CNN's `(N, C, H, W)`) returns stats shaped for broadcasting against
another batched array -- but `WindowDataset` standardizes one *unbatched*
item `(C, H, W)` at a time, and numpy silently left-pads the mismatch
into a wrong result instead of raising. Fixed by squeezing the batch axis
off the stats specifically for `WindowDataset` construction (see
`real_run_cnn.train_cnn_stage_streaming`'s comment); pinned with a
regression test in `test_streaming.py` at the shared-infrastructure level
so it can't recur silently for a model added later.

Windows are still enumerated up front as a plain Python list (each one
cheap -- a handful of `Fix` objects plus small arrays, not field data),
not a true `IterableDataset` with a shuffle buffer -- the simpler
approach the original scope flagged as an alternative turned out to be
sufficient; the CPU-side win (§ below) doesn't require windows themselves
to stream, only the heavy per-window data they reference.

### 3. `torch.utils.data.DataLoader` wiring -- done

Every streaming stage function uses a real `DataLoader(ds, batch_size=N,
shuffle=True)` for train (`shuffle=False` for val, so batch order matches
`val_windows` order for verification-pair building). Built via the shared
`streaming.make_dataloader` helper, which takes a `num_workers: int = 0`
parameter -- left at 0 (main-process loading) by default, since real
batching/shuffling was the actual OOM fix. **Update, PR #70 (2026-09-17):**
worker parallelism, originally scoped above as "a separate, later
optimization... not needed to close this out," turned out to matter for
real once the VM's cache grew large enough that per-batch disk
read+decompress cost became comparable to the GPU step itself (confirmed
via `/proc/<pid>/io`: high `rchar`/`syscr`, flat `read_bytes` --
CPU/decompression-bound, served from the OS page cache, not disk-I/O-
bound). `num_workers>0` now spawns real forked worker *processes*
(`multiprocessing_context="fork"`, forced regardless of platform --
`make_dataloader`'s own docstring has the fork-vs-spawn reasoning) that
prefetch batches ahead of the training loop, so CPU-side loading and
GPU-side compute genuinely overlap instead of alternating:

```text
Phase 1 -- online stats fit (per stage, once): single-threaded, CPU only
  main process ── reads each cached window's .npz sequentially from disk ──▶ OnlineMeanStd.update()
  (deliberately not parallelized -- iter_dataset_in_batches is a one-pass
   sweep; not worth the worker overhead for something run once)

Phase 2 -- the real per-batch training loop: CPU workers ∥ GPU compute, overlapped

  local disk cache (~/era5_cache, ~/gdas_cache -- already-fetched .npz
                     GriddedFields; the training loop only ever reads
                     from here, never fetches live)
        │            │            │            │
        ▼            ▼            ▼            ▼
   worker 0      worker 1     worker 2     worker 3     ← num_workers=4: real forked
   build_x()     build_x()    build_x()    build_x()      OS processes, each running the
   decompress+   decompress+  decompress+  decompress+    model's own build_x/collate_fn
   featurize     featurize    featurize    featurize      closure via copy-on-write fork
        │            │            │            │
        └────────────┴─────┬──────┴────────────┘
                    shared-memory IPC, batched by collate_fn
                            ▼
                 ┌────────────────────┐
                 │  main process      │  DataLoader.__next__() pulls a batch
                 │  (holds CUDA ctx)  │  the workers have already prefetched
                 └────────────────────┘
                            │  batch.to(device)
                            ▼
                 ┌────────────────────┐
                 │  GPU (CUDA/MPS)    │  forward → loss → backward → optimizer.step()
                 └────────────────────┘
                            │  (repeat per batch × epoch; workers keep
                            ▼   prefetching the next batches meanwhile)
```

Verified for real on the VM (`anemoi-train-1`, single L4): CNN's real
Stage A+B wall-clock dropped from ~94 min (`num_workers=0`) to ~48 min
(`num_workers=4`); Transformer from ~158 min to ~75 min. `persistent_workers
=True` follows automatically when `num_workers>0` so workers aren't
re-spawned every epoch. `--num-workers` is wired into both CLI
subcommands and all six sbatch scripts.

### 4. Every `train_*_stage`'s training loop -- done

Each streaming function replaced the single full-batch
`masked_mse(model(xt), yt, mt)` call with a real per-batch loop
(zero_grad/forward/backward/step per batch). Epoch-level loss is reported
as one global `diff2_sum / mask_sum` ratio accumulated across all
batches, not an average of per-batch ratios -- matching the full-batch
version's exact semantics rather than introducing a subtly different
number. Validation predictions are collected across batches via
`np.concatenate` before building `metrics.track.verify` pairs, same as
the full-batch path's single pass.

### 5. PINN's candidate-generator LSTM -- done

`_train_candidate_lstm_streaming` trains via a real `DataLoader` over a
`WindowDataset`, same raw (unstandardized) targets the full-batch
`_train_candidate_lstm` uses. `train_pinn_stage_streaming` runs the
(already-trained, frozen) candidate once per `DataLoader` batch via a new
batched `_disp_to_abs_batch` helper -- mirrors the existing per-sample
`_candidate_and_true_absolute` loop, just batched, instead of running the
candidate over the whole train/val array in one forward call.

### 6. `training/real_latents.py`'s `_extract_for_tracks` -- not done

Still a single-pass materialize-everything-then-batch design. Left as
originally scoped: lower urgency than the main training loops (runs once
per orchestrator schedule, over already-*trained*, frozen, eval-mode
models with no gradients to hold, so its real memory footprint is smaller
than a training step's). Still real, still eventually a wall at large
enough scale -- revisit if it ever actually OOMs, the way
`train_transformer_stage` did.

### 7. Tests -- done, additive as planned

Every existing `build_*_samples`/`train_*_stage` full-batch test in
`tests/test_real_run*.py` is untouched and still passing -- the additive
design held. Each model's streaming path got its own new tests
(`*_streaming_runs_and_produces_val_metrics`,
`*_streaming_raises_on_empty_cache` where cache-dependent,
`run_*_curriculum_streaming_completes_both_stages`), plus
`tests/test_streaming.py` for the shared infrastructure (numerical
equivalence against each real `_standardize_x`/`_standardize_y`, the
keepdims regression test, `filter_windows_with_cache`). Full suite: 541
passed, 5 skipped as of #63.

### 8. A real side benefit, not required but worth having in view -- not done

Mid-stage checkpointing (save every N batches/epochs, resume from the
last checkpoint) is still not implemented -- the streaming loops make it
straightforward to add later (a real per-batch loop is the prerequisite,
now in place), but nothing in #60-#63 added checkpoint save/resume logic
itself. Still independently useful for the Spot-preemption-loses-a-whole-
stage problem `docs/train_infrastructure.md`'s "Training VM" section
documents; revisit if that becomes a real recurring cost again (this
project has since moved off Spot provisioning for the training VM, which
was the original motivation).

## Status

The durable fix is built (§1-5, #60-#63): all five models can train with
`O(batch_size)` VRAM via `streaming=True`, verified numerically equivalent
to the full-batch path's standardization and matching its loss/
verification semantics exactly. The immediate real stopgap for the
2026-09-17 OOM, `--n-augment 1`, is no longer the only lever -- a real VM
run can now use `streaming=True` instead, without reducing augmentation.
Only `real_latents.py` (§6) and mid-stage checkpointing (§8) remain, both
deliberately deferred as lower urgency, not forgotten.
