#!/bin/bash
#SBATCH --job-name=train-lstm
#SBATCH --output=logs/%x-%j.log
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --gres=gpu:1
# Real Stage A -> Stage B curriculum for the LSTM baseline (#22), unlike
# era5_cache.sbatch/gdas_cache.sbatch which are CPU-only data-ingest jobs --
# this one actually trains, so it needs the GPU. Track-only model (no
# gridded-field input, see training.real_run's module docstring), so it
# does NOT depend on era5_cache/gdas_cache having finished -- only a real
# HURDAT2 file. Needs the torch and storage extras plus real R2 credentials
# (S3_ARTIFACT_* in .env) -- every stage's checkpoint uploads durably.
#
# Real SLURM cluster:  sbatch slurm/train_lstm.sbatch
# This VM (no scheduler): slurm/run_local.sh slurm/train_lstm.sbatch

set -euo pipefail
cd "$(dirname "$0")/.."
source "$HOME/.local/bin/env" 2>/dev/null || true  # uv, if installed via astral's installer
if [ -f .env ]; then set -a && source .env && set +a; fi  # S3_ARTIFACT_*, checkpoint upload is not optional here

HURDAT2="${HURDAT2_PATH:-$HOME/hurdat2-atl.txt}"
REGISTRY_ROOT="${REGISTRY_ROOT:-$HOME/.anemoi/registry}"
SEED="${SEED:-20260806}"
N_AUGMENT="${N_AUGMENT:-3}"
HIDDEN_DIM="${HIDDEN_DIM:-128}"
# Streaming training (docs/streaming_dataloader.md, #60-#64): real
# per-batch DataLoader training instead of the default full-batch path.
# STREAMING=1 opts in; BATCH_SIZE left unset keeps the model's own tuned
# default; NUM_WORKERS spawns real DataLoader worker processes to overlap
# batch loading with GPU compute (training.streaming.make_dataloader) --
# left unset keeps the default of 0.
STREAMING="${STREAMING:-}"
BATCH_SIZE="${BATCH_SIZE:-}"
NUM_WORKERS="${NUM_WORKERS:-}"

if [ ! -f "$HURDAT2" ]; then
  echo "HURDAT2 archive not found at $HURDAT2 -- fetch it first:" >&2
  echo "  curl -o $HURDAT2 https://www.nhc.noaa.gov/data/hurdat/hurdat2-atl-1851-2023-042624.txt" >&2
  exit 1
fi

EXTRA_ARGS=()
if [ -n "$STREAMING" ]; then EXTRA_ARGS+=(--streaming); fi
if [ -n "$BATCH_SIZE" ]; then EXTRA_ARGS+=(--batch-size "$BATCH_SIZE"); fi
if [ -n "$NUM_WORKERS" ]; then EXTRA_ARGS+=(--num-workers "$NUM_WORKERS"); fi

uv run anemoi train \
  --model lstm \
  --hurdat2 "$HURDAT2" \
  --registry-root "$REGISTRY_ROOT" \
  --seed "$SEED" \
  --n-augment "$N_AUGMENT" \
  --hidden-dim "$HIDDEN_DIM" \
  "${EXTRA_ARGS[@]}"
