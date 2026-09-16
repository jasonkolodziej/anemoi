#!/bin/bash
# Local stand-in for `sbatch` on a single VM with no SLURM scheduler
# (docs/train_infrastructure.md's anemoi-train-1). Launches the given job
# script in a detached tmux session -- named after the script's #SBATCH
# --job-name plus a locally generated numeric id, the same role SLURM's own
# job id plays -- and tees its output to a log file, so:
#
# * the job survives an SSH disconnect (tmux), the same as a real scheduler
#   not caring whether you're still watching
# * `tmux ls` / `tmux attach -t <name>` give you exactly the "is it still
#   running" / "let me look" operations `squeue` / `tail -f` would
# * every job script here also runs unmodified under a real `sbatch` if
#   this project ever gets access to an actual SLURM cluster -- the
#   #SBATCH lines are directives to a real scheduler and no-op comments to
#   this launcher (it only reads --job-name out of them)
#
# A Spot VM preemption kills whatever's in the tmux session regardless of
# how it was launched -- that's why every job script here is built on top
# of a resumable pipeline (data.gridded_cache's skip_existing), not
# something this launcher tries to solve.
#
# Usage: slurm/run_local.sh slurm/<script>.sbatch [job-script-args...]
#
# Env vars a job script reads (SYNC_ARCHIVE, HURDAT2_PATH, ...) are passed
# through explicitly below via `tmux new-session -e`, not left to ambient
# inheritance -- tmux only captures a NEW session's environment from its
# client at the moment the SERVER itself starts. Once a server is already
# running (any earlier job this boot), a later `tmux new-session` does NOT
# pick up env vars set only in that later shell -- confirmed the hard way:
# `SYNC_ARCHIVE=1 slurm/run_local.sh slurm/gdas_cache.sbatch` silently ran
# with SYNC_ARCHIVE unset whenever it wasn't the first job launched since
# boot, so `--sync-archive` never reached the script and nothing reached R2,
# with no error at all -- the fetch step still "succeeded" on its own.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <job-script> [args...]" >&2
  exit 1
fi

SCRIPT="$1"
shift

if [ ! -f "$SCRIPT" ]; then
  echo "no such job script: $SCRIPT" >&2
  exit 1
fi

JOB_NAME=$(grep -m1 '^#SBATCH --job-name=' "$SCRIPT" | cut -d= -f2)
if [ -z "$JOB_NAME" ]; then
  echo "job script $SCRIPT has no #SBATCH --job-name= line" >&2
  exit 1
fi

JOB_ID=$(date +%s)
SESSION="${JOB_NAME}-${JOB_ID}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_PATH="$LOG_DIR/${SESSION}.log"

#: Job-script env vars this launcher forwards explicitly (see the note
#: above on why ambient inheritance isn't enough). Add a name here if a new
#: job script reads a new env var.
PASSTHROUGH_VARS=(
  SYNC_ARCHIVE HURDAT2_PATH CACHE_DIR MAX_WORKERS
  REGISTRY_ROOT SEED N_AUGMENT HIDDEN_DIM
)
TMUX_ENV_ARGS=()
for var in "${PASSTHROUGH_VARS[@]}"; do
  if [ -n "${!var:-}" ]; then
    TMUX_ENV_ARGS+=(-e "${var}=${!var}")
  fi
done

tmux new-session -d -s "$SESSION" "${TMUX_ENV_ARGS[@]}" \
  "bash '$SCRIPT' $* 2>&1 | tee -a '$LOG_PATH'"

echo "submitted '$JOB_NAME' as tmux session '$SESSION'"
echo "  log:    $LOG_PATH"
echo "  watch:  tmux attach -t $SESSION   (Ctrl+B, D to detach without killing it)"
echo "  status: tmux ls"
