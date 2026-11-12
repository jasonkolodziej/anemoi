# Graph Report - anemoi  (2026-11-12)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 5964 nodes · 15059 edges · 224 communities (202 shown, 22 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 2289 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c2c23208`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

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
- Community 215
- Community 216
- Community 217
- Community 218
- Community 219
- Community 220
- Community 221
- Community 222
- Community 223

## God Nodes (most connected - your core abstractions)
1. `Flavor` - 269 edges
2. `Track` - 174 edges
3. `Fix` - 135 edges
4. `ModelRegistry` - 130 edges
5. `CheckpointStore` - 124 edges
6. `TrackQuality` - 101 edges
7. `require_torch()` - 97 edges
8. `MetricSet` - 81 edges
9. `LatencyOracle` - 68 edges
10. `RealState` - 63 edges

## Surprising Connections (you probably didn't know these)
- `test_internal_calibration_audit_route_reports_new_samples()` --uses--> `RealState`  [INFERRED]
  tests/test_api_real_state.py → src/anemoi/api/real_state.py
- `make_fix()` --calls--> `Fix`  [INFERRED]
  tests/test_streaming.py → src/anemoi/data/besttrack.py
- `make_fix()` --calls--> `Fix`  [INFERRED]
  tests/test_streaming.py → src/anemoi/data/besttrack.py
- `test_a_versions_arch_params_change_what_is_described()` --calls--> `describe()`  [INFERRED]
  tests/test_model_architecture.py → src/anemoi/models/architecture.py
- `test_the_gnn_is_fed_the_real_lattice()` --calls--> `describe()`  [INFERRED]
  tests/test_model_architecture.py → src/anemoi/models/architecture.py

## Import Cycles
- None detected.

## Communities (224 total, 22 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (37): WorkingTrackNoise, basin_one_hot(), with_basin_channels(), with_basin_columns(), with_basin_vector(), get_device(), _displacement_to_absolute(), _empty_samples() (+29 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (53): apply_cold_wake(), area_mean(), assert_flavor(), cold_wake_sst_depression_c(), compare_potential_intensity_estimates(), compute_environment_features(), deep_layer_shear(), emanuel_potential_intensity() (+45 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (53): ModelSpec, require_torch(), torch_available(), build_consistency_model(), consistency_fn(), __init__(), sample(), skip_coeffs() (+45 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (76): ApiError, apiFetch(), getActivePin(), getArchitecture(), getCalibration(), getDrift(), getDriftAll(), getModelRegistry() (+68 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (45): Fix, Track, _build_live_x(), build_live_cnn_x(), build_live_gnn_x(), build_live_lstm_x(), build_live_pinn_x(), build_live_transformer_x() (+37 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (52): basin_value(), trained_basins(), verified_basins(), resolve_basin_inputs(), served_columns(), assert_deployable(), Curriculum, CurriculumError (+44 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (52): guards, handle, Props, Section, SectionPage, { sections }, height, motionClass (+44 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (64): getCycle(), getStorm(), runCycle(), at(), calendarValue, hour, hourAllowed, inRange() (+56 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (41): CycleResult, IntensityPercentiles, haversine_nm(), audit_cycle(), audit_due(), audit_storm(), _audited_key(), calibrate_products() (+33 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (45): basin_tags(), evaluate_promotion(), PromotionError, TestSetBudget, Threshold, _thresholds(), by_basin(), complete_run() (+37 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (14): cycle_payload_out(), cycle_products_out(), cycle_result_out(), provenance_out(), RealState, deterministic(), live_fields(), RealStormState (+6 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (33): ensemble(), DeterministicForecast, basin_inputs(), _build_live_context(), build_real_deterministic_fn(), deterministic_fn(), _compute_env_features(), _item_stat() (+25 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (33): train_cnn_stage_streaming(), freeze_encoder(), train_gnn_stage_streaming(), StageWindow, train_lstm_stage_streaming(), build_x(), train_transformer_stage_streaming(), filter_windows_with_cache() (+25 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (74): dependencies, arktype@^2.2.7, @better-auth/passkey@^1.7.7, bits-ui@^2.20.6, clsx@^2.1.1, d3-polygon@^3.0.1, d3-scale@^4.0.2, @internationalized/date@^3.12.4 (+66 more)

