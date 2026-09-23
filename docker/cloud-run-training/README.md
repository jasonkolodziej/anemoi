# Cloud Run training job

Source Plan: PLAN.md §5 (sample size, real Stage A/B training)
Related stream: #22 real training infrastructure

This folder packages Anemoi training for Google Cloud Run Jobs.
It runs training directly through the CLI (`anemoi train-schedule`) and does not require any SLURM scripts.

## What is in this folder

- `Dockerfile`: builds a training image with `torch`, `gridded`, `storage`, and `tracking` extras.
- `entrypoint.sh`: translates environment variables into `anemoi train-schedule` CLI arguments, or runs any other `anemoi` subcommand passed as job arguments (see "One-off commands").
- `cloudbuild.yaml`: builds the image with Cloud Build and pushes it to Artifact Registry.
- `workflows.train-schedule.yaml`: runs the per-model jobs in order (see "Workflow orchestration").

## Why Cloud Run Job (not service)

Training is batch work that runs to completion and exits. Cloud Run Jobs are the native fit for that execution model.

## Important runtime constraint

GPU-backed Cloud Run Job tasks have a maximum task timeout of 1 hour (CPU-only tasks: up to 168 hours).
If your real run exceeds 1 hour, use one of these patterns:

1. Run CPU-only jobs with longer timeout.
2. Split work into shorter executions (for example by model subset using `MODELS=` and/or by using `DERIVED_FROM_CHAMPIONS=1`).

## Prerequisites

1. A Google Cloud project with billing enabled.
2. APIs enabled: Cloud Run, Artifact Registry, Cloud Build, Secret Manager, and (for orchestration) Workflows:

   ```bash
   gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
     cloudbuild.googleapis.com secretmanager.googleapis.com workflows.googleapis.com
   ```

3. An Artifact Registry Docker repository for the image (`gcloud artifacts repositories create anemoi --repository-format docker --location us-central1`).
4. Secrets in Secret Manager for checkpoint/object storage credentials:
   - `S3_ARTIFACT_API_ENDPOINT`
   - `S3_ARTIFACT_BUCKET`
   - `S3_ARTIFACT_ACCESS_KEYID`
   - `S3_ARTIFACT_SECRET_ACCESS_KEY`
5. Optional, for MLflow tracking parity with the VM: `MLFLOW_TRACKING_URI` as an env var, plus `CF_ACCESS_CLIENT_ID`/`CF_ACCESS_CLIENT_SECRET` as secrets (the MLflow server sits behind Cloudflare Access). Without them tracking degrades to the local JSON store; the registry itself is still mirrored to R2.
6. The job's service account (the default compute service account unless you set `--service-account`) needs `roles/secretmanager.secretAccessor` on those secrets and `roles/storage.objectUser` on the cache bucket.
7. Optional but recommended: a Cloud Storage bucket mounted at `/cache` for the ERA5/GDAS caches between runs.

## Build and push image

Run from repository root. `gcloud builds submit --tag` alone won't work here: it only builds a Dockerfile at the root of the uploaded source, and this one lives in `docker/cloud-run-training/`.

```bash
gcloud builds submit \
  --config docker/cloud-run-training/cloudbuild.yaml \
  --substitutions _IMAGE=us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/anemoi-train,_TAG=$(git rev-parse --short=12 HEAD) \
  .
```

## Build and push image to GHCR

