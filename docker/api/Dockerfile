# Real-mode Anemoi-API server (`ANEMOI_API_REAL_STATE=1`, see
# `anemoi.api.real_state`) for Cloudflare Containers (#91). Structured after
# uv's own example (https://github.com/astral-sh/uv-docker-example): a uv
# base image, dependencies installed from `uv.lock` in their own cached layer
# before the project, and a non-root runtime user.
#
# CPU-only torch via the `torch-cpu` extra (pyproject.toml, PyTorch's CPU
# index): Cloudflare Containers has no GPUs, and real mode only ever runs
# inference -- a handful of small forward passes plus one diffusion
# `sample()` per cycle. Plain `torch` from PyPI is the multi-GB CUDA build on
# Linux and stays the training VM's path.
#
# Build context is the repo root (wrangler.jsonc `image_build_context`);
# `Dockerfile.dockerignore` next to this file limits it to the Python package.

# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim

# Setup a non-root user
RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

# libeccodes0: native library behind the `gridded` extra's eccodes bindings,
# needed for GDAS fetches (data.gdas_cache, #98's on-demand live-inference
# fetch); see data.real_gridded.require_gdas_deps.
RUN apt-get update && apt-get install -y --no-install-recommends libeccodes0 \
    && rm -rf /var/lib/apt/lists/*

# Install the project into `/app`
WORKDIR /app

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Omit development dependencies
ENV UV_NO_DEV=1

# Ensure installed tools can be executed out of the box
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Install the project's dependencies using the lockfile and settings.
# api: fastapi/uvicorn. tracking: mlflow client (registry mirror). storage:
# boto3 for CheckpointStore's R2 checkpoints. gridded: xarray/zarr/gcsfs/
# eccodes for live GDAS fields (#98). torch-cpu: see the header.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project \
      --extra api --extra tracking --extra storage --extra gridded --extra torch-cpu

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked \
      --extra api --extra tracking --extra storage --extra gridded --extra torch-cpu

# Real NHC HURDAT2 Atlantic archive, baked in at build time: static
# historical data, and Containers have ephemeral disk, so HURDAT2_PATH must
# point at a file that already exists when the container starts (see
# docker/api/README.md). Fetched rather than committed -- NHC hosts a
# durable, versioned copy at this URL.
RUN mkdir -p /app/data && python3 -c "\
import urllib.request; \
urllib.request.urlretrieve( \
    'https://www.nhc.noaa.gov/data/hurdat/hurdat2-atl-1851-2023-042624.txt', \
    '/app/data/hurdat2.txt', \
)"

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

ENV ANEMOI_API_REAL_STATE=1
ENV HURDAT2_PATH=/app/data/hurdat2.txt
# The deployed console's origins (its custom domain and workers.dev, both
# serving the same build) plus local dev, so a local `pnpm dev` console can
# also talk to this API.
ENV ANEMOI_API_CORS_ORIGINS="https://anemoi.systems,https://anemoi-console.jasonkolodziej.workers.dev,http://localhost:5173,http://127.0.0.1:5173"
EXPOSE 8080

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Use the non-root user to run our application
USER nonroot

# `anemoi registry-pull` hydrates ~/.anemoi/registry from R2 (#91); without
# it every real cycle falls back to the synthetic forecast. `|| true` so a
# misconfigured or unreachable R2 never blocks startup -- RealState already
# degrades gracefully with an empty registry. Runs the installed entry points
# directly rather than through `uv run`, per the example's production note.
CMD ["sh", "-c", "anemoi registry-pull || true; exec uvicorn anemoi.api.main:app --host 0.0.0.0 --port 8080"]