### Community 14 - "Community 14"
Cohesion: 0.05
Nodes (39): _decode_one_sonde(), DropsondeFetchError, DropsondeProfile, fetch_and_parse_dropsonde_mission(), fetch_dropsonde_mission_tarball(), _ftp_connect(), list_dropsonde_missions(), _mask_missing() (+31 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (34): _crop_variable(), fetch_real_satellite_crop(), _find_real_scan(), GoesFetchError, _lazy_open(), _list_scan_keys(), _nearest_scan_key(), _parse_scan_start() (+26 more)

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (32): check_run(), CycleConflict, _existing_source(), InFlight, operator_ids(), RunRequest, stored_source(), RunInfo (+24 more)

### Community 17 - "Community 17"
Cohesion: 0.06
Nodes (49): AppAuth, buildAuth(), getAuth(), verifyApiKey(), CYCLE_STEP, cycleInstanceId(), CycleParams, CycleWorkflow (+41 more)

### Community 18 - "Community 18"
Cohesion: 0.07
Nodes (31): cmd_ablation(), cmd_atcf_archive(), cmd_cache_localize(), cmd_consistency_distill(), cmd_drift_reference_fit(), cmd_era5_cache(), cmd_gdas_cache(), _cmd_gridded_cache() (+23 more)

### Community 19 - "Community 19"
Cohesion: 0.05
Nodes (51): ArchitectureOut, LayerOut, ModelVersionOut, {
		arch,
		onclose,
		class: className = ''
	}, Box, boxFor(), clamp(), color (+43 more)

### Community 20 - "Community 20"
Cohesion: 0.07
Nodes (33): audit_one(), audit_run(), _AuditPlan, _fix_from_dict(), _fix_to_dict(), list_operational_records(), _load_audited_cycles(), load_skew_samples() (+25 more)

### Community 21 - "Community 21"
Cohesion: 0.04
Nodes (23): stage_a(), stage_b(), StageSpec, test_both_stages_label_from_final_besttrack(), test_stage_a_uses_era5_and_stage_b_uses_gdas(), test_stage_b_learning_rate_is_lower_than_stage_a(), _RecordingStore, _StubMlflowClient (+15 more)

### Community 22 - "Community 22"
Cohesion: 0.07
Nodes (38): brier_score(), crps_ensemble(), _crps_rows(), crps_series(), ensemble_percentiles(), rank_histogram(), reliability(), aggregate_by_storm() (+30 more)

### Community 23 - "Community 23"
Cohesion: 0.06
Nodes (27): initial_fix(), assert_input_safe(), augment_track(), emulate_working_track(), TrackQuality, offset_positions(), assert_operational_flavor(), CycleError (+19 more)

### Community 24 - "Community 24"
Cohesion: 0.07
Nodes (30): invalidated_by(), evaluate_all(), expand_jobs(), nightly_latent(), on_data_volume(), on_drift(), on_latent_desync(), on_skew() (+22 more)

### Community 25 - "Community 25"
Cohesion: 0.05
Nodes (37): svelte-sonner@^1.2.3, ModelCatalog, {
    contributors,
    missingModelReasons = {},
    hoveredModel = $bindable(null),
  }, maxWeight, missingRows, Props, rows, Props (+29 more)

### Community 26 - "Community 26"
Cohesion: 0.08
Nodes (34): Flavor, latent_signature(), RegistryError, _stage_group1_and_derived(), full_set(), register_group1(), _stage_all(), test_champion_falls_back_to_staging_without_a_production_version() (+26 more)

### Community 27 - "Community 27"
Cohesion: 0.07
Nodes (32): build_lstm(), encode(), forward(), __init__(), _storm_split(), boundaries_for_flavor(), build_stage_samples(), _train_candidate_lstm() (+24 more)

### Community 28 - "Community 28"
Cohesion: 0.08
Nodes (26): assert_no_leakage(), assign_splits(), _earliest_season(), filter_tracks(), _latest_season(), LeakageError, _seasons(), Split (+18 more)

### Community 29 - "Community 29"
Cohesion: 0.06
Nodes (23): @lucide/svelte@^1.71.0, sveltekit-superforms@^2.31.0, authClient, { form }, Props, { form }, Props, errorMsg (+15 more)

### Community 30 - "Community 30"
Cohesion: 0.08
Nodes (28): archive_atcf(), ArchiveReport, currentstorms_key(), _digest(), _get_bytes(), NotPublished, _put_bytes(), snapshot_key() (+20 more)

### Community 31 - "Community 31"
Cohesion: 0.08
Nodes (29): _empty_report(), _fake_checkpoint_store(), make_args(), make_track(), _reconcile_args(), _retrain_check_args(), _spy_assign_splits(), test_cmd_era5_cache_keeps_the_default_boundaries() (+21 more)

### Community 32 - "Community 32"
Cohesion: 0.07
Nodes (24): AtcfError, pair_by_valid_time(), parse_bdeck(), _parse_latlon(), parse_tcvitals(), storm_basin(), TcVitalsError, basins_of() (+16 more)

### Community 33 - "Community 33"
Cohesion: 0.09
Nodes (30): archive_key(), build_fetch_tasks(), filter_tracks_by_min_valid_time(), shard_tracks(), sync_cache_to_archive(), FakeArchive, _fix_keys(), make_fields() (+22 more)

### Community 34 - "Community 34"
Cohesion: 0.08
Nodes (12): get_state(), require_api_key(), state_dependency(), get_custom_redoc_html(), create_app(), _debug_last_deterministic_error(), redoc_html(), _lifespan() (+4 more)

### Community 35 - "Community 35"
Cohesion: 0.05
Nodes (40): IdTokenClaims, JwtClaims, OidcAddressClaim, OidcStandardClaims, UserProfile, AsyncReturnType, Expand, ExtractGenericViewableContent (+32 more)

### Community 36 - "Community 36"
Cohesion: 0.10
Nodes (25): arch_params_tag(), candidate_tags(), standardization_tags(), _builder(), _decode_arch_params(), _download_state_dict(), InferenceLoadError, load_run_artifacts() (+17 more)

### Community 37 - "Community 37"
Cohesion: 0.08
Nodes (24): bearing_deg(), bearings_deg(), cross_along_track_nm(), cross_along_track_nms(), km_to_nm(), nm_to_km(), calibrate(), forecast_motion_bearings() (+16 more)

### Community 38 - "Community 38"
Cohesion: 0.08
Nodes (30): QUICK, API, DEVELOP, addVirtualAuthenticator(), EMAIL_DIR, EMAIL_LOCK, listEmailFiles(), localD1() (+22 more)

### Community 39 - "Community 39"
Cohesion: 0.08
Nodes (21): run_fetch_cache(), fetch_one(), ArchiveClient, FetchCacheReport, _memo_enabled(), run_fetch_cache(), SyncReport, make_fields() (+13 more)

### Community 40 - "Community 40"
Cohesion: 0.13
Nodes (26): run_cycle(), deterministic_fn(), good_ensemble(), make_fix(), test_a_pacific_climatological_ensemble_is_drawn_from_pacific_radii(), test_absent_opportunistic_feeds_do_not_flag_the_cycle(), test_an_eastern_pacific_cycle_falls_back_to_nhcs_pacific_radii(), test_caller_requested_members_is_honored_by_the_climatological_fallback() (+18 more)

### Community 41 - "Community 41"
Cohesion: 0.10
Nodes (32): emulate_working_fix(), lr_factor(), _latlon(), make_fix(), make_track(), test_assert_input_safe_allows_working_quality(), test_assert_input_safe_blocks_final_quality(), test_augment_track_rejects_non_final_input() (+24 more)

### Community 42 - "Community 42"
Cohesion: 0.07
Nodes (11): calibration_out(), DemoState, deterministic(), StormState, cmd_cycle(), deterministic(), climatological_ensemble(), LeadProductCalibration (+3 more)

### Community 43 - "Community 43"
Cohesion: 0.09
Nodes (25): _FakeCycleOutput, _get_real_state(), _make_deterministic_forecast(), _memory_store(), test_a_failed_cycle_write_never_fails_the_cycle(), test_a_stale_refresh_in_flight_serves_known_storms_without_waiting(), test_an_unrestored_drift_window_is_never_written_back(), test_calibration_report_is_honest_empty_with_no_samples() (+17 more)

### Community 44 - "Community 44"
Cohesion: 0.05
Nodes (27): rehype-slug@^6.0.0, rehype-stringify@^10.0.1, remark-gfm@^4.0.1, remark-parse@^11.0.0, remark-rehype@^11.1.2, unified@^11.0.5, unist-util-visit@^5.1.0, CONSOLE_ROOT (+19 more)

### Community 45 - "Community 45"
Cohesion: 0.10
Nodes (23): build_cnn(), encode(), forward(), __init__(), build_cnn_samples(), CnnStageSamples, cache_all_fixes(), _FakeS3Client (+15 more)

### Community 46 - "Community 46"
Cohesion: 0.10
Nodes (26): build_gnn(), encode(), forward(), __init__(), build_gnn_samples(), build_mesh_topology(), GnnStageSamples, cache_all_fixes() (+18 more)

### Community 47 - "Community 47"
Cohesion: 0.10
Nodes (24): ExecutionMode, Task, fake_load_run_artifacts(), _FakeJointLatents, runner(), fake_extract_joint_latents(), make_fake(), test_a_failing_model_is_reported_not_raised() (+16 more)

### Community 48 - "Community 48"
Cohesion: 0.09
Nodes (27): ActivePin, ArchitectureOut, ConeSegmentOut, CyclePayload, CyclePlanOut, DegradedFlagRef, DriftReportOut, FeatureDriftOut (+19 more)

### Community 49 - "Community 49"
Cohesion: 0.10
Nodes (11): cycle_plan_out(), _budgets(), CyclePlan, derive_vitals_timeout(), plan_day(), _schedule_stages(), ScheduledStage, Stage (+3 more)

### Community 50 - "Community 50"
Cohesion: 0.11
Nodes (10): ModelRegistry, ModelVersion, _champions(), test_a_basin_is_served_once_every_champion_is_verified_in_it(), test_a_champion_verified_nowhere_serves_no_basin_as_in_distribution(), test_no_champion_or_champions_from_before_the_tag_are_the_atlantic(), test_champion_is_none_with_no_versions_registered(), test_promoting_a_new_production_archives_the_incumbent() (+2 more)

### Community 51 - "Community 51"
Cohesion: 0.09
Nodes (20): config_copy(), edit(), _cron_run_offset_minutes(), _image_layout(), _leaves(), _load(), _run(), test_a_config_change_redeploys_the_api() (+12 more)

### Community 52 - "Community 52"
Cohesion: 0.10
Nodes (20): advisory_time(), floor_synoptic(), is_synoptic(), next_synoptic(), NWPUnavailableError, require_synoptic(), _require_utc(), select_nwp_cycle() (+12 more)

### Community 53 - "Community 53"
Cohesion: 0.08
Nodes (21): Archive, archives_for(), describe(), fetch_latest_hurdat2(), last_season(), latest_name(), manifest_path(), test_a_listing_without_one_archive_falls_back_for_that_archive_only() (+13 more)

### Community 54 - "Community 54"
Cohesion: 0.08
Nodes (28): bounds, colors, coneFeatures, coneHull, currentFix, forecastLine, forecastPoints, geoCircle() (+20 more)

### Community 55 - "Community 55"
Cohesion: 0.06
Nodes (31): layerchart@^2.5.1, IntensityPercentiles, TrackPointOut, BY_ARCHITECTURE, BY_SLUG, colorFor(), FUNCTIONAL_COLORS, FUSION_COLOR (+23 more)

### Community 56 - "Community 56"
Cohesion: 0.08
Nodes (17): experiment_name(), cache_nwp_lead_hours(), CacheLeadMismatch, _claim_cache_dir(), latest_final_season(), baseline_beaten(), basin_input_tags(), build_run_tags() (+9 more)

### Community 57 - "Community 57"
Cohesion: 0.11
Nodes (26): cache_path(), _decode_cached_fields(), FetchTask, load_cached_fields(), _work(), save_cached_fields(), build_x(), build_x() (+18 more)

### Community 58 - "Community 58"
Cohesion: 0.10
Nodes (20): build_pinn(), encode(), forward(), __init__(), cache_all_fixes(), _FakeS3Client, make_fields(), make_track() (+12 more)

### Community 59 - "Community 59"
Cohesion: 0.06
Nodes (35): context, dockerfile, postgres, AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY, MLFLOW_S3_ENDPOINT_URL, POSTGRES_DB (+27 more)

### Community 60 - "Community 60"
Cohesion: 0.08
Nodes (18): absolute_pairs(), basin_key(), is_basin_key(), key_basin(), per_basin_scores(), sample_counts(), scored_basins(), ForecastPoint (+10 more)

### Community 61 - "Community 61"
Cohesion: 0.08
Nodes (18): LeadTimeStats, to_metric_dict(), VerificationPair, ConfigResult, evaluate_step_budget_tradeoff(), evaluate(), point_track_error_48h(), TradeoffReport (+10 more)

### Community 62 - "Community 62"
Cohesion: 0.13
Nodes (18): AvailabilityOracle, earliest_ready_time(), LatencyOracle, resolve_cycle_inputs(), _valid_time_for(), test_all_nwp_missing_marks_the_required_input_unavailable(), test_cycle_is_not_ready_before_vitals_arrive(), test_cycle_is_ready_once_vitals_and_staged_nwp_are_in() (+10 more)

### Community 63 - "Community 63"
Cohesion: 0.13
Nodes (20): AblationCell, AblationReport, build_samples(), run_capacity_ablation(), _cell(), make_track(), test_at_fraction_filters_and_sorts_by_hidden_dim(), test_build_samples_augmentation_multiplies_sample_count() (+12 more)

### Community 64 - "Community 64"
Cohesion: 0.08
Nodes (26): getSchedule(), health(), listStorms(), CyclePlanOut, deadline, { plan }, Props, stageLabel (+18 more)

### Community 65 - "Community 65"
Cohesion: 0.12
Nodes (18): _get_text(), load_drift_live(), _put_text(), save_drift_live(), _get_text(), _load_recent(), _load_audited(), _save_audited() (+10 more)

### Community 66 - "Community 66"
Cohesion: 0.06
Nodes (31): data, basins, stage_a, epochs, flavor, input_sources, label_source, learning_rate (+23 more)

### Community 67 - "Community 67"
Cohesion: 0.07
Nodes (31): better-auth@^1.7.7, @better-auth/api-key@^1.7.7, @types/node@^26.6.4, typescript@^5.9.3, wrangler@^4.147.0, better-auth, @better-auth/api-key, @types/node (+23 more)

### Community 68 - "Community 68"
Cohesion: 0.11
Nodes (23): CycleAbandoned, plan_cycle(), total_budget(), test_a_cycle_started_at_the_timeout_still_clears_the_margin(), test_core_is_ready_before_spread(), test_cycle_starts_when_vitals_land_not_at_synoptic_time(), test_describe_mentions_the_nwp_lag(), test_late_start_sheds_ensemble_load_to_hold_the_advisory() (+15 more)

### Community 69 - "Community 69"
Cohesion: 0.11
Nodes (21): build_products(), intensity_pdf(), landfall_probability(), rapid_intensification_probability(), _member(), members(), test_a_36_hour_gain_is_not_counted_as_24_hour_intensification(), test_a_real_24_hour_surge_is_still_detected() (+13 more)

### Community 70 - "Community 70"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, env, GH_TOKEN, GRAPHIFY_VERSION, permissions, runs-on (+22 more)

### Community 71 - "Community 71"
Cohesion: 0.12
Nodes (13): Fetcher, FetchError, ingest_cycle_inputs(), ingest_one(), IngestionOutcome, IngestionRecord, LakeTier, LakeWriter (+5 more)

### Community 72 - "Community 72"
Cohesion: 0.07
Nodes (29): WithElementRef, ButtonClickEvent, PrimitiveAnchorAttributes, PrimitiveButtonAttributes, PrimitiveCanvasAttributes, PrimitiveDivAttributes, PrimitiveElementAttributes, PrimitiveFigureAttributes (+21 more)

### Community 73 - "Community 73"
Cohesion: 0.14
Nodes (14): InferenceCycleError, cache_current_fix(), _FakeS3Client, make_track(), _register_real_version(), _store(), test_build_real_deterministic_fn_combines_all_four_real_models(), test_build_real_deterministic_fn_raises_with_no_registered_models() (+6 more)

### Community 74 - "Community 74"
Cohesion: 0.12
Nodes (22): authHandle(), Auth, _authByRequest, buildAuth(), checkRegistrationOpen(), getAuth(), buildSessionHeaders(), extractBearerToken() (+14 more)

### Community 75 - "Community 75"
Cohesion: 0.07
Nodes (28): inputArgs, jobs, projectId, region, results, timeoutSeconds, assign, return (+20 more)

### Community 76 - "Community 76"
Cohesion: 0.13
Nodes (19): run_fetch_cache(), make_fields(), make_track(), test_default_fetch_fn_wires_a_shared_session(), fake_fetch_gdas_grib2_fields(), fake_gdas_to_gridded_fields(), test_fetch_one_fetches_exactly_one_real_sample(), fake_gdas_to_gridded_fields() (+11 more)

### Community 77 - "Community 77"
Cohesion: 0.14
Nodes (15): DriftError, ReferenceDistribution, load_reference(), reference_from_json(), reference_to_json(), save_reference(), test_drift_reference_fit_fits_and_persists_from_real_cached_fields(), _make_reference() (+7 more)

### Community 78 - "Community 78"
Cohesion: 0.17
Nodes (23): build_schedule(), Mode, run_schedule(), RunOutcome, failing_runner(), runner(), ok_runner(), test_both_schedules_validate() (+15 more)

### Community 79 - "Community 79"
Cohesion: 0.10
Nodes (12): color_for(), god(), Module, WindGod, test_every_god_color_is_distinct(), test_experiment_name_handles_fusion_without_raising(), test_experiment_names_are_the_god_slugs(), test_lookup_by_slug_and_by_architecture_agree() (+4 more)

### Community 80 - "Community 80"
Cohesion: 0.13
Nodes (10): svelte-guard@^1.1.1, @sveltejs/kit@^2.70.3, DEFAULT_AFTER_LOGIN, loginHref(), safeNext(), requireSignIn(), requireSignInLoad(), guard() (+2 more)

### Community 81 - "Community 81"
Cohesion: 0.14
Nodes (13): accessed(), _check_type(), config_dir(), ConfigError, fixed(), get(), get_list(), _load() (+5 more)

### Community 82 - "Community 82"
Cohesion: 0.14
Nodes (18): Hurdat2Error, _parse_data_line(), _parse_header(), parse_hurdat2(), _parse_latlon(), test_entry_count_mismatch_raises(), test_header_name_is_parsed_onto_the_track(), test_malformed_header_raises() (+10 more)

### Community 83 - "Community 83"
Cohesion: 0.12
Nodes (13): RunTags, Trigger, validate(), make_tags(), test_malformed_dvc_version_is_rejected(), test_malformed_git_commit_is_rejected(), test_malformed_nwp_cycle_lag_is_rejected(), test_none_values_are_dropped_from_the_dict() (+5 more)

### Community 84 - "Community 84"
Cohesion: 0.14
Nodes (7): FORM_FACTORS, freeCycleLabel(), label(), runFreshCycle(), signIn(), cases, @playwright/test

### Community 85 - "Community 85"
Cohesion: 0.12
Nodes (8): cycle_inputs_prefix(), cycle_key(), CycleHistory, list_cycle_labels(), load_cycle_result(), save_cycle_inputs(), save_cycle_result(), _synthetic_fallback_deterministic()

### Community 86 - "Community 86"
Cohesion: 0.13
Nodes (15): fetch_current_storm_ids(), fetch_current_storms(), fetch_live_track(), _get(), LiveAtcfError, test_fetch_current_storm_ids_parses_and_uppercases(), test_fetch_current_storm_ids_raises_on_malformed_json(), test_fetch_current_storm_ids_reads_the_real_nhc_index() (+7 more)

### Community 87 - "Community 87"
Cohesion: 0.13
Nodes (14): fetch_and_parse_ndbc(), fetch_ndbc_realtime2(), _get(), NdbcFetchError, NdbcObservation, parse_ndbc_realtime2(), test_a_row_with_the_wrong_column_count_is_skipped_not_fatal(), test_a_station_missing_wave_columns_still_parses() (+6 more)

### Community 88 - "Community 88"
Cohesion: 0.11
Nodes (13): build_cone(), climatological_cone_nm(), cone_radius_from_spread(), ConeSegment, deterministic_center(), EnsembleMember, ForecastProducts, _interpolate_climo() (+5 more)

### Community 89 - "Community 89"
Cohesion: 0.10
Nodes (8): build_derived_schedule(), _latent_task(), ResourceProfile, Schedule, _train_task(), validate_schedule(), Wave, test_derived_schedule_retrains_no_group1_model()

### Community 90 - "Community 90"
Cohesion: 0.16
Nodes (13): cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_build_transformer_samples_empty_when_nothing_cached(), test_build_transformer_samples_rejects_a_cache_smaller_than_grid_size(), test_build_transformer_samples_trims_the_real_41x41_crop_to_grid_size() (+5 more)

### Community 91 - "Community 91"
Cohesion: 0.08
Nodes (9): _FakeMlflowModelVersion, _mlflow_client_that_registers_and_transitions(), create_model_version(), test_mlflow_mirror_skips_create_registered_model_if_it_already_exists(), create_model_version(), test_mlflow_transition_also_mirrors_the_archived_incumbent(), create_model_version(), test_register_persists_locally_and_durably_before_touching_mlflow() (+1 more)

### Community 92 - "Community 92"
Cohesion: 0.11
Nodes (11): runed@^0.37.1, App, Locals, Platform, DEFAULT_EXTRA, ExtraPreferences, PackageManager, UserContext (+3 more)

### Community 93 - "Community 93"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GH_TOKEN, IMPORTED_FROM, SOURCE_SHA, jobs, publish (+16 more)

### Community 94 - "Community 94"
Cohesion: 0.11
Nodes (17): _crop_box(), crop(), crop_levels(), crop(), _global_grid_with_marker(), _synthetic_era5_dataset(), _synthetic_gdas_fields(), test_crop_box_centers_on_the_requested_lat_lon() (+9 more)

### Community 95 - "Community 95"
Cohesion: 0.12
Nodes (15): assert_not_operational(), get(), operational_sources(), _operational_substitute(), OperationalUseError, Role, test_era5_is_pretrain_only(), test_era5_latency_is_days_not_hours() (+7 more)

### Community 96 - "Community 96"
Cohesion: 0.08
Nodes (8): DELETE, GET, PATCH, POST, PUT, { data }, prerender, ssr

### Community 97 - "Community 97"
Cohesion: 0.15
Nodes (14): _all_tensors(), Architecture, _builder(), describe(), describe_cached(), _describe_cached(), hook(), _example_inputs() (+6 more)

### Community 98 - "Community 98"
Cohesion: 0.12
Nodes (13): generate_season(), generate_track(), make_storm_spec(), StormSpec, wrap_longitude(), test_archive_spans_the_requested_seasons(), test_fields_have_matching_shapes_and_carry_a_flavor(), test_fixes_are_six_hourly_and_synoptic() (+5 more)

### Community 99 - "Community 99"
Cohesion: 0.13
Nodes (10): _download(), fetch_oisst_sst(), require_sst_deps(), sst_at(), SstFetchError, _small_grid(), test_fetch_oisst_sst_reads_real_recent_data(), test_sst_at_finds_the_nearest_cell() (+2 more)

### Community 100 - "Community 100"
Cohesion: 0.17
Nodes (16): _lon_close(), _members(), ref_bearing(), ref_displacement(), ref_haversine(), ref_offset(), rng(), test_array_geodesy_matches_the_per_point_formulas() (+8 more)

### Community 101 - "Community 101"
Cohesion: 0.15
Nodes (10): fetch_gefs_ensemble_grib2_fields(), fetch_gefs_member_grib2_fields(), _gefs_member_url(), _parse_grib2_index(), test_control_member_zero_uses_gec00_not_gep00(), test_fetch_gefs_ensemble_reads_multiple_real_distinct_members(), test_fetch_gefs_member_reads_the_real_noaa_archive(), test_member_out_of_range_raises() (+2 more)

### Community 103 - "Community 103"
Cohesion: 0.13
Nodes (7): mlflow_client_from_env(), test_an_unreachable_server_is_skipped_fast(), test_builds_a_real_client_when_tracking_uri_is_set(), test_fail_fast_settings_never_override_explicit_ones(), test_mlflow_client_from_env_can_actually_reach_the_configured_server(), test_returns_none_when_tracking_uri_is_unset(), test_returns_none_without_mlflow_installed()

### Community 104 - "Community 104"
Cohesion: 0.14
Nodes (11): _files(), localize_cache(), LocalizeReport, _raise(), _cache(), test_a_directory_that_cant_be_listed_fails_the_copy(), test_a_missing_source_raises(), test_a_rerun_only_fills_gaps() (+3 more)

### Community 105 - "Community 105"
Cohesion: 0.13
Nodes (10): _default_fetch_fn(), fetch(), era5_to_gridded_fields(), fetch_era5t_one(), open_era5(), open_era5_store(), _era5t_fetcher(), fetch() (+2 more)

### Community 106 - "Community 106"
Cohesion: 0.10
Nodes (3): Stage, test_registry_route_refreshes_a_stale_registry(), test_run_cycle_picks_up_a_registry_change_mid_warm_lifetime()

### Community 107 - "Community 107"
Cohesion: 0.10
Nodes (7): test_cmd_train_actually_transitions_a_promotable_candidate_to_staging(), _FakeS3Config, test_checkpoint_store_push_mirrors_registry_json_after_every_save(), test_pull_failure_degrades_to_an_empty_registry(), test_pull_from_checkpoint_store_hydrates_a_missing_local_registry(), test_pull_is_a_noop_when_the_key_does_not_exist_remotely_yet(), test_pull_reconciles_with_durable_storage_even_when_local_already_exists()

### Community 108 - "Community 108"
Cohesion: 0.17
Nodes (12): DiffusionArtifacts, _standardize(), _standardize_y(), train_diffusion_stage(), _make_samples(), test_a_longer_epoch_budget_never_returns_a_worse_val_loss(), test_early_stopping_halts_before_the_epoch_cap_on_a_real_overfitting_run(), test_run_diffusion_curriculum_uploads_a_checkpoint_and_registers_stage_b() (+4 more)

### Community 109 - "Community 109"
Cohesion: 0.13
Nodes (11): recommend_extra_conditioning(), _fake_val(), _FakeS3Client, _lc(), patched(), fake_extract(), test_intensity_underdispersion_alone_does_not_trigger_it(), test_long_lead_track_underdispersion_warrants_extra_conditioning() (+3 more)

### Community 110 - "Community 110"
Cohesion: 0.10
Nodes (20): PROJECT_NUMBER, PROJECT_PAT, types, jobs, sync, name, on, issues (+12 more)

### Community 111 - "Community 111"
Cohesion: 0.20
Nodes (13): displacement_nm(), storm_relative_sequence(), make_fix(), test_displacement_direction_matches_bearing(), test_displacement_magnitude_matches_haversine_distance(), test_displacement_nm_matches_storm_relative_sequence(), test_eastward_motion_is_positive_dx_with_a_small_northward_component(), test_mixed_storm_ids_raises() (+5 more)

### Community 112 - "Community 112"
Cohesion: 0.15
Nodes (6): drift_report_out(), calibration(), drift(), drift_all(), skew(), FeatureDrift

### Community 113 - "Community 113"
Cohesion: 0.29
Nodes (11): SkewMonitor, sample(), test_intensity_delta_is_signed_toward_the_operational_run(), test_intensity_skew_alone_can_raise_an_alert(), test_large_track_delta_raises_an_alert(), test_metric_names_match_the_scope_additions(), test_pruning_drops_ancient_samples(), test_report_is_withheld_below_the_sample_minimum() (+3 more)

### Community 114 - "Community 114"
Cohesion: 0.16
Nodes (7): _default_fetch_fn(), fetch(), fetch_gdas_grib2_fields(), gdas_to_gridded_fields(), gfs_url(), test_fetch_gdas_grib2_fields_reads_the_real_noaa_archive(), test_fetch_gdas_grib2_fields_uses_a_passed_in_session_not_the_module()

### Community 115 - "Community 115"
Cohesion: 0.15
Nodes (10): era5_deps_available(), gridded_deps_available(), require_era5_deps(), require_gdas_deps(), require_gridded_deps(), _saturation_vapor_pressure_hpa_array(), _specific_humidity_to_rh_pct(), test_era5_deps_do_not_require_eccodes() (+2 more)

### Community 116 - "Community 116"
Cohesion: 0.12
Nodes (4): _Boto3Client, require_boto3(), _StorageClient, test_boto3_adapter_configures_the_client_for_the_given_endpoint()

### Community 117 - "Community 117"
Cohesion: 0.12
Nodes (7): _filter_windows_with_finite_env(), _freeze_pinn_trunk(), _PinnWindowDataset, train_pinn_stage(), train_pinn_stage_streaming(), forward_batch(), candidate_model()

### Community 118 - "Community 118"
Cohesion: 0.15
Nodes (11): _fields(), _MemoryS3, _run(), test_a_missing_t_minus_6_cycle_falls_back_to_t_minus_12(), fetch_one(), test_gfs_url_names_the_forecast_valid_at_the_time(), fetch_one(), test_no_nwp_at_all_is_flagged() (+3 more)

### Community 119 - "Community 119"
Cohesion: 0.15
Nodes (7): clearPreferenceStorage(), consent, CONSENT_KEY, ConsentCategory, ConsentChoice, ConsentState, PREFERENCE_PREFIXES

### Community 120 - "Community 120"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 121 - "Community 121"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 122 - "Community 122"
Cohesion: 0.15
Nodes (6): CloudflareAccessRequestHeaderProvider, test_headers_are_actually_applied_by_mlflows_own_resolution(), test_in_context_false_when_neither_var_set(), test_in_context_false_when_only_client_id_set(), test_in_context_true_and_correct_headers_when_both_set(), test_registered_as_a_real_mlflow_plugin_via_entry_points()

### Community 123 - "Community 123"
Cohesion: 0.13
Nodes (8): god_out(), model_catalog(), retrain_job_out(), skew_report_out(), source_out(), pending_triggers(), DataSource, pretrain_only_sources()

### Community 124 - "Community 124"
Cohesion: 0.12
Nodes (16): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+8 more)