Cloud Run can pull GHCR images directly only if the package is **public**. GitHub creates packages as private by default, and a private one needs an [Artifact Registry remote repository](https://cloud.google.com/artifact-registry/docs/repositories/remote-repo) holding GitHub credentials. The Artifact Registry build above avoids both.

Use repository-root context so `COPY pyproject.toml README.md LICENSE ./` resolves correctly.

```bash
export GHCR_REGISTRY=ghcr.io
export GHCR_NAMESPACE=<github-owner>
export GHCR_IMAGE=anemoi-train
export GHCR_TAG=$(git rev-parse --short=12 HEAD)
export IMAGE_URI=${GHCR_REGISTRY}/${GHCR_NAMESPACE}/${GHCR_IMAGE}:${GHCR_TAG}
```

Log in:

```bash
echo "${GHCR_PAT}" | docker login ghcr.io -u "${GHCR_NAMESPACE}" --password-stdin
```

Build and push:

```bash
docker build \
  -f docker/cloud-run-training/Dockerfile \
  --build-arg UV_TOOLS_IMAGE=ghcr.io/astral-sh/uv:0.8.22 \
  --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --build-arg VCS_REF="$(git rev-parse HEAD)" \
  --build-arg VERSION="${GHCR_TAG}" \
  --build-arg REPO_URL="https://github.com/${GHCR_NAMESPACE}/anemoi" \
  -t "${IMAGE_URI}" \
  -t "${GHCR_REGISTRY}/${GHCR_NAMESPACE}/${GHCR_IMAGE}:latest" \
  .

docker push "${IMAGE_URI}"
docker push "${GHCR_REGISTRY}/${GHCR_NAMESPACE}/${GHCR_IMAGE}:latest"
```

`UV_TOOLS_IMAGE` is pinned in the Dockerfile and can be bumped intentionally during upgrades.

If `docker login ghcr.io` returns HTTP 403:

1. Verify `GHCR_PAT` is a classic PAT with `write:packages` and `read:packages`.
2. If the repository is private, add `repo` scope too.
3. Confirm `GHCR_NAMESPACE` matches the PAT owner account exactly.
4. Re-run login from a shell where `GHCR_PAT` is actually set (`echo ${GHCR_PAT}` should be non-empty).
5. If SSO is enforced in your org, authorize the PAT for that org.

### Troubleshooting Build

> [!TIP]
> When error is related to host storage exhaustion, you likely need to free local image/layer storage once.

**Docker backend:**

```bash
docker system df
docker image prune -a -f
docker container prune -f
docker volume prune -f
docker builder prune -a -f
docker system prune -a -f
```

**Podman backend:**

```bash
podman system df
podman image prune -a -f
podman container prune -f
podman volume prune -f
podman system prune -a -f
```

## Create a Cloud Run Job (CPU baseline)

This profile avoids the 1-hour GPU task cap and is the easiest migration path.

```bash
gcloud run jobs create anemoi-train-schedule \
  --region us-central1 \
  --image us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/anemoi-train:latest \
  --tasks 1 \
  --parallelism 1 \
  --max-retries 0 \
  --task-timeout 86400s \
  --cpu 8 \
  --memory 32Gi \
  --set-env-vars MODE=sequential,STREAMING=1,NUM_WORKERS=4,ERA5_CACHE_DIR=/cache/era5_cache,GDAS_CACHE_DIR=/cache/gdas_cache,REGISTRY_ROOT=/tmp/registry,HURDAT2_PATH=/app/data/hurdat2-atl.txt \
  --set-secrets S3_ARTIFACT_API_ENDPOINT=S3_ARTIFACT_API_ENDPOINT:latest,S3_ARTIFACT_BUCKET=S3_ARTIFACT_BUCKET:latest,S3_ARTIFACT_ACCESS_KEYID=S3_ARTIFACT_ACCESS_KEYID:latest,S3_ARTIFACT_SECRET_ACCESS_KEY=S3_ARTIFACT_SECRET_ACCESS_KEY:latest
```

`REGISTRY_ROOT` can stay on local disk: `entrypoint.sh` runs `anemoi registry-pull` first, and the registry is mirrored to R2, so it doesn't need the cache bucket.

If you want persistent local cache paths between runs, mount Cloud Storage to `/cache`:

```bash
gcloud run jobs update anemoi-train-schedule \
  --region us-central1 \
  --add-volume mount-path=/cache,type=cloud-storage,bucket=${CACHE_BUCKET}
```

## Seed /cache from an existing VM snapshot

Cloud Run cannot attach a Compute Engine boot disk directly.
To reuse the data from an existing VM boot snapshot, copy it into the Cloud Storage bucket used for `/cache`.

### 1) Create a disk from your snapshot

The training VM's disk is snapshotted on each zone migration (`gcloud compute snapshots list`; the latest is `anemoi-train-1-migrate-20260923`). Snapshots are global, so any zone works; the helper VM needs no GPU.

```bash
gcloud compute disks create anemoi-train-from-snap \
  --project ${PROJECT_ID} \
  --zone us-central1-c \
  --source-snapshot ${SNAPSHOT_NAME} \
  --type pd-balanced \
  --size 100GB
```

### 2) Attach that disk to a helper VM

```bash
gcloud compute instances attach-disk ${HELPER_VM} \
  --project ${PROJECT_ID} \
  --zone us-central1-c \
  --disk anemoi-train-from-snap
```

### 3) Mount and inspect the copied disk

```bash
# Run on the helper VM.
lsblk
sudo mkdir -p /mnt/anemoi-snap

# Example partition path. Confirm yours from lsblk output.
sudo mount /dev/sdb1 /mnt/anemoi-snap
```

### 4) Sync only needed paths into your cache bucket

```bash
# Run on the helper VM.
gsutil -m rsync -r /mnt/anemoi-snap/home/${VM_USER}/era5_cache gs://${CACHE_BUCKET}/era5_cache
gsutil -m rsync -r /mnt/anemoi-snap/home/${VM_USER}/gdas_cache gs://${CACHE_BUCKET}/gdas_cache
```

The registry isn't copied: it's mirrored to R2 and pulled at job start. On the training VM `VM_USER` is `jasonkolodziej`.

### 5) Point job env vars to mounted cache paths

These match the job commands in this README; only needed if you created a job with other paths.

```bash
gcloud run jobs update anemoi-train-schedule \
  --region us-central1 \
  --update-env-vars ERA5_CACHE_DIR=/cache/era5_cache,GDAS_CACHE_DIR=/cache/gdas_cache
```

### 6) Clean up helper resources

```bash
# Run on helper VM first.
sudo umount /mnt/anemoi-snap

# Then from your workstation.
gcloud compute instances detach-disk ${HELPER_VM} \
  --project ${PROJECT_ID} \
  --zone us-central1-c \
  --disk anemoi-train-from-snap

gcloud compute disks delete anemoi-train-from-snap \
  --project ${PROJECT_ID} \
  --zone us-central1-c
```

This preserves your expensive pre-fetched caches while keeping Cloud Run stateless at the compute layer.

## Optional GPU update

For L4, Cloud Run requires at least 4 CPU and 16 GiB memory, and GPU jobs must set `--no-gpu-zonal-redundancy`.
Remember task timeout is limited to 3600s for GPU tasks.
Cloud Run's GPU driver is 580.x (CUDA 13.0), which matches the CUDA build of torch the image installs from `uv.lock`.

```bash
gcloud run jobs update anemoi-train-schedule \
  --region us-central1 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --no-gpu-zonal-redundancy \
  --cpu 4 \
  --memory 16Gi \
  --task-timeout 3600s
```

## Recommended multi-job GPU split plan

Source Plan: PLAN.md §5 and #22 execution stream.

If you want to use Cloud Run GPU jobs, split the schedule into independent executions.
Each execution should run a narrow unit of work and write checkpoints to object storage.

Current practical split:

1. `anemoi-train-lstm` with `MODELS=lstm`
2. `anemoi-train-cnn` with `MODELS=cnn`
3. `anemoi-train-transformer` with `MODELS=transformer`
4. `anemoi-train-gnn` with `MODELS=gnn`
5. `anemoi-train-pinn` with `MODELS=pinn`
6. `anemoi-train-derived` with `DERIVED_FROM_CHAMPIONS=1`

Why this shape:

- Group 1 models are isolated, so one failure does not invalidate all others.
- The derived run (`latents/diffusion/fusion`) is started only after all Group 1 runs complete.
- Every run reuses the same image and entrypoint, only env vars differ.

Important limitation today:

- Splitting by model does not guarantee sub-1-hour completion for every model.
- In current real runs, some models can exceed one hour depending on cache size and runtime conditions.
- If strict sub-1-hour GPU tasks are mandatory, you need finer-grained CLI units than currently exposed (for example stage-level or shard-level commands).

Create one model-specific GPU job (repeat with different `MODELS=` values):

```bash
gcloud run jobs create anemoi-train-lstm \
  --region us-central1 \
  --image us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/anemoi-train:latest \
  --tasks 1 \
  --parallelism 1 \
  --max-retries 0 \
  --task-timeout 3600s \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --no-gpu-zonal-redundancy \
  --cpu 4 \
  --memory 16Gi \
  --set-env-vars MODE=sequential,MODELS=lstm,STREAMING=1,NUM_WORKERS=4,ERA5_CACHE_DIR=/cache/era5_cache,GDAS_CACHE_DIR=/cache/gdas_cache,REGISTRY_ROOT=/tmp/registry,HURDAT2_PATH=/app/data/hurdat2-atl.txt \
  --set-secrets S3_ARTIFACT_API_ENDPOINT=S3_ARTIFACT_API_ENDPOINT:latest,S3_ARTIFACT_BUCKET=S3_ARTIFACT_BUCKET:latest,S3_ARTIFACT_ACCESS_KEYID=S3_ARTIFACT_ACCESS_KEYID:latest,S3_ARTIFACT_SECRET_ACCESS_KEY=S3_ARTIFACT_SECRET_ACCESS_KEY:latest
```

Create derived-only job:

```bash
gcloud run jobs create anemoi-train-derived \
  --region us-central1 \
  --image us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/anemoi-train:latest \
  --tasks 1 \
  --parallelism 1 \
  --max-retries 0 \
  --task-timeout 3600s \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --no-gpu-zonal-redundancy \
  --cpu 4 \
  --memory 16Gi \
  --set-env-vars MODE=sequential,DERIVED_FROM_CHAMPIONS=1,STREAMING=1,NUM_WORKERS=4,ERA5_CACHE_DIR=/cache/era5_cache,GDAS_CACHE_DIR=/cache/gdas_cache,REGISTRY_ROOT=/tmp/registry,HURDAT2_PATH=/app/data/hurdat2-atl.txt \
  --set-secrets S3_ARTIFACT_API_ENDPOINT=S3_ARTIFACT_API_ENDPOINT:latest,S3_ARTIFACT_BUCKET=S3_ARTIFACT_BUCKET:latest,S3_ARTIFACT_ACCESS_KEYID=S3_ARTIFACT_ACCESS_KEYID:latest,S3_ARTIFACT_SECRET_ACCESS_KEY=S3_ARTIFACT_SECRET_ACCESS_KEY:latest
```

Execute in order:

```bash
gcloud run jobs execute anemoi-train-lstm --region us-central1
gcloud run jobs execute anemoi-train-cnn --region us-central1
gcloud run jobs execute anemoi-train-transformer --region us-central1
gcloud run jobs execute anemoi-train-gnn --region us-central1
gcloud run jobs execute anemoi-train-pinn --region us-central1
gcloud run jobs execute anemoi-train-derived --region us-central1
```

For automation, run this order from Cloud Workflows or CI/CD, and gate each step on successful completion.

## Workflow orchestration (included)

This folder includes `workflows.train-schedule.yaml`, a Cloud Workflows definition that:

1. Runs the six Cloud Run jobs in order.
2. Waits for each Run API operation to finish.
3. Waits for each execution to reach a terminal state.
4. Stops immediately on first failed/cancelled execution.

Deploy the workflow:

```bash
gcloud workflows deploy anemoi-train-orchestrator \
  --location us-central1 \
  --source docker/cloud-run-training/workflows.train-schedule.yaml
```

Execute with defaults (uses the six `anemoi-train-*` jobs listed above):

```bash
gcloud workflows run anemoi-train-orchestrator \
  --location us-central1 \
  --data '{"projectId":"'"${PROJECT_ID}"'","region":"us-central1"}'
```

Execute with custom job list and polling settings:

```bash
gcloud workflows run anemoi-train-orchestrator \
  --location us-central1 \
  --data '{
    "projectId": "'"${PROJECT_ID}"'",
    "region": "us-central1",
    "jobs": [
      "anemoi-train-lstm",
      "anemoi-train-cnn",
      "anemoi-train-transformer",
      "anemoi-train-gnn",
      "anemoi-train-pinn",
      "anemoi-train-derived"
    ],
    "pollSeconds": 20,
    "maxPollCycles": 360
  }'
```

`maxPollCycles * pollSeconds` is the per-job upper wait bound before the workflow aborts.

## Execute the job

```bash
gcloud run jobs execute anemoi-train-schedule --region us-central1
```

## One-off commands

Pass arguments to run any `anemoi` subcommand with the same image, secrets, and cache mount instead of `train-schedule`. For example, fitting the drift reference the API's drift monitoring needs (CPU-only, reads the GDAS cache, uploads to R2):

```bash
gcloud run jobs execute anemoi-train-schedule --region us-central1 \
  --args=drift-reference-fit,--gdas-cache-dir,/cache/gdas_cache,--registry-root,/tmp/registry
```

## Common env knobs

- `MODE=sequential|parallel`
- `MODELS=lstm,cnn,transformer,gnn,pinn`
- `STREAMING=1` enables the streaming DataLoader path. It defaults to on in this entrypoint but off in the VM's `slurm/train_schedule.sbatch`, so set it explicitly when comparing runs across the two.
- `NUM_WORKERS=0..N` DataLoader workers
- `BATCH_SIZE=<int>` optional explicit batch size
- `DERIVED_FROM_CHAMPIONS=1` retrains only `latents/diffusion/fusion`

## Notes

- The container defaults `HURDAT2_PATH` to `/app/data/hurdat2-atl.txt` baked into the image.
- `entrypoint.sh` calls `anemoi registry-pull` in best-effort mode before training so ephemeral workers can hydrate a prior registry mirror.
- Checkpoint and registry durability still depend on valid `S3_ARTIFACT_*` credentials.
