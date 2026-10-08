# Glossary

Scope v2.1 Appendix A, extended with terms introduced by the implementation.

---

## System

| Term | Definition |
|---|---|
| **Anemoi** | The platform. Named for the Greek wind gods — the many winds that produce one forecast. |
| **Anemoi-Core** | Deterministic engine: the five Group 1 models fused into one track and intensity forecast |
| **Anemoi-Spread** | Probabilistic ensemble generator (Skiron diffusion) — the cone, intensity PDF, landfall probability and RI flag |
| **Anemoi-Fusion** | The consensus weighting layer that blends Group 1 by rolling validation skill |
| **Group 1** | The five independent deterministic models: LSTM, CNN, Transformer, GNN, PINN |
| **Group 2** | Diffusion (Anemoi-Spread) — depends on Group 1 latents |
| **Group 3** | Fusion consensus model — depends on Group 1 latents |
| **Latent signature** | Deterministic hash of a Group 1 version set, e.g. `lstmv3-cnnv2-...`. Pinning refuses a set whose derived models disagree with it |
| **Model set** | A coherent pinned collection of all seven models. Production runs a set, not individual models |

> **Analogy:** Anemoi-Core answers *where will it go?* Anemoi-Spread answers *how sure are we?* Neither is useful to a decision-maker without the other.

## The Anemoi

See [Branding and Naming](Branding) for the full system. Each architecture is personified as a wind god; the god name is the identifier used in MLflow experiments, run tags and status badges. `anemoi.branding` maps between god and architecture.

| God | Direction | Architecture | Module | Character |
|---|---|---|---|---|
| **Boreas** | N | LSTM / GRU | Anemoi-Core | Fast, violent, first to arrive. The sprinter |
| **Notus** | S | Transformer | Anemoi-Core | Heavy, deliberate, sees the whole sky. The strategist |
| **Eurus** | E | GNN | Anemoi-Core | Unpredictable, turbulent, inner-core specialist. The maverick |
| **Zephyrus** | W | CNN / ViT | Anemoi-Core | Gentle, visual, spring-like. The observer |
| **Kaikias** | NE | PINN / Neural ODE | Anemoi-Core | Rigid, constrained, unyielding. The disciplinarian |
| **Skiron** | NW | Diffusion | Anemoi-Spread | Generative, spreading, mist-like. The oracle |
| **Euronotus** / **Lips** | SE / SW | — | — | Structural winds. They close the eight-point rose in the logo and radial layouts; they are never assigned to a model, so any colour on data maps to exactly one model (§5.3) |

## Data and Organizations

| Term | Definition |
|---|---|
| **NHC** | US National Hurricane Center |
| **NHC-AT** | NHC official forecast — human-machine consensus. The primary baseline |
| **ECMWF** | European Centre for Medium-Range Weather Forecasts |
| **UKM** | UK Met Office global model |
| **GFS** | NOAA Global Forecast System |
| **GDAS** | Global Data Assimilation System — the analysis feeding GFS |
| **GEFS / EPS** | Global Ensemble Forecast System / ECMWF Ensemble Prediction System |
| **ERA5** | ECMWF reanalysis, 1940–present. ~5-day latency (ERA5T). **Pretraining only** |
| **ERA5T** | Preliminary near-real-time ERA5. Enables the ~5-day skew audit |
| **HURDAT2** | NHC's post-season reanalysed best-track database. **Labels only** |
| **ATCF** | Automated Tropical Cyclone Forecasting system — the operational file format |
| **a-deck / b-deck** | ATCF forecast track file / working best-track file |
| **TC-Vitals** | Near-real-time storm position and intensity bulletin. The cycle's **gating input** |
| **NOMADS** | NOAA Operational Model Archive and Distribution System |
| **CDS** | Copernicus Climate Data Store — the ERA5 source |
| **NDBC** | National Data Buoy Center |
| **GOES-18/19** | Current operational GOES East/West pair (2026). GOES-16/17 are archive |

## Time and cycles

