# Graph Report - anemoi  (2026-11-15)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 6805 nodes · 17456 edges · 234 communities (212 shown, 22 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 2547 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c2b2cf8e`
- The stamp normally lags `HEAD`: CI commits the graph only when code structure changes. It is stale only if code changed since this commit (see AGENTS.md).
- Run `GRAPHIFY_VERSION=0.9.97 .github/scripts/build-graph.sh` after code changes (no API cost; not `graphify update .`, see AGENTS.md).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 170
- Community 171
- Community 172
- Community 173
- Community 174
- Community 175
- Community 176
- Community 177
- Community 178
- Community 179
- Community 180
- Community 181
- Community 182
- Community 183
- Community 184
- Community 185
- Community 186
- Community 187
- Community 188
- Community 189
- Community 190
- Community 191
- Community 192
- Community 193
- Community 194
- Community 195
- Community 196
- Community 198
- Community 199
- Community 200
- Community 201
- Community 202
- Community 203
- Community 204
- Community 205
- Community 206
- Community 207
- Community 208
- Community 209
- Community 210
- Community 211
- Community 212
- Community 213
- Community 214
- Community 215
- Community 216
- Community 217
- Community 218
- Community 219
- Community 220
- Community 221
- Community 222
- Community 223
- Community 224
- Community 225
- Community 226
- Community 227
- Community 228
- Community 229
- Community 230
- Community 232
- Community 233

## God Nodes (most connected - your core abstractions)
1. `Flavor` - 290 edges
2. `Track` - 192 edges
3. `Fix` - 145 edges
4. `ModelRegistry` - 135 edges
5. `CheckpointStore` - 131 edges
6. `TrackQuality` - 106 edges
7. `require_torch()` - 101 edges
8. `MetricSet` - 81 edges
9. `FetchTask` - 71 edges
10. `LatencyOracle` - 68 edges

## Surprising Connections (you probably didn't know these)
- `test_cache_round_trip_and_vector()` --uses--> `FetchTask`  [INFERRED]
  tests/test_steering.py → src/anemoi/data/gridded_cache.py
- `test_internal_calibration_audit_route_reports_new_samples()` --uses--> `RealState`  [INFERRED]
  tests/test_api_real_state.py → src/anemoi/api/real_state.py
- `test_a_versions_arch_params_change_what_is_described()` --calls--> `describe()`  [INFERRED]
  tests/test_model_architecture.py → src/anemoi/models/architecture.py
- `test_the_gnn_is_fed_the_real_lattice()` --calls--> `describe()`  [INFERRED]
  tests/test_model_architecture.py → src/anemoi/models/architecture.py
- `test_load_cached_fields_rejects_a_missing_file()` --calls--> `load_cached_fields()`  [INFERRED]
  tests/test_era5_cache.py → src/anemoi/data/gridded_cache.py

## Import Cycles
- None detected.

