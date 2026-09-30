# syntax=docker/dockerfile:1
# Single multi-stage Dockerfile for both images built from this repo: the
# real-mode Anemoi-API server (Cloudflare Containers, docker/api/wrangler.jsonc,
# #91) and the training image (Cloud Run Jobs, docker/cloud-run-training/).
# `builder-base` carries what both share verbatim (the uv image, its ENV
# block, WORKDIR); `training-builder`/`api-builder` diverge only in which
# pyproject.toml extras get pulled in (torch-cpu vs. full CUDA torch) and the
# HURDAT2 filename; `runtime-base` carries what both final images share (apt
# packages, PATH); `training`/`api` diverge in entrypoint and OCI metadata.
#
# `api` is the last stage on purpose: Cloudflare Containers builds a
# Dockerfile's final stage and has no `target` option, while Cloud Build and
# `docker/build-push-action` can both select `training` with `--target`.
# Build context is the repo root in both cases; see
# docker/multistage.Dockerfile.dockerignore.

ARG UV_IMAGE=ghcr.io/astral-sh/uv:python3.12-trixie-slim

# ---------------------------------------------------------------------------
# builder-base: everything training-builder and api-builder share verbatim.
# What they do NOT share -- the uv sync extras and the HURDAT2 filename --
# stays in each stage below rather than being parameterized here: `torch` and
# `torch-cpu` are declared mutually-conflicting extras (pyproject.toml's
# `[tool.uv] conflicts`), so this is two genuinely different venvs, not one
# venv built two ways. Dockerfile has no way to share a RUN body across
# stages without a helper script, which isn't worth it for two call sites.
# ---------------------------------------------------------------------------
FROM ${UV_IMAGE} AS builder-base

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_PYTHON_DOWNLOADS=0
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ---------------------------------------------------------------------------
# training-builder: full CUDA torch (Cloud Run Jobs training has GPUs).
# ---------------------------------------------------------------------------
FROM builder-base AS training-builder

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project \
      --extra torch \
      --extra tracking \
      --extra storage \
      --extra gridded

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked \
      --extra torch \
      --extra tracking \
      --extra storage \
      --extra gridded

# Baked in at build time under the filename docker/cloud-run-training's
# entrypoint.sh expects (HURDAT2_PATH default).
RUN mkdir -p /app/data && python3 -c "import urllib.request; urllib.request.urlretrieve('https://www.nhc.noaa.gov/data/hurdat/hurdat2-atl-1851-2023-042624.txt', '/app/data/hurdat2-atl.txt')"

# ---------------------------------------------------------------------------
# api-builder: CPU-only torch -- Cloudflare Containers has no GPUs, and real
# mode only ever runs inference (a handful of small forward passes plus one
# diffusion `sample()` per cycle).
# ---------------------------------------------------------------------------
FROM builder-base AS api-builder

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project \
      --extra api \
      --extra tracking \
      --extra storage \
      --extra gridded \
      --extra torch-cpu

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked \
      --extra api \
      --extra tracking \
      --extra storage \
      --extra gridded \
      --extra torch-cpu

RUN mkdir -p /app/data && python3 -c "import urllib.request; urllib.request.urlretrieve('https://www.nhc.noaa.gov/data/hurdat/hurdat2-atl-1851-2023-042624.txt', '/app/data/hurdat2.txt')"

# ---------------------------------------------------------------------------
# runtime-base: apt packages common to both final images. libeccodes0 is the
# native library behind the `gridded` extra's eccodes bindings (GDAS fetches,
# data.gdas_cache); ca-certificates for the outbound HTTPS both images make
# (MLflow tracking, R2/GCS, GDAS). No curl -- HURDAT2 is fetched at build
# time via python3/urllib above, not at runtime.
# ---------------------------------------------------------------------------
FROM python:3.12-slim-trixie AS runtime-base

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libeccodes0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# ---------------------------------------------------------------------------
# training: Cloud Run Jobs training image. Build with `--target training`.
# Runs as root, matching the image published today -- Cloud Run Jobs' volume
# mounts (GCS Fuse, R2 caches) are set up for that.
# ---------------------------------------------------------------------------
FROM runtime-base AS training

