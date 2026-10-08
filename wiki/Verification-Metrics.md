# Verification Metrics

Scope v2.1 §7.3, Appendix B. Implemented in `metrics/track.py` and `metrics/probabilistic.py`.

Track error is great-circle distance in nautical miles, because that is the unit NHC verification uses. Intensity error is **signed** in knots so bias is recoverable. Errors are reported **per lead time** — a model can be excellent at 24 h and useless at 96 h, and a single averaged number hides exactly that.

Lead times verified: **12, 24, 36, 48, 72, 96, 120 h**.

---

## Deterministic

```python
from anemoi.metrics.track import verify, to_metric_dict
stats = verify(pairs)              # dict[lead_hours, LeadTimeStats]
to_metric_dict(stats)              # flattened to MLflow metric names
```

| Metric | Definition |
|---|---|
| `track_mae_nm` | Mean great-circle distance, forecast to observed |
| `track_rmse_nm` | Root mean square of the same |
| `intensity_mae_kt` | Mean absolute wind error |
| `intensity_bias_kt` | **Signed** — positive means the forecast was too strong |
| `cross_track_bias_nm` | **Positive = forecast right of observed motion** |
| `along_track_bias_nm` | **Positive = forecast ahead of the storm** |

The cross/along decomposition is what makes a bias diagnosable. A fast bias and a rightward bias have completely different causes and completely different fixes.

### Beat rate

```python
beat_rate(candidate_errors, baseline_errors)
```

Fraction of cases where the candidate error is **strictly** smaller. **Ties count as losses** — a model that matches NHC has not beaten it.

### Diebold–Mariano

```python
stat, p = diebold_mariano(candidate_errors, baseline_errors)
```

Tests whether a difference in forecast accuracy is statistically significant. A negative statistic favours the candidate.

> **Caveat, stated in the docstring and worth repeating:** this uses a lag-0 variance estimate, adequate for storm-wise independent samples. Serially-correlated 6-hourly fixes from a single storm should be aggregated to **one case per storm** first, or the test is anti-conservative. Minimum 8 cases.

---

## Probabilistic — Anemoi-Spread

### CRPS

```python
crps_ensemble(members, observation)
crps_series(members_2d, observations)
```

Fair estimator: `mean|xᵢ − y| − ½·mean|xᵢ − xⱼ|`. Lower is better; for a single member it reduces to absolute error.

### Brier score

For binary events such as landfall. Zero is perfect.

### Spread–skill ratio

**The one to watch.** Ensemble spread against ensemble-mean RMSE.

```python
ss = spread_skill(members, observations)
ss.ratio            # ~1.0 when well calibrated
ss.underdispersed   # ratio < 0.8  — over-confident
ss.overdispersed    # ratio > 1.25
```

Underdispersion is the characteristic failure of an ensemble conditioned on a deterministic guess — see [Model Catalog](Model-Catalog). A ratio well under 1 is what that failure looks like numerically, and it should be tracked **per lead time** from the first backtest.

> **This is a post-hoc tool.** It requires an observation, so it cannot gate a cone at forecast time. `build_cone` uses an ensemble-radius-vs-climatology proxy instead. See [Inference Cycle](Inference-Cycle).

### Rank histogram

Talagrand histogram, `n_members + 1` bins. Flat indicates calibration; a **U shape indicates underdispersion**.

### Reliability

Returns bin centres, observed frequency and counts for a reliability diagram.

---

## Success metrics

Appendix B.

| Metric | Target | Production threshold |
|---|---|---|
| 48 h track error | < 75 nm | < 70 nm (re-baselined; was < 90 nm) |
| 72 h track error | < 120 nm | < 150 nm (not yet re-baselined) |
| 120 h track error | < 200 nm | < 250 nm (not yet re-baselined) |
| 48 h intensity error | < 10 kt | < 15 kt |
| 72 h intensity error | < 15 kt | < 20 kt (not yet re-baselined) |
| **NHC consensus beat rate** | **> 55% at 48 h** | **> 50% at 48 h** |
| **ECMWF beat rate** | **> 50% at 72 h** | **> 45% at 72 h** |
| Ensemble CRPS | < 0.3 normalised | < 0.4 |
| Inference pipeline uptime | > 99.5% | > 99% |
| Training cycle (parallel) | < 60 h | < 72 h |
| Training cycle (sequential) | < 120 h | < 144 h |