## Communities (234 total, 22 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (69): GriddedFields, cache_path(), _decode_cached_fields(), FetchTask, load_cached_fields(), _work(), save_cached_fields(), build_cnn_samples() (+61 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (76): extra_input_conv(), __init__(), extra_input_linear(), __init__(), ModelSpec, require_torch(), torch_available(), build_cnn() (+68 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (63): cycle_inputs_prefix(), _get_text(), list_cycle_labels(), load_drift_live(), _put_text(), save_cycle_inputs(), save_drift_live(), cmd_noise_calibrate() (+55 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (36): absolute_pairs(), basin_value(), is_basin_key(), key_basin(), sample_counts(), scored_basins(), trained_basins(), verified_basins() (+28 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (91): ApiError, apiFetch(), getActivePin(), getArchitecture(), getCalibration(), getCycle(), getDrift(), getDriftAll() (+83 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (49): Flavor, latent_signature(), ModelRegistry, RegistryError, test_cmd_train_actually_transitions_a_promotable_candidate_to_staging(), test_data_volume_counts_seasons_newer_than_any_model_trained_on(), _champions_tagged(), _FakeS3Config (+41 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (52): apply_cold_wake(), area_mean(), assert_flavor(), cold_wake_sst_depression_c(), compare_potential_intensity_estimates(), compute_environment_features(), deep_layer_shear(), emanuel_potential_intensity() (+44 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (41): augment_track(), emulate_working_track(), Track, WorkingTrackNoise, assert_no_leakage(), assign_splits(), _earliest_season(), filter_tracks() (+33 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (51): @lucide/svelte@^1.71.0, svelte-sonner@^1.2.3, sveltekit-superforms@^2.31.0, authClient, { form }, Props, { form }, Props (+43 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (38): basin_inputs(), ModelVersion, _build_live_context(), _build_live_x(), deterministic_fn(), _compute_env_features(), _item_stat(), _live_steering_for() (+30 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (8): cycle_payload_out(), CycleHistory, RealState, deterministic(), live_fields(), RealStormState, _synthetic_fallback_deterministic(), CycleOutput

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (39): adeck_name(), adeck_path(), adeck_urls(), AdeckFetchReport, CachedAdecks, _check_adeck(), _check_official_errors(), fetch_adecks() (+31 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (36): experiment_name(), cmd_train(), latest_final_season(), arch_params_tag(), baseline_beaten(), basin_input_tags(), build_run_tags(), candidate_tags() (+28 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (56): at(), calendarValue, hour, hourAllowed, inRange(), maxValue, minValue, onDateChange() (+48 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (37): cmd_ablation(), cmd_adeck_fetch(), cmd_atcf_archive(), cmd_cache_localize(), cmd_consistency_distill(), cmd_drift_reference_fit(), cmd_era5_cache(), cmd_gdas_cache() (+29 more)

### Community 15 - "Community 15"
Cohesion: 0.04
Nodes (40): svelte@^5.57.1, Props, Section, SectionPage, { sections }, height, motionClass, Props (+32 more)

### Community 16 - "Community 16"
Cohesion: 0.04
Nodes (23): require_api_key(), state_dependency(), get_custom_redoc_html(), create_app(), _debug_last_deterministic_error(), redoc_html(), _lifespan(), get_real_state() (+15 more)

### Community 17 - "Community 17"
Cohesion: 0.06
Nodes (42): AvailabilityOracle, earliest_ready_time(), LatencyOracle, resolve_cycle_inputs(), _valid_time_for(), CycleAbandoned, plan_cycle(), total_budget() (+34 more)

### Community 18 - "Community 18"
Cohesion: 0.05
Nodes (39): build_cone(), build_products(), climatological_cone_nm(), cone_radius_from_spread(), ConeSegment, deterministic_center(), EnsembleMember, ForecastProducts (+31 more)

### Community 19 - "Community 19"
Cohesion: 0.06
Nodes (38): build_derived_schedule(), build_schedule(), _latent_task(), Mode, OrchestrationResult, ResourceProfile, run_schedule(), RunOutcome (+30 more)

### Community 20 - "Community 20"
Cohesion: 0.05
Nodes (34): _crop_variable(), fetch_real_satellite_crop(), _find_real_scan(), GoesFetchError, _lazy_open(), _list_scan_keys(), _nearest_scan_key(), _parse_scan_start() (+26 more)

### Community 21 - "Community 21"
Cohesion: 0.06
Nodes (36): fetch_one(), archive_key(), ArchiveClient, build_fetch_tasks(), FetchCacheReport, filter_tracks_by_min_valid_time(), _memo_enabled(), run_fetch_cache() (+28 more)

### Community 22 - "Community 22"
Cohesion: 0.06
Nodes (50): @cloudflare/containers@^0.3.7, AppAuth, buildAuth(), getAuth(), verifyApiKey(), CYCLE_STEP, cycleInstanceId(), CycleParams (+42 more)

### Community 23 - "Community 23"
Cohesion: 0.05
Nodes (39): brier_score(), crps_ensemble(), _crps_rows(), crps_series(), ensemble_percentiles(), rank_histogram(), reliability(), spread_skill() (+31 more)

### Community 24 - "Community 24"
Cohesion: 0.06
Nodes (33): check_run(), CycleConflict, _existing_source(), InFlight, operator_ids(), RunRequest, stored_source(), RunInfo (+25 more)

### Community 25 - "Community 25"
Cohesion: 0.06
Nodes (35): cycle_key(), load_cycle_result(), save_cycle_result(), audit_cycle(), audit_due(), audit_storm(), _audited_key(), calibrate_products() (+27 more)

### Community 26 - "Community 26"
Cohesion: 0.06
Nodes (36): steering_meta_digest(), build_live_cnn_x(), build_live_gnn_x(), build_live_lstm_x(), build_live_pinn_x(), build_live_transformer_x(), _current_fields(), _current_window() (+28 more)

### Community 27 - "Community 27"
Cohesion: 0.06
Nodes (38): cycle_products_out(), cycle_result_out(), model_version_out(), provenance_out(), get_active_pin(), get_model_architecture(), get_model_registry(), list_registry() (+30 more)

### Community 28 - "Community 28"
Cohesion: 0.06
Nodes (34): pair_by_valid_time(), parse_bdeck(), parse_tcvitals(), TcVitalsError, Fix, recalibrate_from_pairs(), TrackQuality, as_issued() (+26 more)

### Community 29 - "Community 29"
Cohesion: 0.08
Nodes (36): assert_deployable(), Curriculum, CurriculumError, CurriculumRun, stage_a(), stage_b(), StageResult, run_diffusion_curriculum() (+28 more)

### Community 30 - "Community 30"
Cohesion: 0.05
Nodes (45): layerchart@^2.5.1, FixOut, IntensityPercentiles, TrackPointOut, colorFor(), god(), bounds, colors (+37 more)

### Community 31 - "Community 31"
Cohesion: 0.06
Nodes (33): svelte-guard@^1.1.1, authHandle(), guards, handle, DEFAULT_AFTER_LOGIN, loginHref(), safeNext(), Auth (+25 more)

### Community 32 - "Community 32"
Cohesion: 0.07
Nodes (30): invalidated_by(), evaluate_all(), expand_jobs(), nightly_latent(), on_data_volume(), on_drift(), on_latent_desync(), on_skew() (+22 more)

### Community 33 - "Community 33"
Cohesion: 0.06
Nodes (24): basin_one_hot(), with_basin_channels(), with_basin_columns(), with_basin_vector(), batch_graph(), gnn_input(), GnnStageSamples, MeshTopology (+16 more)

### Community 34 - "Community 34"
Cohesion: 0.05
Nodes (29): _baseline_inputs(), _empty_report(), _hurdat2_storm(), make_args(), make_track(), _retrain_check_args(), _spy_assign_splits(), test_adeck_fetch_reads_the_split_and_keeps_cached_files() (+21 more)

### Community 35 - "Community 35"
Cohesion: 0.08
Nodes (24): _aligned(), assemble_validation_forecasts(), scored(), BaselineBacktestError, collect_validation_forecasts(), dump_validation_forecasts(), format_forecast_check(), group1_versions_of() (+16 more)

### Community 36 - "Community 36"
Cohesion: 0.05
Nodes (36): ModelCatalog, BY_ARCHITECTURE, BY_SLUG, FUNCTIONAL_COLORS, FUSION_COLOR, GOD_ORDER, GODS, Module (+28 more)

### Community 37 - "Community 37"
Cohesion: 0.06
Nodes (42): SourceOut, byUse(), hasUnknownEntry(), MODEL_NAMES, MODELS, ORDER, readersOf(), SOURCE_NAMES (+34 more)

### Community 38 - "Community 38"
Cohesion: 0.06
Nodes (23): haversine_nm(), LeadCalibration, LeadTimeStats, motion_bearing(), to_metric_dict(), VerificationPair, verify(), ConfigResult (+15 more)

### Community 39 - "Community 39"
Cohesion: 0.08
Nodes (27): bearing_deg(), bearings_deg(), cross_along_track_nm(), cross_along_track_nms(), km_to_nm(), nm_to_km(), offset_position(), offset_positions() (+19 more)

### Community 40 - "Community 40"
Cohesion: 0.08
Nodes (30): cache_all_fixes(), cache_steering(), _curriculum_tracks(), _FakeS3Client, _fields(), _forward(), make_track(), test_a_zero_steering_conv_computes_the_plain_model() (+22 more)

### Community 41 - "Community 41"
Cohesion: 0.06
Nodes (15): calibration_out(), drift_report_out(), god_out(), model_catalog(), retrain_job_out(), skew_report_out(), health(), models() (+7 more)

### Community 42 - "Community 42"
Cohesion: 0.05
Nodes (14): _RecordingStore, _StubMlflowClient, _StubRun, _StubRunInfo, test_a_failing_store_never_fails_training(), test_baseline_beaten_is_none_when_metric_is_missing(), test_baseline_beaten_matches_promotions_own_threshold(), test_log_stage_run_creates_a_real_run_for_fusion() (+6 more)

### Community 43 - "Community 43"
Cohesion: 0.07
Nodes (25): reconcile_official_errors(), technique_member(), techniques_to_read(), TechniqueSpec, validation_tracks(), adeck_text(), adecks(), archive() (+17 more)

### Community 44 - "Community 44"
Cohesion: 0.08
Nodes (25): boundaries_for_flavor(), run_lstm_curriculum(), StageSamples, _fake_checkpoint_store(), FakeS3Client, make_track(), test_a_run_on_two_basins_scores_each_on_its_own(), test_boundaries_for_flavor_picks_default_for_era5_pretrain() (+17 more)

### Community 45 - "Community 45"
Cohesion: 0.11
Nodes (24): case_errors(), compared_members(), homogeneous_mask(), _limiting(), _mean(), Member, MemberScore, _paired() (+16 more)

### Community 46 - "Community 46"
Cohesion: 0.09
Nodes (28): ExecutionMode, Task, fake_load_run_artifacts(), _FakeJointLatents, runner(), fake_extract_joint_latents(), make_fake(), test_a_failing_model_is_reported_not_raised() (+20 more)

### Community 47 - "Community 47"
Cohesion: 0.09
Nodes (13): cycle_plan_out(), schedule(), ScheduleOut, _budgets(), CyclePlan, derive_vitals_timeout(), plan_day(), _schedule_stages() (+5 more)

### Community 48 - "Community 48"
Cohesion: 0.13
Nodes (25): run_cycle(), deterministic_fn(), good_ensemble(), make_fix(), test_a_pacific_climatological_ensemble_is_drawn_from_pacific_radii(), test_absent_opportunistic_feeds_do_not_flag_the_cycle(), test_an_eastern_pacific_cycle_falls_back_to_nhcs_pacific_radii(), test_caller_requested_members_is_honored_by_the_climatological_fallback() (+17 more)

### Community 49 - "Community 49"
Cohesion: 0.09
Nodes (21): advisory_time(), floor_synoptic(), is_synoptic(), next_synoptic(), NWPUnavailableError, parse_cycle_label(), require_synoptic(), _require_utc() (+13 more)

### Community 50 - "Community 50"
Cohesion: 0.08
Nodes (25): _check_basin(), cycle_date(), ohc_global(), ohc_url(), OhcField, select_file(), sshae_baseline(), target_creation_day() (+17 more)

### Community 51 - "Community 51"
Cohesion: 0.10
Nodes (24): evaluate_promotion(), PromotionError, TestSetBudget, Threshold, _thresholds(), complete_run(), good_metrics(), test_beat_rate_threshold_is_higher_is_better() (+16 more)

### Community 52 - "Community 52"
Cohesion: 0.08
Nodes (22): format_report(), recommend_extra_conditioning(), run_spread_backtest(), SpreadBacktestError, SpreadBacktestReport, _fake_val(), _FakeS3Client, _lc() (+14 more)

### Community 53 - "Community 53"
Cohesion: 0.08
Nodes (25): by_basin(), _forecasts(), metric_set(), test_a_basin_is_verified_when_the_model_beats_persistence_there(), test_a_basin_validated_but_never_trained_on_is_not_verified(), test_a_candidate_that_loses_a_verified_basin_is_refused(), test_a_candidate_that_scored_no_basin_is_judged_as_before(), test_a_candidate_verified_in_a_new_basin_may_be_slightly_worse_on_the_reference() (+17 more)

### Community 54 - "Community 54"
Cohesion: 0.07
Nodes (16): App, Locals, Platform, clearPreferenceStorage(), consent, CONSENT_KEY, ConsentCategory, ConsentChoice (+8 more)

### Community 55 - "Community 55"
Cohesion: 0.10
Nodes (27): expected_coordinates(), place(), _decode(), files(), local(), _ohc(), _row_col(), server() (+19 more)

### Community 56 - "Community 56"
Cohesion: 0.05
Nodes (39): devDependencies, cn@^0.3.3, @fontsource-variable/geist@^5.3.0, @fontsource-variable/geist-mono@^5.3.0, @fontsource-variable/inter@^5.3.0, formsnap@^2.0.1, mode-watcher@^1.1.0, @playwright/test@^1.63.0 (+31 more)

### Community 57 - "Community 57"
Cohesion: 0.08
Nodes (17): _created_date(), creation_day(), _declared_length(), decode_ohc(), detect_format(), fetch_ohc_file(), _grid_values(), name_day_for_creation() (+9 more)

### Community 58 - "Community 58"
Cohesion: 0.08
Nodes (23): _crop_box(), gdas_to_gridded_fields(), crop(), _saturation_vapor_pressure_hpa_array(), _specific_humidity_to_rh_pct(), _global_grid_with_marker(), _synthetic_era5_dataset(), _synthetic_gdas_fields() (+15 more)

### Community 59 - "Community 59"
Cohesion: 0.09
Nodes (20): Stage, test_a_basin_is_in_distribution_once_every_served_model_is_verified_in_it(), _fake_checkpoint_store(), _reconcile_args(), test_cmd_train_passes_streaming_batch_size_and_num_workers_through(), fake_curriculum(), test_cmd_train_passes_the_steering_cache_to_a_gridded_model(), fake() (+12 more)

### Community 60 - "Community 60"
Cohesion: 0.09
Nodes (17): require_meta(), steering_inputs(), _context_features(), _displacement_to_absolute(), _empty_samples(), _extract_for_tracks(), extract_joint_latents(), extract_validation_latents() (+9 more)

### Community 61 - "Community 61"
Cohesion: 0.07
Nodes (37): dependencies, arktype@^2.2.7, @better-auth/passkey@^1.7.7, bits-ui@^2.20.6, clsx@^2.1.1, d3-polygon@^3.0.1, d3-scale@^4.0.2, @internationalized/date@^3.12.4 (+29 more)

### Community 62 - "Community 62"
Cohesion: 0.09
Nodes (20): __init__(), extra_channel_patch(), ArmResult, compare(), expand_patch_channels(), _renamed(), run_steering_spike(), track_errors_nm() (+12 more)

### Community 63 - "Community 63"
Cohesion: 0.12
Nodes (18): audit_due(), _prune_samples(), SkewMonitor, SkewReport, SkewSample, flaky_audit_one(), sample(), test_audit_becomes_due_once_era5t_lands() (+10 more)

### Community 64 - "Community 64"
Cohesion: 0.10
Nodes (19): _decode_one_sonde(), DropsondeFetchError, DropsondeProfile, fetch_and_parse_dropsonde_mission(), fetch_dropsonde_mission_tarball(), _ftp_connect(), list_dropsonde_missions(), _mask_missing() (+11 more)

### Community 65 - "Community 65"
Cohesion: 0.12
Nodes (20): _bytemap_path(), decode_ssmis_bytemap(), fetch_and_decode_ssmis_daily(), fetch_ssmis_daily_bytemap(), MicrowaveFetchError, RSSFtpCredentials, SSMISDaily, _make_bytemap() (+12 more)

### Community 66 - "Community 66"
Cohesion: 0.12
Nodes (24): displacement_nm(), storm_relative_sequence(), validate(), make_fix(), test_displacement_direction_matches_bearing(), test_displacement_magnitude_matches_haversine_distance(), test_displacement_nm_matches_storm_relative_sequence(), test_eastward_motion_is_positive_dx_with_a_small_northward_component() (+16 more)

### Community 67 - "Community 67"
Cohesion: 0.08
Nodes (20): client(), _get_real_state(), hurdat2_file(), _stage_group1_and_derived(), test_a_live_storm_keeps_its_cycles_across_a_feed_refresh(), test_a_stale_refresh_in_flight_serves_known_storms_without_waiting(), test_calibration_report_is_honest_empty_with_no_samples(), test_calibration_report_reflects_persisted_samples() (+12 more)

### Community 68 - "Community 68"
Cohesion: 0.09
Nodes (31): ArchitectureOut, LayerOut, {
		arch,
		onclose,
		class: className = ''
	}, Box, boxFor(), clamp(), color, focus (+23 more)

### Community 69 - "Community 69"
Cohesion: 0.06
Nodes (35): context, dockerfile, postgres, AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY, MLFLOW_S3_ENDPOINT_URL, POSTGRES_DB (+27 more)

### Community 70 - "Community 70"
Cohesion: 0.08
Nodes (9): DemoState, deterministic(), get_state(), StormState, cmd_cycle(), deterministic(), climatological_ensemble(), DeterministicForecast (+1 more)

### Community 71 - "Community 71"
Cohesion: 0.09
Nodes (17): cmd_baseline_backtest(), storm_basin(), basin_key(), per_basin_scores(), _displacement(), _mean_or_none(), _notes(), persistence_members() (+9 more)

### Community 72 - "Community 72"
Cohesion: 0.11
Nodes (18): disc_mean(), fetch_lead_flow(), group_by_time(), lead_flow(), LeadFlow, load_steering(), run_steering_cache(), fetch() (+10 more)

### Community 73 - "Community 73"
Cohesion: 0.09
Nodes (19): config_copy(), edit(), _cron_run_offset_minutes(), _image_layout(), _leaves(), _load(), _run(), test_a_config_change_redeploys_the_api() (+11 more)

### Community 74 - "Community 74"
Cohesion: 0.10
Nodes (16): ensemble(), build_real_ensemble_fn(), ensemble_fn(), InferenceEnsembleError, cache_current_fix(), _FakeS3Client, make_track(), _register() (+8 more)

### Community 75 - "Community 75"
Cohesion: 0.11
Nodes (20): fetch_current_storm_ids(), fetch_current_storms(), fetch_live_track(), fetch_live_tracks(), fetch_one(), _get(), LiveAtcfError, test_fetch_current_storm_ids_parses_and_uppercases() (+12 more)

### Community 76 - "Community 76"
Cohesion: 0.09
Nodes (18): QUICK, API, DEVELOP, PHONE, SourceRow, SOURCES, SOURCES_BEFORE_USED_BY, SOURCES_REWIRED (+10 more)

### Community 77 - "Community 77"
Cohesion: 0.06
Nodes (28): AsyncReturnType, Expand, ExtractGenericViewableContent, GenericItem, GenericSelectorOption, GenericSnippetProps, GenericViewableContent, InheritedSnippetProps (+20 more)

### Community 78 - "Community 78"
Cohesion: 0.11
Nodes (26): assert_input_safe(), emulate_working_fix(), _latlon(), make_fix(), make_track(), test_assert_input_safe_allows_working_quality(), test_assert_input_safe_blocks_final_quality(), test_augment_track_rejects_non_final_input() (+18 more)

### Community 79 - "Community 79"
Cohesion: 0.13
Nodes (20): build_mesh_topology(), cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_batch_graph_offsets_edges_per_sample_block(), test_build_gnn_samples_empty_when_nothing_cached() (+12 more)

### Community 80 - "Community 80"
Cohesion: 0.14
Nodes (17): cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_a_basin_with_no_cached_fields_was_not_trained_on(), test_build_cnn_samples_empty_when_nothing_cached(), test_build_cnn_samples_rejects_ragged_cached_shapes() (+9 more)

### Community 81 - "Community 81"
Cohesion: 0.06
Nodes (31): data, basins, stage_a, epochs, flavor, input_sources, label_source, learning_rate (+23 more)

### Community 82 - "Community 82"
Cohesion: 0.14
Nodes (15): build_real_deterministic_fn(), InferenceCycleError, cache_current_fix(), _FakeS3Client, make_track(), _register_real_version(), _store(), test_build_real_deterministic_fn_combines_all_four_real_models() (+7 more)

### Community 83 - "Community 83"
Cohesion: 0.08
Nodes (30): better-auth@^1.7.7, @better-auth/api-key@^1.7.7, @types/node@^26.6.4, typescript@^5.9.3, wrangler@^4.147.0, better-auth, @better-auth/api-key, @types/node (+22 more)

### Community 84 - "Community 84"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, env, GH_TOKEN, GRAPHIFY_VERSION, permissions, runs-on (+22 more)

### Community 85 - "Community 85"
Cohesion: 0.08
Nodes (15): _expected_meta(), test_a_failed_time_is_reported_and_the_others_still_written(), fetch(), test_a_lost_race_with_no_file_appearing_raises_the_write_error(), test_cache_round_trip_and_vector(), test_disc_mean_is_symmetric_for_a_field_linear_in_longitude(), test_features_advect_with_the_flow_plus_beta_drift(), test_features_raise_where_there_is_no_flow() (+7 more)

### Community 86 - "Community 86"
Cohesion: 0.07
Nodes (23): rehype-slug@^6.0.0, rehype-stringify@^10.0.1, remark-gfm@^4.0.1, remark-parse@^11.0.0, remark-rehype@^11.1.2, unified@^11.0.5, unist-util-visit@^5.1.0, CONSOLE_ROOT (+15 more)

### Community 87 - "Community 87"
Cohesion: 0.07
Nodes (29): WithElementRef, ButtonClickEvent, PrimitiveAnchorAttributes, PrimitiveButtonAttributes, PrimitiveCanvasAttributes, PrimitiveDivAttributes, PrimitiveElementAttributes, PrimitiveFigureAttributes (+21 more)

### Community 88 - "Community 88"
Cohesion: 0.11
Nodes (14): _default_fetch_fn(), fetch(), era5_deps_available(), fetch_era5t_one(), fetch_gdas_grib2_fields(), fetch_grib2_messages(), gfs_url(), gridded_deps_available() (+6 more)

### Community 89 - "Community 89"
Cohesion: 0.13
Nodes (15): cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_build_pinn_samples_empty_when_nothing_cached(), test_build_pinn_samples_environment_width_matches_feature_names(), test_build_pinn_samples_skips_fixes_with_no_cached_file() (+7 more)

### Community 90 - "Community 90"
Cohesion: 0.07
Nodes (11): _FakeMlflowModelVersion, _mlflow_client_that_registers_and_transitions(), create_model_version(), test_mlflow_mirror_registers_model_then_version_with_a_real_source_uri(), create_model_version(), test_mlflow_mirror_skips_create_registered_model_if_it_already_exists(), create_model_version(), test_mlflow_transition_also_mirrors_the_archived_incumbent() (+3 more)

### Community 91 - "Community 91"
Cohesion: 0.08
Nodes (22): CyclePlanOut, deadline, { plan }, Props, stageLabel, t0, totalMs, pollWhileVisible() (+14 more)

### Community 92 - "Community 92"
Cohesion: 0.07
Nodes (28): inputArgs, jobs, projectId, region, results, timeoutSeconds, assign, return (+20 more)

### Community 93 - "Community 93"
Cohesion: 0.15
Nodes (17): AblationReport, build_samples(), _cell(), make_track(), test_at_fraction_filters_and_sorts_by_hidden_dim(), test_build_samples_augmentation_multiplies_sample_count(), test_build_samples_shapes_match_sequence_length_and_columns(), test_build_samples_skips_storms_shorter_than_required() (+9 more)

### Community 94 - "Community 94"
Cohesion: 0.12
Nodes (13): DiffusionArtifacts, _standardize(), _standardize_y(), train_diffusion_stage(), _FakeS3Client, _make_samples(), test_a_longer_epoch_budget_never_returns_a_worse_val_loss(), test_early_stopping_halts_before_the_epoch_cap_on_a_real_overfitting_run() (+5 more)

### Community 95 - "Community 95"
Cohesion: 0.14
Nodes (12): Fetcher, ingest_cycle_inputs(), ingest_one(), IngestionOutcome, IngestionRecord, LakeTier, LakeWriter, LocalLakeWriter (+4 more)

### Community 96 - "Community 96"
Cohesion: 0.10
Nodes (15): used_by(), test_cmd_sources_prints_who_uses_each_source(), _model_sources(), test_a_label_or_verification_source_is_never_a_model_input(), test_a_verification_source_not_read_yet_is_verification_and_nothing_else(), test_an_adapter_is_named_by_other_code_only_if_its_source_is_read(), test_each_curriculum_stage_lists_what_its_models_read(), test_every_fetch_adapter_is_classified() (+7 more)

### Community 97 - "Community 97"
Cohesion: 0.13
Nodes (14): detect_feature_drift(), FeatureDrift, ValidationLossMonitor, reference(), test_a_recovery_resets_the_consecutive_count(), test_collapsed_variance_is_detected(), test_feature_count_mismatch_raises(), test_first_observation_only_sets_the_baseline() (+6 more)

### Community 98 - "Community 98"
Cohesion: 0.10
Nodes (16): http_get(), OhcFetchError, OhcNotPublished, OhcUnavailable, Archive, test_a_cut_off_reply_is_a_fetch_failure(), test_a_cut_off_transfer_raises_rather_than_reading_an_older_file(), test_a_fetch_failure_that_is_not_a_404_is_not_stepped_over() (+8 more)

### Community 99 - "Community 99"
Cohesion: 0.13
Nodes (11): fetch_gefs_ensemble_grib2_fields(), fetch_gefs_member_grib2_fields(), _gefs_member_url(), _parse_grib2_index(), require_gdas_deps(), test_control_member_zero_uses_gec00_not_gep00(), test_fetch_gefs_ensemble_reads_multiple_real_distinct_members(), test_fetch_gefs_member_reads_the_real_noaa_archive() (+3 more)

### Community 100 - "Community 100"
Cohesion: 0.12
Nodes (13): initial_fix(), client(), _MemoryS3, s3(), test_an_archive_storm_says_its_fix_is_the_final_best_track(), test_late_vitals_on_a_live_storm_read_as_estimated(), test_missing_vitals_are_extrapolated_and_estimated(), test_one_earlier_fix_is_persisted() (+5 more)

### Community 101 - "Community 101"
Cohesion: 0.10
Nodes (12): color_for(), god(), Module, WindGod, test_every_god_color_is_distinct(), test_experiment_name_handles_fusion_without_raising(), test_experiment_names_are_the_god_slugs(), test_lookup_by_slug_and_by_architecture_agree() (+4 more)

### Community 102 - "Community 102"
Cohesion: 0.16
Nodes (13): cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_build_transformer_samples_empty_when_nothing_cached(), test_build_transformer_samples_rejects_a_cache_smaller_than_grid_size(), test_build_transformer_samples_trims_the_real_41x41_crop_to_grid_size() (+5 more)

### Community 103 - "Community 103"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GH_TOKEN, IMPORTED_FROM, SOURCE_SHA, jobs, publish (+16 more)

### Community 104 - "Community 104"
Cohesion: 0.15
Nodes (18): _lon_close(), _members(), ref_bearing(), ref_crps(), ref_displacement(), ref_haversine(), ref_offset(), rng() (+10 more)

### Community 105 - "Community 105"
Cohesion: 0.15
Nodes (12): accessed(), _check_type(), config_dir(), ConfigError, fixed(), get(), get_list(), _load() (+4 more)

### Community 106 - "Community 106"
Cohesion: 0.16
Nodes (17): run_fetch_cache(), make_fields(), make_track(), test_gdas_archive_start_is_the_first_valid_time_with_an_atmos_f006(), test_run_fetch_cache_defaults_to_lower_concurrency_than_era5(), test_run_fetch_cache_drops_fixes_before_the_real_archive_start_by_default(), fake_fetch(), test_run_fetch_cache_floor_drops_the_fix_just_before_and_keeps_the_one_at_it() (+9 more)

### Community 107 - "Community 107"
Cohesion: 0.14
Nodes (14): fetch_and_parse_ndbc(), fetch_ndbc_realtime2(), _get(), NdbcFetchError, NdbcObservation, parse_ndbc_realtime2(), test_a_row_with_the_wrong_column_count_is_skipped_not_fatal(), test_a_station_missing_wave_columns_still_parses() (+6 more)

### Community 108 - "Community 108"
Cohesion: 0.08
Nodes (3): client(), test_more_members_than_the_ensemble_runs_is_refused_not_silently_capped(), test_sources_say_who_uses_each_one()

### Community 109 - "Community 109"
Cohesion: 0.15
Nodes (14): _all_tensors(), Architecture, _builder(), describe(), describe_cached(), _describe_cached(), hook(), _example_inputs() (+6 more)

### Community 110 - "Community 110"
Cohesion: 0.12
Nodes (12): client(), _fields(), _MemoryS3, _run(), test_a_missing_t_minus_6_cycle_falls_back_to_t_minus_12(), fetch_one(), fetch_one(), test_no_nwp_at_all_is_flagged() (+4 more)

### Community 111 - "Community 111"
Cohesion: 0.13
Nodes (10): _download(), fetch_oisst_sst(), require_sst_deps(), sst_at(), SstFetchError, _small_grid(), test_fetch_oisst_sst_reads_real_recent_data(), test_sst_at_finds_the_nearest_cell() (+2 more)

### Community 112 - "Community 112"
Cohesion: 0.14
Nodes (11): _files(), localize_cache(), LocalizeReport, _raise(), _cache(), test_a_directory_that_cant_be_listed_fails_the_copy(), test_a_missing_source_raises(), test_a_rerun_only_fills_gaps() (+3 more)

### Community 113 - "Community 113"
Cohesion: 0.15
Nodes (16): parse_hurdat2(), parse_hurdat2_file(), test_entry_count_mismatch_raises(), test_header_name_is_parsed_onto_the_track(), test_malformed_header_raises(), test_malformed_latitude_raises(), test_multi_storm_file_produces_one_track_per_storm(), test_non_numeric_entry_count_raises() (+8 more)

### Community 114 - "Community 114"
Cohesion: 0.13
Nodes (12): generate_season(), generate_track(), make_storm_spec(), StormSpec, test_archive_spans_the_requested_seasons(), test_fields_have_matching_shapes_and_carry_a_flavor(), test_fixes_are_six_hourly_and_synoptic(), test_generated_tracks_are_final_quality() (+4 more)

### Community 115 - "Community 115"
Cohesion: 0.14
Nodes (10): lr_factor(), transformer_optim(), TransformerOptim, TransformerOptimizer, test_a_short_stage_still_ends_on_the_floor(), test_config_values_are_validated(), test_cosine_decays_to_the_floor_on_the_last_update(), test_no_warmup_starts_at_the_peak() (+2 more)

### Community 116 - "Community 116"
Cohesion: 0.10
Nodes (7): DELETE, GET, PATCH, POST, PUT, prerender, ssr

### Community 117 - "Community 117"
Cohesion: 0.10
Nodes (20): PROJECT_NUMBER, PROJECT_PAT, types, jobs, sync, name, on, issues (+12 more)

### Community 118 - "Community 118"
Cohesion: 0.13
Nodes (10): season_boundaries(), test_boundaries_move_with_the_archive(), test_run_tags_record_the_commit_split_and_trigger(), test_stage_bs_validation_season_is_never_seen_by_stage_a(), test_the_archive_a_run_was_given_is_not_what_it_trained_on(), test_the_internal_route_runs_a_bounded_pass(), test_the_skew_audit_runs_after_every_cycle_in_the_api_container(), test_too_short_an_archive_is_refused() (+2 more)

### Community 119 - "Community 119"
Cohesion: 0.21
Nodes (6): freeCycleLabel(), label(), runFreshCycle(), signIn(), cases, @playwright/test

### Community 120 - "Community 120"
Cohesion: 0.16
Nodes (17): answerRuns(), chip(), context(), cycleFor(), dateButton(), expectForm(), expectShowing(), fixture (+9 more)

### Community 121 - "Community 121"
Cohesion: 0.19
Nodes (15): run_fetch_cache(), make_fields(), make_track(), test_build_fetch_tasks_covers_every_fix_across_tracks(), test_load_cached_fields_rejects_a_missing_file(), test_run_fetch_cache_actually_runs_fetches_concurrently(), slow_fetch(), test_run_fetch_cache_can_force_refetch_with_skip_existing_false() (+7 more)

### Community 122 - "Community 122"
Cohesion: 0.18
Nodes (10): DriftError, ReferenceDistribution, reference_from_json(), reference_to_json(), save_reference(), test_drift_report_detects_real_drift_once_enough_samples_are_collected(), test_drift_report_is_honest_zero_for_a_model_that_never_contributed(), test_reference_must_be_the_stage_b_distribution() (+2 more)

### Community 123 - "Community 123"
Cohesion: 0.14
Nodes (9): load_reference(), test_drift_reference_fit_fits_and_persists_from_real_cached_fields(), _FakeClient, _make_reference(), test_durable_round_trip_via_a_shared_checkpoint_store(), test_json_round_trips_a_real_reference_exactly(), test_load_reference_degrades_honestly_when_the_store_is_unreachable(), test_load_reference_returns_none_when_nothing_was_ever_fit() (+1 more)

### Community 124 - "Community 124"
Cohesion: 0.17
Nodes (13): _fetcher(), fetch(), _keys(), test_a_storm_is_still_archived_for_a_few_days_after_it_leaves_the_index(), test_a_storm_seen_on_new_years_eve_is_still_followed_on_new_years_day(), test_an_unreachable_index_raises_so_the_caller_reports_it(), test_archived_tcvitals_keeps_every_revision_once_in_issue_order(), test_every_file_is_archived_verbatim_for_every_basin() (+5 more)

### Community 125 - "Community 125"
Cohesion: 0.12
Nodes (5): build_info(), _build_info_path(), config_digest(), summary(), test_every_image_build_is_smoke_tested_before_it_ships()

### Community 126 - "Community 126"
Cohesion: 0.12
Nodes (4): _Boto3Client, require_boto3(), _StorageClient, test_boto3_adapter_configures_the_client_for_the_given_endpoint()

### Community 127 - "Community 127"
Cohesion: 0.11
Nodes (7): client(), test_docs_route_is_unaffected(), test_sources_role_is_the_role_enum_in_the_openapi_schema(), test_sources_used_by_is_documented_in_the_openapi_schema(), test_theme_http_method_colors_are_distinct(), test_theme_never_uses_a_god_color(), _walk()

### Community 128 - "Community 128"
Cohesion: 0.17
Nodes (7): mlflow_client_from_env(), test_an_unreachable_server_is_skipped_fast(), test_builds_a_real_client_when_tracking_uri_is_set(), test_fail_fast_settings_never_override_explicit_ones(), test_mlflow_client_from_env_can_actually_reach_the_configured_server(), test_returns_none_when_tracking_uri_is_unset(), test_returns_none_without_mlflow_installed()

### Community 129 - "Community 129"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 130 - "Community 130"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 131 - "Community 131"
Cohesion: 0.15
Nodes (6): CloudflareAccessRequestHeaderProvider, test_headers_are_actually_applied_by_mlflows_own_resolution(), test_in_context_false_when_neither_var_set(), test_in_context_false_when_only_client_id_set(), test_in_context_true_and_correct_headers_when_both_set(), test_registered_as_a_real_mlflow_plugin_via_entry_points()

### Community 132 - "Community 132"
Cohesion: 0.12
Nodes (16): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+8 more)

### Community 133 - "Community 133"
Cohesion: 0.12
Nodes (16): compilerOptions, allowJs, allowSyntheticDefaultImports, checkJs, forceConsistentCasingInFileNames, isolatedModules, lib, module (+8 more)

### Community 134 - "Community 134"
Cohesion: 0.12
Nodes (16): permissions, runs-on, steps, jobs, copilot-setup-steps, name, on, pull_request (+8 more)

### Community 135 - "Community 135"
Cohesion: 0.22
Nodes (9): archive_atcf(), ArchiveReport, currentstorms_key(), _digest(), snapshot_key(), _stored_digests(), _write_if_new(), test_the_cli_archives_lists_and_needs_credentials() (+1 more)

### Community 136 - "Community 136"
Cohesion: 0.15
Nodes (12): describe(), fetch_latest_hurdat2(), last_season(), manifest_path(), test_a_listing_without_one_archive_falls_back_for_that_archive_only(), test_an_archive_that_cannot_be_downloaded_leaves_the_file_as_it_was(), test_an_unreadable_listing_falls_back_to_the_pinned_file_and_says_so(), fetch() (+4 more)

### Community 137 - "Community 137"
Cohesion: 0.18
Nodes (8): OfficialErrorsError, parse_official_errors(), _signed(), test_parse_official_errors_reads_columns_by_name_and_skips_missing_leads(), test_parse_official_errors_reads_the_stated_initial_position_domain(), test_parse_official_errors_rejects_a_file_without_the_column_header(), test_parse_official_errors_without_a_domain_line_covers_everything(), test_real_atlantic_file_gives_nhcs_published_2024_48h_error()

### Community 138 - "Community 138"
Cohesion: 0.17
Nodes (8): _fresh_real_state(), _memory_store(), _MemoryS3Client, test_a_failed_cycle_write_never_fails_the_cycle(), test_an_unrestored_drift_window_is_never_written_back(), test_cycles_survive_a_container_restart(), test_drift_samples_survive_a_container_restart(), test_list_cycle_labels_ignores_keys_that_are_not_cycle_results()

### Community 139 - "Community 139"
Cohesion: 0.16
Nodes (7): al_2021_2022(), compare(), open_ocean(), parse_ships(), sample_days(), ShipsCase, test_sohc_equals_bilinear_ohc_on_the_file_named_for_the_day_before()

### Community 140 - "Community 140"
Cohesion: 0.15
Nodes (9): _called(), _calls(), _function(), _modules(), _parameters(), _parse(), test_a_fetch_only_importer_names_the_adapter_it_is_listed_for(), test_model_inputs_match_what_each_runner_and_live_builder_takes() (+1 more)

### Community 141 - "Community 141"
Cohesion: 0.12
Nodes (16): with, build-args, cache-from, cache-to, context, file, load, password (+8 more)

### Community 142 - "Community 142"
Cohesion: 0.12
Nodes (15): jobs, lint-and-validate, name, permissions, runs-on, steps, name, on (+7 more)

### Community 143 - "Community 143"
Cohesion: 0.17
Nodes (9): assert_operational_flavor(), CycleError, extrapolate_fix(), fusion_weights(), test_extrapolation_continues_the_last_motion_vector(), test_extrapolation_needs_two_prior_fixes(), test_fusion_weights_favour_the_lower_error_model(), test_fusion_weights_never_zero_a_model_out() (+1 more)

### Community 144 - "Community 144"
Cohesion: 0.19
Nodes (6): _FakeS3Client, _make_samples(), test_run_fusion_curriculum_uploads_a_checkpoint_and_registers_stage_b(), test_train_fusion_stage_reduces_loss_and_produces_val_metrics(), test_train_fusion_stage_rejects_a_val_set_built_with_a_different_model_count(), test_train_fusion_stage_rejects_empty_samples()

### Community 145 - "Community 145"
Cohesion: 0.13
Nodes (15): scripts, build, cf:deploy, check, check:errors, check:warnings, check:watch, dev (+7 more)

### Community 146 - "Community 146"
Cohesion: 0.19
Nodes (12): loading, onInput(), open, query, results, bodyById, buildIndex(), excerptAround() (+4 more)

### Community 147 - "Community 147"
Cohesion: 0.13
Nodes (15): env, environment, if, name, needs, permissions, runs-on, timeout-minutes (+7 more)

### Community 148 - "Community 148"
Cohesion: 0.16
Nodes (10): get(), Role, test_a_model_input_is_never_a_labels_only_source(), test_era5_is_pretrain_only(), test_era5_latency_is_days_not_hours(), test_every_model_reads_a_source_it_can_be_served_from(), test_final_besttrack_is_labels_only(), test_gdas_latency_exceeds_the_v2_forty_five_minute_assumption() (+2 more)

### Community 149 - "Community 149"
Cohesion: 0.14
Nodes (13): compilerOptions, allowJs, checkJs, esModuleInterop, forceConsistentCasingInFileNames, moduleResolution, resolveJsonModule, rewriteRelativeImportExtensions (+5 more)

### Community 150 - "Community 150"
Cohesion: 0.14
Nodes (13): images, options, diskSizeGb, machineType, steps, args, entrypoint, env (+5 more)

### Community 151 - "Community 151"
Cohesion: 0.14
Nodes (14): default, description, type, default, description, type, api, console (+6 more)

### Community 152 - "Community 152"
Cohesion: 0.16
Nodes (6): HomogeneousRow, BaselineReport, _fmt(), format_report(), _json_safe(), test_the_report_serialises_as_strict_json_and_prints_a_table()

### Community 153 - "Community 153"
Cohesion: 0.35
Nodes (7): NoiseSensitivityReport, _result(), test_is_load_bearing_above_threshold(), test_is_not_load_bearing_below_threshold(), test_relative_change_is_zero_when_losses_match(), test_relative_change_rejects_nonpositive_default_loss(), test_relative_change_sign_matches_direction_of_the_move()

### Community 154 - "Community 154"
Cohesion: 0.17
Nodes (12): IdTokenClaims, JwtClaims, OidcAddressClaim, OidcStandardClaims, UserProfile, Mandatory, RFC-3966, RFC-4627 (+4 more)

### Community 155 - "Community 155"
Cohesion: 0.15
Nodes (12): name, runs-on, timeout-minutes, concurrency, cancel-in-progress, group, jobs, build (+4 more)

### Community 156 - "Community 156"
Cohesion: 0.24
Nodes (5): Hurdat2Error, _parse_data_row(), _parse_header(), _parse_latlon(), _storm_rows()

### Community 157 - "Community 157"
Cohesion: 0.15
Nodes (6): distill_consistency_model(), step_loss(), _pseudo_huber(), test_distillation_rejects_a_non_positive_epochs_or_patience(), test_distillation_restores_the_teachers_device_and_mode_even_if_training_raises(), test_distillation_trains_a_student_without_mutating_the_teachers_device()

### Community 158 - "Community 158"
Cohesion: 0.23
Nodes (11): max, target, budgets, reduced, standard, max, target, assembly (+3 more)

### Community 159 - "Community 159"
Cohesion: 0.17
Nodes (4): local, notes, problems, remote

### Community 160 - "Community 160"
Cohesion: 0.20
Nodes (7): client(), test_a_registered_versions_arch_params_are_used(), test_a_version_without_arch_params_is_described_from_defaults(), test_a_versions_arch_params_change_what_is_described(), test_every_model_runs_its_example_input_and_reports_its_layers(), test_the_gnn_is_fed_the_real_lattice(), test_unknown_models_and_versions_are_404()

### Community 161 - "Community 161"
Cohesion: 0.17
Nodes (11): concurrency, cancel-in-progress, group, jobs, test-api, name, if, name (+3 more)

### Community 162 - "Community 162"
Cohesion: 0.17
Nodes (12): with, cache, cache-dependency-path, enable-cache, fetch-depth, if-no-files-found, include-hidden-files, name (+4 more)

### Community 163 - "Community 163"
Cohesion: 0.18
Nodes (11): cycle, advisory_margin_minutes, advisory_offset_minutes, allow_estimated_vitals, allow_load_shedding, max_nwp_lag_hours, nominal_vitals_offset_minutes, nwp_lag_hours (+3 more)

### Community 165 - "Community 165"
Cohesion: 0.25
Nodes (7): _FakeCycleOutput, _make_deterministic_forecast(), _make_storm_state(), test_env_features_none_is_not_recorded_as_a_sample(), test_live_env_features_window_is_capped(), test_record_skew_sample_is_a_noop_for_the_synthetic_fallback(), test_record_skew_sample_persists_locally_without_a_configured_checkpoint_store()

### Community 166 - "Community 166"
Cohesion: 0.22
Nodes (6): first_record_of_year(), ships_al_url(), _ships_get(), ships_record_year(), ships_size(), ships_window()

### Community 167 - "Community 167"
Cohesion: 0.20
Nodes (10): limit, lower_is_better, limit, lower_is_better, thresholds, intensity_error_48h_kt, intensity_error_72h_kt, track_error_72h_nm (+2 more)

### Community 168 - "Community 168"
Cohesion: 0.20
Nodes (10): steps, EXPECT_GIT_SHA, GCP_CI_SERVICE_ACCOUNT, GCP_WIF_PROVIDER, env, id, if, name (+2 more)

### Community 169 - "Community 169"
Cohesion: 0.20
Nodes (10): name, outputs, runs-on, timeout-minutes, changes, deploy_api, deploy_console, plan (+2 more)

### Community 170 - "Community 170"
Cohesion: 0.40
Nodes (10): steps, steps, id, if, name, run, uses, working-directory (+2 more)

### Community 171 - "Community 171"
Cohesion: 0.27
Nodes (4): ChecksumCheck, FetchResult, NonEmptyCheck, QCFinding

### Community 172 - "Community 172"
Cohesion: 0.31
Nodes (4): _attributes(), _imported(), _names_adapter(), _string_literals()

### Community 173 - "Community 173"
Cohesion: 0.22
Nodes (9): run, test-console, working-directory, defaults, if, name, needs, runs-on (+1 more)

### Community 174 - "Community 174"
Cohesion: 0.22
Nodes (9): BASE_SHA, BEFORE_SHA, DISPATCH_API, DISPATCH_CONSOLE, EVENT, EXPECT_GIT_SHA, HEAD_SHA, REF (+1 more)

### Community 175 - "Community 175"
Cohesion: 0.28
Nodes (5): test_default_fetch_fn_wires_a_shared_session(), fake_fetch_gdas_grib2_fields(), fake_gdas_to_gridded_fields(), test_fetch_one_fetches_exactly_one_real_sample(), fake_gdas_to_gridded_fields()

### Community 176 - "Community 176"
Cohesion: 0.25
Nodes (6): source_out(), SourceOut, DataSource, operational_sources(), pretrain_only_sources(), test_operational_sources_pass_the_guard()

### Community 177 - "Community 177"
Cohesion: 0.25
Nodes (6): _default_fetch_fn(), fetch(), era5_to_gridded_fields(), crop(), crop_levels(), store()

### Community 178 - "Community 178"
Cohesion: 0.28
Nodes (4): cache_nwp_lead_hours(), CacheLeadMismatch, _claim_cache_dir(), test_a_cache_dir_holds_one_lead()

### Community 179 - "Community 179"
Cohesion: 0.22
Nodes (6): Archive, archives_for(), latest_name(), test_the_newest_atlantic_release_is_picked(), test_the_newest_northeast_pacific_release_is_picked(), test_which_archives_hold_which_basins()

### Community 180 - "Community 180"
Cohesion: 0.28
Nodes (4): oracle(), pytest_collection_modifyitems(), target_time(), worst_case_oracle()

### Community 181 - "Community 181"
Cohesion: 0.31
Nodes (5): cache_all_fixes(), make_fields(), make_track(), _task_for(), test_extract_joint_latents_rejects_missing_group1_model()

### Community 182 - "Community 182"
Cohesion: 0.25
Nodes (8): 12, 120, 24, 36, 48, 72, 96, climatological_cone_nm

### Community 183 - "Community 183"
Cohesion: 0.25
Nodes (8): CP, 12, 120, 24, 36, 48, 72, 96

### Community 184 - "Community 184"
Cohesion: 0.25
Nodes (8): EP, 12, 120, 24, 36, 48, 72, 96

### Community 185 - "Community 185"
Cohesion: 0.25
Nodes (7): calibration_audit, cone_nominal_rate, intensity_nominal_rate, min_cases, verdict_margin, test_set_budget, max_evaluations_per_season

### Community 186 - "Community 186"
Cohesion: 0.25
Nodes (8): drift, min_samples, reference_flavor, shift_sigma, validation_loss, variance_ratio_limit, consecutive_required, threshold_fraction

### Community 187 - "Community 187"
Cohesion: 0.25
Nodes (8): promotion, flavor, new_basin_tolerance, primary_metric, reference_basin, require_manual_gate, split, basins()

### Community 189 - "Community 189"
Cohesion: 0.32
Nodes (5): assert_not_operational(), _operational_substitute(), OperationalUseError, test_reading_era5_in_the_inference_path_is_refused(), test_reading_final_besttrack_in_the_inference_path_is_refused()

### Community 190 - "Community 190"
Cohesion: 0.39
Nodes (4): _champions(), test_a_basin_is_served_once_every_champion_is_verified_in_it(), test_a_champion_verified_nowhere_serves_no_basin_as_in_distribution(), test_no_champion_or_champions_from_before_the_tag_are_the_atlantic()

### Community 192 - "Community 192"
Cohesion: 0.29
Nodes (7): products, cone_percentile, landfall_threshold_nm, lead_hours, ri_alert_probability, ri_threshold_kt, ri_window_hours

### Community 193 - "Community 193"
Cohesion: 0.29
Nodes (7): skew_audit, alert_intensity_delta_kt, alert_track_delta_nm, audit_delay_days, lead_hours, min_samples, window_days

### Community 194 - "Community 194"
Cohesion: 0.57
Nodes (5): deploy-plan.sh script, touches(), touches_component(), touches_console(), why

### Community 195 - "Community 195"
Cohesion: 0.29
Nodes (7): env, IMAGE, JOB, PROJECT_ID, PUBLISH, REGION, REGISTRY

### Community 196 - "Community 196"
Cohesion: 0.33
Nodes (3): _bilinear(), _lattice_index(), ohc_at()

### Community 199 - "Community 199"
Cohesion: 0.33
Nodes (6): ensemble, climatological_cone_nm_by_basin, members, min_members_for_ensemble_cone, reduced_members, underdispersion_fraction

### Community 200 - "Community 200"
Cohesion: 0.33
Nodes (6): triggers, data_volume_threshold, nightly_latent_hour_utc, preseason_date, scheduled_monthly_day, suppress_nightly_latent_during_active_storms

### Community 202 - "Community 202"
Cohesion: 0.33
Nodes (6): update_job, workflow_dispatch, default, description, type, inputs

### Community 203 - "Community 203"
Cohesion: 0.33
Nodes (6): on, pull_request, push, paths, branches, paths

### Community 204 - "Community 204"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 205 - "Community 205"
Cohesion: 0.40
Nodes (3): WORLD_GEOJSON, WorldData, WorldFeatureProperties

### Community 206 - "Community 206"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 207 - "Community 207"
Cohesion: 0.40
Nodes (3): _get(), _get_bytes(), NotPublished

### Community 210 - "Community 210"
Cohesion: 0.67
Nodes (4): max, target, diffusion, diffusion

### Community 211 - "Community 211"
Cohesion: 0.67
Nodes (4): max, target, fusion, fusion

### Community 212 - "Community 212"
Cohesion: 0.67
Nodes (4): max, target, postprocess, postprocess

### Community 213 - "Community 213"
Cohesion: 0.67
Nodes (4): max, target, preprocess, preprocess

### Community 214 - "Community 214"
Cohesion: 0.50
Nodes (3): ANEMOI_FIELDS_MEMO, ANEMOI_STEERING_CACHE_DIR, entrypoint.sh script

### Community 215 - "Community 215"
Cohesion: 0.83
Nodes (3): graphify(), normalise_graph(), build-graph.sh script

### Community 216 - "Community 216"
Cohesion: 0.50
Nodes (3): uvx, graphify, graphify-mcp

### Community 219 - "Community 219"
Cohesion: 0.67
Nodes (3): limit, lower_is_better, nhc_consensus_beat_rate_48h

### Community 220 - "Community 220"
Cohesion: 0.67
Nodes (3): track_error_120h_nm, limit, lower_is_better

### Community 221 - "Community 221"
Cohesion: 0.67
Nodes (3): track_error_48h_nm, limit, lower_is_better

## Knowledge Gaps
- **14 isolated node(s):** `./.svelte-kit/tsconfig.json`, `$lib/registry/blocks/navigation/components/site.context.svelte`, `RFC-3966`, `RFC-4627`, `RFC-5322` (+9 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2843 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Flavor` connect `Community 5` to `Community 0`, `Community 1`, `Community 3`, `Community 6`, `Community 7`, `Community 9`, `Community 12`, `Community 14`, `Community 143`, `Community 144`, `Community 19`, `Community 148`, `Community 21`, `Community 26`, `Community 29`, `Community 160`, `Community 33`, `Community 34`, `Community 35`, `Community 40`, `Community 41`, `Community 42`, `Community 43`, `Community 44`, `Community 46`, `Community 177`, `Community 49`, `Community 51`, `Community 52`, `Community 53`, `Community 181`, `Community 58`, `Community 59`, `Community 60`, `Community 62`, `Community 190`, `Community 66`, `Community 67`, `Community 197`, `Community 70`, `Community 74`, `Community 79`, `Community 208`, `Community 209`, `Community 82`, `Community 80`, `Community 88`, `Community 89`, `Community 90`, `Community 94`, `Community 97`, `Community 100`, `Community 102`, `Community 105`, `Community 106`, `Community 110`, `Community 114`, `Community 118`, `Community 121`, `Community 122`, `Community 123`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 254 inferred relationships involving `Flavor` (e.g. with `DemoState` and `drift()`) actually correct?**
  _`Flavor` has 254 INFERRED edges - model-reasoned connections that need verification._
- **What connects `./.svelte-kit/tsconfig.json`, `$lib/registry/blocks/navigation/components/site.context.svelte`, `RFC-3966` to the rest of the system?**
  _14 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.03399558498896247 - nodes in this community are weakly interconnected._
- **Why does `Track` connect `Community 7` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 14`, `Community 21`, `Community 24`, `Community 26`, `Community 27`, `Community 156`, `Community 28`, `Community 33`, `Community 34`, `Community 35`, `Community 165`, `Community 40`, `Community 43`, `Community 44`, `Community 52`, `Community 181`, `Community 59`, `Community 60`, `Community 62`, `Community 67`, `Community 70`, `Community 71`, `Community 74`, `Community 75`, `Community 78`, `Community 79`, `Community 80`, `Community 82`, `Community 89`, `Community 93`, `Community 100`, `Community 102`, `Community 106`, `Community 113`, `Community 114`, `Community 118`, `Community 121`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 140 inferred relationships involving `Track` (e.g. with `save_cycle_inputs()` and `StormState`) actually correct?**
  _`Track` has 140 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.030174291938997823 - nodes in this community are weakly interconnected._