### Community 125 - "Community 125"
Cohesion: 0.12
Nodes (16): compilerOptions, allowJs, allowSyntheticDefaultImports, checkJs, forceConsistentCasingInFileNames, isolatedModules, lib, module (+8 more)

### Community 126 - "Community 126"
Cohesion: 0.12
Nodes (16): permissions, runs-on, steps, jobs, copilot-setup-steps, name, on, pull_request (+8 more)

### Community 127 - "Community 127"
Cohesion: 0.18
Nodes (7): get_cycle(), get_storm(), list_storms(), _overrides(), run_cycle(), _served_basins(), _storm_summary()

### Community 128 - "Community 128"
Cohesion: 0.12
Nodes (5): client(), test_docs_route_is_unaffected(), test_theme_http_method_colors_are_distinct(), test_theme_never_uses_a_god_color(), _walk()

### Community 129 - "Community 129"
Cohesion: 0.12
Nodes (16): with, build-args, cache-from, cache-to, context, file, load, password (+8 more)

### Community 130 - "Community 130"
Cohesion: 0.12
Nodes (15): jobs, lint-and-validate, name, permissions, runs-on, steps, name, on (+7 more)

### Community 131 - "Community 131"
Cohesion: 0.22
Nodes (9): run_spread_backtest(), SpreadBacktestError, _registry_with_champions(), _store(), test_diffusion_version_override_measures_that_version_not_the_champion(), test_diffusion_version_override_raises_cleanly_for_an_unknown_version(), test_diffusion_version_override_still_enforces_the_real_latent_signature(), test_refuses_a_diffusion_desynced_from_the_live_champions() (+1 more)

