# Graph Report - anemoi  (2026-11-17)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 6888 nodes · 17714 edges · 253 communities (225 shown, 28 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 2592 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6b9dc048`
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
- Community 225
- Community 226
- Community 227
- Community 228
- Community 229
- Community 230
- Community 231
- Community 232
- Community 234
- Community 235
- Community 236
- Community 237
- Community 238
- Community 239
- Community 240
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

## God Nodes (most connected - your core abstractions)
1. `Flavor` - 294 edges
2. `Track` - 196 edges
3. `Fix` - 149 edges
4. `ModelRegistry` - 136 edges
5. `CheckpointStore` - 133 edges
6. `TrackQuality` - 108 edges
7. `require_torch()` - 101 edges
8. `MetricSet` - 81 edges
9. `FetchTask` - 71 edges
10. `LatencyOracle` - 68 edges

## Surprising Connections (you probably didn't know these)
- `make_window()` --calls--> `StageWindow`  [INFERRED]
  tests/test_streaming.py → src/anemoi/training/real_run.py
- `test_cache_round_trip_and_vector()` --uses--> `FetchTask`  [INFERRED]
  tests/test_steering.py → src/anemoi/data/gridded_cache.py
- `test_trained_basins_without_champions_is_the_atlantic()` --uses--> `ModelRegistry`  [INFERRED]
  tests/test_registry.py → src/anemoi/tracking/registry.py
- `test_internal_calibration_audit_route_reports_new_samples()` --uses--> `RealState`  [INFERRED]
  tests/test_api_real_state.py → src/anemoi/api/real_state.py
- `make_fix()` --calls--> `Fix`  [INFERRED]
  tests/test_streaming.py → src/anemoi/data/besttrack.py

## Import Cycles
- None detected.

## Communities (253 total, 28 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (72): basins_of(), select_basins(), augment_track(), emulate_working_track(), WorkingTrackNoise, sanitize_field_pixels(), displacement_nm(), basin_one_hot() (+64 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (66): storm_basin(), OfficialErrors, basin_key(), per_basin_scores(), sample_counts(), HomogeneousRow, _aligned(), assemble_validation_forecasts() (+58 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (49): Track, assert_no_leakage(), assign_splits(), _earliest_season(), filter_tracks(), _latest_season(), LeakageError, _seasons() (+41 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (54): cycle_inputs_prefix(), cycle_key(), _get_text(), list_cycle_labels(), load_cycle_result(), load_drift_live(), _put_text(), save_cycle_inputs() (+46 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (59): extra_input_conv(), ModelSpec, require_torch(), torch_available(), build_consistency_model(), consistency_fn(), __init__(), sample() (+51 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (65): intensity_pdf(), case_errors(), compared_members(), homogeneous_mask(), _limiting(), _mean(), Member, MemberScore (+57 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (57): generate_track(), bearing_deg(), bearings_deg(), cross_along_track_nm(), cross_along_track_nms(), haversine_nm(), km_to_nm(), nm_to_km() (+49 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (41): CycleResult, IntensityPercentiles, audit_cycle(), audit_due(), audit_storm(), _audited_key(), calibrate_products(), CalibrationSample (+33 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (10): cycle_payload_out(), cycle_result_out(), provenance_out(), CycleHistory, RealState, deterministic(), live_fields(), RealStormState (+2 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (40): Fix, steering_meta_digest(), _build_live_x(), InferenceCycleError, build_live_cnn_x(), build_live_gnn_x(), build_live_lstm_x(), build_live_pinn_x() (+32 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (42): _baseline_inputs(), _empty_report(), _fake_checkpoint_store(), _fake_curriculum_run(), _hurdat2_storm(), make_args(), make_track(), _retrain_check_args() (+34 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (31): DeterministicForecast, fusion_weights(), build_kwargs(), basin_inputs(), steering_inputs(), _builder(), build_real_deterministic_fn(), deterministic_fn() (+23 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (59): getCycle(), getSchedule(), getSkew(), getStorm(), health(), listStorms(), runCycle(), { flags, notes = [] } (+51 more)

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (34): _crop_variable(), fetch_real_satellite_crop(), _find_real_scan(), GoesFetchError, _lazy_open(), _list_scan_keys(), _nearest_scan_key(), _parse_scan_start() (+26 more)

### Community 14 - "Community 14"
Cohesion: 0.05
Nodes (33): check_run(), CycleConflict, _existing_source(), InFlight, operator_ids(), RunRequest, stored_source(), RunInfo (+25 more)

### Community 15 - "Community 15"
Cohesion: 0.06
Nodes (50): @cloudflare/containers@^0.3.7, AppAuth, buildAuth(), getAuth(), verifyApiKey(), CYCLE_STEP, cycleInstanceId(), CycleParams (+42 more)

### Community 16 - "Community 16"
Cohesion: 0.04
Nodes (37): Props, Section, SectionPage, { sections }, height, motionClass, Props, {
    size = 28,
    spinning = false,
    class: className,
    ...restProps
  } (+29 more)

