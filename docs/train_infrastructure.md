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
| Zone | `us-central1-b` (moved from `us-central1-a` 2026-09-17 -- see "GPU capacity" below; co-location with ARCO-ERA5 is a **region**-level benefit, so any `us-central1` zone is equally close) |
| Machine type | `g2-standard-4` (4 vCPU / 16GB, pairs with 1× L4) |
| GPU | 1× NVIDIA L4 |
| Image | `pytorch-2-9-cu129-ubuntu-2204-nvidia-580` (project `deeplearning-platform-release`) -- PyTorch + CUDA preinstalled, no manual driver setup |
| Provisioning | **On-demand** (`STANDARD`) -- moved off Spot 2026-09-17. Spot's preemption risk is a bad trade for this workload specifically: `train_*_stage` only checkpoints at the end of a completed curriculum *stage*, not per-epoch, so a mid-stage preemption loses that whole stage's progress (hours, for Transformer/diffusion), not just resumes from `tracking.checkpoint_store` as originally assumed. Two preemptions in one real session, one of which required a full zone migration (below), made the actual cost of that risk concrete rather than theoretical |
| Boot disk | 100GB, `pd-balanced` |
| Monitoring | GCP Ops Agent installed and active (`google-cloud-ops-agent.service`) -- system metrics/logs into Cloud Monitoring/Logging. Per-VM install for now; if a second VM joins the project, prefer an OS Config Ops Agent *policy* (`gcloud compute instances ops-agents policies create`) so new VMs auto-enroll instead of a manual install each time |

Create with:

```bash
gcloud compute instances create anemoi-train-1 \
  --project=anemoi-training \
  --zone=us-central1-b \
  --machine-type=g2-standard-4 \
  --accelerator=type=nvidia-l4,count=1 \
  --image-family=pytorch-2-9-cu129-ubuntu-2204-nvidia-580 \
  --image-project=deeplearning-platform-release \
  --maintenance-policy=TERMINATE \
  --provisioning-model=STANDARD \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-balanced
```

`--maintenance-policy=TERMINATE` is mandatory regardless of provisioning model -- GCP cannot live-migrate a VM with an attached GPU. `--provisioning-model=STANDARD` (or omitting the flag; STANDARD is the default) is the only line that actually changed from the original Spot setup.

## GPU capacity: zone stockouts, and moving zones without losing the disk

L4 capacity in `us-central1` is genuinely tight and moves fast: in one real
session, `us-central1-a` returned `ZONE_RESOURCE_POOL_EXHAUSTED_WITH_DETAILS`
(`reason: resource_availability`, `sub-state: STOCKOUT`) for a fresh
**on-demand** create, not just a Spot preemption -- the error's own
`zonesAvailable` hint named `us-central1-c` as having room; by the time the
create was retried there, capacity had already moved to naming
`us-central1-a, us-central1-b` instead. This is live marketplace-style
flapping, not a one-time fluke -- don't trust a stockout error's
`zonesAvailable` field to still be true a few seconds later.

**The boot disk is zonal** -- it cannot attach to an instance in a different
zone directly, which is what actually blocks a same-zone restart-and-hope
retry loop from ever resolving a zone-wide stockout. The real fix is a
disk migration:

