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

tmux new-session -d -s "$SESSION" \
  "bash '$SCRIPT' $* 2>&1 | tee -a '$LOG_PATH'"

echo "submitted '$JOB_NAME' as tmux session '$SESSION'"
echo "  log:    $LOG_PATH"
echo "  watch:  tmux attach -t $SESSION   (Ctrl+B, D to detach without killing it)"
echo "  status: tmux ls"