### Community 132 - "Community 132"
Cohesion: 0.19
Nodes (6): _FakeS3Client, _make_samples(), test_run_fusion_curriculum_uploads_a_checkpoint_and_registers_stage_b(), test_train_fusion_stage_reduces_loss_and_produces_val_metrics(), test_train_fusion_stage_rejects_a_val_set_built_with_a_different_model_count(), test_train_fusion_stage_rejects_empty_samples()

### Community 133 - "Community 133"
Cohesion: 0.13
Nodes (15): scripts, build, cf:deploy, check, check:errors, check:warnings, check:watch, dev (+7 more)

### Community 134 - "Community 134"
Cohesion: 0.19
Nodes (12): loading, onInput(), open, query, results, bodyById, buildIndex(), excerptAround() (+4 more)

### Community 135 - "Community 135"
Cohesion: 0.13
Nodes (15): env, environment, if, name, needs, permissions, runs-on, timeout-minutes (+7 more)

### Community 136 - "Community 136"
Cohesion: 0.14
Nodes (3): CycleInputs, InputStatus, NWPCycleSelection

### Community 137 - "Community 137"
Cohesion: 0.26
Nodes (9): detect_feature_drift(), reference(), test_collapsed_variance_is_detected(), test_feature_count_mismatch_raises(), test_matching_distribution_shows_no_drift(), test_reference_must_be_the_stage_b_distribution(), test_shifted_mean_is_detected(), test_summary_names_the_worst_feature() (+1 more)

