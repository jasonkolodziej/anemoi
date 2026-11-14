# Graph Report - anemoi  (2026-11-14)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 6762 nodes · 17303 edges · 264 communities (235 shown, 29 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 2530 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `aba02ace`
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
- Community 239
- Community 240
- Community 241
- Community 242
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
- Community 263

## God Nodes (most connected - your core abstractions)
1. `Flavor` - 287 edges
2. `Track` - 192 edges
3. `Fix` - 145 edges
4. `ModelRegistry` - 135 edges
5. `CheckpointStore` - 130 edges
6. `TrackQuality` - 106 edges
7. `require_torch()` - 100 edges
8. `MetricSet` - 81 edges
9. `FetchTask` - 71 edges
10. `LatencyOracle` - 68 edges

## Surprising Connections (you probably didn't know these)
- `make_fix()` --calls--> `Fix`  [INFERRED]
  tests/test_streaming.py → src/anemoi/data/besttrack.py
- `make_fix()` --calls--> `Fix`  [INFERRED]
  tests/test_streaming.py → src/anemoi/data/besttrack.py
- `test_internal_calibration_audit_route_reports_new_samples()` --uses--> `RealState`  [INFERRED]
  tests/test_api_real_state.py → src/anemoi/api/real_state.py
- `test_cache_round_trip_and_vector()` --uses--> `FetchTask`  [INFERRED]
  tests/test_steering.py → src/anemoi/data/gridded_cache.py
- `test_trained_basins_without_champions_is_the_atlantic()` --uses--> `ModelRegistry`  [INFERRED]
  tests/test_registry.py → src/anemoi/tracking/registry.py

## Import Cycles
- None detected.

