# Graph Report - anemoi  (2026-11-13)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 6664 nodes · 17031 edges · 238 communities (214 shown, 24 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 2475 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `06cd2e82`
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
- Community 230
- Community 231
- Community 232
- Community 233
- Community 234
- Community 235
- Community 236
- Community 237

## God Nodes (most connected - your core abstractions)
1. `Flavor` - 283 edges
2. `Track` - 187 edges
3. `Fix` - 141 edges
4. `ModelRegistry` - 134 edges
5. `CheckpointStore` - 128 edges
6. `TrackQuality` - 105 edges
7. `require_torch()` - 100 edges
8. `MetricSet` - 81 edges
9. `FetchTask` - 68 edges
10. `LatencyOracle` - 68 edges

## Surprising Connections (you probably didn't know these)
- `make_window()` --calls--> `StageWindow`  [INFERRED]
  tests/test_streaming.py → src/anemoi/training/real_run.py
- `make_fix()` --calls--> `Fix`  [INFERRED]
  tests/test_streaming.py → src/anemoi/data/besttrack.py
- `test_cache_round_trip_and_vector()` --uses--> `FetchTask`  [INFERRED]
  tests/test_steering.py → src/anemoi/data/gridded_cache.py
- `test_internal_calibration_audit_route_reports_new_samples()` --uses--> `RealState`  [INFERRED]
  tests/test_api_real_state.py → src/anemoi/api/real_state.py
- `test_a_versions_arch_params_change_what_is_described()` --calls--> `describe()`  [INFERRED]
  tests/test_model_architecture.py → src/anemoi/models/architecture.py

## Import Cycles
- None detected.

## Communities (238 total, 24 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (55): sanitize_field_pixels(), StageSpec, build_stage_samples(), cnn_input(), _sanitized_channel_stack(), _standardize_cnn_x(), _standardize_y(), train_cnn_stage() (+47 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (56): Adeck, storm_basin(), OfficialErrors, absolute_pairs(), basin_key(), per_basin_scores(), sample_counts(), assemble_validation_forecasts() (+48 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (85): ApiError, apiFetch(), getActivePin(), getArchitecture(), getCalibration(), getDrift(), getDriftAll(), getModelRegistry() (+77 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (56): ModelSpec, require_torch(), torch_available(), build_diffusion(), __init__(), _cosine_schedule(), build_fusion(), forward() (+48 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (51): Flavor, latent_signature(), ModelRegistry, RegistryError, _stage_group1_and_derived(), test_data_volume_counts_seasons_newer_than_any_model_trained_on(), test_seed_from_champions_refuses_an_incomplete_champion_set(), _champions_tagged() (+43 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (48): _put_text(), save_drift_live(), cmd_ablation(), cmd_adeck_fetch(), cmd_atcf_archive(), cmd_baseline_backtest(), cmd_cache_localize(), cmd_consistency_distill() (+40 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (50): apply_cold_wake(), area_mean(), assert_flavor(), cold_wake_sst_depression_c(), compare_potential_intensity_estimates(), compute_environment_features(), deep_layer_shear(), emanuel_potential_intensity() (+42 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (40): bearing_deg(), bearings_deg(), cross_along_track_nm(), cross_along_track_nms(), haversine_nm(), km_to_nm(), nm_to_km(), calibrate() (+32 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (66): getCycle(), getSchedule(), getStorm(), health(), listStorms(), runCycle(), CyclePlanOut, deadline (+58 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (10): cycle_payload_out(), cycle_result_out(), cycle_inputs_prefix(), CycleHistory, RealState, deterministic(), ensemble(), live_fields() (+2 more)

### Community 10 - "Community 10"
Cohesion: 0.06
Nodes (44): Fix, _build_live_context(), _build_live_x(), build_live_cnn_x(), build_live_gnn_x(), build_live_lstm_x(), build_live_pinn_x(), build_live_transformer_x() (+36 more)