```bash
# 1. Snapshot the existing disk (from whichever zone it's currently in)
gcloud compute disks snapshot anemoi-train-1 \
  --project=anemoi-training --zone=us-central1-a \
  --snapshot-names=anemoi-train-1-migrate-YYYYMMDD

# 2. Create a disk copy from that snapshot in each zone worth trying --
#    cheap (a few GB-months of storage) and means the actual instance
#    create isn't blocked waiting on a fresh disk copy once a zone opens up
for zone in us-central1-a us-central1-b us-central1-c; do
  gcloud compute disks create anemoi-train-1 \
    --project=anemoi-training --zone=$zone \
    --source-snapshot=anemoi-train-1-migrate-YYYYMMDD \
    --type=pd-balanced --size=100GB
done

# 3. Race the create across zones -- whichever succeeds first wins;
#    the network/subnet are region-level so no other flag needs to change
for zone in us-central1-b us-central1-c us-central1-a; do
  gcloud compute instances create anemoi-train-1 \
    --project=anemoi-training --zone=$zone \
    --machine-type=g2-standard-4 --accelerator=type=nvidia-l4,count=1 \
    --maintenance-policy=TERMINATE --provisioning-model=STANDARD \
    --disk=name=anemoi-train-1,boot=yes,mode=rw,device-name=persistent-disk-0,auto-delete=yes \
    --network-interface=network=default,subnet=default,network-tier=PREMIUM \
    --service-account=<compute-service-account> --scopes=<same scopes as before> \
    --no-shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring \
    && break
done

# 4. Once one succeeds, delete the now-unused disk copies in the other
#    zones (the snapshot itself is worth keeping as a rollback point --
#    a couple dollars a month for a real disaster-recovery point)
gcloud compute disks delete anemoi-train-1 --zone=<losing-zone> --quiet
```

Deleting a *running instance* is treated as an irreversible action by this
project's usual tooling guardrails (even with `--keep-disks=all` preserving
the data) and needs a human to run that specific step directly -- disk
snapshot/create/delete on an unattached disk is not similarly gated.

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
gcloud compute scp .env anemoi-train-1:~/anemoi/.env --project=anemoi-training --zone=us-central1-b
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

**The `val` split needs fetching too, separately.** Every real per-model
runner's `train_*_stage` builds BOTH a train and a val sample set and
raises if either comes back empty (`training.real_run.train_lstm_stage`'s
`"stage {name}: no usable samples built from the given tracks"` and its
per-model siblings) -- `Curriculum.standard`'s Stage A/B both need real
validation loss and `metrics.track.verify` pairs, not just training data.
Running only `era5_cache.sbatch train`/`gdas_cache.sbatch train` (as the
example above does) leaves the val-split storms with zero cached fixes, so
CNN/Transformer/GNN/PINN's Stage A fails outright with "no cached
GriddedFields matched the given tracks" even once train-split coverage is
substantial -- discovered for real running this on the VM: 152 train-split
storms already well-cached, but 0 of the 68 ERA5/val-split or 21
GDAS-Stage-B-val-split storms. Fetch both:

```bash
slurm/run_local.sh slurm/era5_cache.sbatch val
slurm/run_local.sh slurm/gdas_cache.sbatch val
```

## Durable archive (GDAS/Stage B long-term data strategy)

