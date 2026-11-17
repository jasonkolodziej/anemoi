# Graph Report - anemoi  (2026-11-17)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 6911 nodes · 17790 edges · 259 communities (222 shown, 37 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 2620 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3e6b5d50`
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
- Community 239
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

## God Nodes (most connected - your core abstractions)
1. `Flavor` - 294 edges
2. `Track` - 198 edges
3. `Fix` - 149 edges
4. `ModelRegistry` - 136 edges
5. `CheckpointStore` - 133 edges
6. `TrackQuality` - 108 edges
7. `require_torch()` - 101 edges
8. `MetricSet` - 81 edges
9. `FetchTask` - 71 edges
10. `LatencyOracle` - 68 edges

## Surprising Connections (you probably didn't know these)
- `test_internal_calibration_audit_route_reports_new_samples()` --uses--> `RealState`  [INFERRED]
  tests/test_api_real_state.py → src/anemoi/api/real_state.py
- `test_trained_basins_without_champions_is_the_atlantic()` --uses--> `ModelRegistry`  [INFERRED]
  tests/test_registry.py → src/anemoi/tracking/registry.py
- `test_cache_round_trip_and_vector()` --uses--> `FetchTask`  [INFERRED]
  tests/test_steering.py → src/anemoi/data/gridded_cache.py
- `make_fix()` --calls--> `Fix`  [INFERRED]
  tests/test_streaming.py → src/anemoi/data/besttrack.py
- `make_fix()` --calls--> `Fix`  [INFERRED]
  tests/test_streaming.py → src/anemoi/data/besttrack.py

## Import Cycles
- None detected.

## Communities (259 total, 37 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (79): require_meta(), steering_meta(), assert_deployable(), Curriculum, CurriculumError, CurriculumRun, stage_a(), stage_b() (+71 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (50): sanitize_field_pixels(), TransformerOptimizer, cnn_input(), _sanitized_channel_stack(), _standardize_cnn_x(), _standardize_y(), train_cnn_stage(), train_cnn_stage_streaming() (+42 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (65): extra_input_conv(), __init__(), extra_input_linear(), __init__(), ModelSpec, require_torch(), torch_available(), build_diffusion() (+57 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (53): _put_text(), cmd_ablation(), cmd_adeck_fetch(), cmd_atcf_archive(), cmd_cache_localize(), cmd_consistency_distill(), cmd_drift_reference_fit(), cmd_era5_cache() (+45 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (49): apply_cold_wake(), area_mean(), assert_flavor(), cold_wake_sst_depression_c(), compare_potential_intensity_estimates(), compute_environment_features(), deep_layer_shear(), emanuel_potential_intensity() (+41 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (40): check_run(), CycleConflict, _existing_source(), InFlight, operator_ids(), RunRequest, stored_source(), list_cycle_labels() (+32 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (54): App, Locals, Platform, Props, Section, SectionPage, { sections }, height (+46 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (52): initial_fix(), assert_input_safe(), augment_track(), emulate_working_fix(), emulate_working_track(), recalibrate_from_pairs(), Track, TrackQuality (+44 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (44): Fix, save_steering(), steering_meta_digest(), displacement_nm(), build_live_cnn_x(), build_live_gnn_x(), build_live_lstm_x(), build_live_pinn_x() (+36 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (61): ConeSegmentOut, CyclePlanOut, bounds, colors, coneFeatures, coneHull, currentFix, forecastLine (+53 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (68): ApiError, apiFetch(), getActivePin(), getArchitecture(), getCalibration(), getCycle(), getDrift(), getDriftAll() (+60 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (34): DeterministicForecast, fusion_weights(), build_kwargs(), basin_inputs(), steering_inputs(), _builder(), _build_live_context(), _build_live_x() (+26 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (41): cycle_key(), save_cycle_result(), CycleResult, IntensityPercentiles, audit_cycle(), audit_due(), audit_storm(), _audited_key() (+33 more)

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (21): trained_basins(), verified_basins(), basin_tags(), resolve_basin_inputs(), served_columns(), _sample_config(), _context_features(), _displacement_to_absolute() (+13 more)

