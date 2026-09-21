# Real-mode Anemoi-API server (`ANEMOI_API_REAL_STATE=1`, see
# `anemoi.api.real_state`) -- the spike image for issue #91's primary
# proposal, Cloudflare Containers. CPU-only torch: Cloudflare Containers has
# no GPU instances today, but real-mode only ever does *inference* (a
# handful of small forward passes plus one diffusion `sample()` call per
# cycle, per `training.real_inference_cycle`/`real_inference_ensemble`), not
# training -- training stays on the GCP VM, unaffected by this image.
#
# The CPU wheel is installed explicitly, from PyTorch's own CPU index,
# *before* anemoi's own `[torch]` extra is installed -- this ordering is
# what makes the install CPU-only: pip won't re-resolve/replace an
# already-satisfied `torch>=2.2` requirement, so the much larger default
# CUDA wheel from PyPI is never downloaded.
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir "torch>=2.2" --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

# Real NHC HURDAT2 Atlantic archive -- same file used throughout this
# repo's own training infra/docs (docs/train_infrastructure.md,
# docs/capacity_ablation.md). Static historical data (NHC republishes it
# once a year after each season's reanalysis), so baking it into the
# image at *build* time is the right call, not a container startup fetch
# -- see docker/api/README.md ("What's genuinely still needed") for why
# this can't just be a secret: Containers have ephemeral disk, so
# HURDAT2_PATH needs a real file already present when the container
# starts, not just an env var pointing at one. Fetched here rather than
# `COPY`'d from a committed file -- 6.8MB of static archive data doesn't
# belong in git history when NHC already hosts a durable, versioned copy
# at this exact URL (the same one docs/train_infrastructure.md and
# docs/capacity_ablation.md already point at).
RUN mkdir -p /app/data && python3 -c "\
import urllib.request; \
urllib.request.urlretrieve( \
    'https://www.nhc.noaa.gov/data/hurdat/hurdat2-atl-1851-2023-042624.txt', \
    '/app/data/hurdat2.txt', \
)"

# api: fastapi/uvicorn. tracking: mlflow client (registry mirror; degrades
# to the local JSON store per Scope v2.1 SS10.1 if unreachable/unconfigured).
# storage: boto3, for CheckpointStore's S3/R2-backed checkpoint loading.
# No `gridded` extra -- real_inference_live.py's live feature builders read
# from GriddedFieldCache lookups (numpy only, verified by inspection), not
# xarray/zarr/gcsfs, which are only needed at training-data-fetch time.
RUN pip install --no-cache-dir ".[api,tracking,storage]"

ENV ANEMOI_API_REAL_STATE=1
ENV HURDAT2_PATH=/app/data/hurdat2.txt
EXPOSE 8080

CMD ["uvicorn", "anemoi.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
