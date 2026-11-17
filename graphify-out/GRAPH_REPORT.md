# Graph Report - anemoi  (2026-11-17)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 6921 nodes · 17814 edges · 250 communities (226 shown, 24 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 2633 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `543b6e85`
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
- Community 243
- Community 244
- Community 245
- Community 246
- Community 247
- Community 248
- Community 249

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
- `test_run_request_refuses_an_unknown_source()` --uses--> `RunRequest`  [INFERRED]
  tests/test_cycle_policy.py → src/anemoi/api/cycle_policy.py
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

## Communities (250 total, 24 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (72): Flavor, require_meta(), steering_meta(), assert_deployable(), Curriculum, CurriculumError, CurriculumRun, stage_a() (+64 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (65): basins_of(), select_basins(), assert_input_safe(), augment_track(), emulate_working_fix(), emulate_working_track(), Fix, recalibrate_from_pairs() (+57 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (51): DeterministicForecast, fusion_weights(), build_kwargs(), basin_inputs(), latent_signature(), _builder(), _build_live_context(), _build_live_x() (+43 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (45): StageSpec, build_cnn_samples(), CnnStageSamples, _sanitized_channel_stack(), _standardize_cnn_x(), _standardize_y(), train_cnn_stage(), train_cnn_stage_streaming() (+37 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (91): ApiError, apiFetch(), getActivePin(), getArchitecture(), getCalibration(), getCycle(), getDrift(), getDriftAll() (+83 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (51): Adeck, storm_basin(), displacement_nm(), haversine_nm(), HomogeneousRow, _aligned(), assemble_validation_forecasts(), scored() (+43 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (55): extra_input_conv(), __init__(), extra_input_linear(), __init__(), ModelSpec, require_torch(), torch_available(), build_diffusion() (+47 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (52): run_fetch_cache(), GriddedFields, inner_core_moisture(), integrated_vapor_transport(), relative_vorticity_850(), steering_flow(), archive_key(), cache_path() (+44 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (45): cmd_ablation(), cmd_adeck_fetch(), cmd_atcf_archive(), cmd_baseline_backtest(), cmd_cache_localize(), cmd_consistency_distill(), cmd_cycle(), deterministic() (+37 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (51): @lucide/svelte@^1.71.0, svelte-sonner@^1.2.3, sveltekit-superforms@^2.31.0, authClient, { form }, Props, { form }, Props (+43 more)