### Community 17 - "Community 17"
Cohesion: 0.07
Nodes (32): cmd_ablation(), cmd_adeck_fetch(), cmd_atcf_archive(), cmd_cache_localize(), cmd_consistency_distill(), cmd_drift_reference_fit(), cmd_era5_cache(), cmd_gdas_cache() (+24 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (36): build_cone(), build_products(), climatological_cone_nm(), cone_radius_from_spread(), ConeSegment, deterministic_center(), EnsembleMember, _interpolate_climo() (+28 more)

### Community 19 - "Community 19"
Cohesion: 0.06
Nodes (34): is_basin_key(), key_basin(), scored_basins(), trained_basins(), verified_basins(), basin_tags(), resolve_basin_inputs(), served_columns() (+26 more)

### Community 20 - "Community 20"
Cohesion: 0.05
Nodes (58): devDependencies, cn@^0.3.3, @fontsource-variable/geist@^5.3.0, @fontsource-variable/geist-mono@^5.3.0, @fontsource-variable/inter@^5.3.0, formsnap@^2.0.1, layerchart@^2.5.1, mode-watcher@^1.1.0 (+50 more)

### Community 21 - "Community 21"
Cohesion: 0.07
Nodes (40): svelte@^5.57.1, getActivePin(), getRetrainTriggers(), getSources(), listRegistry(), ActivePin, RegistryEntry, errorDetail() (+32 more)

### Community 22 - "Community 22"
Cohesion: 0.07
Nodes (30): invalidated_by(), evaluate_all(), expand_jobs(), nightly_latent(), on_data_volume(), on_drift(), on_latent_desync(), on_skew() (+22 more)

### Community 23 - "Community 23"
Cohesion: 0.06
Nodes (30): pair_by_valid_time(), Archive, archives_for(), describe(), fetch_latest_hurdat2(), last_season(), latest_name(), manifest_path() (+22 more)

### Community 24 - "Community 24"
Cohesion: 0.07
Nodes (31): build_lstm(), encode(), forward(), __init__(), boundaries_for_flavor(), build_stage_samples(), _train_candidate_lstm(), run_lstm_curriculum() (+23 more)

### Community 25 - "Community 25"
Cohesion: 0.08
Nodes (32): GriddedFields, archive_key(), ArchiveClient, cache_path(), _decode_cached_fields(), FetchCacheReport, FetchTask, load_cached_fields() (+24 more)

### Community 26 - "Community 26"
Cohesion: 0.05
Nodes (23): stage_a(), stage_b(), test_both_stages_label_from_final_besttrack(), test_stage_a_uses_era5_and_stage_b_uses_gdas(), test_stage_b_learning_rate_is_lower_than_stage_a(), _RecordingStore, _StubMlflowClient, _StubRun (+15 more)

### Community 27 - "Community 27"
Cohesion: 0.05
Nodes (38): svelte-sonner@^1.2.3, ModelCatalog, BY_ARCHITECTURE, BY_SLUG, FUNCTIONAL_COLORS, FUSION_COLOR, GOD_ORDER, GODS (+30 more)

### Community 28 - "Community 28"
Cohesion: 0.06
Nodes (23): absolute_pairs(), basin_value(), ForecastPoint, LeadTimeStats, _normal_cdf(), to_metric_dict(), VerificationPair, verify() (+15 more)

### Community 29 - "Community 29"
Cohesion: 0.05
Nodes (39): IntensityPercentiles, TrackPointOut, colorFor(), god(), bounds, colors, coneFeatures, coneHull (+31 more)

### Community 30 - "Community 30"
Cohesion: 0.06
Nodes (25): arktype@^2.2.7, @lucide/svelte@^1.71.0, sveltekit-superforms@^2.31.0, authClient, { form }, Props, { form }, Props (+17 more)

### Community 31 - "Community 31"
Cohesion: 0.07
Nodes (24): Flavor, test_data_volume_counts_seasons_newer_than_any_model_trained_on(), track(), _champions_tagged(), test_a_basin_counts_only_when_every_champion_trained_on_it(), test_a_champion_without_the_tag_counts_as_atlantic_only(), test_champion_is_not_simply_the_most_recently_registered_version(), test_checkpoint_store_push_mirrors_registry_json_after_every_save() (+16 more)

### Community 32 - "Community 32"
Cohesion: 0.09
Nodes (29): require_meta(), steering_meta(), CurriculumRun, OrchestrationError, MetricSet, PromotionDecision, extract_joint_latents(), _require_group1() (+21 more)

### Community 33 - "Community 33"
Cohesion: 0.06
Nodes (42): SourceOut, byUse(), hasUnknownEntry(), MODEL_NAMES, MODELS, ORDER, readersOf(), SOURCE_NAMES (+34 more)

### Community 34 - "Community 34"
Cohesion: 0.05
Nodes (25): client(), _get_real_state(), hurdat2_file(), _stage_group1_and_derived(), test_a_live_storm_keeps_its_cycles_across_a_feed_refresh(), test_a_stale_refresh_in_flight_serves_known_storms_without_waiting(), test_calibration_report_is_honest_empty_with_no_samples(), test_calibration_report_reflects_persisted_samples() (+17 more)

### Community 35 - "Community 35"
Cohesion: 0.07
Nodes (32): _builders(), cache_all_fixes(), cache_steering(), _curriculum_tracks(), _FakeS3Client, _fields(), _forward(), make_track() (+24 more)

### Community 36 - "Community 36"
Cohesion: 0.08
Nodes (24): BasinChoice, _check_basin(), _created_date(), creation_day(), cycle_date(), decode_ohc(), fetch_ohc_file(), name_day_for_creation() (+16 more)

### Community 37 - "Community 37"
Cohesion: 0.08
Nodes (11): get_state(), require_api_key(), state_dependency(), get_custom_redoc_html(), create_app(), _debug_last_deterministic_error(), redoc_html(), _lifespan() (+3 more)

### Community 38 - "Community 38"
Cohesion: 0.07
Nodes (42): ApiError, apiFetch(), getArchitecture(), getCalibration(), getDrift(), getDriftAll(), getModelRegistry(), getModels() (+34 more)

### Community 39 - "Community 39"
Cohesion: 0.06
Nodes (35): CyclePlanOut, pointTime(), at(), calendarValue, hour, hourAllowed, inRange(), maxValue (+27 more)

### Community 40 - "Community 40"
Cohesion: 0.07
Nodes (26): cycle_products_out(), god_out(), model_catalog(), get_model_architecture(), schedule(), ArchitectureOut, ConeSegmentOut, CyclePayload (+18 more)

### Community 41 - "Community 41"
Cohesion: 0.12
Nodes (28): climatological_ensemble(), run_cycle(), deterministic_fn(), good_ensemble(), make_fix(), test_a_pacific_climatological_ensemble_is_drawn_from_pacific_radii(), test_absent_opportunistic_feeds_do_not_flag_the_cycle(), test_an_eastern_pacific_cycle_falls_back_to_nhcs_pacific_radii() (+20 more)

### Community 42 - "Community 42"
Cohesion: 0.09
Nodes (30): expected_coordinates(), place(), _decode(), files(), local(), _ohc(), _row_col(), server() (+22 more)

### Community 43 - "Community 43"
Cohesion: 0.07
Nodes (23): advisory_time(), floor_synoptic(), is_synoptic(), next_synoptic(), NWPCycleSelection, NWPUnavailableError, require_synoptic(), _require_utc() (+15 more)

### Community 44 - "Community 44"
Cohesion: 0.08
Nodes (23): build_pinn(), encode(), forward(), build_pinn_samples(), _filter_and_fit_env_stats(), _PinnWindowDataset, cache_all_fixes(), _FakeS3Client (+15 more)

### Community 45 - "Community 45"
Cohesion: 0.08
Nodes (26): cache_nwp_lead_hours(), _claim_cache_dir(), fetch_one(), run_fetch_cache(), make_fields(), make_track(), test_default_fetch_fn_wires_a_shared_session(), fake_fetch_gdas_grib2_fields() (+18 more)

### Community 46 - "Community 46"
Cohesion: 0.09
Nodes (27): ExecutionMode, Task, fake_load_run_artifacts(), _FakeJointLatents, _register_group1_versions(), runner(), fake_extract_joint_latents(), make_fake() (+19 more)

### Community 47 - "Community 47"
Cohesion: 0.07
Nodes (15): ModelRegistry, _champions(), test_a_basin_is_served_once_every_champion_is_verified_in_it(), test_a_champion_verified_nowhere_serves_no_basin_as_in_distribution(), test_no_champion_or_champions_from_before_the_tag_are_the_atlantic(), _FakeS3Config, test_checkpoint_store_push_failure_degrades_to_local_only(), test_mlflow_failure_degrades_to_local_only() (+7 more)

### Community 48 - "Community 48"
Cohesion: 0.09
Nodes (20): train_lstm_stage_streaming(), iter_dataset_in_batches(), OnlineMaskedLeadMeanStd, OnlineMeanStd, _batches(), _FakeWindow, test_iter_dataset_in_batches_covers_every_item_exactly_once(), test_make_dataloader_num_workers_positive_forks_real_worker_processes() (+12 more)

### Community 49 - "Community 49"
Cohesion: 0.08
Nodes (19): AvailabilityOracle, CycleInputs, earliest_ready_time(), InputStatus, resolve_cycle_inputs(), _valid_time_for(), test_all_nwp_missing_marks_the_required_input_unavailable(), test_cycle_is_not_ready_before_vitals_arrive() (+11 more)

### Community 50 - "Community 50"
Cohesion: 0.09
Nodes (27): build_fetch_tasks(), filter_tracks_by_min_valid_time(), shard_tracks(), FakeArchive, _fix_keys(), make_fields(), make_track(), _saved() (+19 more)

### Community 51 - "Community 51"
Cohesion: 0.10
Nodes (24): build_cnn(), encode(), forward(), __init__(), build_cnn_samples(), CnnStageSamples, test_cnn_is_resolution_agnostic(), cache_all_fixes() (+16 more)

### Community 52 - "Community 52"
Cohesion: 0.10
Nodes (24): assert_deployable(), Curriculum, CurriculumError, StageResult, test_stage_b_frozen_none_builds_an_unfrozen_stage_b(), result(), test_completed_two_stage_run_is_deployable(), test_curriculum_must_end_on_the_operational_flavor() (+16 more)

### Community 53 - "Community 53"
Cohesion: 0.10
Nodes (28): deterministic(), cmd_cycle(), deterministic(), LatencyOracle, CycleAbandoned, plan_cycle(), total_budget(), test_a_cycle_started_at_the_timeout_still_clears_the_margin() (+20 more)

### Community 54 - "Community 54"
Cohesion: 0.10
Nodes (24): build_gnn(), encode(), forward(), build_gnn_samples(), build_mesh_topology(), GnnStageSamples, cache_all_fixes(), _FakeS3Client (+16 more)

### Community 55 - "Community 55"
Cohesion: 0.10
Nodes (18): DriftError, ReferenceDistribution, load_reference(), reference_from_json(), reference_to_json(), save_reference(), test_drift_report_detects_real_drift_once_enough_samples_are_collected(), test_drift_report_is_honest_zero_for_a_model_that_never_contributed() (+10 more)

### Community 56 - "Community 56"
Cohesion: 0.11
Nodes (10): cycle_plan_out(), _budgets(), CyclePlan, derive_vitals_timeout(), plan_day(), _schedule_stages(), ScheduledStage, Stage (+2 more)

### Community 57 - "Community 57"
Cohesion: 0.10
Nodes (19): _decode_one_sonde(), DropsondeFetchError, DropsondeProfile, fetch_and_parse_dropsonde_mission(), fetch_dropsonde_mission_tarball(), _ftp_connect(), list_dropsonde_missions(), _mask_missing() (+11 more)

### Community 58 - "Community 58"
Cohesion: 0.08
Nodes (19): initial_fix(), assert_operational_flavor(), CycleError, extrapolate_fix(), ForecastProducts, client(), _MemoryS3, s3() (+11 more)

### Community 59 - "Community 59"
Cohesion: 0.09
Nodes (18): AdeckPoint, _adeck(), _avni_from_truth(), _persistence(), test_a_version_with_a_prior_is_described_and_loaded(), test_curriculum_with_a_prior_scores_prior_plus_correction(), run(), test_live_prior_matches_training_and_is_none_without_avni() (+10 more)

### Community 60 - "Community 60"
Cohesion: 0.11
Nodes (27): assert_input_safe(), emulate_working_fix(), recalibrate_from_pairs(), TrackQuality, _latlon(), make_fix(), make_track(), test_assert_input_safe_allows_working_quality() (+19 more)

### Community 61 - "Community 61"
Cohesion: 0.12
Nodes (22): evaluate_promotion(), PromotionError, TestSetBudget, complete_run(), good_metrics(), test_budget_allows_a_limited_number_of_looks(), test_budget_exhaustion_raises(), test_budget_requires_a_justification() (+14 more)

### Community 62 - "Community 62"
Cohesion: 0.09
Nodes (31): ArchitectureOut, LayerOut, {
		arch,
		onclose,
		class: className = ''
	}, Box, boxFor(), clamp(), color, focus (+23 more)

### Community 63 - "Community 63"
Cohesion: 0.06
Nodes (35): context, dockerfile, postgres, AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY, MLFLOW_S3_ENDPOINT_URL, POSTGRES_DB (+27 more)

### Community 64 - "Community 64"
Cohesion: 0.12
Nodes (20): _bytemap_path(), decode_ssmis_bytemap(), fetch_and_decode_ssmis_daily(), fetch_ssmis_daily_bytemap(), MicrowaveFetchError, RSSFtpCredentials, SSMISDaily, _make_bytemap() (+12 more)

### Community 65 - "Community 65"
Cohesion: 0.10
Nodes (15): JointLatentBundle, DiffusionArtifacts, run_diffusion_curriculum(), _standardize(), _standardize_y(), train_diffusion_stage(), _FakeS3Client, _make_samples() (+7 more)

### Community 66 - "Community 66"
Cohesion: 0.12
Nodes (18): disc_mean(), fetch_lead_flow(), group_by_time(), lead_flow(), LeadFlow, load_steering(), run_steering_cache(), fetch() (+10 more)

### Community 67 - "Community 67"
Cohesion: 0.11
Nodes (25): authHandle(), guards, handle, Auth, _authByRequest, buildAuth(), checkRegistrationOpen(), getAuth() (+17 more)

### Community 68 - "Community 68"
Cohesion: 0.11
Nodes (20): fetch_current_storm_ids(), fetch_current_storms(), fetch_live_track(), fetch_live_tracks(), fetch_one(), _get(), LiveAtcfError, test_fetch_current_storm_ids_parses_and_uppercases() (+12 more)

### Community 69 - "Community 69"
Cohesion: 0.13
Nodes (20): AblationCell, AblationReport, build_samples(), run_capacity_ablation(), _cell(), make_track(), test_at_fraction_filters_and_sorts_by_hidden_dim(), test_build_samples_augmentation_multiplies_sample_count() (+12 more)

### Community 70 - "Community 70"
Cohesion: 0.06
Nodes (28): AsyncReturnType, Expand, ExtractGenericViewableContent, GenericItem, GenericSelectorOption, GenericSnippetProps, GenericViewableContent, InheritedSnippetProps (+20 more)

### Community 71 - "Community 71"
Cohesion: 0.14
Nodes (15): audit_due(), SkewMonitor, SkewReport, sample(), test_audit_becomes_due_once_era5t_lands(), test_audit_is_not_due_immediately_after_the_cycle(), test_intensity_delta_is_signed_toward_the_operational_run(), test_intensity_skew_alone_can_raise_an_alert() (+7 more)

### Community 72 - "Community 72"
Cohesion: 0.13
Nodes (15): ModelVersion, Stage, _reconcile_args(), test_registry_reconcile_dry_run_reports_without_transitioning(), test_registry_reconcile_ignores_nan_metrics(), test_registry_reconcile_never_touches_a_model_with_a_production_version(), test_registry_reconcile_re_stages_the_real_best_existing_version(), test_registry_reconcile_skips_an_unloadable_version_even_with_better_metrics() (+7 more)

### Community 73 - "Community 73"
Cohesion: 0.06
Nodes (31): data, basins, stage_a, epochs, flavor, input_sources, label_source, learning_rate (+23 more)

### Community 74 - "Community 74"
Cohesion: 0.11
Nodes (20): Hurdat2Error, _parse_data_row(), _parse_header(), parse_hurdat2(), _parse_latlon(), _storm_rows(), test_entry_count_mismatch_raises(), test_header_name_is_parsed_onto_the_track() (+12 more)

### Community 75 - "Community 75"
Cohesion: 0.08
Nodes (30): better-auth@^1.7.7, @better-auth/api-key@^1.7.7, @types/node@^26.6.4, typescript@^5.9.3, wrangler@^4.147.0, better-auth, @better-auth/api-key, @types/node (+22 more)

### Community 76 - "Community 76"
Cohesion: 0.09
Nodes (12): color_for(), god(), Module, WindGod, test_every_god_color_is_distinct(), test_experiment_name_handles_fusion_without_raising(), test_experiment_names_are_the_god_slugs(), test_lookup_by_slug_and_by_architecture_agree() (+4 more)

### Community 77 - "Community 77"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, env, GH_TOKEN, GRAPHIFY_VERSION, permissions, runs-on (+22 more)

### Community 78 - "Community 78"
Cohesion: 0.12
Nodes (15): ensemble(), build_real_ensemble_fn(), InferenceEnsembleError, cache_current_fix(), _FakeS3Client, make_track(), _register(), _register_all_five_and_diffusion() (+7 more)

### Community 79 - "Community 79"
Cohesion: 0.11
Nodes (15): adeck_name(), adeck_path(), adeck_urls(), AdeckFetchReport, CachedAdecks, _check_adeck(), _check_official_errors(), fetch_adecks() (+7 more)

### Community 80 - "Community 80"
Cohesion: 0.12
Nodes (13): Fetcher, FetchError, ingest_cycle_inputs(), ingest_one(), IngestionOutcome, IngestionRecord, LakeTier, LakeWriter (+5 more)

### Community 81 - "Community 81"
Cohesion: 0.09
Nodes (18): _crop_box(), gdas_to_gridded_fields(), crop(), _global_grid_with_marker(), _synthetic_era5_dataset(), _synthetic_gdas_fields(), test_crop_box_centers_on_the_requested_lat_lon(), test_crop_box_rejects_the_wrong_global_shape() (+10 more)

### Community 82 - "Community 82"
Cohesion: 0.12
Nodes (16): _FakeS3Client, _make_version(), _real_builder(), _register_like_training(), _store(), test_load_run_artifacts_rebuilds_pinns_candidate_and_env_stats(), test_load_run_artifacts_refuses_a_version_without_standardisation_stats(), test_load_run_artifacts_round_trips_a_real_training_runs_artifacts() (+8 more)

### Community 83 - "Community 83"
Cohesion: 0.08
Nodes (15): _expected_meta(), test_a_failed_time_is_reported_and_the_others_still_written(), fetch(), test_a_lost_race_with_no_file_appearing_raises_the_write_error(), test_cache_round_trip_and_vector(), test_disc_mean_is_symmetric_for_a_field_linear_in_longitude(), test_features_advect_with_the_flow_plus_beta_drift(), test_features_raise_where_there_is_no_flow() (+7 more)

### Community 84 - "Community 84"
Cohesion: 0.08
Nodes (15): unist-util-visit@^5.1.0, CONSOLE_ROOT, force, LOCAL_WIKI, MANIFEST_DIR, processor, STATIC_DIR, useLocal (+7 more)

### Community 85 - "Community 85"
Cohesion: 0.07
Nodes (29): WithElementRef, ButtonClickEvent, PrimitiveAnchorAttributes, PrimitiveButtonAttributes, PrimitiveCanvasAttributes, PrimitiveDivAttributes, PrimitiveElementAttributes, PrimitiveFigureAttributes (+21 more)

### Community 86 - "Community 86"
Cohesion: 0.10
Nodes (16): _FakeCycleOutput, _fresh_real_state(), _make_deterministic_forecast(), _make_storm_state(), _memory_store(), _MemoryS3Client, test_a_failed_cycle_write_never_fails_the_cycle(), test_an_unrestored_drift_window_is_never_written_back() (+8 more)

### Community 87 - "Community 87"
Cohesion: 0.07
Nodes (28): inputArgs, jobs, projectId, region, results, timeoutSeconds, assign, return (+20 more)

### Community 88 - "Community 88"
Cohesion: 0.13
Nodes (19): _adeck_position(), _adeck_positive(), AtcfError, parse_adeck(), _parse_latlon(), _archive(), _errors_url(), _FakeNhc (+11 more)

### Community 89 - "Community 89"
Cohesion: 0.17
Nodes (23): build_schedule(), Mode, run_schedule(), RunOutcome, failing_runner(), runner(), ok_runner(), test_both_schedules_validate() (+15 more)

### Community 90 - "Community 90"
Cohesion: 0.12
Nodes (14): latent_signature(), RegistryError, full_set(), register_group1(), _stage_all(), test_desynced_derived_models_is_empty_for_a_coherent_set(), test_desynced_derived_models_is_empty_when_no_derived_model_has_a_champion(), test_desynced_derived_models_is_empty_without_a_full_champion_set() (+6 more)

### Community 91 - "Community 91"
Cohesion: 0.16
Nodes (13): cache_current_fix(), _FakeS3Client, make_track(), _register_real_version(), _store(), test_build_real_deterministic_fn_combines_all_four_real_models(), test_build_real_deterministic_fn_raises_with_no_registered_models(), test_build_real_deterministic_fn_uses_the_real_learned_fusion_with_all_five() (+5 more)

### Community 92 - "Community 92"
Cohesion: 0.07
Nodes (27): dependencies, @better-auth/passkey@^1.7.7, bits-ui@^2.20.6, clsx@^2.1.1, d3-polygon@^3.0.1, d3-scale@^4.0.2, @internationalized/date@^3.12.4, kysely@^0.29.6 (+19 more)

### Community 93 - "Community 93"
Cohesion: 0.14
Nodes (17): archive_atcf(), ArchiveReport, _fetcher(), fetch(), _keys(), test_a_storm_is_still_archived_for_a_few_days_after_it_leaves_the_index(), test_a_storm_seen_on_new_years_eve_is_still_followed_on_new_years_day(), test_an_unreachable_index_raises_so_the_caller_reports_it() (+9 more)

### Community 94 - "Community 94"
Cohesion: 0.12
Nodes (14): fetch_and_parse_ndbc(), fetch_ndbc_realtime2(), _get(), NdbcFetchError, NdbcObservation, parse_ndbc_realtime2(), test_a_row_with_the_wrong_column_count_is_skipped_not_fatal(), test_a_station_missing_wave_columns_still_parses() (+6 more)

### Community 95 - "Community 95"
Cohesion: 0.10
Nodes (16): http_get(), OhcFetchError, OhcNotPublished, OhcUnavailable, Archive, test_a_cut_off_reply_is_a_fetch_failure(), test_a_cut_off_transfer_raises_rather_than_reading_an_older_file(), test_a_fetch_failure_that_is_not_a_404_is_not_stepped_over() (+8 more)

### Community 96 - "Community 96"
Cohesion: 0.12
Nodes (15): get(), Role, _model_sources(), test_a_label_or_verification_source_is_never_a_model_input(), test_a_model_input_is_never_a_labels_only_source(), test_each_curriculum_stage_lists_what_its_models_read(), test_era5_is_pretrain_only(), test_era5_latency_is_days_not_hours() (+7 more)

### Community 97 - "Community 97"
Cohesion: 0.10
Nodes (12): categories, choosing, mounted, picked, visible, clearPreferenceStorage(), consent, CONSENT_KEY (+4 more)

### Community 98 - "Community 98"
Cohesion: 0.13
Nodes (15): _all_tensors(), Architecture, _builder(), describe(), describe_cached(), _describe_cached(), hook(), _example_inputs() (+7 more)

### Community 99 - "Community 99"
Cohesion: 0.13
Nodes (12): experiment_name(), baseline_beaten(), build_run_tags(), _git_commit(), _gpu_type(), log_curriculum_stages(), log_stage_run(), stage_run_record() (+4 more)

### Community 100 - "Community 100"
Cohesion: 0.10
Nodes (8): build_derived_schedule(), _latent_task(), ResourceProfile, Schedule, _train_task(), validate_schedule(), Wave, test_derived_schedule_retrains_no_group1_model()

### Community 101 - "Community 101"
Cohesion: 0.16
Nodes (13): cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_build_transformer_samples_empty_when_nothing_cached(), test_build_transformer_samples_rejects_a_cache_smaller_than_grid_size(), test_build_transformer_samples_trims_the_real_41x41_crop_to_grid_size() (+5 more)

### Community 102 - "Community 102"
Cohesion: 0.14
Nodes (13): _FakeClient, _fix(), _make_output(), _record(), test_audit_run_degrades_per_record_when_audit_one_raises(), test_audit_run_replays_only_due_records_and_persists_the_result(), fake_audit_one(), test_audit_run_takes_a_bounded_batch_oldest_first() (+5 more)

### Community 103 - "Community 103"
Cohesion: 0.13
Nodes (8): svelte-guard@^1.1.1, DEFAULT_AFTER_LOGIN, loginHref(), safeNext(), requireSignIn(), requireSignInLoad(), guard(), svelte-guard

### Community 104 - "Community 104"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GH_TOKEN, IMPORTED_FROM, SOURCE_SHA, jobs, publish (+16 more)

### Community 105 - "Community 105"
Cohesion: 0.12
Nodes (12): _cron_run_offset_minutes(), _leaves(), _load(), test_a_config_change_redeploys_the_api(), test_both_images_copy_the_configs(), test_every_config_key_is_read_by_the_code(), test_every_config_parses_and_has_no_duplicate_keys(), test_every_image_build_is_smoke_tested_before_it_ships() (+4 more)

### Community 106 - "Community 106"
Cohesion: 0.08
Nodes (3): client(), test_more_members_than_the_ensemble_runs_is_refused_not_silently_capped(), test_sources_say_who_uses_each_one()

### Community 107 - "Community 107"
Cohesion: 0.13
Nodes (12): _localize_caches(), _files(), localize_cache(), LocalizeReport, _raise(), _cache(), test_a_directory_that_cant_be_listed_fails_the_copy(), test_a_missing_source_raises() (+4 more)

### Community 108 - "Community 108"
Cohesion: 0.08
Nodes (8): DELETE, GET, PATCH, POST, PUT, { data }, prerender, ssr

### Community 109 - "Community 109"
Cohesion: 0.14
Nodes (10): fetch_gefs_ensemble_grib2_fields(), fetch_gefs_member_grib2_fields(), _gefs_member_url(), _parse_grib2_index(), test_control_member_zero_uses_gec00_not_gep00(), test_fetch_gefs_ensemble_reads_multiple_real_distinct_members(), test_fetch_gefs_member_reads_the_real_noaa_archive(), test_member_out_of_range_raises() (+2 more)

### Community 110 - "Community 110"
Cohesion: 0.12
Nodes (9): calibration_out(), drift_report_out(), skew_report_out(), calibration(), drift(), drift_all(), skew(), SkewReportOut (+1 more)

### Community 111 - "Community 111"
Cohesion: 0.16
Nodes (14): detect_feature_drift(), FeatureDrift, ValidationLossMonitor, reference(), test_a_recovery_resets_the_consecutive_count(), test_collapsed_variance_is_detected(), test_feature_count_mismatch_raises(), test_first_observation_only_sets_the_baseline() (+6 more)

### Community 112 - "Community 112"
Cohesion: 0.13
Nodes (9): App, Locals, Platform, DEFAULT_EXTRA, ExtraPreferences, PackageManager, UserContext, UserIdentity (+1 more)

### Community 113 - "Community 113"
Cohesion: 0.11
Nodes (20): addingPasskey, addPasskey(), ApiKeySummary, createKey(), creating, { data }, deleteKey(), errorMsg (+12 more)

### Community 114 - "Community 114"
Cohesion: 0.13
Nodes (10): _download(), fetch_oisst_sst(), require_sst_deps(), sst_at(), SstFetchError, _small_grid(), test_fetch_oisst_sst_reads_real_recent_data(), test_sst_at_finds_the_nearest_cell() (+2 more)

### Community 115 - "Community 115"
Cohesion: 0.16
Nodes (16): _default_fetch_fn(), run_fetch_cache(), make_fields(), make_track(), test_build_fetch_tasks_covers_every_fix_across_tracks(), test_load_cached_fields_rejects_a_missing_file(), test_run_fetch_cache_actually_runs_fetches_concurrently(), slow_fetch() (+8 more)

### Community 116 - "Community 116"
Cohesion: 0.11
Nodes (12): fetch(), era5_to_gridded_fields(), crop(), crop_levels(), fetch_era5t_one(), open_era5(), open_era5_store(), fetch() (+4 more)

### Community 117 - "Community 117"
Cohesion: 0.14
Nodes (13): client(), _fields(), _MemoryS3, _run(), test_a_missing_t_minus_6_cycle_falls_back_to_t_minus_12(), fetch_one(), test_live_fields_come_from_the_t_minus_6_forecast(), fetch_one() (+5 more)

### Community 118 - "Community 118"
Cohesion: 0.09
Nodes (9): _FakeMlflowModelVersion, _mlflow_client_that_registers_and_transitions(), create_model_version(), test_mlflow_mirror_registers_model_then_version_with_a_real_source_uri(), create_model_version(), test_mlflow_mirror_skips_create_registered_model_if_it_already_exists(), create_model_version(), test_mlflow_transition_also_mirrors_the_archived_incumbent() (+1 more)

### Community 119 - "Community 119"
Cohesion: 0.14
Nodes (6): reference_value(), Threshold, _thresholds(), FusionArtifacts, run_fusion_curriculum(), test_beat_rate_threshold_is_higher_is_better()

### Community 120 - "Community 120"
Cohesion: 0.13
Nodes (11): era5_deps_available(), fetch_grib2_messages(), gridded_deps_available(), require_era5_deps(), require_gdas_deps(), require_gridded_deps(), _saturation_vapor_pressure_hpa_array(), _specific_humidity_to_rh_pct() (+3 more)

### Community 121 - "Community 121"
Cohesion: 0.14
Nodes (10): lr_factor(), transformer_optim(), TransformerOptim, TransformerOptimizer, test_a_short_stage_still_ends_on_the_floor(), test_config_values_are_validated(), test_cosine_decays_to_the_floor_on_the_last_update(), test_no_warmup_starts_at_the_peak() (+2 more)

### Community 122 - "Community 122"
Cohesion: 0.13
Nodes (11): recommend_extra_conditioning(), _fake_val(), _FakeS3Client, _lc(), patched(), fake_extract(), test_intensity_underdispersion_alone_does_not_trigger_it(), test_long_lead_track_underdispersion_warrants_extra_conditioning() (+3 more)

### Community 123 - "Community 123"
Cohesion: 0.10
Nodes (20): PROJECT_NUMBER, PROJECT_PAT, types, jobs, sync, name, on, issues (+12 more)

### Community 124 - "Community 124"
Cohesion: 0.13
Nodes (10): cmd_train(), _stage_b_frozen(), latest_final_season(), arch_params_tag(), basin_input_tags(), candidate_tags(), gridded_input_tags(), standardization_tags() (+2 more)

### Community 125 - "Community 125"
Cohesion: 0.19
Nodes (11): accessed(), _check_type(), config_dir(), ConfigError, fixed(), get(), get_list(), _load() (+3 more)

### Community 126 - "Community 126"
Cohesion: 0.16
Nodes (12): ohc_at(), ohc_global(), OhcField, _full_archive(), test_a_blank_run_longer_than_the_window_leaves_na_unavailable(), test_a_degraded_basin_flags_the_field(), test_an_unknown_basin_leaves_the_field_unknown_unless_another_is_degraded(), test_bilinear_is_exact_at_a_node_on_every_source() (+4 more)

### Community 127 - "Community 127"
Cohesion: 0.13
Nodes (8): OhcFile, al_2021_2022(), compare(), open_ocean(), parse_ships(), sample_days(), ShipsCase, test_sohc_equals_bilinear_ohc_on_the_file_named_for_the_day_before()

### Community 128 - "Community 128"
Cohesion: 0.16
Nodes (17): answerRuns(), chip(), context(), cycleFor(), dateButton(), expectForm(), expectShowing(), fixture (+9 more)

### Community 129 - "Community 129"
Cohesion: 0.10
Nodes (7): client(), test_docs_route_is_unaffected(), test_sources_role_is_the_role_enum_in_the_openapi_schema(), test_sources_used_by_is_documented_in_the_openapi_schema(), test_theme_http_method_colors_are_distinct(), test_theme_never_uses_a_god_color(), _walk()

### Community 130 - "Community 130"
Cohesion: 0.24
Nodes (14): storm_relative_sequence(), test_extrapolation_continues_the_last_motion_vector(), test_displacement_to_latlon_round_trips_with_displacement_nm(), make_fix(), test_displacement_direction_matches_bearing(), test_displacement_magnitude_matches_haversine_distance(), test_displacement_nm_matches_storm_relative_sequence(), test_eastward_motion_is_positive_dx_with_a_small_northward_component() (+6 more)

### Community 132 - "Community 132"
Cohesion: 0.15
Nodes (10): read_cached_official_errors(), OfficialErrorsError, parse_official_errors(), _signed(), test_a_cached_error_file_that_is_not_nhcs_is_named_with_the_way_out(), test_parse_official_errors_reads_columns_by_name_and_skips_missing_leads(), test_parse_official_errors_reads_the_stated_initial_position_domain(), test_parse_official_errors_rejects_a_file_without_the_column_header() (+2 more)

### Community 133 - "Community 133"
Cohesion: 0.15
Nodes (7): train_fusion_stage(), _FakeS3Client, _make_samples(), test_run_fusion_curriculum_uploads_a_checkpoint_and_registers_stage_b(), test_train_fusion_stage_reduces_loss_and_produces_val_metrics(), test_train_fusion_stage_rejects_a_val_set_built_with_a_different_model_count(), test_train_fusion_stage_rejects_empty_samples()

### Community 134 - "Community 134"
Cohesion: 0.15
Nodes (10): _attributes(), _calls(), _function(), _imported(), _names_adapter(), _parameters(), _parse(), _string_literals() (+2 more)

### Community 135 - "Community 135"
Cohesion: 0.15
Nodes (12): parse_bdeck(), parse_tcvitals(), TcVitalsError, test_bdeck_malformed_line_raises(), test_bdeck_parses_best_track_rows_only(), test_pair_by_valid_time_matches_shared_timestamps(), test_pair_by_valid_time_rejects_mismatched_storms(), test_recalibration_from_real_parsed_pairs_measures_nonzero_error() (+4 more)

### Community 136 - "Community 136"
Cohesion: 0.15
Nodes (13): apply_cold_wake(), cold_wake_sst_depression_c(), generate_archive(), test_apply_cold_wake_depresses_sst_and_ohc_without_touching_other_fields(), test_apply_cold_wake_is_a_noop_for_a_calm_storm(), test_cold_wake_depression_grows_with_wind_and_shrinks_with_translation_speed(), test_cold_wake_is_a_noop_for_zero_wind(), test_leakage_is_detected_when_a_storm_id_repeats_across_seasons() (+5 more)

### Community 137 - "Community 137"
Cohesion: 0.15
Nodes (12): compute_environment_features(), deep_layer_shear(), generate_fields(), field(), test_compare_potential_intensity_estimates_documents_the_closed_form_running_hot(), test_compute_environment_features_raises_when_storm_is_entirely_over_land(), test_compute_environment_features_succeeds_with_partial_land_coverage(), test_feature_vector_length_matches_the_names() (+4 more)

### Community 138 - "Community 138"
Cohesion: 0.12
Nodes (4): _Boto3Client, require_boto3(), _StorageClient, test_boto3_adapter_configures_the_client_for_the_given_endpoint()

### Community 139 - "Community 139"
Cohesion: 0.17
Nodes (7): mlflow_client_from_env(), test_an_unreachable_server_is_skipped_fast(), test_builds_a_real_client_when_tracking_uri_is_set(), test_fail_fast_settings_never_override_explicit_ones(), test_mlflow_client_from_env_can_actually_reach_the_configured_server(), test_returns_none_when_tracking_uri_is_unset(), test_returns_none_without_mlflow_installed()

### Community 140 - "Community 140"
Cohesion: 0.24
Nodes (7): freeCycleLabel(), label(), runFreshCycle(), signIn(), cases, @playwright/test@^1.63.0, @playwright/test

### Community 141 - "Community 141"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 142 - "Community 142"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 143 - "Community 143"
Cohesion: 0.15
Nodes (6): CloudflareAccessRequestHeaderProvider, test_headers_are_actually_applied_by_mlflows_own_resolution(), test_in_context_false_when_neither_var_set(), test_in_context_false_when_only_client_id_set(), test_in_context_true_and_correct_headers_when_both_set(), test_registered_as_a_real_mlflow_plugin_via_entry_points()

### Community 144 - "Community 144"
Cohesion: 0.18
Nodes (8): get_cycle(), get_storm(), list_storms(), _overrides(), run_cycle(), _served_basins(), _storm_summary(), FixOut

### Community 145 - "Community 145"
Cohesion: 0.14
Nodes (9): config_copy(), edit(), _image_layout(), _run(), test_a_missing_config_dir_is_refused(), test_an_image_without_configs_fails_at_import_and_says_why(), test_an_invalid_config_is_refused_with_a_clear_message(), test_edited_values_take_effect_at_runtime() (+1 more)

### Community 146 - "Community 146"
Cohesion: 0.11
Nodes (7): area_mean(), integrated_vapor_transport(), relative_vorticity_850(), steering_flow(), test_area_mean_ignores_nan_pixels_from_partial_land_coverage(), test_area_mean_matches_plain_mean_when_nothing_is_nan(), test_area_mean_returns_nan_when_the_whole_box_is_land()

### Community 147 - "Community 147"
Cohesion: 0.14
Nodes (8): _bilinear(), _declared_length(), detect_format(), _grid_values(), _lattice_index(), OhcRejected, _read_checked(), test_format_is_detected_from_the_first_bytes()

### Community 148 - "Community 148"
Cohesion: 0.16
Nodes (10): _fake_samples(), _lc(), _report(), _stats(), teacher_and_data(), test_a_collapsed_student_is_not_warranted(), test_a_student_close_to_teacher_calibration_is_warranted(), test_distillation_rejects_a_non_positive_epochs_or_patience() (+2 more)

### Community 149 - "Community 149"
Cohesion: 0.12
Nodes (16): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+8 more)

