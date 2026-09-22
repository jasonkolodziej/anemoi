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

# libeccodes0: the `gridded` extra's `eccodes` PyPI package is pure-Python
# *bindings* only -- it does not bundle the compiled native library (see
# data.real_gridded.require_gdas_deps's docstring; this bit training on a
# fresh machine before too). Needed for GDAS fetches (data.gdas_cache,
# #98's on-demand live-inference fetch), not for ERA5's pure-Python
# xarray/zarr/gcsfs path.
RUN apt-get update && apt-get install -y --no-install-recommends libeccodes0 \
    && rm -rf /var/lib/apt/lists/*

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
# gridded: xarray/zarr/gcsfs/eccodes/requests -- real_inference_live.py's
# live feature builders need this now too (#98): a cache miss fetches the
# real field on demand via data.gdas_cache.fetch_one, not just GriddedField
# lookups against an already-populated cache.
RUN pip install --no-cache-dir ".[api,tracking,storage,gridded]"

ENV ANEMOI_API_REAL_STATE=1
ENV HURDAT2_PATH=/app/data/hurdat2.txt
# The deployed console (#96, console/wrangler.jsonc) needs to be allow-
# listed explicitly -- main.py's own default only covers local dev
# (localhost:5173/127.0.0.1:5173), which a browser hitting the real
# deployed API from the real deployed console's origin doesn't match.
# anemoi.systems is the console's custom domain (console/wrangler.jsonc's
# `routes`) -- a *separate* origin from the workers.dev one, both serving
# the same build, so both need their own allow-list entry. Keeping the
# local-dev defaults too: still useful for testing a local `pnpm dev`
# console against this real deployed API directly.
ENV ANEMOI_API_CORS_ORIGINS="https://anemoi.systems,https://anemoi-console.jasonkolodziej.workers.dev,http://localhost:5173,http://127.0.0.1:5173"
EXPOSE 8080

# `anemoi registry-pull` hydrates a local registry.json from R2 (see
# tracking.registry.ModelRegistry's checkpoint_store mirror, #91) --
# without this, a fresh container has no registered model versions at
# all and every real cycle silently degrades to the synthetic fallback.
# `|| true`: this must never block startup -- RealState already degrades
# gracefully with an empty registry (same contract the registry's own
# best-effort mirror uses), so a misconfigured/unreachable R2 here should
# log and continue, not crash the container. Real errors are still
# visible: `anemoi registry-pull` run directly (not through this `|| true`)
# fails loudly, e.g. for an operator checking why real cycles aren't real.
CMD ["sh", "-c", "anemoi registry-pull || true; exec uvicorn anemoi.api.main:app --host 0.0.0.0 --port 8080"]
