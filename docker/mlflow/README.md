# MLflow tracking server

Real, running infrastructure for the "MLflow is the intended backend" half
of `tracking.registry.ModelRegistry` (wiki: Model-Registry.md,
Storage-and-Versioning.md's "MLflow artifact store" table) -- Postgres
backend store, R2-backed artifact store, matching the wiki's target
architecture exactly.

`cli.cmd_train`/`cmd_train_schedule` already construct `ModelRegistry` with
`tracking.mlflow_client.mlflow_client_from_env()` -- set `MLFLOW_TRACKING_URI`
(below) and a real training run mirrors to this server automatically,
alongside the local JSON store it always writes regardless (Scope v2.1
§10.1: MLflow being absent, unreachable, or never configured must never
fail a training run -- `mlflow_client_from_env()` returns `None` in all
three cases, which `ModelRegistry` already treats identically).

`tracking.experiment_tracking` closes the rest of the loop: every real
training run now builds a real, validated `RunTags` (real git commit,
storm split, GPU type -- see wiki Experiment-Tracking.md) and, when a
client is configured, logs one real MLflow run per completed curriculum
stage under the correct wind-god experiment name. `ModelRegistry`'s
Model Registry mirror was also fixed to match the real `MlflowClient` API
(`create_registered_model` called first, a real artifact-URI `source`,
TitleCase stage strings) -- the mismatch noted in an earlier version of
this file is resolved.

## Setup

Add to the repo root `.env` (alongside the existing `S3_ARTIFACT_*` vars
`tracking.checkpoint_store` already uses -- this reuses that same R2
bucket under a new `mlflow-artifacts/` prefix, not a new bucket):

```bash
MLFLOW_DB_USER=mlflow
MLFLOW_DB_PASSWORD=<pick a real password>
MLFLOW_DB_NAME=mlflow
# MLFLOW_TRACKING_PORT=5000   # optional, defaults to 5000
```

Then:

```bash
cd docker/mlflow
docker compose --env-file ../../.env up -d
open http://localhost:5000
```

`--env-file` is required, not cosmetic -- see the comment at the top of
`docker-compose.yml` for why (it resolves this file's own `${VAR}`
placeholders; the `env_file:` lines inside it only cover what the
containers see at runtime, a separate mechanism).

Point a training run or client at it (add to `.env` so `anemoi train`/
`train-schedule` pick it up automatically, or export directly):

```bash
MLFLOW_TRACKING_URI=http://localhost:5000
# or, once behind a Cloudflare Tunnel (see "Authentication" below):
MLFLOW_TRACKING_URI=https://mlflow.your-domain.example
CF_ACCESS_CLIENT_ID=<service token client id>
CF_ACCESS_CLIENT_SECRET=<service token client secret>
```

## Authentication

The wiki's target design says "internal MLflow server with authentication."
The intended real deployment is **Cloudflare Tunnel + Cloudflare Access**
in front of this container (not MLflow's own basic-auth, and not exposing
port 5000 directly) -- `cloudflared` runs alongside this compose file (or
on whatever host fronts it) and proxies to `mlflow:5000` over the tunnel;
Cloudflare Access then gates every request with your Zero Trust policy.

**Client side:** MLflow's own REST client has no built-in way to attach
custom headers, which Access's machine-to-machine auth needs (a *service
token*'s `CF-Access-Client-Id`/`CF-Access-Client-Secret` headers -- not the
browser SSO flow, since training runs and CLI clients aren't a browser).
`tracking.cloudflare_access.CloudflareAccessRequestHeaderProvider` fills
this gap via MLflow's own plugin system: registered as a
`mlflow.request_header_provider` entry point in this project's
`pyproject.toml`, MLflow discovers and calls it on every outgoing request
automatically once the package is installed with the `tracking` extra --
nothing to configure at each call site. It's a no-op whenever the two env
vars below aren't set, so having it installed is harmless against a server
that isn't behind Access (e.g. this compose file run locally without a
tunnel in front of it).

```bash
# Cloudflare Zero Trust dashboard: Access > Service Auth > Service Tokens
# -- create one scoped to this MLflow server's Access application, then:
CF_ACCESS_CLIENT_ID=<service token client id>
CF_ACCESS_CLIENT_SECRET=<service token client secret>
```

Setting up the tunnel and Access application itself (DNS, the Access
policy, `cloudflared`'s own config) is real Cloudflare-side configuration
this README doesn't attempt to template -- follow Cloudflare's own docs
for Tunnel + Access for that part; this repo's responsibility ends at "the
Python client sends the right headers once you've done that."

If you're not using Cloudflare Access, MLflow's own basic-auth
(`mlflow server --app-name basic-auth`) is the fallback -- see
<https://mlflow.org/docs/latest/self-hosting/security/basic-http-auth/>
rather than a guessed `basic_auth.ini` here going stale. Short of either,
the minimum real mitigation if this is reachable outside `localhost` is an
SSH tunnel to wherever it runs, not exposing port 5000 directly.

## Data lifecycle

- `mlflow-postgres-data` (Docker named volume): experiment/run metadata.
  Back this up like any database you don't want to lose -- `docker exec
  anemoi-mlflow-postgres pg_dump -U ${MLFLOW_DB_USER} ${MLFLOW_DB_NAME}` is
  the plain way.
- Artifacts live in R2 under `mlflow-artifacts/`, already covered by
  whatever backup/retention policy applies to that bucket
  (docs/train_infrastructure.md's "Durable archive" section).
