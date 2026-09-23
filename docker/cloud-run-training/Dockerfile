FROM python:3.12-slim

ARG UV_TOOLS_IMAGE=ghcr.io/astral-sh/uv:0.8.22
COPY --from=${UV_TOOLS_IMAGE} /uv /uvx /bin/

ARG BUILD_DATE=unknown
ARG VCS_REF=unknown
ARG VERSION=dev
ARG REPO_URL=https://github.com/jasonkolodziej/anemoi

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_PYTHON_DOWNLOADS=0
ENV UV_CACHE_DIR=/tmp/uv-cache
ENV IMAGE_REGISTRY=ghcr.io
ENV IMAGE_NAMESPACE=jasonkolodziej
ENV IMAGE_NAME=anemoi-train
ENV IMAGE_TAG=latest
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

LABEL org.opencontainers.image.title="anemoi cloud-run training" \
    org.opencontainers.image.description="Anemoi training image for Cloud Run Jobs" \
    org.opencontainers.image.licenses="AGPL-3.0-only" \
    org.opencontainers.image.source="${REPO_URL}" \
    org.opencontainers.image.url="${REPO_URL}" \
    org.opencontainers.image.version="${VERSION}" \
    org.opencontainers.image.revision="${VCS_REF}" \
    org.opencontainers.image.created="${BUILD_DATE}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libeccodes0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md LICENSE ./

# Install third-party dependencies first for better layer reuse when app code changes.
RUN uv sync --locked --no-install-project \
    --extra torch \
    --extra tracking \
    --extra gridded \
    --extra storage \
    && rm -rf /tmp/uv-cache

COPY src ./src

# Install the project itself into the existing uv-managed environment.
RUN uv sync --locked \
    --extra torch \
    --extra tracking \
    --extra gridded \
    --extra storage \
    && rm -rf /tmp/uv-cache

# Keep the default HURDAT2 archive in-image for unattended jobs.
RUN mkdir -p /app/data \
    && curl -fsSL -o /app/data/hurdat2-atl.txt \
    https://www.nhc.noaa.gov/data/hurdat/hurdat2-atl-1851-2023-042624.txt

COPY docker/cloud-run-training/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