### Community 138 - "Community 138"
Cohesion: 0.13
Nodes (7): distill_consistency_model(), step_loss(), _pseudo_huber(), _sample_config(), test_distillation_rejects_a_non_positive_epochs_or_patience(), test_distillation_restores_the_teachers_device_and_mode_even_if_training_raises(), test_distillation_trains_a_student_without_mutating_the_teachers_device()

### Community 139 - "Community 139"
Cohesion: 0.21
Nodes (6): model_version_out(), get_active_pin(), get_model_architecture(), get_model_registry(), list_registry(), RegistryEntry

### Community 140 - "Community 140"
Cohesion: 0.14
Nodes (13): compilerOptions, allowJs, checkJs, esModuleInterop, forceConsistentCasingInFileNames, moduleResolution, resolveJsonModule, rewriteRelativeImportExtensions (+5 more)

### Community 141 - "Community 141"
Cohesion: 0.14
Nodes (13): images, options, diskSizeGb, machineType, steps, args, entrypoint, env (+5 more)

### Community 142 - "Community 142"
Cohesion: 0.21
Nodes (5): build_info(), _build_info_path(), config_digest(), git_sha(), summary()

### Community 143 - "Community 143"
Cohesion: 0.14
Nodes (14): default, description, type, default, description, type, api, console (+6 more)