### Community 150 - "Community 150"
Cohesion: 0.16
Nodes (14): minisearch@^7.2.0, loading, onInput(), open, query, results, bodyById, buildIndex() (+6 more)

### Community 151 - "Community 151"
Cohesion: 0.12
Nodes (16): compilerOptions, allowJs, allowSyntheticDefaultImports, checkJs, forceConsistentCasingInFileNames, isolatedModules, lib, module (+8 more)

### Community 152 - "Community 152"
Cohesion: 0.12
Nodes (16): permissions, runs-on, steps, jobs, copilot-setup-steps, name, on, pull_request (+8 more)

### Community 153 - "Community 153"
Cohesion: 0.15
Nodes (9): compare_potential_intensity_estimates(), emanuel_potential_intensity(), potential_intensity(), _saturation_vapor_pressure_hpa(), _specific_humidity_kg_kg(), test_emanuel_pi_increases_with_warmer_sst(), test_emanuel_pi_is_reduced_above_the_shear_onset(), test_emanuel_pi_is_zero_when_the_boundary_layer_is_warmer_and_moister_than_the_surface() (+1 more)

### Community 154 - "Community 154"
Cohesion: 0.18
Nodes (7): assert_flavor(), FeatureSet, FlavorMismatchError, Normalizer, test_flavor_guard_rejects_a_pretrain_feature_on_the_operational_path(), test_normalizer_refuses_to_fit_across_flavors(), test_normalizer_rejects_the_wrong_flavor_at_apply_time()

