# Getting Started

## Requirements

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/) for dependency management
- A CUDA GPU only if you intend to train; the operational logic runs on CPU

## Install

```bash
git clone <repo-url> anemoi
cd anemoi

uv sync                      # core: numpy + pyyaml
uv sync --extra torch        # add the model implementations
uv sync --extra tracking     # add MLflow
uv sync --extra gridded      # add real ERA5 (Zarr) + GDAS/GFS (GRIB2) readers
uv sync --extra storage      # add S3/R2 checkpoint upload/download (boto3)
uv sync --extra all          # everything, including pytest and ruff
```

Torch is deliberately optional. The operational layers — scheduling, availability, curriculum, promotion, registry, metrics — carry the v2.1 policy and must remain importable and testable on a machine without a GPU or a torch wheel. `uv sync` without extras gives you a package where all of that is usable; model code is opt-in.

## Verify

```bash
uv run pytest
```

Expect **241 passed, 15 skipped**. The skips are the `torch`-marked model tests; install the `torch` extra to run them. See [Testing](Testing).

## First commands

```bash
uv run anemoi schedule 2026-08-06
```

The fastest way to see what v2.1 changed. Prints cycle start gated on the working fix, the six stage budgets, and the worst-case margin against the advisory deadline:

```
cycle 20260806_06Z  start 06:45Z  nwp t-6h
  assembly       06:45 -> 06:55 (max 07:05)
  preprocess     06:55 -> 07:10 (max 07:30)
  deterministic  07:10 -> 07:20 (max 07:48)
  fusion         07:20 -> 07:22 (max 07:52)
  diffusion      07:22 -> 07:35 (max 08:17)
  postprocess    07:35 -> 07:40 (max 08:27)
  advisory 09:00Z  margin 33 min worst case
  advisory margin check: OK
```

```bash
uv run anemoi schedule 2026-08-06 --worst-case   # plan against max feed latencies
uv run anemoi sources                            # which feeds may be read in production
uv run anemoi cycle 20260806_06Z                 # one demo cycle, JSON payload out
uv run anemoi splits --start 2015 --end 2026     # storm-wise split summary
```

`anemoi sources` marks non-operational sources with `*`:

```
* besttrack_final         labels_only    ~4320.0h  NHC / NOAA (HURDAT2)
  besttrack_working       operational    ~   0.8h  NHC ATCF (a-/b-deck, TC-Vitals)
  gdas_gfs                operational    ~   3.5h  NOAA NOMADS
* era5                    pretrain_only  ~ 120.0h  Copernicus CDS

* not readable during a forecast cycle (Scope v2.1 §4.6)
```

## What is real and what is not

**Real and tested:** cycle timing and input availability, the pretrain/fine-tune curriculum, promotion gates, model-set pinning, retraining triggers, degraded modes, skew and drift monitoring, verification metrics.

**Synthetic:** HURDAT2, ERA5, GDAS/GFS and GOES are not wired in. `anemoi.data.synthetic` generates archives with the same shape and statistics — including a deliberate ERA5-vs-GDAS offset, without which the skew machinery would have nothing to detect. The generator's `GDAS_BIAS` constant is not a claim about the real offset between those analysis systems.

**Untrained:** the seven model builders produce correct shapes and latent contracts. They have never seen data.

Replacing the synthetic layer is the first production task. The interfaces to satisfy are `GriddedFields`, `Track` and `AvailabilityOracle`. See [Roadmap](Roadmap).

## Development

```bash
uv run pytest tests/test_scheduler.py -v   # one module
uv run pytest -m "not torch"               # skip model tests explicitly
uv run ruff check src tests
uv run ruff format src tests
```

Next: [Codebase Map](Codebase-Map) · [System Architecture](System-Architecture)
