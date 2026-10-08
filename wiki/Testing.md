# Testing

```bash
uv run pytest                       # full suite
uv run pytest -m "not torch"        # skip model tests explicitly
uv run pytest tests/test_scheduler.py -v
uv run pytest --cov=anemoi
```

**241 passing, 15 skipped.** The skips are `torch`-marked model tests; `conftest.py` skips them automatically when the extra is absent, so a fresh `uv sync` still gives you a green run.

---

## Naming convention

Tests are named after **the behaviour they protect**, not the function they call:

```
test_same_cycle_nwp_is_never_selected_even_when_offered
test_untrained_pinn_is_the_identity
test_retraining_one_group1_model_invalidates_the_derived_models
test_nightly_latent_is_suppressed_while_a_storm_is_active
test_beat_rate_counts_ties_as_losses
```

rather than `test_select_nwp_cycle_2`. When one fails, the name should tell you what broke.

---

## Suite map

| File | Covers |
|---|---|
| `test_time_utils.py` | Synoptic arithmetic; `t−6` selection; `t−12` fallback |
| `test_sources.py` | Role assignment; operational guard |
| `test_besttrack.py` | Working/final separation; emulator statistics; recalibration |
| `test_hurdat2.py` | HURDAT2 parsing; synoptic-hour filtering; missing-field handling |
| `test_atcf.py` | b-deck/TC-Vitals parsing; unit conversion; working/final pairing + recalibration |
| `test_availability.py` | Publication timing; outages; opportunistic feeds |
| `test_scheduler.py` | Cycle timeline; vitals gating; load shedding; deadlines |
| `test_curriculum.py` | Stage A/B ordering; flavor rules; deployability |
| `test_promotion.py` | Validation-only gates; manual gate; test-set budget; track/intensity threshold split |
| `test_registry.py` | Versioning; model-set pinning; rollback; MLflow degradation |
| `test_triggers.py` | Trigger conditions; cascade; nightly-latent suppression |
| `test_orchestrator.py` | Wave schedules; dependency handling; failure isolation |
| `test_skew.py` | ERA5T audit; alert thresholds; windowing |
| `test_drift.py` | Feature drift; reference flavor; validation-loss trigger |
| `test_metrics.py` | Track/intensity errors; beat rate; DM test; CRPS; spread-skill |
| `test_features_splits.py` | Dual-flavor parity; flavor guards; split leakage; inner-core moisture; cold wake; Emanuel PI closed form |
| `test_cycle.py` | End-to-end cycle; every degraded mode; extrapolation |
| `test_postprocess.py` | Cone construction and fallback; PDF; landfall; RI |
| `test_tags.py` | Tag validation; v2.1 additions |
| `test_synthetic.py` | Generator reproducibility and statistics |
| `test_satellite.py` | Synthetic GOES crop shape/channels; intensity-dependent structure; CNN integration |
| `test_real_gridded.py` | ERA5/GDAS unit conversion and cropping (synthetic-schema); real endpoints behind `ANEMOI_RUN_NETWORK_TESTS=1` |
| `test_models.py` | Architecture shapes and latent contracts (**needs torch**) |

---

## Tests worth reading first

Each of these encodes a v2 defect so it cannot silently return.

| Test | Guards against |
|---|---|
| `test_same_cycle_nwp_is_never_selected_even_when_offered` | Consuming NWP that does not exist yet |
| `test_gdas_latency_exceeds_the_v2_forty_five_minute_assumption` | The latency fact that invalidated v2's schedule |
| `test_assert_input_safe_blocks_final_quality` | Final best-track leaking into inputs |
| `test_curriculum_must_end_on_the_operational_flavor` | Deploying ERA5-only weights |
| `test_test_split_metrics_cannot_gate_promotion` | Burning the held-out set |
| `test_retraining_one_group1_model_invalidates_the_derived_models` | v2's "retrain the affected model only" |
| `test_sequential_schedule_includes_fusion` | v2's omission of fusion from the sequential order |
| `test_nightly_latent_is_suppressed_while_a_storm_is_active` | Swapping the ensemble generator mid-storm |
| `test_reference_must_be_the_stage_b_distribution` | Measuring drift against the wrong reference |
| `test_vitals_timeout_is_derived_not_asserted` | The 10-minute margin shortfall |
| `test_absent_opportunistic_feeds_do_not_flag_the_cycle` | Flag inflation making degradation meaningless |