### Community 155 - "Community 155"
Cohesion: 0.26
Nodes (9): NoiseSensitivityReport, _result(), test_is_load_bearing_above_threshold(), test_is_not_load_bearing_below_threshold(), test_relative_change_is_zero_when_losses_match(), test_relative_change_rejects_nonpositive_default_loss(), test_relative_change_sign_matches_direction_of_the_move(), test_run_noise_sensitivity_covers_both_candidates_on_a_small_synthetic_archive() (+1 more)

### Community 156 - "Community 156"
Cohesion: 0.12
Nodes (16): with, build-args, cache-from, cache-to, context, file, load, password (+8 more)

### Community 157 - "Community 157"
Cohesion: 0.12
Nodes (15): jobs, lint-and-validate, name, permissions, runs-on, steps, name, on (+7 more)

### Community 158 - "Community 158"
Cohesion: 0.13
Nodes (8): source_out(), health(), models(), sources(), HealthOut, SourceOut, DataSource, pretrain_only_sources()

### Community 159 - "Community 159"
Cohesion: 0.22
Nodes (9): run_spread_backtest(), SpreadBacktestError, _registry_with_champions(), _store(), test_diffusion_version_override_measures_that_version_not_the_champion(), test_diffusion_version_override_raises_cleanly_for_an_unknown_version(), test_diffusion_version_override_still_enforces_the_real_latent_signature(), test_refuses_a_diffusion_desynced_from_the_live_champions() (+1 more)

