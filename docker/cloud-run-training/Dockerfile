FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libeccodes0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

# torch: real model training
# tracking: optional MLflow client integration
# gridded: ERA5/GDAS real data deps
# storage: S3/R2-backed checkpoint and registry sync
RUN pip install --upgrade pip && pip install ".[torch,tracking,gridded,storage]"

# Keep the default HURDAT2 archive in-image for unattended jobs.
RUN mkdir -p /app/data \
    && curl -fsSL -o /app/data/hurdat2-atl.txt \
    https://www.nhc.noaa.gov/data/hurdat/hurdat2-atl-1851-2023-042624.txt

COPY docker/cloud-run-training/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