## Communities (264 total, 29 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (51): list_cycle_labels(), cmd_ablation(), cmd_atcf_archive(), cmd_cache_localize(), cmd_consistency_distill(), cmd_drift_reference_fit(), cmd_era5_cache(), cmd_gdas_cache() (+43 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (51): Props, Section, SectionPage, { sections }, height, motionClass, Props, {
    size = 28,
    spinning = false,
    class: className,
    ...restProps
  } (+43 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (75): layerchart@^2.5.1, ActivePin, CyclePayload, CycleProducts, CycleResult, DriftReportOut, FeatureDriftOut, HealthOut (+67 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (28): augment_track(), emulate_working_track(), WorkingTrackNoise, basin_key(), is_basin_key(), key_basin(), per_basin_scores(), sample_counts() (+20 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (46): experiment_name(), cmd_train(), latest_final_season(), basin_value(), trained_basins(), verified_basins(), config_digest(), git_sha() (+38 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (43): ensemble(), basin_inputs(), steering_inputs(), _builder(), _build_live_context(), _build_live_x(), deterministic_fn(), _compute_env_features() (+35 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (42): CycleResult, audit_cycle(), audit_due(), audit_storm(), _audited_key(), calibrate_products(), CalibrationSample, LeadProductCalibration (+34 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (50): calibrate(), forecast_motion_bearings(), observed_motion_bearings(), recurving_cases(), _scalar_errors(), brier_score(), crps_ensemble(), _crps_rows() (+42 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (69): svelte-sonner@^1.2.3, ApiError, apiFetch(), getArchitecture(), getCalibration(), getCycle(), getDrift(), getDriftAll() (+61 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (42): apply_cold_wake(), area_mean(), cold_wake_sst_depression_c(), compare_potential_intensity_estimates(), compute_environment_features(), deep_layer_shear(), emanuel_potential_intensity(), GriddedFields (+34 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (32): train_cnn_stage_streaming(), freeze_encoder(), train_gnn_stage_streaming(), train_lstm_stage_streaming(), _sanitized_channel_stack(), _standardize_x(), _standardize_y(), train_transformer_stage() (+24 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (41): _default_fetch_fn(), fetch(), _default_fetch_fn(), fetch(), _crop_box(), era5_deps_available(), era5_to_gridded_fields(), crop() (+33 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (16): DemoState, get_state(), StormState, require_api_key(), state_dependency(), get_custom_redoc_html(), create_app(), _debug_last_deterministic_error() (+8 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (43): @lucide/svelte@^1.71.0, sveltekit-superforms@^2.31.0, authClient, { form }, Props, { form }, Props, errorMsg (+35 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (38): Fix, steering_meta_digest(), build_live_cnn_x(), build_live_gnn_x(), build_live_lstm_x(), build_live_pinn_x(), build_live_transformer_x(), _current_fields() (+30 more)

### Community 15 - "Community 15"
Cohesion: 0.04
Nodes (35): require_meta(), steering_meta(), _context_features(), _displacement_to_absolute(), _empty_samples(), _extract_for_tracks(), extract_validation_latents(), joint_stage_windows() (+27 more)

### Community 16 - "Community 16"
Cohesion: 0.05
Nodes (39): build_cone(), build_products(), climatological_cone_nm(), cone_radius_from_spread(), ConeSegment, deterministic_center(), EnsembleMember, ForecastProducts (+31 more)

### Community 17 - "Community 17"
Cohesion: 0.06
Nodes (8): cycle_payload_out(), cycle_result_out(), provenance_out(), RealState, deterministic(), live_fields(), RealStormState, CycleOutput

### Community 18 - "Community 18"
Cohesion: 0.05
Nodes (27): initial_fix(), assert_input_safe(), Track, TrackQuality, extrapolate_fix(), test_a_basin_is_in_distribution_once_every_served_model_is_verified_in_it(), test_listing_storms_never_runs_the_calibration_audit(), test_pacific_storm_is_flagged_as_not_a_trained_basin() (+19 more)

### Community 19 - "Community 19"
Cohesion: 0.06
Nodes (49): AppAuth, buildAuth(), getAuth(), verifyApiKey(), CYCLE_STEP, cycleInstanceId(), CycleParams, CycleWorkflow (+41 more)

### Community 20 - "Community 20"
Cohesion: 0.05
Nodes (29): absolute_pairs(), LeadCalibration, ForecastPoint, LeadTimeStats, motion_bearing(), to_metric_dict(), VerificationPair, verify() (+21 more)

### Community 21 - "Community 21"
Cohesion: 0.06
Nodes (31): check_run(), CycleConflict, _existing_source(), InFlight, operator_ids(), RunRequest, stored_source(), RunInfo (+23 more)

### Community 22 - "Community 22"
Cohesion: 0.05
Nodes (34): _baseline_inputs(), _empty_report(), _fake_curriculum_run(), _hurdat2_storm(), make_args(), make_track(), _retrain_check_args(), _spy_assign_splits() (+26 more)

### Community 23 - "Community 23"
Cohesion: 0.06
Nodes (33): svelte-guard@^1.1.1, authHandle(), guards, handle, DEFAULT_AFTER_LOGIN, loginHref(), safeNext(), Auth (+25 more)

### Community 24 - "Community 24"
Cohesion: 0.09
Nodes (34): assert_deployable(), Curriculum, CurriculumError, CurriculumRun, StageResult, boundaries_for_tracks(), run_cnn_curriculum(), run_gnn_curriculum() (+26 more)

### Community 25 - "Community 25"
Cohesion: 0.07
Nodes (30): invalidated_by(), evaluate_all(), expand_jobs(), nightly_latent(), on_data_volume(), on_drift(), on_latent_desync(), on_skew() (+22 more)

### Community 26 - "Community 26"
Cohesion: 0.05
Nodes (30): recalibrate_from_pairs(), Archive, archives_for(), describe(), fetch_latest_hurdat2(), last_season(), latest_name(), manifest_path() (+22 more)

### Community 27 - "Community 27"
Cohesion: 0.06
Nodes (36): cycle_products_out(), model_version_out(), get_active_pin(), get_model_architecture(), get_model_registry(), list_registry(), ActivePin, ArchitectureOut (+28 more)

### Community 28 - "Community 28"
Cohesion: 0.05
Nodes (23): stage_a(), stage_b(), test_both_stages_label_from_final_besttrack(), test_stage_a_uses_era5_and_stage_b_uses_gdas(), test_stage_b_learning_rate_is_lower_than_stage_a(), _RecordingStore, _StubMlflowClient, _StubRun (+15 more)

### Community 29 - "Community 29"
Cohesion: 0.07
Nodes (33): client(), _FakeCycleOutput, _fresh_real_state(), _get_real_state(), hurdat2_file(), _make_deterministic_forecast(), _make_storm_state(), _memory_store() (+25 more)

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (27): case_errors(), compared_members(), homogeneous_mask(), HomogeneousRow, _limiting(), _mean(), Member, MemberScore (+19 more)

### Community 31 - "Community 31"
Cohesion: 0.05
Nodes (38): CyclePlanOut, at(), calendarValue, hour, hourAllowed, inRange(), maxValue, minValue (+30 more)

### Community 32 - "Community 32"
Cohesion: 0.06
Nodes (42): SourceOut, byUse(), hasUnknownEntry(), MODEL_NAMES, MODELS, ORDER, readersOf(), SOURCE_NAMES (+34 more)

### Community 33 - "Community 33"
Cohesion: 0.06
Nodes (25): Flavor, _champions(), test_a_basin_is_served_once_every_champion_is_verified_in_it(), _FakeS3Config, test_champion_falls_back_to_staging_without_a_production_version(), test_champion_is_not_simply_the_most_recently_registered_version(), test_champion_prefers_production_over_staging(), test_checkpoint_store_push_failure_degrades_to_local_only() (+17 more)

### Community 34 - "Community 34"
Cohesion: 0.07
Nodes (36): getActivePin(), getSources(), listRegistry(), RegistryEntry, RetrainJobOut, errorDetail(), notifyError(), anchor (+28 more)

### Community 35 - "Community 35"
Cohesion: 0.07
Nodes (19): sanitize_field_pixels(), reference_value(), _sanitized_channel_stack(), _standardize_cnn_x(), _standardize_y(), train_cnn_stage(), displacement_validation_metrics(), FusionArtifacts (+11 more)

### Community 36 - "Community 36"
Cohesion: 0.09
Nodes (37): emulate_working_fix(), validate(), _latlon(), make_fix(), make_track(), test_assert_input_safe_allows_working_quality(), test_assert_input_safe_blocks_final_quality(), test_augment_track_rejects_non_final_input() (+29 more)

### Community 37 - "Community 37"
Cohesion: 0.08
Nodes (29): cmd_adeck_fetch(), cmd_steering_cache(), assert_no_leakage(), assign_splits(), _earliest_season(), filter_tracks(), _latest_season(), LeakageError (+21 more)

### Community 38 - "Community 38"
Cohesion: 0.07
Nodes (19): JointLatentSamples, _standardize(), _standardize_y(), train_diffusion_stage(), _FakeS3Client, _make_samples(), test_a_longer_epoch_budget_never_returns_a_worse_val_loss(), test_early_stopping_halts_before_the_epoch_cap_on_a_real_overfitting_run() (+11 more)

### Community 39 - "Community 39"
Cohesion: 0.09
Nodes (31): expected_coordinates(), OhcRejected, place(), _decode(), files(), local(), _ohc(), _row_col() (+23 more)

### Community 40 - "Community 40"
Cohesion: 0.09
Nodes (26): ExecutionMode, Task, fake_load_run_artifacts(), _register_group1_versions(), runner(), make_fake(), test_a_desynced_derived_champion_is_not_a_bar_a_servable_candidate_must_clear(), test_a_failing_model_is_reported_not_raised() (+18 more)

### Community 41 - "Community 41"
Cohesion: 0.09
Nodes (24): cache_path(), _decode_cached_fields(), FetchTask, load_cached_fields(), build_x(), build_x(), _filter_and_fit_env_stats(), _filter_windows_with_finite_env() (+16 more)

### Community 42 - "Community 42"
Cohesion: 0.07
Nodes (22): require_torch(), build_transformer(), encode(), forward(), distill_consistency_model(), compile_model(), get_device(), JointLatentBundle (+14 more)

### Community 43 - "Community 43"
Cohesion: 0.10
Nodes (24): build_cnn(), encode(), forward(), __init__(), build_cnn_samples(), CnnStageSamples, test_cnn_is_resolution_agnostic(), cache_all_fixes() (+16 more)

### Community 44 - "Community 44"
Cohesion: 0.13
Nodes (25): run_cycle(), deterministic_fn(), good_ensemble(), make_fix(), test_a_pacific_climatological_ensemble_is_drawn_from_pacific_radii(), test_absent_opportunistic_feeds_do_not_flag_the_cycle(), test_an_eastern_pacific_cycle_falls_back_to_nhcs_pacific_radii(), test_caller_requested_members_is_honored_by_the_climatological_fallback() (+17 more)

### Community 45 - "Community 45"
Cohesion: 0.08
Nodes (20): Adeck, _adeck_position(), AdeckPoint, AtcfError, pair_by_valid_time(), parse_bdeck(), _parse_latlon(), parse_tcvitals() (+12 more)

### Community 46 - "Community 46"
Cohesion: 0.08
Nodes (21): advisory_time(), floor_synoptic(), is_synoptic(), next_synoptic(), NWPCycleSelection, NWPUnavailableError, require_synoptic(), _require_utc() (+13 more)

### Community 47 - "Community 47"
Cohesion: 0.10
Nodes (24): displacement_nm(), storm_relative_sequence(), bearing_deg(), bearings_deg(), cross_along_track_nm(), cross_along_track_nms(), haversine_nm(), km_to_nm() (+16 more)

### Community 48 - "Community 48"
Cohesion: 0.10
Nodes (26): build_gnn(), encode(), forward(), __init__(), build_gnn_samples(), build_mesh_topology(), GnnStageSamples, test_gnn_message_passing_runs_over_a_small_graph() (+18 more)

### Community 49 - "Community 49"
Cohesion: 0.08
Nodes (22): format_report(), recommend_extra_conditioning(), run_spread_backtest(), SpreadBacktestError, SpreadBacktestReport, _fake_val(), _FakeS3Client, _lc() (+14 more)

### Community 50 - "Community 50"
Cohesion: 0.05
Nodes (40): devDependencies, cn@^0.3.3, @fontsource-variable/geist@^5.3.0, @fontsource-variable/geist-mono@^5.3.0, @fontsource-variable/inter@^5.3.0, formsnap@^2.0.1, mode-watcher@^1.1.0, @playwright/test@^1.63.0 (+32 more)

### Community 51 - "Community 51"
Cohesion: 0.07
Nodes (39): dependencies, arktype@^2.2.7, @better-auth/api-key@^1.7.7, @better-auth/passkey@^1.7.7, bits-ui@^2.20.6, clsx@^2.1.1, d3-polygon@^3.0.1, d3-scale@^4.0.2 (+31 more)

### Community 52 - "Community 52"
Cohesion: 0.10
Nodes (11): cycle_plan_out(), schedule(), ScheduleOut, CyclePlan, derive_vitals_timeout(), plan_day(), _schedule_stages(), ScheduledStage (+3 more)

### Community 53 - "Community 53"
Cohesion: 0.11
Nodes (25): build_fetch_tasks(), save_cached_fields(), shard_tracks(), FakeArchive, _fix_keys(), make_fields(), make_track(), _saved() (+17 more)

### Community 54 - "Community 54"
Cohesion: 0.10
Nodes (21): _crop_variable(), fetch_real_satellite_crop(), _find_real_scan(), GoesFetchError, _lazy_open(), _list_scan_keys(), _nearest_scan_key(), _parse_scan_start() (+13 more)

### Community 55 - "Community 55"
Cohesion: 0.10
Nodes (22): build_pinn(), encode(), forward(), __init__(), build_pinn_samples(), cache_all_fixes(), _FakeS3Client, make_fields() (+14 more)

### Community 56 - "Community 56"
Cohesion: 0.07
Nodes (30): ConeSegmentOut, FixOut, bounds, colors, coneFeatures, coneHull, currentFix, forecastLine (+22 more)

### Community 57 - "Community 57"
Cohesion: 0.09
Nodes (17): DriftError, ReferenceDistribution, load_reference(), reference_from_json(), reference_to_json(), save_reference(), test_drift_reference_fit_fits_and_persists_from_real_cached_fields(), test_reference_must_be_the_stage_b_distribution() (+9 more)

### Community 58 - "Community 58"
Cohesion: 0.10
Nodes (19): _decode_one_sonde(), DropsondeFetchError, DropsondeProfile, fetch_and_parse_dropsonde_mission(), fetch_dropsonde_mission_tarball(), _ftp_connect(), list_dropsonde_missions(), _mask_missing() (+11 more)

### Community 59 - "Community 59"
Cohesion: 0.12
Nodes (20): _bytemap_path(), decode_ssmis_bytemap(), fetch_and_decode_ssmis_daily(), fetch_ssmis_daily_bytemap(), MicrowaveFetchError, RSSFtpCredentials, SSMISDaily, _make_bytemap() (+12 more)

### Community 60 - "Community 60"
Cohesion: 0.11
Nodes (19): _check_basin(), _created_date(), creation_day(), cycle_date(), decode_ohc(), detect_format(), fetch_ohc_file(), name_day_for_creation() (+11 more)

### Community 61 - "Community 61"
Cohesion: 0.11
Nodes (21): audit_one(), audit_run(), _AuditPlan, _era5t_fetcher(), fetch(), _fix_from_dict(), _fix_to_dict(), list_operational_records() (+13 more)

### Community 62 - "Community 62"
Cohesion: 0.09
Nodes (19): cache_nwp_lead_hours(), CacheLeadMismatch, _claim_cache_dir(), fetch_one(), _fields(), _MemoryS3, _run(), test_a_cache_dir_holds_one_lead() (+11 more)

### Community 63 - "Community 63"
Cohesion: 0.08
Nodes (9): ModelRegistry, test_registry_route_refreshes_a_stale_registry(), test_a_champion_verified_nowhere_serves_no_basin_as_in_distribution(), test_no_champion_or_champions_from_before_the_tag_are_the_atlantic(), _champions_tagged(), test_a_basin_counts_only_when_every_champion_trained_on_it(), test_a_champion_without_the_tag_counts_as_atlantic_only(), test_champion_is_none_with_no_versions_registered() (+1 more)

### Community 64 - "Community 64"
Cohesion: 0.09
Nodes (31): ArchitectureOut, LayerOut, {
		arch,
		onclose,
		class: className = ''
	}, Box, boxFor(), clamp(), color, focus (+23 more)

### Community 65 - "Community 65"
Cohesion: 0.06
Nodes (35): context, dockerfile, postgres, AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY, MLFLOW_S3_ENDPOINT_URL, POSTGRES_DB (+27 more)

### Community 66 - "Community 66"
Cohesion: 0.08
Nodes (25): aggregate_by_storm(), beat_rate(), diebold_mariano(), _normal_cdf(), pair(), test_aggregation_collapses_fixes_to_one_case_per_storm(), test_aggregation_keeps_the_two_arrays_aligned(), test_aggregation_rejects_an_empty_sample() (+17 more)

### Community 67 - "Community 67"
Cohesion: 0.10
Nodes (22): run_fetch_cache(), make_fields(), make_track(), test_default_fetch_fn_wires_a_shared_session(), fake_fetch_gdas_grib2_fields(), fake_gdas_to_gridded_fields(), test_fetch_one_fetches_exactly_one_real_sample(), fake_gdas_to_gridded_fields() (+14 more)

### Community 68 - "Community 68"
Cohesion: 0.12
Nodes (25): LatencyOracle, CycleAbandoned, plan_cycle(), total_budget(), test_a_cycle_started_at_the_timeout_still_clears_the_margin(), test_all_four_daily_cycles_plan_and_meet_their_deadlines(), test_core_is_ready_before_spread(), test_cycle_starts_when_vitals_land_not_at_synoptic_time() (+17 more)

### Community 69 - "Community 69"
Cohesion: 0.11
Nodes (20): fetch_current_storm_ids(), fetch_current_storms(), fetch_live_track(), fetch_live_tracks(), fetch_one(), _get(), LiveAtcfError, test_fetch_current_storm_ids_parses_and_uppercases() (+12 more)

### Community 70 - "Community 70"
Cohesion: 0.09
Nodes (18): QUICK, API, DEVELOP, PHONE, SourceRow, SOURCES, SOURCES_BEFORE_USED_BY, SOURCES_REWIRED (+10 more)

### Community 71 - "Community 71"
Cohesion: 0.06
Nodes (28): AsyncReturnType, Expand, ExtractGenericViewableContent, GenericItem, GenericSelectorOption, GenericSnippetProps, GenericViewableContent, InheritedSnippetProps (+20 more)

### Community 72 - "Community 72"
Cohesion: 0.11
Nodes (20): Hurdat2Error, _parse_data_row(), _parse_header(), parse_hurdat2(), parse_hurdat2_statuses(), _parse_latlon(), _storm_rows(), test_entry_count_mismatch_raises() (+12 more)

### Community 73 - "Community 73"
Cohesion: 0.13
Nodes (15): build_real_deterministic_fn(), InferenceCycleError, cache_current_fix(), _FakeS3Client, make_track(), _register_real_version(), _store(), test_build_real_deterministic_fn_combines_all_four_real_models() (+7 more)

### Community 74 - "Community 74"
Cohesion: 0.06
Nodes (31): data, basins, stage_a, epochs, flavor, input_sources, label_source, learning_rate (+23 more)

### Community 75 - "Community 75"
Cohesion: 0.12
Nodes (17): AvailabilityOracle, earliest_ready_time(), resolve_cycle_inputs(), _valid_time_for(), test_all_nwp_missing_marks_the_required_input_unavailable(), test_cycle_is_not_ready_before_vitals_arrive(), test_cycle_is_ready_once_vitals_and_staged_nwp_are_in(), test_earliest_ready_time_is_driven_by_the_vitals_arrival() (+9 more)

### Community 76 - "Community 76"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, env, GH_TOKEN, GRAPHIFY_VERSION, permissions, runs-on (+22 more)

### Community 77 - "Community 77"
Cohesion: 0.15
Nodes (15): audit_due(), SkewMonitor, SkewReport, sample(), test_audit_becomes_due_once_era5t_lands(), test_audit_is_not_due_immediately_after_the_cycle(), test_intensity_delta_is_signed_toward_the_operational_run(), test_intensity_skew_alone_can_raise_an_alert() (+7 more)

### Community 78 - "Community 78"
Cohesion: 0.09
Nodes (15): storm_basin(), basins_of(), select_basins(), _displacement(), _mean_or_none(), reconcile_official_errors(), _rms(), technique_diagnostics() (+7 more)

### Community 79 - "Community 79"
Cohesion: 0.12
Nodes (13): Fetcher, FetchError, ingest_cycle_inputs(), ingest_one(), IngestionOutcome, IngestionRecord, LakeTier, LakeWriter (+5 more)

### Community 80 - "Community 80"
Cohesion: 0.13
Nodes (16): latent_signature(), RegistryError, full_set(), register_group1(), _stage_all(), test_desynced_derived_models_detects_a_real_champion_change(), test_desynced_derived_models_is_empty_for_a_coherent_set(), test_desynced_derived_models_is_empty_when_no_derived_model_has_a_champion() (+8 more)

### Community 81 - "Community 81"
Cohesion: 0.15
Nodes (14): ModelVersion, Stage, _fake_checkpoint_store(), _reconcile_args(), test_registry_reconcile_dry_run_reports_without_transitioning(), test_registry_reconcile_ignores_nan_metrics(), test_registry_reconcile_never_touches_a_model_with_a_production_version(), test_registry_reconcile_re_stages_the_real_best_existing_version() (+6 more)

### Community 82 - "Community 82"
Cohesion: 0.14
Nodes (18): by_basin(), complete_run(), metric_set(), test_a_basin_is_verified_when_the_model_beats_persistence_there(), test_a_basin_validated_but_never_trained_on_is_not_verified(), test_a_candidate_that_loses_a_verified_basin_is_refused(), test_a_candidate_that_scored_no_basin_is_judged_as_before(), test_a_candidate_verified_in_a_new_basin_may_be_slightly_worse_on_the_reference() (+10 more)

### Community 83 - "Community 83"
Cohesion: 0.08
Nodes (15): _expected_meta(), test_a_failed_time_is_reported_and_the_others_still_written(), fetch(), test_a_lost_race_with_no_file_appearing_raises_the_write_error(), test_cache_round_trip_and_vector(), test_disc_mean_is_symmetric_for_a_field_linear_in_longitude(), test_features_advect_with_the_flow_plus_beta_drift(), test_features_raise_where_there_is_no_flow() (+7 more)

### Community 84 - "Community 84"
Cohesion: 0.08
Nodes (29): better-auth@^1.7.7, @types/node@^26.6.4, typescript@^5.9.3, wrangler@^4.147.0, better-auth, @types/node, typescript, wrangler (+21 more)

### Community 85 - "Community 85"
Cohesion: 0.07
Nodes (23): rehype-slug@^6.0.0, rehype-stringify@^10.0.1, remark-gfm@^4.0.1, remark-parse@^11.0.0, remark-rehype@^11.1.2, unified@^11.0.5, unist-util-visit@^5.1.0, CONSOLE_ROOT (+15 more)

### Community 86 - "Community 86"
Cohesion: 0.07
Nodes (29): WithElementRef, ButtonClickEvent, PrimitiveAnchorAttributes, PrimitiveButtonAttributes, PrimitiveCanvasAttributes, PrimitiveDivAttributes, PrimitiveElementAttributes, PrimitiveFigureAttributes (+21 more)

### Community 87 - "Community 87"
Cohesion: 0.11
Nodes (14): adeck_name(), adeck_path(), AdeckFetchReport, CachedAdecks, _check_adeck(), _check_official_errors(), fetch_adecks(), _fetch_one() (+6 more)

### Community 88 - "Community 88"
Cohesion: 0.09
Nodes (12): color_for(), god(), Module, WindGod, test_every_god_color_is_distinct(), test_experiment_name_handles_fusion_without_raising(), test_experiment_names_are_the_god_slugs(), test_lookup_by_slug_and_by_architecture_agree() (+4 more)

### Community 89 - "Community 89"
Cohesion: 0.13
Nodes (15): build_transformer_samples(), TransformerStageSamples, cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_build_transformer_samples_empty_when_nothing_cached() (+7 more)

### Community 90 - "Community 90"
Cohesion: 0.07
Nodes (28): inputArgs, jobs, projectId, region, results, timeoutSeconds, assign, return (+20 more)

### Community 91 - "Community 91"
Cohesion: 0.13
Nodes (11): cycle_inputs_prefix(), cycle_key(), CycleHistory, _get_text(), load_cycle_result(), load_drift_live(), _put_text(), save_cycle_inputs() (+3 more)

### Community 92 - "Community 92"
Cohesion: 0.11
Nodes (13): crop_to_cnn_input(), generate_satellite_crop(), SatelliteCrop, test_as_dict_maps_channel_names_to_arrays(), test_crop_has_the_declared_channel_count_and_shape(), test_crop_to_cnn_input_adds_a_batch_dimension(), test_non_3d_channels_are_rejected(), test_rain_rate_is_never_negative() (+5 more)

### Community 93 - "Community 93"
Cohesion: 0.17
Nodes (23): build_schedule(), Mode, run_schedule(), RunOutcome, failing_runner(), runner(), ok_runner(), test_both_schedules_validate() (+15 more)

### Community 94 - "Community 94"
Cohesion: 0.10
Nodes (12): archive_key(), ArchiveClient, FetchCacheReport, filter_tracks_by_min_valid_time(), _memo_enabled(), run_fetch_cache(), _work(), sync_cache_to_archive() (+4 more)

### Community 95 - "Community 95"
Cohesion: 0.12
Nodes (15): get(), Role, _model_sources(), test_a_label_or_verification_source_is_never_a_model_input(), test_a_model_input_is_never_a_labels_only_source(), test_each_curriculum_stage_lists_what_its_models_read(), test_era5_is_pretrain_only(), test_era5_latency_is_days_not_hours() (+7 more)

### Community 96 - "Community 96"
Cohesion: 0.10
Nodes (16): build_diffusion(), __init__(), _consistency_model(), test_consistency_accepts_extra_conditioning(), test_consistency_boundary_condition_is_exact_at_step_zero(), test_consistency_multistep_sampling_matches_one_step_shape_and_is_deterministic(), test_consistency_one_step_sampling_produces_distinct_members(), test_diffusion_accepts_extra_conditioning() (+8 more)

### Community 97 - "Community 97"
Cohesion: 0.16
Nodes (17): AblationReport, _cell(), make_track(), test_at_fraction_filters_and_sorts_by_hidden_dim(), test_build_samples_augmentation_multiplies_sample_count(), test_build_samples_shapes_match_sequence_length_and_columns(), test_build_samples_skips_storms_shorter_than_required(), test_build_samples_wind_label_uses_final_track_not_the_noisy_working_input() (+9 more)

### Community 98 - "Community 98"
Cohesion: 0.11
Nodes (15): adeck_text(), adecks(), archive(), archive_text(), cases(), _row(), _row_of(), storm_text() (+7 more)

### Community 99 - "Community 99"
Cohesion: 0.12
Nodes (16): __init__(), extra_channel_patch(), __init__(), expand_patch_channels(), cache_all_fixes(), _cache_steering(), make_track(), test_compare_refuses_arms_on_different_windows_and_pairs_the_rest() (+8 more)

### Community 100 - "Community 100"
Cohesion: 0.15
Nodes (12): record_operational_cycle(), _FakeClient, _fix(), _make_output(), _record(), test_audit_run_degrades_per_record_when_audit_one_raises(), test_audit_run_replays_only_due_records_and_persists_the_result(), test_audit_run_takes_a_bounded_batch_oldest_first() (+4 more)

### Community 101 - "Community 101"
Cohesion: 0.10
Nodes (8): build_derived_schedule(), _latent_task(), ResourceProfile, Schedule, _train_task(), validate_schedule(), Wave, test_derived_schedule_retrains_no_group1_model()

### Community 102 - "Community 102"
Cohesion: 0.08
Nodes (9): _FakeMlflowModelVersion, _mlflow_client_that_registers_and_transitions(), create_model_version(), test_mlflow_mirror_skips_create_registered_model_if_it_already_exists(), create_model_version(), test_mlflow_transition_also_mirrors_the_archived_incumbent(), create_model_version(), test_register_persists_locally_and_durably_before_touching_mlflow() (+1 more)

### Community 103 - "Community 103"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GH_TOKEN, IMPORTED_FROM, SOURCE_SHA, jobs, publish (+16 more)

### Community 104 - "Community 104"
Cohesion: 0.12
Nodes (12): _cron_run_offset_minutes(), _leaves(), _load(), test_a_config_change_redeploys_the_api(), test_both_images_copy_the_configs(), test_every_config_key_is_read_by_the_code(), test_every_config_parses_and_has_no_duplicate_keys(), test_every_image_build_is_smoke_tested_before_it_ships() (+4 more)

### Community 105 - "Community 105"
Cohesion: 0.14
Nodes (14): fetch_and_parse_ndbc(), fetch_ndbc_realtime2(), _get(), NdbcFetchError, NdbcObservation, parse_ndbc_realtime2(), test_a_row_with_the_wrong_column_count_is_skipped_not_fatal(), test_a_station_missing_wave_columns_still_parses() (+6 more)

### Community 106 - "Community 106"
Cohesion: 0.08
Nodes (3): client(), test_more_members_than_the_ensemble_runs_is_refused_not_silently_capped(), test_sources_say_who_uses_each_one()

### Community 107 - "Community 107"
Cohesion: 0.15
Nodes (12): cache_current_fix(), _FakeS3Client, make_track(), _register(), _register_all_five_and_diffusion(), _store(), test_build_real_ensemble_fn_produces_real_finite_members(), test_build_real_ensemble_fn_raises_without_all_five_models() (+4 more)

### Community 108 - "Community 108"
Cohesion: 0.15
Nodes (14): _all_tensors(), Architecture, _builder(), describe(), describe_cached(), _describe_cached(), hook(), _example_inputs() (+6 more)

### Community 109 - "Community 109"
Cohesion: 0.14
Nodes (17): adeck_urls(), _adeck_positive(), parse_adeck(), _archive(), _errors_url(), _FakeNhc, test_fetch_adecks_does_not_cache_a_body_that_is_not_the_file(), test_fetch_adecks_never_runs_more_than_four_requests() (+9 more)

### Community 110 - "Community 110"
Cohesion: 0.16
Nodes (16): archive_atcf(), _fetcher(), fetch(), _keys(), test_a_storm_is_still_archived_for_a_few_days_after_it_leaves_the_index(), test_a_storm_seen_on_new_years_eve_is_still_followed_on_new_years_day(), test_an_unreachable_index_raises_so_the_caller_reports_it(), test_archived_tcvitals_keeps_every_revision_once_in_issue_order() (+8 more)

### Community 111 - "Community 111"
Cohesion: 0.12
Nodes (14): http_get(), OhcFetchError, OhcNotPublished, Archive, test_a_cut_off_reply_is_a_fetch_failure(), test_a_cut_off_transfer_raises_rather_than_reading_an_older_file(), test_a_fetch_failure_that_is_not_a_404_is_not_stepped_over(), flaky() (+6 more)

### Community 112 - "Community 112"
Cohesion: 0.13
Nodes (9): App, Locals, Platform, DEFAULT_EXTRA, ExtraPreferences, PackageManager, UserContext, UserIdentity (+1 more)

### Community 113 - "Community 113"
Cohesion: 0.17
Nodes (12): accessed(), _check_type(), config_dir(), ConfigError, fixed(), get(), get_list(), _load() (+4 more)

### Community 114 - "Community 114"
Cohesion: 0.12
Nodes (12): generate_season(), make_storm_spec(), StormSpec, test_archive_spans_the_requested_seasons(), test_fields_have_matching_shapes_and_carry_a_flavor(), test_fixes_are_six_hourly_and_synoptic(), test_gdas_fields_are_noisier_than_era5(), test_generated_tracks_are_final_quality() (+4 more)

### Community 115 - "Community 115"
Cohesion: 0.20
Nodes (15): evaluate_promotion(), complete_run(), good_metrics(), test_candidate_worse_than_incumbent_is_not_staged(), test_era5_flavor_metrics_cannot_gate_promotion(), test_first_candidate_is_staged(), test_missing_metric_is_reported_as_a_failure(), test_non_finite_candidate_does_not_beat_an_incumbent_either() (+7 more)

### Community 116 - "Community 116"
Cohesion: 0.15
Nodes (14): _fake_checkpoint_store(), make_track(), test_a_run_on_two_basins_scores_each_on_its_own(), test_build_stage_samples_drops_a_track_too_short_for_any_lead(), test_build_stage_samples_full_length_track_covers_every_lead(), test_build_stage_samples_masked_entries_are_recoverable_positions(), test_build_stage_samples_masks_leads_beyond_a_short_track(), test_displacement_to_latlon_is_a_noop_for_zero_displacement() (+6 more)

### Community 117 - "Community 117"
Cohesion: 0.14
Nodes (16): cache_steering(), _fields(), make_track(), test_latents_need_a_steering_cache_for_a_steering_transformer(), test_live_steering_is_none_before_the_gfs_archive(), test_live_steering_is_none_when_any_lead_is_missing(), fetcher(), test_live_steering_matches_the_training_features_and_is_cached() (+8 more)

### Community 118 - "Community 118"
Cohesion: 0.17
Nodes (12): group_by_time(), load_steering(), run_steering_cache(), fetch(), one_time(), save_steering(), shard_times(), steering_path() (+4 more)

### Community 119 - "Community 119"
Cohesion: 0.14
Nodes (11): _files(), localize_cache(), LocalizeReport, _raise(), _cache(), test_a_directory_that_cant_be_listed_fails_the_copy(), test_a_missing_source_raises(), test_a_rerun_only_fills_gaps() (+3 more)

### Community 120 - "Community 120"
Cohesion: 0.09
Nodes (8): DELETE, GET, PATCH, POST, PUT, { data }, prerender, ssr

### Community 121 - "Community 121"
Cohesion: 0.16
Nodes (9): fetch_gefs_ensemble_grib2_fields(), fetch_gefs_member_grib2_fields(), _gefs_member_url(), require_gdas_deps(), test_control_member_zero_uses_gec00_not_gep00(), test_fetch_gefs_ensemble_reads_multiple_real_distinct_members(), test_fetch_gefs_member_reads_the_real_noaa_archive(), test_member_out_of_range_raises() (+1 more)

### Community 122 - "Community 122"
Cohesion: 0.19
Nodes (12): assemble_validation_forecasts(), BaselineBacktestError, format_forecast_check(), model_members(), ValidationForecasts, _latents(), _registered(), test_a_case_without_a_model_forecast_is_excluded_and_counted() (+4 more)

### Community 123 - "Community 123"
Cohesion: 0.14
Nodes (10): lr_factor(), transformer_optim(), TransformerOptim, TransformerOptimizer, test_a_short_stage_still_ends_on_the_floor(), test_config_values_are_validated(), test_cosine_decays_to_the_floor_on_the_last_update(), test_no_warmup_starts_at_the_peak() (+2 more)

### Community 124 - "Community 124"
Cohesion: 0.10
Nodes (20): PROJECT_NUMBER, PROJECT_PAT, types, jobs, sync, name, on, issues (+12 more)

### Community 125 - "Community 125"
Cohesion: 0.13
Nodes (8): calibration_out(), drift_report_out(), skew_report_out(), calibration(), drift(), drift_all(), skew(), DriftReport

### Community 126 - "Community 126"
Cohesion: 0.21
Nodes (6): freeCycleLabel(), label(), runFreshCycle(), signIn(), cases, @playwright/test

### Community 127 - "Community 127"
Cohesion: 0.16
Nodes (17): answerRuns(), chip(), context(), cycleFor(), dateButton(), expectForm(), expectShowing(), fixture (+9 more)

### Community 128 - "Community 128"
Cohesion: 0.15
Nodes (10): read_cached_official_errors(), OfficialErrorsError, parse_official_errors(), _signed(), test_a_cached_error_file_that_is_not_nhcs_is_named_with_the_way_out(), test_parse_official_errors_reads_columns_by_name_and_skips_missing_leads(), test_parse_official_errors_reads_the_stated_initial_position_domain(), test_parse_official_errors_rejects_a_file_without_the_column_header() (+2 more)

### Community 129 - "Community 129"
Cohesion: 0.19
Nodes (15): run_fetch_cache(), make_fields(), make_track(), test_build_fetch_tasks_covers_every_fix_across_tracks(), test_load_cached_fields_rejects_a_missing_file(), test_run_fetch_cache_actually_runs_fetches_concurrently(), slow_fetch(), test_run_fetch_cache_can_force_refetch_with_skip_existing_false() (+7 more)

### Community 130 - "Community 130"
Cohesion: 0.15
Nodes (10): _attributes(), _calls(), _function(), _imported(), _names_adapter(), _parameters(), _parse(), _string_literals() (+2 more)

### Community 131 - "Community 131"
Cohesion: 0.11
Nodes (7): client(), test_docs_route_is_unaffected(), test_sources_role_is_the_role_enum_in_the_openapi_schema(), test_sources_used_by_is_documented_in_the_openapi_schema(), test_theme_http_method_colors_are_distinct(), test_theme_never_uses_a_god_color(), _walk()

### Community 132 - "Community 132"
Cohesion: 0.17
Nodes (7): mlflow_client_from_env(), test_an_unreachable_server_is_skipped_fast(), test_builds_a_real_client_when_tracking_uri_is_set(), test_fail_fast_settings_never_override_explicit_ones(), test_mlflow_client_from_env_can_actually_reach_the_configured_server(), test_returns_none_when_tracking_uri_is_unset(), test_returns_none_without_mlflow_installed()

### Community 133 - "Community 133"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 134 - "Community 134"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 135 - "Community 135"
Cohesion: 0.12
Nodes (8): god_out(), model_catalog(), source_out(), health(), models(), sources(), DataSource, pretrain_only_sources()

### Community 136 - "Community 136"
Cohesion: 0.15
Nodes (6): CloudflareAccessRequestHeaderProvider, test_headers_are_actually_applied_by_mlflows_own_resolution(), test_in_context_false_when_neither_var_set(), test_in_context_false_when_only_client_id_set(), test_in_context_true_and_correct_headers_when_both_set(), test_registered_as_a_real_mlflow_plugin_via_entry_points()

### Community 137 - "Community 137"
Cohesion: 0.12
Nodes (4): _Boto3Client, require_boto3(), _StorageClient, test_boto3_adapter_configures_the_client_for_the_given_endpoint()

### Community 138 - "Community 138"
Cohesion: 0.12
Nodes (16): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+8 more)

### Community 139 - "Community 139"
Cohesion: 0.12
Nodes (16): compilerOptions, allowJs, allowSyntheticDefaultImports, checkJs, forceConsistentCasingInFileNames, isolatedModules, lib, module (+8 more)

### Community 140 - "Community 140"
Cohesion: 0.12
Nodes (16): permissions, runs-on, steps, jobs, copilot-setup-steps, name, on, pull_request (+8 more)

### Community 141 - "Community 141"
Cohesion: 0.15
Nodes (9): config_copy(), edit(), _image_layout(), _run(), test_a_missing_config_dir_is_refused(), test_an_image_without_configs_fails_at_import_and_says_why(), test_an_invalid_config_is_refused_with_a_clear_message(), test_edited_values_take_effect_at_runtime() (+1 more)

### Community 142 - "Community 142"
Cohesion: 0.19
Nodes (10): ArchiveReport, currentstorms_key(), _digest(), _get_text(), _load_recent(), _put_bytes(), snapshot_key(), _stored_digests() (+2 more)

### Community 143 - "Community 143"
Cohesion: 0.18
Nodes (7): assert_flavor(), FeatureSet, FlavorMismatchError, Normalizer, test_flavor_guard_rejects_a_pretrain_feature_on_the_operational_path(), test_normalizer_refuses_to_fit_across_flavors(), test_normalizer_rejects_the_wrong_flavor_at_apply_time()

### Community 144 - "Community 144"
Cohesion: 0.15
Nodes (6): _aligned(), _join(), _json_rows(), _notes(), _rounded(), ValidationCases

### Community 145 - "Community 145"
Cohesion: 0.16
Nodes (7): al_2021_2022(), compare(), open_ocean(), parse_ships(), sample_days(), ShipsCase, test_sohc_equals_bilinear_ohc_on_the_file_named_for_the_day_before()

### Community 146 - "Community 146"
Cohesion: 0.12
Nodes (16): with, build-args, cache-from, cache-to, context, file, load, password (+8 more)

### Community 147 - "Community 147"
Cohesion: 0.12
Nodes (15): jobs, lint-and-validate, name, permissions, runs-on, steps, name, on (+7 more)

### Community 148 - "Community 148"
Cohesion: 0.16
Nodes (7): _bilinear(), _lattice_index(), ohc_at(), OhcField, test_a_blank_run_longer_than_the_window_leaves_na_unavailable(), test_a_degraded_basin_flags_the_field(), test_ohc_global_places_both_basins_and_reports_where_they_came_from()

### Community 149 - "Community 149"
Cohesion: 0.13
Nodes (5): collect_validation_forecasts(), dump_validation_forecasts(), group1_versions_of(), test_an_extra_version_is_loaded_from_its_registry_entry(), test_group1_versions_come_from_the_latent_signature()

### Community 150 - "Community 150"
Cohesion: 0.13
Nodes (15): scripts, build, cf:deploy, check, check:errors, check:warnings, check:watch, dev (+7 more)

### Community 151 - "Community 151"
Cohesion: 0.19
Nodes (12): loading, onInput(), open, query, results, bodyById, buildIndex(), excerptAround() (+4 more)

### Community 152 - "Community 152"
Cohesion: 0.13
Nodes (15): env, environment, if, name, needs, permissions, runs-on, timeout-minutes (+7 more)

### Community 153 - "Community 153"
Cohesion: 0.26
Nodes (9): detect_feature_drift(), FeatureDrift, reference(), test_collapsed_variance_is_detected(), test_feature_count_mismatch_raises(), test_matching_distribution_shows_no_drift(), test_shifted_mean_is_detected(), test_summary_names_the_worst_feature() (+1 more)

### Community 154 - "Community 154"
Cohesion: 0.19
Nodes (9): cmd_baseline_backtest(), _fmt(), format_report(), RegisteredError, run_baseline_backtest(), _sample_gap(), report(), test_registered_error_spec() (+1 more)

### Community 155 - "Community 155"
Cohesion: 0.16
Nodes (5): _declared_length(), _grid_values(), OhcFile, _read_checked(), StepBack

### Community 156 - "Community 156"
Cohesion: 0.17
Nodes (10): scored_basins(), scored(), validation_metrics(), _forecasts(), test_a_runs_validation_metrics_carry_the_overall_and_each_basin(), test_a_storm_id_per_sample_is_required(), test_each_basin_is_scored_on_its_own_storms(), test_nothing_verifiable_is_an_error_naming_the_stage() (+2 more)

### Community 157 - "Community 157"
Cohesion: 0.10
Nodes (5): _MemoryS3Client, test_a_stale_refresh_in_flight_serves_known_storms_without_waiting(), test_demo_state_is_unaffected_by_default(), test_real_state_monitoring_and_retraining_routes_do_not_500(), test_the_storm_routes_refresh_the_registry_before_reading_coverage()

### Community 158 - "Community 158"
Cohesion: 0.14
Nodes (13): compilerOptions, allowJs, checkJs, esModuleInterop, forceConsistentCasingInFileNames, moduleResolution, resolveJsonModule, rewriteRelativeImportExtensions (+5 more)

### Community 159 - "Community 159"
Cohesion: 0.14
Nodes (13): images, options, diskSizeGb, machineType, steps, args, entrypoint, env (+5 more)

### Community 160 - "Community 160"
Cohesion: 0.14
Nodes (14): default, description, type, default, description, type, api, console (+6 more)

### Community 161 - "Community 161"
Cohesion: 0.19
Nodes (11): ohc_url(), _full_archive(), test_a_missing_file_steps_back_one_creation_day(), test_an_unknown_basin_leaves_the_field_unknown_unless_another_is_degraded(), test_no_url_before_the_archive_or_for_another_basin(), test_stepping_back_stops_after_the_stated_maximum(), test_the_baseline_reads_six_earlier_files_and_nothing_newer(), test_the_baseline_skips_missing_and_rejected_days_and_needs_three() (+3 more)

### Community 162 - "Community 162"
Cohesion: 0.19
Nodes (4): _download(), fetch_oisst_sst(), require_sst_deps(), SstFetchError

### Community 163 - "Community 163"
Cohesion: 0.15
Nodes (3): ModelSpec, __getattr__(), test_spec_output_dim_is_leads_times_outputs()

### Community 164 - "Community 164"
Cohesion: 0.27
Nodes (7): technique_member(), techniques_to_read(), TechniqueSpec, test_a_case_without_an_adeck_has_no_technique_forecast(), test_a_lagged_member_reads_the_earlier_run_at_the_same_valid_time(), test_technique_specs(), test_the_official_member_prefers_the_regular_advisory()

### Community 165 - "Community 165"
Cohesion: 0.35
Nodes (7): NoiseSensitivityReport, _result(), test_is_load_bearing_above_threshold(), test_is_not_load_bearing_below_threshold(), test_relative_change_is_zero_when_losses_match(), test_relative_change_rejects_nonpositive_default_loss(), test_relative_change_sign_matches_direction_of_the_move()

### Community 166 - "Community 166"
Cohesion: 0.17
Nodes (12): IdTokenClaims, JwtClaims, OidcAddressClaim, OidcStandardClaims, UserProfile, Mandatory, RFC-3966, RFC-4627 (+4 more)

### Community 167 - "Community 167"
Cohesion: 0.18
Nodes (7): client(), test_a_registered_versions_arch_params_are_used(), test_a_version_without_arch_params_is_described_from_defaults(), test_a_versions_arch_params_change_what_is_described(), test_every_model_runs_its_example_input_and_reports_its_layers(), test_the_gnn_is_fed_the_real_lattice(), test_unknown_models_and_versions_are_404()

### Community 168 - "Community 168"
Cohesion: 0.15
Nodes (12): name, runs-on, timeout-minutes, concurrency, cancel-in-progress, group, jobs, build (+4 more)

### Community 169 - "Community 169"
Cohesion: 0.21
Nodes (7): build_consistency_model(), consistency_fn(), __init__(), sample(), skip_coeffs(), _cosine_schedule(), test_consistency_rejects_a_non_positive_step_count()

### Community 170 - "Community 170"
Cohesion: 0.27
Nodes (6): PromotionError, TestSetBudget, test_budget_allows_a_limited_number_of_looks(), test_budget_exhaustion_raises(), test_budget_requires_a_justification(), test_budget_resets_across_seasons()

### Community 171 - "Community 171"
Cohesion: 0.17
Nodes (6): _called(), _modules(), test_an_adapter_is_named_by_other_code_only_if_its_source_is_read(), test_every_fetch_adapter_is_classified(), test_no_module_imports_by_a_computed_name(), _unread_sources()

### Community 172 - "Community 172"
Cohesion: 0.23
Nodes (11): max, target, budgets, reduced, standard, max, target, assembly (+3 more)

### Community 173 - "Community 173"
Cohesion: 0.17
Nodes (4): local, notes, problems, remote

### Community 174 - "Community 174"
Cohesion: 0.17
Nodes (11): concurrency, cancel-in-progress, group, jobs, test-api, name, if, name (+3 more)

### Community 175 - "Community 175"
Cohesion: 0.17
Nodes (12): with, cache, cache-dependency-path, enable-cache, fetch-depth, if-no-files-found, include-hidden-files, name (+4 more)

### Community 176 - "Community 176"
Cohesion: 0.21
Nodes (6): disc_mean(), fetch_lead_flow(), lead_flow(), LeadFlow, steering_features(), steering_targets()

### Community 177 - "Community 177"
Cohesion: 0.24
Nodes (9): build_lstm(), encode(), forward(), __init__(), test_train_lstm_stage_reduces_loss_over_epochs(), test_train_lstm_stage_streaming_batch_size_does_not_change_final_metrics_much(), test_train_lstm_stage_streaming_reduces_loss_and_produces_val_metrics(), testfreeze_encoder_is_a_noop_without_encoder_in_frozen_modules() (+1 more)

### Community 178 - "Community 178"
Cohesion: 0.18
Nodes (11): cycle, advisory_margin_minutes, advisory_offset_minutes, allow_estimated_vitals, allow_load_shedding, max_nwp_lag_hours, nominal_vitals_offset_minutes, nwp_lag_hours (+3 more)

### Community 179 - "Community 179"
Cohesion: 0.27
Nodes (6): sst_at(), _small_grid(), test_fetch_oisst_sst_reads_real_recent_data(), test_sst_at_finds_the_nearest_cell(), test_sst_at_normalises_negative_longitude_to_0_360(), test_sst_at_returns_nan_over_a_real_missing_cell()

### Community 180 - "Community 180"
Cohesion: 0.25
Nodes (6): get_cycle(), get_storm(), list_storms(), _served_basins(), _storm_summary(), FixOut

### Community 182 - "Community 182"
Cohesion: 0.22
Nodes (7): assert_not_operational(), operational_sources(), _operational_substitute(), OperationalUseError, test_operational_sources_pass_the_guard(), test_reading_era5_in_the_inference_path_is_refused(), test_reading_final_besttrack_in_the_inference_path_is_refused()

### Community 183 - "Community 183"
Cohesion: 0.22
Nodes (6): first_record_of_year(), ships_al_url(), _ships_get(), ships_record_year(), ships_size(), ships_window()

### Community 184 - "Community 184"
Cohesion: 0.20
Nodes (10): limit, lower_is_better, limit, lower_is_better, thresholds, intensity_error_48h_kt, intensity_error_72h_kt, track_error_72h_nm (+2 more)

### Community 185 - "Community 185"
Cohesion: 0.20
Nodes (10): steps, EXPECT_GIT_SHA, GCP_CI_SERVICE_ACCOUNT, GCP_WIF_PROVIDER, env, id, if, name (+2 more)

### Community 186 - "Community 186"
Cohesion: 0.20
Nodes (10): name, outputs, runs-on, timeout-minutes, changes, deploy_api, deploy_console, plan (+2 more)

### Community 187 - "Community 187"
Cohesion: 0.40
Nodes (10): steps, steps, id, if, name, run, uses, working-directory (+2 more)

### Community 188 - "Community 188"
Cohesion: 0.27
Nodes (5): deterministic(), cmd_cycle(), deterministic(), climatological_ensemble(), DeterministicForecast

### Community 189 - "Community 189"
Cohesion: 0.27
Nodes (4): ChecksumCheck, FetchResult, NonEmptyCheck, QCFinding

### Community 190 - "Community 190"
Cohesion: 0.27
Nodes (3): BasinChoice, test_a_cycle_reads_the_file_made_two_days_before(), test_the_flag_on_real_files()

### Community 191 - "Community 191"
Cohesion: 0.20
Nodes (7): used_by(), test_cmd_sources_prints_who_uses_each_source(), test_a_verification_source_not_read_yet_is_verification_and_nothing_else(), test_every_required_cycle_input_has_a_model_consumer(), test_used_by_follows_the_contract_order_for_every_source(), test_used_by_per_source(), test_used_by_refuses_an_unknown_source()

### Community 192 - "Community 192"
Cohesion: 0.29
Nodes (5): ValidationLossMonitor, test_a_recovery_resets_the_consecutive_count(), test_first_observation_only_sets_the_baseline(), test_increases_below_the_threshold_never_trigger(), test_trigger_requires_three_consecutive_breaches()

### Community 193 - "Community 193"
Cohesion: 0.22
Nodes (9): run, test-console, working-directory, defaults, if, name, needs, runs-on (+1 more)

### Community 194 - "Community 194"
Cohesion: 0.22
Nodes (9): BASE_SHA, BEFORE_SHA, DISPATCH_API, DISPATCH_CONSOLE, EVENT, EXPECT_GIT_SHA, HEAD_SHA, REF (+1 more)

### Community 195 - "Community 195"
Cohesion: 0.25
Nodes (6): assert_operational_flavor(), CycleError, fusion_weights(), test_fusion_weights_favour_the_lower_error_model(), test_fusion_weights_never_zero_a_model_out(), test_operational_flavor_guard_rejects_pretrain_features()

### Community 196 - "Community 196"
Cohesion: 0.25
Nodes (6): build_fusion(), forward(), __init__(), weights(), test_fusion_rejects_the_wrong_number_of_models(), test_fusion_weights_are_normalised_and_floored()

### Community 198 - "Community 198"
Cohesion: 0.22
Nodes (4): test_mlflow_mirror_is_skipped_without_a_checkpoint_uri(), __getattr__(), test_mlflow_mirror_registers_model_then_version_with_a_real_source_uri(), create_model_version()

### Community 199 - "Community 199"
Cohesion: 0.28
Nodes (4): oracle(), pytest_collection_modifyitems(), target_time(), worst_case_oracle()

### Community 200 - "Community 200"
Cohesion: 0.22
Nodes (3): test_cmd_train_schedule_derived_from_champions_seeds_and_runs_derived_only(), fake_run_schedule(), test_retrain_check_dispatches_the_real_schedule_when_a_trigger_fires()

### Community 201 - "Community 201"
Cohesion: 0.25
Nodes (8): 12, 120, 24, 36, 48, 72, 96, climatological_cone_nm

### Community 202 - "Community 202"
Cohesion: 0.25
Nodes (8): CP, 12, 120, 24, 36, 48, 72, 96

### Community 203 - "Community 203"
Cohesion: 0.25
Nodes (8): EP, 12, 120, 24, 36, 48, 72, 96

### Community 204 - "Community 204"
Cohesion: 0.25
Nodes (7): calibration_audit, cone_nominal_rate, intensity_nominal_rate, min_cases, verdict_margin, test_set_budget, max_evaluations_per_season

### Community 205 - "Community 205"
Cohesion: 0.25
Nodes (8): drift, min_samples, reference_flavor, shift_sigma, validation_loss, variance_ratio_limit, consecutive_required, threshold_fraction

### Community 206 - "Community 206"
Cohesion: 0.25
Nodes (8): promotion, flavor, new_basin_tolerance, primary_metric, reference_basin, require_manual_gate, split, basins()

### Community 210 - "Community 210"
Cohesion: 0.36
Nodes (4): cache_all_fixes(), make_fields(), _task_for(), test_extract_joint_latents_rejects_missing_group1_model()

### Community 211 - "Community 211"
Cohesion: 0.29
Nodes (7): products, cone_percentile, landfall_threshold_nm, lead_hours, ri_alert_probability, ri_threshold_kt, ri_window_hours

### Community 212 - "Community 212"
Cohesion: 0.29
Nodes (7): skew_audit, alert_intensity_delta_kt, alert_track_delta_nm, audit_delay_days, lead_hours, min_samples, window_days

### Community 213 - "Community 213"
Cohesion: 0.57
Nodes (5): deploy-plan.sh script, touches(), touches_component(), touches_console(), why

### Community 214 - "Community 214"
Cohesion: 0.29
Nodes (7): env, IMAGE, JOB, PROJECT_ID, PUBLISH, REGION, REGISTRY

### Community 215 - "Community 215"
Cohesion: 0.33
Nodes (3): coriolis_parameter(), physics_residuals(), test_physics_residuals_penalise_impossible_motion()

### Community 216 - "Community 216"
Cohesion: 0.29
Nodes (3): SkewSample, flaky_audit_one(), fake_audit_one()

### Community 218 - "Community 218"
Cohesion: 0.29
Nodes (4): _FakeJointLatents, fake_extract_joint_latents(), test_diffusion_forwards_dropout_and_weight_decay_to_the_real_trainer(), fake_run_diffusion_curriculum()

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
Cohesion: 0.33
Nodes (6): update_job, workflow_dispatch, default, description, type, inputs

### Community 225 - "Community 225"
Cohesion: 0.33
Nodes (6): on, pull_request, push, paths, branches, paths

### Community 227 - "Community 227"
Cohesion: 0.33
Nodes (3): _get(), _get_bytes(), NotPublished

### Community 228 - "Community 228"
Cohesion: 0.47
Nodes (3): Threshold, _thresholds(), test_beat_rate_threshold_is_higher_is_better()

### Community 230 - "Community 230"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 231 - "Community 231"
Cohesion: 0.40
Nodes (3): WORLD_GEOJSON, WorldData, WorldFeatureProperties

### Community 232 - "Community 232"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 234 - "Community 234"
Cohesion: 0.40
Nodes (3): fetch_grib2_messages(), _parse_grib2_index(), test_parse_grib2_index_gives_contiguous_byte_ranges()

### Community 236 - "Community 236"
Cohesion: 0.67
Nodes (4): max, target, diffusion, diffusion

### Community 237 - "Community 237"
Cohesion: 0.67
Nodes (4): max, target, fusion, fusion

### Community 238 - "Community 238"
Cohesion: 0.67
Nodes (4): max, target, postprocess, postprocess

### Community 239 - "Community 239"
Cohesion: 0.67
Nodes (4): max, target, preprocess, preprocess

### Community 240 - "Community 240"
Cohesion: 0.50
Nodes (3): ANEMOI_FIELDS_MEMO, ANEMOI_STEERING_CACHE_DIR, entrypoint.sh script

### Community 241 - "Community 241"
Cohesion: 0.83
Nodes (3): graphify(), normalise_graph(), build-graph.sh script

### Community 242 - "Community 242"
Cohesion: 0.50
Nodes (3): uvx, graphify, graphify-mcp

### Community 246 - "Community 246"
Cohesion: 0.50
Nodes (3): boundaries_for_flavor(), test_boundaries_for_flavor_picks_default_for_era5_pretrain(), test_boundaries_for_flavor_picks_stage_b_for_gdas_finetune()

### Community 248 - "Community 248"
Cohesion: 0.67
Nodes (3): limit, lower_is_better, nhc_consensus_beat_rate_48h

### Community 249 - "Community 249"
Cohesion: 0.67
Nodes (3): track_error_120h_nm, limit, lower_is_better

### Community 250 - "Community 250"
Cohesion: 0.67
Nodes (3): track_error_48h_nm, limit, lower_is_better

## Knowledge Gaps
- **14 isolated node(s):** `$lib/registry/blocks/navigation/components/site.context.svelte`, `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627`, `RFC-5322` (+9 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2823 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Flavor` connect `Community 33` to `Community 0`, `Community 129`, `Community 3`, `Community 4`, `Community 5`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 14`, `Community 143`, `Community 15`, `Community 18`, `Community 22`, `Community 24`, `Community 153`, `Community 26`, `Community 28`, `Community 156`, `Community 29`, `Community 35`, `Community 36`, `Community 37`, `Community 38`, `Community 167`, `Community 40`, `Community 41`, `Community 42`, `Community 43`, `Community 48`, `Community 177`, `Community 49`, `Community 53`, `Community 55`, `Community 57`, `Community 62`, `Community 63`, `Community 195`, `Community 67`, `Community 197`, `Community 198`, `Community 200`, `Community 73`, `Community 80`, `Community 81`, `Community 82`, `Community 210`, `Community 88`, `Community 89`, `Community 94`, `Community 95`, `Community 99`, `Community 102`, `Community 235`, `Community 107`, `Community 113`, `Community 114`, `Community 115`, `Community 116`, `Community 117`, `Community 246`, `Community 122`, `Community 125`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 252 inferred relationships involving `Flavor` (e.g. with `DemoState` and `drift()`) actually correct?**
  _`Flavor` has 252 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$lib/registry/blocks/navigation/components/site.context.svelte`, `./.svelte-kit/tsconfig.json`, `RFC-3966` to the rest of the system?**
  _14 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.046010483401281305 - nodes in this community are weakly interconnected._
- **Why does `CheckpointStore` connect `Community 0` to `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 10`, `Community 142`, `Community 17`, `Community 149`, `Community 24`, `Community 29`, `Community 35`, `Community 38`, `Community 42`, `Community 43`, `Community 48`, `Community 49`, `Community 55`, `Community 57`, `Community 61`, `Community 73`, `Community 89`, `Community 91`, `Community 100`, `Community 107`, `Community 110`, `Community 116`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 140 inferred relationships involving `Track` (e.g. with `save_cycle_inputs()` and `StormState`) actually correct?**
  _`Track` has 140 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.03050704818009678 - nodes in this community are weakly interconnected._