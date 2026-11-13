# Graph Report - anemoi  (2026-11-13)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 6674 nodes · 17045 edges · 246 communities (215 shown, 31 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 2478 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8f230397`
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
- Community 225
- Community 226
- Community 227
- Community 228
- Community 229
- Community 230
- Community 231
- Community 232
- Community 233
- Community 235
- Community 236
- Community 237
- Community 238
- Community 239
- Community 240
- Community 241
- Community 243
- Community 244
- Community 245

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
- `test_internal_calibration_audit_route_reports_new_samples()` --uses--> `RealState`  [INFERRED]
  tests/test_api_real_state.py → src/anemoi/api/real_state.py
- `test_cache_round_trip_and_vector()` --uses--> `FetchTask`  [INFERRED]
  tests/test_steering.py → src/anemoi/data/gridded_cache.py
- `make_fix()` --calls--> `Fix`  [INFERRED]
  tests/test_streaming.py → src/anemoi/data/besttrack.py
- `test_a_versions_arch_params_change_what_is_described()` --calls--> `describe()`  [INFERRED]
  tests/test_model_architecture.py → src/anemoi/models/architecture.py
- `test_the_gnn_is_fed_the_real_lattice()` --calls--> `describe()`  [INFERRED]
  tests/test_model_architecture.py → src/anemoi/models/architecture.py

## Import Cycles
- None detected.