### Community 144 - "Community 144"
Cohesion: 0.35
Nodes (7): NoiseSensitivityReport, _result(), test_is_load_bearing_above_threshold(), test_is_not_load_bearing_below_threshold(), test_relative_change_is_zero_when_losses_match(), test_relative_change_rejects_nonpositive_default_loss(), test_relative_change_sign_matches_direction_of_the_move()

### Community 145 - "Community 145"
Cohesion: 0.21
Nodes (5): TransformerOptimizer, _standardize_x(), _standardize_y(), train_transformer_stage(), test_the_optimiser_caps_the_stage_rate_warms_up_and_clips()

### Community 146 - "Community 146"
Cohesion: 0.19
Nodes (7): OrchestrationError, _register_group1_versions(), test_a_desynced_derived_champion_is_not_a_bar_a_servable_candidate_must_clear(), test_a_servable_derived_champion_is_still_a_real_bar(), test_derived_resync_records_the_champion_signature_and_ends_in_sync(), test_seed_from_champions_loads_each_champion_not_the_latest(), test_seed_from_champions_refuses_an_incomplete_champion_set()

### Community 147 - "Community 147"
Cohesion: 0.18
Nodes (7): batch_graph(), MeshTopology, _node_features(), _standardize_x(), _standardize_y(), train_gnn_stage(), forward_batch()

