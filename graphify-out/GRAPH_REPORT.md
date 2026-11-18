# Graph Report - anemoi  (2026-11-18)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 7073 nodes · 18200 edges · 263 communities (236 shown, 27 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 2666 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b5eb2081`
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
- Community 197
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
- Community 231
- Community 232
- Community 233
- Community 234
- Community 235
- Community 236
- Community 237
- Community 238
- Community 240
- Community 241
- Community 242
- Community 243
- Community 244
- Community 245
- Community 246
- Community 247
- Community 248
- Community 249
- Community 250
- Community 251
- Community 252
- Community 253
- Community 254
- Community 255
- Community 256
- Community 257
- Community 258
- Community 259
- Community 260
- Community 261
- Community 262

## God Nodes (most connected - your core abstractions)
1. `Flavor` - 296 edges
2. `Track` - 205 edges
3. `Fix` - 155 edges
4. `ModelRegistry` - 137 edges
5. `CheckpointStore` - 136 edges
6. `TrackQuality` - 112 edges
7. `require_torch()` - 101 edges
8. `MetricSet` - 81 edges
9. `FetchTask` - 71 edges
10. `LatencyOracle` - 68 edges

## Surprising Connections (you probably didn't know these)
- `test_internal_calibration_audit_route_reports_new_samples()` --uses--> `RealState`  [INFERRED]
  tests/test_api_real_state.py → src/anemoi/api/real_state.py
- `test_trained_basins_without_champions_is_the_atlantic()` --uses--> `ModelRegistry`  [INFERRED]
  tests/test_registry.py → src/anemoi/tracking/registry.py
- `test_the_prior_is_stage_b_only()` --uses--> `Flavor`  [INFERRED]
  tests/test_track_prior.py → src/anemoi/data/sources.py
- `test_cache_round_trip_and_vector()` --uses--> `FetchTask`  [INFERRED]
  tests/test_steering.py → src/anemoi/data/gridded_cache.py
- `test_the_gnn_is_fed_the_real_lattice()` --calls--> `describe()`  [INFERRED]
  tests/test_model_architecture.py → src/anemoi/models/architecture.py

## Import Cycles
- None detected.