`data/sources.py` originally claimed GDAS was "2015-present archived" on
NOAA's AWS Open Data bucket (`noaa-gfs-bdp-pds`). Verified wrong (direct S3
`list-type=2` listing, 2026-09-16): the bucket's real `gfs.*` coverage starts
**2021-01-01**, not 2015 -- `configs/curriculum.yaml`'s old `stage_b.
season_range: [2015, 2019]` covered a period with zero real GDAS data, which
is why an early `anemoi gdas-cache --split train` run 404'd on every single
fix. No retention policy is documented for this bucket either way (a
different, older bucket, `noaa-gfs-pds`, documents a rolling 4-week window --
don't confuse the two).

Given that, the decision for long-term production is to **not** depend on
NOAA's bucket as the system of record: back-fill what's currently available
(2021-present) into this project's own durable storage now, then keep it
current incrementally as new cycles are fetched, rather than re-deriving a
training set from a live bucket whose retention could change at any time.
Concretely:

- `data.gdas_cache.run_fetch_cache` now defaults to dropping any fix earlier
  than `GDAS_ARCHIVE_START` (2021-01-01) before fetching -- `data.splits`'
  *default* season boundaries are shared with Stage A/ERA5 and go back to
  1980, so an unfiltered `--split train` run would otherwise spend one
  request per fix discovering each one is a guaranteed 404.
- `anemoi gdas-cache` now assigns storms with `data.splits.
  STAGE_B_BOUNDARIES` instead of the default boundaries: the default
  `train` window (1980-2019) has **zero overlap** with GDAS's real archive
  at all, which is what this filter first made visible (`--split train`
  going from "100% failed" to "0 total, 0 fetched" -- correct behaviour
  given the filter, but still no real data). `STAGE_B_BOUNDARIES` scopes
  `train`/`val` to 2021-2022/2023 (the only seasons with both real GDAS
  coverage and final best-track labels in the current HURDAT2 archive);
  `test` (2024-2025) is deliberately empty for now -- it fills in as the
  incremental archive (below) accumulates newer seasons, rather than
  needing another boundary change later. `era5-cache` is unaffected and
  keeps the default boundaries -- Stage A wants the full 1980-2025 window.
- `configs/curriculum.yaml`'s `stage_b.season_range` is now `[2021, 2023]` --
  2021 is the real GDAS floor, 2023 is the latest season this project's
  HURDAT2 archive has final best-track labels for.
- `anemoi era5-cache`/`gdas-cache --sync-archive` (or `SYNC_ARCHIVE=1` on the
  `slurm/` scripts) uploads every locally-cached `.npz` not yet in R2 to
  `s3://<bucket>/{era5,gdas}_archive/<storm_id>/<cycle>.npz`, the same
  R2 bucket/credentials `tracking.checkpoint_store` already uses
  (`S3_ARTIFACT_*` in `.env`) -- reused as-is rather than a new backend,
  since that bucket already names itself a general artifact store, not a
  checkpoint-only one. It's a separate, independently-resumable pass over
  the local cache (existence checked in R2 itself, not a separate ledger),
  not folded into the fetch call, so a slow archive endpoint can never stall
  or fail a fetch run.

One-time backfill of everything already cached on this VM:

```bash
SYNC_ARCHIVE=1 slurm/run_local.sh slurm/gdas_cache.sbatch train

# or, without re-fetching (already-cached files are skipped by default,
# --sync-archive still runs against whatever's on disk):
uv run anemoi gdas-cache --hurdat2 ~/hurdat2-atl.txt --cache-dir ~/gdas_cache \
  --split train --sync-archive
```

## Real Stage A/B training runs: all five Group 1 models (#22)

Every Group 1 model now has a real Stage A -> Stage B runner against real
data -- `anemoi train --model {lstm,cnn,transformer,gnn,pinn}`, each with
its own `slurm/train_<model>.sbatch`.

`training.real_run.run_lstm_curriculum` (`--model lstm`,
`slurm/train_lstm.sbatch`) was the first, and deliberately so:
`models.lstm.build_lstm`'s input is storm-history sequences, not gridded
imagery, so it needs no gridded-field cache to train for real, only real
tracks.

CNN, Transformer and GNN (`training.real_run_cnn` / `real_run_transformer`
/ `real_run_gnn`, `--model cnn|transformer|gnn`, `slurm/train_cnn.sbatch` /
`train_transformer.sbatch` / `train_gnn.sbatch`) came next: real GOES
imagery and real station/buoy networks aren't fetched yet (PLAN.md's
Satellite row; `ndbc`/`dropsonde`/`microwave` aren't fetched for real
either), but all three architectures just need *some* multi-channel
spatial input, so they read the real cached `GriddedFields` (all 10
fields) instead of waiting on those. Reads from
`--era5-cache-dir`/`--gdas-cache-dir` (the same dirs `era5-cache`/
`gdas-cache` fetch into); a fix with no cached file yet is skipped, not an
error, so all three train on however much is cached at the moment invoked
and improve as the ingest jobs fill in more.

