# Configuration Reference

Three YAML files under `configs/` set the system's operating parameters. **The code runs on them**: `anemoi.config` reads them at import, into the module constants and function defaults that used to hard-code the same numbers, so every call site is unchanged and each value is written down exactly once ([Decision Log #48](Decision-Log#48-the-configs-were-never-read----every-value-is-now-loaded-at-runtime-211--enhancement)).

The blocks below are the files with their full-line comments removed; the files themselves say where each value is used.

## How the files are loaded

**Where.** First match wins: `$ANEMOI_CONFIG_DIR` (an operator override -- a mounted volume, a test copy), otherwise `configs/` at the repository root, found from the package's own location. Both images built from `docker/multistage.Dockerfile` (the API container and the Cloud Run training job) copy it to `/app/configs` beside `/app/src`, so they need no environment variable.

**No silent defaults.** There are no built-in fallbacks: a missing directory, file or key is a `ConfigError` at import naming the file and key. A fallback would let a misdeployed config run on numbers nobody can see, which is the drift this loader exists to remove.

**Tunable vs fixed keys.** Most keys are tunable: read, type-checked, used. A handful are **fixed** (marked `# fixed:` in the files): they are written down so the constraint is visible, but changing them would break something the file can't -- the synoptic hours every cycle label is keyed on, the trained models' output lead times, the operational flavor, promotion on validation only, the nightly-refresh suppression during active storms. A different value is refused with the reason. `vitals_timeout_minutes` is **derived**: refused unless it equals `advisory_offset − reduced worst case − advisory_margin` for the budgets in the same file.

**Changing a value.** Edit the file in a PR. Anything under `configs/` counts as an API change for the Deploy workflow, so the PR builds and starts the API image ("Test: docker/api") and the merge redeploys the container with the new value. Training reads the same files the next time a job runs; both training-image paths (the GHCR workflow and Cloud Build) smoke-test the image before pushing it. A value the loader refuses fails those checks, not production.

**Validation that can't be expressed per key** also happens at import: `reduced_members` must not exceed `members`; the cone table needs exactly one radius per product lead; `scheduled_run_offset_minutes` must fall after the vitals timeout; `max_nwp_lag_hours` must be a multiple of the 6 h lag; dates and hours must be real ones. Stage input/label sources go through `StageSpec`'s existing role checks, so a labels-only source can't become an input.

**Tests.** `tests/test_config_sync.py` proves every key in the files is read by some module; that edited values reach the running code (in a fresh interpreter pointed at an edited copy); that each kind of invalid file is refused with its message; that the image layout finds its configs with no env var and fails clearly without them; that both images copy `configs/` and a config change redeploys; and that the two copies Python can't reach -- the Worker's cron and the console's `CYCLE_RUN_DELAY_MIN` -- still agree with `scheduled_run_offset_minutes`.

---

## `curriculum.yaml`

Two-stage training. See [Train/Serve Consistency](Train-Serve-Consistency).

```yaml
stage_a:
  name: A  # fixed: recorded in run tags
  flavor: era5_pretrain  # fixed: the stage defines it
  input_sources: [era5, besttrack_working]
  label_source: besttrack_final
  season_range: [1980, 2019]
  epochs: 60
  learning_rate: 1.0e-3

stage_b:
  name: B  # fixed: recorded in run tags
  flavor: gdas_finetune  # fixed: the stage defines it
  input_sources: [gdas_gfs, besttrack_working, goes, sst_ohc]
  label_source: besttrack_final
  season_range: [2021, 2023]
  # Forecast hour of the GFS fields Stage B trains on (#215). Live cycles
  # read the t-6 cycle's f006 (inference.yaml cycle.nwp_lag_hours): the t
  # analysis isn't published until ~t+3:30, after the cycle has run. Keep
  # equal to that lag; 0 (analyses) is what caches before #215 hold.
  nwp_lead_hours: 6
  epochs: 20
  learning_rate: 1.0e-4
  frozen_modules: [encoder]

working_track_noise:
  position_rms_nm: 15.0
  intensity_rms_kt: 5.0
  pressure_rms_mb: 3.0
  quantise: true
```

**The hard rule:** the final stage is always the operational flavor. A run that stops after Stage A cannot be registered or promoted.

Stage B's learning rate is an order of magnitude below Stage A's by design — the aim is to re-seat the model on the operational distribution, not relearn the representation.

Stage B's `season_range` is **2021–2023**: 2021 is the first season the real GDAS archive (`noaa-gfs-bdp-pds`) has data for, and 2023 is the latest season the bundled HURDAT2 archive has final best-track labels for. Stage B needs both for every season it trains on. (This page showed `[2015, 2019]` until #211 -- a range with no real GDAS data at all.)

---

## `inference.yaml`

Operational cycle. See [Inference Cycle](Inference-Cycle).

