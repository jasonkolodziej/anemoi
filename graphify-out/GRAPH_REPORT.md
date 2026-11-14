# Graph Report - anemoi  (2026-11-14)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 6746 nodes · 17261 edges · 249 communities (223 shown, 26 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 2519 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `96c67fac`
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
- Community 241
- Community 242
- Community 243
- Community 244
- Community 245
- Community 247
- Community 248

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
- `make_window()` --calls--> `StageWindow`  [INFERRED]
  tests/test_streaming.py → src/anemoi/training/real_run.py
- `test_internal_calibration_audit_route_reports_new_samples()` --uses--> `RealState`  [INFERRED]
  tests/test_api_real_state.py → src/anemoi/api/real_state.py
- `test_trained_basins_without_champions_is_the_atlantic()` --uses--> `ModelRegistry`  [INFERRED]
  tests/test_registry.py → src/anemoi/tracking/registry.py
- `test_cache_round_trip_and_vector()` --uses--> `FetchTask`  [INFERRED]
  tests/test_steering.py → src/anemoi/data/gridded_cache.py
- `test_a_versions_arch_params_change_what_is_described()` --calls--> `describe()`  [INFERRED]
  tests/test_model_architecture.py → src/anemoi/models/architecture.py

## Import Cycles
- None detected.

