# Training infrastructure (GCP)

PLAN.md §5 "Sample size" / #22. Where real Stage A/B training compute lives,
and why it's sized the way it is.

## Why GCP, and why this size

ARCO-ERA5 (Stage A's data source) is a public Zarr store on Google Cloud
Storage, located in `us-central1` (confirmed via the bucket's own metadata:
`storage.googleapis.com/storage/v1/b/gcp-public-data-arco-era5`). A single
real ERA5 sample fetch from outside GCP takes ~13-15s, dominated by network
I/O against the archive's per-timestep chunking, not compute -- see
`docs/capacity_ablation.md`'s benchmark. Running compute in the same region
turns that into an intra-cloud read instead of a cross-internet one.

The wiki's Training-Architecture.md describes "parallel mode" needing 5+ GPU
workers, one per Group 1 model. That figure predates real measurement:
`docs/capacity_ablation.md` found the models here are small (a few thousand
parameters up to ~4.8M for the transformer) against a thin (~16k-fix)
archive. One GPU runs all five Group 1 models (LSTM, CNN, Transformer, GNN,
PINN) genuinely concurrently -- parallel mode is about the *orchestrator*
running them at the same time
(`training.orchestrator`), not about needing one GPU per model. Provisioning
a multi-GPU cluster for this workload would pay for capacity nothing here
can use.

## GCP project

| Setting | Value |
|---|---|
| Project ID | `anemoi-training` |
| Billing | Enabled |
| APIs enabled | `compute.googleapis.com` |
| GPU quota (`us-central1`) | 1× `NVIDIA_L4_GPUS` (on-demand and Spot) -- sufficient for the VM below without a quota-increase request |

## Training VM

| Setting | Value |
|---|---|
| Name | `anemoi-train-1` |
| Zone | `us-central1-a` (co-located with ARCO-ERA5) |
| Machine type | `g2-standard-4` (4 vCPU / 16GB, pairs with 1× L4) |
| GPU | 1× NVIDIA L4 |
| Image | `pytorch-2-9-cu129-ubuntu-2204-nvidia-580` (project `deeplearning-platform-release`) -- PyTorch + CUDA preinstalled, no manual driver setup |
| Provisioning | Spot -- cheaper, and pairs with `tracking.checkpoint_store` (already built, #32): a preemption just resumes from the last uploaded checkpoint instead of losing the run |
| Boot disk | 100GB, `pd-balanced` |

Create with:

```bash
gcloud compute instances create anemoi-train-1 \
  --project=anemoi-training \
  --zone=us-central1-a \
  --machine-type=g2-standard-4 \
  --accelerator=type=nvidia-l4,count=1 \
  --image-family=pytorch-2-9-cu129-ubuntu-2204-nvidia-580 \
  --image-project=deeplearning-platform-release \
  --maintenance-policy=TERMINATE \
  --provisioning-model=SPOT \
  --instance-termination-action=STOP \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-balanced
```

## Checkpoint storage

Not on GCP -- `tracking.checkpoint_store` targets Cloudflare R2 (S3-compatible,
zero egress fees), reachable from this VM over the public internet like any
other HTTPS endpoint; no GCP-side configuration needed. See the "Checkpoint
store" section of the Storage and Versioning wiki page and `example.env` for
the `S3_ARTIFACT_*` variables.

## On the VM

```bash
git clone <repo-url> anemoi && cd anemoi
uv sync --extra torch --extra gridded --extra storage
cp example.env .env   # fill in the real R2 credentials, not committed
```

Then run the real ERA5 fetch / Stage A data assembly and
`training.orchestrator`'s parallel mode from there rather than from a home
connection -- that's the entire reason this VM is co-located with the data.