```yaml
cycle:
  synoptic_hours: [0, 6, 12, 18]  # fixed: every cycle label is keyed on these
  nwp_lag_hours: 6  # fixed: one cycle interval
  max_nwp_lag_hours: 12
  nominal_vitals_offset_minutes: 45
  vitals_timeout_minutes: 80  # fixed: derived; must equal the budgets
  advisory_offset_minutes: 180
  advisory_margin_minutes: 30
  allow_estimated_vitals: true
  allow_load_shedding: true
  scheduled_run_offset_minutes: 90

budgets:
  standard:
    assembly:      {target: 10, max: 20}
    preprocess:    {target: 15, max: 25}
    deterministic: {target: 10, max: 18}
    fusion:        {target: 2,  max: 4}
    diffusion:     {target: 13, max: 25}
    postprocess:   {target: 5,  max: 10}
  reduced:
    assembly:      {target: 8,  max: 14}
    preprocess:    {target: 12, max: 18}
    deterministic: {target: 10, max: 16}
    fusion:        {target: 2,  max: 4}
    diffusion:     {target: 6,  max: 10}
    postprocess:   {target: 4,  max: 8}

ensemble:
  members: 50
  reduced_members: 25
  min_members_for_ensemble_cone: 10
  underdispersion_fraction: 0.5
  climatological_cone_nm:
    12: 25
    24: 39
    36: 49
    48: 62
    72: 95
    96: 134
    120: 200

products:
  lead_hours: [12, 24, 36, 48, 72, 96, 120]  # fixed: the trained models' output leads
  cone_percentile: 67
  landfall_threshold_nm: 60
  ri_threshold_kt: 30
  ri_window_hours: 24
  ri_alert_probability: 0.3
```

> **`vitals_timeout_minutes` is derived.** It equals `advisory_offset − reduced_worst_case − advisory_margin` = 180 − 70 − 30 = **80**. If you change a reduced-profile budget or the margin, recompute it — `derive_vitals_timeout()` does this in code and `test_vitals_timeout_is_derived_not_asserted` asserts the two agree. Hardcoding it is how the original 10-minute shortfall got in.

Three parameters interact and must stay consistent:

```
cycle_start_latest + reduced_worst_case + advisory_margin ≤ advisory_offset
```

> **`scheduled_run_offset_minutes` is when production runs a cycle**, not when it may start: `anemoi-api-real`'s cron (`30 1,7,13,19 * * *` in `docker/api/wrangler.jsonc`) fires 90 minutes after each synoptic time, 10 minutes past the vitals timeout, so vitals have landed or the estimated fallback is the honest answer. The console's storm page uses its own copy (`CYCLE_RUN_DELAY_MIN` in `console/src/lib/utils.ts`) to say when the next cycle is due. The Python side refuses an offset that isn't after the vitals timeout, and the sync test reads the cron and the console constant -- move one without the others and it fails.

`ensemble.reduced_members` is the load-shedding ensemble size (the 2:1 ratio of #8). `products.cone_percentile` and `products.landfall_threshold_nm` are the definitions of two served products: the ensemble cone's radius is the 67th percentile of member distance from the ensemble mean, and landfall probability counts members passing within 60 nm of the requested coastal point. `ensemble.climatological_cone_nm` is NHC's current-season (2026) 2/3-probability cone, used when the ensemble is too tight to trust; re-baseline it every season.

---

## `monitoring.yaml`

Skew, drift and promotion. See [Monitoring](Monitoring) and [Training Architecture](Training-Architecture).

```yaml
skew_audit:
  audit_delay_days: 5
  window_days: 14
  min_samples: 8
  lead_hours: 48
  alert_track_delta_nm: 15.0
  alert_intensity_delta_kt: 4.0

drift:
  reference_flavor: gdas_finetune  # fixed: never era5_pretrain
  shift_sigma: 2.0
  variance_ratio_limit: 3.0
  min_samples: 30
  validation_loss:
    threshold_fraction: 0.15
    consecutive_required: 3

calibration_audit:
  cone_nominal_rate: 0.6666666666666666  # 2/3: the served cone is a 2/3-probability circle
  intensity_nominal_rate: 0.8       # p10-p90 band
  verdict_margin: 0.15              # +/- around nominal before "too narrow/wide"
  min_cases: 5                      # below this: "not enough data"

promotion:
  split: val  # fixed: never test
  flavor: gdas_finetune  # fixed: operational flavor only
  primary_metric: track_error_48h_nm
  require_manual_gate: true
  thresholds:
    track_error_48h_nm:         {limit: 70.0,  lower_is_better: true}
    track_error_72h_nm:         {limit: 150.0, lower_is_better: true}
    track_error_120h_nm:        {limit: 250.0, lower_is_better: true}
    intensity_error_48h_kt:     {limit: 15.0,  lower_is_better: true}
    intensity_error_72h_kt:     {limit: 20.0,  lower_is_better: true}
    nhc_consensus_beat_rate_48h: {limit: 0.50, lower_is_better: false}

test_set_budget:
  max_evaluations_per_season: 4

triggers:
  scheduled_monthly_day: 1
  preseason_date: "05-01"
  data_volume_threshold: 500
  nightly_latent_hour_utc: 2
  suppress_nightly_latent_during_active_storms: true  # fixed: safety rule
```

`calibration_audit` holds the four values behind the served-product calibration verdicts -- see [Monitoring](Monitoring#calibration-audit). `cone_nominal_rate` is written as `0.6666666666666666` (exactly 2/3, the served cone's probability) rather than `0.667`, so loading it changed nothing.

`promotion.split: val` and `drift.reference_flavor: gdas_finetune` are fixed keys — the loader refuses any other value. They are written out because a config file that silently omits a constraint teaches people the constraint does not exist.

---

## Values that should not stay as they are

| Setting | Why |
|---|---|
| `working_track_noise.*` | Documented placeholders. Measure from your own archive with `recalibrate_from_pairs()` — real-format parsers now exist (`data.atcf`, `data.hurdat2`), not yet pointed at a real archive |
| `promotion.thresholds` absolute track/intensity limits | Re-baseline against the current NHC verification report. Beat-rate is the real gate |

---

Related: [Getting Started](Getting-Started) · [Inference Cycle](Inference-Cycle) · [Roadmap](Roadmap)