### Track and intensity are not the same problem — split in code

Appendix B treats them symmetrically — one table, same target/threshold structure for both. The literature says they are not symmetric: intensity forecast skill has improved slowly since such forecasts became routine, while track skill has improved markedly over the same period (Emanuel & Zhang 2016; DeMaria et al. 2014).

That has a practical consequence for the gates. A beat rate against NHC on **track** is a claim about a rapidly-improving baseline; the same beat rate on **intensity** is a claim about a baseline that has moved much less, and is closer to an intrinsic predictability limit. They should not be read as equivalent achievements, and the intensity thresholds deserve their own derivation rather than inheriting the track table's structure. See [References](References).

`training/promotion.py` now exposes `TRACK_THRESHOLDS` and `INTENSITY_THRESHOLDS` as separate tuples instead of one shared table — `DEFAULT_THRESHOLDS` is their union, so `evaluate_promotion`'s default behavior is unchanged, but each table can now be re-derived on its own schedule.

### The absolute numbers — 48h track re-baselined, the rest still open

Lead times are measured from synoptic time `t` with `t−6` NWP as input.

NHC's official GPRA performance-measures table ([GPRA_history.pdf](https://www.nhc.noaa.gov/verification/pdfs/GPRA_history.pdf)) is the current source for the 48h figures below — it is the only lead time that table publishes, so it is the only one re-baselined here. Extrapolating 72h/120h from a single verified point would be fabricating precision, not re-deriving against a source; pull those from the full spring Verification Report instead.

NHC official 48 h Atlantic track error:

| Season | Error |
|---|---|
| 2023 | 69 n mi (a difficult year) |
| 2024 | **45.4 n mi** — a record at every lead time |
| 2025 | **53.4 n mi** |
| 2026 GPRA target | 51.0 n mi |

NHC official 48 h Atlantic intensity error:

| Season | Error |
|---|---|
| 2024 | **11.4 kt** |
| 2025 | **13.7 kt** — an unusually difficult season (NHC's 2025 verification preview: storms "about 50% harder to predict than average"), not a skill regression |
| 2026 GPRA target | 10.0 kt |

> A system whose *production threshold* is 90 nm would be admitted to production while being roughly twice as bad as the incumbent. The beat-rate gate is the only thing preventing that — which is exactly why it is the primary criterion, not a supplement to the absolute limits.

**`track_error_48h_nm` is now 70.0 nm** (was 90.0) — roughly 1.4x the 2026 GPRA target rather than roughly 1.8x. Still a backstop against a badly broken candidate, not a claim of parity with an operational center running decades of consensus guidance; the beat-rate gate remains the real claim. `intensity_error_48h_kt` (15.0) was left unchanged — unlike the track number, it already sits close to the worse of the two realized years above and was never the badly-miscalibrated one.

Two further consequences for the backtest:

- Atlantic 24–72 h track errors have fallen roughly 75% over twenty years. A backtest spanning decades scores against a **moving** baseline, so a single fixed threshold is meaningless across that span.
- NHC uses CLIPER5, a climatology-and-persistence model, to estimate each season's difficulty. A good year and an easy year are not the same thing, and beat rate alone will not distinguish them. A difficulty-normalised baseline belongs in the verification layer.

`TRACK_THRESHOLDS` / `INTENSITY_THRESHOLDS` in `training/promotion.py` encode the production column (`DEFAULT_THRESHOLDS` is their union). `track_error_72h_nm`, `track_error_120h_nm`, and `intensity_error_72h_kt` remain un-rederived. Citations in [References](References).

---

Related: [References](References) · [Experiment Tracking](Experiment-Tracking) · [Training Architecture](Training-Architecture) · [Inference Cycle](Inference-Cycle)