ARG BUILD_DATE=unknown
ARG VCS_REF=unknown
ARG VERSION=dev
ARG REPO_URL=https://github.com/jasonkolodziej/anemoi

LABEL org.opencontainers.image.title="anemoi cloud-run training" \
    org.opencontainers.image.description="Anemoi training image for Cloud Run Jobs" \
    org.opencontainers.image.licenses="AGPL-3.0-only" \
    org.opencontainers.image.source="${REPO_URL}" \
    org.opencontainers.image.url="${REPO_URL}" \
    org.opencontainers.image.version="${VERSION}" \
    org.opencontainers.image.revision="${VCS_REF}" \
    org.opencontainers.image.created="${BUILD_DATE}"

ENV IMAGE_REGISTRY=ghcr.io
ENV IMAGE_NAMESPACE=jasonkolodziej
ENV IMAGE_NAME=anemoi-train
ENV IMAGE_TAG=latest

COPY --from=training-builder /app/.venv /app/.venv
COPY --from=training-builder /app/src /app/src
COPY --from=training-builder /app/data /app/data
COPY docker/cloud-run-training/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# ---------------------------------------------------------------------------
# api: real-mode Anemoi-API server for Cloudflare Containers (#91). Last
# stage -- this is the one Cloudflare's container builder produces by default.
# ---------------------------------------------------------------------------
FROM runtime-base AS api

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid 10001 --create-home app

ENV ANEMOI_API_REAL_STATE=1
ENV HURDAT2_PATH=/app/data/hurdat2.txt
# The deployed console's origins (its custom domain and workers.dev, both
# serving the same build) plus local dev, so a local `pnpm dev` console can
# also talk to this API.
ENV ANEMOI_API_CORS_ORIGINS="https://anemoi.systems,https://anemoi-console.jasonkolodziej.workers.dev,http://localhost:5173,http://127.0.0.1:5173"

# .venv deliberately stays root-owned (no --chown): `app` never needs to
# write into it at runtime -- UV_COMPILE_BYTECODE=1 already compiled .pyc at
# build time, PYTHONDONTWRITEBYTECODE=1 stops any later attempt -- so owning
# it to `app` would only hand a compromised process write access to its own
# installed dependency tree for no functional benefit. The original
# docker/api/Dockerfile kept this property too (root ran the whole build;
# `USER nonroot` only applied at the very end, after .venv already existed).
# world-readable/executable by default, so `app` can still import from it.
COPY --from=api-builder /app/.venv /app/.venv
COPY --from=api-builder --chown=app:app /app/src /app/src
COPY --from=api-builder --chown=app:app /app/data /app/data

USER app

EXPOSE 8080

# Cloudflare Containers orchestrates readiness itself (port-listen, not
# `pingEndpoint` -- AnemoiRealApi sets neither in docker/api/src/index.ts),
# so this is never consulted in production. It matters for the local
# `docker run`/`docker compose` path docker/api/README.md documents, where
# `docker ps` otherwise reports no health status at all. `/` is the one route
# that needs no auth and no real storm/model state to return 200.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request as u; u.urlopen('http://localhost:8080/').read()" || exit 1

ENTRYPOINT []

# `anemoi registry-pull` hydrates ~/.anemoi/registry from R2 (#91); without
# it every real cycle falls back to the synthetic forecast. `|| true` so a
# misconfigured or unreachable R2 never blocks startup -- RealState already
# degrades gracefully with an empty registry.
CMD ["sh", "-c", "anemoi registry-pull || true; exec uvicorn anemoi.api.main:app --host 0.0.0.0 --port 8080"]