### Community 160 - "Community 160"
Cohesion: 0.13
Nodes (15): scripts, build, cf:deploy, check, check:errors, check:warnings, check:watch, dev (+7 more)

### Community 161 - "Community 161"
Cohesion: 0.13
Nodes (15): env, environment, if, name, needs, permissions, runs-on, timeout-minutes (+7 more)

### Community 162 - "Community 162"
Cohesion: 0.24
Nodes (11): validate(), make_tags(), test_malformed_dvc_version_is_rejected(), test_malformed_git_commit_is_rejected(), test_malformed_nwp_cycle_lag_is_rejected(), test_none_values_are_dropped_from_the_dict(), test_pretrain_flavor_tags_are_not_operational(), test_v2_1_adds_input_flavor_and_nwp_cycle_lag() (+3 more)

### Community 163 - "Community 163"
Cohesion: 0.14
Nodes (8): API, DEVELOP, PHONE, SourceRow, SOURCES, SOURCES_BEFORE_USED_BY, SOURCES_REWIRED, path()

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
Cohesion: 0.18
Nodes (9): cmd_baseline_backtest(), parse_hurdat2_statuses(), git_sha(), _fmt(), format_report(), RegisteredError, report(), test_registered_error_spec() (+1 more)

### Community 168 - "Community 168"
Cohesion: 0.16
Nodes (5): make_storm_spec(), paired_fields(), StormSpec, test_synthetic_gdas_carries_a_measurable_offset_from_era5(), test_the_same_code_path_computes_both_flavors()