## Communities (263 total, 27 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (80): cmd_ablation(), cmd_adeck_fetch(), cmd_atcf_archive(), cmd_cache_localize(), cmd_consistency_distill(), cmd_drift_reference_fit(), cmd_era5_cache(), cmd_gdas_cache() (+72 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (50): _loadable(), gfs_track_meta(), require_meta(), steering_meta(), basin_one_hot(), with_basin_channels(), with_basin_columns(), with_basin_vector() (+42 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (72): extra_input_conv(), __init__(), extra_input_linear(), __init__(), ModelSpec, require_torch(), torch_available(), build_cnn() (+64 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (96): ApiError, apiFetch(), getActivePin(), getArchitecture(), getCalibration(), getDrift(), getDriftAll(), getModelRegistry() (+88 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (52): apply_cold_wake(), area_mean(), assert_flavor(), cold_wake_sst_depression_c(), compare_potential_intensity_estimates(), compute_environment_features(), deep_layer_shear(), emanuel_potential_intensity() (+44 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (38): pair_by_valid_time(), storm_basin(), basins_of(), select_basins(), augment_track(), emulate_working_track(), recalibrate_from_pairs(), Track (+30 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (46): Flavor, assert_deployable(), Curriculum, CurriculumError, stage_a(), stage_b(), StageResult, _fake_curriculum_run() (+38 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (42): physics_residuals(), build_stage_samples(), displacements_to_absolute(), displacements_to_latlon(), iter_stage_windows(), build_pinn_samples(), _candidate_and_true_absolute(), _disp_to_abs_batch() (+34 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (53): archive_key(), ArchiveClient, build_fetch_tasks(), cache_path(), _decode_cached_fields(), FetchCacheReport, FetchTask, filter_tracks_by_min_valid_time() (+45 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (46): guards, handle, Props, Section, SectionPage, { sections }, height, motionClass (+38 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (34): train_cnn_stage_streaming(), train_gnn_stage_streaming(), forward_batch(), StageWindow, train_lstm_stage_streaming(), train_transformer_stage_streaming(), filter_windows_with_cache(), filter_windows_with_finite_fields() (+26 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (75): dependencies, arktype@^2.2.7, @better-auth/passkey@^1.7.7, bits-ui@^2.20.6, clsx@^2.1.1, d3-polygon@^3.0.1, d3-scale@^4.0.2, @internationalized/date@^3.12.4 (+67 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (43): @lucide/svelte@^1.71.0, sveltekit-superforms@^2.31.0, authClient, { form }, Props, { form }, Props, errorMsg (+35 more)

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (8): cycle_payload_out(), cycle_result_out(), RealState, deterministic(), ensemble(), live_fields(), RealStormState, CycleOutput

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (40): Fix, gfs_track_meta_digest(), steering_meta_digest(), _build_live_x(), build_live_cnn_x(), build_live_gnn_x(), build_live_lstm_x(), build_live_pinn_x() (+32 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (42): _model_versions(), _baseline_inputs(), _empty_report(), _fake_checkpoint_store(), _hurdat2_storm(), make_args(), make_track(), _retrain_check_args() (+34 more)

### Community 16 - "Community 16"
Cohesion: 0.04
Nodes (52): bounds, colors, coneFeatures, coneHull, currentFix, forecastLine, forecastPoints, geoCircle() (+44 more)

### Community 17 - "Community 17"
Cohesion: 0.05
Nodes (34): _crop_variable(), fetch_real_satellite_crop(), _find_real_scan(), GoesFetchError, _lazy_open(), _list_scan_keys(), _nearest_scan_key(), _parse_scan_start() (+26 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (40): build_cone(), build_products(), climatological_cone_nm(), cone_radius_from_spread(), ConeSegment, deterministic_center(), EnsembleMember, ForecastProducts (+32 more)

### Community 19 - "Community 19"
Cohesion: 0.04
Nodes (49): layerchart@^2.5.1, getModels(), IntensityPercentiles, ModelCatalog, TrackPointOut, BY_ARCHITECTURE, BY_SLUG, colorFor() (+41 more)

### Community 20 - "Community 20"
Cohesion: 0.04
Nodes (54): svelte-sonner@^1.2.3, getCycle(), getStorm(), runCycle(), { flags, notes = [] }, Props, recall(), remember() (+46 more)

### Community 21 - "Community 21"
Cohesion: 0.08
Nodes (37): case_errors(), compared_members(), homogeneous_mask(), _limiting(), _mean(), Member, MemberScore, _paired() (+29 more)

### Community 22 - "Community 22"
Cohesion: 0.05
Nodes (37): cycle_products_out(), god_out(), model_catalog(), model_version_out(), skew_report_out(), health(), models(), get_active_pin() (+29 more)

### Community 23 - "Community 23"
Cohesion: 0.06
Nodes (15): get_state(), require_api_key(), state_dependency(), get_custom_redoc_html(), create_app(), _debug_last_deterministic_error(), redoc_html(), _lifespan() (+7 more)

### Community 24 - "Community 24"
Cohesion: 0.06
Nodes (30): check_run(), CycleConflict, _existing_source(), InFlight, operator_ids(), RunRequest, stored_source(), RunInfo (+22 more)

### Community 25 - "Community 25"
Cohesion: 0.05
Nodes (29): client(), _FakeCycleOutput, _fresh_real_state(), hurdat2_file(), _make_deterministic_forecast(), _make_storm_state(), _memory_store(), _MemoryS3Client (+21 more)

### Community 26 - "Community 26"
Cohesion: 0.08
Nodes (31): build_kwargs(), basin_inputs(), steering_inputs(), _builder(), _run_pinn(), _decode_arch_params(), _download_state_dict(), _build_joint_latent() (+23 more)

### Community 27 - "Community 27"
Cohesion: 0.08
Nodes (30): invalidated_by(), evaluate_all(), expand_jobs(), nightly_latent(), on_data_volume(), on_drift(), on_latent_desync(), on_skew() (+22 more)

### Community 28 - "Community 28"
Cohesion: 0.07
Nodes (30): cache_nwp_lead_hours(), CacheLeadMismatch, _claim_cache_dir(), _default_fetch_fn(), fetch_one(), run_fetch_cache(), gfs_url(), make_fields() (+22 more)

### Community 29 - "Community 29"
Cohesion: 0.06
Nodes (44): SourceOut, byUse(), hasUnknownEntry(), MODEL_NAMES, MODELS, ORDER, readersOf(), SOURCE_NAMES (+36 more)

### Community 30 - "Community 30"
Cohesion: 0.07
Nodes (27): RegistryError, _FakeS3Config, full_set(), register_group1(), _stage_all(), test_checkpoint_store_push_failure_degrades_to_local_only(), test_checkpoint_store_push_mirrors_registry_json_after_every_save(), test_checkpoint_uri_defaults_to_none_when_not_given() (+19 more)

### Community 31 - "Community 31"
Cohesion: 0.07
Nodes (22): absolute_pairs(), per_basin_scores(), LeadCalibration, ForecastPoint, LeadTimeStats, _normal_cdf(), to_metric_dict(), VerificationPair (+14 more)

### Community 32 - "Community 32"
Cohesion: 0.07
Nodes (24): latent_signature(), format_report(), recommend_extra_conditioning(), run_spread_backtest(), SpreadBacktestError, SpreadBacktestReport, test_signature_changes_when_any_group1_version_changes(), _fake_val() (+16 more)

### Community 33 - "Community 33"
Cohesion: 0.07
Nodes (20): AvailabilityOracle, CycleInputs, earliest_ready_time(), InputStatus, resolve_cycle_inputs(), _valid_time_for(), NWPCycleSelection, test_all_nwp_missing_marks_the_required_input_unavailable() (+12 more)

### Community 34 - "Community 34"
Cohesion: 0.08
Nodes (21): cmd_train(), arch_params_tag(), baseline_beaten(), basin_input_tags(), build_run_tags(), candidate_tags(), _git_commit(), _gpu_type() (+13 more)

### Community 35 - "Community 35"
Cohesion: 0.07
Nodes (28): fetch(), _crop_box(), era5_to_gridded_fields(), crop(), crop_levels(), gdas_to_gridded_fields(), crop(), _saturation_vapor_pressure_hpa_array() (+20 more)

### Community 36 - "Community 36"
Cohesion: 0.09
Nodes (27): scored(), basin_tags(), validation_metrics(), by_basin(), complete_run(), _forecasts(), metric_set(), test_a_basin_is_verified_when_the_model_beats_persistence_there() (+19 more)

### Community 37 - "Community 37"
Cohesion: 0.09
Nodes (25): load_cycle_result(), _synthetic_fallback_deterministic(), audit_due(), audit_storm(), _audited_key(), calibrate_products(), CalibrationSample, LeadProductCalibration (+17 more)

### Community 38 - "Community 38"
Cohesion: 0.07
Nodes (26): brier_score(), crps_ensemble(), _crps_rows(), crps_series(), ensemble_percentiles(), rank_histogram(), reliability(), spread_skill() (+18 more)

### Community 39 - "Community 39"
Cohesion: 0.12
Nodes (26): climatological_ensemble(), run_cycle(), deterministic_fn(), good_ensemble(), make_fix(), test_a_pacific_climatological_ensemble_is_drawn_from_pacific_radii(), test_absent_opportunistic_feeds_do_not_flag_the_cycle(), test_an_eastern_pacific_cycle_falls_back_to_nhcs_pacific_radii() (+18 more)

### Community 40 - "Community 40"
Cohesion: 0.08
Nodes (25): build_lstm(), encode(), forward(), __init__(), candidate_model(), _fake_checkpoint_store(), FakeS3Client, make_track() (+17 more)

### Community 41 - "Community 41"
Cohesion: 0.10
Nodes (26): ExecutionMode, Task, fake_load_run_artifacts(), _FakeJointLatents, _register_group1_versions(), runner(), fake_extract_joint_latents(), make_fake() (+18 more)

### Community 42 - "Community 42"
Cohesion: 0.08
Nodes (23): advisory_time(), floor_synoptic(), is_synoptic(), next_synoptic(), NWPUnavailableError, require_synoptic(), _require_utc(), select_nwp_cycle() (+15 more)

### Community 43 - "Community 43"
Cohesion: 0.09
Nodes (24): audit_one(), audit_run(), _AuditPlan, _fix_from_dict(), _fix_to_dict(), list_operational_records(), _load_audited_cycles(), load_skew_samples() (+16 more)

### Community 44 - "Community 44"
Cohesion: 0.08
Nodes (21): config_copy(), edit(), _cron_run_offset_minutes(), _image_layout(), _leaves(), _load(), _run(), test_a_config_change_redeploys_the_api() (+13 more)

### Community 45 - "Community 45"
Cohesion: 0.09
Nodes (22): cycle_key(), save_cycle_result(), CycleResult, audit_cycle(), _CountingClient, _FakeClient, _fix(), _result() (+14 more)

### Community 46 - "Community 46"
Cohesion: 0.10
Nodes (25): build_gnn(), encode(), forward(), build_gnn_samples(), build_mesh_topology(), GnnStageSamples, cache_all_fixes(), _FakeS3Client (+17 more)

### Community 47 - "Community 47"
Cohesion: 0.07
Nodes (16): App, Locals, Platform, clearPreferenceStorage(), consent, CONSENT_KEY, ConsentCategory, ConsentChoice (+8 more)

### Community 48 - "Community 48"
Cohesion: 0.09
Nodes (26): _check_basin(), expected_coordinates(), write_stage_runs(), _decode(), files(), local(), _ohc(), _row_col() (+18 more)

### Community 49 - "Community 49"
Cohesion: 0.08
Nodes (26): bearing_deg(), bearings_deg(), cross_along_track_nm(), cross_along_track_nms(), km_to_nm(), nm_to_km(), offset_positions(), wrap_longitude() (+18 more)

### Community 50 - "Community 50"
Cohesion: 0.10
Nodes (20): _box_mean(), cached_track(), _centroid(), fetch_lead_field(), GfsTrackCacheReport, lead_field(), LeadField, load_track() (+12 more)

### Community 51 - "Community 51"
Cohesion: 0.10
Nodes (28): deterministic(), cmd_cycle(), deterministic(), LatencyOracle, CycleAbandoned, plan_cycle(), total_budget(), test_a_cycle_started_at_the_timeout_still_clears_the_margin() (+20 more)

### Community 52 - "Community 52"
Cohesion: 0.09
Nodes (19): DriftError, ReferenceDistribution, load_reference(), reference_from_json(), reference_to_json(), save_reference(), test_drift_report_detects_real_drift_once_enough_samples_are_collected(), test_drift_report_is_honest_zero_for_a_model_that_never_contributed() (+11 more)

### Community 53 - "Community 53"
Cohesion: 0.10
Nodes (10): cycle_plan_out(), schedule(), CyclePlan, derive_vitals_timeout(), plan_day(), _schedule_stages(), ScheduledStage, Stage (+2 more)

### Community 54 - "Community 54"
Cohesion: 0.10
Nodes (20): disc_mean(), fetch_lead_flow(), group_by_time(), lead_flow(), LeadFlow, load_steering(), require_meta(), run_steering_cache() (+12 more)

### Community 55 - "Community 55"
Cohesion: 0.09
Nodes (16): _created_date(), creation_day(), _declared_length(), decode_ohc(), detect_format(), fetch_ohc_file(), _grid_values(), name_day_for_creation() (+8 more)

### Community 56 - "Community 56"
Cohesion: 0.10
Nodes (16): DeterministicForecast, build_real_ensemble_fn(), cycle_sample_seed(), InferenceEnsembleError, cache_current_fix(), _FakeS3Client, make_track(), _register() (+8 more)

### Community 57 - "Community 57"
Cohesion: 0.08
Nodes (13): ModelRegistry, _champions(), test_a_basin_is_served_once_every_champion_is_verified_in_it(), test_a_champion_verified_nowhere_serves_no_basin_as_in_distribution(), test_no_champion_or_champions_from_before_the_tag_are_the_atlantic(), test_data_volume_counts_seasons_newer_than_any_model_trained_on(), track(), _champions_tagged() (+5 more)

### Community 58 - "Community 58"
Cohesion: 0.11
Nodes (17): ModelVersion, Stage, _reconcile_args(), test_registry_reconcile_dry_run_reports_without_transitioning(), test_registry_reconcile_ignores_nan_metrics(), test_registry_reconcile_never_stages_a_version_trained_on_the_adecks(), test_registry_reconcile_never_touches_a_model_with_a_production_version(), test_registry_reconcile_re_stages_the_real_best_existing_version() (+9 more)

### Community 59 - "Community 59"
Cohesion: 0.08
Nodes (32): ArchitectureOut, LayerOut, {
		arch,
		onclose,
		class: className = ''
	}, Box, boxFor(), clamp(), color, focus (+24 more)

### Community 60 - "Community 60"
Cohesion: 0.12
Nodes (20): _bytemap_path(), decode_ssmis_bytemap(), fetch_and_decode_ssmis_daily(), fetch_ssmis_daily_bytemap(), MicrowaveFetchError, RSSFtpCredentials, SSMISDaily, _make_bytemap() (+12 more)

### Community 61 - "Community 61"
Cohesion: 0.09
Nodes (15): era5_deps_available(), fetch_era5t_one(), fetch_gdas_grib2_fields(), fetch_grib2_messages(), gridded_deps_available(), open_era5(), open_era5_store(), _parse_grib2_index() (+7 more)

### Community 62 - "Community 62"
Cohesion: 0.10
Nodes (23): cycle_date(), ohc_global(), ohc_url(), select_file(), sshae_baseline(), target_creation_day(), _full_archive(), test_a_blank_run_longer_than_the_window_leaves_na_unavailable() (+15 more)

### Community 63 - "Community 63"
Cohesion: 0.12
Nodes (19): build_cnn_samples(), CnnStageSamples, cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_a_basin_with_no_cached_fields_was_not_trained_on() (+11 more)

### Community 64 - "Community 64"
Cohesion: 0.06
Nodes (35): context, dockerfile, postgres, AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY, MLFLOW_S3_ENDPOINT_URL, POSTGRES_DB (+27 more)

### Community 65 - "Community 65"
Cohesion: 0.10
Nodes (19): _decode_one_sonde(), DropsondeFetchError, DropsondeProfile, fetch_and_parse_dropsonde_mission(), fetch_dropsonde_mission_tarball(), _ftp_connect(), list_dropsonde_missions(), _mask_missing() (+11 more)

### Community 66 - "Community 66"
Cohesion: 0.12
Nodes (27): assert_input_safe(), emulate_working_fix(), TrackQuality, _latlon(), make_fix(), make_track(), test_assert_input_safe_allows_working_quality(), test_assert_input_safe_blocks_final_quality() (+19 more)

### Community 67 - "Community 67"
Cohesion: 0.10
Nodes (18): ArmResult, compare(), expand_patch_channels(), _renamed(), run_steering_spike(), track_errors_nm(), cache_all_fixes(), _cache_steering() (+10 more)

### Community 68 - "Community 68"
Cohesion: 0.10
Nodes (12): basin_key(), basin_value(), is_basin_key(), key_basin(), sample_counts(), scored_basins(), trained_basins(), verified_basins() (+4 more)

### Community 69 - "Community 69"
Cohesion: 0.11
Nodes (21): Hurdat2Error, _parse_data_row(), _parse_header(), parse_hurdat2(), parse_hurdat2_statuses(), _parse_latlon(), _storm_rows(), test_entry_count_mismatch_raises() (+13 more)

### Community 70 - "Community 70"
Cohesion: 0.11
Nodes (20): fetch_current_storm_ids(), fetch_current_storms(), fetch_live_track(), fetch_live_tracks(), fetch_one(), _get(), LiveAtcfError, test_fetch_current_storm_ids_parses_and_uppercases() (+12 more)

### Community 71 - "Community 71"
Cohesion: 0.09
Nodes (21): get(), Role, used_by(), _model_sources(), test_a_label_or_verification_source_is_never_a_model_input(), test_a_model_input_is_never_a_labels_only_source(), test_a_verification_source_not_read_yet_is_verification_and_nothing_else(), test_each_curriculum_stage_lists_what_its_models_read() (+13 more)

### Community 72 - "Community 72"
Cohesion: 0.14
Nodes (22): CurriculumRun, OrchestrationError, MetricSet, PromotionDecision, RealOrchestratorRunner, _run_cnn(), _run_diffusion(), _run_fusion() (+14 more)

### Community 73 - "Community 73"
Cohesion: 0.09
Nodes (18): QUICK, API, DEVELOP, PHONE, SourceRow, SOURCES, SOURCES_BEFORE_USED_BY, SOURCES_REWIRED (+10 more)

### Community 74 - "Community 74"
Cohesion: 0.06
Nodes (28): AsyncReturnType, Expand, ExtractGenericViewableContent, GenericItem, GenericSelectorOption, GenericSnippetProps, GenericViewableContent, InheritedSnippetProps (+20 more)

### Community 75 - "Community 75"
Cohesion: 0.09
Nodes (14): fusion_weights(), _build_live_context(), deterministic_fn(), _compute_env_features(), _item_stat(), _live_steering_for(), _real_fusion_forecast(), _run_group1_model() (+6 more)

### Community 76 - "Community 76"
Cohesion: 0.06
Nodes (31): data, basins, stage_a, epochs, flavor, input_sources, label_source, learning_rate (+23 more)

### Community 77 - "Community 77"
Cohesion: 0.07
Nodes (31): better-auth@^1.7.7, @better-auth/api-key@^1.7.7, @types/node@^26.6.4, typescript@^5.9.3, wrangler@^4.147.0, better-auth, @better-auth/api-key, @types/node (+23 more)

### Community 78 - "Community 78"
Cohesion: 0.14
Nodes (20): evaluate_promotion(), PromotionError, Threshold, _thresholds(), complete_run(), good_metrics(), test_beat_rate_threshold_is_higher_is_better(), test_budget_exhaustion_raises() (+12 more)

### Community 79 - "Community 79"
Cohesion: 0.14
Nodes (15): build_real_deterministic_fn(), InferenceCycleError, cache_current_fix(), _FakeS3Client, make_track(), _register_real_version(), _store(), test_build_real_deterministic_fn_combines_all_four_real_models() (+7 more)

### Community 80 - "Community 80"
Cohesion: 0.10
Nodes (23): _builders(), cache_steering(), _fields(), _forward(), make_track(), test_a_zero_steering_path_computes_the_plain_model(), test_gridded_inputs_append_steering_after_the_basin_inputs(), test_latents_need_a_steering_cache_for_a_model_that_reads_steering() (+15 more)

### Community 81 - "Community 81"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, env, GH_TOKEN, GRAPHIFY_VERSION, permissions, runs-on (+22 more)

### Community 82 - "Community 82"
Cohesion: 0.12
Nodes (16): list_cycle_labels(), load_drift_live(), save_drift_live(), archive_atcf(), archived_bdeck_tracks(), archived_tcvitals(), ArchiveReport, _bdeck_name() (+8 more)

### Community 83 - "Community 83"
Cohesion: 0.12
Nodes (18): cmd_baseline_backtest(), _aligned(), assemble_validation_forecasts(), BaselineBacktestError, format_forecast_check(), group1_versions_of(), model_members(), ValidationForecasts (+10 more)

### Community 84 - "Community 84"
Cohesion: 0.16
Nodes (24): cmd_train_schedule(), build_schedule(), Mode, run_schedule(), RunOutcome, failing_runner(), runner(), ok_runner() (+16 more)

### Community 85 - "Community 85"
Cohesion: 0.12
Nodes (13): Fetcher, FetchError, ingest_cycle_inputs(), ingest_one(), IngestionOutcome, IngestionRecord, LakeTier, LakeWriter (+5 more)

### Community 86 - "Community 86"
Cohesion: 0.11
Nodes (13): DiffusionArtifacts, _standardize(), _standardize_y(), train_diffusion_stage(), _FakeS3Client, _make_samples(), test_a_longer_epoch_budget_never_returns_a_worse_val_loss(), test_early_stopping_halts_before_the_epoch_cap_on_a_real_overfitting_run() (+5 more)

### Community 87 - "Community 87"
Cohesion: 0.08
Nodes (15): _expected_meta(), test_a_failed_time_is_reported_and_the_others_still_written(), fetch(), test_a_lost_race_with_no_file_appearing_raises_the_write_error(), test_cache_round_trip_and_vector(), test_disc_mean_is_symmetric_for_a_field_linear_in_longitude(), test_features_advect_with_the_flow_plus_beta_drift(), test_features_raise_where_there_is_no_flow() (+7 more)

### Community 88 - "Community 88"
Cohesion: 0.07
Nodes (23): rehype-slug@^6.0.0, rehype-stringify@^10.0.1, remark-gfm@^4.0.1, remark-parse@^11.0.0, remark-rehype@^11.1.2, unified@^11.0.5, unist-util-visit@^5.1.0, CONSOLE_ROOT (+15 more)

### Community 89 - "Community 89"
Cohesion: 0.07
Nodes (29): WithElementRef, ButtonClickEvent, PrimitiveAnchorAttributes, PrimitiveButtonAttributes, PrimitiveCanvasAttributes, PrimitiveDivAttributes, PrimitiveElementAttributes, PrimitiveFigureAttributes (+21 more)

### Community 90 - "Community 90"
Cohesion: 0.13
Nodes (15): build_transformer_samples(), TransformerStageSamples, cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_build_transformer_samples_empty_when_nothing_cached() (+7 more)

### Community 91 - "Community 91"
Cohesion: 0.10
Nodes (17): adeck_text(), adecks(), archive(), archive_text(), cases(), _gfs_track_cache(), _row(), _row_of() (+9 more)

### Community 92 - "Community 92"
Cohesion: 0.11
Nodes (23): field_with(), _moving(), test_a_cycle_whose_fields_cannot_be_fetched_is_reported_not_cached(), test_a_moving_vortex_is_followed_through_every_lead(), test_a_storm_that_stalls_is_still_found(), test_a_working_fix_seeds_the_same_track_as_the_best_track_fix(), test_locate_finds_the_centre_between_grid_points(), test_locate_is_none_in_a_resting_field_and_outside_the_radius() (+15 more)

### Community 93 - "Community 93"
Cohesion: 0.07
Nodes (28): inputArgs, jobs, projectId, region, results, timeoutSeconds, assign, return (+20 more)

### Community 94 - "Community 94"
Cohesion: 0.16
Nodes (15): audit_due(), SkewMonitor, SkewReport, sample(), test_audit_becomes_due_once_era5t_lands(), test_audit_is_not_due_immediately_after_the_cycle(), test_intensity_delta_is_signed_toward_the_operational_run(), test_intensity_skew_alone_can_raise_an_alert() (+7 more)

### Community 95 - "Community 95"
Cohesion: 0.11
Nodes (16): adeck_urls(), AdeckFetchReport, _check_adeck(), _check_official_errors(), fetch_adecks(), _fetch_one(), _get(), _get_bytes() (+8 more)

### Community 96 - "Community 96"
Cohesion: 0.13
Nodes (17): calibrate(), forecast_motion_bearings(), observed_motion_bearings(), recurving_cases(), _scalar_errors(), _centre(), _jitter(), _synthetic() (+9 more)

### Community 97 - "Community 97"
Cohesion: 0.15
Nodes (17): AblationReport, build_samples(), _cell(), make_track(), test_at_fraction_filters_and_sorts_by_hidden_dim(), test_build_samples_augmentation_multiplies_sample_count(), test_build_samples_shapes_match_sequence_length_and_columns(), test_build_samples_skips_storms_shorter_than_required() (+9 more)

### Community 98 - "Community 98"
Cohesion: 0.11
Nodes (13): _budget_entries(), spend_test_set_budget(), season_keys(), TestSetBudget, _FakeStore, test_a_legacy_single_file_ledger_still_counts(), test_an_earlier_key_landing_late_cannot_take_a_slot_already_spent(), early_key() (+5 more)

### Community 99 - "Community 99"
Cohesion: 0.10
Nodes (12): color_for(), experiment_name(), god(), Module, test_every_god_color_is_distinct(), test_experiment_name_handles_fusion_without_raising(), test_experiment_names_are_the_god_slugs(), test_lookup_by_slug_and_by_architecture_agree() (+4 more)

### Community 100 - "Community 100"
Cohesion: 0.11
Nodes (10): JointLatentBundle, FusionArtifacts, run_fusion_curriculum(), train_fusion_stage(), _FakeS3Client, _make_samples(), test_run_fusion_curriculum_uploads_a_checkpoint_and_registers_stage_b(), test_train_fusion_stage_reduces_loss_and_produces_val_metrics() (+2 more)

### Community 101 - "Community 101"
Cohesion: 0.13
Nodes (10): svelte-guard@^1.1.1, @sveltejs/kit@^2.70.3, DEFAULT_AFTER_LOGIN, loginHref(), safeNext(), requireSignIn(), requireSignInLoad(), guard() (+2 more)

### Community 102 - "Community 102"
Cohesion: 0.12
Nodes (13): initial_fix(), client(), _MemoryS3, s3(), test_an_archive_storm_says_its_fix_is_the_final_best_track(), test_an_archived_storms_fix_is_labelled_as_its_bdeck(), test_missing_vitals_are_extrapolated_and_estimated(), test_one_earlier_fix_is_persisted() (+5 more)

### Community 103 - "Community 103"
Cohesion: 0.10
Nodes (16): http_get(), OhcFetchError, OhcNotPublished, OhcUnavailable, Archive, test_a_cut_off_reply_is_a_fetch_failure(), test_a_cut_off_transfer_raises_rather_than_reading_an_older_file(), test_a_fetch_failure_that_is_not_a_404_is_not_stepped_over() (+8 more)

### Community 104 - "Community 104"
Cohesion: 0.13
Nodes (15): _all_tensors(), Architecture, _builder(), describe(), describe_cached(), _describe_cached(), hook(), _example_inputs() (+7 more)

### Community 105 - "Community 105"
Cohesion: 0.14
Nodes (14): accessed(), _check_type(), config_dir(), ConfigError, fixed(), get(), get_list(), _load() (+6 more)

### Community 106 - "Community 106"
Cohesion: 0.10
Nodes (8): build_derived_schedule(), _latent_task(), ResourceProfile, Schedule, _train_task(), validate_schedule(), Wave, test_derived_schedule_retrains_no_group1_model()

### Community 107 - "Community 107"
Cohesion: 0.13
Nodes (18): _bdeck_line(), _fetcher(), fetch(), _keys(), test_a_storm_is_still_archived_for_a_few_days_after_it_leaves_the_index(), test_a_storm_seen_on_new_years_eve_is_still_followed_on_new_years_day(), test_an_unreachable_index_raises_so_the_caller_reports_it(), test_archived_bdeck_tracks_keep_a_storms_january_fixes() (+10 more)

### Community 108 - "Community 108"
Cohesion: 0.10
Nodes (13): season_boundaries(), test_an_archive_that_cannot_be_downloaded_leaves_the_file_as_it_was(), test_an_unreadable_listing_falls_back_to_the_pinned_file_and_says_so(), fetch(), test_boundaries_move_with_the_archive(), test_no_file_at_all_raises(), test_stage_bs_validation_season_is_never_seen_by_stage_a(), test_the_archive_a_run_was_given_is_not_what_it_trained_on() (+5 more)

### Community 109 - "Community 109"
Cohesion: 0.11
Nodes (3): cache_all_fixes(), make_fields(), _task_for()

### Community 110 - "Community 110"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GH_TOKEN, IMPORTED_FROM, SOURCE_SHA, jobs, publish (+16 more)

### Community 111 - "Community 111"
Cohesion: 0.14
Nodes (14): fetch_and_parse_ndbc(), fetch_ndbc_realtime2(), _get(), NdbcFetchError, NdbcObservation, parse_ndbc_realtime2(), test_a_row_with_the_wrong_column_count_is_skipped_not_fatal(), test_a_station_missing_wave_columns_still_parses() (+6 more)

### Community 112 - "Community 112"
Cohesion: 0.08
Nodes (3): client(), test_more_members_than_the_ensemble_runs_is_refused_not_silently_capped(), test_sources_say_who_uses_each_one()

### Community 113 - "Community 113"
Cohesion: 0.16
Nodes (8): freeCycleLabel(), label(), runFreshCycle(), signIn(), cases, Storm, @playwright/test@^1.63.0, @playwright/test

### Community 114 - "Community 114"
Cohesion: 0.08
Nodes (8): DELETE, GET, PATCH, POST, PUT, { data }, prerender, ssr

### Community 115 - "Community 115"
Cohesion: 0.13
Nodes (14): Archive, archives_for(), describe(), fetch_latest_hurdat2(), last_season(), latest_name(), manifest_path(), test_a_listing_without_one_archive_falls_back_for_that_archive_only() (+6 more)

### Community 116 - "Community 116"
Cohesion: 0.13
Nodes (11): read_cached_official_errors(), OfficialErrors, OfficialErrorsError, parse_official_errors(), _signed(), test_a_cached_error_file_that_is_not_nhcs_is_named_with_the_way_out(), test_parse_official_errors_reads_columns_by_name_and_skips_missing_leads(), test_parse_official_errors_reads_the_stated_initial_position_domain() (+3 more)

### Community 117 - "Community 117"
Cohesion: 0.16
Nodes (12): record_operational_cycle(), record_to_json(), _FakeClient, _fix(), _make_output(), _record(), test_audit_run_degrades_per_record_when_audit_one_raises(), test_audit_run_takes_a_bounded_batch_oldest_first() (+4 more)

### Community 118 - "Community 118"
Cohesion: 0.13
Nodes (18): CYCLE_STEP, cycleInstanceId(), CycleParams, CycleWorkflow, LIGHT_STEP, runStormCycle(), SKEW_STEP, StormSummaryOut (+10 more)

### Community 119 - "Community 119"
Cohesion: 0.13
Nodes (10): _download(), fetch_oisst_sst(), require_sst_deps(), sst_at(), SstFetchError, _small_grid(), test_fetch_oisst_sst_reads_real_recent_data(), test_sst_at_finds_the_nearest_cell() (+2 more)

### Community 120 - "Community 120"
Cohesion: 0.16
Nodes (16): _default_fetch_fn(), run_fetch_cache(), make_fields(), make_track(), test_build_fetch_tasks_covers_every_fix_across_tracks(), test_load_cached_fields_rejects_a_missing_file(), test_run_fetch_cache_actually_runs_fetches_concurrently(), slow_fetch() (+8 more)

### Community 121 - "Community 121"
Cohesion: 0.14
Nodes (13): _notes(), persistence_members(), RegisteredError, _registry_sample(), run_baseline_backtest(), _sample_gap(), technique_diagnostics(), ValidationCases (+5 more)

### Community 122 - "Community 122"
Cohesion: 0.15
Nodes (12): _cache(), _persistence(), _positions(), test_a_lead_gfs_has_lost_the_storm_by_falls_back_to_persistence(), test_latents_refuse_an_adeck_prior_and_need_the_cache(), test_live_prior_is_the_training_prior_and_is_cached(), test_no_prior_without_a_position_at_the_cycle_or_the_first_lead(), test_prior_is_the_displacement_to_where_gfs_has_the_storm() (+4 more)

### Community 123 - "Community 123"
Cohesion: 0.13
Nodes (7): mlflow_client_from_env(), test_an_unreachable_server_is_skipped_fast(), test_builds_a_real_client_when_tracking_uri_is_set(), test_fail_fast_settings_never_override_explicit_ones(), test_mlflow_client_from_env_can_actually_reach_the_configured_server(), test_returns_none_when_tracking_uri_is_unset(), test_returns_none_without_mlflow_installed()

### Community 124 - "Community 124"
Cohesion: 0.14
Nodes (11): _files(), localize_cache(), LocalizeReport, _raise(), _cache(), test_a_directory_that_cant_be_listed_fails_the_copy(), test_a_missing_source_raises(), test_a_rerun_only_fills_gaps() (+3 more)

### Community 125 - "Community 125"
Cohesion: 0.21
Nodes (15): storm_relative_sequence(), test_track_48h_threshold_is_rebaselined_against_the_gpra_record(), test_extract_joint_latents_rejects_missing_group1_model(), test_displacement_to_latlon_round_trips_with_displacement_nm(), make_fix(), test_displacement_direction_matches_bearing(), test_displacement_magnitude_matches_haversine_distance(), test_displacement_nm_matches_storm_relative_sequence() (+7 more)

### Community 126 - "Community 126"
Cohesion: 0.15
Nodes (13): _fields(), _MemoryS3, _run(), test_a_missing_t_minus_6_cycle_falls_back_to_t_minus_12(), fetch_one(), test_live_fields_come_from_the_t_minus_6_forecast(), fetch_one(), test_no_nwp_at_all_is_flagged() (+5 more)

### Community 127 - "Community 127"
Cohesion: 0.18
Nodes (17): CacheTarget, cacheTargetFor(), cycleKey(), EntryMeta, jsonResponse(), put(), putCycleResult(), readThrough() (+9 more)

### Community 128 - "Community 128"
Cohesion: 0.10
Nodes (20): PROJECT_NUMBER, PROJECT_PAT, types, jobs, sync, name, on, issues (+12 more)

### Community 129 - "Community 129"
Cohesion: 0.13
Nodes (9): calibration_out(), drift_report_out(), calibration(), drift(), drift_all(), skew(), FeatureDriftOut, DriftReport (+1 more)

### Community 130 - "Community 130"
Cohesion: 0.18
Nodes (13): detect_feature_drift(), ValidationLossMonitor, reference(), test_a_recovery_resets_the_consecutive_count(), test_collapsed_variance_is_detected(), test_feature_count_mismatch_raises(), test_first_observation_only_sets_the_baseline(), test_increases_below_the_threshold_never_trigger() (+5 more)

### Community 131 - "Community 131"
Cohesion: 0.16
Nodes (17): answerRuns(), chip(), context(), cycleFor(), dateButton(), expectForm(), expectShowing(), fixture (+9 more)

### Community 132 - "Community 132"
Cohesion: 0.10
Nodes (7): client(), test_docs_route_is_unaffected(), test_sources_role_is_the_role_enum_in_the_openapi_schema(), test_sources_used_by_is_documented_in_the_openapi_schema(), test_theme_http_method_colors_are_distinct(), test_theme_never_uses_a_god_color(), _walk()

### Community 134 - "Community 134"
Cohesion: 0.17
Nodes (13): authHandle(), Auth, _authByRequest, buildAuth(), checkRegistrationOpen(), getAuth(), buildSessionHeaders(), extractBearerToken() (+5 more)

### Community 135 - "Community 135"
Cohesion: 0.16
Nodes (8): fetch_gefs_ensemble_grib2_fields(), fetch_gefs_member_grib2_fields(), _gefs_member_url(), test_control_member_zero_uses_gec00_not_gep00(), test_fetch_gefs_ensemble_reads_multiple_real_distinct_members(), test_fetch_gefs_member_reads_the_real_noaa_archive(), test_member_out_of_range_raises(), test_perturbed_member_url_matches_the_real_verified_path()

### Community 136 - "Community 136"
Cohesion: 0.19
Nodes (10): reconcile_official_errors(), technique_member(), techniques_to_read(), TechniqueSpec, test_a_case_without_an_adeck_has_no_technique_forecast(), test_a_lagged_member_reads_the_earlier_run_at_the_same_valid_time(), test_an_east_offset_is_scored_as_a_great_circle_distance_end_to_end(), test_reconciliation_reproduces_nhcs_errors_and_says_why_cases_differ() (+2 more)

### Community 137 - "Community 137"
Cohesion: 0.15
Nodes (11): _fake_samples(), _lc(), _report(), _stats(), teacher_and_data(), test_a_collapsed_student_is_not_warranted(), test_a_student_close_to_teacher_calibration_is_warranted(), test_distillation_rejects_a_non_positive_epochs_or_patience() (+3 more)

### Community 138 - "Community 138"
Cohesion: 0.11
Nodes (7): _FakeMlflowModelVersion, _mlflow_client_that_registers_and_transitions(), create_model_version(), test_mlflow_mirror_skips_create_registered_model_if_it_already_exists(), create_model_version(), test_mlflow_transition_also_mirrors_the_archived_incumbent(), create_model_version()

### Community 139 - "Community 139"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 140 - "Community 140"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 141 - "Community 141"
Cohesion: 0.15
Nodes (6): CloudflareAccessRequestHeaderProvider, test_headers_are_actually_applied_by_mlflows_own_resolution(), test_in_context_false_when_neither_var_set(), test_in_context_false_when_only_client_id_set(), test_in_context_true_and_correct_headers_when_both_set(), test_registered_as_a_real_mlflow_plugin_via_entry_points()

### Community 142 - "Community 142"
Cohesion: 0.17
Nodes (12): _adeck_position(), _adeck_positive(), AtcfError, parse_adeck(), _parse_latlon(), test_parse_adeck_converts_tenths_and_hemispheres_and_wraps_longitude(), test_parse_adeck_counts_unreadable_rows_instead_of_raising(), test_parse_adeck_keeps_the_first_of_each_point_and_counts_disagreeing_repeats() (+4 more)

### Community 143 - "Community 143"
Cohesion: 0.12
Nodes (4): _Boto3Client, require_boto3(), _StorageClient, test_boto3_adapter_configures_the_client_for_the_given_endpoint()

### Community 144 - "Community 144"
Cohesion: 0.12
Nodes (6): _bdeck_line(), _FrozenYear, _MemoryS3, replace_storm(), test_a_storm_leaving_the_live_feed_keeps_its_cycle_history(), test_a_storm_that_left_the_live_feed_is_listed_from_the_season_archive()

### Community 145 - "Community 145"
Cohesion: 0.12
Nodes (16): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+8 more)

### Community 146 - "Community 146"
Cohesion: 0.12
Nodes (16): compilerOptions, allowJs, allowSyntheticDefaultImports, checkJs, forceConsistentCasingInFileNames, isolatedModules, lib, module (+8 more)

### Community 147 - "Community 147"
Cohesion: 0.12
Nodes (16): permissions, runs-on, steps, jobs, copilot-setup-steps, name, on, pull_request (+8 more)

### Community 148 - "Community 148"
Cohesion: 0.17
Nodes (11): parse_bdeck(), parse_tcvitals(), TcVitalsError, test_bdeck_malformed_line_raises(), test_bdeck_parses_best_track_rows_only(), test_pair_by_valid_time_matches_shared_timestamps(), test_pair_by_valid_time_rejects_mismatched_storms(), test_storm_basin_is_a_direct_slice_of_the_storm_id() (+3 more)

### Community 149 - "Community 149"
Cohesion: 0.17
Nodes (9): _bilinear(), _lattice_index(), ohc_at(), OhcField, place(), test_bilinear_between_nodes(), test_bilinear_is_exact_at_a_node_on_every_source(), test_bilinear_needs_all_four_corners() (+1 more)

### Community 150 - "Community 150"
Cohesion: 0.17
Nodes (8): lr_factor(), TransformerOptimizer, test_a_short_stage_still_ends_on_the_floor(), test_config_values_are_validated(), test_cosine_decays_to_the_floor_on_the_last_update(), test_no_warmup_starts_at_the_peak(), test_the_optimiser_caps_the_stage_rate_warms_up_and_clips(), test_warmup_rises_linearly_to_the_peak()

### Community 151 - "Community 151"
Cohesion: 0.16
Nodes (7): al_2021_2022(), compare(), open_ocean(), parse_ships(), sample_days(), ShipsCase, test_sohc_equals_bilinear_ohc_on_the_file_named_for_the_day_before()

### Community 152 - "Community 152"
Cohesion: 0.16
Nodes (9): cache_all_fixes(), _curriculum_tracks(), _FakeS3Client, test_a_zero_steering_conv_computes_the_plain_model(), test_builder_without_steering_keeps_the_old_layout(), test_curriculum_refuses_steering_without_streaming_or_without_the_cache_meta(), test_curriculum_trains_the_steering_path_in_stage_b_only(), test_curriculum_with_steering_trains_the_conv_in_stage_b_only() (+1 more)

### Community 153 - "Community 153"
Cohesion: 0.15
Nodes (9): _called(), _calls(), _function(), _modules(), _parameters(), _parse(), test_a_fetch_only_importer_names_the_adapter_it_is_listed_for(), test_model_inputs_match_what_each_runner_and_live_builder_takes() (+1 more)

### Community 154 - "Community 154"
Cohesion: 0.12
Nodes (16): with, build-args, cache-from, cache-to, context, file, load, password (+8 more)

### Community 155 - "Community 155"
Cohesion: 0.12
Nodes (15): jobs, lint-and-validate, name, permissions, runs-on, steps, name, on (+7 more)

### Community 156 - "Community 156"
Cohesion: 0.15
Nodes (7): HomogeneousRow, BaselineReport, _fmt(), format_report(), _json_safe(), samples_for(), test_the_report_serialises_as_strict_json_and_prints_a_table()

### Community 157 - "Community 157"
Cohesion: 0.28
Nodes (8): NoiseSensitivityReport, _result(), test_is_load_bearing_above_threshold(), test_is_not_load_bearing_below_threshold(), test_relative_change_is_zero_when_losses_match(), test_relative_change_rejects_nonpositive_default_loss(), test_relative_change_sign_matches_direction_of_the_move(), test_run_noise_sensitivity_raises_without_val_storms()

### Community 158 - "Community 158"
Cohesion: 0.17
Nodes (10): _live_prior_for(), _cache_truth(), test_a_version_trained_on_the_adecks_is_never_served(), test_a_version_with_a_prior_is_described(), test_curriculum_with_a_prior_scores_prior_plus_correction(), test_one_prior_fetch_is_shared_by_every_model_in_a_forecast(), test_served_forecast_is_the_prior_plus_the_correction(), test_serving_gate_only_applies_to_a_version_trained_with_a_prior() (+2 more)

### Community 159 - "Community 159"
Cohesion: 0.13
Nodes (15): scripts, build, cf:deploy, check, check:errors, check:warnings, check:watch, dev (+7 more)

### Community 160 - "Community 160"
Cohesion: 0.19
Nodes (12): loading, onInput(), open, query, results, bodyById, buildIndex(), excerptAround() (+4 more)

### Community 161 - "Community 161"
Cohesion: 0.13
Nodes (15): env, environment, if, name, needs, permissions, runs-on, timeout-minutes (+7 more)

### Community 162 - "Community 162"
Cohesion: 0.19
Nodes (8): adeck_name(), adeck_path(), file_record(), read_adeck(), read_cached_adecks(), test_adeck_names_urls_and_paths_come_only_from_valid_storm_ids(), test_read_cached_adecks_reads_gzip_and_records_missing_and_unreadable(), test_real_archived_adeck_carries_the_default_techniques()

### Community 163 - "Community 163"
Cohesion: 0.24
Nodes (11): validate(), make_tags(), test_malformed_dvc_version_is_rejected(), test_malformed_git_commit_is_rejected(), test_malformed_nwp_cycle_lag_is_rejected(), test_none_values_are_dropped_from_the_dict(), test_pretrain_flavor_tags_are_not_operational(), test_v2_1_adds_input_flavor_and_nwp_cycle_lag() (+3 more)

### Community 164 - "Community 164"
Cohesion: 0.14
Nodes (13): compilerOptions, allowJs, checkJs, esModuleInterop, forceConsistentCasingInFileNames, moduleResolution, resolveJsonModule, rewriteRelativeImportExtensions (+5 more)

### Community 165 - "Community 165"
Cohesion: 0.14
Nodes (13): images, options, diskSizeGb, machineType, steps, args, entrypoint, env (+5 more)

### Community 166 - "Community 166"
Cohesion: 0.14
Nodes (14): default, description, type, default, description, type, api, console (+6 more)

### Community 167 - "Community 167"
Cohesion: 0.19
Nodes (10): generate_season(), test_archive_spans_the_requested_seasons(), test_fields_have_matching_shapes_and_carry_a_flavor(), test_fixes_are_six_hourly_and_synoptic(), test_gdas_fields_are_noisier_than_era5(), test_generated_tracks_are_final_quality(), test_generation_is_reproducible(), test_intensity_rises_and_falls() (+2 more)

### Community 168 - "Community 168"
Cohesion: 0.17
Nodes (12): IdTokenClaims, JwtClaims, OidcAddressClaim, OidcStandardClaims, UserProfile, Mandatory, RFC-3966, RFC-4627 (+4 more)

### Community 169 - "Community 169"
Cohesion: 0.15
Nodes (12): name, runs-on, timeout-minutes, concurrency, cancel-in-progress, group, jobs, build (+4 more)

### Community 170 - "Community 170"
Cohesion: 0.21
Nodes (7): provenance_out(), get_cycle(), get_storm(), list_storms(), _served_basins(), _storm_summary(), FixOut

### Community 171 - "Community 171"
Cohesion: 0.18
Nodes (9): _get_real_state(), _stage_group1_and_derived(), test_a_live_storm_keeps_its_cycles_across_a_feed_refresh(), test_calibration_report_is_honest_empty_with_no_samples(), test_drift_report_is_honest_zero_when_no_reference_has_been_fit(), test_pending_retrain_jobs_detects_a_real_latent_desync(), test_pending_retrain_jobs_is_empty_for_a_coherent_registry(), test_pending_retrain_jobs_route_serves_a_real_latent_desync() (+1 more)

### Community 172 - "Community 172"
Cohesion: 0.23
Nodes (11): max, target, budgets, reduced, standard, max, target, assembly (+3 more)

### Community 173 - "Community 173"
Cohesion: 0.17
Nodes (4): local, notes, problems, remote

### Community 174 - "Community 174"
Cohesion: 0.21
Nodes (7): client(), test_a_registered_versions_arch_params_are_used(), test_a_version_that_reads_steering_is_described(), test_a_version_without_arch_params_is_described_from_defaults(), test_every_model_runs_its_example_input_and_reports_its_layers(), test_the_gnn_is_fed_the_real_lattice(), test_unknown_models_and_versions_are_404()

### Community 175 - "Community 175"
Cohesion: 0.17
Nodes (11): concurrency, cancel-in-progress, group, jobs, test-api, name, if, name (+3 more)

### Community 176 - "Community 176"
Cohesion: 0.17
Nodes (12): with, cache, cache-dependency-path, enable-cache, fetch-depth, if-no-files-found, include-hidden-files, name (+4 more)

### Community 177 - "Community 177"
Cohesion: 0.18
Nodes (3): CachedAdecks, Adeck, AdeckPoint

### Community 178 - "Community 178"
Cohesion: 0.18
Nodes (5): offset_position(), ConeOutcome, served_cone_outcome(), test_served_cone_scores_what_build_cone_actually_serves(), ensemble()

### Community 179 - "Community 179"
Cohesion: 0.24
Nodes (5): build_info(), _build_info_path(), config_digest(), git_sha(), summary()

### Community 180 - "Community 180"
Cohesion: 0.17
Nodes (6): test_mlflow_failure_degrades_to_local_only(), __getattr__(), test_mlflow_mirror_is_skipped_without_a_checkpoint_uri(), __getattr__(), test_mlflow_mirror_registers_model_then_version_with_a_real_source_uri(), create_model_version()

### Community 181 - "Community 181"
Cohesion: 0.17
Nodes (3): test_pull_is_a_noop_when_the_key_does_not_exist_remotely_yet(), test_register_persists_locally_and_durably_before_touching_mlflow(), create_model_version()

### Community 182 - "Community 182"
Cohesion: 0.18
Nodes (11): cycle, advisory_margin_minutes, advisory_offset_minutes, allow_estimated_vitals, allow_load_shedding, max_nwp_lag_hours, nominal_vitals_offset_minutes, nwp_lag_hours (+3 more)

### Community 184 - "Community 184"
Cohesion: 0.22
Nodes (7): assert_not_operational(), operational_sources(), _operational_substitute(), OperationalUseError, test_operational_sources_pass_the_guard(), test_reading_era5_in_the_inference_path_is_refused(), test_reading_final_besttrack_in_the_inference_path_is_refused()

### Community 185 - "Community 185"
Cohesion: 0.22
Nodes (3): _join(), _json_rows(), _rounded()

### Community 186 - "Community 186"
Cohesion: 0.18
Nodes (6): fields(), gdas_likely_unpublished(), _memoised_lead(), test_gdas_likely_unpublished_false_for_an_archived_storm(), test_gdas_likely_unpublished_false_once_real_typical_latency_has_passed(), test_gdas_likely_unpublished_true_within_real_typical_latency()

### Community 187 - "Community 187"
Cohesion: 0.22
Nodes (6): first_record_of_year(), ships_al_url(), _ships_get(), ships_record_year(), ships_size(), ships_window()

### Community 188 - "Community 188"
Cohesion: 0.20
Nodes (10): limit, lower_is_better, limit, lower_is_better, thresholds, intensity_error_48h_kt, intensity_error_72h_kt, track_error_72h_nm (+2 more)

### Community 189 - "Community 189"
Cohesion: 0.29
Nodes (9): getMagicLinkHtml(), getMagicLinkText(), getOtpHtml(), getOtpText(), OTP_BODY_COPY, OTP_SUBJECTS, OtpType, sendMagicLinkEmail() (+1 more)

### Community 190 - "Community 190"
Cohesion: 0.42
Nodes (8): fetch(), classifyCycleResponse(), CYCLE_POST_RE, CycleOutcome, cycleRunStormId(), decodedPath(), isInternalPath(), requiresSignedInUser()

### Community 191 - "Community 191"
Cohesion: 0.20
Nodes (10): steps, EXPECT_GIT_SHA, GCP_CI_SERVICE_ACCOUNT, GCP_WIF_PROVIDER, env, id, if, name (+2 more)

### Community 192 - "Community 192"
Cohesion: 0.20
Nodes (10): name, outputs, runs-on, timeout-minutes, changes, deploy_api, deploy_console, plan (+2 more)

### Community 193 - "Community 193"
Cohesion: 0.40
Nodes (10): steps, steps, id, if, name, run, uses, working-directory (+2 more)

### Community 194 - "Community 194"
Cohesion: 0.20
Nodes (4): fetch(), _MemoryS3, s3(), store()

### Community 195 - "Community 195"
Cohesion: 0.27
Nodes (4): ChecksumCheck, FetchResult, NonEmptyCheck, QCFinding

### Community 196 - "Community 196"
Cohesion: 0.24
Nodes (6): assert_operational_flavor(), CycleError, extrapolate_fix(), test_extrapolation_continues_the_last_motion_vector(), test_extrapolation_needs_two_prior_fixes(), test_operational_flavor_guard_rejects_pretrain_features()

### Community 197 - "Community 197"
Cohesion: 0.20
Nodes (3): test_cmd_train_actually_transitions_a_promotable_candidate_to_staging(), test_pull_is_skipped_entirely_without_a_checkpoint_store(), test_pull_reconciles_with_durable_storage_even_when_local_already_exists()

### Community 198 - "Community 198"
Cohesion: 0.31
Nodes (4): _attributes(), _imported(), _names_adapter(), _string_literals()

### Community 199 - "Community 199"
Cohesion: 0.22
Nodes (9): run, test-console, working-directory, defaults, if, name, needs, runs-on (+1 more)

### Community 200 - "Community 200"
Cohesion: 0.22
Nodes (9): BASE_SHA, BEFORE_SHA, DISPATCH_API, DISPATCH_CONSOLE, EVENT, EXPECT_GIT_SHA, HEAD_SHA, REF (+1 more)

### Community 201 - "Community 201"
Cohesion: 0.25
Nodes (5): source_out(), sources(), SourceOut, DataSource, pretrain_only_sources()

### Community 202 - "Community 202"
Cohesion: 0.28
Nodes (4): oracle(), pytest_collection_modifyitems(), target_time(), worst_case_oracle()

### Community 203 - "Community 203"
Cohesion: 0.25
Nodes (6): _fake_fields(), fetch(), test_a_corrected_previous_fix_is_tracked_again_not_read_from_the_cache(), test_an_unwritable_cache_still_returns_the_track(), test_the_field_memo_fetches_each_lead_once_under_concurrent_cycles(), cycle()

### Community 204 - "Community 204"
Cohesion: 0.25
Nodes (8): 12, 120, 24, 36, 48, 72, 96, climatological_cone_nm

### Community 205 - "Community 205"
Cohesion: 0.25
Nodes (8): CP, 12, 120, 24, 36, 48, 72, 96

### Community 206 - "Community 206"
Cohesion: 0.25
Nodes (8): EP, 12, 120, 24, 36, 48, 72, 96

### Community 207 - "Community 207"
Cohesion: 0.25
Nodes (7): calibration_audit, cone_nominal_rate, intensity_nominal_rate, min_cases, verdict_margin, test_set_budget, max_evaluations_per_season

### Community 208 - "Community 208"
Cohesion: 0.25
Nodes (8): drift, min_samples, reference_flavor, shift_sigma, validation_loss, variance_ratio_limit, consecutive_required, threshold_fraction

### Community 209 - "Community 209"
Cohesion: 0.25
Nodes (8): promotion, flavor, new_basin_tolerance, primary_metric, reference_basin, require_manual_gate, split, basins()

### Community 210 - "Community 210"
Cohesion: 0.43
Nodes (4): cycle_inputs_prefix(), _get_text(), _put_text(), save_cycle_inputs()

### Community 212 - "Community 212"
Cohesion: 0.25
Nodes (3): test_a_desynced_derived_champion_is_not_a_bar_a_servable_candidate_must_clear(), test_a_servable_derived_champion_is_still_a_real_bar(), test_derived_resync_records_the_champion_signature_and_ends_in_sync()

### Community 214 - "Community 214"
Cohesion: 0.29
Nodes (7): products, cone_percentile, landfall_threshold_nm, lead_hours, ri_alert_probability, ri_threshold_kt, ri_window_hours

### Community 215 - "Community 215"
Cohesion: 0.29
Nodes (7): skew_audit, alert_intensity_delta_kt, alert_track_delta_nm, audit_delay_days, lead_hours, min_samples, window_days

### Community 216 - "Community 216"
Cohesion: 0.57
Nodes (5): deploy-plan.sh script, touches(), touches_component(), touches_console(), why

### Community 217 - "Community 217"
Cohesion: 0.29
Nodes (7): env, IMAGE, JOB, PROJECT_ID, PUBLISH, REGION, REGISTRY

### Community 218 - "Community 218"
Cohesion: 0.29
Nodes (3): retrain_job_out(), pending_triggers(), RetrainJobOut

### Community 220 - "Community 220"
Cohesion: 0.33
Nodes (6): ensemble, climatological_cone_nm_by_basin, members, min_members_for_ensemble_cone, reduced_members, underdispersion_fraction

### Community 221 - "Community 221"
Cohesion: 0.33
Nodes (6): triggers, data_volume_threshold, nightly_latent_hour_utc, preseason_date, scheduled_monthly_day, suppress_nightly_latent_during_active_storms

### Community 223 - "Community 223"
Cohesion: 0.33
Nodes (4): {
		flagged,
		probability,
		lo = null,
		hi = null,
		uncertain = null,
		ensembleSize = null,
	}, membersNote, Props, range

### Community 224 - "Community 224"
Cohesion: 0.47
Nodes (5): AppAuth, buildAuth(), getAuth(), verifyApiKey(), resolveUserId()

### Community 226 - "Community 226"
Cohesion: 0.33
Nodes (6): update_job, workflow_dispatch, default, description, type, inputs

### Community 227 - "Community 227"
Cohesion: 0.33
Nodes (6): on, pull_request, push, paths, branches, paths

### Community 230 - "Community 230"
Cohesion: 0.33
Nodes (3): test_an_adapter_is_named_by_other_code_only_if_its_source_is_read(), test_every_fetch_adapter_is_classified(), _unread_sources()

### Community 231 - "Community 231"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 232 - "Community 232"
Cohesion: 0.40
Nodes (3): WORLD_GEOJSON, WorldData, WorldFeatureProperties

### Community 233 - "Community 233"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 234 - "Community 234"
Cohesion: 0.40
Nodes (4): ANEMOI_FIELDS_MEMO, ANEMOI_GFS_TRACK_DIR, ANEMOI_STEERING_CACHE_DIR, entrypoint.sh script

### Community 236 - "Community 236"
Cohesion: 0.40
Nodes (3): generate_track(), make_storm_spec(), StormSpec

### Community 240 - "Community 240"
Cohesion: 0.67
Nodes (4): max, target, diffusion, diffusion

### Community 241 - "Community 241"
Cohesion: 0.67
Nodes (4): max, target, fusion, fusion

### Community 242 - "Community 242"
Cohesion: 0.67
Nodes (4): max, target, postprocess, postprocess

### Community 243 - "Community 243"
Cohesion: 0.67
Nodes (4): max, target, preprocess, preprocess

### Community 244 - "Community 244"
Cohesion: 0.83
Nodes (3): graphify(), normalise_graph(), build-graph.sh script

### Community 245 - "Community 245"
Cohesion: 0.50
Nodes (3): uvx, graphify, graphify-mcp

### Community 249 - "Community 249"
Cohesion: 0.67
Nodes (3): limit, lower_is_better, nhc_consensus_beat_rate_48h

### Community 250 - "Community 250"
Cohesion: 0.67
Nodes (3): track_error_120h_nm, limit, lower_is_better

### Community 251 - "Community 251"
Cohesion: 0.67
Nodes (3): track_error_48h_nm, limit, lower_is_better

## Knowledge Gaps
- **15 isolated node(s):** `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627`, `RFC-5322`, `RFC-5646` (+10 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2944 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Flavor` connect `Community 6` to `Community 0`, `Community 129`, `Community 1`, `Community 256`, `Community 4`, `Community 133`, `Community 5`, `Community 7`, `Community 8`, `Community 130`, `Community 2`, `Community 138`, `Community 10`, `Community 14`, `Community 15`, `Community 18`, `Community 23`, `Community 152`, `Community 26`, `Community 28`, `Community 30`, `Community 158`, `Community 32`, `Community 34`, `Community 35`, `Community 163`, `Community 36`, `Community 167`, `Community 40`, `Community 41`, `Community 171`, `Community 174`, `Community 46`, `Community 52`, `Community 180`, `Community 181`, `Community 56`, `Community 57`, `Community 58`, `Community 61`, `Community 63`, `Community 67`, `Community 196`, `Community 68`, `Community 197`, `Community 71`, `Community 72`, `Community 78`, `Community 79`, `Community 80`, `Community 83`, `Community 212`, `Community 86`, `Community 90`, `Community 99`, `Community 100`, `Community 102`, `Community 105`, `Community 108`, `Community 109`, `Community 238`, `Community 237`, `Community 120`, `Community 122`, `Community 126`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 259 inferred relationships involving `Flavor` (e.g. with `DemoState` and `drift()`) actually correct?**
  _`Flavor` has 259 INFERRED edges - model-reasoned connections that need verification._
- **What connects `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627` to the rest of the system?**
  _15 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.033514872224549644 - nodes in this community are weakly interconnected._
- **Why does `Track` connect `Community 5` to `Community 0`, `Community 1`, `Community 2`, `Community 256`, `Community 4`, `Community 133`, `Community 7`, `Community 8`, `Community 136`, `Community 10`, `Community 13`, `Community 14`, `Community 15`, `Community 144`, `Community 148`, `Community 24`, `Community 25`, `Community 26`, `Community 152`, `Community 28`, `Community 157`, `Community 158`, `Community 32`, `Community 37`, `Community 167`, `Community 40`, `Community 42`, `Community 43`, `Community 171`, `Community 46`, `Community 54`, `Community 56`, `Community 57`, `Community 61`, `Community 63`, `Community 66`, `Community 67`, `Community 69`, `Community 70`, `Community 72`, `Community 75`, `Community 203`, `Community 79`, `Community 80`, `Community 210`, `Community 82`, `Community 90`, `Community 92`, `Community 97`, `Community 102`, `Community 236`, `Community 109`, `Community 108`, `Community 117`, `Community 120`, `Community 121`, `Community 126`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 151 inferred relationships involving `Track` (e.g. with `save_cycle_inputs()` and `StormState`) actually correct?**
  _`Track` has 151 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.03261623872310895 - nodes in this community are weakly interconnected._