- Transformer needs an exact grid size (its patch embedding is not
  resolution-agnostic like CNN's global-average-pool encoder is) -- the
  real cached crop is 41x41 (`box_deg=10.0` at 0.25 deg resolution),
  trimmed to 40x40 (the architecture's own default, divisible by its patch
  size).
- GNN treats the cached grid as a lattice mesh: cells subsampled every 4
  in each direction become nodes (10 field values + row/col offset from
  centre -- 12 features, matching `build_gnn`'s own default exactly),
  4-connectivity gives the edges (3 features: d_row, d_col, distance,
  again matching the default exactly). Samples are batched the standard
  block-diagonal way (`real_run_gnn.batch_graph`) rather than one graph at
  a time.

PINN (`training.real_run_pinn`, `--model pinn`, `slurm/train_pinn.sbatch`)
came last because it's architecturally different from the other four --
`models.pinn.build_pinn`'s own docstring frames it as a residual corrector
*applied on top of a candidate forecast*, not a predictor from raw input.
This runner supplies that candidate by training a small internal LSTM
each run (self-contained, not dependent on a specific external checkpoint
existing), plus a real environment vector
(`data.features.compute_environment_features`) from the same cached
`GriddedFields`. `models.pinn.physics_residuals` is folded into the
training loss, but only over the 12/24/36/48h leads -- the uniformly
12h-spaced prefix of `DEFAULT_LEADS` its constant-`dt_hours` assumption is
actually valid for (the 48-120h gaps are 24h, not 12h).

What it actually does, end to end:

- Builds real multi-lead-time samples (`DEFAULT_LEADS`, 12-120h) from
  working-quality input / final-quality labels, generalising
  `training.capacity_ablation`'s proven single-6h-step pattern -- a lead
  beyond a storm's real track length is masked out of the loss, not
  synthesised or dropped as a whole sample.
- Stage A trains on `data.splits.DEFAULT_BOUNDARIES`' train/val seasons
  (1980-2019 / 2020-2022); Stage B fine-tunes the same model (frozen
  encoder, `.head` only) on `STAGE_B_BOUNDARIES`' seasons (2021-2022 /
  2023) -- the real-GDAS-aware split this doc's earlier section added.
- Every stage's checkpoint uploads to R2 via `CheckpointStore` (the same
  bucket `--sync-archive` uses, under `checkpoints/lstm/<stage>/...`) --
  never left local-only, so a Spot preemption mid-run doesn't lose it.
- Registers the trained model in `tracking.registry.ModelRegistry` (a local
  JSON store, `--registry-root`, default `~/.anemoi/registry`) and runs
  `training.promotion.evaluate_promotion` against the previous registered
  version, if any.

```bash
# on the VM, once (if not already fetched by the ingest jobs above):
curl -o ~/hurdat2-atl.txt https://www.nhc.noaa.gov/data/hurdat/hurdat2-atl-1851-2023-042624.txt

slurm/run_local.sh slurm/train_lstm.sbatch
tmux attach -t train-lstm-<id>

# CNN / Transformer / GNN / PINN -- benefit from era5_cache/gdas_cache
# having fetched data first, but work with whatever's cached so far:
slurm/run_local.sh slurm/train_cnn.sbatch
slurm/run_local.sh slurm/train_transformer.sbatch
slurm/run_local.sh slurm/train_gnn.sbatch
slurm/run_local.sh slurm/train_pinn.sbatch
```

## Running all seven as one schedule (`training.orchestrator`)

`training.orchestrator.run_schedule`'s injected `runner` is wired to all
seven real tasks the schedule can contain
(`training.real_orchestrator.RealOrchestratorRunner`, `anemoi
train-schedule`, `slurm/train_schedule.sbatch`) -- one job/log instead of
launching each `train_<model>.sbatch` by hand, with the same real
checkpoint upload, registry registration and promotion evaluation per
model:

```bash
slurm/run_local.sh slurm/train_schedule.sbatch sequential
# or: slurm/run_local.sh slurm/train_schedule.sbatch parallel
tmux attach -t train-schedule-<id>
```

`run_schedule`'s own dependency semantics (§10.1: one model's failure only
skips *its* dependents) still apply -- if a Group 1 model's real training
fails (e.g. an empty val split, see above), the `latents` task depending
on it is skipped, and `diffusion`/`fusion` depending on `latents` are
skipped in turn, while every model that *can* train still does.

## Real latent extraction and the two derived models (#22, §5.7)

