# Real-mode Anemoi-API on Cloudflare Containers

Issue #91's primary proposal, spiked. `Dockerfile` packages `anemoi.api.main:app`
with `ANEMOI_API_REAL_STATE=1` (real HURDAT2 storms + real trained-model
inference via #78/#85, `anemoi.api.real_state.RealState`) as a real
`linux/amd64` container -- not the Pyodide-based Python Workers runtime,
which has no PyTorch wheel available. `wrangler.jsonc` + `src/index.ts` are
the Worker front door Cloudflare Containers requires (a Durable Object
binding routes requests into the container).

## Spike result (2026-09-21)

Built and smoke-tested locally (`podman`, aliased to `docker`) -- the one
open risk #91 flagged before committing to this proposal:

- `docker build -f docker/api/Dockerfile .` succeeds, both natively
  (`aarch64`, this machine) and cross-built for `--platform linux/amd64`
  (Cloudflare's required architecture, via emulation) -- confirms the image
  isn't accidentally arch-locked to the build host.
- CPU-only torch installs cleanly: `torch.__version__` reports a `+cpu`
  build, `torch.cuda.is_available()` is `False`, confirming pip never
  pulled the much larger default CUDA wheel (Cloudflare Containers has no
  GPU instances -- see #91).
- `anemoi.api.real_state`, `anemoi.training.real_inference_cycle`, and
  `anemoi.training.real_inference_ensemble` all import successfully inside
  the built image.
- Final image size: **1.78 GB** -- comfortably inside Cloudflare's 20 GB
  limit on the `standard-4` instance tier.
- Running the image and hitting `GET /v1/health` returns
  `{"state_mode": "real", "torch_available": true, ...}` -- the server
  boots and serves real-mode traffic correctly.
- `GET /v1/storms` returns `500` with `RealState needs a real HURDAT2
  archive -- set HURDAT2_PATH or pass hurdat2_path explicitly` -- expected:
  this spike ran with no config. Real deployment needs `HURDAT2_PATH` plus
  the S3/R2 credentials `CheckpointStore`/`ModelRegistry` need (`S3_ARTIFACT_*`,
  same vars `docker/mlflow/README.md` documents) as container secrets, not
  new infrastructure.

**Conclusion: no architectural blocker found.** Proposal A (Containers,
issue #91) stands; Proposal B (Python Workers demo + real-mode off
Cloudflare) is not needed as a fallback.

## What's NOT done yet

This repo has no Cloudflare account credentials configured, so nothing
here has actually been deployed -- `npx wrangler deploy` (from this
directory, after `wrangler login` or `CLOUDFLARE_API_TOKEN`) is the real
next step once that access exists. Also not done, per #91's remaining
scope:

- Demo/real routing in the Worker (`src/index.ts` currently forwards
  everything into the container unconditionally).
- The console (`console/`) deploying to Cloudflare Workers/Pages.
- CI building and pushing this image on merge to `main`.
- Wiki documentation of the live deployment topology.

## Local build/run

```bash
docker build -f docker/api/Dockerfile -t anemoi-api-real:spike .
docker run --rm -p 8080:8080 \
  -e HURDAT2_PATH=/path/to/hurdat2.txt \
  -e S3_ARTIFACT_API_ENDPOINT=... -e S3_ARTIFACT_BUCKET=... \
  -e S3_ARTIFACT_ACCESS_KEYID=... -e S3_ARTIFACT_SECRET_ACCESS_KEY=... \
  anemoi-api-real:spike
curl http://127.0.0.1:8080/v1/health
```

## Deploying for real (once Cloudflare credentials are available)

```bash
cd docker/api
npm install
npx wrangler secret put HURDAT2_PATH        # or bake into the image / a mounted volume
npx wrangler secret put S3_ARTIFACT_ACCESS_KEYID
npx wrangler secret put S3_ARTIFACT_SECRET_ACCESS_KEY
npx wrangler deploy
```

Docker (or a Docker-compatible daemon reachable the way `wrangler` expects)
must be running locally during `wrangler deploy` -- it builds and pushes
the image as part of the deploy.