### Community 148 - "Community 148"
Cohesion: 0.15
Nodes (12): name, runs-on, timeout-minutes, concurrency, cancel-in-progress, group, jobs, build (+4 more)

### Community 149 - "Community 149"
Cohesion: 0.18
Nodes (3): health(), models(), sources()

### Community 150 - "Community 150"
Cohesion: 0.09
Nodes (7): client(), hurdat2_file(), test_debug_last_deterministic_error_route_needs_opt_in(), test_real_state_monitoring_and_retraining_routes_do_not_500(), test_real_state_run_cycle_degrades_to_the_synthetic_fallback(), test_run_cycle_rejects_a_cycle_that_has_not_started_yet(), test_the_storm_routes_refresh_the_registry_before_reading_coverage()

### Community 151 - "Community 151"
Cohesion: 0.23
Nodes (11): max, target, budgets, reduced, standard, max, target, assembly (+3 more)

### Community 152 - "Community 152"
Cohesion: 0.20
Nodes (7): client(), test_a_registered_versions_arch_params_are_used(), test_a_version_without_arch_params_is_described_from_defaults(), test_a_versions_arch_params_change_what_is_described(), test_every_model_runs_its_example_input_and_reports_its_layers(), test_the_gnn_is_fed_the_real_lattice(), test_unknown_models_and_versions_are_404()

### Community 153 - "Community 153"
Cohesion: 0.17
Nodes (11): concurrency, cancel-in-progress, group, jobs, test-api, name, if, name (+3 more)

### Community 154 - "Community 154"
Cohesion: 0.17
Nodes (12): with, cache, cache-dependency-path, enable-cache, fetch-depth, if-no-files-found, include-hidden-files, name (+4 more)

### Community 155 - "Community 155"
Cohesion: 0.18
Nodes (5): offset_position(), ConeOutcome, served_cone_outcome(), test_served_cone_scores_what_build_cone_actually_serves(), ensemble()

### Community 156 - "Community 156"
Cohesion: 0.24
Nodes (3): LeadCalibration, format_report(), SpreadBacktestReport

### Community 157 - "Community 157"
Cohesion: 0.20
Nodes (4): spread_skill(), SpreadSkill, test_calibrated_ensemble_has_a_spread_skill_ratio_near_one(), test_underdispersion_is_flagged()

### Community 158 - "Community 158"
Cohesion: 0.18
Nodes (11): cycle, advisory_margin_minutes, advisory_offset_minutes, allow_estimated_vitals, allow_load_shedding, max_nwp_lag_hours, nominal_vitals_offset_minutes, nwp_lag_hours (+3 more)

### Community 159 - "Community 159"
Cohesion: 0.20
Nodes (3): audit_due(), test_audit_becomes_due_once_era5t_lands(), test_audit_is_not_due_immediately_after_the_cycle()

### Community 160 - "Community 160"
Cohesion: 0.20
Nodes (10): limit, lower_is_better, limit, lower_is_better, thresholds, intensity_error_48h_kt, intensity_error_72h_kt, track_error_72h_nm (+2 more)

### Community 161 - "Community 161"
Cohesion: 0.20
Nodes (10): steps, EXPECT_GIT_SHA, GCP_CI_SERVICE_ACCOUNT, GCP_WIF_PROVIDER, env, id, if, name (+2 more)

### Community 162 - "Community 162"
Cohesion: 0.20
Nodes (10): name, outputs, runs-on, timeout-minutes, changes, deploy_api, deploy_console, plan (+2 more)

### Community 163 - "Community 163"
Cohesion: 0.40
Nodes (10): steps, steps, id, if, name, run, uses, working-directory (+2 more)

### Community 164 - "Community 164"
Cohesion: 0.27
Nodes (4): ChecksumCheck, FetchResult, NonEmptyCheck, QCFinding

### Community 165 - "Community 165"
Cohesion: 0.29
Nodes (5): ValidationLossMonitor, test_a_recovery_resets_the_consecutive_count(), test_first_observation_only_sets_the_baseline(), test_increases_below_the_threshold_never_trigger(), test_trigger_requires_three_consecutive_breaches()

### Community 166 - "Community 166"
Cohesion: 0.22
Nodes (9): run, test-console, working-directory, defaults, if, name, needs, runs-on (+1 more)

### Community 167 - "Community 167"
Cohesion: 0.22
Nodes (9): BASE_SHA, BEFORE_SHA, DISPATCH_API, DISPATCH_CONSOLE, EVENT, EXPECT_GIT_SHA, HEAD_SHA, REF (+1 more)

### Community 168 - "Community 168"
Cohesion: 0.25
Nodes (5): fetch_live_tracks(), fetch_one(), test_fetch_live_tracks_fetches_storms_concurrently_and_keeps_index_order(), test_fetch_live_tracks_skips_a_storm_whose_own_fetch_fails(), fake_fetch_live_track()

### Community 169 - "Community 169"
Cohesion: 0.22
Nodes (4): test_mlflow_mirror_is_skipped_without_a_checkpoint_uri(), __getattr__(), test_mlflow_mirror_registers_model_then_version_with_a_real_source_uri(), create_model_version()

### Community 170 - "Community 170"
Cohesion: 0.31
Nodes (5): _champions_tagged(), test_a_basin_counts_only_when_every_champion_trained_on_it(), test_a_champion_without_the_tag_counts_as_atlantic_only(), test_trained_basins_come_from_the_champions_tags(), test_trained_basins_follow_the_champion_not_the_latest_version()

### Community 171 - "Community 171"
Cohesion: 0.28
Nodes (4): oracle(), pytest_collection_modifyitems(), target_time(), worst_case_oracle()

### Community 172 - "Community 172"
Cohesion: 0.25
Nodes (4): season_boundaries(), test_boundaries_move_with_the_archive(), test_stage_bs_validation_season_is_never_seen_by_stage_a(), test_too_short_an_archive_is_refused()

### Community 173 - "Community 173"
Cohesion: 0.25
Nodes (8): 12, 120, 24, 36, 48, 72, 96, climatological_cone_nm