---

## Markers

```toml
markers = [
    "torch: requires the optional torch extra (skipped automatically if absent)",
    "slow: long-running training-shaped tests",
    "api: requires the optional api extra, fastapi (skipped automatically if absent)",
    "gridded: requires the optional gridded extra, xarray/zarr/eccodes (skipped automatically if absent)",
    "storage: requires the optional storage extra, boto3 (skipped automatically if absent)",
    "tracking: requires the optional tracking extra, mlflow (skipped automatically if absent)",
    "network: makes a real network call to a public data source (skipped by default; run with -m network)",
    "mlflow_live: makes a real network call to a configured MLflow tracking server (skipped automatically unless MLFLOW_TRACKING_URI is set)",
]
```

`conftest.py`'s `pytest_collection_modifyitems` auto-skips `torch`-marked tests when the extra isn't installed, `network`-marked tests unless `ANEMOI_RUN_NETWORK_TESTS=1` is set, and `mlflow_live`-marked tests unless `MLFLOW_TRACKING_URI` is actually set (its presence *is* the opt-in -- a private MLflow server, unlike a public data source, only exists when someone's configured one, so there's no separate flag). `api`-, `gridded`- and `storage`-marked test files self-skip via `pytest.importorskip(...)` at module level instead.

`tests/test_mlflow_client.py`'s `mlflow_live` test is the one real end-to-end check in the suite: source a real `.env` (`MLFLOW_TRACKING_URI`, and `CF_ACCESS_CLIENT_ID`/`CF_ACCESS_CLIENT_SECRET` if the server is behind Cloudflare Access) and `pytest -m mlflow_live` exercises the whole real path -- client construction, Access header injection (`tracking.cloudflare_access`), tunnel, MLflow REST API round trip -- not just unit-level plumbing. See [Model Registry](Model-Registry)'s "Real MLflow server and client" section.

---

## Fixtures

Deliberately few. Most tests construct exactly what they need inline, so a failing test is readable without chasing a fixture chain.

| Fixture | Provides |
|---|---|
| `target_time` | `2026-08-06 06:00 UTC`, a synoptic time |
| `oracle` | `LatencyOracle()` — nominal feed timing |
| `worst_case_oracle` | `LatencyOracle(use_max_latency=True)` |

Timing scenarios are built by configuring an oracle rather than mocking a clock:

```python
oracle = LatencyOracle()
oracle.set_arrival("besttrack_working", t, t + timedelta(hours=3))
oracle.set_missing("gdas_gfs", t - timedelta(hours=6))
```

Three lines for an outage scenario, and the same protocol would let a real season be replayed.

---

## Statistical tests

A few tests assert on distributions rather than exact values, and use large enough samples that they are not flaky:

- `test_emulated_position_error_matches_the_requested_rms` — 2,000 draws, asserts RMS falls in 13–17 nm for a requested 15 nm
- `test_recalibration_recovers_the_injected_error_scale` — 400 pairs, 20% relative tolerance
- `test_calibrated_ensemble_has_a_spread_skill_ratio_near_one` — 600 cases × 30 members, truth and members drawn from the same predictive distribution

All are seeded. If one of these starts failing intermittently, the sample size is the thing to raise — not the tolerance.

---

Related: [Codebase Map](Codebase-Map) · [Getting Started](Getting-Started) · [Decision Log](Decision-Log)