## Communities (249 total, 26 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (81): augment_track(), emulate_working_track(), WorkingTrackNoise, displacement_nm(), basin_one_hot(), with_basin_channels(), with_basin_columns(), with_basin_vector() (+73 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (106): cmd_adeck_fetch(), cmd_era5_cache(), cmd_gdas_cache(), _cmd_gridded_cache(), cmd_splits(), cmd_steering_cache(), cmd_train(), _localize_caches() (+98 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (66): apply_cold_wake(), area_mean(), assert_flavor(), cold_wake_sst_depression_c(), compare_potential_intensity_estimates(), compute_environment_features(), deep_layer_shear(), emanuel_potential_intensity() (+58 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (73): run_fetch_cache(), archive_key(), ArchiveClient, build_fetch_tasks(), cache_path(), _decode_cached_fields(), FetchCacheReport, FetchTask (+65 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (83): getCycle(), getSchedule(), health(), listStorms(), CyclePlanOut, at(), calendarValue, hour (+75 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (51): Props, Section, SectionPage, { sections }, height, motionClass, Props, {
    size = 28,
    spinning = false,
    class: className,
    ...restProps
  } (+43 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (45): cmd_baseline_backtest(), Adeck, storm_basin(), OfficialErrors, assemble_validation_forecasts(), BaselineBacktestError, _displacement(), dump_validation_forecasts() (+37 more)

### Community 7 - "Community 7"
Cohesion: 0.06
Nodes (48): cycle_inputs_prefix(), cycle_key(), _get_text(), list_cycle_labels(), load_cycle_result(), load_drift_live(), _put_text(), save_cycle_inputs() (+40 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (31): experiment_name(), assert_deployable(), CurriculumError, stage_a(), stage_b(), DiffusionArtifacts, FusionArtifacts, test_both_stages_label_from_final_besttrack() (+23 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (57): brier_score(), crps_ensemble(), _crps_rows(), crps_series(), ensemble_percentiles(), rank_histogram(), reliability(), spread_skill() (+49 more)

### Community 10 - "Community 10"
Cohesion: 0.04
Nodes (60): layerchart@^2.5.1, DriftReportOut, IntensityPercentiles, LeadCalibrationOut, ModelCatalog, SkewReportOut, TrackPointOut, BY_ARCHITECTURE (+52 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (8): cycle_payload_out(), cycle_result_out(), provenance_out(), CycleHistory, RealState, ensemble(), RealStormState, CycleOutput

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (46): @lucide/svelte@^1.71.0, svelte-sonner@^1.2.3, sveltekit-superforms@^2.31.0, authClient, { form }, Props, { form }, Props (+38 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (34): deterministic(), live_fields(), _synthetic_fallback_deterministic(), DeterministicForecast, fusion_weights(), basin_inputs(), steering_inputs(), collect_validation_forecasts() (+26 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (36): AvailabilityOracle, CycleInputs, earliest_ready_time(), InputStatus, LatencyOracle, resolve_cycle_inputs(), _valid_time_for(), Role (+28 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (40): _baseline_inputs(), _empty_report(), _fake_checkpoint_store(), _hurdat2_storm(), make_args(), make_track(), _retrain_check_args(), _spy_assign_splits() (+32 more)

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (52): ApiError, apiFetch(), getActivePin(), getArchitecture(), getCalibration(), getDrift(), getDriftAll(), getModelRegistry() (+44 more)

### Community 17 - "Community 17"
Cohesion: 0.05
Nodes (34): _crop_variable(), fetch_real_satellite_crop(), _find_real_scan(), GoesFetchError, _lazy_open(), _list_scan_keys(), _nearest_scan_key(), _parse_scan_start() (+26 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (29): cmd_ablation(), cmd_atcf_archive(), cmd_cache_localize(), cmd_consistency_distill(), cmd_drift_reference_fit(), cmd_hurdat2_fetch(), cmd_noise_calibrate(), cmd_registry_pull() (+21 more)

### Community 19 - "Community 19"
Cohesion: 0.06
Nodes (50): @cloudflare/containers@^0.3.7, AppAuth, buildAuth(), getAuth(), verifyApiKey(), CYCLE_STEP, cycleInstanceId(), CycleParams (+42 more)

### Community 20 - "Community 20"
Cohesion: 0.06
Nodes (33): audit_one(), audit_run(), _AuditPlan, _fix_from_dict(), _fix_to_dict(), list_operational_records(), OperationalCycleRecord, _prune_samples() (+25 more)

### Community 21 - "Community 21"
Cohesion: 0.06
Nodes (31): check_run(), CycleConflict, _existing_source(), InFlight, operator_ids(), RunRequest, stored_source(), RunInfo (+23 more)

### Community 22 - "Community 22"
Cohesion: 0.06
Nodes (36): build_cone(), build_products(), climatological_cone_nm(), cone_radius_from_spread(), ConeSegment, deterministic_center(), EnsembleMember, intensity_pdf() (+28 more)

### Community 23 - "Community 23"
Cohesion: 0.08
Nodes (23): ModelRegistry, ModelVersion, Stage, _champions(), test_a_basin_is_served_once_every_champion_is_verified_in_it(), test_a_champion_verified_nowhere_serves_no_basin_as_in_distribution(), test_no_champion_or_champions_from_before_the_tag_are_the_atlantic(), _reconcile_args() (+15 more)

### Community 24 - "Community 24"
Cohesion: 0.05
Nodes (32): Archive, archives_for(), describe(), fetch_latest_hurdat2(), last_season(), latest_name(), manifest_path(), season_boundaries() (+24 more)

### Community 25 - "Community 25"
Cohesion: 0.05
Nodes (34): svelte-guard@^1.1.1, authHandle(), guards, handle, Auth, _authByRequest, buildAuth(), checkRegistrationOpen() (+26 more)

### Community 26 - "Community 26"
Cohesion: 0.07
Nodes (34): adeck_name(), adeck_path(), adeck_urls(), AdeckFetchReport, CachedAdecks, _check_adeck(), _check_official_errors(), fetch_adecks() (+26 more)

### Community 27 - "Community 27"
Cohesion: 0.06
Nodes (26): require_meta(), steering_meta(), _context_features(), _displacement_to_absolute(), _empty_samples(), _extract_for_tracks(), extract_joint_latents(), extract_validation_latents() (+18 more)

### Community 28 - "Community 28"
Cohesion: 0.06
Nodes (31): _files(), localize_cache(), LocalizeReport, _raise(), fetch_current_storm_ids(), fetch_current_storms(), fetch_live_track(), fetch_live_tracks() (+23 more)

### Community 29 - "Community 29"
Cohesion: 0.08
Nodes (30): invalidated_by(), evaluate_all(), expand_jobs(), nightly_latent(), on_data_volume(), on_drift(), on_latent_desync(), on_skew() (+22 more)

### Community 30 - "Community 30"
Cohesion: 0.11
Nodes (32): cmd_cycle(), deterministic(), climatological_ensemble(), run_cycle(), plan_cycle(), deterministic_fn(), good_ensemble(), make_fix() (+24 more)

### Community 31 - "Community 31"
Cohesion: 0.07
Nodes (19): absolute_pairs(), basin_key(), per_basin_scores(), sample_counts(), LeadCalibration, ForecastPoint, LeadTimeStats, to_metric_dict() (+11 more)

### Community 32 - "Community 32"
Cohesion: 0.06
Nodes (43): ModelVersionOut, SourceOut, byUse(), hasUnknownEntry(), MODEL_NAMES, MODELS, ORDER, readersOf() (+35 more)

### Community 33 - "Community 33"
Cohesion: 0.06
Nodes (45): ArchitectureOut, CyclePayload, CycleProducts, CycleResult, FeatureDriftOut, HealthOut, LayerOut, ProvenanceOut (+37 more)

### Community 34 - "Community 34"
Cohesion: 0.08
Nodes (29): batch_graph(), build_gnn_samples(), build_mesh_topology(), GnnStageSamples, MeshTopology, _node_features(), _standardize_x(), _standardize_y() (+21 more)

### Community 35 - "Community 35"
Cohesion: 0.07
Nodes (28): bearing_deg(), bearings_deg(), cross_along_track_nm(), cross_along_track_nms(), haversine_nm(), km_to_nm(), nm_to_km(), offset_position() (+20 more)

### Community 36 - "Community 36"
Cohesion: 0.07
Nodes (26): cycle_products_out(), god_out(), model_catalog(), get_model_architecture(), schedule(), ArchitectureOut, ConeSegmentOut, CyclePayload (+18 more)

### Community 37 - "Community 37"
Cohesion: 0.10
Nodes (25): case_errors(), compared_members(), homogeneous_mask(), _limiting(), _mean(), Member, MemberScore, _paired() (+17 more)

### Community 38 - "Community 38"
Cohesion: 0.09
Nodes (26): ExecutionMode, Task, fake_load_run_artifacts(), _FakeJointLatents, _register_group1_versions(), runner(), fake_extract_joint_latents(), make_fake() (+18 more)

### Community 39 - "Community 39"
Cohesion: 0.09
Nodes (17): cycle_plan_out(), StageOut, cmd_schedule(), CyclePlan, derive_vitals_timeout(), plan_day(), _schedule_stages(), ScheduledStage (+9 more)

### Community 40 - "Community 40"
Cohesion: 0.09
Nodes (23): advisory_time(), cycle_label(), floor_synoptic(), is_synoptic(), next_synoptic(), NWPUnavailableError, parse_cycle_label(), require_synoptic() (+15 more)

### Community 41 - "Community 41"
Cohesion: 0.08
Nodes (19): _created_date(), creation_day(), cycle_date(), _declared_length(), decode_ohc(), detect_format(), _grid_values(), name_day_for_creation() (+11 more)

### Community 42 - "Community 42"
Cohesion: 0.09
Nodes (24): count_untrained_fixes(), latent_signature(), RegistryError, full_set(), register_group1(), _stage_all(), test_champion_is_none_with_no_versions_registered(), test_checkpoint_uri_defaults_to_none_when_not_given() (+16 more)

### Community 43 - "Community 43"
Cohesion: 0.05
Nodes (40): devDependencies, cn@^0.3.3, @fontsource-variable/geist@^5.3.0, @fontsource-variable/geist-mono@^5.3.0, @fontsource-variable/inter@^5.3.0, formsnap@^2.0.1, mode-watcher@^1.1.0, @playwright/test@^1.63.0 (+32 more)

### Community 44 - "Community 44"
Cohesion: 0.08
Nodes (20): fetch_and_parse_ndbc(), fetch_ndbc_realtime2(), _get(), NdbcFetchError, NdbcObservation, parse_ndbc_realtime2(), test_a_row_with_the_wrong_column_count_is_skipped_not_fatal(), test_a_station_missing_wave_columns_still_parses() (+12 more)

### Community 45 - "Community 45"
Cohesion: 0.05
Nodes (17): client(), hurdat2_file(), test_a_basin_is_in_distribution_once_every_served_model_is_verified_in_it(), test_a_stale_refresh_in_flight_serves_known_storms_without_waiting(), test_concurrent_requests_share_one_live_feed_fetch(), test_debug_last_deterministic_error_route_needs_opt_in(), test_demo_state_is_unaffected_by_default(), test_internal_calibration_audit_route_reports_new_samples() (+9 more)

### Community 46 - "Community 46"
Cohesion: 0.10
Nodes (25): by_basin(), complete_run(), _forecasts(), metric_set(), test_a_basin_is_verified_when_the_model_beats_persistence_there(), test_a_basin_validated_but_never_trained_on_is_not_verified(), test_a_candidate_that_loses_a_verified_basin_is_refused(), test_a_candidate_that_scored_no_basin_is_judged_as_before() (+17 more)

### Community 47 - "Community 47"
Cohesion: 0.11
Nodes (6): get_state(), require_api_key(), state_dependency(), _lifespan(), get_real_state(), storm_stream()

### Community 48 - "Community 48"
Cohesion: 0.07
Nodes (39): dependencies, arktype@^2.2.7, better-auth@^1.7.7, @better-auth/passkey@^1.7.7, bits-ui@^2.20.6, clsx@^2.1.1, d3-polygon@^3.0.1, d3-scale@^4.0.2 (+31 more)

### Community 49 - "Community 49"
Cohesion: 0.07
Nodes (30): ConeSegmentOut, FixOut, bounds, colors, coneFeatures, coneHull, currentFix, forecastLine (+22 more)

### Community 50 - "Community 50"
Cohesion: 0.10
Nodes (19): _decode_one_sonde(), DropsondeFetchError, DropsondeProfile, fetch_and_parse_dropsonde_mission(), fetch_dropsonde_mission_tarball(), _ftp_connect(), list_dropsonde_missions(), _mask_missing() (+11 more)

### Community 51 - "Community 51"
Cohesion: 0.10
Nodes (26): build_lstm(), encode(), forward(), __init__(), test_gru_variant_builds(), test_invalid_cell_is_rejected(), test_lstm_shapes_and_latent(), _fake_checkpoint_store() (+18 more)

### Community 52 - "Community 52"
Cohesion: 0.10
Nodes (20): build_pinn_samples(), _filter_and_fit_env_stats(), _PinnWindowDataset, train_pinn_stage(), cache_all_fixes(), make_fields(), make_track(), _task_for() (+12 more)

### Community 53 - "Community 53"
Cohesion: 0.09
Nodes (20): recommend_extra_conditioning(), run_spread_backtest(), SpreadBacktestError, _fake_val(), _FakeS3Client, _lc(), patched(), fake_extract() (+12 more)

### Community 54 - "Community 54"
Cohesion: 0.11
Nodes (18): CycleResult, audit_cycle(), _CountingClient, _FakeClient, _fix(), _result(), test_a_cycle_stored_before_the_ri_interval_still_loads(), test_a_sample_persisted_before_ensemble_size_was_tracked_still_loads() (+10 more)

### Community 55 - "Community 55"
Cohesion: 0.08
Nodes (18): _adeck_position(), _adeck_positive(), AdeckPoint, pair_by_valid_time(), parse_bdeck(), _parse_latlon(), parse_tcvitals(), TcVitalsError (+10 more)

### Community 56 - "Community 56"
Cohesion: 0.10
Nodes (22): Hurdat2Error, _parse_data_row(), _parse_header(), parse_hurdat2(), parse_hurdat2_file(), parse_hurdat2_statuses(), _parse_latlon(), _storm_rows() (+14 more)

### Community 57 - "Community 57"
Cohesion: 0.11
Nodes (18): disc_mean(), fetch_lead_flow(), group_by_time(), lead_flow(), LeadFlow, load_steering(), run_steering_cache(), fetch() (+10 more)

### Community 58 - "Community 58"
Cohesion: 0.06
Nodes (35): context, dockerfile, postgres, AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY, MLFLOW_S3_ENDPOINT_URL, POSTGRES_DB (+27 more)

### Community 59 - "Community 59"
Cohesion: 0.12
Nodes (20): _bytemap_path(), decode_ssmis_bytemap(), fetch_and_decode_ssmis_daily(), fetch_ssmis_daily_bytemap(), MicrowaveFetchError, RSSFtpCredentials, SSMISDaily, _make_bytemap() (+12 more)

### Community 60 - "Community 60"
Cohesion: 0.11
Nodes (23): _check_basin(), expected_coordinates(), _decode(), files(), local(), _ohc(), _row_col(), server() (+15 more)

### Community 61 - "Community 61"
Cohesion: 0.11
Nodes (22): archive_atcf(), ArchiveReport, currentstorms_key(), _digest(), snapshot_key(), _stored_digests(), _write_if_new(), _fetcher() (+14 more)

### Community 62 - "Community 62"
Cohesion: 0.10
Nodes (27): assert_input_safe(), emulate_working_fix(), recalibrate_from_pairs(), _latlon(), make_fix(), make_track(), test_assert_input_safe_allows_working_quality(), test_assert_input_safe_blocks_final_quality() (+19 more)

### Community 63 - "Community 63"
Cohesion: 0.13
Nodes (25): storm_relative_sequence(), validate(), test_extrapolation_continues_the_last_motion_vector(), test_displacement_to_latlon_round_trips_with_displacement_nm(), make_fix(), test_displacement_direction_matches_bearing(), test_displacement_magnitude_matches_haversine_distance(), test_displacement_nm_matches_storm_relative_sequence() (+17 more)

### Community 64 - "Community 64"
Cohesion: 0.12
Nodes (20): AblationCell, AblationReport, build_samples(), train_cell(), _cell(), make_track(), test_at_fraction_filters_and_sorts_by_hidden_dim(), test_build_samples_augmentation_multiplies_sample_count() (+12 more)

### Community 65 - "Community 65"
Cohesion: 0.07
Nodes (21): rehype-slug@^6.0.0, rehype-stringify@^10.0.1, remark-gfm@^4.0.1, remark-rehype@^11.1.2, unified@^11.0.5, unist-util-visit@^5.1.0, CONSOLE_ROOT, force (+13 more)

### Community 66 - "Community 66"
Cohesion: 0.11
Nodes (27): QUICK, addVirtualAuthenticator(), EMAIL_DIR, EMAIL_LOCK, listEmailFiles(), localD1(), setRegistrationOpen(), signUpViaMagicLink() (+19 more)

### Community 67 - "Community 67"
Cohesion: 0.06
Nodes (28): AsyncReturnType, Expand, ExtractGenericViewableContent, GenericItem, GenericSelectorOption, GenericSnippetProps, GenericViewableContent, InheritedSnippetProps (+20 more)

### Community 68 - "Community 68"
Cohesion: 0.09
Nodes (21): get(), used_by(), test_cmd_sources_prints_who_uses_each_source(), _model_sources(), test_a_label_or_verification_source_is_never_a_model_input(), test_a_model_input_is_never_a_labels_only_source(), test_a_verification_source_not_read_yet_is_verification_and_nothing_else(), test_each_curriculum_stage_lists_what_its_models_read() (+13 more)

### Community 69 - "Community 69"
Cohesion: 0.10
Nodes (14): baseline_beaten(), build_run_tags(), _git_commit(), _gpu_type(), log_curriculum_stages(), log_stage_run(), stage_run_record(), _storm_split() (+6 more)

### Community 70 - "Community 70"
Cohesion: 0.14
Nodes (17): cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_a_basin_with_no_cached_fields_was_not_trained_on(), test_build_cnn_samples_empty_when_nothing_cached(), test_build_cnn_samples_rejects_ragged_cached_shapes() (+9 more)

### Community 71 - "Community 71"
Cohesion: 0.06
Nodes (31): data, basins, stage_a, epochs, flavor, input_sources, label_source, learning_rate (+23 more)

### Community 72 - "Community 72"
Cohesion: 0.07
Nodes (10): _FakeS3Config, test_checkpoint_store_push_failure_degrades_to_local_only(), test_checkpoint_store_push_mirrors_registry_json_after_every_save(), test_pull_failure_degrades_to_an_empty_registry(), test_pull_from_checkpoint_store_hydrates_a_missing_local_registry(), test_pull_is_a_noop_when_the_key_does_not_exist_remotely_yet(), test_pull_is_skipped_entirely_without_a_checkpoint_store(), test_pull_reconciles_with_durable_storage_even_when_local_already_exists() (+2 more)

### Community 73 - "Community 73"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, env, GH_TOKEN, GRAPHIFY_VERSION, permissions, runs-on (+22 more)

### Community 74 - "Community 74"
Cohesion: 0.15
Nodes (15): audit_due(), SkewMonitor, SkewReport, sample(), test_audit_becomes_due_once_era5t_lands(), test_audit_is_not_due_immediately_after_the_cycle(), test_intensity_delta_is_signed_toward_the_operational_run(), test_intensity_skew_alone_can_raise_an_alert() (+7 more)

### Community 75 - "Community 75"
Cohesion: 0.12
Nodes (13): Fetcher, FetchError, ingest_cycle_inputs(), ingest_one(), IngestionOutcome, IngestionRecord, LakeTier, LakeWriter (+5 more)

### Community 76 - "Community 76"
Cohesion: 0.12
Nodes (16): _FakeS3Client, _make_version(), _real_builder(), _register_like_training(), _store(), test_load_run_artifacts_rebuilds_pinns_candidate_and_env_stats(), test_load_run_artifacts_refuses_a_version_without_standardisation_stats(), test_load_run_artifacts_round_trips_a_real_training_runs_artifacts() (+8 more)

### Community 77 - "Community 77"
Cohesion: 0.08
Nodes (15): _expected_meta(), test_a_failed_time_is_reported_and_the_others_still_written(), fetch(), test_a_lost_race_with_no_file_appearing_raises_the_write_error(), test_cache_round_trip_and_vector(), test_disc_mean_is_symmetric_for_a_field_linear_in_longitude(), test_features_advect_with_the_flow_plus_beta_drift(), test_features_raise_where_there_is_no_flow() (+7 more)

### Community 78 - "Community 78"
Cohesion: 0.11
Nodes (19): _curriculum_tracks(), _FakeS3Client, _fields(), make_track(), test_a_zero_steering_conv_computes_the_plain_model(), test_builder_without_steering_keeps_the_old_layout(), test_curriculum_refuses_steering_without_streaming_or_without_the_cache_meta(), test_curriculum_without_steering_records_no_n_steering() (+11 more)

### Community 79 - "Community 79"
Cohesion: 0.07
Nodes (29): WithElementRef, ButtonClickEvent, PrimitiveAnchorAttributes, PrimitiveButtonAttributes, PrimitiveCanvasAttributes, PrimitiveDivAttributes, PrimitiveElementAttributes, PrimitiveFigureAttributes (+21 more)

### Community 80 - "Community 80"
Cohesion: 0.09
Nodes (4): DemoState, deterministic(), StormState, LeadProductCalibration

### Community 81 - "Community 81"
Cohesion: 0.08
Nodes (9): build_derived_schedule(), _latent_task(), OrchestrationResult, ResourceProfile, Schedule, _train_task(), validate_schedule(), Wave (+1 more)

### Community 82 - "Community 82"
Cohesion: 0.08
Nodes (28): @better-auth/api-key@^1.7.7, @types/node@^26.6.4, typescript@^5.9.3, wrangler@^4.147.0, @better-auth/api-key, @types/node, typescript, wrangler (+20 more)

### Community 83 - "Community 83"
Cohesion: 0.07
Nodes (28): inputArgs, jobs, projectId, region, results, timeoutSeconds, assign, return (+20 more)

### Community 84 - "Community 84"
Cohesion: 0.11
Nodes (15): config_copy(), edit(), _cron_run_offset_minutes(), _image_layout(), _run(), test_a_config_change_redeploys_the_api(), test_a_missing_config_dir_is_refused(), test_an_image_without_configs_fails_at_import_and_says_why() (+7 more)

### Community 85 - "Community 85"
Cohesion: 0.12
Nodes (14): initial_fix(), TrackQuality, client(), _MemoryS3, s3(), test_an_archive_storm_says_its_fix_is_the_final_best_track(), test_late_vitals_on_a_live_storm_read_as_estimated(), test_missing_vitals_are_extrapolated_and_estimated() (+6 more)

### Community 86 - "Community 86"
Cohesion: 0.11
Nodes (16): fetch_ohc_file(), ohc_url(), select_file(), sshae_baseline(), Archive, _full_archive(), test_a_cycle_time_must_be_a_synoptic_utc_time(), test_a_missing_file_steps_back_one_creation_day() (+8 more)

### Community 87 - "Community 87"
Cohesion: 0.10
Nodes (14): SpreadSkill, distill_consistency_model(), step_loss(), _pseudo_huber(), _fake_samples(), _lc(), _report(), _stats() (+6 more)

### Community 88 - "Community 88"
Cohesion: 0.10
Nodes (7): ModelSpec, torch_available(), _cosine_schedule(), __getattr__(), pytest_collection_modifyitems(), test_require_torch_message_names_the_extra(), test_spec_output_dim_is_leads_times_outputs()

### Community 89 - "Community 89"
Cohesion: 0.17
Nodes (23): build_schedule(), Mode, run_schedule(), RunOutcome, failing_runner(), runner(), ok_runner(), test_both_schedules_validate() (+15 more)

### Community 90 - "Community 90"
Cohesion: 0.13
Nodes (20): build_live_lstm_x(), build_live_pinn_x(), _current_window(), cache_current_fix(), candidate_model(), make_fields(), make_track(), test_build_live_cnn_x_is_none_without_a_cached_field_and_the_live_fetch_fails() (+12 more)

### Community 91 - "Community 91"
Cohesion: 0.10
Nodes (14): _default_fetch_fn(), fetch(), era5_to_gridded_fields(), crop(), crop_levels(), fetch_era5t_one(), open_era5(), open_era5_store() (+6 more)

### Community 92 - "Community 92"
Cohesion: 0.13
Nodes (13): build_real_ensemble_fn(), cache_current_fix(), _FakeS3Client, make_track(), _register(), _register_all_five_and_diffusion(), _store(), test_build_real_ensemble_fn_produces_real_finite_members() (+5 more)

### Community 93 - "Community 93"
Cohesion: 0.12
Nodes (12): _standardize(), _standardize_y(), train_diffusion_stage(), _FakeS3Client, _make_samples(), test_a_longer_epoch_budget_never_returns_a_worse_val_loss(), test_early_stopping_halts_before_the_epoch_cap_on_a_real_overfitting_run(), test_run_diffusion_curriculum_uploads_a_checkpoint_and_registers_stage_b() (+4 more)

### Community 94 - "Community 94"
Cohesion: 0.11
Nodes (15): _FakeCycleOutput, _fresh_real_state(), _make_deterministic_forecast(), _make_storm_state(), _memory_store(), _MemoryS3Client, test_a_failed_cycle_write_never_fails_the_cycle(), test_an_unrestored_drift_window_is_never_written_back() (+7 more)

### Community 95 - "Community 95"
Cohesion: 0.10
Nodes (12): color_for(), god(), Module, WindGod, test_every_god_color_is_distinct(), test_experiment_name_handles_fusion_without_raising(), test_experiment_names_are_the_god_slugs(), test_lookup_by_slug_and_by_architecture_agree() (+4 more)

### Community 96 - "Community 96"
Cohesion: 0.11
Nodes (14): adeck_text(), adecks(), archive(), archive_text(), cases(), _row(), _row_of(), storm_text() (+6 more)

### Community 97 - "Community 97"
Cohesion: 0.16
Nodes (13): cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_build_transformer_samples_empty_when_nothing_cached(), test_build_transformer_samples_rejects_a_cache_smaller_than_grid_size(), test_build_transformer_samples_trims_the_real_41x41_crop_to_grid_size() (+5 more)

### Community 98 - "Community 98"
Cohesion: 0.11
Nodes (11): runed@^0.37.1, App, Locals, Platform, DEFAULT_EXTRA, ExtraPreferences, PackageManager, UserContext (+3 more)

### Community 99 - "Community 99"
Cohesion: 0.14
Nodes (14): _all_tensors(), Architecture, _builder(), describe(), describe_cached(), _describe_cached(), hook(), _example_inputs() (+6 more)

### Community 100 - "Community 100"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GH_TOKEN, IMPORTED_FROM, SOURCE_SHA, jobs, publish (+16 more)

### Community 101 - "Community 101"
Cohesion: 0.12
Nodes (10): _download(), fetch_oisst_sst(), require_sst_deps(), sst_at(), SstFetchError, _small_grid(), test_fetch_oisst_sst_reads_real_recent_data(), test_sst_at_finds_the_nearest_cell() (+2 more)

### Community 102 - "Community 102"
Cohesion: 0.13
Nodes (14): _bilinear(), _lattice_index(), ohc_at(), ohc_global(), OhcField, place(), test_a_blank_run_longer_than_the_window_leaves_na_unavailable(), test_a_degraded_basin_flags_the_field() (+6 more)

### Community 103 - "Community 103"
Cohesion: 0.08
Nodes (3): client(), test_more_members_than_the_ensemble_runs_is_refused_not_silently_capped(), test_sources_say_who_uses_each_one()

### Community 104 - "Community 104"
Cohesion: 0.14
Nodes (10): fetch_gefs_ensemble_grib2_fields(), fetch_gefs_member_grib2_fields(), _gefs_member_url(), _parse_grib2_index(), test_control_member_zero_uses_gec00_not_gep00(), test_fetch_gefs_ensemble_reads_multiple_real_distinct_members(), test_fetch_gefs_member_reads_the_real_noaa_archive(), test_member_out_of_range_raises() (+2 more)

### Community 105 - "Community 105"
Cohesion: 0.11
Nodes (11): calibration_out(), drift_report_out(), skew_report_out(), calibration(), drift(), drift_all(), skew(), FeatureDriftOut (+3 more)

### Community 106 - "Community 106"
Cohesion: 0.17
Nodes (12): accessed(), _check_type(), config_dir(), ConfigError, fixed(), get(), get_list(), _load() (+4 more)

### Community 107 - "Community 107"
Cohesion: 0.18
Nodes (16): run_fetch_cache(), make_fields(), make_track(), test_run_fetch_cache_defaults_to_lower_concurrency_than_era5(), test_run_fetch_cache_drops_fixes_before_the_real_archive_start_by_default(), fake_fetch(), test_run_fetch_cache_floor_drops_the_fix_just_before_and_keeps_the_one_at_it(), fake_fetch() (+8 more)

### Community 108 - "Community 108"
Cohesion: 0.13
Nodes (15): _crop_box(), crop(), _global_grid_with_marker(), _synthetic_era5_dataset(), _synthetic_gdas_fields(), test_crop_box_centers_on_the_requested_lat_lon(), test_crop_box_rejects_the_wrong_global_shape(), test_crop_box_shape_matches_requested_box_degrees() (+7 more)

### Community 109 - "Community 109"
Cohesion: 0.15
Nodes (10): DriftError, ReferenceDistribution, reference_from_json(), reference_to_json(), save_reference(), test_drift_report_detects_real_drift_once_enough_samples_are_collected(), test_drift_report_is_honest_zero_for_a_model_that_never_contributed(), test_reference_must_be_the_stage_b_distribution() (+2 more)

### Community 110 - "Community 110"
Cohesion: 0.20
Nodes (15): evaluate_promotion(), complete_run(), good_metrics(), test_candidate_worse_than_incumbent_is_not_staged(), test_era5_flavor_metrics_cannot_gate_promotion(), test_first_candidate_is_staged(), test_missing_metric_is_reported_as_a_failure(), test_non_finite_candidate_does_not_beat_an_incumbent_either() (+7 more)

### Community 111 - "Community 111"
Cohesion: 0.14
Nodes (11): require_torch(), coriolis_parameter(), physics_residuals(), compile_model(), test_compile_model_does_not_raise_on_cpu(), test_compile_model_rejects_non_module_input(), test_compile_model_skips_compilation_on_mps(), test_get_device_falls_back_to_cpu_when_no_gpu_backend_is_available() (+3 more)

### Community 112 - "Community 112"
Cohesion: 0.13
Nodes (14): http_get(), OhcFetchError, OhcNotPublished, OhcUnavailable, test_a_cut_off_reply_is_a_fetch_failure(), test_a_cut_off_transfer_raises_rather_than_reading_an_older_file(), test_a_fetch_failure_that_is_not_a_404_is_not_stepped_over(), flaky() (+6 more)

### Community 113 - "Community 113"
Cohesion: 0.13
Nodes (12): build_diffusion(), __init__(), _consistency_model(), test_consistency_accepts_extra_conditioning(), test_consistency_boundary_condition_is_exact_at_step_zero(), test_consistency_multistep_sampling_matches_one_step_shape_and_is_deterministic(), test_consistency_one_step_sampling_produces_distinct_members(), test_diffusion_accepts_extra_conditioning() (+4 more)

### Community 114 - "Community 114"
Cohesion: 0.17
Nodes (13): detect_feature_drift(), ValidationLossMonitor, reference(), test_a_recovery_resets_the_consecutive_count(), test_collapsed_variance_is_detected(), test_feature_count_mismatch_raises(), test_first_observation_only_sets_the_baseline(), test_increases_below_the_threshold_never_trigger() (+5 more)

### Community 115 - "Community 115"
Cohesion: 0.14
Nodes (10): lr_factor(), transformer_optim(), TransformerOptim, TransformerOptimizer, test_a_short_stage_still_ends_on_the_floor(), test_config_values_are_validated(), test_cosine_decays_to_the_floor_on_the_last_update(), test_no_warmup_starts_at_the_peak() (+2 more)

### Community 116 - "Community 116"
Cohesion: 0.23
Nodes (12): cache_current_fix(), make_track(), _register_real_version(), _store(), test_build_real_deterministic_fn_combines_all_four_real_models(), test_build_real_deterministic_fn_raises_with_no_registered_models(), test_build_real_deterministic_fn_uses_the_real_learned_fusion_with_all_five(), test_deterministic_fn_reports_missing_standardisation_stats_by_name() (+4 more)

### Community 117 - "Community 117"
Cohesion: 0.10
Nodes (20): PROJECT_NUMBER, PROJECT_PAT, types, jobs, sync, name, on, issues (+12 more)

### Community 118 - "Community 118"
Cohesion: 0.13
Nodes (12): expand_patch_channels(), track_errors_nm(), _cache_steering(), make_track(), test_compare_refuses_arms_on_different_windows_and_pairs_the_rest(), test_expanded_patch_channels_start_as_the_same_function(), test_stage_b_trains_the_steering_conv_and_keeps_the_rest_frozen(), run() (+4 more)

### Community 119 - "Community 119"
Cohesion: 0.21
Nodes (6): freeCycleLabel(), label(), runFreshCycle(), signIn(), cases, @playwright/test

### Community 120 - "Community 120"
Cohesion: 0.15
Nodes (10): read_cached_official_errors(), OfficialErrorsError, parse_official_errors(), _signed(), test_a_cached_error_file_that_is_not_nhcs_is_named_with_the_way_out(), test_parse_official_errors_reads_columns_by_name_and_skips_missing_leads(), test_parse_official_errors_reads_the_stated_initial_position_domain(), test_parse_official_errors_rejects_a_file_without_the_column_header() (+2 more)

### Community 121 - "Community 121"
Cohesion: 0.13
Nodes (10): Fix, _current_fields(), fetch_live_nwp(), live_cache_path(), test_current_fields_fetches_on_demand_and_caches_the_result(), fake_fetch_one(), test_fetch_live_nwp_floor_is_inclusive_and_reads_the_first_atmos_cycle(), fix_at() (+2 more)

### Community 122 - "Community 122"
Cohesion: 0.15
Nodes (8): _default_fetch_fn(), fetch(), fetch_gdas_grib2_fields(), gdas_to_gridded_fields(), gfs_url(), test_gdas_archive_start_is_the_first_valid_time_with_an_atmos_f006(), test_fetch_gdas_grib2_fields_reads_the_real_noaa_archive(), test_fetch_gdas_grib2_fields_uses_a_passed_in_session_not_the_module()

### Community 123 - "Community 123"
Cohesion: 0.15
Nodes (10): _attributes(), _calls(), _function(), _imported(), _names_adapter(), _parameters(), _parse(), _string_literals() (+2 more)

### Community 124 - "Community 124"
Cohesion: 0.19
Nodes (6): DEFAULT_AFTER_LOGIN, loginHref(), safeNext(), requireSignIn(), requireSignInLoad(), guard()

### Community 125 - "Community 125"
Cohesion: 0.15
Nodes (8): load_reference(), _FakeClient, _make_reference(), test_durable_round_trip_via_a_shared_checkpoint_store(), test_json_round_trips_a_real_reference_exactly(), test_load_reference_degrades_honestly_when_the_store_is_unreachable(), test_load_reference_returns_none_when_nothing_was_ever_fit(), test_save_then_load_round_trips_via_the_local_file()

### Community 126 - "Community 126"
Cohesion: 0.12
Nodes (4): _Boto3Client, require_boto3(), _StorageClient, test_boto3_adapter_configures_the_client_for_the_given_endpoint()

### Community 127 - "Community 127"
Cohesion: 0.11
Nodes (7): client(), test_docs_route_is_unaffected(), test_sources_role_is_the_role_enum_in_the_openapi_schema(), test_sources_used_by_is_documented_in_the_openapi_schema(), test_theme_http_method_colors_are_distinct(), test_theme_never_uses_a_god_color(), _walk()

### Community 128 - "Community 128"
Cohesion: 0.11
Nodes (7): _FakeMlflowModelVersion, _mlflow_client_that_registers_and_transitions(), create_model_version(), test_mlflow_mirror_skips_create_registered_model_if_it_already_exists(), create_model_version(), test_mlflow_transition_also_mirrors_the_archived_incumbent(), create_model_version()

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
Cohesion: 0.21
Nodes (14): _fields(), _run(), test_a_cache_dir_holds_one_lead(), test_a_missing_t_minus_6_cycle_falls_back_to_t_minus_12(), fetch_one(), test_gfs_url_names_the_forecast_valid_at_the_time(), test_live_fields_come_from_the_t_minus_6_forecast(), fetch_one() (+6 more)

### Community 133 - "Community 133"
Cohesion: 0.12
Nodes (16): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+8 more)

### Community 134 - "Community 134"
Cohesion: 0.12
Nodes (16): compilerOptions, allowJs, allowSyntheticDefaultImports, checkJs, forceConsistentCasingInFileNames, isolatedModules, lib, module (+8 more)

### Community 135 - "Community 135"
Cohesion: 0.12
Nodes (16): permissions, runs-on, steps, jobs, copilot-setup-steps, name, on, pull_request (+8 more)

### Community 136 - "Community 136"
Cohesion: 0.16
Nodes (8): _overrides(), run_cycle(), assert_operational_flavor(), CycleError, extrapolate_fix(), ForecastProducts, test_extrapolation_needs_two_prior_fixes(), test_operational_flavor_guard_rejects_pretrain_features()

### Community 137 - "Community 137"
Cohesion: 0.13
Nodes (7): fetch_one(), steering_meta_digest(), gdas_likely_unpublished(), live_steering_path(), test_gdas_likely_unpublished_false_for_an_archived_storm(), test_gdas_likely_unpublished_false_once_real_typical_latency_has_passed(), test_gdas_likely_unpublished_true_within_real_typical_latency()

### Community 138 - "Community 138"
Cohesion: 0.26
Nodes (9): NoiseSensitivityReport, _result(), test_is_load_bearing_above_threshold(), test_is_not_load_bearing_below_threshold(), test_relative_change_is_zero_when_losses_match(), test_relative_change_rejects_nonpositive_default_loss(), test_relative_change_sign_matches_direction_of_the_move(), test_run_noise_sensitivity_covers_both_candidates_on_a_small_synthetic_archive() (+1 more)

### Community 139 - "Community 139"
Cohesion: 0.12
Nodes (16): with, build-args, cache-from, cache-to, context, file, load, password (+8 more)

### Community 140 - "Community 140"
Cohesion: 0.12
Nodes (15): jobs, lint-and-validate, name, permissions, runs-on, steps, name, on (+7 more)

### Community 141 - "Community 141"
Cohesion: 0.13
Nodes (8): source_out(), health(), models(), sources(), HealthOut, SourceOut, DataSource, pretrain_only_sources()

### Community 142 - "Community 142"
Cohesion: 0.13
Nodes (15): scripts, build, cf:deploy, check, check:errors, check:warnings, check:watch, dev (+7 more)

### Community 143 - "Community 143"
Cohesion: 0.19
Nodes (12): loading, onInput(), open, query, results, bodyById, buildIndex(), excerptAround() (+4 more)

### Community 144 - "Community 144"
Cohesion: 0.13
Nodes (15): env, environment, if, name, needs, permissions, runs-on, timeout-minutes (+7 more)

### Community 145 - "Community 145"
Cohesion: 0.19
Nodes (7): era5_deps_available(), fetch_grib2_messages(), gridded_deps_available(), require_era5_deps(), require_gdas_deps(), require_gridded_deps(), test_era5_deps_do_not_require_eccodes()

### Community 146 - "Community 146"
Cohesion: 0.14
Nodes (8): API, DEVELOP, PHONE, SourceRow, SOURCES, SOURCES_BEFORE_USED_BY, SOURCES_REWIRED, path()

### Community 147 - "Community 147"
Cohesion: 0.14
Nodes (13): compilerOptions, allowJs, checkJs, esModuleInterop, forceConsistentCasingInFileNames, moduleResolution, resolveJsonModule, rewriteRelativeImportExtensions (+5 more)

### Community 148 - "Community 148"
Cohesion: 0.14
Nodes (13): images, options, diskSizeGb, machineType, steps, args, entrypoint, env (+5 more)

### Community 149 - "Community 149"
Cohesion: 0.14
Nodes (14): default, description, type, default, description, type, api, console (+6 more)

### Community 150 - "Community 150"
Cohesion: 0.16
Nodes (11): build_cnn(), encode(), forward(), __init__(), build_gnn(), encode(), forward(), __init__() (+3 more)

### Community 151 - "Community 151"
Cohesion: 0.19
Nodes (7): al_2021_2022(), compare(), open_ocean(), parse_ships(), sample_days(), ShipsCase, test_sohc_equals_bilinear_ohc_on_the_file_named_for_the_day_before()

### Community 152 - "Community 152"
Cohesion: 0.17
Nodes (12): IdTokenClaims, JwtClaims, OidcAddressClaim, OidcStandardClaims, UserProfile, Mandatory, RFC-3966, RFC-4627 (+4 more)

### Community 153 - "Community 153"
Cohesion: 0.17
Nodes (5): get_custom_redoc_html(), create_app(), _debug_last_deterministic_error(), redoc_html(), test_debug_last_deterministic_error_route_reports_the_real_reason()

### Community 154 - "Community 154"
Cohesion: 0.18
Nodes (7): client(), test_a_registered_versions_arch_params_are_used(), test_a_version_without_arch_params_is_described_from_defaults(), test_a_versions_arch_params_change_what_is_described(), test_every_model_runs_its_example_input_and_reports_its_layers(), test_the_gnn_is_fed_the_real_lattice(), test_unknown_models_and_versions_are_404()

### Community 155 - "Community 155"
Cohesion: 0.15
Nodes (12): name, runs-on, timeout-minutes, concurrency, cancel-in-progress, group, jobs, build (+4 more)

### Community 156 - "Community 156"
Cohesion: 0.26
Nodes (6): get_cycle(), get_storm(), list_storms(), _served_basins(), _storm_summary(), FixOut

### Community 157 - "Community 157"
Cohesion: 0.19
Nodes (7): basin_value(), is_basin_key(), key_basin(), scored_basins(), trained_basins(), verified_basins(), reference_value()

### Community 158 - "Community 158"
Cohesion: 0.27
Nodes (6): PromotionError, TestSetBudget, test_budget_allows_a_limited_number_of_looks(), test_budget_exhaustion_raises(), test_budget_requires_a_justification(), test_budget_resets_across_seasons()

### Community 159 - "Community 159"
Cohesion: 0.18
Nodes (9): _get_real_state(), _stage_group1_and_derived(), test_a_live_storm_keeps_its_cycles_across_a_feed_refresh(), test_calibration_report_is_honest_empty_with_no_samples(), test_drift_report_is_honest_zero_when_no_reference_has_been_fit(), test_pending_retrain_jobs_detects_a_real_latent_desync(), test_pending_retrain_jobs_is_empty_for_a_coherent_registry(), test_pending_retrain_jobs_route_serves_a_real_latent_desync() (+1 more)

### Community 160 - "Community 160"
Cohesion: 0.17
Nodes (6): _called(), _modules(), test_an_adapter_is_named_by_other_code_only_if_its_source_is_read(), test_every_fetch_adapter_is_classified(), test_no_module_imports_by_a_computed_name(), _unread_sources()

### Community 161 - "Community 161"
Cohesion: 0.23
Nodes (11): max, target, budgets, reduced, standard, max, target, assembly (+3 more)

### Community 162 - "Community 162"
Cohesion: 0.17
Nodes (4): local, notes, problems, remote

### Community 163 - "Community 163"
Cohesion: 0.17
Nodes (11): concurrency, cancel-in-progress, group, jobs, test-api, name, if, name (+3 more)

### Community 164 - "Community 164"
Cohesion: 0.17
Nodes (12): with, cache, cache-dependency-path, enable-cache, fetch-depth, if-no-files-found, include-hidden-files, name (+4 more)

### Community 165 - "Community 165"
Cohesion: 0.23
Nodes (4): BasinChoice, test_a_cycle_reads_the_file_made_two_days_before(), test_a_real_file_from_each_chain(), test_the_flag_on_real_files()

### Community 166 - "Community 166"
Cohesion: 0.17
Nodes (6): test_mlflow_failure_degrades_to_local_only(), __getattr__(), test_mlflow_mirror_is_skipped_without_a_checkpoint_uri(), __getattr__(), test_mlflow_mirror_registers_model_then_version_with_a_real_source_uri(), create_model_version()

### Community 167 - "Community 167"
Cohesion: 0.24
Nodes (7): model_version_out(), get_active_pin(), get_model_registry(), list_registry(), ActivePin, ModelVersionOut, RegistryEntry

### Community 168 - "Community 168"
Cohesion: 0.18
Nodes (11): cycle, advisory_margin_minutes, advisory_offset_minutes, allow_estimated_vitals, allow_load_shedding, max_nwp_lag_hours, nominal_vitals_offset_minutes, nwp_lag_hours (+3 more)

### Community 169 - "Community 169"
Cohesion: 0.22
Nodes (7): assert_not_operational(), operational_sources(), _operational_substitute(), OperationalUseError, test_operational_sources_pass_the_guard(), test_reading_era5_in_the_inference_path_is_refused(), test_reading_final_besttrack_in_the_inference_path_is_refused()

### Community 170 - "Community 170"
Cohesion: 0.22
Nodes (8): build_transformer(), encode(), forward(), __init__(), extra_channel_patch(), __init__(), test_transformer_emits_track_and_regime(), test_transformer_rejects_an_indivisible_grid()

### Community 171 - "Community 171"
Cohesion: 0.22
Nodes (6): first_record_of_year(), ships_al_url(), _ships_get(), ships_record_year(), ships_size(), ships_window()

### Community 172 - "Community 172"
Cohesion: 0.20
Nodes (10): limit, lower_is_better, limit, lower_is_better, thresholds, intensity_error_48h_kt, intensity_error_72h_kt, track_error_72h_nm (+2 more)

### Community 173 - "Community 173"
Cohesion: 0.20
Nodes (10): steps, EXPECT_GIT_SHA, GCP_CI_SERVICE_ACCOUNT, GCP_WIF_PROVIDER, env, id, if, name (+2 more)

### Community 174 - "Community 174"
Cohesion: 0.20
Nodes (10): name, outputs, runs-on, timeout-minutes, changes, deploy_api, deploy_console, plan (+2 more)

### Community 175 - "Community 175"
Cohesion: 0.40
Nodes (10): steps, steps, id, if, name, run, uses, working-directory (+2 more)

### Community 176 - "Community 176"
Cohesion: 0.27
Nodes (4): ChecksumCheck, FetchResult, NonEmptyCheck, QCFinding

### Community 177 - "Community 177"
Cohesion: 0.24
Nodes (3): HomogeneousRow, BaselineReport, _json_safe()

### Community 178 - "Community 178"
Cohesion: 0.29
Nodes (4): build_live_cnn_x(), build_live_gnn_x(), build_live_transformer_x(), era5t_fields()

### Community 179 - "Community 179"
Cohesion: 0.22
Nodes (9): run, test-console, working-directory, defaults, if, name, needs, runs-on (+1 more)

### Community 180 - "Community 180"
Cohesion: 0.22
Nodes (9): BASE_SHA, BEFORE_SHA, DISPATCH_API, DISPATCH_CONSOLE, EVENT, EXPECT_GIT_SHA, HEAD_SHA, REF (+1 more)

### Community 181 - "Community 181"
Cohesion: 0.28
Nodes (5): test_default_fetch_fn_wires_a_shared_session(), fake_fetch_gdas_grib2_fields(), fake_gdas_to_gridded_fields(), test_fetch_one_fetches_exactly_one_real_sample(), fake_gdas_to_gridded_fields()

### Community 182 - "Community 182"
Cohesion: 0.28
Nodes (7): build_consistency_model(), consistency_fn(), __init__(), sample(), skip_coeffs(), test_evaluate_step_budget_tradeoff_reports_insufficient_data_below_min_cases(), test_consistency_rejects_a_non_positive_step_count()

### Community 183 - "Community 183"
Cohesion: 0.31
Nodes (5): _champions_tagged(), test_a_basin_counts_only_when_every_champion_trained_on_it(), test_a_champion_without_the_tag_counts_as_atlantic_only(), test_trained_basins_come_from_the_champions_tags(), test_trained_basins_follow_the_champion_not_the_latest_version()

### Community 184 - "Community 184"
Cohesion: 0.22
Nodes (4): test_a_desynced_derived_champion_is_not_a_bar_a_servable_candidate_must_clear(), test_a_servable_derived_champion_is_still_a_real_bar(), test_derived_resync_records_the_champion_signature_and_ends_in_sync(), test_seed_from_champions_refuses_an_incomplete_champion_set()

### Community 185 - "Community 185"
Cohesion: 0.22
Nodes (4): _load(), test_every_config_parses_and_has_no_duplicate_keys(), test_the_lead_times_match_the_api_s_own_copy(), test_the_load_shed_comment_still_describes_the_real_reduced_count()

### Community 186 - "Community 186"
Cohesion: 0.25
Nodes (8): 12, 120, 24, 36, 48, 72, 96, climatological_cone_nm

### Community 187 - "Community 187"
Cohesion: 0.25
Nodes (8): CP, 12, 120, 24, 36, 48, 72, 96

### Community 188 - "Community 188"
Cohesion: 0.25
Nodes (8): EP, 12, 120, 24, 36, 48, 72, 96

### Community 189 - "Community 189"
Cohesion: 0.25
Nodes (7): calibration_audit, cone_nominal_rate, intensity_nominal_rate, min_cases, verdict_margin, test_set_budget, max_evaluations_per_season

### Community 190 - "Community 190"
Cohesion: 0.25
Nodes (8): drift, min_samples, reference_flavor, shift_sigma, validation_loss, variance_ratio_limit, consecutive_required, threshold_fraction

### Community 191 - "Community 191"
Cohesion: 0.25
Nodes (8): promotion, flavor, new_basin_tolerance, primary_metric, reference_basin, require_manual_gate, split, basins()

### Community 192 - "Community 192"
Cohesion: 0.29
Nodes (3): cache_nwp_lead_hours(), CacheLeadMismatch, _claim_cache_dir()

### Community 194 - "Community 194"
Cohesion: 0.29
Nodes (7): products, cone_percentile, landfall_threshold_nm, lead_hours, ri_alert_probability, ri_threshold_kt, ri_window_hours

### Community 195 - "Community 195"
Cohesion: 0.29
Nodes (7): skew_audit, alert_intensity_delta_kt, alert_track_delta_nm, audit_delay_days, lead_hours, min_samples, window_days

### Community 196 - "Community 196"
Cohesion: 0.29
Nodes (6): activeId, { container, refreshKey, related = [] }, Heading, headings, Props, RelatedPage

### Community 197 - "Community 197"
Cohesion: 0.57
Nodes (5): deploy-plan.sh script, touches(), touches_component(), touches_console(), why

### Community 198 - "Community 198"
Cohesion: 0.29
Nodes (7): env, IMAGE, JOB, PROJECT_ID, PUBLISH, REGION, REGISTRY

### Community 199 - "Community 199"
Cohesion: 0.29
Nodes (3): retrain_job_out(), pending_triggers(), RetrainJobOut

### Community 200 - "Community 200"
Cohesion: 0.29
Nodes (3): archive_atcf(), calibration_audit(), skew_audit()

### Community 201 - "Community 201"
Cohesion: 0.33
Nodes (6): build_fusion(), forward(), __init__(), weights(), test_fusion_rejects_the_wrong_number_of_models(), test_fusion_weights_are_normalised_and_floored()

### Community 202 - "Community 202"
Cohesion: 0.33
Nodes (5): build_pinn(), encode(), forward(), __init__(), test_untrained_pinn_is_the_identity()

### Community 204 - "Community 204"
Cohesion: 0.38
Nodes (3): oracle(), target_time(), worst_case_oracle()

### Community 207 - "Community 207"
Cohesion: 0.33
Nodes (6): ensemble, climatological_cone_nm_by_basin, members, min_members_for_ensemble_cone, reduced_members, underdispersion_fraction

### Community 208 - "Community 208"
Cohesion: 0.33
Nodes (6): triggers, data_volume_threshold, nightly_latent_hour_utc, preseason_date, scheduled_monthly_day, suppress_nightly_latent_during_active_storms

### Community 210 - "Community 210"
Cohesion: 0.33
Nodes (4): {
		flagged,
		probability,
		lo = null,
		hi = null,
		uncertain = null,
		ensembleSize = null,
	}, membersNote, Props, range

### Community 211 - "Community 211"
Cohesion: 0.33
Nodes (6): update_job, workflow_dispatch, default, description, type, inputs

### Community 212 - "Community 212"
Cohesion: 0.33
Nodes (6): on, pull_request, push, paths, branches, paths

### Community 213 - "Community 213"
Cohesion: 0.40
Nodes (4): _saturation_vapor_pressure_hpa_array(), _specific_humidity_to_rh_pct(), test_specific_humidity_at_saturation_gives_rh_near_100(), test_specific_humidity_is_clipped_to_the_unit_range()

### Community 214 - "Community 214"
Cohesion: 0.47
Nodes (3): Threshold, _thresholds(), test_beat_rate_threshold_is_higher_is_better()

### Community 217 - "Community 217"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 218 - "Community 218"
Cohesion: 0.40
Nodes (3): WORLD_GEOJSON, WorldData, WorldFeatureProperties

### Community 219 - "Community 219"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 222 - "Community 222"
Cohesion: 0.67
Nodes (4): max, target, diffusion, diffusion

### Community 223 - "Community 223"
Cohesion: 0.67
Nodes (4): max, target, fusion, fusion

### Community 224 - "Community 224"
Cohesion: 0.67
Nodes (4): max, target, postprocess, postprocess

### Community 225 - "Community 225"
Cohesion: 0.67
Nodes (4): max, target, preprocess, preprocess

### Community 226 - "Community 226"
Cohesion: 0.50
Nodes (3): ANEMOI_FIELDS_MEMO, ANEMOI_STEERING_CACHE_DIR, entrypoint.sh script

### Community 227 - "Community 227"
Cohesion: 0.83
Nodes (3): graphify(), normalise_graph(), build-graph.sh script

### Community 228 - "Community 228"
Cohesion: 0.50
Nodes (3): uvx, graphify, graphify-mcp

### Community 234 - "Community 234"
Cohesion: 0.67
Nodes (3): limit, lower_is_better, nhc_consensus_beat_rate_48h

### Community 235 - "Community 235"
Cohesion: 0.67
Nodes (3): track_error_120h_nm, limit, lower_is_better

### Community 236 - "Community 236"
Cohesion: 0.67
Nodes (3): track_error_48h_nm, limit, lower_is_better

## Knowledge Gaps
- **14 isolated node(s):** `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627`, `RFC-5322`, `RFC-5646` (+9 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2815 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Flavor` connect `Community 2` to `Community 0`, `Community 1`, `Community 128`, `Community 3`, `Community 132`, `Community 6`, `Community 8`, `Community 136`, `Community 14`, `Community 15`, `Community 145`, `Community 18`, `Community 23`, `Community 24`, `Community 154`, `Community 27`, `Community 159`, `Community 34`, `Community 38`, `Community 166`, `Community 42`, `Community 44`, `Community 45`, `Community 46`, `Community 47`, `Community 51`, `Community 52`, `Community 53`, `Community 183`, `Community 184`, `Community 63`, `Community 69`, `Community 70`, `Community 72`, `Community 76`, `Community 78`, `Community 80`, `Community 85`, `Community 90`, `Community 91`, `Community 220`, `Community 93`, `Community 221`, `Community 92`, `Community 97`, `Community 105`, `Community 106`, `Community 107`, `Community 108`, `Community 109`, `Community 110`, `Community 114`, `Community 116`, `Community 118`, `Community 122`, `Community 125`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 252 inferred relationships involving `Flavor` (e.g. with `DemoState` and `drift()`) actually correct?**
  _`Flavor` has 252 INFERRED edges - model-reasoned connections that need verification._
- **What connects `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627` to the rest of the system?**
  _14 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.025451559934318555 - nodes in this community are weakly interconnected._
- **Why does `Track` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 132`, `Community 6`, `Community 7`, `Community 137`, `Community 138`, `Community 11`, `Community 13`, `Community 15`, `Community 20`, `Community 24`, `Community 27`, `Community 28`, `Community 159`, `Community 34`, `Community 36`, `Community 40`, `Community 45`, `Community 178`, `Community 51`, `Community 52`, `Community 53`, `Community 55`, `Community 56`, `Community 57`, `Community 62`, `Community 64`, `Community 70`, `Community 78`, `Community 80`, `Community 85`, `Community 90`, `Community 91`, `Community 92`, `Community 94`, `Community 97`, `Community 107`, `Community 240`, `Community 116`, `Community 118`, `Community 121`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 140 inferred relationships involving `Track` (e.g. with `save_cycle_inputs()` and `StormState`) actually correct?**
  _`Track` has 140 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.02806964113496777 - nodes in this community are weakly interconnected._