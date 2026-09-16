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
| `gdas_cache.sbatch` | Fetch+cache real GDAS (`data.gdas_cache`), the Stage B analog | `gridded` extra's `eccodes` (see its docstring for a real broken-native-library failure mode) |

Both take the split name as their one positional arg (default `train`), and
read `HURDAT2_PATH` / `CACHE_DIR` / `MAX_WORKERS` from the environment if you
want to override their defaults without editing the script.

Add a new ingest job here the same way: a `#SBATCH`-headered script that
`cd`s to the repo root, resolves its inputs from env vars with sane
defaults, and calls the relevant `anemoi <subcommand>` -- not a bespoke
one-off shell invocation typed into an SSH session.
