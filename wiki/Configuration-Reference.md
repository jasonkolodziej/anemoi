# Configuration Reference

Three YAML files under `configs/`. They document the operating parameters and are the intended source for a config loader; the current implementation carries the same values as module constants, so the two must be kept in step until a loader is wired in.

---

## `curriculum.yaml`

Two-stage training. See [Train/Serve Consistency](Train-Serve-Consistency).

```yaml
stage_a:
  flavor: era5_pretrain
  input_sources: [era5, besttrack_working]
  label_source: besttrack_final
  season_range: [1980, 2019]
  epochs: 60
  learning_rate: 1.0e-3

stage_b:
  flavor: gdas_finetune
  input_sources: [gdas_gfs, besttrack_working, goes, sst_ohc]
  label_source: besttrack_final
  season_range: [2015, 2019]
  epochs: 20
  learning_rate: 1.0e-4
  frozen_modules: [encoder]

working_track_noise:
  position_rms_nm: 15.0     # placeholder — replace via recalibrate_from_pairs
  intensity_rms_kt: 5.0     # placeholder
  pressure_rms_mb: 3.0      # placeholder
  quantise: true
```

**The hard rule:** the final stage is always the operational flavor. A run that stops after Stage A cannot be registered or promoted.

Stage B's learning rate is an order of magnitude below Stage A's by design — the aim is to re-seat the model on the operational distribution, not relearn the representation.

---

## `inference.yaml`

Operational cycle. See [Inference Cycle](Inference-Cycle).

```yaml
cycle:
  synoptic_hours: [0, 6, 12, 18]
  nwp_lag_hours: 6              # cycle t consumes the t−6 cycle
  max_nwp_lag_hours: 12
  nominal_vitals_offset_minutes: 45
  vitals_timeout_minutes: 80    # DERIVED, not chosen — see below
  advisory_offset_minutes: 180
  advisory_margin_minutes: 30
  allow_estimated_vitals: true
  allow_load_shedding: true

budgets:
  standard:                     # minutes from cycle start
    assembly:      {target: 10, max: 20}
    preprocess:    {target: 15, max: 25}
    deterministic: {target: 10, max: 18}
    fusion:        {target: 2,  max: 4}
    diffusion:     {target: 13, max: 25}
    postprocess:   {target: 5,  max: 10}
  reduced:                      # ~25 members instead of 50
    assembly:      {target: 8,  max: 14}
    preprocess:    {target: 12, max: 18}
    deterministic: {target: 10, max: 16}
    fusion:        {target: 2,  max: 4}
    diffusion:     {target: 6,  max: 10}
    postprocess:   {target: 4,  max: 8}

ensemble:
  members: 50
  min_members_for_ensemble_cone: 10
  underdispersion_fraction: 0.5

products:
  lead_hours: [12, 24, 36, 48, 72, 96, 120]
  ri_threshold_kt: 30
  ri_window_hours: 24
  ri_alert_probability: 0.3
```

> **`vitals_timeout_minutes` is derived.** It equals `advisory_offset − reduced_worst_case − advisory_margin` = 180 − 70 − 30 = **80**. If you change a reduced-profile budget or the margin, recompute it — `derive_vitals_timeout()` does this in code and `test_vitals_timeout_is_derived_not_asserted` asserts the two agree. Hardcoding it is how the original 10-minute shortfall got in.

Three parameters interact and must stay consistent:

```
cycle_start_latest + reduced_worst_case + advisory_margin ≤ advisory_offset
```

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
  reference_flavor: gdas_finetune   # never era5_pretrain
  shift_sigma: 2.0
  variance_ratio_limit: 3.0
  min_samples: 30
  validation_loss:
    threshold_fraction: 0.15
    consecutive_required: 3

promotion:
  split: val                        # never test
  flavor: gdas_finetune
  primary_metric: track_error_48h_nm
  require_manual_gate: true
  # track_error_48h_nm re-baselined against NHC's GPRA record (45.4 nm 2024,
  # 53.4 nm 2025, 51.0 nm 2026 target); the rest are not yet re-derived.
  thresholds:
    track_error_48h_nm:          {limit: 70.0,  lower_is_better: true}
    track_error_72h_nm:          {limit: 150.0, lower_is_better: true}
    track_error_120h_nm:         {limit: 250.0, lower_is_better: true}
    intensity_error_48h_kt:      {limit: 15.0,  lower_is_better: true}
    intensity_error_72h_kt:      {limit: 20.0,  lower_is_better: true}
    nhc_consensus_beat_rate_48h: {limit: 0.50,  lower_is_better: false}

test_set_budget:
  max_evaluations_per_season: 4

triggers:
  scheduled_monthly_day: 1
  preseason_date: "05-01"
  data_volume_threshold: 500
  nightly_latent_hour_utc: 2
  suppress_nightly_latent_during_active_storms: true
```

`promotion.split: val` and `drift.reference_flavor: gdas_finetune` are not tunable in any meaningful sense — the code raises on any other value. They are written out because a config file that silently omits a constraint teaches people the constraint does not exist.

---

## Values that should not stay as they are

| Setting | Why |
|---|---|
| `working_track_noise.*` | Documented placeholders. Measure from your own archive with `recalibrate_from_pairs()` — real-format parsers now exist (`data.atcf`, `data.hurdat2`), not yet pointed at a real archive |
| `promotion.thresholds` absolute track/intensity limits | Re-baseline against the current NHC verification report. Beat-rate is the real gate |

---

Related: [Getting Started](Getting-Started) · [Inference Cycle](Inference-Cycle) · [Roadmap](Roadmap)
