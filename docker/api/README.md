# Real-mode Anemoi-API on Cloudflare Containers

Issue #91's primary proposal. `Dockerfile` packages `anemoi.api.main:app`
with `ANEMOI_API_REAL_STATE=1` (real HURDAT2 storms + real trained-model
inference via #78/#85, `anemoi.api.real_state.RealState`) as a real
`linux/amd64` container -- not the Pyodide-based Python Workers runtime,
which has no PyTorch wheel available. `wrangler.jsonc` + `src/index.ts` are
the Worker front door Cloudflare Containers requires (a Durable Object
binding routes requests into the container). Types (`Env`,
`ExportedHandler`, container/DO runtime types) are generated, not
hand-written -- see "Regenerating types" below.

## Status: deployed and serving real storms + real registry data (2026-09-21)

Live at `https://anemoi-api-real.jasonkolodziej.workers.dev`. Confirmed for
real, not just built-then-assumed:

- `GET /v1/health` -> `{"state_mode": "real", "torch_available": true, ...}`
- `GET /v1/storms` -> real 2023-season HURDAT2 storms
- `GET /v1/registry` -> all 7 real models at their real, verified versions
  from the completed training run (`lstm v6`, `cnn v5`, `transformer v4`,
  `gnn v4`, `pinn v4`, `diffusion v3`, `fusion v3`) -- the registry-data
  gap below is resolved.

Not yet exercised: an actual `POST .../cycles` real forecast end to end
(the pieces are now all in place -- real storms, real registry, real
checkpoints in R2 -- but running one for real and checking the output is
still a distinct, not-yet-done step).

Spike findings (all confirmed, not just built-then-assumed):

- CPU-only torch installs cleanly (`torch.cuda.is_available()` is `False`);
  no GPU wheel pulled. Cloudflare Containers has no GPU instances, but
  real-mode only ever does *inference* (a handful of small forward passes
  plus one diffusion `sample()` call per cycle, see #91), not training.
- `anemoi.api.real_state`, `anemoi.training.real_inference_cycle`, and
  `anemoi.training.real_inference_ensemble` all import successfully inside
  the built image.
- Builds cleanly both natively (`aarch64`) and cross-built for
  `linux/amd64` (Cloudflare's required architecture).

**Conclusion holds: no architectural blocker.** Proposal A (Containers,
issue #91) stands; Proposal B (Python Workers demo + real-mode off
Cloudflare) is not needed as a fallback.

## Six real problems hit during the actual deploy, and their fixes

Worth recording -- none of these were visible from the local `docker
build` spike alone, only from a real `wrangler deploy` attempt:

1. **`image_build_context`.** Cloudflare Containers defaults the Docker
   build context to the Dockerfile's own directory (`docker/api/`), but
   this Dockerfile's `COPY pyproject.toml ... / COPY src ./src` expect the
   repo root. Fixed by setting `"image_build_context": "../.."` in
   `wrangler.jsonc` (see the comment there).
2. **`instance_type`.** The built image is ~2.2GB; the default instance
   type (`lite`) caps images at 2000MB, so the deploy failed with "Image
   too large" until `instance_type: "standard-1"` (4GiB memory / 8GB disk)
   was set explicitly in `wrangler.jsonc`.
3. **`DOCKER_HOST` pointed at podman.** This machine's shell has
   `DOCKER_HOST` set globally to a podman-machine socket, so *even the
   real Docker Desktop CLI* silently talked to podman instead of Docker
   Desktop's own engine. Podman's pushed image manifest didn't match the
   digest Wrangler expected from Cloudflare's registry, failing with
   `IMAGE_REGISTRY_DOESNT_CONTAIN_IMAGE` even though the push itself
   reported success. Root-caused by comparing `docker context ls` (shows
   `desktop-linux` as the selected context) against `echo $DOCKER_HOST`
   (pointed at podman regardless) -- `DOCKER_HOST` overrides context
   selection. This bit us twice: once diagnosed and worked around
   one-off with `env -u DOCKER_HOST`, then again when `pnpm cf:deploy`
   was run plainly in a fresh shell (same `DOCKER_HOST` still set) and
   failed the exact same way -- the fix wasn't durable until it moved
   into the script itself. **Fixed for good** by baking `env -u
   DOCKER_HOST` into the `dev`/`cf:deploy` scripts in `package.json`, so
   `pnpm run cf:deploy` (or `pnpm cf:deploy`) is safe regardless of shell
   state; invoking `wrangler deploy` directly (bypassing the npm script)
   still needs the manual override. Cloudflare's own container tooling
   has a documented, unresolved podman incompatibility
   ([workers-sdk#9755](https://github.com/cloudflare/workers-sdk/issues/9755)).
4. **A transient 500 on `/v1/storms` right after the HURDAT2 fix landed,
   that turned out not to be a real bug.** Its response body was plain
   text `Internal Server Error`, not FastAPI's JSON error shape -- a sign
   it came from Cloudflare's own edge/platform layer (e.g. mid
   provisioning) rather than the Python app. `wrangler containers ssh`
   couldn't confirm this directly (needs an `authorized_keys` config this
   deployment doesn't have, and its own instances kept scaling back to
   `inactive` faster than a manual SSH attempt could catch one -- see the
   `ANEMOI_API_DEBUG` addition below, added specifically because this was
   otherwise unreachable). Several follow-up requests all returned clean
   200s, confirming it wasn't a real, reproducible bug in the app.
5. **`wrangler secret put` secrets never reached the container process at
   all.** Confirmed by reading `@cloudflare/containers`' own source
   (`dist/lib/container.js`): `Container.envVars` defaults to `{}` and is
   never auto-populated from the Worker's `env` bindings -- secrets set via
   `wrangler secret put` are Worker-level only. `S3_ARTIFACT_*` looked
   configured (`wrangler secret list` showed all four) but never actually
   reached Python's `os.environ`; `RealState.run_cycle`'s broad exception
   handling silently swallowed the resulting `CheckpointStoreError` into
   the synthetic fallback, so this produced no visible error at all until
   traced through the SDK source directly. Fixed in `index.ts`:
   `AnemoiRealApi`'s constructor now explicitly forwards the four secrets
   into `envVars` via `super(ctx, env, { envVars: {...} })`.
6. **A redeploy does not restart an already-running container instance.**
   Cloudflare Containers here run as a single long-lived "singleton"
   instance (same instance ID persists across multiple `wrangler deploy`
   runs, confirmed via `wrangler containers instances`) -- a new image only
   takes effect on the *next natural cold start* (after `sleepAfter`, 5m
   here, with zero requests). Cost several rounds of "why didn't my fix
   take effect" confusion: `/v1/registry` still came back empty right
   after deploying the registry-sync fix, not because the fix was wrong,
   but because the already-warm instance from before that deploy was still
   serving the old image. Confirmed by genuinely waiting out a full idle
   `sleepAfter` window before re-checking. Worth remembering for any future
   deploy: **don't immediately re-probe after `cf:deploy` and conclude a
   fix failed** -- either wait out `sleepAfter`, or accept the previous
   instance keeps serving until it naturally sleeps.

`anemoi.api.main.create_app` gained `ANEMOI_API_DEBUG` (off by default)
while chasing problem 4 -- when set, an unhandled exception returns its
real traceback in the response body (Starlette's own debug mode) instead
of a bare "Internal Server Error." Kept permanently since container log
access here is genuinely hard to get to. A second, more invasive
diagnostic built while chasing problems 5/6 -- a temporary
`/debug/registry-pull-log` route plus a Dockerfile CMD change capturing
`anemoi registry-pull`'s real stdout/stderr to a file -- was **not** kept;
it was removed once problems 5/6 were actually diagnosed and fixed, since
unlike `ANEMOI_API_DEBUG` it hardcoded a container-specific file path and
had no purpose once the fix worked.

### SSH access

`wrangler containers ssh <instance-id>` needs an `authorized_keys` entry
under the container's `wrangler.jsonc` config (only `ssh-ed25519` keys) --
not configured until problem 6 above made shell access seem necessary. A
dedicated keypair now lives at `~/.ssh/anemoi_cf_container` (this
machine only, not committed) with its public half in `wrangler.jsonc`.
In practice this was never successfully used *during* diagnosis here --
the two gotchas above (a live instance is needed to attach to, and a
redeploy doesn't create one) made the timing genuinely hard to catch, so
the `/debug/registry-pull-log` route ended up being the thing that
actually worked. Kept configured for next time regardless; catching a
live instance is easier if you trigger a request and immediately run
`wrangler containers instances <app-id>` / `wrangler containers ssh
<instance-id>` right after, ideally right after a fresh cold start
rather than hours into a warm/idle cycle.

## What's genuinely still needed before this serves real forecasts

- ~~`HURDAT2_PATH`~~ **Done.** The archive is fetched from NHC's public
  URL at Docker build time (not `COPY`'d from a committed file -- 6.8MB
  of static data doesn't belong in git history) and `HURDAT2_PATH` is set
  via `ENV` in the `Dockerfile`, so it's already present when the
  container starts. Containers have ephemeral disk with no host to mount
  a volume from, so this genuinely couldn't have been solved by a secret
  alone -- a secret only sets an env var, it doesn't put a file anywhere.
- ~~The real registry data~~ **Done.** `tracking.registry.ModelRegistry`
  gained an optional durable-storage (R2) mirror, symmetric with its
  existing MLflow mirror: every real save now pushes `registry.json` to
  `registry/registry.json` in the same R2 bucket checkpoints already live
  in, and construction with no local file pulls one from there first. A
  new `anemoi registry-pull` CLI command wraps the read side; the
  Dockerfile's `CMD` runs it (wrapped in `|| true`, never blocking
  startup) before `uvicorn` starts. The VM's existing `registry.json` was
  pushed once manually (`CheckpointStore.upload`, no code changes needed
  for that one-time seed) to give the new pull path something real to
  hydrate from immediately, rather than waiting for the next full
  training run. Confirmed for real: `/v1/registry` on the live deployment
  now returns all 7 models at their real versions.

Also not done, per #91's remaining scope:

- Demo/real routing in the Worker (`src/index.ts` currently forwards
  everything into the container unconditionally).
- The console (`console/`) deploying to Cloudflare Workers/Pages.
- CI building and pushing this image on merge to `main`.
- Wiki documentation of the live deployment topology.

## Local build/run

```bash
docker build -f docker/api/Dockerfile -t anemoi-api-real:spike .
docker run --rm -p 8080:8080 \
  -e S3_ARTIFACT_API_ENDPOINT=... -e S3_ARTIFACT_BUCKET=... \
  -e S3_ARTIFACT_ACCESS_KEYID=... -e S3_ARTIFACT_SECRET_ACCESS_KEY=... \
  anemoi-api-real:spike
curl http://127.0.0.1:8080/v1/health
curl http://127.0.0.1:8080/v1/storms   # real HURDAT2 storms, baked into the image
```

`HURDAT2_PATH` needs no override here -- the image fetches the real
archive at build time and sets it via `ENV` (see the Dockerfile). Pass
`-e HURDAT2_PATH=... -v host/path:...` only if you want to point at a
*different* archive than the one baked in.

## Deploying

```bash
cd docker/api
pnpm install
pnpm exec wrangler login    # or set CLOUDFLARE_API_TOKEN
```

Set secrets, either one at a time:

```bash
pnpm exec wrangler secret put S3_ARTIFACT_API_ENDPOINT
pnpm exec wrangler secret put S3_ARTIFACT_BUCKET
pnpm exec wrangler secret put S3_ARTIFACT_ACCESS_KEYID
pnpm exec wrangler secret put S3_ARTIFACT_SECRET_ACCESS_KEY
```

or in bulk, which `wrangler secret bulk` accepts either as a JSON object
(`{"KEY": "value", ...}`, where a `null` value **deletes** that secret
rather than setting it -- not a way to pull from the environment) or, more
usefully here, directly as an `.env`-style file:

```bash
pnpm exec wrangler secret bulk path/to/an/.env/style/file
```

A plain JSON blob piped via `echo` puts the real secret values in your
shell history; prefer a `KEY=VALUE` file (e.g. a scratch copy of the
relevant `S3_ARTIFACT_*` lines from the repo's own `.env`) over that.

No `wrangler secret put HURDAT2_PATH` here -- it's baked into the image
at build time instead, see "What's genuinely still needed" above.

Then deploy:

```bash
pnpm run cf:deploy
```

Use `pnpm run cf:deploy` (or `pnpm cf:deploy`), not bare `pnpm deploy` --
that's a **different, built-in pnpm command** (exports a workspace
package as a standalone deploy target, unrelated to this project) and
fails with `ERR_PNPM_INVALID_DEPLOY_TARGET`. `cf:deploy` also has the
`DOCKER_HOST` fix (see problem 3 above) baked in; calling `wrangler
deploy` directly instead of through this script does not.

A real Docker engine must be reachable locally during the deploy; it
builds and pushes the image as part of it.

## Regenerating types

`worker-configuration.d.ts` (the `Env` interface, `ExportedHandler`, and
Workers/Containers/Durable Object runtime types) is generated from
`wrangler.jsonc`, not hand-written, and is committed so editors/CI don't
need an extra step to get types. Per Workers best practice, regenerate it
(and re-run `pnpm run check` to type-check `src/index.ts` against it)
after any change to `wrangler.jsonc`'s bindings:

```bash
pnpm run types  # wrangler types
pnpm run check  # tsc --noEmit
```
