#!/bin/bash
#SBATCH --job-name=train-schedule
#SBATCH --output=logs/%x-%j.log
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --gres=gpu:1
# Runs the full multi-model wave schedule (#22) -- all five Group 1
# models (lstm/cnn/transformer/gnn/pinn) via training.orchestrator, backed
# by the real per-model runners (training.real_orchestrator). Alternative
# to launching each train_<model>.sbatch by hand: one job, one log,
# registry + promotion for every model. latents/diffusion/fusion have no
# real implementation yet and report as such in the output -- expected,
# not a failure of this job. Needs the torch and storage extras plus real
# R2 credentials (S3_ARTIFACT_* in .env).
#
# Real SLURM cluster:  sbatch slurm/train_schedule.sbatch [sequential|parallel]
# This VM (no scheduler): slurm/run_local.sh slurm/train_schedule.sbatch [sequential|parallel]

set -euo pipefail
cd "$(dirname "$0")/.."
source "$HOME/.local/bin/env" 2>/dev/null || true  # uv, if installed via astral's installer
if [ -f .env ]; then set -a && source .env && set +a; fi  # S3_ARTIFACT_*, checkpoint upload is not optional here

MODE="${1:-sequential}"
HURDAT2="${HURDAT2_PATH:-$HOME/hurdat2-atl.txt}"
ERA5_CACHE_DIR="${ERA5_CACHE_DIR:-$HOME/era5_cache}"
GDAS_CACHE_DIR="${GDAS_CACHE_DIR:-$HOME/gdas_cache}"
REGISTRY_ROOT="${REGISTRY_ROOT:-$HOME/.anemoi/registry}"
SEED="${SEED:-20260806}"
N_AUGMENT="${N_AUGMENT:-3}"

if [ ! -f "$HURDAT2" ]; then
  echo "HURDAT2 archive not found at $HURDAT2 -- fetch it first:" >&2
  echo "  curl -o $HURDAT2 https://www.nhc.noaa.gov/data/hurdat/hurdat2-atl-1851-2023-042624.txt" >&2
  exit 1
fi

uv run anemoi train-schedule \
  --mode "$MODE" \
  --hurdat2 "$HURDAT2" \
  --era5-cache-dir "$ERA5_CACHE_DIR" \
  --gdas-cache-dir "$GDAS_CACHE_DIR" \
  --registry-root "$REGISTRY_ROOT" \
  --seed "$SEED" \
  --n-augment "$N_AUGMENT"
