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

## Homogeneous baseline: guidance on the registry's own validation windows

A registered `{basin}/track_error_{lead}h_nm` says neither how hard its windows were nor what the guidance a cycle already has scores on them. `anemoi baseline-backtest` (`training.baseline_backtest`, `metrics.homogeneous`) answers that from NHC's a-decks: it scores operational techniques on exactly the windows fusion and diffusion are validated on -- the Stage B validation season (2024 while the archive ends in 2025), the same storms, initial times, emulated working fixes, final best-track truth and mask, enumerated by the function training itself uses (`real_latents.joint_stage_windows`), with `metrics.track.verify`'s errors.

**Three samples, no single headline.** A number is comparable only with another on the same sample.

| Sample | Cases | Comparable with |
|---|---|---|
| A | every registry window | a registered model metric (fusion v12's 231 / 136 / 69 nm) |
| B | A where every compared member has a forecast and the verifying fix is at init + lead | other members on B |
| C | B, tropical or subtropical at both initial and verifying time (NHC's rule) | the 70 nm gate, NHC's 51 nm 2026 target, NHC's published errors |

C still starts each storm 24 h after its first fix and assigns basin by storm id (EP rows include CPHC-issued forecasts west of 140W; CP is CPHC, with no NHC counterpart).

**Members.** `OFCL` (the regular advisory: `OFCO` where a special advisory replaced it, as NHC verifies), `AVNI` (the previous GFS run shifted to the storm's position at `t`: the GFS track a cycle has), `AVNO-6` (the raw track of the `t−6` run whose fields the models read), `AVNO` (late: the `t` run arrives after NHC's `t+3` advisory, context only), `EMXI` (ECMWF interpolated: `EMXI` at 06/18Z, `EMX2` at 00/12Z, since ECMWF's full runs start at 00 and 12Z), `OCD5` (CLIPER5 track, Decay-SHIFOR5 intensity: NHC's skill baseline), `XTRP` (extrapolation from the working fixes), and the registry's `persistence` with the same rule on the un-noised best track. `--techniques` takes any a-deck technique (`TVCN`, `HCCA`, ...). Each row carries the storm count and the largest storm's share, case- and storm-weighted means, and against `AVNI` and `OFCL` the paired difference with a storm-block bootstrap interval, the beat rate and a Diebold–Mariano p-value on one case per storm; under 8 storms, means only.

**Decision rule, fixed before any model number exists:** fusion minus AVNI, Atlantic, 48 h track, on B and C. Positive with a storm-block interval excluding zero on both: the ML layer subtracts value; negative and excluding zero on both: it adds value; otherwise the season does not decide. The registry's `nhc_consensus_beat_rate_48h` threshold is a different comparison (against NHC's consensus, `TVCN`); nothing computes it yet.

**The join is checked against NHC.** OFCL scored under NHC's rules in full (every initial time, tropical at both times, NHC's initial-position domain) reproduces NHC's per-forecast file case for case: 2024 Atlantic 48 h, all 214 cases, 45.44 nm against NHC's 45.41, largest per-case difference 0.12 nm; East Pacific 89 of 89, 48.84 against 48.81. The residual is a near-constant ratio of 1.0007 at every lead, which is what 60 n mi per degree of arc gives against `geo.haversine_nm`'s 6371.0088 km sphere: a different Earth radius, not a different case.

**2024**, 48 h track error in nm (`docs/backtests/2026-11-13-homogeneous-baseline-val2024.json`; * fewer than 8 storms):

| Basin, sample | n (storms) | OFCL | AVNI | AVNO-6 | AVNO | EMXI | OCD5 | XTRP | persistence | un-noised |
|---|---|---|---|---|---|---|---|---|---|---|
| AL A | 255 (15) | | | | | | | | 335 | 287 |
| AL B | 242 (15) | 57 | 66 | 67 | 58 | 59 | 248 | 297 | 330 | 285 |
| AL C | 190 (15) | 44 | 53 | 54 | 48 | 48 | 206 | 248 | 289 | 237 |
| EP A | 138 (10) | | | | | | | | 253 | 194 |
| EP B | 102 (9) | 47 | 57 | 59 | 49 | 56 | 140 | 192 | 242 | 183 |
| EP C | 70 (7*) | 45 | 57 | 58 | 49 | 50 | 130 | 169 | 232 | 161 |
| CP A | 30 (1*) | | | | | | | | 186 | 101 |
| CP B | 27 (1*) | 55 | 78 | 83 | 76 | 56 | 64 | 101 | 190 | 102 |
| CP C | 26 (1*) | 54 | 75 | 79 | 71 | 54 | 61 | 97 | 188 | 99 |

What this says before any model forecast is scored:

- **The registry's persistence is not CLIPER.** It extrapolates the last 6 h of two independently perturbed fixes, so on B in the Atlantic it scores 330 nm at 48 h against OCD5's 248 and XTRP's 297. "Beats persistence" is a far lower bar than NHC's skill baseline.
- **Fusion's registered error bounds it on B and C** (`sample_gap`). Fusion v12 scores 231 nm on Atlantic A. To match AVNI on B, its error on the 13 windows B leaves out would have to average 3,304 nm (persistence there: 434); on C, 752 nm on 65 windows (persistence: 470). East Pacific: 359 nm on 36 windows for B (persistence 283); C is not decided by the bound (218 nm on 68; persistence 275). Central Pacific is Hone alone: fusion's 69 nm on A is at most 76.7 nm on B, under AVNI's 77.8.
- **The inputs differ even where the cases are the same.** The models read an emulated working fix 13.0 nm from the best track (Atlantic mean); the as-issued fix (CARQ) was 5.3 nm off, and its 6 h motion error 10.3 nm RMS against the emulator's 20.8.

Fusion and the Group 1 models join the same samples through a per-case forecast file that `anemoi validation-forecasts` writes on the training machine (inference only; [Cloud Run README](https://github.com/jasonkolodziej/anemoi/blob/main/docker/cloud-run-training/README.md), "One-off commands"), passed as `--model-forecasts`. The a-decks are fetched once with `anemoi adeck-fetch`; `baseline-backtest` reads files only.

---

Related: [References](References) · [Experiment Tracking](Experiment-Tracking) · [Training Architecture](Training-Architecture) · [Inference Cycle](Inference-Cycle)
