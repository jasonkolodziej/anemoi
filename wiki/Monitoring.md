# Monitoring

Scope v2.1 §4.6.3, §8.3. Implemented in `monitoring/skew.py`, `monitoring/drift.py`, and `monitoring/calibration_audit.py`.

Four independent signals, each answering a different question.

| Signal | Question | Module |
|---|---|---|
| **Skew audit** | Has the operational input distribution moved away from what Stage B fitted? | `monitoring/skew` |
| **Feature drift** | Are live features off the training manifold? | `monitoring/drift` |
| **Validation loss** | Is the model getting worse on data we have labels for? | `monitoring/drift` |
| **Calibration audit** | Was the cone/intensity band actually *served* to a user right, once truth became known? | `monitoring/calibration_audit` |

---

## Skew audit

The check that makes the [train/serve policy](Train-Serve-Consistency) self-checking. Without it, train/serve skew is a thing we asserted we fixed in a document.

**How it works.** Roughly five days after each cycle, ERA5T becomes available for that synoptic time. The deterministic stack is re-run on ERA5T inputs and compared against what the operational GDAS-driven run produced. A growing gap means the fine-tuning stage has gone stale relative to whatever NCEP changed in the operational system.

```python
from anemoi.monitoring.skew import SkewMonitor, SkewSample, audit_due

audit_due(target_time, now)          # True once ERA5T should be usable
monitor = SkewMonitor()
monitor.record(sample)
report = monitor.report(now, lead_hours=48)
```

| Parameter | Default |
|---|---|
| Audit delay | 5 days |
| Rolling window | 14 days |
| Minimum samples | 8 |
| Alert: mean 48 h track delta | > 15 nm |
| Alert: mean 48 h intensity delta | > 4 kt |

**`report()` returns `None` below the sample minimum** rather than a noisy estimate. With a handful of storms a fortnight, a two-sample "mean" would fire the retrain trigger on one unusual case.

The intensity delta is **signed** — positive means the operational run was stronger — so a systematic bias is distinguishable from noise. `mean_abs_intensity_delta_kt` drives the alert; `intensity_bias_kt` tells you which direction.

**Response:** a Stage B re-fine-tune of the affected model, plus the derived-model cascade. See [Retraining Triggers](Retraining-Triggers).

**Metrics:** `skew_track_delta_nm_48h`, `skew_intensity_delta_kt_48h`.

**Housekeeping:** `monitor.prune(now)` drops samples older than twice the window.

---

## Feature drift

Compares live feature distributions against a reference — which **must** be the Stage B distribution:

```python
ReferenceDistribution.fit(samples, Flavor.ERA5_PRETRAIN)
# DriftError: drift reference must be the Stage B (gdas_finetune)
# distribution, got era5_pretrain (§4.6.3)
```

Comparing live GDAS features to ERA5 statistics would show a large constant offset that is not drift at all. It would either fire permanently or be tuned until it never fires. This is a small change from v2 with a large consequence.

Two independent signals per feature:

| Signal | Default threshold | Usually means |
|---|---|---|
| Standardised mean shift | \|shift\| > 2.0 σ | Model pushed off its training manifold |
| Variance ratio | > 3× or < ⅓ | Upstream feed returning a constant, or a units change |

```python
report = detect_feature_drift(reference, live_features)
report.alert       # bool
report.drifted     # tuple of FeatureDrift
report.summary()   # "2 drifted feature(s) over 200 samples;
                   #  worst shear_magnitude_kt shift +4.13 sigma"
```

Minimum 30 live samples. Live feature count must match the reference.

In production this is Evidently AI or an equivalent; the implementation here is dependency-free so it runs in CI.

---

## Validation loss

The §5.5 drift trigger, implemented directly:

```python
monitor = ValidationLossMonitor(threshold_fraction=0.15, consecutive_required=3)
monitor.observe(val_loss)   # returns True when the trigger fires
```

Loss above `baseline × 1.15` for **three consecutive checks**. A single recovery resets the count — `test_a_recovery_resets_the_consecutive_count`.

---

## Calibration audit