### Community 169 - "Community 169"
Cohesion: 0.19
Nodes (10): generate_season(), test_archive_spans_the_requested_seasons(), test_fields_have_matching_shapes_and_carry_a_flavor(), test_fixes_are_six_hourly_and_synoptic(), test_gdas_fields_are_noisier_than_era5(), test_generated_tracks_are_final_quality(), test_generation_is_reproducible(), test_intensity_rises_and_falls() (+2 more)

### Community 170 - "Community 170"
Cohesion: 0.20
Nodes (8): _cache_steering(), make_track(), test_compare_refuses_arms_on_different_windows_and_pairs_the_rest(), test_stage_b_trains_the_steering_conv_and_keeps_the_rest_frozen(), test_steering_vectors_are_appended_after_the_basin_channels(), extra(), test_the_spike_runs_both_arms_on_the_same_windows_and_registers_nothing(), test_track_errors_are_zero_for_a_perfect_forecast_and_nan_without_a_target()

### Community 171 - "Community 171"
Cohesion: 0.31
Nodes (10): QUICK, addVirtualAuthenticator(), EMAIL_DIR, EMAIL_LOCK, listEmailFiles(), localD1(), setRegistrationOpen(), signUpViaMagicLink() (+2 more)

### Community 172 - "Community 172"
Cohesion: 0.17
Nodes (12): IdTokenClaims, JwtClaims, OidcAddressClaim, OidcStandardClaims, UserProfile, Mandatory, RFC-3966, RFC-4627 (+4 more)