### Community 10 - "Community 10"
Cohesion: 0.06
Nodes (42): list_cycle_labels(), open_era5_store(), audit_one(), audit_run(), _AuditPlan, _era5t_fetcher(), fetch(), _fix_from_dict() (+34 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (44): disc_mean(), lead_flow(), LeadFlow, load_steering(), save_steering(), steering_features(), steering_meta_digest(), build_live_cnn_x() (+36 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (34): WorkingTrackNoise, assert_no_leakage(), assign_splits(), _earliest_season(), filter_tracks(), _latest_season(), LeakageError, season_boundaries() (+26 more)

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (37): experiment_name(), cmd_train(), latest_final_season(), arch_params_tag(), baseline_beaten(), basin_input_tags(), build_run_tags(), candidate_tags() (+29 more)

### Community 14 - "Community 14"
Cohesion: 0.05
Nodes (33): absolute_pairs(), basin_key(), basin_value(), is_basin_key(), key_basin(), per_basin_scores(), sample_counts(), scored_basins() (+25 more)

### Community 15 - "Community 15"
Cohesion: 0.04
Nodes (56): at(), calendarValue, hour, hourAllowed, inRange(), maxValue, minValue, onDateChange() (+48 more)

### Community 16 - "Community 16"
Cohesion: 0.05
Nodes (32): sanitize_field_pixels(), basin_one_hot(), with_basin_channels(), with_basin_columns(), with_basin_vector(), cnn_input(), batch_graph(), build_gnn_samples() (+24 more)

### Community 17 - "Community 17"
Cohesion: 0.04
Nodes (40): svelte@^5.57.1, Props, Section, SectionPage, { sections }, height, motionClass, Props (+32 more)

### Community 18 - "Community 18"
Cohesion: 0.05
Nodes (9): cycle_payload_out(), cycle_result_out(), provenance_out(), RealState, deterministic(), ensemble(), live_fields(), RealStormState (+1 more)

### Community 19 - "Community 19"
Cohesion: 0.05
Nodes (31): _sample_config(), compile_model(), get_device(), _displacement_to_absolute(), _empty_samples(), _extract_for_tracks(), extract_joint_latents(), extract_validation_latents() (+23 more)

### Community 20 - "Community 20"
Cohesion: 0.05
Nodes (34): _crop_variable(), fetch_real_satellite_crop(), _find_real_scan(), GoesFetchError, _lazy_open(), _list_scan_keys(), _nearest_scan_key(), _parse_scan_start() (+26 more)

### Community 21 - "Community 21"
Cohesion: 0.05
Nodes (39): _baseline_inputs(), _empty_report(), _fake_checkpoint_store(), _hurdat2_storm(), make_args(), _retrain_check_args(), _spy_assign_splits(), test_adeck_fetch_reads_the_split_and_keeps_cached_files() (+31 more)

### Community 22 - "Community 22"
Cohesion: 0.06
Nodes (35): ExecutionMode, build_derived_schedule(), _latent_task(), ResourceProfile, Task, _train_task(), Wave, fake_load_run_artifacts() (+27 more)

### Community 23 - "Community 23"
Cohesion: 0.06
Nodes (48): AppAuth, buildAuth(), getAuth(), verifyApiKey(), CYCLE_STEP, cycleInstanceId(), CycleParams, CycleWorkflow (+40 more)

### Community 24 - "Community 24"
Cohesion: 0.05
Nodes (16): DemoState, StormState, initial_fix(), _synthetic_fallback_deterministic(), climatological_ensemble(), Stage, SkewReport, cycle_label() (+8 more)

### Community 25 - "Community 25"
Cohesion: 0.06
Nodes (29): build_pinn_samples(), _candidate_and_true_absolute(), _disp_to_abs_batch(), _freeze_pinn_trunk(), PinnStageSamples, _PinnWindowDataset, _train_candidate_lstm_streaming(), build_x() (+21 more)

### Community 26 - "Community 26"
Cohesion: 0.05
Nodes (45): layerchart@^2.5.1, FixOut, IntensityPercentiles, TrackPointOut, colorFor(), god(), bounds, colors (+37 more)

### Community 27 - "Community 27"
Cohesion: 0.06
Nodes (33): svelte-guard@^1.1.1, authHandle(), guards, handle, DEFAULT_AFTER_LOGIN, loginHref(), safeNext(), Auth (+25 more)

### Community 28 - "Community 28"
Cohesion: 0.07
Nodes (30): invalidated_by(), evaluate_all(), expand_jobs(), nightly_latent(), on_data_volume(), on_drift(), on_latent_desync(), on_skew() (+22 more)

### Community 29 - "Community 29"
Cohesion: 0.06
Nodes (32): aggregate_by_storm(), beat_rate(), diebold_mariano(), ForecastPoint, LeadTimeStats, _normal_cdf(), to_metric_dict(), VerificationPair (+24 more)

### Community 30 - "Community 30"
Cohesion: 0.08
Nodes (35): basin_tags(), evaluate_promotion(), by_basin(), complete_run(), metric_set(), test_a_basin_is_verified_when_the_model_beats_persistence_there(), test_a_basin_validated_but_never_trained_on_is_not_verified(), test_a_candidate_that_loses_a_verified_basin_is_refused() (+27 more)

### Community 31 - "Community 31"
Cohesion: 0.05
Nodes (36): ModelCatalog, BY_ARCHITECTURE, BY_SLUG, FUNCTIONAL_COLORS, FUSION_COLOR, GOD_ORDER, GODS, Module (+28 more)

### Community 32 - "Community 32"
Cohesion: 0.06
Nodes (42): SourceOut, byUse(), hasUnknownEntry(), MODEL_NAMES, MODELS, ORDER, readersOf(), SOURCE_NAMES (+34 more)

### Community 33 - "Community 33"
Cohesion: 0.06
Nodes (25): technique_member(), techniques_to_read(), TechniqueSpec, adeck_text(), adecks(), archive(), archive_text(), cases() (+17 more)

### Community 34 - "Community 34"
Cohesion: 0.11
Nodes (29): assert_operational_flavor(), CycleError, run_cycle(), deterministic_fn(), good_ensemble(), make_fix(), test_a_pacific_climatological_ensemble_is_drawn_from_pacific_radii(), test_absent_opportunistic_feeds_do_not_flag_the_cycle() (+21 more)

### Community 35 - "Community 35"
Cohesion: 0.07
Nodes (24): fetch_and_parse_ndbc(), fetch_ndbc_realtime2(), _get(), NdbcFetchError, NdbcObservation, parse_ndbc_realtime2(), _download(), fetch_oisst_sst() (+16 more)

### Community 36 - "Community 36"
Cohesion: 0.08
Nodes (28): archive_atcf(), ArchiveReport, currentstorms_key(), _digest(), _get_text(), _load_recent(), _put_bytes(), snapshot_key() (+20 more)

### Community 37 - "Community 37"
Cohesion: 0.07
Nodes (20): AvailabilityOracle, CycleInputs, earliest_ready_time(), InputStatus, resolve_cycle_inputs(), _valid_time_for(), NWPCycleSelection, test_all_nwp_missing_marks_the_required_input_unavailable() (+12 more)

### Community 38 - "Community 38"
Cohesion: 0.11
Nodes (24): case_errors(), compared_members(), homogeneous_mask(), _limiting(), _mean(), Member, MemberScore, _paired() (+16 more)

### Community 39 - "Community 39"
Cohesion: 0.09
Nodes (27): build_schedule(), Mode, OrchestrationResult, run_schedule(), RunOutcome, Schedule, validate_schedule(), failing_runner() (+19 more)

### Community 40 - "Community 40"
Cohesion: 0.07
Nodes (20): Hurdat2Error, _parse_data_row(), _parse_header(), _parse_latlon(), _storm_rows(), generate_track(), make_storm_spec(), StormSpec (+12 more)

### Community 41 - "Community 41"
Cohesion: 0.08
Nodes (21): config_copy(), edit(), _cron_run_offset_minutes(), _image_layout(), _leaves(), _load(), _run(), test_a_config_change_redeploys_the_api() (+13 more)

### Community 42 - "Community 42"
Cohesion: 0.09
Nodes (23): audit_due(), audit_storm(), _audited_key(), calibrate_products(), CalibrationSample, LeadProductCalibration, _load_audited(), load_calibration_samples() (+15 more)

### Community 43 - "Community 43"
Cohesion: 0.07
Nodes (23): LeadCalibration, build_consistency_model(), consistency_fn(), __init__(), sample(), skip_coeffs(), ConfigResult, distill_consistency_model() (+15 more)

### Community 44 - "Community 44"
Cohesion: 0.06
Nodes (22): client(), _get_real_state(), hurdat2_file(), _stage_group1_and_derived(), test_a_stale_refresh_in_flight_serves_known_storms_without_waiting(), test_calibration_report_is_honest_empty_with_no_samples(), test_calibration_report_reflects_persisted_samples(), test_concurrent_requests_share_one_live_feed_fetch() (+14 more)

### Community 45 - "Community 45"
Cohesion: 0.08
Nodes (28): cycle_products_out(), ActivePin, ArchitectureOut, ConeSegmentOut, CyclePayload, CyclePlanOut, CycleProducts, DegradedFlagRef (+20 more)

### Community 46 - "Community 46"
Cohesion: 0.09
Nodes (24): RegistryError, full_set(), register_group1(), _stage_all(), test_checkpoint_uri_defaults_to_none_when_not_given(), test_checkpoint_uri_persists_on_the_version_itself(), test_derived_models_require_a_latent_signature(), test_desynced_derived_models_detects_a_real_champion_change() (+16 more)

### Community 47 - "Community 47"
Cohesion: 0.08
Nodes (22): format_report(), recommend_extra_conditioning(), run_spread_backtest(), SpreadBacktestError, SpreadBacktestReport, _fake_val(), _FakeS3Client, _lc() (+14 more)

### Community 48 - "Community 48"
Cohesion: 0.07
Nodes (16): App, Locals, Platform, clearPreferenceStorage(), consent, CONSENT_KEY, ConsentCategory, ConsentChoice (+8 more)

### Community 49 - "Community 49"
Cohesion: 0.09
Nodes (22): build_fetch_tasks(), run_fetch_cache(), _work(), save_cached_fields(), sync_cache_to_archive(), SyncReport, test_build_fetch_tasks_covers_every_fix_across_tracks(), FakeArchive (+14 more)

### Community 50 - "Community 50"
Cohesion: 0.07
Nodes (39): dependencies, arktype@^2.2.7, better-auth@^1.7.7, @better-auth/passkey@^1.7.7, bits-ui@^2.20.6, clsx@^2.1.1, d3-polygon@^3.0.1, d3-scale@^4.0.2 (+31 more)

### Community 51 - "Community 51"
Cohesion: 0.05
Nodes (39): devDependencies, cn@^0.3.3, @fontsource-variable/geist@^5.3.0, @fontsource-variable/geist-mono@^5.3.0, @fontsource-variable/inter@^5.3.0, formsnap@^2.0.1, mode-watcher@^1.1.0, @playwright/test@^1.63.0 (+31 more)

### Community 52 - "Community 52"
Cohesion: 0.11
Nodes (29): parse_hurdat2(), storm_relative_sequence(), test_fusion_weights_favour_the_lower_error_model(), test_entry_count_mismatch_raises(), test_header_name_is_parsed_onto_the_track(), test_malformed_header_raises(), test_malformed_latitude_raises(), test_multi_storm_file_produces_one_track_per_storm() (+21 more)

### Community 53 - "Community 53"
Cohesion: 0.10
Nodes (20): CycleResult, IntensityPercentiles, audit_cycle(), _CountingClient, _FakeClient, _fix(), _result(), test_a_cycle_stored_before_the_ri_interval_still_loads() (+12 more)

### Community 54 - "Community 54"
Cohesion: 0.09
Nodes (11): get_state(), require_api_key(), state_dependency(), get_custom_redoc_html(), create_app(), _debug_last_deterministic_error(), redoc_html(), _lifespan() (+3 more)

### Community 55 - "Community 55"
Cohesion: 0.10
Nodes (25): _check_basin(), expected_coordinates(), _decode(), files(), local(), _ohc(), _row_col(), server() (+17 more)

### Community 56 - "Community 56"
Cohesion: 0.10
Nodes (19): _decode_one_sonde(), DropsondeFetchError, DropsondeProfile, fetch_and_parse_dropsonde_mission(), fetch_dropsonde_mission_tarball(), _ftp_connect(), list_dropsonde_missions(), _mask_missing() (+11 more)

### Community 57 - "Community 57"
Cohesion: 0.11
Nodes (26): deterministic(), LatencyOracle, CycleAbandoned, plan_cycle(), total_budget(), test_a_cycle_started_at_the_timeout_still_clears_the_margin(), test_all_four_daily_cycles_plan_and_meet_their_deadlines(), test_core_is_ready_before_spread() (+18 more)

### Community 58 - "Community 58"
Cohesion: 0.09
Nodes (31): ArchitectureOut, LayerOut, {
		arch,
		onclose,
		class: className = ''
	}, Box, boxFor(), clamp(), color, focus (+23 more)

### Community 59 - "Community 59"
Cohesion: 0.06
Nodes (35): context, dockerfile, postgres, AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY, MLFLOW_S3_ENDPOINT_URL, POSTGRES_DB (+27 more)

### Community 60 - "Community 60"
Cohesion: 0.11
Nodes (20): _bytemap_path(), decode_ssmis_bytemap(), fetch_and_decode_ssmis_daily(), fetch_ssmis_daily_bytemap(), MicrowaveFetchError, RSSFtpCredentials, SSMISDaily, _make_bytemap() (+12 more)

### Community 61 - "Community 61"
Cohesion: 0.12
Nodes (15): ModelVersion, Stage, _reconcile_args(), test_registry_reconcile_dry_run_reports_without_transitioning(), test_registry_reconcile_ignores_nan_metrics(), test_registry_reconcile_never_touches_a_model_with_a_production_version(), test_registry_reconcile_re_stages_the_real_best_existing_version(), test_registry_reconcile_skips_an_unloadable_version_even_with_better_metrics() (+7 more)

### Community 62 - "Community 62"
Cohesion: 0.09
Nodes (20): advisory_time(), floor_synoptic(), is_synoptic(), next_synoptic(), NWPUnavailableError, require_synoptic(), _require_utc(), select_nwp_cycle() (+12 more)

### Community 63 - "Community 63"
Cohesion: 0.07
Nodes (19): brier_score(), crps_ensemble(), _crps_rows(), crps_series(), rank_histogram(), reliability(), spread_skill(), SpreadSkill (+11 more)

### Community 64 - "Community 64"
Cohesion: 0.09
Nodes (11): ModelRegistry, test_registry_route_refreshes_a_stale_registry(), _champions(), test_a_basin_is_served_once_every_champion_is_verified_in_it(), test_a_champion_verified_nowhere_serves_no_basin_as_in_distribution(), test_no_champion_or_champions_from_before_the_tag_are_the_atlantic(), _champions_tagged(), test_a_basin_counts_only_when_every_champion_trained_on_it() (+3 more)

### Community 65 - "Community 65"
Cohesion: 0.09
Nodes (17): _default_fetch_fn(), fetch(), era5_deps_available(), era5_to_gridded_fields(), fetch_era5t_one(), fetch_grib2_messages(), gridded_deps_available(), open_era5() (+9 more)

### Community 66 - "Community 66"
Cohesion: 0.11
Nodes (20): fetch_current_storm_ids(), fetch_current_storms(), fetch_live_track(), fetch_live_tracks(), fetch_one(), _get(), LiveAtcfError, test_fetch_current_storm_ids_parses_and_uppercases() (+12 more)

### Community 67 - "Community 67"
Cohesion: 0.11
Nodes (21): cycle_date(), ohc_global(), ohc_url(), select_file(), sshae_baseline(), target_creation_day(), _full_archive(), test_a_blank_run_longer_than_the_window_leaves_na_unavailable() (+13 more)

### Community 68 - "Community 68"
Cohesion: 0.09
Nodes (18): QUICK, API, DEVELOP, PHONE, SourceRow, SOURCES, SOURCES_BEFORE_USED_BY, SOURCES_REWIRED (+10 more)

### Community 69 - "Community 69"
Cohesion: 0.06
Nodes (28): AsyncReturnType, Expand, ExtractGenericViewableContent, GenericItem, GenericSelectorOption, GenericSnippetProps, GenericViewableContent, InheritedSnippetProps (+20 more)

### Community 70 - "Community 70"
Cohesion: 0.11
Nodes (16): _budget_entries(), PromotionError, spend_test_set_budget(), season_keys(), TestSetBudget, _FakeStore, test_a_legacy_single_file_ledger_still_counts(), test_an_earlier_key_landing_late_cannot_take_a_slot_already_spent() (+8 more)

### Community 71 - "Community 71"
Cohesion: 0.06
Nodes (31): data, basins, stage_a, epochs, flavor, input_sources, label_source, learning_rate (+23 more)

### Community 72 - "Community 72"
Cohesion: 0.12
Nodes (21): run_fetch_cache(), make_fields(), make_track(), test_default_fetch_fn_wires_a_shared_session(), fake_fetch_gdas_grib2_fields(), fake_gdas_to_gridded_fields(), test_fetch_one_fetches_exactly_one_real_sample(), fake_gdas_to_gridded_fields() (+13 more)

### Community 73 - "Community 73"
Cohesion: 0.10
Nodes (14): _check_adeck(), _check_official_errors(), file_record(), read_cached_official_errors(), OfficialErrors, OfficialErrorsError, parse_official_errors(), _signed() (+6 more)

### Community 74 - "Community 74"
Cohesion: 0.08
Nodes (9): _Boto3Client, require_boto3(), _StorageClient, FakeClient, test_boto3_adapter_configures_the_client_for_the_given_endpoint(), test_download_round_trips_the_uploaded_bytes(), test_list_filters_by_prefix(), test_upload_missing_file_raises() (+1 more)

### Community 75 - "Community 75"
Cohesion: 0.08
Nodes (30): @better-auth/api-key@^1.7.7, @types/node@^26.6.4, typescript@^5.9.3, wrangler@^4.147.0, @better-auth/api-key, @types/node, typescript, wrangler (+22 more)

### Community 76 - "Community 76"
Cohesion: 0.12
Nodes (8): cycle_plan_out(), CyclePlan, derive_vitals_timeout(), plan_day(), _schedule_stages(), ScheduledStage, StageBudget, test_vitals_timeout_is_derived_not_asserted()

### Community 77 - "Community 77"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, env, GH_TOKEN, GRAPHIFY_VERSION, permissions, runs-on (+22 more)

### Community 78 - "Community 78"
Cohesion: 0.11
Nodes (16): _adeck_position(), AtcfError, pair_by_valid_time(), parse_bdeck(), _parse_latlon(), parse_tcvitals(), TcVitalsError, test_bdeck_malformed_line_raises() (+8 more)

### Community 79 - "Community 79"
Cohesion: 0.12
Nodes (13): Fetcher, FetchError, ingest_cycle_inputs(), ingest_one(), IngestionOutcome, IngestionRecord, LakeTier, LakeWriter (+5 more)

### Community 80 - "Community 80"
Cohesion: 0.15
Nodes (20): build_cnn(), encode(), forward(), __init__(), cache_all_fixes(), make_fields(), make_track(), _task_for() (+12 more)

### Community 81 - "Community 81"
Cohesion: 0.12
Nodes (16): ReferenceDistribution, load_reference(), reference_from_json(), reference_to_json(), save_reference(), test_drift_report_detects_real_drift_once_enough_samples_are_collected(), test_drift_report_is_honest_zero_for_a_model_that_never_contributed(), test_reference_must_be_the_stage_b_distribution() (+8 more)

### Community 82 - "Community 82"
Cohesion: 0.08
Nodes (15): _expected_meta(), test_a_failed_time_is_reported_and_the_others_still_written(), fetch(), test_a_lost_race_with_no_file_appearing_raises_the_write_error(), test_cache_round_trip_and_vector(), test_disc_mean_is_symmetric_for_a_field_linear_in_longitude(), test_features_advect_with_the_flow_plus_beta_drift(), test_features_raise_where_there_is_no_flow() (+7 more)

### Community 83 - "Community 83"
Cohesion: 0.07
Nodes (23): rehype-slug@^6.0.0, rehype-stringify@^10.0.1, remark-gfm@^4.0.1, remark-parse@^11.0.0, remark-rehype@^11.1.2, unified@^11.0.5, unist-util-visit@^5.1.0, CONSOLE_ROOT (+15 more)

### Community 84 - "Community 84"
Cohesion: 0.07
Nodes (29): WithElementRef, ButtonClickEvent, PrimitiveAnchorAttributes, PrimitiveButtonAttributes, PrimitiveCanvasAttributes, PrimitiveDivAttributes, PrimitiveElementAttributes, PrimitiveFigureAttributes (+21 more)

### Community 85 - "Community 85"
Cohesion: 0.11
Nodes (13): _created_date(), creation_day(), decode_ohc(), detect_format(), fetch_ohc_file(), name_day_for_creation(), OhcFile, OhcRejected (+5 more)

### Community 86 - "Community 86"
Cohesion: 0.12
Nodes (17): cross_along_track_nms(), calibrate(), forecast_motion_bearings(), observed_motion_bearings(), recurving_cases(), _scalar_errors(), _centre(), _jitter() (+9 more)

### Community 87 - "Community 87"
Cohesion: 0.10
Nodes (16): _FakeCycleOutput, _fresh_real_state(), _make_deterministic_forecast(), _make_storm_state(), _memory_store(), _MemoryS3Client, test_a_failed_cycle_write_never_fails_the_cycle(), test_an_unrestored_drift_window_is_never_written_back() (+8 more)

### Community 88 - "Community 88"
Cohesion: 0.08
Nodes (22): CyclePlanOut, deadline, { plan }, Props, stageLabel, t0, totalMs, pollWhileVisible() (+14 more)

### Community 89 - "Community 89"
Cohesion: 0.07
Nodes (28): inputArgs, jobs, projectId, region, results, timeoutSeconds, assign, return (+20 more)

### Community 90 - "Community 90"
Cohesion: 0.12
Nodes (19): adeck_urls(), AdeckFetchReport, fetch_adecks(), _adeck_positive(), parse_adeck(), _archive(), _errors_url(), _FakeNhc (+11 more)

### Community 91 - "Community 91"
Cohesion: 0.12
Nodes (15): AdeckPoint, _adeck(), _avni_from_truth(), _persistence(), test_live_prior_matches_training_and_is_none_without_avni(), test_no_prior_without_avni_at_the_first_lead_or_the_cycle(), test_one_prior_fetch_is_shared_by_every_model_in_a_forecast(), test_prior_is_avni_displacement_with_persistence_where_avni_stops() (+7 more)

### Community 92 - "Community 92"
Cohesion: 0.10
Nodes (18): Archive, archives_for(), describe(), fetch_latest_hurdat2(), last_season(), latest_name(), manifest_path(), test_a_listing_without_one_archive_falls_back_for_that_archive_only() (+10 more)

### Community 93 - "Community 93"
Cohesion: 0.12
Nodes (22): build_cone(), climatological_cone_nm(), ConeSegment, _interpolate_climo(), members(), test_a_climatological_cone_uses_the_storms_basin(), test_cone_has_one_segment_per_lead_time(), test_cone_is_ensemble_based_when_spread_is_credible() (+14 more)

### Community 94 - "Community 94"
Cohesion: 0.10
Nodes (17): _crop_box(), crop(), crop_levels(), _global_grid_with_marker(), _synthetic_era5_dataset(), _synthetic_gdas_fields(), test_crop_box_centers_on_the_requested_lat_lon(), test_crop_box_rejects_the_wrong_global_shape() (+9 more)

### Community 95 - "Community 95"
Cohesion: 0.10
Nodes (16): http_get(), OhcFetchError, OhcNotPublished, OhcUnavailable, Archive, test_a_cut_off_reply_is_a_fetch_failure(), test_a_cut_off_transfer_raises_rather_than_reading_an_older_file(), test_a_fetch_failure_that_is_not_a_404_is_not_stepped_over() (+8 more)

### Community 96 - "Community 96"
Cohesion: 0.12
Nodes (13): build_products(), cone_radius_from_spread(), deterministic_center(), EnsembleMember, ForecastProducts, intensity_pdf(), landfall_probability(), _positions() (+5 more)

### Community 97 - "Community 97"
Cohesion: 0.14
Nodes (15): detect_feature_drift(), DriftError, FeatureDrift, ValidationLossMonitor, reference(), test_a_recovery_resets_the_consecutive_count(), test_collapsed_variance_is_detected(), test_feature_count_mismatch_raises() (+7 more)

### Community 98 - "Community 98"
Cohesion: 0.16
Nodes (13): cache_current_fix(), _FakeS3Client, make_track(), _register_real_version(), _store(), test_build_real_deterministic_fn_combines_all_four_real_models(), test_build_real_deterministic_fn_raises_with_no_registered_models(), test_build_real_deterministic_fn_uses_the_real_learned_fusion_with_all_five() (+5 more)

### Community 99 - "Community 99"
Cohesion: 0.14
Nodes (18): _fake_checkpoint_store(), make_track(), test_a_run_on_two_basins_scores_each_on_its_own(), test_build_stage_samples_drops_a_track_too_short_for_any_lead(), test_build_stage_samples_full_length_track_covers_every_lead(), test_build_stage_samples_masked_entries_are_recoverable_positions(), test_build_stage_samples_masks_leads_beyond_a_short_track(), test_displacement_to_latlon_is_a_noop_for_zero_displacement() (+10 more)

### Community 100 - "Community 100"
Cohesion: 0.07
Nodes (10): _FakeMlflowModelVersion, _mlflow_client_that_registers_and_transitions(), create_model_version(), test_mlflow_mirror_skips_create_registered_model_if_it_already_exists(), create_model_version(), test_mlflow_transition_also_mirrors_the_archived_incumbent(), create_model_version(), test_mlflow_transition_mirror_uses_the_real_mlflow_version_number() (+2 more)

### Community 101 - "Community 101"
Cohesion: 0.14
Nodes (13): InferenceEnsembleError, cache_current_fix(), _FakeS3Client, make_track(), _register(), _register_all_five_and_diffusion(), _store(), test_build_real_ensemble_fn_produces_real_finite_members() (+5 more)

### Community 102 - "Community 102"
Cohesion: 0.19
Nodes (14): audit_due(), SkewMonitor, sample(), test_audit_becomes_due_once_era5t_lands(), test_audit_is_not_due_immediately_after_the_cycle(), test_intensity_delta_is_signed_toward_the_operational_run(), test_intensity_skew_alone_can_raise_an_alert(), test_large_track_delta_raises_an_alert() (+6 more)

### Community 103 - "Community 103"
Cohesion: 0.10
Nodes (12): color_for(), god(), Module, WindGod, test_every_god_color_is_distinct(), test_experiment_name_handles_fusion_without_raising(), test_experiment_names_are_the_god_slugs(), test_lookup_by_slug_and_by_architecture_agree() (+4 more)

### Community 104 - "Community 104"
Cohesion: 0.12
Nodes (15): get(), Role, _model_sources(), test_a_label_or_verification_source_is_never_a_model_input(), test_a_model_input_is_never_a_labels_only_source(), test_each_curriculum_stage_lists_what_its_models_read(), test_era5_is_pretrain_only(), test_era5_latency_is_days_not_hours() (+7 more)

### Community 105 - "Community 105"
Cohesion: 0.08
Nodes (9): test_cmd_train_actually_transitions_a_promotable_candidate_to_staging(), _FakeS3Config, test_checkpoint_store_push_failure_degrades_to_local_only(), test_checkpoint_store_push_mirrors_registry_json_after_every_save(), test_pull_failure_degrades_to_an_empty_registry(), test_pull_from_checkpoint_store_hydrates_a_missing_local_registry(), test_pull_is_a_noop_when_the_key_does_not_exist_remotely_yet(), test_pull_is_skipped_entirely_without_a_checkpoint_store() (+1 more)

### Community 106 - "Community 106"
Cohesion: 0.18
Nodes (19): build_mesh_topology(), cache_all_fixes(), make_fields(), make_track(), _task_for(), test_batch_graph_offsets_edges_per_sample_block(), test_build_gnn_samples_empty_when_nothing_cached(), test_build_gnn_samples_node_feature_width_matches_default() (+11 more)

### Community 107 - "Community 107"
Cohesion: 0.16
Nodes (13): cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_build_transformer_samples_empty_when_nothing_cached(), test_build_transformer_samples_rejects_a_cache_smaller_than_grid_size(), test_build_transformer_samples_trims_the_real_41x41_crop_to_grid_size() (+5 more)

### Community 108 - "Community 108"
Cohesion: 0.11
Nodes (13): _attributes(), _called(), _calls(), _function(), _imported(), _modules(), _names_adapter(), _parameters() (+5 more)

### Community 109 - "Community 109"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GH_TOKEN, IMPORTED_FROM, SOURCE_SHA, jobs, publish (+16 more)

### Community 110 - "Community 110"
Cohesion: 0.14
Nodes (15): _all_tensors(), Architecture, _builder(), describe(), describe_cached(), _describe_cached(), hook(), _example_inputs() (+7 more)

### Community 111 - "Community 111"
Cohesion: 0.15
Nodes (17): cross_along_track_nm(), _lon_close(), _members(), ref_bearing(), ref_displacement(), ref_haversine(), ref_offset(), rng() (+9 more)

### Community 112 - "Community 112"
Cohesion: 0.14
Nodes (10): cycle_inputs_prefix(), cycle_key(), CycleHistory, _get_text(), load_cycle_result(), load_drift_live(), _put_text(), save_cycle_inputs() (+2 more)

### Community 113 - "Community 113"
Cohesion: 0.12
Nodes (15): check_run(), _existing_source(), operator_ids(), RunRequest, stored_source(), RunInfo, _check(), _Stored (+7 more)

### Community 114 - "Community 114"
Cohesion: 0.12
Nodes (10): _default_fetch_fn(), fetch(), fetch_one(), fetch_gdas_grib2_fields(), gdas_to_gridded_fields(), crop(), gfs_url(), test_gdas_archive_start_is_the_first_valid_time_with_an_atmos_f006() (+2 more)

### Community 115 - "Community 115"
Cohesion: 0.13
Nodes (11): fetch_gefs_ensemble_grib2_fields(), fetch_gefs_member_grib2_fields(), _gefs_member_url(), _parse_grib2_index(), require_gdas_deps(), test_control_member_zero_uses_gec00_not_gep00(), test_fetch_gefs_ensemble_reads_multiple_real_distinct_members(), test_fetch_gefs_member_reads_the_real_noaa_archive() (+3 more)

### Community 116 - "Community 116"
Cohesion: 0.08
Nodes (3): client(), test_more_members_than_the_ensemble_runs_is_refused_not_silently_capped(), test_sources_say_who_uses_each_one()

### Community 117 - "Community 117"
Cohesion: 0.11
Nodes (8): god_out(), model_catalog(), source_out(), health(), models(), sources(), DataSource, pretrain_only_sources()

### Community 118 - "Community 118"
Cohesion: 0.16
Nodes (12): fetch_lead_flow(), group_by_time(), run_steering_cache(), fetch(), one_time(), shard_times(), steering_path(), steering_targets() (+4 more)

### Community 119 - "Community 119"
Cohesion: 0.17
Nodes (12): accessed(), _check_type(), config_dir(), ConfigError, fixed(), get(), get_list(), _load() (+4 more)

### Community 120 - "Community 120"
Cohesion: 0.13
Nodes (7): mlflow_client_from_env(), test_an_unreachable_server_is_skipped_fast(), test_builds_a_real_client_when_tracking_uri_is_set(), test_fail_fast_settings_never_override_explicit_ones(), test_mlflow_client_from_env_can_actually_reach_the_configured_server(), test_returns_none_when_tracking_uri_is_unset(), test_returns_none_without_mlflow_installed()

### Community 121 - "Community 121"
Cohesion: 0.14
Nodes (11): _files(), localize_cache(), LocalizeReport, _raise(), _cache(), test_a_directory_that_cant_be_listed_fails_the_copy(), test_a_missing_source_raises(), test_a_rerun_only_fills_gaps() (+3 more)

### Community 122 - "Community 122"
Cohesion: 0.14
Nodes (10): lr_factor(), transformer_optim(), TransformerOptim, TransformerOptimizer, test_a_short_stage_still_ends_on_the_floor(), test_config_values_are_validated(), test_cosine_decays_to_the_floor_on_the_last_update(), test_no_warmup_starts_at_the_peak() (+2 more)

### Community 123 - "Community 123"
Cohesion: 0.15
Nodes (9): _FakeS3Client, _make_samples(), test_a_longer_epoch_budget_never_returns_a_worse_val_loss(), test_early_stopping_halts_before_the_epoch_cap_on_a_real_overfitting_run(), test_run_diffusion_curriculum_uploads_a_checkpoint_and_registers_stage_b(), test_train_diffusion_stage_accepts_dropout_and_weight_decay(), test_train_diffusion_stage_produces_val_metrics_and_artifacts(), test_train_diffusion_stage_records_a_real_dropout_value_in_arch_params() (+1 more)

### Community 124 - "Community 124"
Cohesion: 0.10
Nodes (7): DELETE, GET, PATCH, POST, PUT, prerender, ssr

### Community 125 - "Community 125"
Cohesion: 0.10
Nodes (20): PROJECT_NUMBER, PROJECT_PAT, types, jobs, sync, name, on, issues (+12 more)

### Community 126 - "Community 126"
Cohesion: 0.18
Nodes (12): build_samples(), run_capacity_ablation(), train_cell(), make_track(), test_build_samples_augmentation_multiplies_sample_count(), test_build_samples_shapes_match_sequence_length_and_columns(), test_build_samples_skips_storms_shorter_than_required(), test_build_samples_wind_label_uses_final_track_not_the_noisy_working_input() (+4 more)

### Community 127 - "Community 127"
Cohesion: 0.15
Nodes (14): cache_steering(), _curriculum_tracks(), make_track(), test_curriculum_refuses_steering_without_streaming_or_without_the_cache_meta(), test_latents_need_a_steering_cache_for_a_model_that_reads_steering(), test_live_steering_is_none_before_the_gfs_archive(), test_n_steering_of_reads_arch_params_and_defaults_to_zero(), test_one_forecast_call_fetches_steering_once_failures_included() (+6 more)

### Community 128 - "Community 128"
Cohesion: 0.21
Nodes (6): freeCycleLabel(), label(), runFreshCycle(), signIn(), cases, @playwright/test

### Community 129 - "Community 129"
Cohesion: 0.16
Nodes (17): answerRuns(), chip(), context(), cycleFor(), dateButton(), expectForm(), expectShowing(), fixture (+9 more)

### Community 130 - "Community 130"
Cohesion: 0.10
Nodes (7): client(), test_docs_route_is_unaffected(), test_sources_role_is_the_role_enum_in_the_openapi_schema(), test_sources_used_by_is_documented_in_the_openapi_schema(), test_theme_http_method_colors_are_distinct(), test_theme_never_uses_a_god_color(), _walk()

### Community 131 - "Community 131"
Cohesion: 0.15
Nodes (12): client(), _post(), s3(), test_a_concurrent_run_of_the_same_label_is_refused(), test_a_label_outside_the_track_is_a_400(), test_a_second_run_of_a_label_is_a_409_with_a_code(), test_an_operator_can_replace_a_cycle(), test_run_request_refuses_an_unknown_source() (+4 more)

### Community 132 - "Community 132"
Cohesion: 0.15
Nodes (11): compute_environment_features(), generate_fields(), field(), paired_fields(), test_compute_environment_features_raises_when_storm_is_entirely_over_land(), test_compute_environment_features_succeeds_with_partial_land_coverage(), test_feature_vector_length_matches_the_names(), test_features_carry_their_flavor() (+3 more)

### Community 133 - "Community 133"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 134 - "Community 134"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 135 - "Community 135"
Cohesion: 0.15
Nodes (6): CloudflareAccessRequestHeaderProvider, test_headers_are_actually_applied_by_mlflows_own_resolution(), test_in_context_false_when_neither_var_set(), test_in_context_false_when_only_client_id_set(), test_in_context_true_and_correct_headers_when_both_set(), test_registered_as_a_real_mlflow_plugin_via_entry_points()

### Community 136 - "Community 136"
Cohesion: 0.18
Nodes (8): get_cycle(), get_storm(), list_storms(), _overrides(), run_cycle(), _served_basins(), _storm_summary(), FixOut

### Community 137 - "Community 137"
Cohesion: 0.14
Nodes (6): BasinChoice, _declared_length(), _grid_values(), _read_checked(), StepBack, test_the_flag_on_real_files()

### Community 138 - "Community 138"
Cohesion: 0.15
Nodes (12): generate_archive(), _radial_gradient_fields(), test_inner_core_moisture_reflects_the_core_not_the_environment(), test_leakage_is_detected_when_a_storm_id_repeats_across_seasons(), test_no_storm_appears_in_two_splits(), test_overlapping_boundaries_are_rejected(), test_sanitize_field_pixels_fills_nan_with_the_fields_own_spatial_mean(), test_sanitize_field_pixels_is_a_no_op_when_nothing_is_nan() (+4 more)

### Community 139 - "Community 139"
Cohesion: 0.12
Nodes (16): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+8 more)

### Community 140 - "Community 140"
Cohesion: 0.12
Nodes (16): compilerOptions, allowJs, allowSyntheticDefaultImports, checkJs, forceConsistentCasingInFileNames, isolatedModules, lib, module (+8 more)

### Community 141 - "Community 141"
Cohesion: 0.12
Nodes (16): permissions, runs-on, steps, jobs, copilot-setup-steps, name, on, pull_request (+8 more)

### Community 142 - "Community 142"
Cohesion: 0.15
Nodes (6): calibration_out(), skew_report_out(), calibration(), drift(), drift_all(), skew()

### Community 143 - "Community 143"
Cohesion: 0.18
Nodes (7): assert_flavor(), FeatureSet, FlavorMismatchError, Normalizer, test_flavor_guard_rejects_a_pretrain_feature_on_the_operational_path(), test_normalizer_refuses_to_fit_across_flavors(), test_normalizer_rejects_the_wrong_flavor_at_apply_time()

### Community 144 - "Community 144"
Cohesion: 0.17
Nodes (9): _bilinear(), _lattice_index(), ohc_at(), OhcField, place(), test_bilinear_between_nodes(), test_bilinear_is_exact_at_a_node_on_every_source(), test_bilinear_needs_all_four_corners() (+1 more)

### Community 145 - "Community 145"
Cohesion: 0.21
Nodes (13): _fields(), _run(), test_a_missing_t_minus_6_cycle_falls_back_to_t_minus_12(), fetch_one(), test_gfs_url_names_the_forecast_valid_at_the_time(), test_live_fields_come_from_the_t_minus_6_forecast(), fetch_one(), test_no_nwp_at_all_is_flagged() (+5 more)

### Community 146 - "Community 146"
Cohesion: 0.16
Nodes (8): al_2021_2022(), compare(), open_ocean(), parse_ships(), sample_days(), ShipsCase, test_sohc_equals_bilinear_ohc_on_the_file_named_for_the_day_before(), test_compare_refuses_arms_on_different_windows_and_pairs_the_rest()

### Community 147 - "Community 147"
Cohesion: 0.12
Nodes (16): with, build-args, cache-from, cache-to, context, file, load, password (+8 more)

### Community 148 - "Community 148"
Cohesion: 0.12
Nodes (15): jobs, lint-and-validate, name, permissions, runs-on, steps, name, on (+7 more)

### Community 149 - "Community 149"
Cohesion: 0.17
Nodes (8): adeck_name(), adeck_path(), CachedAdecks, read_adeck(), read_cached_adecks(), test_adeck_names_urls_and_paths_come_only_from_valid_storm_ids(), test_read_cached_adecks_reads_gzip_and_records_missing_and_unreadable(), test_real_archived_adeck_carries_the_default_techniques()

### Community 150 - "Community 150"
Cohesion: 0.13
Nodes (7): area_mean(), deep_layer_shear(), test_area_mean_ignores_nan_pixels_from_partial_land_coverage(), test_area_mean_matches_plain_mean_when_nothing_is_nan(), test_area_mean_returns_nan_when_the_whole_box_is_land(), test_potential_intensity_proxy_is_unaffected_by_the_closed_form_addition(), test_shear_increases_when_the_upper_flow_strengthens()

### Community 151 - "Community 151"
Cohesion: 0.12
Nodes (10): used_by(), test_cmd_sources_prints_who_uses_each_source(), test_a_verification_source_not_read_yet_is_verification_and_nothing_else(), test_an_adapter_is_named_by_other_code_only_if_its_source_is_read(), test_every_fetch_adapter_is_classified(), test_every_required_cycle_input_has_a_model_consumer(), test_used_by_follows_the_contract_order_for_every_source(), test_used_by_per_source() (+2 more)

### Community 152 - "Community 152"
Cohesion: 0.26
Nodes (9): AblationCell, AblationReport, _cell(), test_at_fraction_filters_and_sorts_by_hidden_dim(), test_capacity_does_not_help_when_val_loss_plateaus(), test_capacity_helps_requires_at_least_two_capacity_levels(), test_capacity_helps_uses_the_largest_fraction_present(), test_capacity_helps_when_val_loss_keeps_dropping_with_width() (+1 more)

### Community 153 - "Community 153"
Cohesion: 0.19
Nodes (6): _FakeS3Client, _make_samples(), test_run_fusion_curriculum_uploads_a_checkpoint_and_registers_stage_b(), test_train_fusion_stage_reduces_loss_and_produces_val_metrics(), test_train_fusion_stage_rejects_a_val_set_built_with_a_different_model_count(), test_train_fusion_stage_rejects_empty_samples()

### Community 154 - "Community 154"
Cohesion: 0.13
Nodes (15): scripts, build, cf:deploy, check, check:errors, check:warnings, check:watch, dev (+7 more)

### Community 155 - "Community 155"
Cohesion: 0.19
Nodes (12): loading, onInput(), open, query, results, bodyById, buildIndex(), excerptAround() (+4 more)

### Community 156 - "Community 156"
Cohesion: 0.13
Nodes (15): env, environment, if, name, needs, permissions, runs-on, timeout-minutes (+7 more)

### Community 157 - "Community 157"
Cohesion: 0.19
Nodes (11): filter_tracks_by_min_valid_time(), shard_tracks(), _fix_keys(), make_track(), test_a_shard_drops_storms_with_no_fixes_in_it(), test_filter_drops_a_storm_entirely_if_no_fixes_survive(), test_filter_drops_fixes_earlier_than_the_cutoff(), test_filter_keeps_a_straddling_storm_partially() (+3 more)

### Community 158 - "Community 158"
Cohesion: 0.24
Nodes (11): validate(), make_tags(), test_malformed_dvc_version_is_rejected(), test_malformed_git_commit_is_rejected(), test_malformed_nwp_cycle_lag_is_rejected(), test_none_values_are_dropped_from_the_dict(), test_pretrain_flavor_tags_are_not_operational(), test_v2_1_adds_input_flavor_and_nwp_cycle_lag() (+3 more)

### Community 159 - "Community 159"
Cohesion: 0.21
Nodes (6): model_version_out(), get_active_pin(), get_model_architecture(), get_model_registry(), list_registry(), RegistryEntry

### Community 160 - "Community 160"
Cohesion: 0.14
Nodes (13): compilerOptions, allowJs, checkJs, esModuleInterop, forceConsistentCasingInFileNames, moduleResolution, resolveJsonModule, rewriteRelativeImportExtensions (+5 more)

### Community 161 - "Community 161"
Cohesion: 0.14
Nodes (13): images, options, diskSizeGb, machineType, steps, args, entrypoint, env (+5 more)

### Community 162 - "Community 162"
Cohesion: 0.14
Nodes (14): default, description, type, default, description, type, api, console (+6 more)

### Community 163 - "Community 163"
Cohesion: 0.19
Nodes (10): generate_season(), test_archive_spans_the_requested_seasons(), test_fields_have_matching_shapes_and_carry_a_flavor(), test_fixes_are_six_hourly_and_synoptic(), test_gdas_fields_are_noisier_than_era5(), test_generated_tracks_are_final_quality(), test_generation_is_reproducible(), test_intensity_rises_and_falls() (+2 more)

### Community 164 - "Community 164"
Cohesion: 0.35
Nodes (7): NoiseSensitivityReport, _result(), test_is_load_bearing_above_threshold(), test_is_not_load_bearing_below_threshold(), test_relative_change_is_zero_when_losses_match(), test_relative_change_rejects_nonpositive_default_loss(), test_relative_change_sign_matches_direction_of_the_move()

### Community 165 - "Community 165"
Cohesion: 0.17
Nodes (12): IdTokenClaims, JwtClaims, OidcAddressClaim, OidcStandardClaims, UserProfile, Mandatory, RFC-3966, RFC-4627 (+4 more)

### Community 166 - "Community 166"
Cohesion: 0.19
Nodes (7): client(), test_a_registered_versions_arch_params_are_used(), test_a_version_that_reads_steering_is_described(), test_a_version_without_arch_params_is_described_from_defaults(), test_a_versions_arch_params_change_what_is_described(), test_every_model_runs_its_example_input_and_reports_its_layers(), test_unknown_models_and_versions_are_404()

### Community 167 - "Community 167"
Cohesion: 0.15
Nodes (12): name, runs-on, timeout-minutes, concurrency, cancel-in-progress, group, jobs, build (+4 more)

### Community 168 - "Community 168"
Cohesion: 0.23
Nodes (11): max, target, budgets, reduced, standard, max, target, assembly (+3 more)

### Community 169 - "Community 169"
Cohesion: 0.17
Nodes (4): local, notes, problems, remote

### Community 170 - "Community 170"
Cohesion: 0.23
Nodes (5): build_info(), _build_info_path(), config_digest(), git_sha(), summary()

### Community 171 - "Community 171"
Cohesion: 0.17
Nodes (11): concurrency, cancel-in-progress, group, jobs, test-api, name, if, name (+3 more)

### Community 172 - "Community 172"
Cohesion: 0.17
Nodes (12): with, cache, cache-dependency-path, enable-cache, fetch-depth, if-no-files-found, include-hidden-files, name (+4 more)

### Community 173 - "Community 173"
Cohesion: 0.17
Nodes (6): test_mlflow_failure_degrades_to_local_only(), __getattr__(), test_mlflow_mirror_is_skipped_without_a_checkpoint_uri(), __getattr__(), test_mlflow_mirror_registers_model_then_version_with_a_real_source_uri(), create_model_version()

### Community 174 - "Community 174"
Cohesion: 0.18
Nodes (11): cycle, advisory_margin_minutes, advisory_offset_minutes, allow_estimated_vitals, allow_load_shedding, max_nwp_lag_hours, nominal_vitals_offset_minutes, nwp_lag_hours (+3 more)

### Community 175 - "Community 175"
Cohesion: 0.18
Nodes (7): emanuel_potential_intensity(), _saturation_vapor_pressure_hpa(), _specific_humidity_kg_kg(), test_emanuel_pi_increases_with_warmer_sst(), test_emanuel_pi_is_reduced_above_the_shear_onset(), test_emanuel_pi_is_zero_when_the_boundary_layer_is_warmer_and_moister_than_the_surface(), test_saturation_vapor_pressure_matches_known_bolton_values()

### Community 176 - "Community 176"
Cohesion: 0.22
Nodes (7): assert_not_operational(), operational_sources(), _operational_substitute(), OperationalUseError, test_operational_sources_pass_the_guard(), test_reading_era5_in_the_inference_path_is_refused(), test_reading_final_besttrack_in_the_inference_path_is_refused()

### Community 177 - "Community 177"
Cohesion: 0.22
Nodes (6): first_record_of_year(), ships_al_url(), _ships_get(), ships_record_year(), ships_size(), ships_window()

### Community 178 - "Community 178"
Cohesion: 0.20
Nodes (10): limit, lower_is_better, limit, lower_is_better, thresholds, intensity_error_48h_kt, intensity_error_72h_kt, track_error_72h_nm (+2 more)

### Community 179 - "Community 179"
Cohesion: 0.20
Nodes (10): steps, EXPECT_GIT_SHA, GCP_CI_SERVICE_ACCOUNT, GCP_WIF_PROVIDER, env, id, if, name (+2 more)

### Community 180 - "Community 180"
Cohesion: 0.20
Nodes (10): name, outputs, runs-on, timeout-minutes, changes, deploy_api, deploy_console, plan (+2 more)

### Community 181 - "Community 181"
Cohesion: 0.40
Nodes (10): steps, steps, id, if, name, run, uses, working-directory (+2 more)

### Community 182 - "Community 182"
Cohesion: 0.22
Nodes (5): _fetch_one(), _get(), _get_bytes(), NotPublished, fetch_live_adeck()

### Community 183 - "Community 183"
Cohesion: 0.27
Nodes (4): ChecksumCheck, FetchResult, NonEmptyCheck, QCFinding

### Community 184 - "Community 184"
Cohesion: 0.20
Nodes (4): _FakeS3Client, test_a_version_with_a_prior_is_described_and_loaded(), test_curriculum_with_a_prior_scores_prior_plus_correction(), run()

### Community 185 - "Community 185"
Cohesion: 0.22
Nodes (9): run, test-console, working-directory, defaults, if, name, needs, runs-on (+1 more)

### Community 186 - "Community 186"
Cohesion: 0.22
Nodes (9): BASE_SHA, BEFORE_SHA, DISPATCH_API, DISPATCH_CONSOLE, EVENT, EXPECT_GIT_SHA, HEAD_SHA, REF (+1 more)

### Community 187 - "Community 187"
Cohesion: 0.28
Nodes (3): CycleConflict, InFlight, test_in_flight_allows_one_run_per_label()

### Community 188 - "Community 188"
Cohesion: 0.28
Nodes (4): cache_nwp_lead_hours(), CacheLeadMismatch, _claim_cache_dir(), test_a_cache_dir_holds_one_lead()

### Community 189 - "Community 189"
Cohesion: 0.25
Nodes (6): build_lstm(), encode(), forward(), __init__(), candidate_model(), test_train_lstm_stage_streaming_num_workers_matches_the_main_process_result()

### Community 190 - "Community 190"
Cohesion: 0.28
Nodes (4): oracle(), pytest_collection_modifyitems(), target_time(), worst_case_oracle()

### Community 191 - "Community 191"
Cohesion: 0.22
Nodes (3): client(), _MemoryS3, s3()

### Community 192 - "Community 192"
Cohesion: 0.25
Nodes (5): _forward(), test_a_zero_steering_conv_computes_the_plain_model(), test_a_zero_steering_path_computes_the_plain_model(), test_builder_without_steering_keeps_the_old_layout(), test_curriculum_trains_the_steering_path_in_stage_b_only()

### Community 193 - "Community 193"
Cohesion: 0.25
Nodes (8): 12, 120, 24, 36, 48, 72, 96, climatological_cone_nm

### Community 194 - "Community 194"
Cohesion: 0.25
Nodes (8): CP, 12, 120, 24, 36, 48, 72, 96

### Community 195 - "Community 195"
Cohesion: 0.25
Nodes (8): EP, 12, 120, 24, 36, 48, 72, 96

### Community 196 - "Community 196"
Cohesion: 0.25
Nodes (7): calibration_audit, cone_nominal_rate, intensity_nominal_rate, min_cases, verdict_margin, test_set_budget, max_evaluations_per_season

### Community 197 - "Community 197"
Cohesion: 0.25
Nodes (8): drift, min_samples, reference_flavor, shift_sigma, validation_loss, variance_ratio_limit, consecutive_required, threshold_fraction

### Community 198 - "Community 198"
Cohesion: 0.25
Nodes (8): promotion, flavor, new_basin_tolerance, primary_metric, reference_basin, require_manual_gate, split, basins()

### Community 199 - "Community 199"
Cohesion: 0.25
Nodes (6): apply_cold_wake(), cold_wake_sst_depression_c(), test_apply_cold_wake_depresses_sst_and_ohc_without_touching_other_fields(), test_apply_cold_wake_is_a_noop_for_a_calm_storm(), test_cold_wake_depression_grows_with_wind_and_shrinks_with_translation_speed(), test_cold_wake_is_a_noop_for_zero_wind()

### Community 201 - "Community 201"
Cohesion: 0.29
Nodes (7): products, cone_percentile, landfall_threshold_nm, lead_hours, ri_alert_probability, ri_threshold_kt, ri_window_hours

### Community 202 - "Community 202"
Cohesion: 0.29
Nodes (7): skew_audit, alert_intensity_delta_kt, alert_track_delta_nm, audit_delay_days, lead_hours, min_samples, window_days

### Community 203 - "Community 203"
Cohesion: 0.57
Nodes (5): deploy-plan.sh script, touches(), touches_component(), touches_console(), why

### Community 204 - "Community 204"
Cohesion: 0.29
Nodes (7): env, IMAGE, JOB, PROJECT_ID, PUBLISH, REGION, REGISTRY

### Community 207 - "Community 207"
Cohesion: 0.29
Nodes (3): archive_atcf(), calibration_audit(), skew_audit()

### Community 208 - "Community 208"
Cohesion: 0.33
Nodes (4): wilson_interval(), test_ri_uncertain_marks_an_ensemble_that_cannot_resolve_the_threshold(), test_wilson_interval_brackets_the_estimate_and_stays_in_the_unit_range(), width()

### Community 213 - "Community 213"
Cohesion: 0.33
Nodes (6): ensemble, climatological_cone_nm_by_basin, members, min_members_for_ensemble_cone, reduced_members, underdispersion_fraction

### Community 214 - "Community 214"
Cohesion: 0.33
Nodes (6): triggers, data_volume_threshold, nightly_latent_hour_utc, preseason_date, scheduled_monthly_day, suppress_nightly_latent_during_active_storms

### Community 216 - "Community 216"
Cohesion: 0.33
Nodes (6): update_job, workflow_dispatch, default, description, type, inputs

### Community 217 - "Community 217"
Cohesion: 0.33
Nodes (6): on, pull_request, push, paths, branches, paths

### Community 219 - "Community 219"
Cohesion: 0.33
Nodes (3): compare_potential_intensity_estimates(), potential_intensity(), test_compare_potential_intensity_estimates_documents_the_closed_form_running_hot()

### Community 220 - "Community 220"
Cohesion: 0.47
Nodes (3): Threshold, _thresholds(), test_beat_rate_threshold_is_higher_is_better()

### Community 223 - "Community 223"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 224 - "Community 224"
Cohesion: 0.40
Nodes (3): WORLD_GEOJSON, WorldData, WorldFeatureProperties

### Community 225 - "Community 225"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 226 - "Community 226"
Cohesion: 0.40
Nodes (4): ANEMOI_ADECK_DIR, ANEMOI_FIELDS_MEMO, ANEMOI_STEERING_CACHE_DIR, entrypoint.sh script

### Community 229 - "Community 229"
Cohesion: 0.60
Nodes (5): test_live_steering_is_none_when_any_lead_is_missing(), fetcher(), test_live_steering_matches_the_training_features_and_is_cached(), fetcher(), _uniform()

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

### Community 235 - "Community 235"
Cohesion: 0.83
Nodes (3): graphify(), normalise_graph(), build-graph.sh script

### Community 236 - "Community 236"
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
- **15 isolated node(s):** `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627`, `RFC-5322`, `RFC-5646` (+10 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2886 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Flavor` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 132`, `Community 5`, `Community 7`, `Community 8`, `Community 138`, `Community 11`, `Community 12`, `Community 13`, `Community 142`, `Community 143`, `Community 14`, `Community 16`, `Community 145`, `Community 19`, `Community 21`, `Community 150`, `Community 22`, `Community 24`, `Community 153`, `Community 25`, `Community 158`, `Community 30`, `Community 34`, `Community 163`, `Community 166`, `Community 40`, `Community 44`, `Community 173`, `Community 46`, `Community 47`, `Community 49`, `Community 184`, `Community 61`, `Community 64`, `Community 65`, `Community 192`, `Community 199`, `Community 72`, `Community 80`, `Community 81`, `Community 219`, `Community 91`, `Community 94`, `Community 97`, `Community 98`, `Community 99`, `Community 228`, `Community 101`, `Community 100`, `Community 104`, `Community 105`, `Community 106`, `Community 107`, `Community 114`, `Community 119`, `Community 123`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 257 inferred relationships involving `Flavor` (e.g. with `DemoState` and `drift()`) actually correct?**
  _`Flavor` has 257 INFERRED edges - model-reasoned connections that need verification._
- **What connects `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627` to the rest of the system?**
  _15 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.03597055260460349 - nodes in this community are weakly interconnected._
- **Why does `Track` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 5`, `Community 7`, `Community 8`, `Community 138`, `Community 10`, `Community 12`, `Community 13`, `Community 11`, `Community 14`, `Community 16`, `Community 145`, `Community 18`, `Community 19`, `Community 21`, `Community 24`, `Community 25`, `Community 157`, `Community 163`, `Community 40`, `Community 47`, `Community 49`, `Community 52`, `Community 66`, `Community 72`, `Community 78`, `Community 80`, `Community 87`, `Community 91`, `Community 98`, `Community 99`, `Community 101`, `Community 106`, `Community 107`, `Community 112`, `Community 114`, `Community 126`, `Community 127`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 146 inferred relationships involving `Track` (e.g. with `save_cycle_inputs()` and `StormState`) actually correct?**
  _`Track` has 146 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.033307107264621036 - nodes in this community are weakly interconnected._