### Community 174 - "Community 174"
Cohesion: 0.25
Nodes (8): CP, 12, 120, 24, 36, 48, 72, 96

### Community 175 - "Community 175"
Cohesion: 0.25
Nodes (8): EP, 12, 120, 24, 36, 48, 72, 96

### Community 176 - "Community 176"
Cohesion: 0.25
Nodes (7): calibration_audit, cone_nominal_rate, intensity_nominal_rate, min_cases, verdict_margin, test_set_budget, max_evaluations_per_season

### Community 177 - "Community 177"
Cohesion: 0.25
Nodes (8): drift, min_samples, reference_flavor, shift_sigma, validation_loss, variance_ratio_limit, consecutive_required, threshold_fraction

### Community 178 - "Community 178"
Cohesion: 0.25
Nodes (8): promotion, flavor, new_basin_tolerance, primary_metric, reference_basin, require_manual_gate, split, basins()

### Community 179 - "Community 179"
Cohesion: 0.36
Nodes (4): cache_all_fixes(), make_fields(), _task_for(), test_extract_joint_latents_rejects_missing_group1_model()

### Community 180 - "Community 180"
Cohesion: 0.29
Nodes (7): products, cone_percentile, landfall_threshold_nm, lead_hours, ri_alert_probability, ri_threshold_kt, ri_window_hours

### Community 181 - "Community 181"
Cohesion: 0.29
Nodes (7): skew_audit, alert_intensity_delta_kt, alert_track_delta_nm, audit_delay_days, lead_hours, min_samples, window_days

### Community 182 - "Community 182"
Cohesion: 0.57
Nodes (5): deploy-plan.sh script, touches(), touches_component(), touches_console(), why

### Community 183 - "Community 183"
Cohesion: 0.29
Nodes (7): env, IMAGE, JOB, PROJECT_ID, PUBLISH, REGION, REGISTRY

### Community 184 - "Community 184"
Cohesion: 0.29
Nodes (3): archive_atcf(), calibration_audit(), skew_audit()

### Community 185 - "Community 185"
Cohesion: 0.33
Nodes (3): _standardize_cnn_x(), _standardize_y(), train_cnn_stage()

### Community 190 - "Community 190"
Cohesion: 0.33
Nodes (6): ensemble, climatological_cone_nm_by_basin, members, min_members_for_ensemble_cone, reduced_members, underdispersion_fraction

### Community 191 - "Community 191"
Cohesion: 0.33
Nodes (6): triggers, data_volume_threshold, nightly_latent_hour_utc, preseason_date, scheduled_monthly_day, suppress_nightly_latent_during_active_storms

### Community 192 - "Community 192"
Cohesion: 0.33
Nodes (6): update_job, workflow_dispatch, default, description, type, inputs

### Community 193 - "Community 193"
Cohesion: 0.33
Nodes (6): on, pull_request, push, paths, branches, paths

### Community 194 - "Community 194"
Cohesion: 0.33
Nodes (3): wilson_interval(), test_ri_uncertain_marks_an_ensemble_that_cannot_resolve_the_threshold(), test_wilson_interval_brackets_the_estimate_and_stays_in_the_unit_range()

### Community 196 - "Community 196"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 197 - "Community 197"
Cohesion: 0.40
Nodes (3): WORLD_GEOJSON, WorldData, WorldFeatureProperties

### Community 198 - "Community 198"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 199 - "Community 199"
Cohesion: 0.70
Nodes (4): graphify(), normalise_graph(), normalise_report(), build-graph.sh script

### Community 200 - "Community 200"
Cohesion: 0.67
Nodes (4): max, target, diffusion, diffusion

### Community 201 - "Community 201"
Cohesion: 0.67
Nodes (4): max, target, fusion, fusion

### Community 202 - "Community 202"
Cohesion: 0.67
Nodes (4): max, target, postprocess, postprocess

### Community 203 - "Community 203"
Cohesion: 0.67
Nodes (4): max, target, preprocess, preprocess

### Community 204 - "Community 204"
Cohesion: 0.50
Nodes (3): uvx, graphify, graphify-mcp

### Community 207 - "Community 207"
Cohesion: 0.67
Nodes (3): limit, lower_is_better, nhc_consensus_beat_rate_48h

### Community 208 - "Community 208"
Cohesion: 0.67
Nodes (3): track_error_120h_nm, limit, lower_is_better

### Community 209 - "Community 209"
Cohesion: 0.67
Nodes (3): track_error_48h_nm, limit, lower_is_better

## Knowledge Gaps
- **13 isolated node(s):** `./.svelte-kit/tsconfig.json`, `why`, `uvx`, `graphify-mcp`, `ANEMOI_FIELDS_MEMO` (+8 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2520 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Flavor` connect `Community 26` to `Community 0`, `Community 1`, `Community 131`, `Community 4`, `Community 5`, `Community 132`, `Community 137`, `Community 9`, `Community 11`, `Community 12`, `Community 18`, `Community 146`, `Community 21`, `Community 23`, `Community 152`, `Community 27`, `Community 28`, `Community 31`, `Community 33`, `Community 36`, `Community 39`, `Community 169`, `Community 42`, `Community 43`, `Community 170`, `Community 45`, `Community 46`, `Community 47`, `Community 172`, `Community 50`, `Community 179`, `Community 57`, `Community 58`, `Community 60`, `Community 73`, `Community 76`, `Community 77`, `Community 79`, `Community 81`, `Community 83`, `Community 90`, `Community 91`, `Community 94`, `Community 95`, `Community 98`, `Community 105`, `Community 106`, `Community 107`, `Community 108`, `Community 112`, `Community 114`, `Community 115`, `Community 118`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Are the 236 inferred relationships involving `Flavor` (e.g. with `DemoState` and `drift()`) actually correct?**
  _`Flavor` has 236 INFERRED edges - model-reasoned connections that need verification._
- **What connects `./.svelte-kit/tsconfig.json`, `why`, `uvx` to the rest of the system?**
  _13 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.04937121564974383 - nodes in this community are weakly interconnected._
- **Why does `CheckpointStore` connect `Community 65` to `Community 0`, `Community 131`, `Community 132`, `Community 5`, `Community 8`, `Community 10`, `Community 11`, `Community 18`, `Community 20`, `Community 27`, `Community 156`, `Community 30`, `Community 36`, `Community 43`, `Community 45`, `Community 46`, `Community 58`, `Community 73`, `Community 77`, `Community 85`, `Community 90`, `Community 108`, `Community 116`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 124 inferred relationships involving `Track` (e.g. with `save_cycle_inputs()` and `StormState`) actually correct?**
  _`Track` has 124 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.03940982333527471 - nodes in this community are weakly interconnected._