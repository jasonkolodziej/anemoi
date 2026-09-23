# Cloud Run training job

Source Plan: PLAN.md §5 (sample size, real Stage A/B training)
Related stream: #22 real training infrastructure

This folder packages Anemoi training for Google Cloud Run Jobs.
It runs training directly through the CLI (`anemoi train-schedule`) and does not require any SLURM scripts.

## What is in this folder

- `Dockerfile`: builds a training image with `torch`, `gridded`, `storage`, and `tracking` extras.
- `entrypoint.sh`: translates environment variables into `anemoi train-schedule` CLI arguments.

## Why Cloud Run Job (not service)

Training is batch work that runs to completion and exits. Cloud Run Jobs are the native fit for that execution model.

## Important runtime constraint

GPU-backed Cloud Run Job tasks currently have a maximum task timeout of 1 hour.
If your real run exceeds 1 hour, use one of these patterns:

1. Run CPU-only jobs with longer timeout.
2. Split work into shorter executions (for example by model subset using `MODELS=` and/or by using `DERIVED_FROM_CHAMPIONS=1`).

## Prerequisites

1. A Google Cloud project with billing enabled.
2. Cloud Run API enabled.
3. Artifact Registry repository for container images.
4. Secrets configured for checkpoint/object storage credentials:
   - `S3_ARTIFACT_API_ENDPOINT`
   - `S3_ARTIFACT_BUCKET`
   - `S3_ARTIFACT_ACCESS_KEYID`
   - `S3_ARTIFACT_SECRET_ACCESS_KEY`
5. Optional but recommended: a Cloud Storage bucket mounted at `/cache` for reusable cache and registry state between runs.

## Build and push image

Run from repository root:

```bash
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/anemoi-train:latest \
  .
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
  --set-env-vars MODE=sequential,STREAMING=1,NUM_WORKERS=4,ERA5_CACHE_DIR=/cache/era5,GDAS_CACHE_DIR=/cache/gdas,REGISTRY_ROOT=/cache/registry,HURDAT2_PATH=/app/data/hurdat2-atl.txt \
  --set-secrets S3_ARTIFACT_API_ENDPOINT=S3_ARTIFACT_API_ENDPOINT:latest,S3_ARTIFACT_BUCKET=S3_ARTIFACT_BUCKET:latest,S3_ARTIFACT_ACCESS_KEYID=S3_ARTIFACT_ACCESS_KEYID:latest,S3_ARTIFACT_SECRET_ACCESS_KEY=S3_ARTIFACT_SECRET_ACCESS_KEY:latest
```

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

```bash
gcloud compute disks create anemoi-train-from-snap \
  --project ${PROJECT_ID} \
  --zone us-central1-b \
  --source-snapshot ${SNAPSHOT_NAME} \
  --type pd-balanced \
  --size 100GB
```

### 2) Attach that disk to a helper VM

```bash
gcloud compute instances attach-disk ${HELPER_VM} \
  --project ${PROJECT_ID} \
  --zone us-central1-b \
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
gsutil -m rsync -r /mnt/anemoi-snap/home/${VM_USER}/.anemoi/registry gs://${CACHE_BUCKET}/registry
```

### 5) Point job env vars to mounted cache paths

```bash
gcloud run jobs update anemoi-train-schedule \
  --region us-central1 \
  --set-env-vars ERA5_CACHE_DIR=/cache/era5_cache,GDAS_CACHE_DIR=/cache/gdas_cache,REGISTRY_ROOT=/cache/registry
```

### 6) Clean up helper resources

```bash
# Run on helper VM first.
sudo umount /mnt/anemoi-snap

# Then from your workstation.
gcloud compute instances detach-disk ${HELPER_VM} \
  --project ${PROJECT_ID} \
  --zone us-central1-b \
  --disk anemoi-train-from-snap

gcloud compute disks delete anemoi-train-from-snap \
  --project ${PROJECT_ID} \
  --zone us-central1-b
```

This preserves your expensive pre-fetched caches while keeping Cloud Run stateless at the compute layer.

## Optional GPU update

For L4, Cloud Run requires at least 4 CPU and 16 GiB memory.
Remember task timeout is limited to 3600s for GPU tasks.

```bash
gcloud run jobs update anemoi-train-schedule \
  --region us-central1 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
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
  --cpu 4 \
  --memory 16Gi \
  --set-env-vars MODE=sequential,MODELS=lstm,STREAMING=1,NUM_WORKERS=4,ERA5_CACHE_DIR=/cache/era5,GDAS_CACHE_DIR=/cache/gdas,REGISTRY_ROOT=/cache/registry,HURDAT2_PATH=/app/data/hurdat2-atl.txt \
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
  --cpu 4 \
  --memory 16Gi \
  --set-env-vars MODE=sequential,DERIVED_FROM_CHAMPIONS=1,STREAMING=1,NUM_WORKERS=4,ERA5_CACHE_DIR=/cache/era5,GDAS_CACHE_DIR=/cache/gdas,REGISTRY_ROOT=/cache/registry,HURDAT2_PATH=/app/data/hurdat2-atl.txt \
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

## Common env knobs

- `MODE=sequential|parallel`
- `MODELS=lstm,cnn,transformer,gnn,pinn`
- `STREAMING=1` enables streaming DataLoader path
- `NUM_WORKERS=0..N` DataLoader workers
- `BATCH_SIZE=<int>` optional explicit batch size
- `DERIVED_FROM_CHAMPIONS=1` retrains only `latents/diffusion/fusion`

## Notes

- The container defaults `HURDAT2_PATH` to `/app/data/hurdat2-atl.txt` baked into the image.
- `entrypoint.sh` calls `anemoi registry-pull` in best-effort mode before training so ephemeral workers can hydrate a prior registry mirror.
- Checkpoint and registry durability still depend on valid `S3_ARTIFACT_*` credentials.
