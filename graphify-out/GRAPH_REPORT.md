# Graph Report - anemoi  (2026-11-15)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 6806 nodes · 17460 edges · 249 communities (222 shown, 27 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 2548 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d890bb7b`
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
- Community 243
- Community 244
- Community 245
- Community 246
- Community 247
- Community 248

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
- `make_fix()` --calls--> `Fix`  [INFERRED]
  tests/test_streaming.py → src/anemoi/data/besttrack.py
- `make_fix()` --calls--> `Fix`  [INFERRED]
  tests/test_streaming.py → src/anemoi/data/besttrack.py
- `test_trained_basins_without_champions_is_the_atlantic()` --uses--> `ModelRegistry`  [INFERRED]
  tests/test_registry.py → src/anemoi/tracking/registry.py
- `test_internal_calibration_audit_route_reports_new_samples()` --uses--> `RealState`  [INFERRED]
  tests/test_api_real_state.py → src/anemoi/api/real_state.py
- `test_cache_round_trip_and_vector()` --uses--> `FetchTask`  [INFERRED]
  tests/test_steering.py → src/anemoi/data/gridded_cache.py

## Import Cycles
- None detected.

## Communities (249 total, 27 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (39): augment_track(), emulate_working_track(), WorkingTrackNoise, sanitize_field_pixels(), filter_tracks(), require_meta(), steering_meta(), displacement_nm() (+31 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (55): Fix, Track, steering_meta_digest(), generate_track(), build_live_cnn_x(), build_live_gnn_x(), build_live_lstm_x(), build_live_pinn_x() (+47 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (88): ApiError, apiFetch(), getActivePin(), getArchitecture(), getCalibration(), getCycle(), getDrift(), getDriftAll() (+80 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (54): svelte@^5.57.1, Props, Section, SectionPage, { sections }, height, motionClass, Props (+46 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (40): cmd_ablation(), cmd_adeck_fetch(), cmd_atcf_archive(), cmd_cache_localize(), cmd_consistency_distill(), cmd_drift_reference_fit(), cmd_era5_cache(), cmd_gdas_cache() (+32 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (43): GriddedFields, steering_flow(), cache_path(), _decode_cached_fields(), FetchCacheReport, FetchTask, load_cached_fields(), run_fetch_cache() (+35 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (41): _baseline_inputs(), _empty_report(), _fake_checkpoint_store(), _fake_curriculum_run(), _hurdat2_storm(), make_args(), make_track(), _retrain_check_args() (+33 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (44): assert_not_operational(), get(), operational_sources(), _operational_substitute(), OperationalUseError, Role, used_by(), _attributes() (+36 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (38): experiment_name(), cmd_train(), latest_final_season(), arch_params_tag(), baseline_beaten(), basin_input_tags(), build_run_tags(), candidate_tags() (+30 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (56): at(), calendarValue, hour, hourAllowed, inRange(), maxValue, minValue, onDateChange() (+48 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (39): _decode_one_sonde(), DropsondeFetchError, DropsondeProfile, fetch_and_parse_dropsonde_mission(), fetch_dropsonde_mission_tarball(), _ftp_connect(), list_dropsonde_missions(), _mask_missing() (+31 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (29): DeterministicForecast, fusion_weights(), basin_inputs(), steering_inputs(), _build_live_context(), _build_live_x(), build_real_deterministic_fn(), deterministic_fn() (+21 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (38): fetch_era5t_one(), audit_one(), audit_run(), _AuditPlan, _era5t_fetcher(), fetch(), _fix_from_dict(), _fix_to_dict() (+30 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (52): svelte-sonner@^1.2.3, ModelCatalog, BY_ARCHITECTURE, BY_SLUG, FUNCTIONAL_COLORS, FUSION_COLOR, GOD_ORDER, GODS (+44 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (34): cycle_inputs_prefix(), cycle_key(), CycleHistory, _get_text(), list_cycle_labels(), load_cycle_result(), load_drift_live(), _put_text() (+26 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (7): cycle_payload_out(), RealState, deterministic(), ensemble(), live_fields(), RealStormState, CycleOutput

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (37): build_derived_schedule(), build_schedule(), _latent_task(), Mode, OrchestrationResult, ResourceProfile, run_schedule(), RunOutcome (+29 more)

