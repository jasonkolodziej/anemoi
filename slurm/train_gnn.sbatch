#!/bin/bash
#SBATCH --job-name=train-gnn
#SBATCH --output=logs/%x-%j.log
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --gres=gpu:1
# Real Stage A -> Stage B curriculum for the GNN baseline (#22). Same real
# cached GriddedFields source as train_cnn.sbatch/train_transformer.sbatch,
# but treated as a lattice-graph mesh (subsampled grid cells as nodes,
# 4-connectivity edges) -- see training.real_run_gnn's module docstring.
# Needs era5_cache.sbatch/gdas_cache.sbatch to have fetched at least some
# data first, and gets better as more of the cache fills in. Needs the
# torch and storage extras plus real R2 credentials (S3_ARTIFACT_* in .env).
#
# Real SLURM cluster:  sbatch slurm/train_gnn.sbatch
# This VM (no scheduler): slurm/run_local.sh slurm/train_gnn.sbatch

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
HIDDEN_DIM="${HIDDEN_DIM:-128}"

if [ ! -f "$HURDAT2" ]; then
  echo "HURDAT2 archive not found at $HURDAT2 -- fetch it first:" >&2
  echo "  curl -o $HURDAT2 https://www.nhc.noaa.gov/data/hurdat/hurdat2-atl-1851-2023-042624.txt" >&2
  exit 1
fi

uv run anemoi train \
  --model gnn \
  --hurdat2 "$HURDAT2" \
  --era5-cache-dir "$ERA5_CACHE_DIR" \
  --gdas-cache-dir "$GDAS_CACHE_DIR" \
  --registry-root "$REGISTRY_ROOT" \
  --seed "$SEED" \
  --n-augment "$N_AUGMENT" \
  --hidden-dim "$HIDDEN_DIM"
