# Configuration Reference

Three YAML files under `configs/`. **Nothing reads them at runtime**: there is no config loader yet (see [Roadmap](Roadmap)), and the values that run are module constants and function defaults. The files document those values, and `tests/test_config_sync.py` keeps the two honest. It checks every key in all three files against what the code does -- reading constants, defaults, and in places behaviour (which day the monthly trigger fires, which hour the nightly refresh runs) -- and fails when a value disagrees, a key is missing, or a key is added that nothing checks ([Decision Log #48](Decision-Log#48-the-configs-were-never-read----every-value-is-now-checked-against-the-code-211--bugfix-docs)).

The blocks below are the files with their comments removed; the files themselves say where each value lives in code.

---

## `curriculum.yaml`

Two-stage training. See [Train/Serve Consistency](Train-Serve-Consistency).

```yaml
stage_a:
  name: A
  flavor: era5_pretrain
  input_sources: [era5, besttrack_working]
  label_source: besttrack_final
  season_range: [1980, 2019]
  epochs: 60
  learning_rate: 1.0e-3

stage_b:
  name: B
  flavor: gdas_finetune
  input_sources: [gdas_gfs, besttrack_working, goes, sst_ohc]
  label_source: besttrack_final
  season_range: [2021, 2023]
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
  synoptic_hours: [0, 6, 12, 18]
  nwp_lag_hours: 6
  max_nwp_lag_hours: 12
  nominal_vitals_offset_minutes: 45
  vitals_timeout_minutes: 80
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
  lead_hours: [12, 24, 36, 48, 72, 96, 120]
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

> **`scheduled_run_offset_minutes` is when production runs a cycle**, not when it may start: `anemoi-api-real`'s cron (`30 1,7,13,19 * * *` in `docker/api/wrangler.jsonc`) fires 90 minutes after each synoptic time, 10 minutes past the vitals timeout, so vitals have landed or the estimated fallback is the honest answer. The console's storm page uses its own copy (`CYCLE_RUN_DELAY_MIN` in `console/src/lib/utils.ts`) to say when the next cycle is due. The sync test reads the cron and the console constant, and checks the offset stays after the vitals timeout -- move one without the others and it fails.

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
  reference_flavor: gdas_finetune
  shift_sigma: 2.0
  variance_ratio_limit: 3.0
  min_samples: 30
  validation_loss:
    threshold_fraction: 0.15
    consecutive_required: 3

calibration_audit:
  cone_nominal_rate: 0.667          # the served cone is a 2/3-probability circle
  intensity_nominal_rate: 0.8       # p10-p90 band
  verdict_margin: 0.15              # +/- around nominal before "too narrow/wide"
  min_cases: 5                      # below this: "not enough data"

promotion:
  split: val
  flavor: gdas_finetune
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
  suppress_nightly_latent_during_active_storms: true
```

`calibration_audit` holds the four constants behind the served-product calibration verdicts -- see [Monitoring](Monitoring#calibration-audit).

`promotion.split: val` and `drift.reference_flavor: gdas_finetune` are not tunable in any meaningful sense — the code raises on any other value. They are written out because a config file that silently omits a constraint teaches people the constraint does not exist.

---

## Values that should not stay as they are

| Setting | Why |
|---|---|
| `working_track_noise.*` | Documented placeholders. Measure from your own archive with `recalibrate_from_pairs()` — real-format parsers now exist (`data.atcf`, `data.hurdat2`), not yet pointed at a real archive |
| `promotion.thresholds` absolute track/intensity limits | Re-baseline against the current NHC verification report. Beat-rate is the real gate |

---

Related: [Getting Started](Getting-Started) · [Inference Cycle](Inference-Cycle) · [Roadmap](Roadmap)