Anemoi-Spread (diffusion) and the fusion consensus model don't read tracks
or gridded fields directly -- they're conditioned on real latents pulled
from the five just-trained Group 1 models, which is what the `latents`
task (`training.real_latents.extract_joint_latents`) does: for every real
window all five models can build a representation for (same
`iter_stage_windows` loop every Group 1 runner shares, so a window missing
cached `GriddedFields` is skipped for all five at once), it runs each
model's `.encode()` -- the hook `models.base.ModelSpec`'s docstring was
explicit was built for exactly this -- and concatenates the five real
latent vectors, plus each model's own real Stage B forecast (converted to
a shared absolute lat/lon/wind space) and a real synoptic context vector
derived from the window's own track data (heading, speed, intensity trend,
season, `real_latents.CONTEXT_FEATURE_NAMES`).

This runs against the trained model objects still in memory from the SAME
schedule run, not against checkpoints reloaded from storage:
`tracking.registry.ModelVersion` doesn't record a checkpoint_uri today, and
PINN's candidate-generator LSTM is never persisted at all (retrained fresh
each run, per `real_run_pinn`'s own module docstring). Each Group 1
runner's `real_run.RunArtifacts` carries the exact standardisation stats
Stage B fit its inputs/targets with, so a model's raw output can be
correctly un-standardised back to real units -- refitting those
independently would only approximate the real inverse of the model's
output space.

Diffusion (`training.real_run_diffusion`) trains the standard DDPM
epsilon-prediction objective (predict the noise added at a random
timestep, `models.diffusion.build_diffusion`'s own cosine-schedule
buffers) over the real masked multi-lead displacement targets, masked the
same way every other real runner masks a lead beyond a short track's real
length. Validation reduces the trained ensemble to its per-sample mean for
`metrics.track.verify` -- a point number for promotion, not a claim that
the mean IS the model's real product (the full ensemble is;
`metrics.probabilistic.spread_skill` is the real check for that).

Fusion (`training.real_run_fusion`) trains `models.fusion.build_fusion`'s
learned per-lead-time consensus weights with a masked MSE directly in the
shared absolute-coordinate space the five real per-model predictions and
the true track already share -- no further standardisation needed, the
same reason PINN's own absolute-space loss doesn't standardise either.

Both derived models register with the real `latent_signature`
(`tracking.registry.latent_signature`) computed from the Group 1 versions
they were actually trained against, satisfying `ModelRegistry.pin_set`'s
requirement that a promotable production set is coherent end to end --
retraining any Group 1 model changes the signature and correctly
invalidates the diffusion/fusion versions built from the old one.

Needs `torch` and `storage` extras (`uv sync --all-extras` already covers
both) and real `S3_ARTIFACT_*` credentials -- unlike the two ingest jobs,
this one always uploads (no local-only fallback), since a multi-hour GPU
run losing its result to a preemption is a real cost this project already
built `CheckpointStore` to avoid.

## Alternative: vast.ai, if GCP L4 capacity stays unreliable