### Community 14 - "Community 14"
Cohesion: 0.05
Nodes (39): _decode_one_sonde(), DropsondeFetchError, DropsondeProfile, fetch_and_parse_dropsonde_mission(), fetch_dropsonde_mission_tarball(), _ftp_connect(), list_dropsonde_missions(), _mask_missing() (+31 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (45): svelte@^5.57.1, svelte-sonner@^1.2.3, getSources(), ActivePin, ModelCatalog, RegistryEntry, FUSION_COLOR, { href, stars = $bindable(0) } (+37 more)

### Community 16 - "Community 16"
Cohesion: 0.05
Nodes (34): _crop_variable(), fetch_real_satellite_crop(), _find_real_scan(), GoesFetchError, _lazy_open(), _list_scan_keys(), _nearest_scan_key(), _parse_scan_start() (+26 more)

### Community 17 - "Community 17"
Cohesion: 0.05
Nodes (40): _baseline_inputs(), _empty_report(), _fake_checkpoint_store(), _fake_curriculum_run(), _hurdat2_storm(), make_args(), make_track(), _retrain_check_args() (+32 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (34): WorkingTrackNoise, assert_no_leakage(), assign_splits(), _earliest_season(), filter_tracks(), _latest_season(), LeakageError, _seasons() (+26 more)

### Community 19 - "Community 19"
Cohesion: 0.06
Nodes (36): build_derived_schedule(), build_schedule(), _latent_task(), Mode, OrchestrationError, OrchestrationResult, ResourceProfile, run_schedule() (+28 more)

### Community 20 - "Community 20"
Cohesion: 0.04
Nodes (58): CyclePayload, CycleProducts, CycleResult, DriftReportOut, FeatureDriftOut, FixOut, HealthOut, IntensityPercentiles (+50 more)

### Community 21 - "Community 21"
Cohesion: 0.06
Nodes (7): cycle_payload_out(), RealState, deterministic(), ensemble(), live_fields(), RealStormState, CycleOutput

### Community 22 - "Community 22"
Cohesion: 0.06
Nodes (48): AppAuth, buildAuth(), getAuth(), verifyApiKey(), CYCLE_STEP, cycleInstanceId(), CycleParams, CycleWorkflow (+40 more)

### Community 23 - "Community 23"
Cohesion: 0.06
Nodes (42): _paired(), storm_block_interval(), brier_score(), crps_ensemble(), _crps_rows(), crps_series(), ensemble_percentiles(), rank_histogram() (+34 more)

### Community 24 - "Community 24"
Cohesion: 0.06
Nodes (37): Flavor, _champions(), test_a_basin_is_served_once_every_champion_is_verified_in_it(), test_data_volume_counts_seasons_newer_than_any_model_trained_on(), _champions_tagged(), full_set(), register_group1(), _stage_all() (+29 more)

### Community 25 - "Community 25"
Cohesion: 0.05
Nodes (34): ForecastPoint, LeadTimeStats, _normal_cdf(), to_metric_dict(), VerificationPair, verify(), build_consistency_model(), consistency_fn() (+26 more)

### Community 26 - "Community 26"
Cohesion: 0.06
Nodes (38): build_cone(), build_products(), climatological_cone_nm(), cone_radius_from_spread(), ConeSegment, deterministic_center(), EnsembleMember, ForecastProducts (+30 more)

### Community 27 - "Community 27"
Cohesion: 0.05
Nodes (59): devDependencies, cn@^0.3.3, @fontsource-variable/geist@^5.3.0, @fontsource-variable/geist-mono@^5.3.0, @fontsource-variable/inter@^5.3.0, formsnap@^2.0.1, layerchart@^2.5.1, mode-watcher@^1.1.0 (+51 more)

### Community 28 - "Community 28"
Cohesion: 0.07
Nodes (21): ModelRegistry, ModelVersion, Stage, _reconcile_args(), test_registry_reconcile_dry_run_reports_without_transitioning(), test_registry_reconcile_ignores_nan_metrics(), test_registry_reconcile_never_touches_a_model_with_a_production_version(), test_registry_reconcile_re_stages_the_real_best_existing_version() (+13 more)

### Community 29 - "Community 29"
Cohesion: 0.06
Nodes (37): cycle_products_out(), cycle_result_out(), provenance_out(), get_model_architecture(), get_cycle(), get_storm(), list_storms(), _served_basins() (+29 more)

### Community 30 - "Community 30"
Cohesion: 0.05
Nodes (25): basin_one_hot(), with_basin_channels(), with_basin_columns(), with_basin_vector(), _extract_for_tracks(), extract_validation_latents(), _prior_source(), prior_of() (+17 more)

### Community 31 - "Community 31"
Cohesion: 0.08
Nodes (11): get_state(), require_api_key(), state_dependency(), get_custom_redoc_html(), create_app(), _debug_last_deterministic_error(), redoc_html(), _lifespan() (+3 more)

### Community 32 - "Community 32"
Cohesion: 0.08
Nodes (30): invalidated_by(), evaluate_all(), expand_jobs(), nightly_latent(), on_data_volume(), on_drift(), on_latent_desync(), on_skew() (+22 more)

### Community 33 - "Community 33"
Cohesion: 0.05
Nodes (38): {
    contributors,
    missingModelReasons = {},
    hoveredModel = $bindable(null),
  }, maxWeight, missingRows, Props, rows, activeId, { container, refreshKey, related = [] }, Heading (+30 more)

### Community 34 - "Community 34"
Cohesion: 0.07
Nodes (34): arch_params_tag(), _builders(), cache_all_fixes(), cache_steering(), _curriculum_tracks(), _FakeS3Client, _fields(), _forward() (+26 more)

### Community 35 - "Community 35"
Cohesion: 0.06
Nodes (25): arktype@^2.2.7, @lucide/svelte@^1.71.0, sveltekit-superforms@^2.31.0, authClient, { form }, Props, { form }, Props (+17 more)

### Community 36 - "Community 36"
Cohesion: 0.07
Nodes (27): BasinChoice, _check_basin(), _created_date(), creation_day(), cycle_date(), decode_ohc(), fetch_ohc_file(), name_day_for_creation() (+19 more)

### Community 37 - "Community 37"
Cohesion: 0.06
Nodes (20): physics_residuals(), build_pinn_samples(), _candidate_and_true_absolute(), _disp_to_abs_batch(), _freeze_pinn_trunk(), pinn_environment(), PinnStageSamples, _PinnWindowDataset (+12 more)

### Community 38 - "Community 38"
Cohesion: 0.06
Nodes (42): SourceOut, byUse(), hasUnknownEntry(), MODEL_NAMES, MODELS, ORDER, readersOf(), SOURCE_NAMES (+34 more)

### Community 39 - "Community 39"
Cohesion: 0.06
Nodes (17): svelte-guard@^1.1.1, DEFAULT_AFTER_LOGIN, loginHref(), safeNext(), requireSignIn(), requireSignInLoad(), DELETE, GET (+9 more)

### Community 40 - "Community 40"
Cohesion: 0.07
Nodes (21): experiment_name(), latest_final_season(), config_digest(), baseline_beaten(), build_run_tags(), _git_commit(), _gpu_type(), log_curriculum_stages() (+13 more)

### Community 41 - "Community 41"
Cohesion: 0.09
Nodes (27): archive_key(), ArchiveClient, cache_path(), _decode_cached_fields(), FetchCacheReport, FetchTask, load_cached_fields(), _memo_enabled() (+19 more)

### Community 42 - "Community 42"
Cohesion: 0.08
Nodes (29): build_lstm(), encode(), forward(), __init__(), build_stage_samples(), _train_candidate_lstm(), run_lstm_curriculum(), StageSamples (+21 more)

### Community 43 - "Community 43"
Cohesion: 0.08
Nodes (21): _aligned(), assemble_validation_forecasts(), scored(), BaselineBacktestError, collect_validation_forecasts(), dump_validation_forecasts(), format_forecast_check(), group1_versions_of() (+13 more)

### Community 44 - "Community 44"
Cohesion: 0.08
Nodes (21): storm_basin(), haversine_nm(), absolute_pairs(), basin_key(), basin_value(), is_basin_key(), key_basin(), per_basin_scores() (+13 more)

### Community 45 - "Community 45"
Cohesion: 0.07
Nodes (24): advisory_time(), floor_synoptic(), is_synoptic(), next_synoptic(), NWPCycleSelection, NWPUnavailableError, parse_cycle_label(), require_synoptic() (+16 more)

### Community 46 - "Community 46"
Cohesion: 0.07
Nodes (21): calibrate(), forecast_motion_bearings(), LeadCalibration, observed_motion_bearings(), recurving_cases(), _scalar_errors(), spread_skill(), SpreadSkill (+13 more)

### Community 47 - "Community 47"
Cohesion: 0.09
Nodes (27): ExecutionMode, Task, fake_load_run_artifacts(), _FakeJointLatents, _register_group1_versions(), runner(), fake_extract_joint_latents(), make_fake() (+19 more)

### Community 48 - "Community 48"
Cohesion: 0.12
Nodes (27): climatological_ensemble(), run_cycle(), deterministic_fn(), good_ensemble(), make_fix(), test_a_pacific_climatological_ensemble_is_drawn_from_pacific_radii(), test_absent_opportunistic_feeds_do_not_flag_the_cycle(), test_an_eastern_pacific_cycle_falls_back_to_nhcs_pacific_radii() (+19 more)

### Community 49 - "Community 49"
Cohesion: 0.10
Nodes (31): storm_relative_sequence(), validate(), lr_factor(), test_fusion_weights_favour_the_lower_error_model(), test_sanitize_field_pixels_fills_nan_with_the_fields_own_spatial_mean(), test_a_short_stage_still_ends_on_the_floor(), test_config_values_are_validated(), test_cosine_decays_to_the_floor_on_the_last_update() (+23 more)

### Community 50 - "Community 50"
Cohesion: 0.10
Nodes (27): build_fetch_tasks(), filter_tracks_by_min_valid_time(), shard_tracks(), FakeArchive, _fix_keys(), make_fields(), make_track(), _saved() (+19 more)

### Community 51 - "Community 51"
Cohesion: 0.11
Nodes (22): case_errors(), compared_members(), homogeneous_mask(), _limiting(), _mean(), Member, MemberScore, PairedComparison (+14 more)

### Community 52 - "Community 52"
Cohesion: 0.10
Nodes (23): build_cnn(), encode(), forward(), __init__(), build_cnn_samples(), CnnStageSamples, cache_all_fixes(), _FakeS3Client (+15 more)

### Community 53 - "Community 53"
Cohesion: 0.08
Nodes (22): format_report(), recommend_extra_conditioning(), run_spread_backtest(), SpreadBacktestError, SpreadBacktestReport, _fake_val(), _FakeS3Client, _lc() (+14 more)

### Community 54 - "Community 54"
Cohesion: 0.10
Nodes (19): DriftError, FeatureDrift, ReferenceDistribution, load_reference(), reference_from_json(), reference_to_json(), save_reference(), test_drift_report_detects_real_drift_once_enough_samples_are_collected() (+11 more)

### Community 55 - "Community 55"
Cohesion: 0.09
Nodes (19): al_2021_2022(), compare(), files(), first_record_of_year(), local(), open_ocean(), parse_ships(), sample_days() (+11 more)

### Community 56 - "Community 56"
Cohesion: 0.09
Nodes (26): CycleAbandoned, derive_vitals_timeout(), plan_cycle(), StageBudget, total_budget(), test_a_cycle_started_at_the_timeout_still_clears_the_margin(), test_core_is_ready_before_spread(), test_cycle_starts_when_vitals_land_not_at_synoptic_time() (+18 more)

### Community 57 - "Community 57"
Cohesion: 0.07
Nodes (20): joint_stage_windows(), adeck_text(), adecks(), archive(), archive_text(), cases(), _FakeStore, _row() (+12 more)

### Community 58 - "Community 58"
Cohesion: 0.10
Nodes (23): adeck_name(), adeck_path(), adeck_urls(), fetch_adecks(), _adeck_positive(), AtcfError, parse_adeck(), _archive() (+15 more)

### Community 59 - "Community 59"
Cohesion: 0.10
Nodes (19): _filter_and_fit_env_stats(), cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_build_pinn_samples_empty_when_nothing_cached(), test_build_pinn_samples_environment_width_matches_feature_names() (+11 more)

### Community 60 - "Community 60"
Cohesion: 0.07
Nodes (20): client(), _get_real_state(), hurdat2_file(), _stage_group1_and_derived(), test_a_stale_refresh_in_flight_serves_known_storms_without_waiting(), test_calibration_report_is_honest_empty_with_no_samples(), test_calibration_report_reflects_persisted_samples(), test_debug_last_deterministic_error_route_needs_opt_in() (+12 more)

### Community 61 - "Community 61"
Cohesion: 0.09
Nodes (31): ArchitectureOut, LayerOut, {
		arch,
		onclose,
		class: className = ''
	}, Box, boxFor(), clamp(), color, focus (+23 more)

### Community 62 - "Community 62"
Cohesion: 0.06
Nodes (35): context, dockerfile, postgres, AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY, MLFLOW_S3_ENDPOINT_URL, POSTGRES_DB (+27 more)

### Community 63 - "Community 63"
Cohesion: 0.12
Nodes (21): build_gnn_samples(), build_mesh_topology(), GnnStageSamples, cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for() (+13 more)

### Community 64 - "Community 64"
Cohesion: 0.10
Nodes (26): @better-auth/passkey@^1.7.7, authHandle(), guards, handle, Auth, _authByRequest, buildAuth(), checkRegistrationOpen() (+18 more)

### Community 65 - "Community 65"
Cohesion: 0.10
Nodes (16): AdeckPoint, _adeck(), _avni_from_truth(), _persistence(), test_a_version_with_a_prior_is_described_and_loaded(), test_live_prior_matches_training_and_is_none_without_avni(), test_no_prior_without_avni_at_the_first_lead_or_the_cycle(), test_one_prior_fetch_is_shared_by_every_model_in_a_forecast() (+8 more)

### Community 66 - "Community 66"
Cohesion: 0.13
Nodes (18): AvailabilityOracle, earliest_ready_time(), LatencyOracle, resolve_cycle_inputs(), _valid_time_for(), test_all_nwp_missing_marks_the_required_input_unavailable(), test_cycle_is_not_ready_before_vitals_arrive(), test_cycle_is_ready_once_vitals_and_staged_nwp_are_in() (+10 more)

### Community 67 - "Community 67"
Cohesion: 0.11
Nodes (20): fetch_current_storm_ids(), fetch_current_storms(), fetch_live_track(), fetch_live_tracks(), fetch_one(), _get(), LiveAtcfError, test_fetch_current_storm_ids_parses_and_uppercases() (+12 more)

### Community 68 - "Community 68"
Cohesion: 0.13
Nodes (20): AblationCell, AblationReport, build_samples(), run_capacity_ablation(), _cell(), make_track(), test_at_fraction_filters_and_sorts_by_hidden_dim(), test_build_samples_augmentation_multiplies_sample_count() (+12 more)

### Community 69 - "Community 69"
Cohesion: 0.11
Nodes (27): QUICK, addVirtualAuthenticator(), EMAIL_DIR, EMAIL_LOCK, listEmailFiles(), localD1(), setRegistrationOpen(), signUpViaMagicLink() (+19 more)

### Community 70 - "Community 70"
Cohesion: 0.07
Nodes (32): better-auth@^1.7.7, @better-auth/api-key@^1.7.7, @types/node@^26.6.4, typescript@^5.9.3, wrangler@^4.147.0, better-auth, @better-auth/api-key, @types/node (+24 more)

### Community 71 - "Community 71"
Cohesion: 0.06
Nodes (28): AsyncReturnType, Expand, ExtractGenericViewableContent, GenericItem, GenericSelectorOption, GenericSnippetProps, GenericViewableContent, InheritedSnippetProps (+20 more)

### Community 72 - "Community 72"
Cohesion: 0.12
Nodes (17): disc_mean(), fetch_lead_flow(), group_by_time(), lead_flow(), LeadFlow, load_steering(), run_steering_cache(), fetch() (+9 more)

### Community 73 - "Community 73"
Cohesion: 0.06
Nodes (31): data, basins, stage_a, epochs, flavor, input_sources, label_source, learning_rate (+23 more)

### Community 74 - "Community 74"
Cohesion: 0.12
Nodes (21): run_fetch_cache(), make_fields(), make_track(), test_default_fetch_fn_wires_a_shared_session(), fake_fetch_gdas_grib2_fields(), fake_gdas_to_gridded_fields(), test_fetch_one_fetches_exactly_one_real_sample(), fake_gdas_to_gridded_fields() (+13 more)

### Community 75 - "Community 75"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, env, GH_TOKEN, GRAPHIFY_VERSION, permissions, runs-on (+22 more)

### Community 76 - "Community 76"
Cohesion: 0.15
Nodes (15): audit_due(), SkewMonitor, SkewReport, sample(), test_audit_becomes_due_once_era5t_lands(), test_audit_is_not_due_immediately_after_the_cycle(), test_intensity_delta_is_signed_toward_the_operational_run(), test_intensity_skew_alone_can_raise_an_alert() (+7 more)

### Community 77 - "Community 77"
Cohesion: 0.11
Nodes (17): _adeck_position(), pair_by_valid_time(), parse_bdeck(), _parse_latlon(), parse_tcvitals(), TcVitalsError, as_issued(), calibrate_season() (+9 more)

### Community 78 - "Community 78"
Cohesion: 0.12
Nodes (13): Fetcher, FetchError, ingest_cycle_inputs(), ingest_one(), IngestionOutcome, IngestionRecord, LakeTier, LakeWriter (+5 more)

### Community 79 - "Community 79"
Cohesion: 0.08
Nodes (15): _expected_meta(), test_a_failed_time_is_reported_and_the_others_still_written(), fetch(), test_a_lost_race_with_no_file_appearing_raises_the_write_error(), test_cache_round_trip_and_vector(), test_disc_mean_is_symmetric_for_a_field_linear_in_longitude(), test_features_advect_with_the_flow_plus_beta_drift(), test_features_raise_where_there_is_no_flow() (+7 more)

### Community 80 - "Community 80"
Cohesion: 0.07
Nodes (29): WithElementRef, ButtonClickEvent, PrimitiveAnchorAttributes, PrimitiveButtonAttributes, PrimitiveCanvasAttributes, PrimitiveDivAttributes, PrimitiveElementAttributes, PrimitiveFigureAttributes (+21 more)

### Community 81 - "Community 81"
Cohesion: 0.12
Nodes (14): build_real_ensemble_fn(), InferenceEnsembleError, cache_current_fix(), _FakeS3Client, make_track(), _register(), _register_all_five_and_diffusion(), _store() (+6 more)

### Community 82 - "Community 82"
Cohesion: 0.13
Nodes (15): build_transformer_samples(), TransformerStageSamples, cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_build_transformer_samples_empty_when_nothing_cached() (+7 more)

### Community 83 - "Community 83"
Cohesion: 0.10
Nodes (16): _FakeCycleOutput, _fresh_real_state(), _make_deterministic_forecast(), _make_storm_state(), _memory_store(), _MemoryS3Client, test_a_failed_cycle_write_never_fails_the_cycle(), test_an_unrestored_drift_window_is_never_written_back() (+8 more)

### Community 84 - "Community 84"
Cohesion: 0.14
Nodes (7): cycle_plan_out(), CyclePlan, plan_day(), _schedule_stages(), ScheduledStage, Stage, test_all_four_daily_cycles_plan_and_meet_their_deadlines()

### Community 85 - "Community 85"
Cohesion: 0.07
Nodes (28): inputArgs, jobs, projectId, region, results, timeoutSeconds, assign, return (+20 more)

### Community 86 - "Community 86"
Cohesion: 0.13
Nodes (15): _record_key(), record_operational_cycle(), _FakeClient, _fix(), _make_output(), _record(), test_audit_run_degrades_per_record_when_audit_one_raises(), flaky_audit_one() (+7 more)

### Community 87 - "Community 87"
Cohesion: 0.12
Nodes (12): _standardize(), _standardize_y(), train_diffusion_stage(), _FakeS3Client, _make_samples(), test_a_longer_epoch_budget_never_returns_a_worse_val_loss(), test_early_stopping_halts_before_the_epoch_cap_on_a_real_overfitting_run(), test_run_diffusion_curriculum_uploads_a_checkpoint_and_registers_stage_b() (+4 more)

### Community 88 - "Community 88"
Cohesion: 0.16
Nodes (13): cache_current_fix(), _FakeS3Client, make_track(), _register_real_version(), _store(), test_build_real_deterministic_fn_combines_all_four_real_models(), test_build_real_deterministic_fn_raises_with_no_registered_models(), test_build_real_deterministic_fn_uses_the_real_learned_fusion_with_all_five() (+5 more)

### Community 89 - "Community 89"
Cohesion: 0.12
Nodes (14): fetch_and_parse_ndbc(), fetch_ndbc_realtime2(), _get(), NdbcFetchError, NdbcObservation, parse_ndbc_realtime2(), test_a_row_with_the_wrong_column_count_is_skipped_not_fatal(), test_a_station_missing_wave_columns_still_parses() (+6 more)

### Community 90 - "Community 90"
Cohesion: 0.12
Nodes (15): get(), Role, _model_sources(), test_a_label_or_verification_source_is_never_a_model_input(), test_a_model_input_is_never_a_labels_only_source(), test_each_curriculum_stage_lists_what_its_models_read(), test_era5_is_pretrain_only(), test_era5_latency_is_days_not_hours() (+7 more)

### Community 91 - "Community 91"
Cohesion: 0.11
Nodes (13): bearing_deg(), bearings_deg(), cross_along_track_nms(), km_to_nm(), nm_to_km(), offset_position(), offset_positions(), wrap_longitude() (+5 more)

### Community 92 - "Community 92"
Cohesion: 0.10
Nodes (12): color_for(), god(), Module, WindGod, test_every_god_color_is_distinct(), test_experiment_name_handles_fusion_without_raising(), test_experiment_names_are_the_god_slugs(), test_lookup_by_slug_and_by_architecture_agree() (+4 more)

### Community 93 - "Community 93"
Cohesion: 0.08
Nodes (25): dependencies, bits-ui@^2.20.6, clsx@^2.1.1, d3-polygon@^3.0.1, d3-scale@^4.0.2, @internationalized/date@^3.12.4, kysely@^0.29.6, maplibre-gl@^6.11.2 (+17 more)

### Community 94 - "Community 94"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GH_TOKEN, IMPORTED_FROM, SOURCE_SHA, jobs, publish (+16 more)

### Community 95 - "Community 95"
Cohesion: 0.15
Nodes (17): cross_along_track_nm(), _lon_close(), _members(), ref_bearing(), ref_displacement(), ref_haversine(), ref_offset(), rng() (+9 more)

### Community 96 - "Community 96"
Cohesion: 0.12
Nodes (9): _default_fetch_fn(), fetch(), fetch_one(), fetch_gdas_grib2_fields(), gdas_to_gridded_fields(), gfs_url(), test_gdas_archive_start_is_the_first_valid_time_with_an_atmos_f006(), test_fetch_gdas_grib2_fields_reads_the_real_noaa_archive() (+1 more)

### Community 97 - "Community 97"
Cohesion: 0.12
Nodes (15): Archive, archives_for(), describe(), fetch_latest_hurdat2(), last_season(), latest_name(), manifest_path(), test_a_listing_without_one_archive_falls_back_for_that_archive_only() (+7 more)

### Community 98 - "Community 98"
Cohesion: 0.11
Nodes (17): _crop_box(), crop(), crop_levels(), crop(), _global_grid_with_marker(), _synthetic_era5_dataset(), _synthetic_gdas_fields(), test_crop_box_centers_on_the_requested_lat_lon() (+9 more)

### Community 99 - "Community 99"
Cohesion: 0.14
Nodes (14): audit_one(), audit_run(), _AuditPlan, _era5t_fetcher(), fetch(), _fix_from_dict(), _fix_to_dict(), list_operational_records() (+6 more)

### Community 100 - "Community 100"
Cohesion: 0.08
Nodes (3): client(), test_more_members_than_the_ensemble_runs_is_refused_not_silently_capped(), test_sources_say_who_uses_each_one()

### Community 101 - "Community 101"
Cohesion: 0.14
Nodes (15): by_basin(), complete_run(), metric_set(), test_a_basin_validated_but_never_trained_on_is_not_verified(), test_a_candidate_that_loses_a_verified_basin_is_refused(), test_a_candidate_that_scored_no_basin_is_judged_as_before(), test_a_candidate_verified_in_a_new_basin_may_be_slightly_worse_on_the_reference(), test_a_candidate_with_no_reference_basin_storms_is_not_compared_on_others() (+7 more)

### Community 102 - "Community 102"
Cohesion: 0.15
Nodes (13): _FakeS3Client, _make_version(), _real_builder(), _store(), test_load_run_artifacts_rebuilds_pinns_candidate_and_env_stats(), test_load_run_artifacts_refuses_a_version_without_standardisation_stats(), test_load_run_artifacts_round_trips_a_real_training_runs_artifacts(), test_load_standardization_stats_is_empty_without_any_tags() (+5 more)

### Community 103 - "Community 103"
Cohesion: 0.10
Nodes (11): unist-util-visit@^5.1.0, CONSOLE_ROOT, force, LOCAL_WIKI, MANIFEST_DIR, processor, STATIC_DIR, useLocal (+3 more)

### Community 104 - "Community 104"
Cohesion: 0.14
Nodes (10): fetch_gefs_ensemble_grib2_fields(), fetch_gefs_member_grib2_fields(), _gefs_member_url(), _parse_grib2_index(), test_control_member_zero_uses_gec00_not_gep00(), test_fetch_gefs_ensemble_reads_multiple_real_distinct_members(), test_fetch_gefs_member_reads_the_real_noaa_archive(), test_member_out_of_range_raises() (+2 more)

### Community 105 - "Community 105"
Cohesion: 0.15
Nodes (14): _all_tensors(), Architecture, _builder(), describe(), describe_cached(), _describe_cached(), hook(), _example_inputs() (+6 more)

### Community 106 - "Community 106"
Cohesion: 0.16
Nodes (16): archive_atcf(), _fetcher(), fetch(), _keys(), test_a_storm_is_still_archived_for_a_few_days_after_it_leaves_the_index(), test_a_storm_seen_on_new_years_eve_is_still_followed_on_new_years_day(), test_an_unreachable_index_raises_so_the_caller_reports_it(), test_archived_tcvitals_keeps_every_revision_once_in_issue_order() (+8 more)

### Community 107 - "Community 107"
Cohesion: 0.11
Nodes (14): scored_basins(), reference_value(), _forecasts(), test_a_basin_is_verified_when_the_model_beats_persistence_there(), test_a_run_from_before_the_counts_sets_no_basin_tags(), test_a_runs_validation_metrics_carry_the_overall_and_each_basin(), test_a_storm_id_per_sample_is_required(), test_columns_never_trained_on_are_blanked_once_for_latents_and_serving() (+6 more)

### Community 108 - "Community 108"
Cohesion: 0.13
Nodes (10): _download(), fetch_oisst_sst(), require_sst_deps(), sst_at(), SstFetchError, _small_grid(), test_fetch_oisst_sst_reads_real_recent_data(), test_sst_at_finds_the_nearest_cell() (+2 more)

### Community 109 - "Community 109"
Cohesion: 0.17
Nodes (12): accessed(), _check_type(), config_dir(), ConfigError, fixed(), get(), get_list(), _load() (+4 more)

### Community 110 - "Community 110"
Cohesion: 0.20
Nodes (15): evaluate_promotion(), complete_run(), good_metrics(), test_candidate_worse_than_incumbent_is_not_staged(), test_era5_flavor_metrics_cannot_gate_promotion(), test_first_candidate_is_staged(), test_missing_metric_is_reported_as_a_failure(), test_non_finite_candidate_does_not_beat_an_incumbent_either() (+7 more)

### Community 111 - "Community 111"
Cohesion: 0.11
Nodes (11): season_boundaries(), test_an_unreadable_listing_falls_back_to_the_pinned_file_and_says_so(), fetch(), test_boundaries_move_with_the_archive(), test_no_file_at_all_raises(), test_stage_bs_validation_season_is_never_seen_by_stage_a(), test_the_archive_a_run_was_given_is_not_what_it_trained_on(), test_the_internal_route_runs_a_bounded_pass() (+3 more)

### Community 112 - "Community 112"
Cohesion: 0.14
Nodes (11): _files(), localize_cache(), LocalizeReport, _raise(), _cache(), test_a_directory_that_cant_be_listed_fails_the_copy(), test_a_missing_source_raises(), test_a_rerun_only_fills_gaps() (+3 more)

### Community 113 - "Community 113"
Cohesion: 0.13
Nodes (11): era5_deps_available(), fetch_grib2_messages(), gridded_deps_available(), require_era5_deps(), require_gdas_deps(), require_gridded_deps(), _saturation_vapor_pressure_hpa_array(), _specific_humidity_to_rh_pct() (+3 more)

### Community 114 - "Community 114"
Cohesion: 0.15
Nodes (16): _bilinear(), _lattice_index(), ohc_at(), place(), _decode(), _row_col(), test_a_truncated_file_is_rejected(), test_bilinear_between_nodes() (+8 more)

### Community 115 - "Community 115"
Cohesion: 0.14
Nodes (14): detect_format(), expected_coordinates(), OhcRejected, _ohc(), test_a_blank_file_is_rejected(), test_a_file_made_later_than_its_name_says_is_rejected(), test_a_file_with_no_fill_cell_is_rejected(), test_bilinear_on_a_files_north_and_east_edges_steps_back_inside_it() (+6 more)

### Community 116 - "Community 116"
Cohesion: 0.13
Nodes (13): http_get(), OhcFetchError, OhcNotPublished, OhcUnavailable, Archive, test_a_cut_off_reply_is_a_fetch_failure(), test_a_fetch_failure_that_is_not_a_404_is_not_stepped_over(), flaky() (+5 more)

### Community 117 - "Community 117"
Cohesion: 0.10
Nodes (7): _FakeS3Config, test_checkpoint_store_push_mirrors_registry_json_after_every_save(), test_pull_failure_degrades_to_an_empty_registry(), test_pull_from_checkpoint_store_hydrates_a_missing_local_registry(), test_pull_is_a_noop_when_the_key_does_not_exist_remotely_yet(), test_pull_is_skipped_entirely_without_a_checkpoint_store(), test_pull_reconciles_with_durable_storage_even_when_local_already_exists()

### Community 118 - "Community 118"
Cohesion: 0.10
Nodes (20): PROJECT_NUMBER, PROJECT_PAT, types, jobs, sync, name, on, issues (+12 more)

### Community 119 - "Community 119"
Cohesion: 0.13
Nodes (9): AdeckFetchReport, CachedAdecks, _check_adeck(), _check_official_errors(), _fetch_one(), file_record(), read_adeck(), read_cached_adecks() (+1 more)

### Community 120 - "Community 120"
Cohesion: 0.15
Nodes (11): _cron_run_offset_minutes(), _leaves(), _load(), test_a_config_change_redeploys_the_api(), test_both_images_copy_the_configs(), test_every_config_key_is_read_by_the_code(), test_every_image_build_is_smoke_tested_before_it_ships(), test_the_console_uses_the_same_scheduled_run_offset() (+3 more)

### Community 121 - "Community 121"
Cohesion: 0.13
Nodes (8): calibration_out(), drift_report_out(), skew_report_out(), calibration(), drift(), drift_all(), skew(), DriftReport

### Community 122 - "Community 122"
Cohesion: 0.15
Nodes (12): cmd_baseline_backtest(), OfficialErrors, _notes(), RegisteredError, run_baseline_backtest(), validation_cases(), validation_tracks(), report() (+4 more)

### Community 123 - "Community 123"
Cohesion: 0.14
Nodes (10): ohc_global(), OhcField, _full_archive(), test_a_blank_run_longer_than_the_window_leaves_na_unavailable(), test_a_degraded_basin_flags_the_field(), test_a_missing_file_steps_back_one_creation_day(), test_a_rejected_file_is_stepped_over(), test_ohc_global_places_both_basins_and_reports_where_they_came_from() (+2 more)

### Community 124 - "Community 124"
Cohesion: 0.18
Nodes (13): detect_feature_drift(), ValidationLossMonitor, reference(), test_a_recovery_resets_the_consecutive_count(), test_collapsed_variance_is_detected(), test_feature_count_mismatch_raises(), test_first_observation_only_sets_the_baseline(), test_increases_below_the_threshold_never_trigger() (+5 more)

### Community 125 - "Community 125"
Cohesion: 0.21
Nodes (6): freeCycleLabel(), label(), runFreshCycle(), signIn(), cases, @playwright/test

### Community 127 - "Community 127"
Cohesion: 0.15
Nodes (10): read_cached_official_errors(), OfficialErrorsError, parse_official_errors(), _signed(), test_a_cached_error_file_that_is_not_nhcs_is_named_with_the_way_out(), test_parse_official_errors_reads_columns_by_name_and_skips_missing_leads(), test_parse_official_errors_reads_the_stated_initial_position_domain(), test_parse_official_errors_rejects_a_file_without_the_column_header() (+2 more)

### Community 128 - "Community 128"
Cohesion: 0.19
Nodes (15): run_fetch_cache(), make_fields(), make_track(), test_build_fetch_tasks_covers_every_fix_across_tracks(), test_load_cached_fields_rejects_a_missing_file(), test_run_fetch_cache_actually_runs_fetches_concurrently(), slow_fetch(), test_run_fetch_cache_can_force_refetch_with_skip_existing_false() (+7 more)

### Community 129 - "Community 129"
Cohesion: 0.19
Nodes (15): fetch_live_nwp(), _fields(), _run(), test_a_cache_dir_holds_one_lead(), test_a_missing_t_minus_6_cycle_falls_back_to_t_minus_12(), fetch_one(), test_gfs_url_names_the_forecast_valid_at_the_time(), test_live_fields_come_from_the_t_minus_6_forecast() (+7 more)

### Community 130 - "Community 130"
Cohesion: 0.15
Nodes (10): _attributes(), _calls(), _function(), _imported(), _names_adapter(), _parameters(), _parse(), _string_literals() (+2 more)

### Community 131 - "Community 131"
Cohesion: 0.12
Nodes (4): _Boto3Client, require_boto3(), _StorageClient, test_boto3_adapter_configures_the_client_for_the_given_endpoint()

### Community 132 - "Community 132"
Cohesion: 0.11
Nodes (7): _FakeMlflowModelVersion, _mlflow_client_that_registers_and_transitions(), create_model_version(), test_mlflow_mirror_skips_create_registered_model_if_it_already_exists(), create_model_version(), test_mlflow_transition_also_mirrors_the_archived_incumbent(), create_model_version()

### Community 133 - "Community 133"
Cohesion: 0.17
Nodes (7): mlflow_client_from_env(), test_an_unreachable_server_is_skipped_fast(), test_builds_a_real_client_when_tracking_uri_is_set(), test_fail_fast_settings_never_override_explicit_ones(), test_mlflow_client_from_env_can_actually_reach_the_configured_server(), test_returns_none_when_tracking_uri_is_unset(), test_returns_none_without_mlflow_installed()

### Community 134 - "Community 134"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 135 - "Community 135"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 136 - "Community 136"
Cohesion: 0.12
Nodes (8): god_out(), model_catalog(), source_out(), health(), models(), sources(), DataSource, pretrain_only_sources()

### Community 137 - "Community 137"
Cohesion: 0.15
Nodes (6): CloudflareAccessRequestHeaderProvider, test_headers_are_actually_applied_by_mlflows_own_resolution(), test_in_context_false_when_neither_var_set(), test_in_context_false_when_only_client_id_set(), test_in_context_true_and_correct_headers_when_both_set(), test_registered_as_a_real_mlflow_plugin_via_entry_points()

### Community 138 - "Community 138"
Cohesion: 0.16
Nodes (8): _default_fetch_fn(), fetch(), era5_to_gridded_fields(), fetch_era5t_one(), open_era5(), open_era5_store(), test_open_era5_reads_the_real_arco_era5_store(), test_open_era5_reuses_a_passed_in_store_instead_of_reopening()

### Community 139 - "Community 139"
Cohesion: 0.18
Nodes (14): parse_hurdat2(), test_entry_count_mismatch_raises(), test_header_name_is_parsed_onto_the_track(), test_malformed_header_raises(), test_malformed_latitude_raises(), test_multi_storm_file_produces_one_track_per_storm(), test_non_numeric_entry_count_raises(), test_off_synoptic_and_missing_pressure_entries_are_dropped() (+6 more)

### Community 140 - "Community 140"
Cohesion: 0.22
Nodes (8): PromotionError, spend_test_set_budget(), TestSetBudget, test_the_test_set_budget_outlives_one_job_and_runs_out(), test_budget_allows_a_limited_number_of_looks(), test_budget_exhaustion_raises(), test_budget_requires_a_justification(), test_budget_resets_across_seasons()

### Community 141 - "Community 141"
Cohesion: 0.12
Nodes (16): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+8 more)

### Community 142 - "Community 142"
Cohesion: 0.16
Nodes (14): minisearch@^7.2.0, loading, onInput(), open, query, results, bodyById, buildIndex() (+6 more)

### Community 143 - "Community 143"
Cohesion: 0.12
Nodes (16): compilerOptions, allowJs, allowSyntheticDefaultImports, checkJs, forceConsistentCasingInFileNames, isolatedModules, lib, module (+8 more)

### Community 144 - "Community 144"
Cohesion: 0.12
Nodes (5): client(), test_docs_route_is_unaffected(), test_sources_role_is_the_role_enum_in_the_openapi_schema(), test_sources_used_by_is_documented_in_the_openapi_schema(), test_theme_http_method_colors_are_distinct()

### Community 145 - "Community 145"
Cohesion: 0.12
Nodes (16): permissions, runs-on, steps, jobs, copilot-setup-steps, name, on, pull_request (+8 more)

### Community 146 - "Community 146"
Cohesion: 0.15
Nodes (9): config_copy(), edit(), _image_layout(), _run(), test_a_missing_config_dir_is_refused(), test_an_image_without_configs_fails_at_import_and_says_why(), test_an_invalid_config_is_refused_with_a_clear_message(), test_edited_values_take_effect_at_runtime() (+1 more)

### Community 147 - "Community 147"
Cohesion: 0.19
Nodes (10): ArchiveReport, currentstorms_key(), _digest(), _get_text(), _load_recent(), _put_bytes(), snapshot_key(), _stored_digests() (+2 more)

### Community 148 - "Community 148"
Cohesion: 0.15
Nodes (12): generate_season(), make_storm_spec(), StormSpec, test_archive_spans_the_requested_seasons(), test_fields_have_matching_shapes_and_carry_a_flavor(), test_fixes_are_six_hourly_and_synoptic(), test_gdas_fields_are_noisier_than_era5(), test_generated_tracks_are_final_quality() (+4 more)

### Community 149 - "Community 149"
Cohesion: 0.12
Nodes (16): with, build-args, cache-from, cache-to, context, file, load, password (+8 more)

### Community 150 - "Community 150"
Cohesion: 0.12
Nodes (15): jobs, lint-and-validate, name, permissions, runs-on, steps, name, on (+7 more)

### Community 151 - "Community 151"
Cohesion: 0.20
Nodes (7): Hurdat2Error, _parse_data_row(), _parse_header(), parse_hurdat2_statuses(), _parse_latlon(), _storm_rows(), test_statuses_cover_exactly_the_fixes_the_tracks_keep()

### Community 152 - "Community 152"
Cohesion: 0.15
Nodes (7): HomogeneousRow, BaselineReport, _fmt(), format_report(), _json_safe(), samples_for(), test_the_report_serialises_as_strict_json_and_prints_a_table()

### Community 153 - "Community 153"
Cohesion: 0.19
Nodes (6): _FakeS3Client, _make_samples(), test_run_fusion_curriculum_uploads_a_checkpoint_and_registers_stage_b(), test_train_fusion_stage_reduces_loss_and_produces_val_metrics(), test_train_fusion_stage_rejects_a_val_set_built_with_a_different_model_count(), test_train_fusion_stage_rejects_empty_samples()

### Community 154 - "Community 154"
Cohesion: 0.13
Nodes (15): scripts, build, cf:deploy, check, check:errors, check:warnings, check:watch, dev (+7 more)

### Community 155 - "Community 155"
Cohesion: 0.13
Nodes (15): env, environment, if, name, needs, permissions, runs-on, timeout-minutes (+7 more)

### Community 156 - "Community 156"
Cohesion: 0.14
Nodes (8): API, DEVELOP, PHONE, SourceRow, SOURCES, SOURCES_BEFORE_USED_BY, SOURCES_REWIRED, path()

### Community 157 - "Community 157"
Cohesion: 0.14
Nodes (13): compilerOptions, allowJs, checkJs, esModuleInterop, forceConsistentCasingInFileNames, moduleResolution, resolveJsonModule, rewriteRelativeImportExtensions (+5 more)

### Community 158 - "Community 158"
Cohesion: 0.14
Nodes (13): images, options, diskSizeGb, machineType, steps, args, entrypoint, env (+5 more)

### Community 159 - "Community 159"
Cohesion: 0.14
Nodes (14): default, description, type, default, description, type, api, console (+6 more)

### Community 160 - "Community 160"
Cohesion: 0.24
Nodes (8): _get_text(), load_drift_live(), save_drift_live(), _load_audited(), _load_audited_cycles(), load_skew_samples(), _save_audited_cycles(), test_load_skew_samples_is_empty_when_nothing_was_ever_audited()

### Community 161 - "Community 161"
Cohesion: 0.18
Nodes (3): cycle_inputs_prefix(), CycleHistory, save_cycle_inputs()

### Community 162 - "Community 162"
Cohesion: 0.27
Nodes (7): technique_member(), techniques_to_read(), TechniqueSpec, test_a_case_without_an_adeck_has_no_technique_forecast(), test_a_lagged_member_reads_the_earlier_run_at_the_same_valid_time(), test_technique_specs(), test_the_official_member_prefers_the_regular_advisory()

### Community 163 - "Community 163"
Cohesion: 0.35
Nodes (7): NoiseSensitivityReport, _result(), test_is_load_bearing_above_threshold(), test_is_not_load_bearing_below_threshold(), test_relative_change_is_zero_when_losses_match(), test_relative_change_rejects_nonpositive_default_loss(), test_relative_change_sign_matches_direction_of_the_move()

### Community 164 - "Community 164"
Cohesion: 0.23
Nodes (8): cache_all_fixes(), _cache_steering(), make_track(), test_compare_refuses_arms_on_different_windows_and_pairs_the_rest(), test_stage_b_trains_the_steering_conv_and_keeps_the_rest_frozen(), test_the_spike_runs_both_arms_on_the_same_windows_and_registers_nothing(), test_track_errors_are_zero_for_a_perfect_forecast_and_nan_without_a_target(), test_with_zero_steering_both_arms_are_the_same_run()

### Community 165 - "Community 165"
Cohesion: 0.17
Nodes (12): IdTokenClaims, JwtClaims, OidcAddressClaim, OidcStandardClaims, UserProfile, Mandatory, RFC-3966, RFC-4627 (+4 more)

### Community 166 - "Community 166"
Cohesion: 0.19
Nodes (8): client(), test_a_registered_versions_arch_params_are_used(), test_a_version_that_reads_steering_is_described(), test_a_version_without_arch_params_is_described_from_defaults(), test_a_versions_arch_params_change_what_is_described(), test_every_model_runs_its_example_input_and_reports_its_layers(), test_the_gnn_is_fed_the_real_lattice(), test_unknown_models_and_versions_are_404()

### Community 167 - "Community 167"
Cohesion: 0.15
Nodes (12): name, runs-on, timeout-minutes, concurrency, cancel-in-progress, group, jobs, build (+4 more)

### Community 168 - "Community 168"
Cohesion: 0.19
Nodes (4): _declared_length(), _grid_values(), OhcFile, _read_checked()

### Community 169 - "Community 169"
Cohesion: 0.17
Nodes (6): _called(), _modules(), test_an_adapter_is_named_by_other_code_only_if_its_source_is_read(), test_every_fetch_adapter_is_classified(), test_no_module_imports_by_a_computed_name(), _unread_sources()

### Community 170 - "Community 170"
Cohesion: 0.23
Nodes (11): max, target, budgets, reduced, standard, max, target, assembly (+3 more)

### Community 171 - "Community 171"
Cohesion: 0.17
Nodes (4): local, notes, problems, remote

### Community 172 - "Community 172"
Cohesion: 0.17
Nodes (11): concurrency, cancel-in-progress, group, jobs, test-api, name, if, name (+3 more)

### Community 173 - "Community 173"
Cohesion: 0.17
Nodes (12): with, cache, cache-dependency-path, enable-cache, fetch-depth, if-no-files-found, include-hidden-files, name (+4 more)

### Community 174 - "Community 174"
Cohesion: 0.18
Nodes (11): cycle, advisory_margin_minutes, advisory_offset_minutes, allow_estimated_vitals, allow_load_shedding, max_nwp_lag_hours, nominal_vitals_offset_minutes, nwp_lag_hours (+3 more)

### Community 177 - "Community 177"
Cohesion: 0.22
Nodes (7): assert_not_operational(), operational_sources(), _operational_substitute(), OperationalUseError, test_operational_sources_pass_the_guard(), test_reading_era5_in_the_inference_path_is_refused(), test_reading_final_besttrack_in_the_inference_path_is_refused()

### Community 178 - "Community 178"
Cohesion: 0.22
Nodes (4): save_skew_samples(), SkewSample, test_skew_report_falls_back_to_the_legacy_flat_path(), test_save_then_load_skew_samples_round_trips()

### Community 179 - "Community 179"
Cohesion: 0.20
Nodes (10): limit, lower_is_better, limit, lower_is_better, thresholds, intensity_error_48h_kt, intensity_error_72h_kt, track_error_72h_nm (+2 more)

### Community 180 - "Community 180"
Cohesion: 0.22
Nodes (3): build_info(), _build_info_path(), summary()

### Community 181 - "Community 181"
Cohesion: 0.20
Nodes (10): steps, EXPECT_GIT_SHA, GCP_CI_SERVICE_ACCOUNT, GCP_WIF_PROVIDER, env, id, if, name (+2 more)

### Community 182 - "Community 182"
Cohesion: 0.20
Nodes (10): name, outputs, runs-on, timeout-minutes, changes, deploy_api, deploy_console, plan (+2 more)

### Community 183 - "Community 183"
Cohesion: 0.40
Nodes (10): steps, steps, id, if, name, run, uses, working-directory (+2 more)

### Community 184 - "Community 184"
Cohesion: 0.27
Nodes (4): ChecksumCheck, FetchResult, NonEmptyCheck, QCFinding

### Community 185 - "Community 185"
Cohesion: 0.20
Nodes (7): used_by(), test_cmd_sources_prints_who_uses_each_source(), test_a_verification_source_not_read_yet_is_verification_and_nothing_else(), test_every_required_cycle_input_has_a_model_consumer(), test_used_by_follows_the_contract_order_for_every_source(), test_used_by_per_source(), test_used_by_refuses_an_unknown_source()

### Community 186 - "Community 186"
Cohesion: 0.31
Nodes (5): model_version_out(), get_active_pin(), get_model_registry(), list_registry(), RegistryEntry

### Community 187 - "Community 187"
Cohesion: 0.22
Nodes (9): run, test-console, working-directory, defaults, if, name, needs, runs-on (+1 more)

### Community 188 - "Community 188"
Cohesion: 0.22
Nodes (9): BASE_SHA, BEFORE_SHA, DISPATCH_API, DISPATCH_CONSOLE, EVENT, EXPECT_GIT_SHA, HEAD_SHA, REF (+1 more)

### Community 189 - "Community 189"
Cohesion: 0.28
Nodes (4): latent_signature(), RegistryError, test_signature_changes_when_any_group1_version_changes(), test_signature_requires_every_group1_model()

### Community 190 - "Community 190"
Cohesion: 0.28
Nodes (4): oracle(), pytest_collection_modifyitems(), target_time(), worst_case_oracle()

### Community 191 - "Community 191"
Cohesion: 0.25
Nodes (8): 12, 120, 24, 36, 48, 72, 96, climatological_cone_nm

### Community 192 - "Community 192"
Cohesion: 0.25
Nodes (8): CP, 12, 120, 24, 36, 48, 72, 96

### Community 193 - "Community 193"
Cohesion: 0.25
Nodes (8): EP, 12, 120, 24, 36, 48, 72, 96

### Community 194 - "Community 194"
Cohesion: 0.25
Nodes (7): calibration_audit, cone_nominal_rate, intensity_nominal_rate, min_cases, verdict_margin, test_set_budget, max_evaluations_per_season

### Community 195 - "Community 195"
Cohesion: 0.25
Nodes (8): drift, min_samples, reference_flavor, shift_sigma, validation_loss, variance_ratio_limit, consecutive_required, threshold_fraction

### Community 196 - "Community 196"
Cohesion: 0.25
Nodes (8): promotion, flavor, new_basin_tolerance, primary_metric, reference_basin, require_manual_gate, split, basins()

### Community 197 - "Community 197"
Cohesion: 0.29
Nodes (3): cache_nwp_lead_hours(), CacheLeadMismatch, _claim_cache_dir()

### Community 202 - "Community 202"
Cohesion: 0.36
Nodes (4): cache_all_fixes(), make_fields(), _task_for(), test_extract_joint_latents_rejects_missing_group1_model()

### Community 203 - "Community 203"
Cohesion: 0.29
Nodes (7): products, cone_percentile, landfall_threshold_nm, lead_hours, ri_alert_probability, ri_threshold_kt, ri_window_hours

### Community 204 - "Community 204"
Cohesion: 0.29
Nodes (7): skew_audit, alert_intensity_delta_kt, alert_track_delta_nm, audit_delay_days, lead_hours, min_samples, window_days

### Community 205 - "Community 205"
Cohesion: 0.57
Nodes (5): deploy-plan.sh script, touches(), touches_component(), touches_console(), why

### Community 206 - "Community 206"
Cohesion: 0.29
Nodes (7): env, IMAGE, JOB, PROJECT_ID, PUBLISH, REGION, REGISTRY

### Community 207 - "Community 207"
Cohesion: 0.29
Nodes (3): archive_atcf(), calibration_audit(), skew_audit()

### Community 208 - "Community 208"
Cohesion: 0.33
Nodes (4): _get(), _get_bytes(), NotPublished, fetch_live_adeck()

### Community 211 - "Community 211"
Cohesion: 0.33
Nodes (6): ensemble, climatological_cone_nm_by_basin, members, min_members_for_ensemble_cone, reduced_members, underdispersion_fraction

### Community 212 - "Community 212"
Cohesion: 0.33
Nodes (6): triggers, data_volume_threshold, nightly_latent_hour_utc, preseason_date, scheduled_monthly_day, suppress_nightly_latent_during_active_storms

### Community 214 - "Community 214"
Cohesion: 0.33
Nodes (4): {
		flagged,
		probability,
		lo = null,
		hi = null,
		uncertain = null,
		ensembleSize = null,
	}, membersNote, Props, range

### Community 215 - "Community 215"
Cohesion: 0.33
Nodes (6): update_job, workflow_dispatch, default, description, type, inputs

### Community 216 - "Community 216"
Cohesion: 0.33
Nodes (6): on, pull_request, push, paths, branches, paths

### Community 219 - "Community 219"
Cohesion: 0.47
Nodes (3): Threshold, _thresholds(), test_beat_rate_threshold_is_higher_is_better()

### Community 222 - "Community 222"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 223 - "Community 223"
Cohesion: 0.40
Nodes (3): WORLD_GEOJSON, WorldData, WorldFeatureProperties

### Community 224 - "Community 224"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 225 - "Community 225"
Cohesion: 0.40
Nodes (4): ANEMOI_ADECK_DIR, ANEMOI_FIELDS_MEMO, ANEMOI_STEERING_CACHE_DIR, entrypoint.sh script

### Community 227 - "Community 227"
Cohesion: 0.40
Nodes (3): basins_of(), select_basins(), test_training_reads_only_the_configured_basins()

### Community 231 - "Community 231"
Cohesion: 0.67
Nodes (4): max, target, diffusion, diffusion

### Community 232 - "Community 232"
Cohesion: 0.67
Nodes (4): max, target, fusion, fusion

### Community 233 - "Community 233"
Cohesion: 0.67
Nodes (4): max, target, postprocess, postprocess

### Community 234 - "Community 234"
Cohesion: 0.67
Nodes (4): max, target, preprocess, preprocess

### Community 236 - "Community 236"
Cohesion: 0.83
Nodes (3): graphify(), normalise_graph(), build-graph.sh script

### Community 237 - "Community 237"
Cohesion: 0.50
Nodes (3): uvx, graphify, graphify-mcp

### Community 241 - "Community 241"
Cohesion: 0.67
Nodes (3): limit, lower_is_better, nhc_consensus_beat_rate_48h

### Community 242 - "Community 242"
Cohesion: 0.67
Nodes (3): track_error_120h_nm, limit, lower_is_better

### Community 243 - "Community 243"
Cohesion: 0.67
Nodes (3): track_error_48h_nm, limit, lower_is_better

## Knowledge Gaps
- **15 isolated node(s):** `$lib/registry/blocks/navigation/components/site.context.svelte`, `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627`, `RFC-5322` (+10 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2882 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Flavor` connect `Community 24` to `Community 0`, `Community 1`, `Community 128`, `Community 3`, `Community 4`, `Community 5`, `Community 129`, `Community 7`, `Community 8`, `Community 132`, `Community 138`, `Community 2`, `Community 13`, `Community 17`, `Community 18`, `Community 19`, `Community 148`, `Community 153`, `Community 28`, `Community 30`, `Community 31`, `Community 34`, `Community 164`, `Community 37`, `Community 166`, `Community 40`, `Community 41`, `Community 42`, `Community 43`, `Community 44`, `Community 47`, `Community 49`, `Community 50`, `Community 52`, `Community 53`, `Community 54`, `Community 59`, `Community 60`, `Community 189`, `Community 63`, `Community 65`, `Community 74`, `Community 202`, `Community 81`, `Community 82`, `Community 87`, `Community 88`, `Community 90`, `Community 221`, `Community 96`, `Community 98`, `Community 229`, `Community 230`, `Community 101`, `Community 102`, `Community 107`, `Community 109`, `Community 110`, `Community 111`, `Community 113`, `Community 117`, `Community 121`, `Community 122`, `Community 124`, `Community 126`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 257 inferred relationships involving `Flavor` (e.g. with `DemoState` and `drift()`) actually correct?**
  _`Flavor` has 257 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$lib/registry/blocks/navigation/components/site.context.svelte`, `./.svelte-kit/tsconfig.json`, `RFC-3966` to the rest of the system?**
  _15 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.03164774681802546 - nodes in this community are weakly interconnected._
- **Why does `ModelRegistry` connect `Community 28` to `Community 0`, `Community 3`, `Community 132`, `Community 5`, `Community 11`, `Community 17`, `Community 21`, `Community 24`, `Community 43`, `Community 44`, `Community 47`, `Community 53`, `Community 189`, `Community 81`, `Community 88`, `Community 218`, `Community 221`, `Community 99`, `Community 229`, `Community 230`, `Community 117`, `Community 126`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Are the 146 inferred relationships involving `Track` (e.g. with `save_cycle_inputs()` and `StormState`) actually correct?**
  _`Track` has 146 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.037528790136837825 - nodes in this community are weakly interconnected._