| Term | Definition |
|---|---|
| **Synoptic time** | 00Z, 06Z, 12Z or 18Z. All time series are resampled to these |
| **Cycle `t`** | The forecast run anchored to synoptic time `t` |
| **`t−6` cycle** | The previous NWP cycle. **What cycle `t` actually consumes** |
| **NWP cycle lag** | Offset between the forecast cycle and the NWP cycle it uses. Nominally 6 h, 12 h when degraded |
| **Lead time** | Hours ahead of `t` that a forecast is valid. 12/24/36/48/72/96/120 |
| **Advisory** | NHC public advisory at 03/09/15/21Z, i.e. `t+3:00`. The operative deadline |
| **Advisory margin** | Required buffer between product delivery and the advisory. 30 minutes |
| **Vitals timeout** | Point past which the cycle stops waiting for the working fix. **Derived**: `t+1:20` |
| **Load shedding** | Switching to the reduced-ensemble budget profile to hold the advisory after a late start |

## Data quality

| Term | Definition |
|---|---|
| **Working best-track** | Near-real-time, noisy, quantised. **What models are served** |
| **Final best-track** | Post-season reanalysed and smoothed. **Labels and verification only** |
| **Flavor** | Which input distribution a feature or set of weights came from: `era5_pretrain` or `gdas_finetune` |
| **Role** | What a source may be used for: `operational`, `pretrain_only`, `labels_only` |
| **Opportunistic source** | Event- or orbit-driven feed absent from most cycles by nature. Absence does **not** flag |
| **Emulated fix** | Working-quality fix synthesised from a final fix by adding measured error |
| **Estimated fix** | Fix extrapolated because the real one was late |
| **Train/serve skew** | Divergence between the distribution a model was fitted on and the one it is served |

## Meteorology

| Term | Definition |
|---|---|
| **OHC** | Ocean Heat Content |
| **PI** | Potential Intensity — theoretical maximum given the thermodynamic environment |
| **IVT** | Integrated Vapor Transport |
| **Deep-layer shear** | 200–850 mb wind difference. Strong shear inhibits intensification |
| **Steering flow** | Deep-layer-mean wind that advects the storm |
| **RI** | Rapid Intensification — ≥30 kt increase in 24 h |
| **Recurvature** | A storm turning poleward and then eastward. Where forecast distributions go bimodal |
| **Cone of uncertainty** | Probability circles around the forecast track. NHC's is built from historical error percentiles |
| **Coriolis parameter** | `f = 2Ω sin(latitude)`. Sign constrains plausible drift direction |

## Verification

| Term | Definition |
|---|---|
| **Track error** | Great-circle distance forecast-to-observed, in nautical miles |
| **Cross-track error** | Component perpendicular to storm motion. **Positive = right of track** |
| **Along-track error** | Component parallel to motion. **Positive = ahead of the storm** |
| **Beat rate** | Fraction of cases where our error is strictly smaller than a baseline's. **Ties count as losses** |
| **CRPS** | Continuous Ranked Probability Score. Reduces to absolute error for a single member |
| **Brier score** | Mean squared error of probability forecasts for binary events |
| **Spread–skill ratio** | Ensemble spread ÷ ensemble-mean RMSE. ~1.0 when calibrated |
| **Underdispersion** | Spread–skill below 0.8. The ensemble is over-confident |
| **Rank histogram** | Talagrand diagram. Flat = calibrated; U-shaped = underdispersed |
| **Diebold–Mariano** | Test for statistically significant difference in forecast accuracy |

## Architectures

| Term | Definition |
|---|---|
| **PINN** | Physics-Informed Neural Network. Here, a zero-initialised residual corrector |
| **GNN** | Graph Neural Network. Message passing over an irregular mesh |
| **Diffusion model** | Generative model learning a distribution of futures by iterative denoising |
| **Latent** | Pooled internal representation extracted from a trained model, used to condition Anemoi-Spread and fusion |
| **Neural ODE** | Continuous-depth network parameterising a derivative |

## Infrastructure

| Term | Definition |
|---|---|
| **MLflow** | Experiment tracking and model registry |
| **DVC** | Data Version Control — versions datasets alongside git |
| **Zarr** | Chunked, compressed array format for cloud-optimised access |
| **GRIB2** | WMO gridded binary format used by NWP centres |
| **Optuna** | Hyperparameter optimisation framework |
| **Evidently** | Data drift detection |
| **Great Expectations** | Data validation gates |
| **R2** | Cloudflare object storage — the warm tier |
