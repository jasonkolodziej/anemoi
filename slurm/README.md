# Job scripts (SLURM-equivalent)

Data-ingest jobs (real ERA5/GDAS fetch, and whatever else joins them) are
long-running, run unattended, and need to survive both SSH disconnects and
Spot preemption. Rather than one-off `tmux new-session` commands typed by
hand each time, every such job lives here as a real `#SBATCH`-headered
script -- the same format a SLURM cluster expects.

## Why SLURM-shaped scripts on a single VM

`docs/train_infrastructure.md`'s current infrastructure is one GCP VM, not
a SLURM cluster -- there's no scheduler daemon here. But writing the job
scripts in SLURM's own format costs nothing and buys real portability: if
this project ever gets access to an actual SLURM cluster, every script here
is submittable as-is with `sbatch`. Until then, `run_local.sh` is a small
local stand-in that gives the same operational shape (a named, backgrounded,
loggable job) using `tmux` instead of a scheduler daemon.

```bash
# Real SLURM cluster:
sbatch slurm/era5_cache.sbatch train

# This project's actual environment (no scheduler):
slurm/run_local.sh slurm/era5_cache.sbatch train
```

`run_local.sh` reads the script's `#SBATCH --job-name=` line, launches it in
a detached `tmux` session named `<job-name>-<id>`, and tees output to
`logs/<job-name>-<id>.log`. `tmux attach -t <session>` to watch,
`tmux ls` to check what's still running -- the closest single-VM equivalents
to `squeue`/`tail -f` a real scheduler would give you.

## What a Spot preemption does *not* solve

Neither `sbatch` nor `run_local.sh` protects against a Spot VM preemption --
that kills whatever's running regardless of how it was launched. Every job
script here is instead built on a resumable pipeline
(`data.gridded_cache`'s `skip_existing=True`): re-running the exact same
command after a preemption picks up wherever the cache left off, rather than
needing checkpoint/restart logic in the launcher itself.

## Jobs

| Script | What | Needs |
|---|---|---|
| `era5_cache.sbatch` | Fetch+cache real ERA5 (`data.era5_cache`) for one `data.splits` split | `gridded` extra (xarray/zarr/gcsfs) |
| `gdas_cache.sbatch` | Fetch+cache real GDAS (`data.gdas_cache`), the Stage B analog | `gridded` extra, plus `sudo apt-get install libeccodes0` -- `pip install eccodes` alone is bindings only, not the compiled library (docs/train_infrastructure.md) |
| `train_lstm.sbatch` | Real Stage A -> Stage B curriculum for the LSTM baseline (`training.real_run`, #22) -- a GPU job, unlike the two ingest jobs above | `torch` + `storage` extras, real R2 credentials (`S3_ARTIFACT_*` in `.env`) -- every stage's checkpoint uploads durably |
| `train_cnn.sbatch` | Real Stage A -> Stage B curriculum for the CNN baseline (`training.real_run_cnn`, #22) -- reads real cached GriddedFields as its channel stack, so it benefits from `era5_cache.sbatch`/`gdas_cache.sbatch` having fetched data first (works with whatever's cached so far, not all-or-nothing) | Same as `train_lstm.sbatch`, plus `ERA5_CACHE_DIR`/`GDAS_CACHE_DIR` pointing at the ingest jobs' cache dirs |
| `train_transformer.sbatch` | Same as `train_cnn.sbatch` for the Transformer baseline (`training.real_run_transformer`) -- the real cached crop (41x41) is trimmed to the model's fixed grid size (40x40) | Same as `train_cnn.sbatch` |
| `train_gnn.sbatch` | Same real cached-field source as `train_cnn.sbatch`, treated as a lattice-graph mesh (`training.real_run_gnn`) -- subsampled grid cells as nodes, 4-connectivity edges | Same as `train_cnn.sbatch` |

The two cache scripts take the split name as their one positional arg
(default `train`), and read `HURDAT2_PATH` / `CACHE_DIR` / `MAX_WORKERS`
from the environment if you want to override their defaults without editing
the script. Set
`SYNC_ARCHIVE=1` to also upload newly-cached files to the durable R2 archive
(`.env`'s `S3_ARTIFACT_*`, same bucket `tracking.checkpoint_store` uses) --
see docs/train_infrastructure.md's "Durable archive" section for why this
matters more for GDAS than ERA5 (NOAA's bucket has no documented retention
policy, so a local-only cache on a Spot VM is the only copy until it's
synced off-box).

`gdas_cache.sbatch` also drops any fix dated before GDAS's real archive
start (2021-01-01, `data.gdas_cache.GDAS_ARCHIVE_START`) before fetching --
`--split train` covers 1980-2019, decades before real GDAS data exists, so
without this every such fix would just 404.

Add a new ingest job here the same way: a `#SBATCH`-headered script that
`cd`s to the repo root, resolves its inputs from env vars with sane
defaults, and calls the relevant `anemoi <subcommand>` -- not a bespoke
one-off shell invocation typed into an SSH session.