## Communities (246 total, 31 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (33): basins_of(), augment_track(), emulate_working_track(), WorkingTrackNoise, sanitize_field_pixels(), filter_tracks(), latest_final_season(), displacement_nm() (+25 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (68): ModelSpec, require_torch(), build_diffusion(), __init__(), _cosine_schedule(), build_fusion(), forward(), __init__() (+60 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (45): cycle_products_out(), god_out(), model_catalog(), model_version_out(), get_state(), require_api_key(), state_dependency(), get_custom_redoc_html() (+37 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (64): cycle_inputs_prefix(), save_cycle_inputs(), GriddedFields, cache_path(), _decode_cached_fields(), FetchTask, load_cached_fields(), _memo_enabled() (+56 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (53): Flavor, ModelRegistry, RegistryError, Stage, _champions(), test_a_basin_is_served_once_every_champion_is_verified_in_it(), test_a_champion_verified_nowhere_serves_no_basin_as_in_distribution(), test_no_champion_or_champions_from_before_the_tag_are_the_atlantic() (+45 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (43): TransformerOptimizer, train_cnn_stage_streaming(), freeze_encoder(), train_gnn_stage_streaming(), iter_stage_windows(), StageWindow, train_lstm_stage_streaming(), build_transformer_samples() (+35 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (48): Fix, Track, generate_track(), _build_live_context(), _build_live_x(), build_live_cnn_x(), build_live_gnn_x(), build_live_lstm_x() (+40 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (41): cmd_baseline_backtest(), Adeck, storm_basin(), recalibrate_from_pairs(), OfficialErrors, as_issued(), calibrate_season(), basin_key() (+33 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (72): ApiError, apiFetch(), getArchitecture(), getCalibration(), getCycle(), getDrift(), getDriftAll(), getModelRegistry() (+64 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (46): bearing_deg(), bearings_deg(), cross_along_track_nm(), cross_along_track_nms(), haversine_nm(), km_to_nm(), nm_to_km(), offset_position() (+38 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (43): cycle_key(), load_cycle_result(), save_cycle_result(), CycleResult, audit_cycle(), audit_due(), audit_storm(), _audited_key() (+35 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (38): cmd_ablation(), cmd_adeck_fetch(), cmd_atcf_archive(), cmd_cache_localize(), cmd_consistency_distill(), cmd_drift_reference_fit(), cmd_era5_cache(), cmd_gdas_cache() (+30 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (75): dependencies, arktype@^2.2.7, @better-auth/passkey@^1.7.7, bits-ui@^2.20.6, clsx@^2.1.1, d3-polygon@^3.0.1, d3-scale@^4.0.2, @internationalized/date@^3.12.4 (+67 more)

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (9): cycle_payload_out(), cycle_result_out(), provenance_out(), CycleHistory, RealState, deterministic(), live_fields(), RealStormState (+1 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (35): basin_inputs(), ModelVersion, _builder(), deterministic_fn(), _compute_env_features(), _item_stat(), _real_fusion_forecast(), _run_group1_model() (+27 more)

### Community 15 - "Community 15"
Cohesion: 0.04
Nodes (53): FixOut, bounds, colors, coneFeatures, coneHull, currentFix, forecastLine, forecastPoints (+45 more)

### Community 16 - "Community 16"
Cohesion: 0.04
Nodes (52): svelte-sonner@^1.2.3, ModelCatalog, BY_ARCHITECTURE, BY_SLUG, FUNCTIONAL_COLORS, FUSION_COLOR, GOD_ORDER, GODS (+44 more)

### Community 17 - "Community 17"
Cohesion: 0.05
Nodes (34): _crop_variable(), fetch_real_satellite_crop(), _find_real_scan(), GoesFetchError, _lazy_open(), _list_scan_keys(), _nearest_scan_key(), _parse_scan_start() (+26 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (31): check_run(), CycleConflict, _existing_source(), InFlight, operator_ids(), RunRequest, stored_source(), _synthetic_fallback_deterministic() (+23 more)

### Community 19 - "Community 19"
Cohesion: 0.06
Nodes (50): @cloudflare/containers@^0.3.7, AppAuth, buildAuth(), getAuth(), verifyApiKey(), CYCLE_STEP, cycleInstanceId(), CycleParams (+42 more)

### Community 20 - "Community 20"
Cohesion: 0.06
Nodes (33): retrain_job_out(), pending_triggers(), RetrainJobOut, invalidated_by(), evaluate_all(), expand_jobs(), nightly_latent(), on_data_volume() (+25 more)

### Community 21 - "Community 21"
Cohesion: 0.05
Nodes (35): _baseline_inputs(), _empty_report(), _fake_checkpoint_store(), _hurdat2_storm(), make_args(), make_track(), _retrain_check_args(), _spy_assign_splits() (+27 more)

### Community 22 - "Community 22"
Cohesion: 0.07
Nodes (40): brier_score(), crps_ensemble(), _crps_rows(), crps_series(), ensemble_percentiles(), rank_histogram(), reliability(), spread_skill() (+32 more)

### Community 23 - "Community 23"
Cohesion: 0.07
Nodes (36): build_cone(), build_products(), climatological_cone_nm(), cone_radius_from_spread(), ConeSegment, deterministic_center(), EnsembleMember, intensity_pdf() (+28 more)

### Community 24 - "Community 24"
Cohesion: 0.07
Nodes (33): build_derived_schedule(), build_schedule(), _latent_task(), Mode, OrchestrationResult, ResourceProfile, run_schedule(), RunOutcome (+25 more)

### Community 25 - "Community 25"
Cohesion: 0.06
Nodes (33): basin_value(), scored_basins(), trained_basins(), verified_basins(), basin_tags(), served_columns(), reference_value(), by_basin() (+25 more)

### Community 26 - "Community 26"
Cohesion: 0.06
Nodes (34): adeck_name(), adeck_path(), adeck_urls(), AdeckFetchReport, CachedAdecks, _check_adeck(), _check_official_errors(), fetch_adecks() (+26 more)

### Community 27 - "Community 27"
Cohesion: 0.05
Nodes (25): App, Locals, Platform, categories, choosing, mounted, picked, visible (+17 more)

### Community 28 - "Community 28"
Cohesion: 0.07
Nodes (38): getActivePin(), getSources(), listRegistry(), ActivePin, RegistryEntry, errorDetail(), notifyError(), anchor (+30 more)

### Community 29 - "Community 29"
Cohesion: 0.06
Nodes (33): build_lstm(), encode(), forward(), __init__(), build_stage_samples(), _train_candidate_lstm_streaming(), build_x(), StageSamples (+25 more)

### Community 30 - "Community 30"
Cohesion: 0.05
Nodes (34): guards, handle, Props, Section, SectionPage, { sections }, height, motionClass (+26 more)

### Community 31 - "Community 31"
Cohesion: 0.06
Nodes (32): select_basins(), Archive, archives_for(), describe(), fetch_latest_hurdat2(), last_season(), latest_name(), manifest_path() (+24 more)

### Community 32 - "Community 32"
Cohesion: 0.06
Nodes (26): latent_signature(), ConeOutcome, format_report(), recommend_extra_conditioning(), run_spread_backtest(), SpreadBacktestError, SpreadBacktestReport, test_signature_changes_when_any_group1_version_changes() (+18 more)

### Community 33 - "Community 33"
Cohesion: 0.05
Nodes (46): layerchart@^2.5.1, ConeSegmentOut, CyclePayload, CycleProducts, CycleResult, DriftReportOut, FeatureDriftOut, HealthOut (+38 more)

### Community 34 - "Community 34"
Cohesion: 0.07
Nodes (31): archive_key(), ArchiveClient, build_fetch_tasks(), shard_tracks(), sync_cache_to_archive(), SyncReport, FakeArchive, _fix_keys() (+23 more)

### Community 35 - "Community 35"
Cohesion: 0.07
Nodes (31): build_gnn(), encode(), forward(), __init__(), batch_graph(), build_gnn_samples(), build_mesh_topology(), GnnStageSamples (+23 more)

### Community 36 - "Community 36"
Cohesion: 0.06
Nodes (42): SourceOut, byUse(), hasUnknownEntry(), MODEL_NAMES, MODELS, ORDER, readersOf(), SOURCE_NAMES (+34 more)

### Community 37 - "Community 37"
Cohesion: 0.05
Nodes (26): client(), _get_real_state(), hurdat2_file(), _stage_group1_and_derived(), test_a_live_storm_keeps_its_cycles_across_a_feed_refresh(), test_a_stale_refresh_in_flight_serves_known_storms_without_waiting(), test_calibration_report_is_honest_empty_with_no_samples(), test_calibration_report_reflects_persisted_samples() (+18 more)

### Community 38 - "Community 38"
Cohesion: 0.06
Nodes (23): @lucide/svelte@^1.71.0, sveltekit-superforms@^2.31.0, authClient, { form }, Props, { form }, Props, errorMsg (+15 more)

### Community 39 - "Community 39"
Cohesion: 0.07
Nodes (22): AvailabilityOracle, CycleInputs, earliest_ready_time(), InputStatus, resolve_cycle_inputs(), _valid_time_for(), oracle(), target_time() (+14 more)

### Community 40 - "Community 40"
Cohesion: 0.05
Nodes (15): experiment_name(), _RecordingStore, _StubMlflowClient, _StubRun, _StubRunInfo, test_a_failing_store_never_fails_training(), test_baseline_beaten_is_none_when_metric_is_missing(), test_baseline_beaten_matches_promotions_own_threshold() (+7 more)

### Community 41 - "Community 41"
Cohesion: 0.09
Nodes (28): assert_deployable(), Curriculum, CurriculumError, stage_a(), stage_b(), StageResult, _fake_curriculum_run(), result() (+20 more)

### Community 42 - "Community 42"
Cohesion: 0.08
Nodes (28): list_cycle_labels(), archive_atcf(), archived_tcvitals(), ArchiveReport, currentstorms_key(), _digest(), _get_text(), _load_recent() (+20 more)

### Community 43 - "Community 43"
Cohesion: 0.07
Nodes (24): advisory_time(), floor_synoptic(), is_synoptic(), next_synoptic(), NWPCycleSelection, NWPUnavailableError, parse_cycle_label(), require_synoptic() (+16 more)

### Community 44 - "Community 44"
Cohesion: 0.10
Nodes (25): case_errors(), compared_members(), homogeneous_mask(), _limiting(), _mean(), Member, MemberScore, _paired() (+17 more)

### Community 45 - "Community 45"
Cohesion: 0.10
Nodes (26): basin_input_tags(), gridded_input_tags(), CurriculumRun, OrchestrationError, MetricSet, PromotionDecision, RealOrchestratorRunner, _run_cnn() (+18 more)

### Community 46 - "Community 46"
Cohesion: 0.09
Nodes (29): ExecutionMode, Task, _fake_curriculum_run(), fake_load_run_artifacts(), _FakeJointLatents, runner(), fake_extract_joint_latents(), make_fake() (+21 more)

### Community 47 - "Community 47"
Cohesion: 0.10
Nodes (25): _get_text(), load_drift_live(), _put_text(), save_drift_live(), _load_audited(), audit_one(), audit_run(), _AuditPlan (+17 more)

### Community 48 - "Community 48"
Cohesion: 0.09
Nodes (32): assert_input_safe(), emulate_working_fix(), lr_factor(), _latlon(), make_fix(), make_track(), test_assert_input_safe_allows_working_quality(), test_assert_input_safe_blocks_final_quality() (+24 more)

### Community 49 - "Community 49"
Cohesion: 0.07
Nodes (26): _crop_box(), era5_to_gridded_fields(), crop(), crop_levels(), gdas_to_gridded_fields(), crop(), _saturation_vapor_pressure_hpa_array(), _specific_humidity_to_rh_pct() (+18 more)

### Community 50 - "Community 50"
Cohesion: 0.10
Nodes (25): evaluate_promotion(), PromotionError, TestSetBudget, Threshold, _thresholds(), complete_run(), good_metrics(), test_beat_rate_threshold_is_higher_is_better() (+17 more)

### Community 51 - "Community 51"
Cohesion: 0.13
Nodes (25): run_cycle(), deterministic_fn(), good_ensemble(), make_fix(), test_a_pacific_climatological_ensemble_is_drawn_from_pacific_radii(), test_absent_opportunistic_feeds_do_not_flag_the_cycle(), test_an_eastern_pacific_cycle_falls_back_to_nhcs_pacific_radii(), test_caller_requested_members_is_honored_by_the_climatological_fallback() (+17 more)

### Community 52 - "Community 52"
Cohesion: 0.08
Nodes (18): absolute_pairs(), is_basin_key(), key_basin(), per_basin_scores(), ForecastPoint, LeadTimeStats, to_metric_dict(), VerificationPair (+10 more)

### Community 53 - "Community 53"
Cohesion: 0.11
Nodes (27): LatencyOracle, CycleAbandoned, derive_vitals_timeout(), plan_cycle(), total_budget(), test_a_cycle_started_at_the_timeout_still_clears_the_margin(), test_all_four_daily_cycles_plan_and_meet_their_deadlines(), test_core_is_ready_before_spread() (+19 more)

### Community 54 - "Community 54"
Cohesion: 0.09
Nodes (27): QUICK, addVirtualAuthenticator(), EMAIL_DIR, EMAIL_LOCK, listEmailFiles(), localD1(), setRegistrationOpen(), signUpViaMagicLink() (+19 more)

### Community 55 - "Community 55"
Cohesion: 0.12
Nodes (17): audit_due(), _prune_samples(), SkewMonitor, SkewReport, SkewSample, sample(), test_audit_becomes_due_once_era5t_lands(), test_audit_is_not_due_immediately_after_the_cycle() (+9 more)

### Community 56 - "Community 56"
Cohesion: 0.12
Nodes (21): build_cnn(), encode(), forward(), __init__(), cache_all_fixes(), _FakeS3Client, make_fields(), make_track() (+13 more)

### Community 57 - "Community 57"
Cohesion: 0.09
Nodes (20): technique_member(), techniques_to_read(), TechniqueSpec, adeck_text(), adecks(), archive(), archive_text(), cases() (+12 more)

### Community 58 - "Community 58"
Cohesion: 0.11
Nodes (9): cycle_plan_out(), schedule(), ScheduleOut, CyclePlan, plan_day(), _schedule_stages(), ScheduledStage, Stage (+1 more)

### Community 59 - "Community 59"
Cohesion: 0.10
Nodes (19): _decode_one_sonde(), DropsondeFetchError, DropsondeProfile, fetch_and_parse_dropsonde_mission(), fetch_dropsonde_mission_tarball(), _ftp_connect(), list_dropsonde_missions(), _mask_missing() (+11 more)

### Community 60 - "Community 60"
Cohesion: 0.12
Nodes (20): _bytemap_path(), decode_ssmis_bytemap(), fetch_and_decode_ssmis_daily(), fetch_ssmis_daily_bytemap(), MicrowaveFetchError, RSSFtpCredentials, SSMISDaily, _make_bytemap() (+12 more)

### Community 61 - "Community 61"
Cohesion: 0.11
Nodes (24): expected_coordinates(), _decode(), files(), local(), _ohc(), _row_col(), server(), test_a_blank_file_is_rejected() (+16 more)

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
Cohesion: 0.10
Nodes (17): _adeck_position(), AdeckPoint, AtcfError, pair_by_valid_time(), parse_bdeck(), _parse_latlon(), parse_tcvitals(), TcVitalsError (+9 more)

### Community 65 - "Community 65"
Cohesion: 0.09
Nodes (15): _default_fetch_fn(), fetch(), era5_deps_available(), fetch_era5t_one(), fetch_grib2_messages(), gridded_deps_available(), open_era5(), open_era5_store() (+7 more)

### Community 66 - "Community 66"
Cohesion: 0.12
Nodes (17): disc_mean(), fetch_lead_flow(), group_by_time(), lead_flow(), LeadFlow, load_steering(), run_steering_cache(), fetch() (+9 more)

### Community 67 - "Community 67"
Cohesion: 0.11
Nodes (21): Hurdat2Error, _parse_data_row(), _parse_header(), parse_hurdat2(), parse_hurdat2_statuses(), _parse_latlon(), _storm_rows(), test_entry_count_mismatch_raises() (+13 more)

### Community 68 - "Community 68"
Cohesion: 0.08
Nodes (21): build_consistency_model(), consistency_fn(), __init__(), sample(), skip_coeffs(), distill_consistency_model(), step_loss(), _pseudo_huber() (+13 more)

### Community 69 - "Community 69"
Cohesion: 0.13
Nodes (20): AblationCell, AblationReport, build_samples(), run_capacity_ablation(), _cell(), make_track(), test_at_fraction_filters_and_sorts_by_hidden_dim(), test_build_samples_augmentation_multiplies_sample_count() (+12 more)

### Community 70 - "Community 70"
Cohesion: 0.06
Nodes (28): AsyncReturnType, Expand, ExtractGenericViewableContent, GenericItem, GenericSelectorOption, GenericSnippetProps, GenericViewableContent, InheritedSnippetProps (+20 more)

### Community 71 - "Community 71"
Cohesion: 0.06
Nodes (31): data, basins, stage_a, epochs, flavor, input_sources, label_source, learning_rate (+23 more)

### Community 72 - "Community 72"
Cohesion: 0.11
Nodes (21): make_fields(), make_track(), test_default_fetch_fn_wires_a_shared_session(), fake_fetch_gdas_grib2_fields(), fake_gdas_to_gridded_fields(), test_fetch_one_fetches_exactly_one_real_sample(), fake_gdas_to_gridded_fields(), test_gdas_archive_start_is_the_first_valid_time_with_an_atmos_f006() (+13 more)

### Community 73 - "Community 73"
Cohesion: 0.10
Nodes (16): initial_fix(), TrackQuality, extrapolate_fix(), _MemoryS3, s3(), test_an_archive_storm_says_its_fix_is_the_final_best_track(), test_late_vitals_on_a_live_storm_read_as_estimated(), test_missing_vitals_are_extrapolated_and_estimated() (+8 more)

### Community 74 - "Community 74"
Cohesion: 0.08
Nodes (30): better-auth@^1.7.7, @better-auth/api-key@^1.7.7, @types/node@^26.6.4, typescript@^5.9.3, wrangler@^4.147.0, better-auth, @better-auth/api-key, @types/node (+22 more)

### Community 75 - "Community 75"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, env, GH_TOKEN, GRAPHIFY_VERSION, permissions, runs-on (+22 more)

### Community 76 - "Community 76"
Cohesion: 0.11
Nodes (13): git_sha(), baseline_beaten(), build_run_tags(), _git_commit(), _gpu_type(), log_curriculum_stages(), log_stage_run(), stage_run_record() (+5 more)

### Community 77 - "Community 77"
Cohesion: 0.08
Nodes (15): _expected_meta(), test_a_failed_time_is_reported_and_the_others_still_written(), fetch(), test_a_lost_race_with_no_file_appearing_raises_the_write_error(), test_cache_round_trip_and_vector(), test_disc_mean_is_symmetric_for_a_field_linear_in_longitude(), test_features_advect_with_the_flow_plus_beta_drift(), test_features_raise_where_there_is_no_flow() (+7 more)

### Community 78 - "Community 78"
Cohesion: 0.07
Nodes (23): rehype-slug@^6.0.0, rehype-stringify@^10.0.1, remark-gfm@^4.0.1, remark-parse@^11.0.0, remark-rehype@^11.1.2, unified@^11.0.5, unist-util-visit@^5.1.0, CONSOLE_ROOT (+15 more)

### Community 79 - "Community 79"
Cohesion: 0.07
Nodes (29): WithElementRef, ButtonClickEvent, PrimitiveAnchorAttributes, PrimitiveButtonAttributes, PrimitiveCanvasAttributes, PrimitiveDivAttributes, PrimitiveElementAttributes, PrimitiveFigureAttributes (+21 more)

### Community 80 - "Community 80"
Cohesion: 0.09
Nodes (16): ArmResult, expand_patch_channels(), __init__(), _renamed(), run_steering_spike(), has_steering(), track_errors_nm(), _cache_steering() (+8 more)

### Community 81 - "Community 81"
Cohesion: 0.14
Nodes (12): _check_basin(), _created_date(), cycle_date(), decode_ohc(), fetch_ohc_file(), name_day_for_creation(), OhcFile, require_ohc_deps() (+4 more)

### Community 82 - "Community 82"
Cohesion: 0.09
Nodes (12): color_for(), god(), Module, WindGod, test_every_god_color_is_distinct(), test_experiment_name_handles_fusion_without_raising(), test_experiment_names_are_the_god_slugs(), test_lookup_by_slug_and_by_architecture_agree() (+4 more)

### Community 83 - "Community 83"
Cohesion: 0.13
Nodes (18): assert_no_leakage(), assign_splits(), _earliest_season(), _latest_season(), LeakageError, _seasons(), Split, _split_for_season() (+10 more)

### Community 84 - "Community 84"
Cohesion: 0.12
Nodes (16): _record_key(), record_operational_cycle(), _FakeClient, _fix(), _make_output(), _record(), test_audit_run_degrades_per_record_when_audit_one_raises(), flaky_audit_one() (+8 more)

### Community 85 - "Community 85"
Cohesion: 0.15
Nodes (14): build_real_deterministic_fn(), cache_current_fix(), _FakeS3Client, make_track(), _register_real_version(), _store(), test_build_real_deterministic_fn_combines_all_four_real_models(), test_build_real_deterministic_fn_raises_with_no_registered_models() (+6 more)

### Community 86 - "Community 86"
Cohesion: 0.10
Nodes (16): _FakeCycleOutput, _fresh_real_state(), _make_deterministic_forecast(), _make_storm_state(), _memory_store(), _MemoryS3Client, test_a_failed_cycle_write_never_fails_the_cycle(), test_an_unrestored_drift_window_is_never_written_back() (+8 more)

### Community 87 - "Community 87"
Cohesion: 0.07
Nodes (11): _FakeMlflowModelVersion, _mlflow_client_that_registers_and_transitions(), create_model_version(), test_mlflow_mirror_registers_model_then_version_with_a_real_source_uri(), create_model_version(), test_mlflow_mirror_skips_create_registered_model_if_it_already_exists(), create_model_version(), test_mlflow_transition_also_mirrors_the_archived_incumbent() (+3 more)

### Community 88 - "Community 88"
Cohesion: 0.12
Nodes (22): authHandle(), Auth, _authByRequest, buildAuth(), checkRegistrationOpen(), getAuth(), buildSessionHeaders(), extractBearerToken() (+14 more)

### Community 89 - "Community 89"
Cohesion: 0.07
Nodes (28): inputArgs, jobs, projectId, region, results, timeoutSeconds, assign, return (+20 more)

### Community 90 - "Community 90"
Cohesion: 0.11
Nodes (12): cache_nwp_lead_hours(), CacheLeadMismatch, _claim_cache_dir(), _default_fetch_fn(), fetch(), fetch_one(), run_fetch_cache(), FetchCacheReport (+4 more)

### Community 91 - "Community 91"
Cohesion: 0.14
Nodes (12): Fetcher, ingest_cycle_inputs(), ingest_one(), IngestionOutcome, IngestionRecord, LakeTier, LakeWriter, LocalLakeWriter (+4 more)

### Community 92 - "Community 92"
Cohesion: 0.10
Nodes (16): http_get(), OhcFetchError, OhcNotPublished, OhcUnavailable, Archive, test_a_cut_off_reply_is_a_fetch_failure(), test_a_cut_off_transfer_raises_rather_than_reading_an_older_file(), test_a_fetch_failure_that_is_not_a_404_is_not_stepped_over() (+8 more)

### Community 93 - "Community 93"
Cohesion: 0.10
Nodes (15): used_by(), test_cmd_sources_prints_who_uses_each_source(), _model_sources(), test_a_label_or_verification_source_is_never_a_model_input(), test_a_verification_source_not_read_yet_is_verification_and_nothing_else(), test_an_adapter_is_named_by_other_code_only_if_its_source_is_read(), test_each_curriculum_stage_lists_what_its_models_read(), test_every_fetch_adapter_is_classified() (+7 more)

### Community 94 - "Community 94"
Cohesion: 0.13
Nodes (8): FORM_FACTORS, freeCycleLabel(), label(), runFreshCycle(), signIn(), cases, @playwright/test@^1.63.0, @playwright/test

### Community 95 - "Community 95"
Cohesion: 0.13
Nodes (10): svelte-guard@^1.1.1, @sveltejs/kit@^2.70.3, DEFAULT_AFTER_LOGIN, loginHref(), safeNext(), requireSignIn(), requireSignInLoad(), guard() (+2 more)

### Community 96 - "Community 96"
Cohesion: 0.10
Nodes (12): deterministic(), cmd_cycle(), deterministic(), assert_operational_flavor(), climatological_ensemble(), CycleError, DeterministicForecast, fusion_weights() (+4 more)

### Community 97 - "Community 97"
Cohesion: 0.09
Nodes (12): calibration_out(), drift_report_out(), skew_report_out(), calibration(), drift(), drift_all(), skew(), DriftReportOut (+4 more)

### Community 98 - "Community 98"
Cohesion: 0.12
Nodes (13): ensemble(), build_real_ensemble_fn(), InferenceEnsembleError, _FakeS3Client, make_track(), _register(), _register_all_five_and_diffusion(), _store() (+5 more)

### Community 99 - "Community 99"
Cohesion: 0.11
Nodes (16): compute_environment_features(), deep_layer_shear(), generate_fields(), field(), paired_fields(), test_compute_environment_features_raises_when_storm_is_entirely_over_land(), test_compute_environment_features_succeeds_with_partial_land_coverage(), test_feature_vector_length_matches_the_names() (+8 more)

### Community 100 - "Community 100"
Cohesion: 0.13
Nodes (14): fetch_and_parse_ndbc(), fetch_ndbc_realtime2(), _get(), NdbcFetchError, NdbcObservation, parse_ndbc_realtime2(), test_a_row_with_the_wrong_column_count_is_skipped_not_fatal(), test_a_station_missing_wave_columns_still_parses() (+6 more)

### Community 101 - "Community 101"
Cohesion: 0.16
Nodes (13): cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_build_transformer_samples_empty_when_nothing_cached(), test_build_transformer_samples_rejects_a_cache_smaller_than_grid_size(), test_build_transformer_samples_trims_the_real_41x41_crop_to_grid_size() (+5 more)

### Community 102 - "Community 102"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GH_TOKEN, IMPORTED_FROM, SOURCE_SHA, jobs, publish (+16 more)

### Community 103 - "Community 103"
Cohesion: 0.15
Nodes (14): detect_feature_drift(), FeatureDrift, ValidationLossMonitor, reference(), test_a_recovery_resets_the_consecutive_count(), test_collapsed_variance_is_detected(), test_feature_count_mismatch_raises(), test_first_observation_only_sets_the_baseline() (+6 more)

### Community 104 - "Community 104"
Cohesion: 0.08
Nodes (3): client(), test_more_members_than_the_ensemble_runs_is_refused_not_silently_capped(), test_sources_say_who_uses_each_one()

### Community 105 - "Community 105"
Cohesion: 0.08
Nodes (8): DELETE, GET, PATCH, POST, PUT, { data }, prerender, ssr

### Community 106 - "Community 106"
Cohesion: 0.14
Nodes (10): fetch_gefs_ensemble_grib2_fields(), fetch_gefs_member_grib2_fields(), _gefs_member_url(), _parse_grib2_index(), test_control_member_zero_uses_gec00_not_gep00(), test_fetch_gefs_ensemble_reads_multiple_real_distinct_members(), test_fetch_gefs_member_reads_the_real_noaa_archive(), test_member_out_of_range_raises() (+2 more)

### Community 107 - "Community 107"
Cohesion: 0.15
Nodes (14): _all_tensors(), Architecture, _builder(), describe(), describe_cached(), _describe_cached(), hook(), _example_inputs() (+6 more)

### Community 108 - "Community 108"
Cohesion: 0.16
Nodes (13): _check_type(), config_dir(), ConfigError, fixed(), get(), get_list(), _load(), _names() (+5 more)

### Community 109 - "Community 109"
Cohesion: 0.11
Nodes (16): apply_cold_wake(), cold_wake_sst_depression_c(), emanuel_potential_intensity(), _saturation_vapor_pressure_hpa(), _specific_humidity_kg_kg(), test_apply_cold_wake_depresses_sst_and_ohc_without_touching_other_fields(), test_apply_cold_wake_is_a_noop_for_a_calm_storm(), test_cold_wake_depression_grows_with_wind_and_shrinks_with_translation_speed() (+8 more)

### Community 110 - "Community 110"
Cohesion: 0.14
Nodes (11): _files(), localize_cache(), LocalizeReport, _raise(), _cache(), test_a_directory_that_cant_be_listed_fails_the_copy(), test_a_missing_source_raises(), test_a_rerun_only_fills_gaps() (+3 more)

### Community 111 - "Community 111"
Cohesion: 0.10
Nodes (20): PROJECT_NUMBER, PROJECT_PAT, types, jobs, sync, name, on, issues (+12 more)

### Community 112 - "Community 112"
Cohesion: 0.15
Nodes (11): _cron_run_offset_minutes(), _leaves(), _load(), test_a_config_change_redeploys_the_api(), test_both_images_copy_the_configs(), test_every_config_key_is_read_by_the_code(), test_every_image_build_is_smoke_tested_before_it_ships(), test_the_console_uses_the_same_scheduled_run_offset() (+3 more)

### Community 113 - "Community 113"
Cohesion: 0.15
Nodes (12): fetch_current_storm_ids(), fetch_current_storms(), fetch_live_track(), _get(), test_fetch_current_storm_ids_parses_and_uppercases(), test_fetch_current_storm_ids_raises_on_malformed_json(), test_fetch_current_storm_ids_reads_the_real_nhc_index(), test_fetch_current_storms_pairs_ids_with_real_names() (+4 more)

### Community 114 - "Community 114"
Cohesion: 0.17
Nodes (10): DriftError, ReferenceDistribution, reference_from_json(), reference_to_json(), save_reference(), test_drift_report_detects_real_drift_once_enough_samples_are_collected(), test_drift_report_is_honest_zero_for_a_model_that_never_contributed(), test_reference_must_be_the_stage_b_distribution() (+2 more)

### Community 116 - "Community 116"
Cohesion: 0.15
Nodes (10): read_cached_official_errors(), OfficialErrorsError, parse_official_errors(), _signed(), test_a_cached_error_file_that_is_not_nhcs_is_named_with_the_way_out(), test_parse_official_errors_reads_columns_by_name_and_skips_missing_leads(), test_parse_official_errors_reads_the_stated_initial_position_domain(), test_parse_official_errors_rejects_a_file_without_the_column_header() (+2 more)

### Community 117 - "Community 117"
Cohesion: 0.19
Nodes (15): run_fetch_cache(), make_fields(), make_track(), test_build_fetch_tasks_covers_every_fix_across_tracks(), test_load_cached_fields_rejects_a_missing_file(), test_run_fetch_cache_actually_runs_fetches_concurrently(), slow_fetch(), test_run_fetch_cache_can_force_refetch_with_skip_existing_false() (+7 more)

### Community 118 - "Community 118"
Cohesion: 0.16
Nodes (14): ohc_global(), ohc_url(), _full_archive(), test_a_blank_run_longer_than_the_window_leaves_na_unavailable(), test_a_degraded_basin_flags_the_field(), test_a_missing_file_steps_back_one_creation_day(), test_an_unknown_basin_leaves_the_field_unknown_unless_another_is_degraded(), test_no_url_before_the_archive_or_for_another_basin() (+6 more)

### Community 119 - "Community 119"
Cohesion: 0.14
Nodes (9): load_reference(), test_drift_reference_fit_fits_and_persists_from_real_cached_fields(), _FakeClient, _make_reference(), test_durable_round_trip_via_a_shared_checkpoint_store(), test_json_round_trips_a_real_reference_exactly(), test_load_reference_degrades_honestly_when_the_store_is_unreachable(), test_load_reference_returns_none_when_nothing_was_ever_fit() (+1 more)

### Community 120 - "Community 120"
Cohesion: 0.12
Nodes (4): _Boto3Client, require_boto3(), _StorageClient, test_boto3_adapter_configures_the_client_for_the_given_endpoint()

### Community 121 - "Community 121"
Cohesion: 0.11
Nodes (7): client(), test_docs_route_is_unaffected(), test_sources_role_is_the_role_enum_in_the_openapi_schema(), test_sources_used_by_is_documented_in_the_openapi_schema(), test_theme_http_method_colors_are_distinct(), test_theme_never_uses_a_god_color(), _walk()

### Community 122 - "Community 122"
Cohesion: 0.11
Nodes (6): _FakeS3Config, test_checkpoint_store_push_mirrors_registry_json_after_every_save(), test_pull_failure_degrades_to_an_empty_registry(), test_pull_from_checkpoint_store_hydrates_a_missing_local_registry(), test_pull_is_a_noop_when_the_key_does_not_exist_remotely_yet(), test_pull_reconciles_with_durable_storage_even_when_local_already_exists()

### Community 123 - "Community 123"
Cohesion: 0.17
Nodes (7): mlflow_client_from_env(), test_an_unreachable_server_is_skipped_fast(), test_builds_a_real_client_when_tracking_uri_is_set(), test_fail_fast_settings_never_override_explicit_ones(), test_mlflow_client_from_env_can_actually_reach_the_configured_server(), test_returns_none_when_tracking_uri_is_unset(), test_returns_none_without_mlflow_installed()

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
Cohesion: 0.12
Nodes (16): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+8 more)

### Community 128 - "Community 128"
Cohesion: 0.12
Nodes (16): compilerOptions, allowJs, allowSyntheticDefaultImports, checkJs, forceConsistentCasingInFileNames, isolatedModules, lib, module (+8 more)

### Community 129 - "Community 129"
Cohesion: 0.12
Nodes (16): permissions, runs-on, steps, jobs, copilot-setup-steps, name, on, pull_request (+8 more)

### Community 130 - "Community 130"
Cohesion: 0.15
Nodes (9): config_copy(), edit(), _image_layout(), _run(), test_a_missing_config_dir_is_refused(), test_an_image_without_configs_fails_at_import_and_says_why(), test_an_invalid_config_is_refused_with_a_clear_message(), test_edited_values_take_effect_at_runtime() (+1 more)

### Community 131 - "Community 131"
Cohesion: 0.18
Nodes (7): assert_flavor(), FeatureSet, FlavorMismatchError, Normalizer, test_flavor_guard_rejects_a_pretrain_feature_on_the_operational_path(), test_normalizer_refuses_to_fit_across_flavors(), test_normalizer_rejects_the_wrong_flavor_at_apply_time()

### Community 132 - "Community 132"
Cohesion: 0.15
Nodes (8): BasinChoice, creation_day(), test_a_cycle_reads_the_file_made_two_days_before(), test_a_real_file_from_each_chain(), test_name_day_for_creation_inverts_creation_day_and_has_a_gap_at_the_switch(), test_the_flag_is_relative_to_the_baseline(), test_the_flag_on_real_files(), test_v1r1_files_are_made_the_day_after_their_name()

### Community 133 - "Community 133"
Cohesion: 0.17
Nodes (9): _bilinear(), _lattice_index(), ohc_at(), OhcField, place(), test_bilinear_between_nodes(), test_bilinear_is_exact_at_a_node_on_every_source(), test_bilinear_needs_all_four_corners() (+1 more)

### Community 134 - "Community 134"
Cohesion: 0.26
Nodes (12): storm_relative_sequence(), make_fix(), test_displacement_direction_matches_bearing(), test_displacement_magnitude_matches_haversine_distance(), test_displacement_nm_matches_storm_relative_sequence(), test_eastward_motion_is_positive_dx_with_a_small_northward_component(), test_mixed_storm_ids_raises(), test_northward_motion_is_positive_dy_and_zero_dx() (+4 more)

### Community 135 - "Community 135"
Cohesion: 0.26
Nodes (9): NoiseSensitivityReport, _result(), test_is_load_bearing_above_threshold(), test_is_not_load_bearing_below_threshold(), test_relative_change_is_zero_when_losses_match(), test_relative_change_rejects_nonpositive_default_loss(), test_relative_change_sign_matches_direction_of_the_move(), test_run_noise_sensitivity_covers_both_candidates_on_a_small_synthetic_archive() (+1 more)

### Community 136 - "Community 136"
Cohesion: 0.15
Nodes (9): _called(), _calls(), _function(), _modules(), _parameters(), _parse(), test_a_fetch_only_importer_names_the_adapter_it_is_listed_for(), test_model_inputs_match_what_each_runner_and_live_builder_takes() (+1 more)

### Community 137 - "Community 137"
Cohesion: 0.14
Nodes (10): {
    class: klass,
    fullPage,
    children,
    size = 60,
    message = "Please wait...",
    messageClass,
    carriageWidth = "0.08em",
    loading = false,
    iconComponent: IconComponent,
    ...rest
  }, IconConfig, iconDefinition, isBusy, messageLength, routeLoading, WaiterProps, setWaiterLoading() (+2 more)

### Community 138 - "Community 138"
Cohesion: 0.12
Nodes (16): with, build-args, cache-from, cache-to, context, file, load, password (+8 more)

### Community 139 - "Community 139"
Cohesion: 0.12
Nodes (15): jobs, lint-and-validate, name, permissions, runs-on, steps, name, on (+7 more)

### Community 140 - "Community 140"
Cohesion: 0.17
Nodes (8): al_2021_2022(), compare(), open_ocean(), parse_ships(), sample_days(), ShipsCase, test_sohc_equals_bilinear_ohc_on_the_file_named_for_the_day_before(), test_compare_refuses_arms_on_different_windows_and_pairs_the_rest()

### Community 141 - "Community 141"
Cohesion: 0.13
Nodes (15): scripts, build, cf:deploy, check, check:errors, check:warnings, check:watch, dev (+7 more)

### Community 142 - "Community 142"
Cohesion: 0.19
Nodes (12): loading, onInput(), open, query, results, bodyById, buildIndex(), excerptAround() (+4 more)

### Community 143 - "Community 143"
Cohesion: 0.13
Nodes (15): env, environment, if, name, needs, permissions, runs-on, timeout-minutes (+7 more)

### Community 144 - "Community 144"
Cohesion: 0.13
Nodes (7): area_mean(), integrated_vapor_transport(), relative_vorticity_850(), steering_flow(), test_area_mean_ignores_nan_pixels_from_partial_land_coverage(), test_area_mean_matches_plain_mean_when_nothing_is_nan(), test_area_mean_returns_nan_when_the_whole_box_is_land()

### Community 145 - "Community 145"
Cohesion: 0.16
Nodes (7): _declared_length(), detect_format(), _grid_values(), OhcRejected, _read_checked(), StepBack, test_format_is_detected_from_the_first_bytes()

### Community 146 - "Community 146"
Cohesion: 0.16
Nodes (10): get(), Role, test_a_model_input_is_never_a_labels_only_source(), test_era5_is_pretrain_only(), test_era5_latency_is_days_not_hours(), test_every_model_reads_a_source_it_can_be_served_from(), test_final_besttrack_is_labels_only(), test_gdas_latency_exceeds_the_v2_forty_five_minute_assumption() (+2 more)

### Community 147 - "Community 147"
Cohesion: 0.24
Nodes (11): validate(), make_tags(), test_malformed_dvc_version_is_rejected(), test_malformed_git_commit_is_rejected(), test_malformed_nwp_cycle_lag_is_rejected(), test_none_values_are_dropped_from_the_dict(), test_pretrain_flavor_tags_are_not_operational(), test_v2_1_adds_input_flavor_and_nwp_cycle_lag() (+3 more)

### Community 148 - "Community 148"
Cohesion: 0.26
Nodes (8): _make_samples(), test_a_longer_epoch_budget_never_returns_a_worse_val_loss(), test_early_stopping_halts_before_the_epoch_cap_on_a_real_overfitting_run(), test_run_diffusion_curriculum_uploads_a_checkpoint_and_registers_stage_b(), test_train_diffusion_stage_accepts_dropout_and_weight_decay(), test_train_diffusion_stage_produces_val_metrics_and_artifacts(), test_train_diffusion_stage_records_a_real_dropout_value_in_arch_params(), test_train_diffusion_stage_rejects_empty_samples()

### Community 149 - "Community 149"
Cohesion: 0.14
Nodes (8): API, DEVELOP, PHONE, SourceRow, SOURCES, SOURCES_BEFORE_USED_BY, SOURCES_REWIRED, path()

### Community 150 - "Community 150"
Cohesion: 0.14
Nodes (13): compilerOptions, allowJs, checkJs, esModuleInterop, forceConsistentCasingInFileNames, moduleResolution, resolveJsonModule, rewriteRelativeImportExtensions (+5 more)

### Community 151 - "Community 151"
Cohesion: 0.14
Nodes (13): images, options, diskSizeGb, machineType, steps, args, entrypoint, env (+5 more)

### Community 152 - "Community 152"
Cohesion: 0.14
Nodes (14): default, description, type, default, description, type, api, console (+6 more)

### Community 153 - "Community 153"
Cohesion: 0.19
Nodes (8): fetch_live_tracks(), fetch_one(), LiveAtcfError, test_fetch_live_tracks_fetches_storms_concurrently_and_keeps_index_order(), test_fetch_live_tracks_returns_empty_when_index_unreachable(), raise_error(), test_fetch_live_tracks_skips_a_storm_whose_own_fetch_fails(), fake_fetch_live_track()

### Community 154 - "Community 154"
Cohesion: 0.16
Nodes (6): HomogeneousRow, BaselineReport, _fmt(), format_report(), _json_safe(), test_the_report_serialises_as_strict_json_and_prints_a_table()

### Community 155 - "Community 155"
Cohesion: 0.23
Nodes (6): FakeClient, test_download_rejects_a_uri_from_a_different_bucket(), test_download_round_trips_the_uploaded_bytes(), test_list_filters_by_prefix(), test_upload_missing_file_raises(), test_upload_returns_an_s3_uri_and_stores_the_bytes()

### Community 156 - "Community 156"
Cohesion: 0.16
Nodes (7): extract_joint_latents(), extract_validation_latents(), JointLatentBundle, _require_group1(), test_the_latents_extraction_runs_the_models_on_joint_stage_windows_own_windows(), _window_key(), test_extract_joint_latents_rejects_missing_group1_model()

### Community 157 - "Community 157"
Cohesion: 0.17
Nodes (12): IdTokenClaims, JwtClaims, OidcAddressClaim, OidcStandardClaims, UserProfile, Mandatory, RFC-3966, RFC-4627 (+4 more)

### Community 158 - "Community 158"
Cohesion: 0.18
Nodes (7): client(), test_a_registered_versions_arch_params_are_used(), test_a_version_without_arch_params_is_described_from_defaults(), test_a_versions_arch_params_change_what_is_described(), test_every_model_runs_its_example_input_and_reports_its_layers(), test_the_gnn_is_fed_the_real_lattice(), test_unknown_models_and_versions_are_404()

### Community 159 - "Community 159"
Cohesion: 0.15
Nodes (12): name, runs-on, timeout-minutes, concurrency, cancel-in-progress, group, jobs, build (+4 more)

### Community 160 - "Community 160"
Cohesion: 0.22
Nodes (8): get_cycle(), get_storm(), list_storms(), _served_basins(), _storm_summary(), FixOut, StormDetail, StormSummary

### Community 161 - "Community 161"
Cohesion: 0.27
Nodes (6): train_fusion_stage(), _make_samples(), test_run_fusion_curriculum_uploads_a_checkpoint_and_registers_stage_b(), test_train_fusion_stage_reduces_loss_and_produces_val_metrics(), test_train_fusion_stage_rejects_a_val_set_built_with_a_different_model_count(), test_train_fusion_stage_rejects_empty_samples()

### Community 162 - "Community 162"
Cohesion: 0.23
Nodes (11): max, target, budgets, reduced, standard, max, target, assembly (+3 more)

### Community 163 - "Community 163"
Cohesion: 0.17
Nodes (4): local, notes, problems, remote

### Community 164 - "Community 164"
Cohesion: 0.20
Nodes (4): build_info(), _build_info_path(), config_digest(), summary()

### Community 165 - "Community 165"
Cohesion: 0.17
Nodes (11): concurrency, cancel-in-progress, group, jobs, test-api, name, if, name (+3 more)

### Community 166 - "Community 166"
Cohesion: 0.17
Nodes (12): with, cache, cache-dependency-path, enable-cache, fetch-depth, if-no-files-found, include-hidden-files, name (+4 more)

### Community 167 - "Community 167"
Cohesion: 0.23
Nodes (4): _download(), fetch_oisst_sst(), require_sst_deps(), SstFetchError

### Community 168 - "Community 168"
Cohesion: 0.23
Nodes (8): generate_season(), test_archive_spans_the_requested_seasons(), test_fixes_are_six_hourly_and_synoptic(), test_generated_tracks_are_final_quality(), test_generation_is_reproducible(), test_intensity_rises_and_falls(), test_storm_ids_are_unique_within_the_archive(), test_storms_fall_within_the_requested_season()

### Community 170 - "Community 170"
Cohesion: 0.18
Nodes (11): cycle, advisory_margin_minutes, advisory_offset_minutes, allow_estimated_vitals, allow_load_shedding, max_nwp_lag_hours, nominal_vitals_offset_minutes, nwp_lag_hours (+3 more)

### Community 171 - "Community 171"
Cohesion: 0.27
Nodes (6): sst_at(), _small_grid(), test_fetch_oisst_sst_reads_real_recent_data(), test_sst_at_finds_the_nearest_cell(), test_sst_at_normalises_negative_longitude_to_0_360(), test_sst_at_returns_nan_over_a_real_missing_cell()

### Community 172 - "Community 172"
Cohesion: 0.22
Nodes (6): first_record_of_year(), ships_al_url(), _ships_get(), ships_record_year(), ships_size(), ships_window()

### Community 173 - "Community 173"
Cohesion: 0.20
Nodes (10): limit, lower_is_better, limit, lower_is_better, thresholds, intensity_error_48h_kt, intensity_error_72h_kt, track_error_72h_nm (+2 more)

### Community 174 - "Community 174"
Cohesion: 0.20
Nodes (10): steps, EXPECT_GIT_SHA, GCP_CI_SERVICE_ACCOUNT, GCP_WIF_PROVIDER, env, id, if, name (+2 more)

### Community 175 - "Community 175"
Cohesion: 0.20
Nodes (10): name, outputs, runs-on, timeout-minutes, changes, deploy_api, deploy_console, plan (+2 more)

### Community 176 - "Community 176"
Cohesion: 0.40
Nodes (10): steps, steps, id, if, name, run, uses, working-directory (+2 more)

### Community 177 - "Community 177"
Cohesion: 0.27
Nodes (4): ChecksumCheck, FetchResult, NonEmptyCheck, QCFinding

### Community 178 - "Community 178"
Cohesion: 0.31
Nodes (5): basin_one_hot(), with_basin_channels(), with_basin_columns(), with_basin_vector(), test_the_basin_input_builders_add_one_column_or_channel_per_basin()

### Community 179 - "Community 179"
Cohesion: 0.24
Nodes (5): _register_group1_versions(), test_a_desynced_derived_champion_is_not_a_bar_a_servable_candidate_must_clear(), test_a_servable_derived_champion_is_still_a_real_bar(), test_seed_from_champions_loads_each_champion_not_the_latest(), test_seed_from_champions_refuses_an_incomplete_champion_set()

### Community 180 - "Community 180"
Cohesion: 0.31
Nodes (4): _attributes(), _imported(), _names_adapter(), _string_literals()

### Community 181 - "Community 181"
Cohesion: 0.22
Nodes (9): run, test-console, working-directory, defaults, if, name, needs, runs-on (+1 more)

### Community 182 - "Community 182"
Cohesion: 0.22
Nodes (9): BASE_SHA, BEFORE_SHA, DISPATCH_API, DISPATCH_CONSOLE, EVENT, EXPECT_GIT_SHA, HEAD_SHA, REF (+1 more)

### Community 183 - "Community 183"
Cohesion: 0.25
Nodes (6): source_out(), SourceOut, DataSource, operational_sources(), pretrain_only_sources(), test_operational_sources_pass_the_guard()

### Community 184 - "Community 184"
Cohesion: 0.22
Nodes (3): _MemoryS3, s3(), store()

### Community 185 - "Community 185"
Cohesion: 0.25
Nodes (8): 12, 120, 24, 36, 48, 72, 96, climatological_cone_nm

### Community 186 - "Community 186"
Cohesion: 0.25
Nodes (8): CP, 12, 120, 24, 36, 48, 72, 96

### Community 187 - "Community 187"
Cohesion: 0.25
Nodes (8): EP, 12, 120, 24, 36, 48, 72, 96

### Community 188 - "Community 188"
Cohesion: 0.25
Nodes (7): calibration_audit, cone_nominal_rate, intensity_nominal_rate, min_cases, verdict_margin, test_set_budget, max_evaluations_per_season

### Community 189 - "Community 189"
Cohesion: 0.25
Nodes (8): drift, min_samples, reference_flavor, shift_sigma, validation_loss, variance_ratio_limit, consecutive_required, threshold_fraction

### Community 190 - "Community 190"
Cohesion: 0.25
Nodes (8): promotion, flavor, new_basin_tolerance, primary_metric, reference_basin, require_manual_gate, split, basins()

### Community 191 - "Community 191"
Cohesion: 0.32
Nodes (5): assert_not_operational(), _operational_substitute(), OperationalUseError, test_reading_era5_in_the_inference_path_is_refused(), test_reading_final_besttrack_in_the_inference_path_is_refused()

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

### Community 198 - "Community 198"
Cohesion: 0.29
Nodes (3): archive_atcf(), calibration_audit(), skew_audit()

### Community 200 - "Community 200"
Cohesion: 0.33
Nodes (4): DiffusionArtifacts, _standardize(), _standardize_y(), train_diffusion_stage()

### Community 203 - "Community 203"
Cohesion: 0.33
Nodes (6): ensemble, climatological_cone_nm_by_basin, members, min_members_for_ensemble_cone, reduced_members, underdispersion_fraction

### Community 204 - "Community 204"
Cohesion: 0.33
Nodes (6): triggers, data_volume_threshold, nightly_latent_hour_utc, preseason_date, scheduled_monthly_day, suppress_nightly_latent_during_active_storms

### Community 205 - "Community 205"
Cohesion: 0.33
Nodes (4): {
		flagged,
		probability,
		lo = null,
		hi = null,
		uncertain = null,
		ensembleSize = null,
	}, membersNote, Props, range

### Community 206 - "Community 206"
Cohesion: 0.33
Nodes (6): update_job, workflow_dispatch, default, description, type, inputs

### Community 207 - "Community 207"
Cohesion: 0.33
Nodes (6): on, pull_request, push, paths, branches, paths

### Community 208 - "Community 208"
Cohesion: 0.33
Nodes (3): compare_potential_intensity_estimates(), potential_intensity(), test_compare_potential_intensity_estimates_documents_the_closed_form_running_hot()

### Community 209 - "Community 209"
Cohesion: 0.33
Nodes (3): inner_core_moisture(), _radial_gradient_fields(), test_inner_core_moisture_reflects_the_core_not_the_environment()

### Community 210 - "Community 210"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 211 - "Community 211"
Cohesion: 0.40
Nodes (3): WORLD_GEOJSON, WorldData, WorldFeatureProperties

### Community 212 - "Community 212"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 218 - "Community 218"
Cohesion: 0.67
Nodes (4): max, target, diffusion, diffusion

### Community 219 - "Community 219"
Cohesion: 0.67
Nodes (4): max, target, fusion, fusion

### Community 220 - "Community 220"
Cohesion: 0.67
Nodes (4): max, target, postprocess, postprocess

### Community 221 - "Community 221"
Cohesion: 0.67
Nodes (4): max, target, preprocess, preprocess

### Community 222 - "Community 222"
Cohesion: 0.83
Nodes (3): graphify(), normalise_graph(), build-graph.sh script

### Community 223 - "Community 223"
Cohesion: 0.50
Nodes (3): uvx, graphify, graphify-mcp

### Community 227 - "Community 227"
Cohesion: 0.67
Nodes (3): limit, lower_is_better, nhc_consensus_beat_rate_48h

### Community 228 - "Community 228"
Cohesion: 0.67
Nodes (3): track_error_120h_nm, limit, lower_is_better

### Community 229 - "Community 229"
Cohesion: 0.67
Nodes (3): track_error_48h_nm, limit, lower_is_better

## Knowledge Gaps
- **13 isolated node(s):** `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627`, `RFC-5322`, `RFC-5646` (+8 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2786 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Flavor` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 131`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 11`, `Community 14`, `Community 146`, `Community 147`, `Community 148`, `Community 21`, `Community 25`, `Community 29`, `Community 158`, `Community 31`, `Community 32`, `Community 161`, `Community 34`, `Community 35`, `Community 37`, `Community 40`, `Community 41`, `Community 45`, `Community 46`, `Community 49`, `Community 50`, `Community 179`, `Community 52`, `Community 56`, `Community 65`, `Community 199`, `Community 200`, `Community 73`, `Community 72`, `Community 76`, `Community 80`, `Community 209`, `Community 82`, `Community 208`, `Community 85`, `Community 87`, `Community 216`, `Community 217`, `Community 96`, `Community 97`, `Community 98`, `Community 99`, `Community 101`, `Community 103`, `Community 108`, `Community 236`, `Community 109`, `Community 114`, `Community 115`, `Community 117`, `Community 119`, `Community 122`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 248 inferred relationships involving `Flavor` (e.g. with `DemoState` and `drift()`) actually correct?**
  _`Flavor` has 248 INFERRED edges - model-reasoned connections that need verification._
- **What connects `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627` to the rest of the system?**
  _13 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.04002026342451875 - nodes in this community are weakly interconnected._
- **Why does `Track` connect `Community 6` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 135`, `Community 11`, `Community 13`, `Community 14`, `Community 18`, `Community 21`, `Community 153`, `Community 156`, `Community 29`, `Community 31`, `Community 32`, `Community 34`, `Community 35`, `Community 37`, `Community 168`, `Community 43`, `Community 45`, `Community 47`, `Community 48`, `Community 56`, `Community 64`, `Community 65`, `Community 67`, `Community 69`, `Community 72`, `Community 73`, `Community 80`, `Community 83`, `Community 84`, `Community 85`, `Community 214`, `Community 86`, `Community 90`, `Community 96`, `Community 98`, `Community 101`, `Community 236`, `Community 113`, `Community 115`, `Community 117`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 135 inferred relationships involving `Track` (e.g. with `save_cycle_inputs()` and `StormState`) actually correct?**
  _`Track` has 135 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.026658203744842908 - nodes in this community are weakly interconnected._