Answers a narrower, more directly product-facing question than the spread/skill work in [Verification Metrics](Verification-Metrics): not "would a rebuilt cone be calibrated against raw ensemble members," but **was the cone and intensity band this system actually served to a user right, once the real truth became known?** `training.spread_backtest` (#10) needs raw per-member positions, which are sampled and then discarded once the served aggregates are computed — nothing durable keeps them. This audit instead uses what's already durably stored: the served `CycleResult` (#175) and a storm's own real subsequent fixes.

```python
from anemoi.monitoring.calibration_audit import audit_storm, calibrate_products

new_samples = audit_storm(
    storm_id, stored_labels, fixes, checkpoint_store, local_root,
    lead_hours=(12, 24, 36, 48, 72, 96, 120),  # skip downloads with nothing to audit
)
reports = calibrate_products(load_calibration_samples(path, checkpoint_store))
```

**When it runs.** Once per synoptic cycle, as the last step of the `anemoi-cycle` Workflow (see [Operations Runbook](Operations-Runbook#automatic-cycles-in-production)), through `POST /v1/internal/calibration-audit` → `RealState.run_calibration_audit()`. Until #206 it ran inside `_refresh_live_storms`, i.e. inside whichever console request found the live feed stale, downloading every stored cycle of every live storm from R2 while that request waited ([Decision Log #44](Decision-Log#44-every-console-view-woke-the-api-container----storm-reads-now-served-from-kv-206--bugfix-performance)). With `lead_hours` given, a stored cycle whose leads are all not yet due, or all already audited, is skipped from its label alone, without a download.

| Parameter | Default |
|---|---|
| Cone nominal containment | 2/3 (the served cone is a 2/3-probability circle) |
| Intensity band nominal containment | 80% (p10-p90 by construction) |
| Verdict margin | ±15 points |
| Minimum samples for a verdict | 5 |

A lead becomes **due** once its own real valid time has passed — no extra publish-lag margin the way skew needs, since the truth source here is the storm's own live NHC feed, which already publishes close to real synoptic time, not days later (`audit_due`). `containment_rate` is `None` only when zero samples have resolved for that lead yet; below the 5-sample floor it's still a real numeric rate, just with `verdict: "not enough data"` rather than a noisy "too narrow"/"too wide"/"calibrated" call.

**Response:** a lead-dependent regularization tune (see [Decision Log #40](Decision-Log#40-live-served-product-calibration-monitoring--closes-166-follow-up-item-4--enhancement)) if a genuine, sustained miscalibration shows up — not an automatic retrain trigger by itself.

**Metrics:** `GET /v1/monitoring/calibration` (`LeadCalibrationOut[]`), rendered on the console Monitoring page as containment-by-lead against each product's nominal rate.

---

## Production wiring: `RealState` (#148)

The three signals above are the operational logic -- real, tested, unchanged since they were built. What was missing until 2026-09-22 was real data flowing through them in production: `api.real_state.RealState.drift_report()`/`skew_report()` were both hardcoded stubs (`n_live=0`/`n=0`, always), because a *real* deployment fabricating synthetic reference/live numbers the way `DemoState` does for its own demo purposes would be actively misleading, not just incomplete.

**Feature drift is now real end to end:**

1. **The live sample.** Every real cycle (`training.real_inference_cycle.build_real_deterministic_fn`) now computes `data.features.compute_environment_features` once, independent of which Group 1 models go on to contribute -- `DeterministicForecast.env_features`, `None` only when no real gridded field was available at all this cycle.
2. **The reference distribution.** Fit offline, not by the live API process itself:

   ```sh
   anemoi drift-reference-fit --gdas-cache-dir ~/gdas_cache --registry-root ~/.anemoi/registry
   ```

   Iterates real cached GDAS fields (the same `{cache_dir}/{storm_id}/{valid_time}.npz` layout `anemoi gdas-cache` already writes), computes the same `compute_environment_features` a real cycle uses, and fits `ReferenceDistribution`. Persisted via the new `monitoring.reference_store` module -- local JSON plus a best-effort durable mirror through the same `CheckpointStore` `ModelRegistry` already uses, so a fresh Cloudflare Container cold start can pull a reference fit hours earlier from a different machine.
3. **`RealState.drift_report(model)`** compares a rolling in-memory window of this process's own real live samples (capped at 500) against the real reference via `detect_feature_drift`, unchanged. Degrades honestly, not by fabricating: `n_live=0` when no reference has been fit yet, when `model` hasn't itself contributed to a real cycle this process's lifetime, or when fewer than `detect_feature_drift`'s own 30-sample minimum has been collected.

**A real caveat worth knowing, not hidden:** the live-sample window is in-memory only, not durably persisted -- it resets on every cold start. A long-lived warm container accumulates real signal over its own lifetime, but one that recycles often may rarely reach the 30-sample minimum. Real cross-restart persistence of live samples is separate future work, not yet built.

**Skew is now real too (2026-09-22, closing #148 entirely).** It needed two things drift didn't: a durable record of what operationally ran (drift's rolling live-sample window is in-memory, fine for a 30-sample minimum accumulated within one warm container's lifetime, but skew's audit delay is 5 days -- far longer than any observed container lifetime), and a way to swap the input source through the *existing* inference path rather than build a parallel implementation that could drift out of sync with production.

1. **The swap.** `training.real_inference_cycle.build_real_deterministic_fn` and every `training.real_inference_live.build_live_*_x` builder now take an optional `fields_fetcher` override -- default `None` (the unchanged real live/operational GDAS path). The one real caller that passes something else is `monitoring.skew_audit`: `real_inference_live.era5t_fields`, backed by a new `data.real_gridded.fetch_era5t_one` (reuses the already-open ERA5T read confirmed live 2026-09-22 -- ARCO-ERA5's same store used for final ERA5 also carries `valid_time_stop_era5t`, ~6 days behind real time). This re-runs the real deterministic stack -- CNN/Transformer/GNN/PINN's real forward passes, the real learned fusion layer when all five Group 1 models contribute -- pointed at ERA5T instead of GDAS.
2. **The durable operational record.** `RealState.run_cycle` calls `_record_skew_sample` right after a real, non-synthetic-fallback cycle completes: `monitoring.skew_audit.record_operational_cycle` persists the storm's trailing real fixes, the exact `Fix` the cycle used, and the real fused output -- local JSON plus a best-effort durable mirror via `CheckpointStore`, same contract as the drift reference.
3. **The offline audit.** `anemoi skew-audit` (new CLI command) lists every durably-recorded operational cycle old enough for ERA5T to have caught up with (`monitoring.skew.audit_due`) and not yet audited, replays each via the swap above, and appends any resulting real `SkewSample`s to a durably-persisted corpus. A cycle whose ERA5T replay keeps coming back empty for more than twice the audit delay is marked audited anyway, so a genuinely unreachable cycle doesn't get retried forever.
4. **`RealState.skew_report(lead_hours)`** loads that corpus (TTL-refreshed, since new samples land continuously as `skew-audit` runs on a schedule, likely from a different machine), feeds it to the real, unchanged `monitoring.skew.SkewMonitor`, and returns its real report. Degrades honestly, not by fabricating: an empty corpus, or fewer than `SkewMonitor`'s own 8-sample minimum in the rolling 14-day window, reads as `n=0` with an explicit `reasons` entry.

See [Decision Log #33](Decision-Log#33-real-era5t-vs-operational-skew-audit-for-realstate----148-closed--enhancement) for the full writeup, including the real bug-shaped cutoff (give up re-auditing a cycle after 2×`AUDIT_DELAY`) and the test suite that backs it.

---

## Dashboards

§8.3.

- **Model performance:** Grafana displaying real-time track/intensity errors against NHC and ECMWF baselines, per lead time
- **Data drift:** Evidently AI reports comparing incoming feature distributions to the Stage B distribution
- **Cycle health:** flag rates over time — `vitals=estimated`, `nwp_stale`, `spread_fallback`, `load_shed`

That last one is worth building early. A single degraded cycle is routine; a rising rate is a leading indicator that the vitals feed, the NWP transfer or the compute envelope needs attention before it becomes an outage.

---

Related: [Train/Serve Consistency](Train-Serve-Consistency) · [Retraining Triggers](Retraining-Triggers) · [Operations Runbook](Operations-Runbook)
