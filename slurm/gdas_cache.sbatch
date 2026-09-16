#!/bin/bash
#SBATCH --job-name=gdas-cache
#SBATCH --output=logs/%x-%j.log
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
# No GPU -- I/O-bound (data.gdas_cache), Stage B analog of era5_cache.sbatch.
# Lower default concurrency than ERA5 (4 vs 8): many fixes share the same
# underlying GRIB2 file's byte ranges, see gdas_cache.run_fetch_cache's
# docstring for why hammering one NOAA object harder isn't free here.
# Needs the real libeccodes system library, not just `pip install eccodes`
# (that package is pure-Python bindings only): `sudo apt-get install
# libeccodes0` on this VM's Ubuntu 22.04 -- see docs/train_infrastructure.md
# and real_gridded.py's module docstring for the "prebuilt binary" claim
# this corrects.
#
# Real SLURM cluster:  sbatch slurm/gdas_cache.sbatch [split]
# This VM (no scheduler): slurm/run_local.sh slurm/gdas_cache.sbatch [split]

set -euo pipefail
cd "$(dirname "$0")/.."
source "$HOME/.local/bin/env" 2>/dev/null || true  # uv, if installed via astral's installer

SPLIT="${1:-train}"
HURDAT2="${HURDAT2_PATH:-$HOME/hurdat2-atl.txt}"
CACHE_DIR="${CACHE_DIR:-$HOME/gdas_cache}"
MAX_WORKERS="${MAX_WORKERS:-4}"

if [ ! -f "$HURDAT2" ]; then
  echo "HURDAT2 archive not found at $HURDAT2 -- fetch it first:" >&2
  echo "  curl -o $HURDAT2 https://www.nhc.noaa.gov/data/hurdat/hurdat2-atl-1851-2023-042624.txt" >&2
  exit 1
fi

uv run anemoi gdas-cache \
  --hurdat2 "$HURDAT2" \
  --cache-dir "$CACHE_DIR" \
  --split "$SPLIT" \
  --max-workers "$MAX_WORKERS"
