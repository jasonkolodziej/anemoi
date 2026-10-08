# Model Catalog

Scope v2.1 §3. Seven builders, all in `src/anemoi/models/`, all returning `(module, spec)` where `spec` is a `ModelSpec` describing the I/O contract.

Each architecture is personified as one of the Anemoi — the Greek wind gods (see [Branding and Naming](Branding)). The god name is the identifier used in MLflow experiments, run tags, status badges and API paths; the architecture name stays the module name. `anemoi.branding` maps between them:

```python
from anemoi.branding import god, experiment_name

god("lstm").name          # 'Boreas'
god("boreas").direction   # 'N'
experiment_name("gnn")    # 'eurus'
```

All require the optional `torch` extra. The package imports fine without it — `models/__init__.py` uses lazy `__getattr__` so only the builder you touch pulls torch in.

```python
from anemoi.models import build_lstm
model, spec = build_lstm(input_dim=14, hidden_dim=128)
```

---

## Group 1 — deterministic

### Boreas — LSTM / GRU — `models/lstm.py`

*North wind. Fast, violent, first to arrive. The sprinter.* · `#06B6D4`

**Role:** track and intensity time-series forecasting. The fast baseline.

- **Input:** working-quality storm history sequences (lat, lon, max wind, min pressure, derived environment)
- **Output:** 6-hourly track and intensity to 120 h
- **In pipeline:** runs every cycle to warm-start the ensemble and provide a low-latency first guess

Recurrent architectures learn smooth, physics-constrained temporal evolution from sequential tabular data. The head predicts **displacements** from the current position rather than absolute lat/lon — absolute coordinates make the model memorise basin climatology, which looks excellent in training and fails on any storm outside the usual corridor.

`cell="gru"` selects the GRU variant.

### Zephyrus — CNN / U-Net / ResNet — `models/cnn.py`

*West wind. Gentle, visual, spring-like. The observer.* · `#10B981`

**Role:** satellite and radar feature extraction.

- **Input:** GOES-18/19 IR, water vapour, visible, plus SAR and microwave passes
- **Output:** eye-feature detection, convective burst identification, initial-condition corrections
- **In pipeline:** encoder front-end feeding the Transformer and GNN backbones

Global average pooling at the end makes the encoder resolution-agnostic, which matters because GOES crop sizes differ between the 512 and 1024 pixel datasets.

### Notus — Transformer — `models/transformer.py`

*South wind. Heavy, deliberate, sees the whole sky. The strategist.* · `#F59E0B`

**Role:** global context and long-range steering.

- **Operational input:** GDAS/GFS 0.25° fields from the most recent *available* cycle (typically `t−6`) — MSLP, Z500, U/V at 200 and 850 mb, T700, RH700, shear vectors
- **Training input:** two-stage curriculum, ERA5 then GDAS. See [Train/Serve Consistency](Train-Serve-Consistency)
- **Output:** track forecast, steering current identification, synoptic regime classification

Self-attention captures long-range dependencies — a trough over the Great Plains affecting a Gulf storm — without the locality bias of convolutions. A learned CLS token carries the pooled state and is the latent handed to Anemoi-Spread, so it must summarise the synoptic regime rather than any single grid point.

> **Hard rule (§3.2):** no model may consume a feature at inference time that was computed from ERA5 during training unless it has been fine-tuned or bias-corrected against the operational equivalent.

### Eurus — GNN — `models/gnn.py`

*East wind. Unpredictable, turbulent, inner-core specialist. The maverick.* · `#EF4444`

**Role:** mesh-based physics and spatial interaction.

- **Input:** icosahedral or unstructured mesh, station networks, buoy arrays; node features plus edge features (geodesic distance, pressure gradient)
- **Output:** fine-scale wind/pressure fields, storm-environment interaction, landfall point refinement
- **In pipeline:** critical for rapid intensification, where inner-core processes are localised and non-Euclidean

Implemented as an interaction network with `index_add_` scatter rather than a PyTorch Geometric dependency, so the reference implementation installs with plain torch. The message/update decomposition is the standard one; swapping in PyG later is a local change.

### Kaikias — PINN / Neural ODE — `models/pinn.py`

*Northeast wind. Rigid, constrained, unyielding. The disciplinarian.* · `#8B5CF6`

**Role:** constraint and conservation enforcement.

- **Input:** an environment vector **and a candidate forecast**
- **Output:** a physics-regularised correction to that forecast

> **Correction from review:** v2 §3.6 listed the governing equations under "Input". They are **loss constraints**, not model inputs. The equations enter through `physics_residuals()`, which is added to the loss — not through the forward pass.