### Community 17 - "Community 17"
Cohesion: 0.05
Nodes (34): _crop_variable(), fetch_real_satellite_crop(), _find_real_scan(), GoesFetchError, _lazy_open(), _list_scan_keys(), _nearest_scan_key(), _parse_scan_start() (+26 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (39): climatological_ensemble(), build_cone(), build_products(), climatological_cone_nm(), cone_radius_from_spread(), ConeSegment, deterministic_center(), EnsembleMember (+31 more)

### Community 19 - "Community 19"
Cohesion: 0.06
Nodes (16): retrain_job_out(), get_state(), require_api_key(), state_dependency(), get_custom_redoc_html(), create_app(), _debug_last_deterministic_error(), redoc_html() (+8 more)

### Community 20 - "Community 20"
Cohesion: 0.06
Nodes (49): AppAuth, buildAuth(), getAuth(), verifyApiKey(), CYCLE_STEP, cycleInstanceId(), CycleParams, CycleWorkflow (+41 more)

### Community 21 - "Community 21"
Cohesion: 0.05
Nodes (40): cycle_products_out(), cycle_result_out(), model_version_out(), provenance_out(), get_active_pin(), get_model_architecture(), get_model_registry(), list_registry() (+32 more)

### Community 22 - "Community 22"
Cohesion: 0.07
Nodes (26): train_gnn_stage_streaming(), _train_candidate_lstm_streaming(), build_x(), track_input(), train_lstm_stage_streaming(), build_x(), iter_dataset_in_batches(), make_dataloader() (+18 more)

### Community 23 - "Community 23"
Cohesion: 0.04
Nodes (25): stage_a(), stage_b(), test_both_stages_label_from_final_besttrack(), test_final_besttrack_cannot_be_a_stage_input(), test_stage_a_uses_era5_and_stage_b_uses_gdas(), test_stage_b_cannot_read_a_pretrain_only_source(), test_stage_b_learning_rate_is_lower_than_stage_a(), _RecordingStore (+17 more)

### Community 24 - "Community 24"
Cohesion: 0.09
Nodes (29): assert_deployable(), Curriculum, CurriculumError, CurriculumRun, StageResult, run_cnn_curriculum(), run_diffusion_curriculum(), run_gnn_curriculum() (+21 more)

### Community 25 - "Community 25"
Cohesion: 0.06
Nodes (33): svelte-guard@^1.1.1, authHandle(), guards, handle, DEFAULT_AFTER_LOGIN, loginHref(), safeNext(), Auth (+25 more)

### Community 26 - "Community 26"
Cohesion: 0.07
Nodes (33): archive_key(), ArchiveClient, build_fetch_tasks(), filter_tracks_by_min_valid_time(), _memo_enabled(), shard_tracks(), sync_cache_to_archive(), SyncReport (+25 more)

### Community 27 - "Community 27"
Cohesion: 0.07
Nodes (30): check_run(), CycleConflict, _existing_source(), InFlight, operator_ids(), RunRequest, stored_source(), RunInfo (+22 more)

### Community 28 - "Community 28"
Cohesion: 0.09
Nodes (27): Flavor, ModelVersion, Stage, test_a_basin_is_in_distribution_once_every_served_model_is_verified_in_it(), _champions(), test_a_basin_is_served_once_every_champion_is_verified_in_it(), _reconcile_args(), test_registry_reconcile_dry_run_reports_without_transitioning() (+19 more)

### Community 29 - "Community 29"
Cohesion: 0.05
Nodes (43): FixOut, IntensityPercentiles, TrackPointOut, colorFor(), god(), bounds, colors, coneFeatures (+35 more)

### Community 30 - "Community 30"
Cohesion: 0.05
Nodes (45): SourceOut, byUse(), hasUnknownEntry(), MODEL_NAMES, MODELS, ORDER, readersOf(), SOURCE_NAMES (+37 more)

### Community 31 - "Community 31"
Cohesion: 0.06
Nodes (26): absolute_pairs(), basin_key(), basin_value(), is_basin_key(), key_basin(), per_basin_scores(), sample_counts(), scored_basins() (+18 more)

### Community 32 - "Community 32"
Cohesion: 0.08
Nodes (30): invalidated_by(), evaluate_all(), expand_jobs(), nightly_latent(), on_data_volume(), on_drift(), on_latent_desync(), on_skew() (+22 more)

### Community 33 - "Community 33"
Cohesion: 0.07
Nodes (30): batch_graph(), build_gnn_samples(), build_mesh_topology(), gnn_input(), GnnStageSamples, MeshTopology, _node_features(), _standardize_x() (+22 more)

### Community 34 - "Community 34"
Cohesion: 0.06
Nodes (30): Archive, archives_for(), describe(), fetch_latest_hurdat2(), last_season(), latest_name(), manifest_path(), as_issued() (+22 more)

### Community 35 - "Community 35"
Cohesion: 0.08
Nodes (28): build_cnn(), encode(), forward(), __init__(), build_cnn_samples(), cnn_input(), CnnStageSamples, _standardize_cnn_x() (+20 more)

### Community 36 - "Community 36"
Cohesion: 0.06
Nodes (23): @lucide/svelte@^1.71.0, sveltekit-superforms@^2.31.0, authClient, { form }, Props, { form }, Props, errorMsg (+15 more)

### Community 37 - "Community 37"
Cohesion: 0.12
Nodes (30): cmd_cycle(), deterministic(), run_cycle(), plan_cycle(), deterministic_fn(), good_ensemble(), make_fix(), test_a_pacific_climatological_ensemble_is_drawn_from_pacific_radii() (+22 more)

### Community 38 - "Community 38"
Cohesion: 0.07
Nodes (31): _builders(), cache_all_fixes(), cache_steering(), _curriculum_tracks(), _FakeS3Client, _fields(), _forward(), make_track() (+23 more)

### Community 39 - "Community 39"
Cohesion: 0.07
Nodes (23): client(), _FakeCycleOutput, _fresh_real_state(), hurdat2_file(), _make_deterministic_forecast(), _make_storm_state(), _memory_store(), _MemoryS3Client (+15 more)

### Community 40 - "Community 40"
Cohesion: 0.08
Nodes (29): adeck_name(), adeck_path(), adeck_urls(), CachedAdecks, _check_adeck(), fetch_adecks(), file_record(), read_adeck() (+21 more)

### Community 41 - "Community 41"
Cohesion: 0.06
Nodes (18): archived_tcvitals(), _get_text(), _load_recent(), _Boto3Client, CheckpointStore, require_boto3(), _StorageClient, store() (+10 more)

### Community 42 - "Community 42"
Cohesion: 0.07
Nodes (22): _candidate_and_true_absolute(), _disp_to_abs_batch(), _freeze_pinn_trunk(), PinnStageSamples, train_pinn_stage(), train_pinn_stage_streaming(), forward_batch(), cache_all_fixes() (+14 more)

### Community 43 - "Community 43"
Cohesion: 0.11
Nodes (24): case_errors(), compared_members(), homogeneous_mask(), _limiting(), _mean(), Member, MemberScore, _paired() (+16 more)

### Community 44 - "Community 44"
Cohesion: 0.09
Nodes (26): basin_tags(), by_basin(), complete_run(), _forecasts(), metric_set(), test_a_basin_is_verified_when_the_model_beats_persistence_there(), test_a_basin_validated_but_never_trained_on_is_not_verified(), test_a_candidate_that_loses_a_verified_basin_is_refused() (+18 more)

### Community 45 - "Community 45"
Cohesion: 0.10
Nodes (19): Adeck, storm_basin(), _displacement(), _join(), _json_rows(), _mean_or_none(), _notes(), persistence_members() (+11 more)

### Community 46 - "Community 46"
Cohesion: 0.09
Nodes (24): latent_signature(), RegistryError, _champions_tagged(), full_set(), register_group1(), _stage_all(), test_a_basin_counts_only_when_every_champion_trained_on_it(), test_a_champion_without_the_tag_counts_as_atlantic_only() (+16 more)

### Community 47 - "Community 47"
Cohesion: 0.09
Nodes (27): ExecutionMode, Task, fake_load_run_artifacts(), _FakeJointLatents, runner(), fake_extract_joint_latents(), make_fake(), test_a_failing_model_is_reported_not_raised() (+19 more)

### Community 48 - "Community 48"
Cohesion: 0.09
Nodes (20): _aligned(), assemble_validation_forecasts(), scored(), BaselineBacktestError, collect_validation_forecasts(), dump_validation_forecasts(), format_forecast_check(), group1_versions_of() (+12 more)

### Community 49 - "Community 49"
Cohesion: 0.05
Nodes (41): devDependencies, cn@^0.3.3, @fontsource-variable/geist@^5.3.0, @fontsource-variable/geist-mono@^5.3.0, @fontsource-variable/inter@^5.3.0, formsnap@^2.0.1, layerchart@^2.5.1, mode-watcher@^1.1.0 (+33 more)

### Community 50 - "Community 50"
Cohesion: 0.08
Nodes (19): _check_basin(), _created_date(), creation_day(), _declared_length(), decode_ohc(), detect_format(), expected_coordinates(), fetch_ohc_file() (+11 more)

### Community 51 - "Community 51"
Cohesion: 0.07
Nodes (23): area_mean(), compare_potential_intensity_estimates(), compute_environment_features(), deep_layer_shear(), integrated_vapor_transport(), potential_intensity(), relative_vorticity_850(), generate_fields() (+15 more)

### Community 52 - "Community 52"
Cohesion: 0.08
Nodes (22): technique_member(), techniques_to_read(), TechniqueSpec, adeck_text(), adecks(), archive(), archive_text(), cases() (+14 more)

### Community 53 - "Community 53"
Cohesion: 0.07
Nodes (16): App, Locals, Platform, clearPreferenceStorage(), consent, CONSENT_KEY, ConsentCategory, ConsentChoice (+8 more)

### Community 54 - "Community 54"
Cohesion: 0.09
Nodes (17): ChecksumCheck, Fetcher, FetchError, FetchResult, ingest_cycle_inputs(), ingest_one(), IngestionOutcome, IngestionRecord (+9 more)

### Community 55 - "Community 55"
Cohesion: 0.07
Nodes (39): dependencies, arktype@^2.2.7, better-auth@^1.7.7, @better-auth/passkey@^1.7.7, bits-ui@^2.20.6, clsx@^2.1.1, d3-polygon@^3.0.1, d3-scale@^4.0.2 (+31 more)

### Community 56 - "Community 56"
Cohesion: 0.10
Nodes (28): assert_input_safe(), emulate_working_fix(), recalibrate_from_pairs(), TrackQuality, _latlon(), make_fix(), make_track(), test_assert_input_safe_allows_working_quality() (+20 more)

### Community 57 - "Community 57"
Cohesion: 0.11
Nodes (23): AblationCell, AblationReport, build_samples(), run_capacity_ablation(), train_cell(), NoiseSensitivityResult, run_noise_sensitivity(), _cell() (+15 more)

### Community 58 - "Community 58"
Cohesion: 0.08
Nodes (21): format_report(), recommend_extra_conditioning(), run_spread_backtest(), SpreadBacktestError, SpreadBacktestReport, _fake_val(), _FakeS3Client, _lc() (+13 more)

### Community 59 - "Community 59"
Cohesion: 0.08
Nodes (17): AdeckFetchReport, _check_official_errors(), _fetch_one(), _get(), read_cached_official_errors(), _get_bytes(), NotPublished, OfficialErrors (+9 more)

### Community 60 - "Community 60"
Cohesion: 0.10
Nodes (19): audit_cycle(), _CountingClient, _FakeClient, _fix(), _result(), test_a_cycle_stored_before_the_ri_interval_still_loads(), test_a_sample_persisted_before_ensemble_size_was_tracked_still_loads(), test_audit_cycle_leaves_cone_hit_none_when_a_lead_has_no_cone_segment() (+11 more)

### Community 61 - "Community 61"
Cohesion: 0.12
Nodes (22): AvailabilityOracle, earliest_ready_time(), LatencyOracle, resolve_cycle_inputs(), _valid_time_for(), test_all_nwp_missing_marks_the_required_input_unavailable(), test_cycle_is_not_ready_before_vitals_arrive(), test_cycle_is_ready_once_vitals_and_staged_nwp_are_in() (+14 more)

### Community 62 - "Community 62"
Cohesion: 0.10
Nodes (20): advisory_time(), floor_synoptic(), is_synoptic(), next_synoptic(), NWPUnavailableError, require_synoptic(), _require_utc(), select_nwp_cycle() (+12 more)

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
Cohesion: 0.11
Nodes (25): brier_score(), aggregate_by_storm(), beat_rate(), diebold_mariano(), pair(), test_aggregation_collapses_fixes_to_one_case_per_storm(), test_aggregation_keeps_the_two_arrays_aligned(), test_aggregation_rejects_an_empty_sample() (+17 more)

### Community 66 - "Community 66"
Cohesion: 0.10
Nodes (22): run_fetch_cache(), make_fields(), make_track(), test_default_fetch_fn_wires_a_shared_session(), fake_fetch_gdas_grib2_fields(), fake_gdas_to_gridded_fields(), test_fetch_one_fetches_exactly_one_real_sample(), fake_gdas_to_gridded_fields() (+14 more)

### Community 67 - "Community 67"
Cohesion: 0.11
Nodes (22): _decode(), files(), local(), _ohc(), _row_col(), server(), test_a_blank_file_is_rejected(), test_a_file_made_later_than_its_name_says_is_rejected() (+14 more)

### Community 68 - "Community 68"
Cohesion: 0.09
Nodes (23): _crop_box(), era5_to_gridded_fields(), crop(), crop_levels(), crop(), _saturation_vapor_pressure_hpa_array(), _specific_humidity_to_rh_pct(), _global_grid_with_marker() (+15 more)

### Community 69 - "Community 69"
Cohesion: 0.12
Nodes (17): disc_mean(), fetch_lead_flow(), group_by_time(), lead_flow(), LeadFlow, load_steering(), run_steering_cache(), fetch() (+9 more)

### Community 70 - "Community 70"
Cohesion: 0.11
Nodes (21): Hurdat2Error, _parse_data_row(), _parse_header(), parse_hurdat2(), parse_hurdat2_statuses(), _parse_latlon(), _storm_rows(), test_entry_count_mismatch_raises() (+13 more)

### Community 71 - "Community 71"
Cohesion: 0.11
Nodes (20): fetch_current_storm_ids(), fetch_current_storms(), fetch_live_track(), fetch_live_tracks(), fetch_one(), _get(), LiveAtcfError, test_fetch_current_storm_ids_parses_and_uppercases() (+12 more)

### Community 72 - "Community 72"
Cohesion: 0.11
Nodes (21): cycle_date(), ohc_global(), ohc_url(), select_file(), sshae_baseline(), target_creation_day(), _full_archive(), test_a_blank_run_longer_than_the_window_leaves_na_unavailable() (+13 more)

### Community 73 - "Community 73"
Cohesion: 0.14
Nodes (20): evaluate_promotion(), PromotionError, TestSetBudget, complete_run(), good_metrics(), test_budget_allows_a_limited_number_of_looks(), test_budget_exhaustion_raises(), test_budget_requires_a_justification() (+12 more)

### Community 74 - "Community 74"
Cohesion: 0.11
Nodes (22): boundaries_for_flavor(), _fake_checkpoint_store(), make_track(), test_a_run_on_two_basins_scores_each_on_its_own(), test_boundaries_for_flavor_picks_default_for_era5_pretrain(), test_boundaries_for_flavor_picks_stage_b_for_gdas_finetune(), test_build_stage_samples_drops_a_track_too_short_for_any_lead(), test_build_stage_samples_full_length_track_covers_every_lead() (+14 more)

### Community 75 - "Community 75"
Cohesion: 0.09
Nodes (18): QUICK, API, DEVELOP, PHONE, SourceRow, SOURCES, SOURCES_BEFORE_USED_BY, SOURCES_REWIRED (+10 more)

### Community 76 - "Community 76"
Cohesion: 0.06
Nodes (28): AsyncReturnType, Expand, ExtractGenericViewableContent, GenericItem, GenericSelectorOption, GenericSnippetProps, GenericViewableContent, InheritedSnippetProps (+20 more)

### Community 77 - "Community 77"
Cohesion: 0.14
Nodes (15): audit_due(), SkewMonitor, SkewReport, sample(), test_audit_becomes_due_once_era5t_lands(), test_audit_is_not_due_immediately_after_the_cycle(), test_intensity_delta_is_signed_toward_the_operational_run(), test_intensity_skew_alone_can_raise_an_alert() (+7 more)

### Community 78 - "Community 78"
Cohesion: 0.08
Nodes (15): crps_ensemble(), _crps_rows(), crps_series(), ensemble_percentiles(), rank_histogram(), reliability(), spread_skill(), SpreadSkill (+7 more)

### Community 79 - "Community 79"
Cohesion: 0.06
Nodes (31): data, basins, stage_a, epochs, flavor, input_sources, label_source, learning_rate (+23 more)

### Community 80 - "Community 80"
Cohesion: 0.13
Nodes (21): storm_relative_sequence(), lr_factor(), test_a_short_stage_still_ends_on_the_floor(), test_config_values_are_validated(), test_cosine_decays_to_the_floor_on_the_last_update(), test_no_warmup_starts_at_the_peak(), test_warmup_rises_linearly_to_the_peak(), test_track_48h_threshold_is_rebaselined_against_the_gpra_record() (+13 more)

### Community 81 - "Community 81"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, env, GH_TOKEN, GRAPHIFY_VERSION, permissions, runs-on (+22 more)

### Community 82 - "Community 82"
Cohesion: 0.11
Nodes (13): bearing_deg(), bearings_deg(), cross_along_track_nm(), cross_along_track_nms(), haversine_nm(), km_to_nm(), nm_to_km(), offset_positions() (+5 more)

### Community 83 - "Community 83"
Cohesion: 0.12
Nodes (16): _FakeS3Client, _make_version(), _real_builder(), _register_like_training(), _store(), test_load_run_artifacts_rebuilds_pinns_candidate_and_env_stats(), test_load_run_artifacts_refuses_a_version_without_standardisation_stats(), test_load_run_artifacts_round_trips_a_real_training_runs_artifacts() (+8 more)

### Community 84 - "Community 84"
Cohesion: 0.08
Nodes (15): _expected_meta(), test_a_failed_time_is_reported_and_the_others_still_written(), fetch(), test_a_lost_race_with_no_file_appearing_raises_the_write_error(), test_cache_round_trip_and_vector(), test_disc_mean_is_symmetric_for_a_field_linear_in_longitude(), test_features_advect_with_the_flow_plus_beta_drift(), test_features_raise_where_there_is_no_flow() (+7 more)

### Community 85 - "Community 85"
Cohesion: 0.08
Nodes (29): @better-auth/api-key@^1.7.7, @types/node@^26.6.4, typescript@^5.9.3, wrangler@^4.147.0, @better-auth/api-key, @types/node, typescript, wrangler (+21 more)

### Community 86 - "Community 86"
Cohesion: 0.07
Nodes (23): rehype-slug@^6.0.0, rehype-stringify@^10.0.1, remark-gfm@^4.0.1, remark-parse@^11.0.0, remark-rehype@^11.1.2, unified@^11.0.5, unist-util-visit@^5.1.0, CONSOLE_ROOT (+15 more)

### Community 87 - "Community 87"
Cohesion: 0.07
Nodes (29): WithElementRef, ButtonClickEvent, PrimitiveAnchorAttributes, PrimitiveButtonAttributes, PrimitiveCanvasAttributes, PrimitiveDivAttributes, PrimitiveElementAttributes, PrimitiveFigureAttributes (+21 more)

### Community 88 - "Community 88"
Cohesion: 0.08
Nodes (19): apply_cold_wake(), cold_wake_sst_depression_c(), emanuel_potential_intensity(), inner_core_moisture(), _saturation_vapor_pressure_hpa(), _specific_humidity_kg_kg(), _radial_gradient_fields(), test_apply_cold_wake_depresses_sst_and_ohc_without_touching_other_fields() (+11 more)

### Community 89 - "Community 89"
Cohesion: 0.13
Nodes (18): assert_no_leakage(), assign_splits(), _earliest_season(), _latest_season(), LeakageError, _seasons(), Split, _split_for_season() (+10 more)

### Community 90 - "Community 90"
Cohesion: 0.10
Nodes (8): extra_input_conv(), ModelSpec, torch_available(), _cosine_schedule(), __getattr__(), pytest_collection_modifyitems(), test_require_torch_message_names_the_extra(), test_spec_output_dim_is_leads_times_outputs()

### Community 91 - "Community 91"
Cohesion: 0.12
Nodes (14): build_real_ensemble_fn(), InferenceEnsembleError, cache_current_fix(), _FakeS3Client, make_track(), _register(), _register_all_five_and_diffusion(), _store() (+6 more)

### Community 92 - "Community 92"
Cohesion: 0.07
Nodes (28): inputArgs, jobs, projectId, region, results, timeoutSeconds, assign, return (+20 more)

### Community 93 - "Community 93"
Cohesion: 0.08
Nodes (9): _FakeS3Config, test_checkpoint_store_push_failure_degrades_to_local_only(), test_checkpoint_store_push_mirrors_registry_json_after_every_save(), test_pull_failure_degrades_to_an_empty_registry(), test_pull_from_checkpoint_store_hydrates_a_missing_local_registry(), test_pull_is_a_noop_when_the_key_does_not_exist_remotely_yet(), test_pull_reconciles_with_durable_storage_even_when_local_already_exists(), test_register_persists_locally_and_durably_before_touching_mlflow() (+1 more)

### Community 94 - "Community 94"
Cohesion: 0.10
Nodes (14): _displacement_to_absolute(), _empty_samples(), _extract_for_tracks(), extract_joint_latents(), extract_validation_latents(), JointLatentBundle, JointLatentSamples, _require_group1() (+6 more)

### Community 95 - "Community 95"
Cohesion: 0.12
Nodes (13): DiffusionArtifacts, _standardize(), _standardize_y(), train_diffusion_stage(), _FakeS3Client, _make_samples(), test_a_longer_epoch_budget_never_returns_a_worse_val_loss(), test_early_stopping_halts_before_the_epoch_cap_on_a_real_overfitting_run() (+5 more)

### Community 96 - "Community 96"
Cohesion: 0.10
Nodes (14): initial_fix(), extrapolate_fix(), _MemoryS3, s3(), test_an_archive_storm_says_its_fix_is_the_final_best_track(), test_missing_vitals_are_extrapolated_and_estimated(), test_one_earlier_fix_is_persisted(), test_overrides_apply_on_top() (+6 more)

### Community 97 - "Community 97"
Cohesion: 0.11
Nodes (11): cache_nwp_lead_hours(), _claim_cache_dir(), _default_fetch_fn(), fetch(), fetch_one(), fetch_gdas_grib2_fields(), gdas_to_gridded_fields(), gfs_url() (+3 more)

### Community 98 - "Community 98"
Cohesion: 0.10
Nodes (16): http_get(), OhcFetchError, OhcNotPublished, OhcUnavailable, Archive, test_a_cut_off_reply_is_a_fetch_failure(), test_a_cut_off_transfer_raises_rather_than_reading_an_older_file(), test_a_fetch_failure_that_is_not_a_404_is_not_stepped_over() (+8 more)

### Community 99 - "Community 99"
Cohesion: 0.16
Nodes (13): cache_current_fix(), _FakeS3Client, make_track(), _register_real_version(), _store(), test_build_real_deterministic_fn_combines_all_four_real_models(), test_build_real_deterministic_fn_raises_with_no_registered_models(), test_build_real_deterministic_fn_uses_the_real_learned_fusion_with_all_five() (+5 more)

### Community 100 - "Community 100"
Cohesion: 0.13
Nodes (15): _all_tensors(), Architecture, _builder(), describe(), describe_cached(), _describe_cached(), hook(), _example_inputs() (+7 more)

### Community 101 - "Community 101"
Cohesion: 0.10
Nodes (12): color_for(), god(), Module, WindGod, test_every_god_color_is_distinct(), test_experiment_name_handles_fusion_without_raising(), test_experiment_names_are_the_god_slugs(), test_lookup_by_slug_and_by_architecture_agree() (+4 more)

### Community 102 - "Community 102"
Cohesion: 0.10
Nodes (5): ModelRegistry, test_run_cycle_picks_up_a_registry_change_mid_warm_lifetime(), test_a_champion_verified_nowhere_serves_no_basin_as_in_distribution(), test_no_champion_or_champions_from_before_the_tag_are_the_atlantic(), test_checkpoint_uri_persists_on_the_version_itself()

### Community 103 - "Community 103"
Cohesion: 0.16
Nodes (13): cache_all_fixes(), _FakeS3Client, make_fields(), make_track(), _task_for(), test_build_transformer_samples_empty_when_nothing_cached(), test_build_transformer_samples_rejects_a_cache_smaller_than_grid_size(), test_build_transformer_samples_trims_the_real_41x41_crop_to_grid_size() (+5 more)

### Community 104 - "Community 104"
Cohesion: 0.09
Nodes (19): CyclePlanOut, deadline, { plan }, Props, stageLabel, t0, totalMs, pollWhileVisible() (+11 more)

### Community 105 - "Community 105"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GH_TOKEN, IMPORTED_FROM, SOURCE_SHA, jobs, publish (+16 more)

### Community 106 - "Community 106"
Cohesion: 0.12
Nodes (12): _cron_run_offset_minutes(), _leaves(), _load(), test_a_config_change_redeploys_the_api(), test_both_images_copy_the_configs(), test_every_config_key_is_read_by_the_code(), test_every_config_parses_and_has_no_duplicate_keys(), test_every_image_build_is_smoke_tested_before_it_ships() (+4 more)

### Community 107 - "Community 107"
Cohesion: 0.15
Nodes (14): detect_feature_drift(), FeatureDrift, ValidationLossMonitor, reference(), test_a_recovery_resets_the_consecutive_count(), test_collapsed_variance_is_detected(), test_feature_count_mismatch_raises(), test_first_observation_only_sets_the_baseline() (+6 more)

### Community 108 - "Community 108"
Cohesion: 0.14
Nodes (15): _adeck_position(), pair_by_valid_time(), parse_bdeck(), _parse_latlon(), parse_tcvitals(), TcVitalsError, test_bdeck_malformed_line_raises(), test_bdeck_parses_best_track_rows_only() (+7 more)

### Community 109 - "Community 109"
Cohesion: 0.11
Nodes (11): fetch(), era5_deps_available(), fetch_grib2_messages(), gridded_deps_available(), open_era5(), open_era5_store(), require_era5_deps(), require_gdas_deps() (+3 more)

### Community 110 - "Community 110"
Cohesion: 0.14
Nodes (14): fetch_and_parse_ndbc(), fetch_ndbc_realtime2(), _get(), NdbcFetchError, NdbcObservation, parse_ndbc_realtime2(), test_a_row_with_the_wrong_column_count_is_skipped_not_fatal(), test_a_station_missing_wave_columns_still_parses() (+6 more)

### Community 111 - "Community 111"
Cohesion: 0.11
Nodes (12): basin_one_hot(), with_basin_channels(), with_basin_columns(), with_basin_vector(), build_transformer_samples(), _sanitized_channel_stack(), _standardize_x(), _standardize_y() (+4 more)

### Community 112 - "Community 112"
Cohesion: 0.08
Nodes (3): client(), test_more_members_than_the_ensemble_runs_is_refused_not_silently_capped(), test_sources_say_who_uses_each_one()

### Community 113 - "Community 113"
Cohesion: 0.08
Nodes (8): DELETE, GET, PATCH, POST, PUT, { data }, prerender, ssr

### Community 114 - "Community 114"
Cohesion: 0.09
Nodes (14): ArmResult, compare(), expand_patch_channels(), _renamed(), run_steering_spike(), has_steering(), track_errors_nm(), _cache_steering() (+6 more)

### Community 115 - "Community 115"
Cohesion: 0.14
Nodes (10): fetch_gefs_ensemble_grib2_fields(), fetch_gefs_member_grib2_fields(), _gefs_member_url(), _parse_grib2_index(), test_control_member_zero_uses_gec00_not_gep00(), test_fetch_gefs_ensemble_reads_multiple_real_distinct_members(), test_fetch_gefs_member_reads_the_real_noaa_archive(), test_member_out_of_range_raises() (+2 more)

### Community 116 - "Community 116"
Cohesion: 0.14
Nodes (15): calibrate(), forecast_motion_bearings(), observed_motion_bearings(), recurving_cases(), _centre(), _jitter(), _synthetic(), test_a_calibrated_ensemble_reads_as_calibrated() (+7 more)

### Community 117 - "Community 117"
Cohesion: 0.12
Nodes (13): distill_consistency_model(), step_loss(), _pseudo_huber(), _fake_samples(), _lc(), _report(), _stats(), teacher_and_data() (+5 more)

### Community 118 - "Community 118"
Cohesion: 0.13
Nodes (10): _download(), fetch_oisst_sst(), require_sst_deps(), sst_at(), SstFetchError, _small_grid(), test_fetch_oisst_sst_reads_real_recent_data(), test_sst_at_finds_the_nearest_cell() (+2 more)

### Community 119 - "Community 119"
Cohesion: 0.16
Nodes (16): _lon_close(), ref_bearing(), ref_crps(), ref_displacement(), ref_haversine(), ref_offset(), rng(), test_array_geodesy_matches_the_per_point_formulas() (+8 more)

### Community 120 - "Community 120"
Cohesion: 0.11
Nodes (17): total_budget(), test_a_cycle_started_at_the_timeout_still_clears_the_margin(), test_core_is_ready_before_spread(), test_cycle_starts_when_vitals_land_not_at_synoptic_time(), test_describe_mentions_the_nwp_lag(), test_late_start_sheds_ensemble_load_to_hold_the_advisory(), test_late_vitals_triggers_estimation_at_the_timeout(), test_load_shedding_can_be_disabled_and_then_the_deadline_is_missed() (+9 more)

### Community 121 - "Community 121"
Cohesion: 0.12
Nodes (13): build_diffusion(), __init__(), _consistency_model(), test_cnn_is_resolution_agnostic(), test_consistency_accepts_extra_conditioning(), test_consistency_boundary_condition_is_exact_at_step_zero(), test_consistency_multistep_sampling_matches_one_step_shape_and_is_deterministic(), test_consistency_one_step_sampling_produces_distinct_members() (+5 more)

### Community 122 - "Community 122"
Cohesion: 0.14
Nodes (11): _files(), localize_cache(), LocalizeReport, _raise(), _cache(), test_a_directory_that_cant_be_listed_fails_the_copy(), test_a_missing_source_raises(), test_a_rerun_only_fills_gaps() (+3 more)

### Community 123 - "Community 123"
Cohesion: 0.14
Nodes (11): require_torch(), coriolis_parameter(), physics_residuals(), compile_model(), test_compile_model_does_not_raise_on_cpu(), test_compile_model_rejects_non_module_input(), test_compile_model_skips_compilation_on_mps(), test_get_device_falls_back_to_cpu_when_no_gpu_backend_is_available() (+3 more)

### Community 125 - "Community 125"
Cohesion: 0.14
Nodes (15): _default_fetch_fn(), run_fetch_cache(), make_fields(), test_build_fetch_tasks_covers_every_fix_across_tracks(), test_load_cached_fields_rejects_a_missing_file(), test_run_fetch_cache_actually_runs_fetches_concurrently(), slow_fetch(), test_run_fetch_cache_can_force_refetch_with_skip_existing_false() (+7 more)

### Community 126 - "Community 126"
Cohesion: 0.12
Nodes (14): __init__(), extra_input_linear(), __init__(), build_gnn(), encode(), forward(), __init__(), build_pinn() (+6 more)

### Community 128 - "Community 128"
Cohesion: 0.10
Nodes (20): PROJECT_NUMBER, PROJECT_PAT, types, jobs, sync, name, on, issues (+12 more)

### Community 129 - "Community 129"
Cohesion: 0.13
Nodes (8): calibration_out(), drift_report_out(), skew_report_out(), calibration(), drift(), drift_all(), skew(), DriftReport

### Community 130 - "Community 130"
Cohesion: 0.12
Nodes (10): _budgets(), CycleAbandoned, derive_vitals_timeout(), plan_day(), _schedule_stages(), ScheduledStage, Stage, StageBudget (+2 more)

### Community 131 - "Community 131"
Cohesion: 0.21
Nodes (6): freeCycleLabel(), label(), runFreshCycle(), signIn(), cases, @playwright/test

### Community 132 - "Community 132"
Cohesion: 0.16
Nodes (17): answerRuns(), chip(), context(), cycleFor(), dateButton(), expectForm(), expectShowing(), fixture (+9 more)

### Community 133 - "Community 133"
Cohesion: 0.10
Nodes (7): client(), test_docs_route_is_unaffected(), test_sources_role_is_the_role_enum_in_the_openapi_schema(), test_sources_used_by_is_documented_in_the_openapi_schema(), test_theme_http_method_colors_are_distinct(), test_theme_never_uses_a_god_color(), _walk()

### Community 134 - "Community 134"
Cohesion: 0.18
Nodes (10): DriftError, ReferenceDistribution, reference_from_json(), reference_to_json(), save_reference(), test_drift_report_detects_real_drift_once_enough_samples_are_collected(), test_drift_report_is_honest_zero_for_a_model_that_never_contributed(), test_reference_must_be_the_stage_b_distribution() (+2 more)

### Community 135 - "Community 135"
Cohesion: 0.14
Nodes (9): load_reference(), test_drift_reference_fit_fits_and_persists_from_real_cached_fields(), _FakeClient, _make_reference(), test_durable_round_trip_via_a_shared_checkpoint_store(), test_json_round_trips_a_real_reference_exactly(), test_load_reference_degrades_honestly_when_the_store_is_unreachable(), test_load_reference_returns_none_when_nothing_was_ever_fit() (+1 more)

### Community 136 - "Community 136"
Cohesion: 0.17
Nodes (13): _fetcher(), fetch(), _keys(), test_a_storm_is_still_archived_for_a_few_days_after_it_leaves_the_index(), test_a_storm_seen_on_new_years_eve_is_still_followed_on_new_years_day(), test_an_unreachable_index_raises_so_the_caller_reports_it(), test_archived_tcvitals_keeps_every_revision_once_in_issue_order(), test_every_file_is_archived_verbatim_for_every_basin() (+5 more)

### Community 137 - "Community 137"
Cohesion: 0.21
Nodes (10): accessed(), _check_type(), ConfigError, fixed(), get(), get_list(), _load(), _names() (+2 more)

### Community 138 - "Community 138"
Cohesion: 0.15
Nodes (12): generate_season(), make_storm_spec(), StormSpec, test_archive_spans_the_requested_seasons(), test_fields_have_matching_shapes_and_carry_a_flavor(), test_fixes_are_six_hourly_and_synoptic(), test_gdas_fields_are_noisier_than_era5(), test_generated_tracks_are_final_quality() (+4 more)

### Community 139 - "Community 139"
Cohesion: 0.11
Nodes (7): _FakeMlflowModelVersion, _mlflow_client_that_registers_and_transitions(), create_model_version(), test_mlflow_mirror_skips_create_registered_model_if_it_already_exists(), create_model_version(), test_mlflow_transition_also_mirrors_the_archived_incumbent(), create_model_version()

### Community 140 - "Community 140"
Cohesion: 0.17
Nodes (7): mlflow_client_from_env(), test_an_unreachable_server_is_skipped_fast(), test_builds_a_real_client_when_tracking_uri_is_set(), test_fail_fast_settings_never_override_explicit_ones(), test_mlflow_client_from_env_can_actually_reach_the_configured_server(), test_returns_none_when_tracking_uri_is_unset(), test_returns_none_without_mlflow_installed()

### Community 141 - "Community 141"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 142 - "Community 142"
Cohesion: 0.11
Nodes (17): assignees, description, label, options, placeholder, value, body, attributes (+9 more)

### Community 143 - "Community 143"
Cohesion: 0.12
Nodes (8): god_out(), model_catalog(), source_out(), health(), models(), sources(), DataSource, pretrain_only_sources()

### Community 144 - "Community 144"
Cohesion: 0.15
Nodes (6): CloudflareAccessRequestHeaderProvider, test_headers_are_actually_applied_by_mlflows_own_resolution(), test_in_context_false_when_neither_var_set(), test_in_context_false_when_only_client_id_set(), test_in_context_true_and_correct_headers_when_both_set(), test_registered_as_a_real_mlflow_plugin_via_entry_points()

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
Cohesion: 0.18
Nodes (7): get_cycle(), get_storm(), list_storms(), _overrides(), run_cycle(), _served_basins(), _storm_summary()

### Community 149 - "Community 149"
Cohesion: 0.15
Nodes (9): config_copy(), edit(), _image_layout(), _run(), test_a_missing_config_dir_is_refused(), test_an_image_without_configs_fails_at_import_and_says_why(), test_an_invalid_config_is_refused_with_a_clear_message(), test_edited_values_take_effect_at_runtime() (+1 more)

### Community 150 - "Community 150"
Cohesion: 0.23
Nodes (10): archive_atcf(), ArchiveReport, currentstorms_key(), _digest(), _put_bytes(), snapshot_key(), _stored_digests(), _write_if_new() (+2 more)

### Community 151 - "Community 151"
Cohesion: 0.18
Nodes (7): assert_flavor(), FeatureSet, FlavorMismatchError, Normalizer, test_flavor_guard_rejects_a_pretrain_feature_on_the_operational_path(), test_normalizer_refuses_to_fit_across_flavors(), test_normalizer_rejects_the_wrong_flavor_at_apply_time()

### Community 152 - "Community 152"
Cohesion: 0.17
Nodes (9): _bilinear(), _lattice_index(), ohc_at(), OhcField, place(), test_bilinear_between_nodes(), test_bilinear_is_exact_at_a_node_on_every_source(), test_bilinear_needs_all_four_corners() (+1 more)

### Community 153 - "Community 153"
Cohesion: 0.26
Nodes (9): NoiseSensitivityReport, _result(), test_is_load_bearing_above_threshold(), test_is_not_load_bearing_below_threshold(), test_relative_change_is_zero_when_losses_match(), test_relative_change_rejects_nonpositive_default_loss(), test_relative_change_sign_matches_direction_of_the_move(), test_run_noise_sensitivity_covers_both_candidates_on_a_small_synthetic_archive() (+1 more)

### Community 154 - "Community 154"
Cohesion: 0.16
Nodes (8): al_2021_2022(), compare(), open_ocean(), parse_ships(), sample_days(), ShipsCase, test_sohc_equals_bilinear_ohc_on_the_file_named_for_the_day_before(), test_compare_refuses_arms_on_different_windows_and_pairs_the_rest()

### Community 155 - "Community 155"
Cohesion: 0.12
Nodes (16): with, build-args, cache-from, cache-to, context, file, load, password (+8 more)

### Community 156 - "Community 156"
Cohesion: 0.12
Nodes (15): jobs, lint-and-validate, name, permissions, runs-on, steps, name, on (+7 more)

### Community 157 - "Community 157"
Cohesion: 0.19
Nodes (6): _FakeS3Client, _make_samples(), test_run_fusion_curriculum_uploads_a_checkpoint_and_registers_stage_b(), test_train_fusion_stage_reduces_loss_and_produces_val_metrics(), test_train_fusion_stage_rejects_a_val_set_built_with_a_different_model_count(), test_train_fusion_stage_rejects_empty_samples()

### Community 158 - "Community 158"
Cohesion: 0.13
Nodes (15): scripts, build, cf:deploy, check, check:errors, check:warnings, check:watch, dev (+7 more)

### Community 159 - "Community 159"
Cohesion: 0.19
Nodes (12): loading, onInput(), open, query, results, bodyById, buildIndex(), excerptAround() (+4 more)

### Community 160 - "Community 160"
Cohesion: 0.13
Nodes (15): env, environment, if, name, needs, permissions, runs-on, timeout-minutes (+7 more)

### Community 161 - "Community 161"
Cohesion: 0.21
Nodes (6): config_dir(), build_info(), _build_info_path(), config_digest(), git_sha(), summary()

### Community 162 - "Community 162"
Cohesion: 0.14
Nodes (3): CycleInputs, InputStatus, NWPCycleSelection

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
Cohesion: 0.16
Nodes (6): HomogeneousRow, BaselineReport, _fmt(), format_report(), _json_safe(), test_the_report_serialises_as_strict_json_and_prints_a_table()

### Community 168 - "Community 168"
Cohesion: 0.17
Nodes (12): IdTokenClaims, JwtClaims, OidcAddressClaim, OidcStandardClaims, UserProfile, Mandatory, RFC-3966, RFC-4627 (+4 more)

### Community 169 - "Community 169"
Cohesion: 0.15
Nodes (12): name, runs-on, timeout-minutes, concurrency, cancel-in-progress, group, jobs, build (+4 more)

### Community 170 - "Community 170"
Cohesion: 0.18
Nodes (10): _get_real_state(), _stage_group1_and_derived(), test_calibration_report_is_honest_empty_with_no_samples(), test_calibration_report_reflects_persisted_samples(), test_drift_report_is_honest_zero_when_no_reference_has_been_fit(), test_pending_retrain_jobs_detects_a_real_latent_desync(), test_pending_retrain_jobs_is_empty_for_a_coherent_registry(), test_pending_retrain_jobs_route_serves_a_real_latent_desync() (+2 more)

### Community 171 - "Community 171"
Cohesion: 0.23
Nodes (11): max, target, budgets, reduced, standard, max, target, assembly (+3 more)

### Community 172 - "Community 172"
Cohesion: 0.17
Nodes (4): local, notes, problems, remote

### Community 173 - "Community 173"
Cohesion: 0.21
Nodes (7): client(), test_a_registered_versions_arch_params_are_used(), test_a_version_that_reads_steering_is_described(), test_a_version_without_arch_params_is_described_from_defaults(), test_every_model_runs_its_example_input_and_reports_its_layers(), test_the_gnn_is_fed_the_real_lattice(), test_unknown_models_and_versions_are_404()

### Community 174 - "Community 174"
Cohesion: 0.17
Nodes (11): concurrency, cancel-in-progress, group, jobs, test-api, name, if, name (+3 more)

### Community 175 - "Community 175"
Cohesion: 0.17
Nodes (12): with, cache, cache-dependency-path, enable-cache, fetch-depth, if-no-files-found, include-hidden-files, name (+4 more)

### Community 176 - "Community 176"
Cohesion: 0.18
Nodes (5): offset_position(), ConeOutcome, served_cone_outcome(), test_served_cone_scores_what_build_cone_actually_serves(), ensemble()

### Community 177 - "Community 177"
Cohesion: 0.17
Nodes (6): test_mlflow_failure_degrades_to_local_only(), __getattr__(), test_mlflow_mirror_is_skipped_without_a_checkpoint_uri(), __getattr__(), test_mlflow_mirror_registers_model_then_version_with_a_real_source_uri(), create_model_version()

### Community 178 - "Community 178"
Cohesion: 0.24
Nodes (4): transformer_optim(), TransformerOptim, TransformerOptimizer, test_the_optimiser_caps_the_stage_rate_warms_up_and_clips()

### Community 179 - "Community 179"
Cohesion: 0.18
Nodes (11): cycle, advisory_margin_minutes, advisory_offset_minutes, allow_estimated_vitals, allow_load_shedding, max_nwp_lag_hours, nominal_vitals_offset_minutes, nwp_lag_hours (+3 more)

### Community 180 - "Community 180"
Cohesion: 0.24
Nodes (4): BasinChoice, test_a_cycle_reads_the_file_made_two_days_before(), test_the_flag_is_relative_to_the_baseline(), test_the_flag_on_real_files()

### Community 181 - "Community 181"
Cohesion: 0.27
Nodes (8): _fields(), _run(), test_a_cache_dir_holds_one_lead(), fetch_one(), test_no_nwp_at_all_is_flagged(), test_the_cycle_reports_the_nwp_it_really_used(), fetch_one(), test_training_records_the_lead_it_trained_on()

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
Cohesion: 0.24
Nodes (8): build_consistency_model(), consistency_fn(), __init__(), sample(), skip_coeffs(), test_evaluate_step_budget_tradeoff_reports_insufficient_data_below_min_cases(), test_evaluate_step_budget_tradeoff_runs_end_to_end(), test_consistency_rejects_a_non_positive_step_count()

### Community 188 - "Community 188"
Cohesion: 0.22
Nodes (8): build_lstm(), encode(), forward(), __init__(), test_gru_variant_builds(), test_invalid_cell_is_rejected(), test_lstm_shapes_and_latent(), candidate_model()

### Community 189 - "Community 189"
Cohesion: 0.22
Nodes (9): run, test-console, working-directory, defaults, if, name, needs, runs-on (+1 more)

### Community 190 - "Community 190"
Cohesion: 0.22
Nodes (9): BASE_SHA, BEFORE_SHA, DISPATCH_API, DISPATCH_CONSOLE, EVENT, EXPECT_GIT_SHA, HEAD_SHA, REF (+1 more)

### Community 191 - "Community 191"
Cohesion: 0.25
Nodes (7): build_transformer(), encode(), forward(), __init__(), extra_channel_patch(), test_transformer_emits_track_and_regime(), test_transformer_rejects_an_indivisible_grid()

### Community 192 - "Community 192"
Cohesion: 0.25
Nodes (8): 12, 120, 24, 36, 48, 72, 96, climatological_cone_nm

### Community 193 - "Community 193"
Cohesion: 0.25
Nodes (8): CP, 12, 120, 24, 36, 48, 72, 96

### Community 194 - "Community 194"
Cohesion: 0.25
Nodes (8): EP, 12, 120, 24, 36, 48, 72, 96

### Community 195 - "Community 195"
Cohesion: 0.25
Nodes (7): calibration_audit, cone_nominal_rate, intensity_nominal_rate, min_cases, verdict_margin, test_set_budget, max_evaluations_per_season

### Community 196 - "Community 196"
Cohesion: 0.25
Nodes (8): drift, min_samples, reference_flavor, shift_sigma, validation_loss, variance_ratio_limit, consecutive_required, threshold_fraction

### Community 197 - "Community 197"
Cohesion: 0.25
Nodes (8): promotion, flavor, new_basin_tolerance, primary_metric, reference_basin, require_manual_gate, split, basins()

### Community 200 - "Community 200"
Cohesion: 0.29
Nodes (7): products, cone_percentile, landfall_threshold_nm, lead_hours, ri_alert_probability, ri_threshold_kt, ri_window_hours

### Community 201 - "Community 201"
Cohesion: 0.29
Nodes (7): skew_audit, alert_intensity_delta_kt, alert_track_delta_nm, audit_delay_days, lead_hours, min_samples, window_days

### Community 202 - "Community 202"
Cohesion: 0.57
Nodes (5): deploy-plan.sh script, touches(), touches_component(), touches_console(), why

### Community 203 - "Community 203"
Cohesion: 0.29
Nodes (7): env, IMAGE, JOB, PROJECT_ID, PUBLISH, REGION, REGISTRY

### Community 204 - "Community 204"
Cohesion: 0.43
Nodes (4): cmd_baseline_backtest(), RegisteredError, report(), test_registered_error_spec()

### Community 206 - "Community 206"
Cohesion: 0.33
Nodes (6): build_fusion(), forward(), __init__(), weights(), test_fusion_rejects_the_wrong_number_of_models(), test_fusion_weights_are_normalised_and_floored()

### Community 207 - "Community 207"
Cohesion: 0.38
Nodes (3): oracle(), target_time(), worst_case_oracle()

### Community 209 - "Community 209"
Cohesion: 0.33
Nodes (6): ensemble, climatological_cone_nm_by_basin, members, min_members_for_ensemble_cone, reduced_members, underdispersion_fraction

### Community 210 - "Community 210"
Cohesion: 0.33
Nodes (6): triggers, data_volume_threshold, nightly_latent_hour_utc, preseason_date, scheduled_monthly_day, suppress_nightly_latent_during_active_storms

### Community 212 - "Community 212"
Cohesion: 0.33
Nodes (6): update_job, workflow_dispatch, default, description, type, inputs

### Community 213 - "Community 213"
Cohesion: 0.33
Nodes (6): on, pull_request, push, paths, branches, paths

### Community 215 - "Community 215"
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

### Community 220 - "Community 220"
Cohesion: 0.50
Nodes (3): assert_operational_flavor(), CycleError, test_operational_flavor_guard_rejects_pretrain_features()

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

### Community 232 - "Community 232"
Cohesion: 0.67
Nodes (3): limit, lower_is_better, nhc_consensus_beat_rate_48h

### Community 233 - "Community 233"
Cohesion: 0.67
Nodes (3): track_error_120h_nm, limit, lower_is_better

### Community 234 - "Community 234"
Cohesion: 0.67
Nodes (3): track_error_48h_nm, limit, lower_is_better

## Knowledge Gaps
- **14 isolated node(s):** `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627`, `RFC-5322`, `RFC-5646` (+9 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2842 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Flavor` connect `Community 28` to `Community 0`, `Community 129`, `Community 1`, `Community 4`, `Community 5`, `Community 134`, `Community 7`, `Community 8`, `Community 137`, `Community 138`, `Community 6`, `Community 135`, `Community 139`, `Community 16`, `Community 18`, `Community 19`, `Community 151`, `Community 24`, `Community 23`, `Community 26`, `Community 157`, `Community 31`, `Community 33`, `Community 34`, `Community 163`, `Community 35`, `Community 38`, `Community 170`, `Community 42`, `Community 44`, `Community 45`, `Community 46`, `Community 173`, `Community 48`, `Community 47`, `Community 177`, `Community 51`, `Community 181`, `Community 66`, `Community 68`, `Community 73`, `Community 74`, `Community 83`, `Community 88`, `Community 91`, `Community 220`, `Community 221`, `Community 94`, `Community 95`, `Community 96`, `Community 97`, `Community 93`, `Community 99`, `Community 102`, `Community 103`, `Community 107`, `Community 109`, `Community 114`, `Community 124`, `Community 125`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 254 inferred relationships involving `Flavor` (e.g. with `DemoState` and `drift()`) actually correct?**
  _`Flavor` has 254 INFERRED edges - model-reasoned connections that need verification._
- **What connects `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627` to the rest of the system?**
  _14 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.039293598233995586 - nodes in this community are weakly interconnected._
- **Why does `Track` connect `Community 1` to `Community 0`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 138`, `Community 11`, `Community 12`, `Community 14`, `Community 15`, `Community 22`, `Community 24`, `Community 153`, `Community 26`, `Community 27`, `Community 28`, `Community 33`, `Community 34`, `Community 35`, `Community 38`, `Community 39`, `Community 42`, `Community 45`, `Community 48`, `Community 56`, `Community 57`, `Community 58`, `Community 66`, `Community 70`, `Community 71`, `Community 74`, `Community 89`, `Community 91`, `Community 94`, `Community 96`, `Community 97`, `Community 99`, `Community 103`, `Community 108`, `Community 111`, `Community 114`, `Community 124`, `Community 125`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Are the 140 inferred relationships involving `Track` (e.g. with `save_cycle_inputs()` and `StormState`) actually correct?**
  _`Track` has 140 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.03853211009174312 - nodes in this community are weakly interconnected._