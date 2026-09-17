#!/bin/bash
#SBATCH --job-name=train-transformer
#SBATCH --output=logs/%x-%j.log
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --gres=gpu:1
# Real Stage A -> Stage B curriculum for the Transformer baseline (#22).
# Same real-data source as train_cnn.sbatch (cached GriddedFields as a
# channel stack), trimmed to the model's fixed real grid size -- see
# training.real_run_transformer's module docstring. Needs
# era5_cache.sbatch/gdas_cache.sbatch to have fetched at least some data
# first, and gets better as more of the cache fills in. Needs the torch
# and storage extras plus real R2 credentials (S3_ARTIFACT_* in .env).
#
# Real SLURM cluster:  sbatch slurm/train_transformer.sbatch
# This VM (no scheduler): slurm/run_local.sh slurm/train_transformer.sbatch

set -euo pipefail
cd "$(dirname "$0")/.."
source "$HOME/.local/bin/env" 2>/dev/null || true  # uv, if installed via astral's installer
if [ -f .env ]; then set -a && source .env && set +a; fi  # S3_ARTIFACT_*, checkpoint upload is not optional here

HURDAT2="${HURDAT2_PATH:-$HOME/hurdat2-atl.txt}"
ERA5_CACHE_DIR="${ERA5_CACHE_DIR:-$HOME/era5_cache}"
GDAS_CACHE_DIR="${GDAS_CACHE_DIR:-$HOME/gdas_cache}"
REGISTRY_ROOT="${REGISTRY_ROOT:-$HOME/.anemoi/registry}"
SEED="${SEED:-20260806}"
N_AUGMENT="${N_AUGMENT:-3}"
# Streaming training (docs/streaming_dataloader.md, #60-#64): real
# per-batch DataLoader training instead of the default full-batch path --
# this is the model that actually hit a real CUDA OOM training full-batch
# against the real, growing cache. STREAMING=1 opts in; BATCH_SIZE left
# unset keeps the model's own tuned default; NUM_WORKERS spawns real
# DataLoader worker processes to overlap batch loading with GPU compute
# (training.streaming.make_dataloader) -- left unset keeps the default of 0.
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
  --model transformer \
  --hurdat2 "$HURDAT2" \
  --era5-cache-dir "$ERA5_CACHE_DIR" \
  --gdas-cache-dir "$GDAS_CACHE_DIR" \
  --registry-root "$REGISTRY_ROOT" \
  --seed "$SEED" \
  --n-augment "$N_AUGMENT" \
  "${EXTRA_ARGS[@]}"
