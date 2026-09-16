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
| Monitoring | GCP Ops Agent installed and active (`google-cloud-ops-agent.service`) -- system metrics/logs into Cloud Monitoring/Logging. Per-VM install for now; if a second VM joins the project, prefer an OS Config Ops Agent *policy* (`gcloud compute instances ops-agents policies create`) so new VMs auto-enroll instead of a manual install each time |

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
curl -LsSf https://astral.sh/uv/install.sh | sh && source $HOME/.local/bin/env
git clone https://github.com/jasonkolodziej/anemoi.git anemoi && cd anemoi
uv sync --all-extras
sudo apt-get update -qq && sudo apt-get install -y libeccodes0 tmux
```

The `libeccodes0` system package is required for GDAS caching (Stage B):
the PyPI `eccodes` package is pure-Python *bindings* only and does not
bundle the compiled library, unlike this repo's earlier assumption (fixed
after being verified wrong on both macOS and this VM -- see
`real_gridded.py`'s module docstring). Without it, `eccodes` fails with
`RuntimeError: Cannot find the ecCodes library` on import -- not a missing
package, a missing native library.

Copy `.env` over from a local machine rather than retyping R2 credentials
(goes through the encrypted SSH tunnel, never printed):

```bash
gcloud compute scp .env anemoi-train-1:~/anemoi/.env --project=anemoi-training --zone=us-central1-a
```

Verified on the real VM (2026-09-16): `uv run pytest` -- 405 passed, 4
skipped; a real R2 checkpoint upload/download round-trip; real ERA5 fetch at
**~6.7-9s/sample**, down from ~13-15s from a home connection but a more
modest improvement than pure network-latency co-location would suggest --
a good chunk of the ~13s cost is ARCO-ERA5 chunk decompression, which
doesn't change with location; `eccodes` (needed for GDAS) confirmed working
after `libeccodes0` install, version 2.24.2 -- older than the 2.42.0
`gribapi` recommends, but functional for this module's message parsing.

## Real ERA5/GDAS fetch/cache (#22 Stage A/B)

`data.era5_cache` / `data.gdas_cache` (`anemoi era5-cache` / `anemoi
gdas-cache` CLIs, both thin wrappers over the shared `data.gridded_cache`
engine) fetch concurrently and cache to local disk -- see their module
docstrings for why, and the resumability design (`skip_existing=True` by
default). At ~16,474 train-split fixes and a modest 6.7-9s/sample even from
this VM, that's still tens of hours sequential; concurrency is what makes it
practical.

Run these via `slurm/` (job scripts, `#SBATCH`-headered so they're also
directly `sbatch`-submittable on a real cluster later; `slurm/run_local.sh`
is the local stand-in for `sbatch` on this single-VM environment, launching
a job in a detached `tmux` session so it survives SSH disconnects) -- see
`slurm/README.md`:

```bash
# on the VM, once:
curl -o ~/hurdat2-atl.txt https://www.nhc.noaa.gov/data/hurdat/hurdat2-atl-1851-2023-042624.txt

slurm/run_local.sh slurm/era5_cache.sbatch train
slurm/run_local.sh slurm/gdas_cache.sbatch train

tmux ls                            # confirm both are running
tmux attach -t era5-cache-<id>     # watch one (Ctrl+B, D to detach)
```

A Spot preemption kills whichever job is running regardless of how it was
launched -- re-running the same `slurm/run_local.sh` command resumes from
whatever's already cached.