Recorded here as a real fallback option, not (yet) adopted -- the current
VM above is still GCP. Worth having ready given `us-central1`'s repeated
L4 stockouts (previous section): vast.ai is a peer-to-peer GPU marketplace
(many independent hosts, not one hyperscaler's capacity pool), so a
region-wide stockout on one platform doesn't imply the same on the other.

**The real trade-off, not just a cheaper price.** Moving off GCP loses the
region co-location with ARCO-ERA5 this doc opens with -- real ERA5 fetch
measured **~6.7-9s/sample** from the GCP VM vs **~13-15s/sample** from
outside GCP (this doc's "On the VM" section). A vast.ai host fetches Stage
A data at the slower, outside-GCP rate regardless of which host -- none of
them peer with Google's network the way a GCP VM does. GDAS/Stage B (AWS
`noaa-gfs-bdp-pds`) was never GCP-local either way, so that fetch is
unaffected. This is a real cost of moving, to weigh against the price
difference below -- not a reason to dismiss it outright, since fetch is a
one-time cost per fix (`skip_existing=True`) while GPU-hours recur every
training run.

### Template

vast.ai instances are Docker containers (`docs.vast.ai/creating-a-custom-template`),
not full VMs -- a template sets the image, launch mode, and an on-start
script; disk size is chosen separately per-instance when picking an offer.

| Field | Value |
|---|---|
| Docker image | `pytorch/pytorch:2.9.0-cuda12.8-cudnn9-runtime` (or vast.ai's own PyTorch template as a base -- pin to torch 2.9 either way, matching the GCP image's `pytorch-2-9-cu129` so `uv.lock`'s resolved torch build is the one actually exercised) |
| Launch mode | SSH (this project's whole workflow -- `slurm/run_local.sh`, tmux sessions, log tailing -- assumes an interactive shell, not a Jupyter-only or entrypoint-only container) |
| Disk space | 100GB minimum (matches the GCP boot disk; current real usage is ~34GB with ERA5/GDAS caches partially filled -- give headroom, this only grows) |
| On-start script | Same commands as this doc's "On the VM" section: |

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh && source $HOME/.local/bin/env
git clone https://github.com/jasonkolodziej/anemoi.git anemoi && cd anemoi
uv sync --all-extras
apt-get update -qq && apt-get install -y libeccodes0 tmux
curl -o ~/hurdat2-atl.txt https://www.nhc.noaa.gov/data/hurdat/hurdat2-atl-1851-2023-042624.txt
# .env (S3_ARTIFACT_* for CheckpointStore) still needs copying in separately --
# never bake real credentials into a template, especially a public one.
```

### GPU options

`docs/capacity_ablation.md`'s real finding matters here: these models are
small (a few thousand parameters up to ~4.8M for the Transformer) and
train full-batch against a thin (~16k-fix) archive. The GCP L4's 24GB is
already far more headroom than any of these five models uses -- so the
selection criterion for a marketplace GPU is "enough VRAM to be safe,
cheap and not chronically out of stock," not raw throughput.

Live pricing is marketplace-set and moves constantly (`vast.ai/pricing`) --
the ranges below are what a real search returned 2026-09-16, not a fixed
quote; check the console at time of use.

| GPU | VRAM | Typical vast.ai range (2026-09-16) | Notes |
|---|---|---|---|
| RTX 3090 | 24GB | as low as ~$0.07-0.08/hr | Cheapest real option with L4-equal VRAM; older architecture (Ampere, no FP8), irrelevant for these model sizes |
| RTX 4090 | 24GB | roughly $0.14/hr (rock-bottom listings) to ~$0.29-0.50/hr (typical, on-demand/reliable hosts) | Best default pick -- comparable price band to 3090's higher end, meaningfully faster, still far more VRAM than needed |
| L4 | 24GB | listed as available; specific rate not returned by this search | Would match the GCP setup exactly (same architecture); fewer vast.ai hosts carry data-center cards vs. consumer RTX, so availability is the real risk here, the same failure mode this section exists to avoid |
| A100 (40/80GB) | 40-80GB | ~$0.60-0.92/hr | Overkill -- 3-6x the RTX price for VRAM/throughput this workload has no use for. Only worth it if a host's *price* happens to undercut a 3090/4090 listing, not for the extra capacity itself |

Recommendation: **RTX 4090** as the default search filter, **RTX 3090** as
the cost-optimized fallback if 4090 availability/price is bad at the
moment -- both give the same 24GB this project's models have never come
close to filling, at a fraction of GCP on-demand L4 pricing, from a
capacity pool that fails independently of GCP's.

Sources: [Vast.ai GPU Pricing — Live Platform Rates](https://vast.ai/pricing), [RTX 4090 pricing](https://vast.ai/pricing/gpu/RTX-4090), [RTX 3090 pricing](https://vast.ai/pricing/gpu/RTX-3090), [Vast.ai GPU Pricing comparison](https://computeprices.com/providers/vast), [Creating Templates — Vast.ai Documentation](https://docs.vast.ai/creating-a-custom-template)