### Community 11 - "Community 11"
Cohesion: 0.07
Nodes (45): assert_deployable(), Curriculum, CurriculumError, CurriculumRun, StageResult, OrchestrationError, MetricSet, PromotionDecision (+37 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (29): pair_by_valid_time(), augment_track(), emulate_working_track(), Track, WorkingTrackNoise, as_issued(), calibrate_season(), filter_tracks() (+21 more)

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (41): check_run(), CycleConflict, _existing_source(), InFlight, operator_ids(), RunRequest, stored_source(), assert_operational_flavor() (+33 more)

### Community 14 - "Community 14"
Cohesion: 0.03
Nodes (45): guards, handle, Props, Section, SectionPage, { sections }, height, motionClass (+37 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (21): get_state(), require_api_key(), state_dependency(), get_custom_redoc_html(), create_app(), _debug_last_deterministic_error(), redoc_html(), _lifespan() (+13 more)

### Community 16 - "Community 16"
Cohesion: 0.04
Nodes (38): client(), _FakeCycleOutput, _fresh_real_state(), _get_real_state(), hurdat2_file(), _make_deterministic_forecast(), _make_storm_state(), _memory_store() (+30 more)

### Community 17 - "Community 17"
Cohesion: 0.05
Nodes (39): _decode_one_sonde(), DropsondeFetchError, DropsondeProfile, fetch_and_parse_dropsonde_mission(), fetch_dropsonde_mission_tarball(), _ftp_connect(), list_dropsonde_missions(), _mask_missing() (+31 more)

### Community 18 - "Community 18"
Cohesion: 0.04
Nodes (52): bounds, colors, coneFeatures, coneHull, currentFix, forecastLine, forecastPoints, geoCircle() (+44 more)

### Community 19 - "Community 19"
Cohesion: 0.05
Nodes (34): _crop_variable(), fetch_real_satellite_crop(), _find_real_scan(), GoesFetchError, _lazy_open(), _list_scan_keys(), _nearest_scan_key(), _parse_scan_start() (+26 more)

### Community 20 - "Community 20"
Cohesion: 0.05
Nodes (33): _context_features(), _displacement_to_absolute(), _empty_samples(), _extract_for_tracks(), extract_joint_latents(), extract_validation_latents(), joint_stage_windows(), JointLatentBundle (+25 more)

### Community 21 - "Community 21"
Cohesion: 0.06
Nodes (50): @cloudflare/containers@^0.3.7, AppAuth, buildAuth(), getAuth(), verifyApiKey(), CYCLE_STEP, cycleInstanceId(), CycleParams (+42 more)

### Community 22 - "Community 22"
Cohesion: 0.06
Nodes (37): build_cone(), build_products(), climatological_cone_nm(), ConeSegment, deterministic_center(), EnsembleMember, ForecastProducts, intensity_pdf() (+29 more)

### Community 23 - "Community 23"
Cohesion: 0.06
Nodes (31): detect_feature_drift(), DriftError, ReferenceDistribution, ValidationLossMonitor, load_reference(), reference_from_json(), reference_to_json(), save_reference() (+23 more)

### Community 24 - "Community 24"
Cohesion: 0.06
Nodes (36): archive_key(), ArchiveClient, build_fetch_tasks(), _decode_cached_fields(), FetchCacheReport, filter_tracks_by_min_valid_time(), _memo_enabled(), run_fetch_cache() (+28 more)

### Community 25 - "Community 25"
Cohesion: 0.07
Nodes (45): assert_input_safe(), emulate_working_fix(), recalibrate_from_pairs(), storm_relative_sequence(), lr_factor(), _latlon(), make_fix(), make_track() (+37 more)

### Community 26 - "Community 26"
Cohesion: 0.07
Nodes (32): basin_inputs(), ModelVersion, collect_validation_forecasts(), _builder(), deterministic_fn(), _compute_env_features(), _item_stat(), _real_fusion_forecast() (+24 more)

### Community 27 - "Community 27"
Cohesion: 0.06
Nodes (39): cycle_products_out(), model_version_out(), provenance_out(), get_active_pin(), get_model_architecture(), get_model_registry(), list_registry(), ActivePin (+31 more)

### Community 28 - "Community 28"
Cohesion: 0.05
Nodes (58): devDependencies, cn@^0.3.3, @fontsource-variable/geist@^5.3.0, @fontsource-variable/geist-mono@^5.3.0, @fontsource-variable/inter@^5.3.0, formsnap@^2.0.1, layerchart@^2.5.1, mode-watcher@^1.1.0 (+50 more)

### Community 29 - "Community 29"
Cohesion: 0.08
Nodes (34): cache_path(), FetchTask, load_cached_fields(), _work(), save_cached_fields(), build_x(), build_x(), _filter_and_fit_env_stats() (+26 more)

### Community 30 - "Community 30"
Cohesion: 0.07
Nodes (9): CachedAdecks, basin_value(), is_basin_key(), key_basin(), scored_basins(), trained_basins(), verified_basins(), served_columns() (+1 more)

### Community 31 - "Community 31"
Cohesion: 0.05
Nodes (25): stage_a(), stage_b(), test_both_stages_label_from_final_besttrack(), test_final_besttrack_cannot_be_a_stage_input(), test_stage_a_uses_era5_and_stage_b_uses_gdas(), test_stage_b_cannot_read_a_pretrain_only_source(), test_stage_b_learning_rate_is_lower_than_stage_a(), _RecordingStore (+17 more)

### Community 32 - "Community 32"
Cohesion: 0.07
Nodes (31): save_cycle_inputs(), archive_atcf(), ArchiveReport, currentstorms_key(), _digest(), _get_text(), _load_recent(), _put_bytes() (+23 more)

### Community 33 - "Community 33"
Cohesion: 0.08
Nodes (30): invalidated_by(), evaluate_all(), expand_jobs(), nightly_latent(), on_data_volume(), on_drift(), on_latent_desync(), on_skew() (+22 more)

### Community 34 - "Community 34"
Cohesion: 0.07
Nodes (30): assert_no_leakage(), assign_splits(), _earliest_season(), _latest_season(), LeakageError, _seasons(), Split, _split_for_season() (+22 more)

### Community 35 - "Community 35"
Cohesion: 0.06
Nodes (30): _baseline_inputs(), _empty_report(), _hurdat2_storm(), make_args(), make_track(), _retrain_check_args(), _spy_assign_splits(), test_adeck_fetch_reads_the_split_and_keeps_cached_files() (+22 more)

### Community 36 - "Community 36"
Cohesion: 0.06
Nodes (18): AdeckPoint, basins_of(), select_basins(), basin_one_hot(), with_basin_channels(), with_basin_columns(), with_basin_vector(), TransformerOptimizer (+10 more)

### Community 37 - "Community 37"
Cohesion: 0.08
Nodes (34): offset_positions(), wrap_longitude(), cone_radius_from_spread(), brier_score(), crps_ensemble(), _crps_rows(), crps_series(), rank_histogram() (+26 more)

### Community 38 - "Community 38"
Cohesion: 0.06
Nodes (42): SourceOut, byUse(), hasUnknownEntry(), MODEL_NAMES, MODELS, ORDER, readersOf(), SOURCE_NAMES (+34 more)

### Community 39 - "Community 39"
Cohesion: 0.08
Nodes (28): _get_text(), list_cycle_labels(), load_cycle_result(), load_drift_live(), _synthetic_fallback_deterministic(), audit_due(), audit_storm(), _audited_key() (+20 more)

### Community 40 - "Community 40"
Cohesion: 0.07
Nodes (21): AvailabilityOracle, CycleInputs, earliest_ready_time(), InputStatus, resolve_cycle_inputs(), _valid_time_for(), Role, NWPCycleSelection (+13 more)

### Community 41 - "Community 41"
Cohesion: 0.07
Nodes (30): build_lstm(), encode(), forward(), __init__(), boundaries_for_flavor(), displacement_to_latlon(), candidate_model(), _fake_checkpoint_store() (+22 more)

### Community 42 - "Community 42"
Cohesion: 0.06
Nodes (23): @lucide/svelte@^1.71.0, sveltekit-superforms@^2.31.0, authClient, { form }, Props, { form }, Props, errorMsg (+15 more)

### Community 43 - "Community 43"
Cohesion: 0.06
Nodes (21): App, Locals, Platform, categories, choosing, mounted, picked, visible (+13 more)

### Community 44 - "Community 44"
Cohesion: 0.06
Nodes (34): svelte-sonner@^1.2.3, {
    contributors,
    missingModelReasons = {},
    hoveredModel = $bindable(null),
  }, maxWeight, missingRows, Props, rows, Props, qualityLabel (+26 more)

### Community 45 - "Community 45"
Cohesion: 0.08
Nodes (28): basin_tags(), by_basin(), complete_run(), _forecasts(), metric_set(), test_a_basin_is_verified_when_the_model_beats_persistence_there(), test_a_basin_validated_but_never_trained_on_is_not_verified(), test_a_candidate_that_loses_a_verified_basin_is_refused() (+20 more)

### Community 46 - "Community 46"
Cohesion: 0.11
Nodes (24): case_errors(), compared_members(), homogeneous_mask(), _limiting(), _mean(), Member, MemberScore, _paired() (+16 more)

### Community 47 - "Community 47"
Cohesion: 0.09
Nodes (26): ExecutionMode, Task, fake_load_run_artifacts(), _FakeJointLatents, _register_group1_versions(), runner(), fake_extract_joint_latents(), make_fake() (+18 more)

### Community 48 - "Community 48"
Cohesion: 0.12
Nodes (26): climatological_ensemble(), run_cycle(), deterministic_fn(), good_ensemble(), make_fix(), test_a_pacific_climatological_ensemble_is_drawn_from_pacific_radii(), test_absent_opportunistic_feeds_do_not_flag_the_cycle(), test_an_eastern_pacific_cycle_falls_back_to_nhcs_pacific_radii() (+18 more)

### Community 49 - "Community 49"
Cohesion: 0.06
Nodes (11): calibration_out(), drift_report_out(), skew_report_out(), DemoState, StormState, calibration(), drift(), drift_all() (+3 more)

### Community 50 - "Community 50"
Cohesion: 0.10
Nodes (23): build_cnn(), encode(), forward(), __init__(), build_cnn_samples(), CnnStageSamples, cache_all_fixes(), _FakeS3Client (+15 more)

### Community 51 - "Community 51"
Cohesion: 0.10
Nodes (24): evaluate_promotion(), PromotionError, TestSetBudget, Threshold, _thresholds(), complete_run(), good_metrics(), test_beat_rate_threshold_is_higher_is_better() (+16 more)

### Community 52 - "Community 52"
Cohesion: 0.08
Nodes (22): format_report(), recommend_extra_conditioning(), run_spread_backtest(), SpreadBacktestError, SpreadBacktestReport, _fake_val(), _FakeS3Client, _lc() (+14 more)

### Community 53 - "Community 53"
Cohesion: 0.10
Nodes (21): cycle_key(), save_cycle_result(), audit_cycle(), _CountingClient, _FakeClient, _fix(), _result(), test_a_cycle_stored_before_the_ri_interval_still_loads() (+13 more)

### Community 54 - "Community 54"
Cohesion: 0.10
Nodes (25): build_gnn(), encode(), forward(), __init__(), build_gnn_samples(), build_mesh_topology(), GnnStageSamples, cache_all_fixes() (+17 more)

### Community 55 - "Community 55"
Cohesion: 0.09
Nodes (20): experiment_name(), cmd_train(), latest_final_season(), arch_params_tag(), baseline_beaten(), basin_input_tags(), build_run_tags(), candidate_tags() (+12 more)

### Community 56 - "Community 56"
Cohesion: 0.10
Nodes (10): cycle_plan_out(), schedule(), CyclePlan, derive_vitals_timeout(), plan_day(), _schedule_stages(), ScheduledStage, Stage (+2 more)

### Community 57 - "Community 57"
Cohesion: 0.09
Nodes (20): advisory_time(), floor_synoptic(), is_synoptic(), next_synoptic(), NWPUnavailableError, require_synoptic(), _require_utc(), select_nwp_cycle() (+12 more)

### Community 58 - "Community 58"
Cohesion: 0.10
Nodes (16): ChecksumCheck, Fetcher, FetchResult, ingest_cycle_inputs(), ingest_one(), IngestionOutcome, IngestionRecord, LakeTier (+8 more)

### Community 59 - "Community 59"
Cohesion: 0.10
Nodes (18): Stage, test_a_basin_is_in_distribution_once_every_served_model_is_verified_in_it(), _fake_checkpoint_store(), _reconcile_args(), test_cmd_train_passes_streaming_batch_size_and_num_workers_through(), fake_curriculum(), test_cmd_train_schedule_passes_streaming_batch_size_and_num_workers_to_runner(), test_cmd_train_unpacks_the_real_three_tuple_for_every_model() (+10 more)

### Community 60 - "Community 60"
Cohesion: 0.11
Nodes (24): expected_coordinates(), _decode(), files(), local(), _ohc(), _row_col(), server(), test_a_blank_file_is_rejected() (+16 more)

### Community 61 - "Community 61"
Cohesion: 0.07
Nodes (21): fetch(), _crop_box(), era5_to_gridded_fields(), crop(), crop_levels(), crop(), _global_grid_with_marker(), _synthetic_era5_dataset() (+13 more)

### Community 62 - "Community 62"
Cohesion: 0.06
Nodes (15): unist-util-visit@^5.1.0, CONSOLE_ROOT, force, LOCAL_WIKI, MANIFEST_DIR, processor, STATIC_DIR, useLocal (+7 more)

### Community 63 - "Community 63"
Cohesion: 0.09
Nodes (31): ArchitectureOut, LayerOut, {
		arch,
		onclose,
		class: className = ''
	}, Box, boxFor(), clamp(), color, focus (+23 more)

### Community 64 - "Community 64"
Cohesion: 0.06
Nodes (35): context, dockerfile, postgres, AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY, MLFLOW_S3_ENDPOINT_URL, POSTGRES_DB (+27 more)

### Community 65 - "Community 65"
Cohesion: 0.09
Nodes (18): cache_nwp_lead_hours(), CacheLeadMismatch, _claim_cache_dir(), fetch_one(), _fields(), _MemoryS3, _run(), test_a_cache_dir_holds_one_lead() (+10 more)

### Community 66 - "Community 66"
Cohesion: 0.07
Nodes (29): IntensityPercentiles, TrackPointOut, BY_ARCHITECTURE, BY_SLUG, colorFor(), FUNCTIONAL_COLORS, FUSION_COLOR, god() (+21 more)

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
Cohesion: 0.12
Nodes (18): disc_mean(), fetch_lead_flow(), group_by_time(), lead_flow(), LeadFlow, load_steering(), run_steering_cache(), fetch() (+10 more)

### Community 71 - "Community 71"
Cohesion: 0.11
Nodes (27): QUICK, addVirtualAuthenticator(), EMAIL_DIR, EMAIL_LOCK, listEmailFiles(), localD1(), setRegistrationOpen(), signUpViaMagicLink() (+19 more)

### Community 72 - "Community 72"
Cohesion: 0.06
Nodes (28): AsyncReturnType, Expand, ExtractGenericViewableContent, GenericItem, GenericSelectorOption, GenericSnippetProps, GenericViewableContent, InheritedSnippetProps (+20 more)

### Community 73 - "Community 73"
Cohesion: 0.09
Nodes (15): _build_joint_latent(), build_real_ensemble_fn(), ensemble_fn(), cycle_sample_seed(), _encode_group1(), InferenceEnsembleError, make_track(), _register() (+7 more)

### Community 74 - "Community 74"
Cohesion: 0.08
Nodes (16): Archive, archives_for(), latest_name(), season_boundaries(), test_boundaries_move_with_the_archive(), test_stage_bs_validation_season_is_never_seen_by_stage_a(), test_the_archive_a_run_was_given_is_not_what_it_trained_on(), test_the_as_issued_bulletin_is_paired_with_the_final_fix() (+8 more)

### Community 75 - "Community 75"
Cohesion: 0.06
Nodes (31): data, basins, stage_a, epochs, flavor, input_sources, label_source, learning_rate (+23 more)

### Community 76 - "Community 76"
Cohesion: 0.10
Nodes (22): aggregate_by_storm(), beat_rate(), diebold_mariano(), _normal_cdf(), verify(), pair(), test_aggregation_collapses_fixes_to_one_case_per_storm(), test_aggregation_keeps_the_two_arrays_aligned() (+14 more)

### Community 77 - "Community 77"
Cohesion: 0.08
Nodes (30): better-auth@^1.7.7, @better-auth/api-key@^1.7.7, @types/node@^26.6.4, typescript@^5.9.3, wrangler@^4.147.0, better-auth, @better-auth/api-key, @types/node (+22 more)

### Community 78 - "Community 78"
Cohesion: 0.11
Nodes (24): @sveltejs/kit@^2.70.3, authHandle(), Auth, _authByRequest, buildAuth(), checkRegistrationOpen(), getAuth(), buildSessionHeaders() (+16 more)

### Community 79 - "Community 79"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, env, GH_TOKEN, GRAPHIFY_VERSION, permissions, runs-on (+22 more)

### Community 80 - "Community 80"
Cohesion: 0.15
Nodes (15): audit_due(), SkewMonitor, SkewReport, sample(), test_audit_becomes_due_once_era5t_lands(), test_audit_is_not_due_immediately_after_the_cycle(), test_intensity_delta_is_signed_toward_the_operational_run(), test_intensity_skew_alone_can_raise_an_alert() (+7 more)

### Community 81 - "Community 81"
Cohesion: 0.09
Nodes (19): build_consistency_model(), consistency_fn(), __init__(), sample(), skip_coeffs(), distill_consistency_model(), step_loss(), _pseudo_huber() (+11 more)

### Community 82 - "Community 82"
Cohesion: 0.07
Nodes (29): WithElementRef, ButtonClickEvent, PrimitiveAnchorAttributes, PrimitiveButtonAttributes, PrimitiveCanvasAttributes, PrimitiveDivAttributes, PrimitiveElementAttributes, PrimitiveFigureAttributes (+21 more)

### Community 83 - "Community 83"
Cohesion: 0.14
Nodes (12): _check_basin(), _created_date(), cycle_date(), decode_ohc(), fetch_ohc_file(), name_day_for_creation(), OhcFile, require_ohc_deps() (+4 more)

### Community 84 - "Community 84"
Cohesion: 0.15
Nodes (14): build_real_deterministic_fn(), cache_current_fix(), _FakeS3Client, make_track(), _register_real_version(), _store(), test_build_real_deterministic_fn_combines_all_four_real_models(), test_build_real_deterministic_fn_raises_with_no_registered_models() (+6 more)

### Community 85 - "Community 85"
Cohesion: 0.07
Nodes (29): dependencies, arktype@^2.2.7, @better-auth/passkey@^1.7.7, bits-ui@^2.20.6, clsx@^2.1.1, d3-polygon@^3.0.1, d3-scale@^4.0.2, @internationalized/date@^3.12.4 (+21 more)

### Community 86 - "Community 86"
Cohesion: 0.07
Nodes (28): inputArgs, jobs, projectId, region, results, timeoutSeconds, assign, return (+20 more)

### Community 87 - "Community 87"
Cohesion: 0.10
Nodes (17): describe(), fetch_latest_hurdat2(), last_season(), manifest_path(), build_info(), _build_info_path(), config_digest(), git_sha() (+9 more)

### Community 88 - "Community 88"
Cohesion: 0.13
Nodes (13): _default_fetch_fn(), fetch(), fetch_era5t_one(), fetch_gdas_grib2_fields(), fetch_grib2_messages(), gdas_to_gridded_fields(), gfs_url(), open_era5() (+5 more)

### Community 89 - "Community 89"
Cohesion: 0.17
Nodes (23): build_schedule(), Mode, run_schedule(), RunOutcome, failing_runner(), runner(), ok_runner(), test_both_schedules_validate() (+15 more)

### Community 90 - "Community 90"
Cohesion: 0.12
Nodes (13): DiffusionArtifacts, _standardize(), _standardize_y(), train_diffusion_stage(), _FakeS3Client, _make_samples(), test_a_longer_epoch_budget_never_returns_a_worse_val_loss(), test_early_stopping_halts_before_the_epoch_cap_on_a_real_overfitting_run() (+5 more)

### Community 91 - "Community 91"
Cohesion: 0.12
Nodes (13): initial_fix(), TrackQuality, _MemoryS3, s3(), test_an_archive_storm_says_its_fix_is_the_final_best_track(), test_late_vitals_on_a_live_storm_read_as_estimated(), test_missing_vitals_are_extrapolated_and_estimated(), test_one_earlier_fix_is_persisted() (+5 more)

### Community 92 - "Community 92"
Cohesion: 0.10
Nodes (16): http_get(), OhcFetchError, OhcNotPublished, OhcUnavailable, Archive, test_a_cut_off_reply_is_a_fetch_failure(), test_a_cut_off_transfer_raises_rather_than_reading_an_older_file(), test_a_fetch_failure_that_is_not_a_404_is_not_stepped_over() (+8 more)

### Community 93 - "Community 93"
Cohesion: 0.13
Nodes (8): FORM_FACTORS, freeCycleLabel(), label(), runFreshCycle(), signIn(), cases, @playwright/test@^1.63.0, @playwright/test

### Community 94 - "Community 94"
Cohesion: 0.13
Nodes (11): fetch_gefs_ensemble_grib2_fields(), fetch_gefs_member_grib2_fields(), _gefs_member_url(), _parse_grib2_index(), require_gdas_deps(), test_control_member_zero_uses_gec00_not_gep00(), test_fetch_gefs_ensemble_reads_multiple_real_distinct_members(), test_fetch_gefs_member_reads_the_real_noaa_archive() (+3 more)

### Community 95 - "Community 95"
Cohesion: 0.10
Nodes (12): color_for(), god(), Module, WindGod, test_every_god_color_is_distinct(), test_experiment_name_handles_fusion_without_raising(), test_experiment_names_are_the_god_slugs(), test_lookup_by_slug_and_by_architecture_agree() (+4 more)

### Community 96 - "Community 96"
Cohesion: 0.10
Nodes (8): build_derived_schedule(), _latent_task(), ResourceProfile, Schedule, _train_task(), validate_schedule(), Wave, test_derived_schedule_retrains_no_group1_model()

### Community 97 - "Community 97"
Cohesion: 0.16
Nodes (13): cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_build_transformer_samples_empty_when_nothing_cached(), test_build_transformer_samples_rejects_a_cache_smaller_than_grid_size(), test_build_transformer_samples_trims_the_real_41x41_crop_to_grid_size() (+5 more)

### Community 98 - "Community 98"
Cohesion: 0.13
Nodes (8): svelte-guard@^1.1.1, DEFAULT_AFTER_LOGIN, loginHref(), safeNext(), requireSignIn(), requireSignInLoad(), guard(), svelte-guard

### Community 99 - "Community 99"
Cohesion: 0.14
Nodes (14): _all_tensors(), Architecture, _builder(), describe(), describe_cached(), _describe_cached(), hook(), _example_inputs() (+6 more)

### Community 100 - "Community 100"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GH_TOKEN, IMPORTED_FROM, SOURCE_SHA, jobs, publish (+16 more)

### Community 101 - "Community 101"
Cohesion: 0.14
Nodes (14): fetch_and_parse_ndbc(), fetch_ndbc_realtime2(), _get(), NdbcFetchError, NdbcObservation, parse_ndbc_realtime2(), test_a_row_with_the_wrong_column_count_is_skipped_not_fatal(), test_a_station_missing_wave_columns_still_parses() (+6 more)

### Community 102 - "Community 102"
Cohesion: 0.15
Nodes (11): record_operational_cycle(), _FakeClient, _fix(), _make_output(), _record(), test_audit_run_degrades_per_record_when_audit_one_raises(), test_audit_run_replays_only_due_records_and_persists_the_result(), test_audit_run_takes_a_bounded_batch_oldest_first() (+3 more)

### Community 103 - "Community 103"
Cohesion: 0.08
Nodes (3): client(), test_more_members_than_the_ensemble_runs_is_refused_not_silently_capped(), test_sources_say_who_uses_each_one()

### Community 104 - "Community 104"
Cohesion: 0.08
Nodes (8): DELETE, GET, PATCH, POST, PUT, { data }, prerender, ssr

### Community 105 - "Community 105"
Cohesion: 0.13
Nodes (15): _adeck_position(), AtcfError, parse_bdeck(), _parse_latlon(), parse_tcvitals(), TcVitalsError, test_bdeck_malformed_line_raises(), test_bdeck_parses_best_track_rows_only() (+7 more)

### Community 106 - "Community 106"
Cohesion: 0.13
Nodes (12): RunTags, validate(), make_tags(), test_malformed_dvc_version_is_rejected(), test_malformed_git_commit_is_rejected(), test_malformed_nwp_cycle_lag_is_rejected(), test_none_values_are_dropped_from_the_dict(), test_pretrain_flavor_tags_are_not_operational() (+4 more)

### Community 107 - "Community 107"
Cohesion: 0.16
Nodes (16): _default_fetch_fn(), run_fetch_cache(), make_fields(), make_track(), test_build_fetch_tasks_covers_every_fix_across_tracks(), test_load_cached_fields_rejects_a_missing_file(), test_run_fetch_cache_actually_runs_fetches_concurrently(), slow_fetch() (+8 more)

### Community 108 - "Community 108"
Cohesion: 0.13
Nodes (14): get(), _model_sources(), test_a_label_or_verification_source_is_never_a_model_input(), test_a_model_input_is_never_a_labels_only_source(), test_each_curriculum_stage_lists_what_its_models_read(), test_era5_is_pretrain_only(), test_era5_latency_is_days_not_hours(), test_every_model_reads_a_source_it_can_be_served_from() (+6 more)

### Community 109 - "Community 109"
Cohesion: 0.09
Nodes (9): _FakeMlflowModelVersion, _mlflow_client_that_registers_and_transitions(), create_model_version(), test_mlflow_mirror_registers_model_then_version_with_a_real_source_uri(), create_model_version(), test_mlflow_mirror_skips_create_registered_model_if_it_already_exists(), create_model_version(), test_mlflow_transition_also_mirrors_the_archived_incumbent() (+1 more)

### Community 110 - "Community 110"
Cohesion: 0.13
Nodes (7): mlflow_client_from_env(), test_an_unreachable_server_is_skipped_fast(), test_builds_a_real_client_when_tracking_uri_is_set(), test_fail_fast_settings_never_override_explicit_ones(), test_mlflow_client_from_env_can_actually_reach_the_configured_server(), test_returns_none_when_tracking_uri_is_unset(), test_returns_none_without_mlflow_installed()

### Community 111 - "Community 111"
Cohesion: 0.14
Nodes (11): _files(), localize_cache(), LocalizeReport, _raise(), _cache(), test_a_directory_that_cant_be_listed_fails_the_copy(), test_a_missing_source_raises(), test_a_rerun_only_fills_gaps() (+3 more)

### Community 112 - "Community 112"
Cohesion: 0.13
Nodes (10): boundaries_for_tracks(), ArmResult, compare(), expand_patch_channels(), __init__(), _renamed(), run_steering_spike(), split() (+2 more)

### Community 113 - "Community 113"
Cohesion: 0.15
Nodes (10): config_copy(), edit(), _image_layout(), _run(), test_a_missing_config_dir_is_refused(), test_an_image_without_configs_fails_at_import_and_says_why(), test_an_invalid_config_is_refused_with_a_clear_message(), test_edited_values_take_effect_at_runtime() (+2 more)

### Community 114 - "Community 114"
Cohesion: 0.16
Nodes (13): audit_one(), _AuditPlan, _fix_from_dict(), _fix_to_dict(), list_operational_records(), OperationalCycleRecord, record_from_json(), _record_key() (+5 more)

### Community 115 - "Community 115"
Cohesion: 0.12
Nodes (10): test_a_failed_time_is_reported_and_the_others_still_written(), fetch(), test_cache_round_trip_and_vector(), test_disc_mean_is_symmetric_for_a_field_linear_in_longitude(), test_features_advect_with_the_flow_plus_beta_drift(), test_features_raise_where_there_is_no_flow(), test_features_sample_each_lead_where_the_track_has_reached(), test_run_fetches_each_time_once_shares_it_and_skips_what_is_cached() (+2 more)

### Community 116 - "Community 116"
Cohesion: 0.10
Nodes (20): PROJECT_NUMBER, PROJECT_PAT, types, jobs, sync, name, on, issues (+12 more)

### Community 117 - "Community 117"
Cohesion: 0.20
Nodes (11): _check_type(), config_dir(), ConfigError, fixed(), get(), get_list(), _load(), _names() (+3 more)

### Community 118 - "Community 118"
Cohesion: 0.15
Nodes (14): adeck_name(), adeck_path(), adeck_urls(), _check_adeck(), fetch_adecks(), _archive(), _errors_url(), _FakeNhc (+6 more)

### Community 119 - "Community 119"
Cohesion: 0.16
Nodes (14): ohc_global(), ohc_url(), _full_archive(), test_a_blank_run_longer_than_the_window_leaves_na_unavailable(), test_a_degraded_basin_flags_the_field(), test_a_missing_file_steps_back_one_creation_day(), test_an_unknown_basin_leaves_the_field_unknown_unless_another_is_degraded(), test_no_url_before_the_archive_or_for_another_basin() (+6 more)

### Community 120 - "Community 120"
Cohesion: 0.15
Nodes (10): _attributes(), _calls(), _function(), _imported(), _names_adapter(), _parameters(), _parse(), _string_literals() (+2 more)

### Community 121 - "Community 121"
Cohesion: 0.15
Nodes (11): _check_official_errors(), read_cached_official_errors(), OfficialErrorsError, parse_official_errors(), _signed(), test_a_cached_error_file_that_is_not_nhcs_is_named_with_the_way_out(), test_parse_official_errors_reads_columns_by_name_and_skips_missing_leads(), test_parse_official_errors_reads_the_stated_initial_position_domain() (+3 more)

### Community 122 - "Community 122"
Cohesion: 0.18
Nodes (15): parse_hurdat2(), test_entry_count_mismatch_raises(), test_header_name_is_parsed_onto_the_track(), test_malformed_header_raises(), test_malformed_latitude_raises(), test_multi_storm_file_produces_one_track_per_storm(), test_non_numeric_entry_count_raises(), test_off_synoptic_and_missing_pressure_entries_are_dropped() (+7 more)

### Community 123 - "Community 123"
Cohesion: 0.11
Nodes (7): client(), test_docs_route_is_unaffected(), test_sources_role_is_the_role_enum_in_the_openapi_schema(), test_sources_used_by_is_documented_in_the_openapi_schema(), test_theme_http_method_colors_are_distinct(), test_theme_never_uses_a_god_color(), _walk()

### Community 124 - "Community 124"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 125 - "Community 125"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 126 - "Community 126"
Cohesion: 0.15
Nodes (6): CloudflareAccessRequestHeaderProvider, test_headers_are_actually_applied_by_mlflows_own_resolution(), test_in_context_false_when_neither_var_set(), test_in_context_false_when_only_client_id_set(), test_in_context_true_and_correct_headers_when_both_set(), test_registered_as_a_real_mlflow_plugin_via_entry_points()

### Community 127 - "Community 127"
Cohesion: 0.14
Nodes (9): GriddedFields, field(), cache_all_fixes(), make_fields(), _task_for(), test_extract_joint_latents_rejects_missing_group1_model(), test_filter_windows_with_finite_fields_drops_only_the_all_nan_window(), make_fix() (+1 more)

### Community 128 - "Community 128"
Cohesion: 0.12
Nodes (4): _Boto3Client, require_boto3(), _StorageClient, test_boto3_adapter_configures_the_client_for_the_given_endpoint()

### Community 129 - "Community 129"
Cohesion: 0.12
Nodes (16): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+8 more)

### Community 130 - "Community 130"
Cohesion: 0.16
Nodes (14): minisearch@^7.2.0, loading, onInput(), open, query, results, bodyById, buildIndex() (+6 more)

### Community 131 - "Community 131"
Cohesion: 0.12
Nodes (16): compilerOptions, allowJs, allowSyntheticDefaultImports, checkJs, forceConsistentCasingInFileNames, isolatedModules, lib, module (+8 more)

### Community 132 - "Community 132"
Cohesion: 0.12
Nodes (16): permissions, runs-on, steps, jobs, copilot-setup-steps, name, on, pull_request (+8 more)

### Community 133 - "Community 133"
Cohesion: 0.15
Nodes (8): BasinChoice, creation_day(), test_a_cycle_reads_the_file_made_two_days_before(), test_a_real_file_from_each_chain(), test_name_day_for_creation_inverts_creation_day_and_has_a_gap_at_the_switch(), test_the_flag_is_relative_to_the_baseline(), test_the_flag_on_real_files(), test_v1r1_files_are_made_the_day_after_their_name()

### Community 134 - "Community 134"
Cohesion: 0.17
Nodes (9): _bilinear(), _lattice_index(), ohc_at(), OhcField, place(), test_bilinear_between_nodes(), test_bilinear_is_exact_at_a_node_on_every_source(), test_bilinear_needs_all_four_corners() (+1 more)

### Community 135 - "Community 135"
Cohesion: 0.20
Nodes (10): cache_all_fixes(), _cache_steering(), make_track(), test_stage_b_trains_the_steering_conv_and_keeps_the_rest_frozen(), run(), test_steering_vectors_are_appended_after_the_basin_channels(), extra(), test_the_spike_runs_both_arms_on_the_same_windows_and_registers_nothing() (+2 more)

### Community 136 - "Community 136"
Cohesion: 0.12
Nodes (16): with, build-args, cache-from, cache-to, context, file, load, password (+8 more)

### Community 137 - "Community 137"
Cohesion: 0.12
Nodes (15): jobs, lint-and-validate, name, permissions, runs-on, steps, name, on (+7 more)

### Community 138 - "Community 138"
Cohesion: 0.17
Nodes (8): al_2021_2022(), compare(), open_ocean(), parse_ships(), sample_days(), ShipsCase, test_sohc_equals_bilinear_ohc_on_the_file_named_for_the_day_before(), test_compare_refuses_arms_on_different_windows_and_pairs_the_rest()

### Community 139 - "Community 139"
Cohesion: 0.19
Nodes (6): _FakeS3Client, _make_samples(), test_run_fusion_curriculum_uploads_a_checkpoint_and_registers_stage_b(), test_train_fusion_stage_reduces_loss_and_produces_val_metrics(), test_train_fusion_stage_rejects_a_val_set_built_with_a_different_model_count(), test_train_fusion_stage_rejects_empty_samples()

### Community 140 - "Community 140"
Cohesion: 0.13
Nodes (15): scripts, build, cf:deploy, check, check:errors, check:warnings, check:watch, dev (+7 more)

### Community 141 - "Community 141"
Cohesion: 0.13
Nodes (15): env, environment, if, name, needs, permissions, runs-on, timeout-minutes (+7 more)

### Community 142 - "Community 142"
Cohesion: 0.16
Nodes (7): _declared_length(), detect_format(), _grid_values(), OhcRejected, _read_checked(), StepBack, test_format_is_detected_from_the_first_bytes()

### Community 143 - "Community 143"
Cohesion: 0.14
Nodes (8): API, DEVELOP, PHONE, SourceRow, SOURCES, SOURCES_BEFORE_USED_BY, SOURCES_REWIRED, path()

### Community 144 - "Community 144"
Cohesion: 0.14
Nodes (13): compilerOptions, allowJs, checkJs, esModuleInterop, forceConsistentCasingInFileNames, moduleResolution, resolveJsonModule, rewriteRelativeImportExtensions (+5 more)

### Community 145 - "Community 145"
Cohesion: 0.14
Nodes (13): images, options, diskSizeGb, machineType, steps, args, entrypoint, env (+5 more)

### Community 146 - "Community 146"
Cohesion: 0.14
Nodes (14): default, description, type, default, description, type, api, console (+6 more)

### Community 147 - "Community 147"
Cohesion: 0.19
Nodes (4): _download(), fetch_oisst_sst(), require_sst_deps(), SstFetchError

### Community 148 - "Community 148"
Cohesion: 0.31
Nodes (8): AblationReport, _cell(), test_at_fraction_filters_and_sorts_by_hidden_dim(), test_capacity_does_not_help_when_val_loss_plateaus(), test_capacity_helps_requires_at_least_two_capacity_levels(), test_capacity_helps_uses_the_largest_fraction_present(), test_capacity_helps_when_val_loss_keeps_dropping_with_width(), test_to_markdown_includes_every_cell()

### Community 149 - "Community 149"
Cohesion: 0.35
Nodes (7): NoiseSensitivityReport, _result(), test_is_load_bearing_above_threshold(), test_is_not_load_bearing_below_threshold(), test_relative_change_is_zero_when_losses_match(), test_relative_change_rejects_nonpositive_default_loss(), test_relative_change_sign_matches_direction_of_the_move()

### Community 150 - "Community 150"
Cohesion: 0.17
Nodes (12): IdTokenClaims, JwtClaims, OidcAddressClaim, OidcStandardClaims, UserProfile, Mandatory, RFC-3966, RFC-4627 (+4 more)

### Community 151 - "Community 151"
Cohesion: 0.18
Nodes (7): client(), test_a_registered_versions_arch_params_are_used(), test_a_version_without_arch_params_is_described_from_defaults(), test_a_versions_arch_params_change_what_is_described(), test_every_model_runs_its_example_input_and_reports_its_layers(), test_the_gnn_is_fed_the_real_lattice(), test_unknown_models_and_versions_are_404()

### Community 152 - "Community 152"
Cohesion: 0.15
Nodes (12): name, runs-on, timeout-minutes, concurrency, cancel-in-progress, group, jobs, build (+4 more)

### Community 153 - "Community 153"
Cohesion: 0.15
Nodes (5): god_out(), model_catalog(), health(), models(), sources()

### Community 154 - "Community 154"
Cohesion: 0.23
Nodes (9): _adeck_positive(), parse_adeck(), test_parse_adeck_converts_tenths_and_hemispheres_and_wraps_longitude(), test_parse_adeck_counts_unreadable_rows_instead_of_raising(), test_parse_adeck_keeps_the_first_of_each_point_and_counts_disagreeing_repeats(), test_parse_adeck_matches_rows_by_cyclone_number_not_basin_column(), test_parse_adeck_reads_sentinels_as_absent_never_as_zero(), test_parse_adeck_rejects_a_bad_storm_id_and_text_with_no_record() (+1 more)

### Community 155 - "Community 155"
Cohesion: 0.19
Nodes (7): save_skew_samples(), SkewSample, test_skew_report_alerts_on_real_skew_once_enough_samples_are_persisted(), test_skew_report_falls_back_to_the_legacy_flat_path(), flaky_audit_one(), fake_audit_one(), test_save_then_load_skew_samples_round_trips()

### Community 156 - "Community 156"
Cohesion: 0.19
Nodes (5): test_registry_route_refreshes_a_stale_registry(), _champions(), test_a_basin_is_served_once_every_champion_is_verified_in_it(), test_a_champion_verified_nowhere_serves_no_basin_as_in_distribution(), test_no_champion_or_champions_from_before_the_tag_are_the_atlantic()

### Community 157 - "Community 157"
Cohesion: 0.22
Nodes (6): FakeClient, test_download_rejects_a_uri_from_a_different_bucket(), test_download_round_trips_the_uploaded_bytes(), test_list_filters_by_prefix(), test_upload_missing_file_raises(), test_upload_returns_an_s3_uri_and_stores_the_bytes()

### Community 158 - "Community 158"
Cohesion: 0.17
Nodes (6): _called(), _modules(), test_an_adapter_is_named_by_other_code_only_if_its_source_is_read(), test_every_fetch_adapter_is_classified(), test_no_module_imports_by_a_computed_name(), _unread_sources()

### Community 159 - "Community 159"
Cohesion: 0.23
Nodes (11): max, target, budgets, reduced, standard, max, target, assembly (+3 more)

### Community 160 - "Community 160"
Cohesion: 0.17
Nodes (11): concurrency, cancel-in-progress, group, jobs, test-api, name, if, name (+3 more)

### Community 161 - "Community 161"
Cohesion: 0.17
Nodes (12): with, cache, cache-dependency-path, enable-cache, fetch-depth, if-no-files-found, include-hidden-files, name (+4 more)

### Community 162 - "Community 162"
Cohesion: 0.18
Nodes (5): offset_position(), ConeOutcome, served_cone_outcome(), test_served_cone_scores_what_build_cone_actually_serves(), ensemble()

### Community 163 - "Community 163"
Cohesion: 0.20
Nodes (4): spread_skill(), SpreadSkill, test_calibrated_ensemble_has_a_spread_skill_ratio_near_one(), test_underdispersion_is_flagged()

### Community 164 - "Community 164"
Cohesion: 0.18
Nodes (11): cycle, advisory_margin_minutes, advisory_offset_minutes, allow_estimated_vitals, allow_load_shedding, max_nwp_lag_hours, nominal_vitals_offset_minutes, nwp_lag_hours (+3 more)

### Community 165 - "Community 165"
Cohesion: 0.27
Nodes (6): sst_at(), _small_grid(), test_fetch_oisst_sst_reads_real_recent_data(), test_sst_at_finds_the_nearest_cell(), test_sst_at_normalises_negative_longitude_to_0_360(), test_sst_at_returns_nan_over_a_real_missing_cell()

### Community 166 - "Community 166"
Cohesion: 0.27
Nodes (6): audit_run(), _load_audited_cycles(), load_skew_samples(), _prune_samples(), _save_audited_cycles(), test_load_skew_samples_is_empty_when_nothing_was_ever_audited()

### Community 167 - "Community 167"
Cohesion: 0.22
Nodes (6): first_record_of_year(), ships_al_url(), _ships_get(), ships_record_year(), ships_size(), ships_window()

### Community 168 - "Community 168"
Cohesion: 0.20
Nodes (10): limit, lower_is_better, limit, lower_is_better, thresholds, intensity_error_48h_kt, intensity_error_72h_kt, track_error_72h_nm (+2 more)

### Community 169 - "Community 169"
Cohesion: 0.20
Nodes (10): steps, EXPECT_GIT_SHA, GCP_CI_SERVICE_ACCOUNT, GCP_WIF_PROVIDER, env, id, if, name (+2 more)

### Community 170 - "Community 170"
Cohesion: 0.20
Nodes (10): name, outputs, runs-on, timeout-minutes, changes, deploy_api, deploy_console, plan (+2 more)

### Community 171 - "Community 171"
Cohesion: 0.40
Nodes (10): steps, steps, id, if, name, run, uses, working-directory (+2 more)

### Community 172 - "Community 172"
Cohesion: 0.27
Nodes (5): Hurdat2Error, _parse_data_row(), _parse_header(), _parse_latlon(), _storm_rows()

### Community 173 - "Community 173"
Cohesion: 0.20
Nodes (7): used_by(), test_cmd_sources_prints_who_uses_each_source(), test_a_verification_source_not_read_yet_is_verification_and_nothing_else(), test_every_required_cycle_input_has_a_model_consumer(), test_used_by_follows_the_contract_order_for_every_source(), test_used_by_per_source(), test_used_by_refuses_an_unknown_source()

### Community 174 - "Community 174"
Cohesion: 0.24
Nodes (3): HomogeneousRow, BaselineReport, _json_safe()

### Community 175 - "Community 175"
Cohesion: 0.22
Nodes (9): run, test-console, working-directory, defaults, if, name, needs, runs-on (+1 more)

### Community 176 - "Community 176"
Cohesion: 0.22
Nodes (9): BASE_SHA, BEFORE_SHA, DISPATCH_API, DISPATCH_CONSOLE, EVENT, EXPECT_GIT_SHA, HEAD_SHA, REF (+1 more)

### Community 177 - "Community 177"
Cohesion: 0.25
Nodes (5): era5_deps_available(), gridded_deps_available(), require_era5_deps(), require_gridded_deps(), test_era5_deps_do_not_require_eccodes()

### Community 178 - "Community 178"
Cohesion: 0.28
Nodes (4): oracle(), pytest_collection_modifyitems(), target_time(), worst_case_oracle()

### Community 179 - "Community 179"
Cohesion: 0.22
Nodes (4): _load(), test_every_config_parses_and_has_no_duplicate_keys(), test_the_lead_times_match_the_api_s_own_copy(), test_the_load_shed_comment_still_describes_the_real_reduced_count()

### Community 180 - "Community 180"
Cohesion: 0.25
Nodes (8): 12, 120, 24, 36, 48, 72, 96, climatological_cone_nm

### Community 181 - "Community 181"
Cohesion: 0.25
Nodes (8): CP, 12, 120, 24, 36, 48, 72, 96

### Community 182 - "Community 182"
Cohesion: 0.25
Nodes (8): EP, 12, 120, 24, 36, 48, 72, 96

### Community 183 - "Community 183"
Cohesion: 0.25
Nodes (7): calibration_audit, cone_nominal_rate, intensity_nominal_rate, min_cases, verdict_margin, test_set_budget, max_evaluations_per_season

### Community 184 - "Community 184"
Cohesion: 0.25
Nodes (8): drift, min_samples, reference_flavor, shift_sigma, validation_loss, variance_ratio_limit, consecutive_required, threshold_fraction

### Community 185 - "Community 185"
Cohesion: 0.25
Nodes (8): promotion, flavor, new_basin_tolerance, primary_metric, reference_basin, require_manual_gate, split, basins()

### Community 186 - "Community 186"
Cohesion: 0.25
Nodes (5): _cron_run_offset_minutes(), test_a_config_change_redeploys_the_api(), test_both_images_copy_the_configs(), test_the_console_uses_the_same_scheduled_run_offset(), test_the_worker_cron_runs_at_the_configured_offset()

### Community 187 - "Community 187"
Cohesion: 0.29
Nodes (5): source_out(), DataSource, operational_sources(), pretrain_only_sources(), test_operational_sources_pass_the_guard()

### Community 188 - "Community 188"
Cohesion: 0.29
Nodes (4): deterministic(), cmd_cycle(), deterministic(), DeterministicForecast

### Community 189 - "Community 189"
Cohesion: 0.25
Nodes (4): _fetch_one(), _get(), _get_bytes(), NotPublished

### Community 190 - "Community 190"
Cohesion: 0.36
Nodes (4): file_record(), read_adeck(), read_cached_adecks(), test_read_cached_adecks_reads_gzip_and_records_missing_and_unreadable()

### Community 191 - "Community 191"
Cohesion: 0.32
Nodes (5): assert_not_operational(), _operational_substitute(), OperationalUseError, test_reading_era5_in_the_inference_path_is_refused(), test_reading_final_besttrack_in_the_inference_path_is_refused()

### Community 192 - "Community 192"
Cohesion: 0.25
Nodes (3): test_a_desynced_derived_champion_is_not_a_bar_a_servable_candidate_must_clear(), test_a_servable_derived_champion_is_still_a_real_bar(), test_derived_resync_records_the_champion_signature_and_ends_in_sync()

### Community 194 - "Community 194"
Cohesion: 0.29
Nodes (7): products, cone_percentile, landfall_threshold_nm, lead_hours, ri_alert_probability, ri_threshold_kt, ri_window_hours

### Community 195 - "Community 195"
Cohesion: 0.29
Nodes (7): skew_audit, alert_intensity_delta_kt, alert_track_delta_nm, audit_delay_days, lead_hours, min_samples, window_days

### Community 196 - "Community 196"
Cohesion: 0.57
Nodes (5): deploy-plan.sh script, touches(), touches_component(), touches_console(), why

### Community 197 - "Community 197"
Cohesion: 0.29
Nodes (7): env, IMAGE, JOB, PROJECT_ID, PUBLISH, REGION, REGISTRY

### Community 200 - "Community 200"
Cohesion: 0.33
Nodes (6): ensemble, climatological_cone_nm_by_basin, members, min_members_for_ensemble_cone, reduced_members, underdispersion_fraction

### Community 201 - "Community 201"
Cohesion: 0.33
Nodes (6): triggers, data_volume_threshold, nightly_latent_hour_utc, preseason_date, scheduled_monthly_day, suppress_nightly_latent_during_active_storms

### Community 202 - "Community 202"
Cohesion: 0.33
Nodes (6): update_job, workflow_dispatch, default, description, type, inputs

### Community 203 - "Community 203"
Cohesion: 0.33
Nodes (6): on, pull_request, push, paths, branches, paths

### Community 205 - "Community 205"
Cohesion: 0.40
Nodes (4): _saturation_vapor_pressure_hpa_array(), _specific_humidity_to_rh_pct(), test_specific_humidity_at_saturation_gives_rh_near_100(), test_specific_humidity_is_clipped_to_the_unit_range()

### Community 207 - "Community 207"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 208 - "Community 208"
Cohesion: 0.40
Nodes (3): WORLD_GEOJSON, WorldData, WorldFeatureProperties

### Community 209 - "Community 209"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 213 - "Community 213"
Cohesion: 0.67
Nodes (4): max, target, diffusion, diffusion

### Community 214 - "Community 214"
Cohesion: 0.67
Nodes (4): max, target, fusion, fusion

### Community 215 - "Community 215"
Cohesion: 0.67
Nodes (4): max, target, postprocess, postprocess

### Community 216 - "Community 216"
Cohesion: 0.67
Nodes (4): max, target, preprocess, preprocess

### Community 217 - "Community 217"
Cohesion: 0.83
Nodes (3): graphify(), normalise_graph(), build-graph.sh script

### Community 218 - "Community 218"
Cohesion: 0.50
Nodes (3): uvx, graphify, graphify-mcp

### Community 222 - "Community 222"
Cohesion: 0.67
Nodes (3): limit, lower_is_better, nhc_consensus_beat_rate_48h

### Community 223 - "Community 223"
Cohesion: 0.67
Nodes (3): track_error_120h_nm, limit, lower_is_better

### Community 224 - "Community 224"
Cohesion: 0.67
Nodes (3): track_error_48h_nm, limit, lower_is_better

## Knowledge Gaps
- **13 isolated node(s):** `$lib/registry/blocks/navigation/components/site.context.svelte`, `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627`, `RFC-5322` (+8 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2781 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Flavor` connect `Community 4` to `Community 0`, `Community 1`, `Community 3`, `Community 5`, `Community 6`, `Community 135`, `Community 10`, `Community 11`, `Community 139`, `Community 13`, `Community 15`, `Community 16`, `Community 20`, `Community 23`, `Community 24`, `Community 151`, `Community 26`, `Community 156`, `Community 29`, `Community 30`, `Community 31`, `Community 34`, `Community 35`, `Community 36`, `Community 40`, `Community 41`, `Community 45`, `Community 47`, `Community 49`, `Community 50`, `Community 51`, `Community 52`, `Community 54`, `Community 55`, `Community 57`, `Community 59`, `Community 61`, `Community 192`, `Community 65`, `Community 67`, `Community 198`, `Community 73`, `Community 74`, `Community 211`, `Community 84`, `Community 212`, `Community 88`, `Community 90`, `Community 91`, `Community 97`, `Community 106`, `Community 107`, `Community 109`, `Community 112`, `Community 117`, `Community 127`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 248 inferred relationships involving `Flavor` (e.g. with `DemoState` and `drift()`) actually correct?**
  _`Flavor` has 248 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$lib/registry/blocks/navigation/components/site.context.svelte`, `./.svelte-kit/tsconfig.json`, `RFC-3966` to the rest of the system?**
  _13 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.036548693037242654 - nodes in this community are weakly interconnected._
- **Why does `Track` connect `Community 12` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 135`, `Community 9`, `Community 10`, `Community 11`, `Community 13`, `Community 16`, `Community 20`, `Community 24`, `Community 25`, `Community 26`, `Community 27`, `Community 29`, `Community 30`, `Community 32`, `Community 34`, `Community 35`, `Community 36`, `Community 39`, `Community 41`, `Community 49`, `Community 50`, `Community 52`, `Community 54`, `Community 55`, `Community 59`, `Community 65`, `Community 67`, `Community 69`, `Community 73`, `Community 74`, `Community 84`, `Community 88`, `Community 91`, `Community 97`, `Community 102`, `Community 105`, `Community 107`, `Community 112`, `Community 114`, `Community 122`, `Community 127`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 135 inferred relationships involving `Track` (e.g. with `save_cycle_inputs()` and `StormState`) actually correct?**
  _`Track` has 135 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.03698685814930226 - nodes in this community are weakly interconnected._