The network outputs a *correction*, initialised at zero, so an untrained corrector is the identity. A physics layer should never make a good forecast worse before it has learned anything. `test_untrained_pinn_is_the_identity` pins this.

`physics_residuals()` returns three terms separately rather than summed, so the loss weights are visible and a failure is attributable:

| Residual | Penalises |
|---|---|
| `speed` | Translation faster than 45 kt |
| `curvature` | Implausibly sharp heading changes between steps |
| `hemisphere` | Motion inconsistent with the sign of the Coriolis parameter |

---

## Group 2 — Anemoi-Spread

### Skiron — Diffusion — `models/diffusion.py`

*Northwest wind. Generative, spreading, mist-like. The oracle.* · `#EC4899`

**Role:** ensemble generation and uncertainty quantification.

- **Input:** Anemoi-Core latents plus structured noise
- **Output:** 20–50 structurally diverse ensemble members
- **In pipeline:** the Anemoi-Spread component

Diffusion models learn the distribution of possible futures, not just a point estimate. Uses a cosine noise schedule, which degrades less gracelessly at low step counts than the linear schedule — and step count is a hard constraint here, since the whole ensemble must be generated inside the 13-minute stage budget.

> **Known risk:** conditioning purely on the deterministic latent anchors the ensemble to the deterministic guess and tends toward **underdispersion**, exactly when it matters most (bimodal recurvature). `extra_conditioning_dim` exists so raw environmental fields or GEFS/EPS perturbations can be concatenated to the conditioning vector. The rank histogram and spread-skill ratio in [Verification Metrics](Verification-Metrics) are how you find out whether that was enough.

> **On the sampling budget:** step count is traded against quality inside a 13-minute stage. If that binds, consistency distillation (Song et al. 2023) is a better answer than shedding ensemble members — one-step generation by default, multistep available when the schedule permits, distillable from an already-trained diffusion model. See [References](References) and [Roadmap](Roadmap).

---

## Group 3 — fusion

### Anemoi-Fusion — `models/fusion.py`

*The consensus of all six. Not a god — it takes the neutral Eye colour.* · `#F8FAFC`

**Role:** learned consensus over the deterministic models.

Weights are per-model and per-lead-time, softmax normalised, conditioned on the synoptic situation — a GNN strong on inner-core intensification and a transformer strong on steering should not receive the same weight in every regime.

Two deliberate choices:

- **Weights are exposed**, not hidden inside the forward pass. §10.1 requires the fusion layer to down-weight a divergent model, and that is only auditable if the weights can be read out per cycle.
- **A weight floor** prevents any model being fully zeroed. Mid-season there may be only a handful of verifying storms; a model discarded on three cases is unrecoverable for the rest of the season. `inference/cycle.fusion_weights` applies the same floor on the non-learned fallback path.

---

## Resource profile

| Model | GPU memory | Training time |
|---|---|---|
| LSTM | 8 GB | 4–6 h |
| CNN | 16 GB | 8–12 h |
| Transformer | 40 GB | 18–24 h |
| GNN | 24 GB | 12–16 h |
| PINN | 16 GB | 6–10 h |
| Diffusion | 48 GB | 24–36 h |
| Fusion | 8 GB | 2–4 h |
| Latent generation | 24 GB | 1.5–3 h |

Latent generation was implicit in v2; it takes real time and GPU and is scheduled explicitly. See [Training Architecture](Training-Architecture).

> **These are design-time/production-scale estimates, not yet reconciled with real measured numbers (2026-09-17).** The only training VM provisioned so far (`anemoi-train-1`) has a single NVIDIA L4 with ~23 GB VRAM — physically less than this table's 40–48 GB entries (Transformer, Diffusion), so those figures assume hardware not yet provisioned. Real wall-clock from actual `--streaming` runs on that VM, at the `--n-augment 3` scale currently cached (a small verification-scale dataset, not the full multi-year ERA5 history this table's hour-scale estimates likely assume): LSTM ~12 min, CNN ~94 min, Transformer ~158 min, PINN ~67 min — roughly one to two orders of magnitude under this table's per-model range. Treat this table as the target for a full production-scale deployment, not a description of what's running today; see [Training Architecture](Training-Architecture)'s "Real streaming relaunch" notes for the measured numbers.

---

Related: [Training Architecture](Training-Architecture) · [Model Registry](Model-Registry) · [Train/Serve Consistency](Train-Serve-Consistency) · [References](References)
