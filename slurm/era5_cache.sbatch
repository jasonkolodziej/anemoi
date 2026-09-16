#!/bin/bash
#SBATCH --job-name=era5-cache
#SBATCH --output=logs/%x-%j.log
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
# No GPU -- this is an I/O-bound data-fetch job (data.era5_cache), not
# training. See docs/train_infrastructure.md for the measured throughput
# (~6.7-9s/sample even from co-located compute) this job's concurrency is
# built to amortise over the ~16k train-split fixes.
#
# Real SLURM cluster:  sbatch slurm/era5_cache.sbatch [split]
# This VM (no scheduler): slurm/run_local.sh slurm/era5_cache.sbatch [split]

set -euo pipefail
cd "$(dirname "$0")/.."
source "$HOME/.local/bin/env" 2>/dev/null || true  # uv, if installed via astral's installer

SPLIT="${1:-train}"
HURDAT2="${HURDAT2_PATH:-$HOME/hurdat2-atl.txt}"
CACHE_DIR="${CACHE_DIR:-$HOME/era5_cache}"
MAX_WORKERS="${MAX_WORKERS:-8}"
# Set SYNC_ARCHIVE=1 to also upload newly-cached files to the durable R2
# archive (needs the storage extra and S3_ARTIFACT_* in .env) -- see
# docs/train_infrastructure.md's "Durable archive" section.
SYNC_ARCHIVE_FLAG=""
[ "${SYNC_ARCHIVE:-0}" = "1" ] && SYNC_ARCHIVE_FLAG="--sync-archive"

if [ ! -f "$HURDAT2" ]; then
  echo "HURDAT2 archive not found at $HURDAT2 -- fetch it first:" >&2
  echo "  curl -o $HURDAT2 https://www.nhc.noaa.gov/data/hurdat/hurdat2-atl-1851-2023-042624.txt" >&2
  exit 1
fi

uv run anemoi era5-cache \
  --hurdat2 "$HURDAT2" \
  --cache-dir "$CACHE_DIR" \
  --split "$SPLIT" \
  --max-workers "$MAX_WORKERS" \
  $SYNC_ARCHIVE_FLAG