### Community 173 - "Community 173"
Cohesion: 0.15
Nodes (12): name, runs-on, timeout-minutes, concurrency, cancel-in-progress, group, jobs, build (+4 more)

### Community 174 - "Community 174"
Cohesion: 0.17
Nodes (6): _called(), _modules(), test_an_adapter_is_named_by_other_code_only_if_its_source_is_read(), test_every_fetch_adapter_is_classified(), test_no_module_imports_by_a_computed_name(), _unread_sources()

### Community 175 - "Community 175"
Cohesion: 0.23
Nodes (11): max, target, budgets, reduced, standard, max, target, assembly (+3 more)

### Community 176 - "Community 176"
Cohesion: 0.21
Nodes (7): client(), test_a_registered_versions_arch_params_are_used(), test_a_version_that_reads_steering_is_described(), test_a_version_without_arch_params_is_described_from_defaults(), test_every_model_runs_its_example_input_and_reports_its_layers(), test_the_gnn_is_fed_the_real_lattice(), test_unknown_models_and_versions_are_404()

### Community 177 - "Community 177"
Cohesion: 0.17
Nodes (11): concurrency, cancel-in-progress, group, jobs, test-api, name, if, name (+3 more)

### Community 178 - "Community 178"
Cohesion: 0.17
Nodes (12): with, cache, cache-dependency-path, enable-cache, fetch-depth, if-no-files-found, include-hidden-files, name (+4 more)

### Community 179 - "Community 179"
Cohesion: 0.24
Nodes (7): model_version_out(), get_active_pin(), get_model_registry(), list_registry(), ActivePin, ModelVersionOut, RegistryEntry

### Community 180 - "Community 180"
Cohesion: 0.18
Nodes (11): cycle, advisory_margin_minutes, advisory_offset_minutes, allow_estimated_vitals, allow_load_shedding, max_nwp_lag_hours, nominal_vitals_offset_minutes, nwp_lag_hours (+3 more)

### Community 181 - "Community 181"
Cohesion: 0.22
Nodes (7): assert_not_operational(), operational_sources(), _operational_substitute(), OperationalUseError, test_operational_sources_pass_the_guard(), test_reading_era5_in_the_inference_path_is_refused(), test_reading_final_besttrack_in_the_inference_path_is_refused()

### Community 182 - "Community 182"
Cohesion: 0.22
Nodes (6): first_record_of_year(), ships_al_url(), _ships_get(), ships_record_year(), ships_size(), ships_window()

### Community 183 - "Community 183"
Cohesion: 0.20
Nodes (10): limit, lower_is_better, limit, lower_is_better, thresholds, intensity_error_48h_kt, intensity_error_72h_kt, track_error_72h_nm (+2 more)

### Community 184 - "Community 184"
Cohesion: 0.20
Nodes (10): steps, EXPECT_GIT_SHA, GCP_CI_SERVICE_ACCOUNT, GCP_WIF_PROVIDER, env, id, if, name (+2 more)

### Community 185 - "Community 185"
Cohesion: 0.20
Nodes (10): name, outputs, runs-on, timeout-minutes, changes, deploy_api, deploy_console, plan (+2 more)

### Community 186 - "Community 186"
Cohesion: 0.40
Nodes (10): steps, steps, id, if, name, run, uses, working-directory (+2 more)

### Community 187 - "Community 187"
Cohesion: 0.27
Nodes (6): _default_fetch_fn(), fetch(), fetch_gdas_grib2_fields(), gfs_url(), test_gfs_url_names_the_forecast_valid_at_the_time(), fetch_one()

### Community 188 - "Community 188"
Cohesion: 0.27
Nodes (4): ChecksumCheck, FetchResult, NonEmptyCheck, QCFinding

### Community 189 - "Community 189"
Cohesion: 0.20
Nodes (7): used_by(), test_cmd_sources_prints_who_uses_each_source(), test_a_verification_source_not_read_yet_is_verification_and_nothing_else(), test_every_required_cycle_input_has_a_model_consumer(), test_used_by_follows_the_contract_order_for_every_source(), test_used_by_per_source(), test_used_by_refuses_an_unknown_source()

### Community 190 - "Community 190"
Cohesion: 0.22
Nodes (9): run, test-console, working-directory, defaults, if, name, needs, runs-on (+1 more)

### Community 191 - "Community 191"
Cohesion: 0.22
Nodes (9): BASE_SHA, BEFORE_SHA, DISPATCH_API, DISPATCH_CONSOLE, EVENT, EXPECT_GIT_SHA, HEAD_SHA, REF (+1 more)

### Community 193 - "Community 193"
Cohesion: 0.22
Nodes (4): test_a_desynced_derived_champion_is_not_a_bar_a_servable_candidate_must_clear(), test_a_servable_derived_champion_is_still_a_real_bar(), test_derived_resync_records_the_champion_signature_and_ends_in_sync(), test_seed_from_champions_refuses_an_incomplete_champion_set()

