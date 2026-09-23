#!/usr/bin/env bash
set -euo pipefail

MODE="${MODE:-sequential}"
HURDAT2_PATH="${HURDAT2_PATH:-/app/data/hurdat2-atl.txt}"
ERA5_CACHE_DIR="${ERA5_CACHE_DIR:-/cache/era5}"
GDAS_CACHE_DIR="${GDAS_CACHE_DIR:-/cache/gdas}"
REGISTRY_ROOT="${REGISTRY_ROOT:-/cache/registry}"
SEED="${SEED:-20260806}"
N_AUGMENT="${N_AUGMENT:-3}"
STREAMING="${STREAMING:-1}"
BATCH_SIZE="${BATCH_SIZE:-}"
NUM_WORKERS="${NUM_WORKERS:-0}"
DERIVED_FROM_CHAMPIONS="${DERIVED_FROM_CHAMPIONS:-}"
MODELS="${MODELS:-}"
# Diffusion-only regularization (#166 follow-up to early stopping) --
# both default to 0.0, unchanged pre-#166 behavior.
DIFFUSION_DROPOUT="${DIFFUSION_DROPOUT:-}"
DIFFUSION_WEIGHT_DECAY="${DIFFUSION_WEIGHT_DECAY:-}"

mkdir -p "${ERA5_CACHE_DIR}" "${GDAS_CACHE_DIR}" "${REGISTRY_ROOT}"

if [ ! -f "${HURDAT2_PATH}" ]; then
  echo "HURDAT2 archive not found at ${HURDAT2_PATH}" >&2
  echo "Set HURDAT2_PATH to a valid file or mount one into the job." >&2
  exit 1
fi

# Best-effort hydration for ephemeral workers: if a previous registry mirror
# exists in durable object storage (R2/S3), pull it before training.
anemoi registry-pull --registry-root "${REGISTRY_ROOT}" || true

# Arguments given to the job (`gcloud run jobs execute --args=...`) run that
# anemoi subcommand instead of train-schedule, so the same image and caches
# also serve one-off jobs like drift-reference-fit or spread-backtest.
if [ "$#" -gt 0 ]; then
  exec anemoi "$@"
fi

ARGS=(
  train-schedule
  --mode "${MODE}"
  --hurdat2 "${HURDAT2_PATH}"
  --era5-cache-dir "${ERA5_CACHE_DIR}"
  --gdas-cache-dir "${GDAS_CACHE_DIR}"
  --registry-root "${REGISTRY_ROOT}"
  --seed "${SEED}"
  --n-augment "${N_AUGMENT}"
)

if [ -n "${MODELS}" ]; then
  ARGS+=(--models "${MODELS}")
fi
if [ "${STREAMING}" = "1" ]; then
  ARGS+=(--streaming)
fi
if [ -n "${BATCH_SIZE}" ]; then
  ARGS+=(--batch-size "${BATCH_SIZE}")
fi
if [ -n "${NUM_WORKERS}" ]; then
  ARGS+=(--num-workers "${NUM_WORKERS}")
fi
if [ -n "${DERIVED_FROM_CHAMPIONS}" ]; then
  ARGS+=(--derived-from-champions)
fi
if [ -n "${DIFFUSION_DROPOUT}" ]; then
  ARGS+=(--diffusion-dropout "${DIFFUSION_DROPOUT}")
fi
if [ -n "${DIFFUSION_WEIGHT_DECAY}" ]; then
  ARGS+=(--diffusion-weight-decay "${DIFFUSION_WEIGHT_DECAY}")
fi

exec anemoi "${ARGS[@]}"