### Community 194 - "Community 194"
Cohesion: 0.28
Nodes (4): oracle(), pytest_collection_modifyitems(), target_time(), worst_case_oracle()

### Community 195 - "Community 195"
Cohesion: 0.25
Nodes (8): 12, 120, 24, 36, 48, 72, 96, climatological_cone_nm

### Community 196 - "Community 196"
Cohesion: 0.25
Nodes (8): CP, 12, 120, 24, 36, 48, 72, 96

### Community 197 - "Community 197"
Cohesion: 0.25
Nodes (8): EP, 12, 120, 24, 36, 48, 72, 96

### Community 198 - "Community 198"
Cohesion: 0.25
Nodes (7): calibration_audit, cone_nominal_rate, intensity_nominal_rate, min_cases, verdict_margin, test_set_budget, max_evaluations_per_season

### Community 199 - "Community 199"
Cohesion: 0.25
Nodes (8): drift, min_samples, reference_flavor, shift_sigma, validation_loss, variance_ratio_limit, consecutive_required, threshold_fraction

### Community 200 - "Community 200"
Cohesion: 0.25
Nodes (8): promotion, flavor, new_basin_tolerance, primary_metric, reference_basin, require_manual_gate, split, basins()

### Community 201 - "Community 201"
Cohesion: 0.29
Nodes (4): _get(), _get_bytes(), NotPublished, fetch_live_adeck()

### Community 202 - "Community 202"
Cohesion: 0.29
Nodes (7): products, cone_percentile, landfall_threshold_nm, lead_hours, ri_alert_probability, ri_threshold_kt, ri_window_hours

### Community 203 - "Community 203"
Cohesion: 0.29
Nodes (7): skew_audit, alert_intensity_delta_kt, alert_track_delta_nm, audit_delay_days, lead_hours, min_samples, window_days

### Community 204 - "Community 204"
Cohesion: 0.57
Nodes (5): deploy-plan.sh script, touches(), touches_component(), touches_console(), why

### Community 205 - "Community 205"
Cohesion: 0.29
Nodes (7): env, IMAGE, JOB, PROJECT_ID, PUBLISH, REGION, REGISTRY

### Community 206 - "Community 206"
Cohesion: 0.29
Nodes (3): retrain_job_out(), pending_triggers(), RetrainJobOut

### Community 207 - "Community 207"
Cohesion: 0.29
Nodes (3): archive_atcf(), calibration_audit(), skew_audit()

### Community 209 - "Community 209"
Cohesion: 0.29
Nodes (5): __init__(), extra_input_linear(), __init__(), __init__(), __init__()

### Community 210 - "Community 210"
Cohesion: 0.33
Nodes (6): ensemble, climatological_cone_nm_by_basin, members, min_members_for_ensemble_cone, reduced_members, underdispersion_fraction

### Community 211 - "Community 211"
Cohesion: 0.33
Nodes (6): triggers, data_volume_threshold, nightly_latent_hour_utc, preseason_date, scheduled_monthly_day, suppress_nightly_latent_during_active_storms

### Community 214 - "Community 214"
Cohesion: 0.33
Nodes (6): update_job, workflow_dispatch, default, description, type, inputs

### Community 215 - "Community 215"
Cohesion: 0.33
Nodes (6): on, pull_request, push, paths, branches, paths

### Community 216 - "Community 216"
Cohesion: 0.33
Nodes (3): inner_core_moisture(), _radial_gradient_fields(), test_inner_core_moisture_reflects_the_core_not_the_environment()

### Community 219 - "Community 219"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 220 - "Community 220"
Cohesion: 0.40
Nodes (3): WORLD_GEOJSON, WorldData, WorldFeatureProperties

### Community 221 - "Community 221"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 222 - "Community 222"
Cohesion: 0.40
Nodes (4): ANEMOI_ADECK_DIR, ANEMOI_FIELDS_MEMO, ANEMOI_STEERING_CACHE_DIR, entrypoint.sh script

### Community 227 - "Community 227"
Cohesion: 0.67
Nodes (4): max, target, diffusion, diffusion

### Community 228 - "Community 228"
Cohesion: 0.67
Nodes (4): max, target, fusion, fusion

### Community 229 - "Community 229"
Cohesion: 0.67
Nodes (4): max, target, postprocess, postprocess

### Community 230 - "Community 230"
Cohesion: 0.67
Nodes (4): max, target, preprocess, preprocess

### Community 231 - "Community 231"
Cohesion: 0.83
Nodes (3): graphify(), normalise_graph(), build-graph.sh script

### Community 232 - "Community 232"
Cohesion: 0.50
Nodes (3): uvx, graphify, graphify-mcp

### Community 238 - "Community 238"
Cohesion: 0.67
Nodes (3): limit, lower_is_better, nhc_consensus_beat_rate_48h

### Community 239 - "Community 239"
Cohesion: 0.67
Nodes (3): track_error_120h_nm, limit, lower_is_better

### Community 240 - "Community 240"
Cohesion: 0.67
Nodes (3): track_error_48h_nm, limit, lower_is_better

## Knowledge Gaps
- **15 isolated node(s):** `$lib/registry/blocks/navigation/components/site.context.svelte`, `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627`, `RFC-5322` (+10 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2874 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Flavor` connect `Community 31` to `Community 0`, `Community 1`, `Community 2`, `Community 131`, `Community 133`, `Community 5`, `Community 7`, `Community 136`, `Community 137`, `Community 10`, `Community 9`, `Community 17`, `Community 19`, `Community 23`, `Community 24`, `Community 153`, `Community 154`, `Community 25`, `Community 26`, `Community 159`, `Community 32`, `Community 162`, `Community 34`, `Community 35`, `Community 37`, `Community 168`, `Community 169`, `Community 170`, `Community 44`, `Community 45`, `Community 46`, `Community 47`, `Community 176`, `Community 50`, `Community 51`, `Community 52`, `Community 54`, `Community 55`, `Community 58`, `Community 59`, `Community 61`, `Community 65`, `Community 193`, `Community 72`, `Community 76`, `Community 78`, `Community 81`, `Community 82`, `Community 216`, `Community 90`, `Community 247`, `Community 91`, `Community 96`, `Community 224`, `Community 226`, `Community 99`, `Community 225`, `Community 101`, `Community 110`, `Community 111`, `Community 115`, `Community 116`, `Community 117`, `Community 118`, `Community 119`, `Community 120`, `Community 124`, `Community 125`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 257 inferred relationships involving `Flavor` (e.g. with `DemoState` and `drift()`) actually correct?**
  _`Flavor` has 257 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$lib/registry/blocks/navigation/components/site.context.svelte`, `./.svelte-kit/tsconfig.json`, `RFC-3966` to the rest of the system?**
  _15 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.02606698360130335 - nodes in this community are weakly interconnected._
- **Why does `Track` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 131`, `Community 6`, `Community 7`, `Community 8`, `Community 135`, `Community 136`, `Community 11`, `Community 9`, `Community 10`, `Community 14`, `Community 17`, `Community 23`, `Community 24`, `Community 25`, `Community 155`, `Community 159`, `Community 32`, `Community 31`, `Community 34`, `Community 35`, `Community 168`, `Community 169`, `Community 170`, `Community 43`, `Community 44`, `Community 45`, `Community 48`, `Community 50`, `Community 51`, `Community 54`, `Community 58`, `Community 59`, `Community 60`, `Community 68`, `Community 69`, `Community 74`, `Community 78`, `Community 86`, `Community 88`, `Community 91`, `Community 101`, `Community 102`, `Community 115`, `Community 117`, `Community 247`, `Community 124`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 144 inferred relationships involving `Track` (e.g. with `save_cycle_inputs()` and `StormState`) actually correct?**
  _`Track` has 144 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.031123805771693096 - nodes in this community are weakly interconnected._