# Graph Report - anemoi  (2026-11-12)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 5963 nodes · 15057 edges · 222 communities (195 shown, 27 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 2289 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4016d750`
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
- Community 192
- Community 193
- Community 194
- Community 195
- Community 196
- Community 197
- Community 198
- Community 199
- Community 201
- Community 202
- Community 203
- Community 204
- Community 205
- Community 206
- Community 207
- Community 208
- Community 209
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
- `test_trained_basins_without_champions_is_the_atlantic()` --uses--> `ModelRegistry`  [INFERRED]
  tests/test_registry.py → src/anemoi/tracking/registry.py
- `test_a_versions_arch_params_change_what_is_described()` --calls--> `describe()`  [INFERRED]
  tests/test_model_architecture.py → src/anemoi/models/architecture.py
- `test_the_gnn_is_fed_the_real_lattice()` --calls--> `describe()`  [INFERRED]
  tests/test_model_architecture.py → src/anemoi/models/architecture.py
- `test_cli_exits_nonzero_on_failure_so_the_entrypoint_falls_back()` --calls--> `main()`  [INFERRED]
  tests/test_cache_localize.py → src/anemoi/cli.py

## Import Cycles
- None detected.

## Communities (222 total, 27 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (71): assert_deployable(), Curriculum, CurriculumError, CurriculumRun, stage_a(), stage_b(), StageResult, OrchestrationError (+63 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (61): archive_key(), cache_path(), _decode_cached_fields(), FetchTask, load_cached_fields(), _memo_enabled(), run_fetch_cache(), _work() (+53 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (54): apply_cold_wake(), area_mean(), assert_flavor(), cold_wake_sst_depression_c(), compare_potential_intensity_estimates(), compute_environment_features(), deep_layer_shear(), emanuel_potential_intensity() (+46 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (18): cycle_inputs_prefix(), save_cycle_inputs(), basins_of(), select_basins(), augment_track(), emulate_working_track(), Track, WorkingTrackNoise (+10 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (49): Props, Section, SectionPage, { sections }, height, motionClass, Props, {
    size = 28,
    spinning = false,
    class: className,
    ...restProps
  } (+41 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (45): _default_fetch_fn(), fetch(), _default_fetch_fn(), fetch(), _crop_box(), era5_deps_available(), era5_to_gridded_fields(), crop() (+37 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (44): cycle_key(), load_cycle_result(), save_cycle_result(), CycleResult, IntensityPercentiles, audit_cycle(), audit_due(), audit_storm() (+36 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (63): CyclePlanOut, at(), calendarValue, hour, hourAllowed, inRange(), maxValue, minValue (+55 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (44): @lucide/svelte@^1.71.0, sveltekit-superforms@^2.31.0, authClient, { form }, Props, { form }, Props, errorMsg (+36 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (35): audit_one(), audit_run(), _AuditPlan, _fix_from_dict(), _fix_to_dict(), list_operational_records(), _load_audited_cycles(), load_skew_samples() (+27 more)

### Community 10 - "Community 10"
Cohesion: 0.04
Nodes (29): ModelSpec, require_torch(), build_fusion(), forward(), __init__(), weights(), __getattr__(), coriolis_parameter() (+21 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (44): run_fetch_cache(), ArchiveClient, build_fetch_tasks(), filter_tracks_by_min_valid_time(), shard_tracks(), sync_cache_to_archive(), SyncReport, make_fields() (+36 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (34): _crop_variable(), fetch_real_satellite_crop(), _find_real_scan(), GoesFetchError, _lazy_open(), _list_scan_keys(), _nearest_scan_key(), _parse_scan_start() (+26 more)

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (37): cycle_products_out(), god_out(), model_catalog(), model_version_out(), retrain_job_out(), skew_report_out(), get_active_pin(), get_model_architecture() (+29 more)

### Community 14 - "Community 14"
Cohesion: 0.07
Nodes (30): cmd_ablation(), cmd_atcf_archive(), cmd_cache_localize(), cmd_consistency_distill(), cmd_drift_reference_fit(), cmd_era5_cache(), cmd_gdas_cache(), _cmd_gridded_cache() (+22 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (38): cache_nwp_lead_hours(), CacheLeadMismatch, _claim_cache_dir(), fetch_one(), run_fetch_cache(), make_fields(), make_track(), test_default_fetch_fn_wires_a_shared_session() (+30 more)

### Community 16 - "Community 16"
Cohesion: 0.05
Nodes (32): ChecksumCheck, Fetcher, FetchError, FetchResult, ingest_cycle_inputs(), ingest_one(), IngestionOutcome, IngestionRecord (+24 more)

### Community 17 - "Community 17"
Cohesion: 0.06
Nodes (48): AppAuth, buildAuth(), getAuth(), verifyApiKey(), CYCLE_STEP, cycleInstanceId(), CycleParams, CycleWorkflow (+40 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (38): build_cone(), build_products(), climatological_cone_nm(), cone_radius_from_spread(), ConeSegment, deterministic_center(), EnsembleMember, ForecastProducts (+30 more)

### Community 19 - "Community 19"
Cohesion: 0.05
Nodes (27): StageSpec, train_cnn_stage(), displacement_validation_metrics(), freeze_encoder(), batch_graph(), build_gnn_samples(), gnn_input(), GnnStageSamples (+19 more)

### Community 20 - "Community 20"
Cohesion: 0.05
Nodes (51): ArchitectureOut, LayerOut, ModelVersionOut, {
		arch,
		onclose,
		class: className = ''
	}, Box, boxFor(), clamp(), color (+43 more)

### Community 21 - "Community 21"
Cohesion: 0.05
Nodes (34): svelte-guard@^1.1.1, authHandle(), guards, handle, Auth, _authByRequest, buildAuth(), checkRegistrationOpen() (+26 more)

### Community 22 - "Community 22"
Cohesion: 0.06
Nodes (39): svelte-sonner@^1.2.3, getActivePin(), listRegistry(), ActivePin, ModelCatalog, RegistryEntry, FUSION_COLOR, errorDetail() (+31 more)

### Community 23 - "Community 23"
Cohesion: 0.07
Nodes (26): experiment_name(), cmd_train(), build_info(), _build_info_path(), config_digest(), git_sha(), summary(), arch_params_tag() (+18 more)

### Community 24 - "Community 24"
Cohesion: 0.07
Nodes (32): list_cycle_labels(), archive_atcf(), archived_tcvitals(), ArchiveReport, currentstorms_key(), _digest(), _get_bytes(), _get_text() (+24 more)

### Community 25 - "Community 25"
Cohesion: 0.07
Nodes (28): check_run(), CycleConflict, _existing_source(), InFlight, operator_ids(), RunRequest, stored_source(), RunInfo (+20 more)

### Community 26 - "Community 26"
Cohesion: 0.06
Nodes (30): calibrate(), forecast_motion_bearings(), observed_motion_bearings(), recurving_cases(), _scalar_errors(), crps_ensemble(), _crps_rows(), crps_series() (+22 more)

### Community 27 - "Community 27"
Cohesion: 0.08
Nodes (30): invalidated_by(), evaluate_all(), expand_jobs(), nightly_latent(), on_data_volume(), on_drift(), on_latent_desync(), on_skew() (+22 more)

### Community 28 - "Community 28"
Cohesion: 0.08
Nodes (30): Fix, build_live_cnn_x(), build_live_gnn_x(), build_live_lstm_x(), build_live_pinn_x(), build_live_transformer_x(), _current_fields(), _current_window() (+22 more)

### Community 29 - "Community 29"
Cohesion: 0.08
Nodes (30): ExecutionMode, Task, fake_load_run_artifacts(), _FakeJointLatents, _register_group1_versions(), runner(), fake_extract_joint_latents(), make_fake() (+22 more)

### Community 30 - "Community 30"
Cohesion: 0.07
Nodes (5): RealState, deterministic(), live_fields(), RealStormState, _synthetic_fallback_deterministic()

### Community 31 - "Community 31"
Cohesion: 0.05
Nodes (45): layerchart@^2.5.1, CyclePayload, CycleProducts, CycleResult, DriftReportOut, FeatureDriftOut, HealthOut, IntensityPercentiles (+37 more)

### Community 32 - "Community 32"
Cohesion: 0.06
Nodes (25): storm_basin(), absolute_pairs(), basin_key(), basin_value(), is_basin_key(), key_basin(), per_basin_scores(), sample_counts() (+17 more)

### Community 33 - "Community 33"
Cohesion: 0.07
Nodes (29): build_lstm(), encode(), forward(), __init__(), boundaries_for_flavor(), StageSamples, candidate_model(), _fake_checkpoint_store() (+21 more)

### Community 34 - "Community 34"
Cohesion: 0.08
Nodes (11): get_state(), require_api_key(), state_dependency(), get_custom_redoc_html(), create_app(), _debug_last_deterministic_error(), redoc_html(), _lifespan() (+3 more)

### Community 35 - "Community 35"
Cohesion: 0.06
Nodes (22): _sample_config(), _context_features(), _displacement_to_absolute(), _empty_samples(), _extract_for_tracks(), extract_joint_latents(), JointLatentBundle, JointLatentSamples (+14 more)

### Community 36 - "Community 36"
Cohesion: 0.06
Nodes (28): _empty_report(), _fake_curriculum_run(), make_args(), make_track(), _retrain_check_args(), _save_real_shaped_gdas_sample(), _spy_assign_splits(), test_cmd_era5_cache_keeps_the_default_boundaries() (+20 more)

### Community 37 - "Community 37"
Cohesion: 0.07
Nodes (26): Archive, archives_for(), describe(), fetch_latest_hurdat2(), last_season(), latest_name(), manifest_path(), season_boundaries() (+18 more)

### Community 38 - "Community 38"
Cohesion: 0.08
Nodes (41): ApiError, apiFetch(), getArchitecture(), getCalibration(), getCycle(), getDrift(), getDriftAll(), getModelRegistry() (+33 more)

### Community 39 - "Community 39"
Cohesion: 0.07
Nodes (20): AvailabilityOracle, CycleInputs, earliest_ready_time(), InputStatus, resolve_cycle_inputs(), _valid_time_for(), NWPCycleSelection, test_all_nwp_missing_marks_the_required_input_unavailable() (+12 more)

### Community 40 - "Community 40"
Cohesion: 0.05
Nodes (32): BY_ARCHITECTURE, BY_SLUG, FUNCTIONAL_COLORS, GOD_ORDER, GODS, Module, STATUS_COLORS, STRUCTURAL_COLORS (+24 more)

### Community 41 - "Community 41"
Cohesion: 0.06
Nodes (18): bearing_deg(), bearings_deg(), cross_along_track_nm(), cross_along_track_nms(), haversine_nm(), km_to_nm(), nm_to_km(), offset_position() (+10 more)

### Community 42 - "Community 42"
Cohesion: 0.08
Nodes (25): build_pinn(), encode(), forward(), __init__(), build_pinn_samples(), _train_candidate_lstm_streaming(), build_x(), track_input() (+17 more)

### Community 43 - "Community 43"
Cohesion: 0.08
Nodes (25): advisory_time(), cycle_label(), floor_synoptic(), is_synoptic(), next_synoptic(), NWPUnavailableError, require_synoptic(), _require_utc() (+17 more)

### Community 44 - "Community 44"
Cohesion: 0.06
Nodes (24): client(), _get_real_state(), hurdat2_file(), _stage_group1_and_derived(), test_a_live_storm_keeps_its_cycles_across_a_feed_refresh(), test_a_stale_refresh_in_flight_serves_known_storms_without_waiting(), test_calibration_report_is_honest_empty_with_no_samples(), test_calibration_report_reflects_persisted_samples() (+16 more)

### Community 45 - "Community 45"
Cohesion: 0.12
Nodes (26): climatological_ensemble(), run_cycle(), deterministic_fn(), good_ensemble(), make_fix(), test_a_pacific_climatological_ensemble_is_drawn_from_pacific_radii(), test_absent_opportunistic_feeds_do_not_flag_the_cycle(), test_an_eastern_pacific_cycle_falls_back_to_nhcs_pacific_radii() (+18 more)

### Community 46 - "Community 46"
Cohesion: 0.07
Nodes (39): dependencies, arktype@^2.2.7, better-auth@^1.7.7, @better-auth/passkey@^1.7.7, bits-ui@^2.20.6, clsx@^2.1.1, d3-polygon@^3.0.1, d3-scale@^4.0.2 (+31 more)

### Community 47 - "Community 47"
Cohesion: 0.10
Nodes (10): cycle_plan_out(), _budgets(), CyclePlan, derive_vitals_timeout(), plan_day(), _schedule_stages(), ScheduledStage, Stage (+2 more)

### Community 48 - "Community 48"
Cohesion: 0.09
Nodes (18): DriftError, ReferenceDistribution, load_reference(), reference_from_json(), reference_to_json(), save_reference(), test_drift_report_detects_real_drift_once_enough_samples_are_collected(), test_drift_report_is_honest_zero_for_a_model_that_never_contributed() (+10 more)

### Community 49 - "Community 49"
Cohesion: 0.09
Nodes (21): recommend_extra_conditioning(), run_spread_backtest(), SpreadBacktestError, SpreadBacktestReport, _fake_val(), _FakeS3Client, _lc(), patched() (+13 more)

### Community 50 - "Community 50"
Cohesion: 0.07
Nodes (30): ConeSegmentOut, FixOut, bounds, colors, coneFeatures, coneHull, currentFix, forecastLine (+22 more)

### Community 51 - "Community 51"
Cohesion: 0.05
Nodes (38): devDependencies, cn@^0.3.3, @fontsource-variable/geist@^5.3.0, @fontsource-variable/geist-mono@^5.3.0, @fontsource-variable/inter@^5.3.0, formsnap@^2.0.1, mode-watcher@^1.1.0, @playwright/test@^1.63.0 (+30 more)

### Community 52 - "Community 52"
Cohesion: 0.11
Nodes (28): assert_input_safe(), emulate_working_fix(), recalibrate_from_pairs(), TrackQuality, _latlon(), make_fix(), make_track(), test_assert_input_safe_allows_working_quality() (+20 more)

### Community 53 - "Community 53"
Cohesion: 0.09
Nodes (23): assert_no_leakage(), assign_splits(), _earliest_season(), _latest_season(), LeakageError, _seasons(), Split, _split_for_season() (+15 more)

### Community 54 - "Community 54"
Cohesion: 0.11
Nodes (22): build_cnn(), encode(), forward(), __init__(), test_cnn_is_resolution_agnostic(), cache_all_fixes(), _FakeS3Client, make_fields() (+14 more)

### Community 55 - "Community 55"
Cohesion: 0.11
Nodes (26): cmd_cycle(), LatencyOracle, CycleAbandoned, plan_cycle(), total_budget(), test_a_cycle_started_at_the_timeout_still_clears_the_margin(), test_all_four_daily_cycles_plan_and_meet_their_deadlines(), test_core_is_ready_before_spread() (+18 more)

### Community 56 - "Community 56"
Cohesion: 0.08
Nodes (26): brier_score(), aggregate_by_storm(), beat_rate(), diebold_mariano(), verify(), pair(), test_aggregation_collapses_fixes_to_one_case_per_storm(), test_aggregation_keeps_the_two_arrays_aligned() (+18 more)

### Community 57 - "Community 57"
Cohesion: 0.11
Nodes (24): build_gnn(), encode(), forward(), __init__(), build_mesh_topology(), cache_all_fixes(), _FakeS3Client, make_fields() (+16 more)

### Community 58 - "Community 58"
Cohesion: 0.13
Nodes (22): _builder(), _decode_arch_params(), _download_state_dict(), InferenceLoadError, load_run_artifacts(), load_standardization_stats(), load_trained_model(), load_trained_pinn_candidate() (+14 more)

### Community 59 - "Community 59"
Cohesion: 0.06
Nodes (35): context, dockerfile, postgres, AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY, MLFLOW_S3_ENDPOINT_URL, POSTGRES_DB (+27 more)

### Community 60 - "Community 60"
Cohesion: 0.12
Nodes (20): by_basin(), complete_run(), _forecasts(), metric_set(), test_a_basin_is_verified_when_the_model_beats_persistence_there(), test_a_candidate_that_loses_a_verified_basin_is_refused(), test_a_candidate_that_scored_no_basin_is_judged_as_before(), test_a_candidate_verified_in_a_new_basin_may_be_slightly_worse_on_the_reference() (+12 more)

### Community 61 - "Community 61"
Cohesion: 0.10
Nodes (18): AtcfError, pair_by_valid_time(), parse_bdeck(), _parse_latlon(), parse_tcvitals(), TcVitalsError, as_issued(), calibrate_season() (+10 more)

### Community 62 - "Community 62"
Cohesion: 0.11
Nodes (20): fetch_current_storm_ids(), fetch_current_storms(), fetch_live_track(), fetch_live_tracks(), fetch_one(), _get(), LiveAtcfError, test_fetch_current_storm_ids_parses_and_uppercases() (+12 more)

### Community 63 - "Community 63"
Cohesion: 0.10
Nodes (10): ModelRegistry, _champions(), test_a_basin_is_served_once_every_champion_is_verified_in_it(), test_a_champion_verified_nowhere_serves_no_basin_as_in_distribution(), test_no_champion_or_champions_from_before_the_tag_are_the_atlantic(), _champions_tagged(), test_a_basin_counts_only_when_every_champion_trained_on_it(), test_a_champion_without_the_tag_counts_as_atlantic_only() (+2 more)

### Community 64 - "Community 64"
Cohesion: 0.06
Nodes (28): AsyncReturnType, Expand, ExtractGenericViewableContent, GenericItem, GenericSelectorOption, GenericSnippetProps, GenericViewableContent, InheritedSnippetProps (+20 more)

### Community 65 - "Community 65"
Cohesion: 0.14
Nodes (12): ModelVersion, Stage, _fake_checkpoint_store(), _reconcile_args(), test_registry_reconcile_dry_run_reports_without_transitioning(), test_registry_reconcile_ignores_nan_metrics(), test_registry_reconcile_never_touches_a_model_with_a_production_version(), test_registry_reconcile_re_stages_the_real_best_existing_version() (+4 more)

### Community 66 - "Community 66"
Cohesion: 0.06
Nodes (31): data, basins, stage_a, epochs, flavor, input_sources, label_source, learning_rate (+23 more)

### Community 67 - "Community 67"
Cohesion: 0.10
Nodes (17): LeadCalibration, LeadTimeStats, to_metric_dict(), ConfigResult, evaluate_step_budget_tradeoff(), evaluate(), point_track_error_48h(), TradeoffReport (+9 more)

### Community 68 - "Community 68"
Cohesion: 0.08
Nodes (30): @better-auth/api-key@^1.7.7, @types/node@^26.6.4, typescript@^5.9.3, wrangler@^4.147.0, @better-auth/api-key, @types/node, typescript, wrangler (+22 more)

### Community 69 - "Community 69"
Cohesion: 0.09
Nodes (12): color_for(), god(), Module, WindGod, test_every_god_color_is_distinct(), test_experiment_name_handles_fusion_without_raising(), test_experiment_names_are_the_god_slugs(), test_lookup_by_slug_and_by_architecture_agree() (+4 more)

### Community 70 - "Community 70"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, env, GH_TOKEN, GRAPHIFY_VERSION, permissions, runs-on (+22 more)

### Community 71 - "Community 71"
Cohesion: 0.12
Nodes (15): ensemble(), build_real_ensemble_fn(), ensemble_fn(), InferenceEnsembleError, cache_current_fix(), _FakeS3Client, make_track(), _register() (+7 more)

### Community 72 - "Community 72"
Cohesion: 0.07
Nodes (23): rehype-slug@^6.0.0, rehype-stringify@^10.0.1, remark-gfm@^4.0.1, remark-parse@^11.0.0, remark-rehype@^11.1.2, unified@^11.0.5, unist-util-visit@^5.1.0, CONSOLE_ROOT (+15 more)

### Community 73 - "Community 73"
Cohesion: 0.07
Nodes (29): WithElementRef, ButtonClickEvent, PrimitiveAnchorAttributes, PrimitiveButtonAttributes, PrimitiveCanvasAttributes, PrimitiveDivAttributes, PrimitiveElementAttributes, PrimitiveFigureAttributes (+21 more)

### Community 74 - "Community 74"
Cohesion: 0.13
Nodes (16): _get_text(), load_drift_live(), _put_text(), save_drift_live(), _load_audited(), _save_audited(), CheckpointStore, FakeClient (+8 more)

### Community 75 - "Community 75"
Cohesion: 0.14
Nodes (18): AblationReport, build_samples(), _cell(), make_track(), test_at_fraction_filters_and_sorts_by_hidden_dim(), test_build_samples_augmentation_multiplies_sample_count(), test_build_samples_shapes_match_sequence_length_and_columns(), test_build_samples_skips_storms_shorter_than_required() (+10 more)

### Community 76 - "Community 76"
Cohesion: 0.08
Nodes (9): build_derived_schedule(), _latent_task(), OrchestrationResult, ResourceProfile, Schedule, _train_task(), validate_schedule(), Wave (+1 more)

### Community 77 - "Community 77"
Cohesion: 0.15
Nodes (14): build_real_deterministic_fn(), cache_current_fix(), _FakeS3Client, make_track(), _register_real_version(), _store(), test_build_real_deterministic_fn_combines_all_four_real_models(), test_build_real_deterministic_fn_raises_with_no_registered_models() (+6 more)

### Community 78 - "Community 78"
Cohesion: 0.10
Nodes (16): _FakeCycleOutput, _fresh_real_state(), _make_deterministic_forecast(), _make_storm_state(), _memory_store(), _MemoryS3Client, test_a_failed_cycle_write_never_fails_the_cycle(), test_an_unrestored_drift_window_is_never_written_back() (+8 more)

### Community 79 - "Community 79"
Cohesion: 0.07
Nodes (28): inputArgs, jobs, projectId, region, results, timeoutSeconds, assign, return (+20 more)

### Community 80 - "Community 80"
Cohesion: 0.17
Nodes (23): build_schedule(), Mode, run_schedule(), RunOutcome, failing_runner(), runner(), ok_runner(), test_both_schedules_validate() (+15 more)

### Community 81 - "Community 81"
Cohesion: 0.07
Nodes (10): _FakeMlflowModelVersion, _mlflow_client_that_registers_and_transitions(), create_model_version(), test_mlflow_mirror_skips_create_registered_model_if_it_already_exists(), create_model_version(), test_mlflow_transition_also_mirrors_the_archived_incumbent(), create_model_version(), test_mlflow_transition_mirror_uses_the_real_mlflow_version_number() (+2 more)

### Community 82 - "Community 82"
Cohesion: 0.14
Nodes (18): Hurdat2Error, _parse_data_line(), _parse_header(), parse_hurdat2(), _parse_latlon(), test_entry_count_mismatch_raises(), test_header_name_is_parsed_onto_the_track(), test_malformed_header_raises() (+10 more)

### Community 83 - "Community 83"
Cohesion: 0.13
Nodes (16): Flavor, RegistryError, test_data_volume_counts_seasons_newer_than_any_model_trained_on(), test_champion_falls_back_to_staging_without_a_production_version(), test_champion_prefers_production_over_staging(), test_checkpoint_store_push_failure_degrades_to_local_only(), test_checkpoint_uri_defaults_to_none_when_not_given(), test_checkpoint_uri_persists_on_the_version_itself() (+8 more)

### Community 84 - "Community 84"
Cohesion: 0.19
Nodes (14): audit_due(), SkewMonitor, sample(), test_audit_becomes_due_once_era5t_lands(), test_audit_is_not_due_immediately_after_the_cycle(), test_intensity_delta_is_signed_toward_the_operational_run(), test_intensity_skew_alone_can_raise_an_alert(), test_large_track_delta_raises_an_alert() (+6 more)

### Community 85 - "Community 85"
Cohesion: 0.13
Nodes (14): fetch_and_parse_ndbc(), fetch_ndbc_realtime2(), _get(), NdbcFetchError, NdbcObservation, parse_ndbc_realtime2(), test_a_row_with_the_wrong_column_count_is_skipped_not_fatal(), test_a_station_missing_wave_columns_still_parses() (+6 more)

### Community 86 - "Community 86"
Cohesion: 0.14
Nodes (11): basin_inputs(), _build_live_context(), _build_live_x(), deterministic_fn(), _compute_env_features(), InferenceCycleError, _item_stat(), _real_fusion_forecast() (+3 more)

### Community 87 - "Community 87"
Cohesion: 0.11
Nodes (11): runed@^0.37.1, App, Locals, Platform, DEFAULT_EXTRA, ExtraPreferences, PackageManager, UserContext (+3 more)

### Community 88 - "Community 88"
Cohesion: 0.11
Nodes (5): cycle_payload_out(), cycle_result_out(), provenance_out(), CycleHistory, CycleOutput

### Community 89 - "Community 89"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GH_TOKEN, IMPORTED_FROM, SOURCE_SHA, jobs, publish (+16 more)

### Community 90 - "Community 90"
Cohesion: 0.15
Nodes (14): detect_feature_drift(), FeatureDrift, ValidationLossMonitor, reference(), test_a_recovery_resets_the_consecutive_count(), test_collapsed_variance_is_detected(), test_feature_count_mismatch_raises(), test_first_observation_only_sets_the_baseline() (+6 more)

### Community 91 - "Community 91"
Cohesion: 0.14
Nodes (13): QUICK, API, DEVELOP, addVirtualAuthenticator(), EMAIL_DIR, EMAIL_LOCK, listEmailFiles(), localD1() (+5 more)

### Community 92 - "Community 92"
Cohesion: 0.13
Nodes (10): _download(), fetch_oisst_sst(), require_sst_deps(), sst_at(), SstFetchError, _small_grid(), test_fetch_oisst_sst_reads_real_recent_data(), test_sst_at_finds_the_nearest_cell() (+2 more)

### Community 93 - "Community 93"
Cohesion: 0.15
Nodes (14): _all_tensors(), Architecture, _builder(), describe(), describe_cached(), _describe_cached(), hook(), _example_inputs() (+6 more)

### Community 94 - "Community 94"
Cohesion: 0.13
Nodes (11): initial_fix(), _MemoryS3, s3(), test_an_archive_storm_says_its_fix_is_the_final_best_track(), test_missing_vitals_are_extrapolated_and_estimated(), test_one_earlier_fix_is_persisted(), test_overrides_apply_on_top(), test_the_fix_at_the_cycle_time_is_used_not_the_latest() (+3 more)

### Community 95 - "Community 95"
Cohesion: 0.16
Nodes (15): latent_signature(), full_set(), register_group1(), _stage_all(), test_desynced_derived_models_detects_a_real_champion_change(), test_desynced_derived_models_is_empty_for_a_coherent_set(), test_desynced_derived_models_is_empty_when_no_derived_model_has_a_champion(), test_desynced_derived_models_is_empty_without_a_full_champion_set() (+7 more)

### Community 96 - "Community 96"
Cohesion: 0.09
Nodes (8): _FakeS3Config, test_champion_is_not_simply_the_most_recently_registered_version(), test_checkpoint_store_push_mirrors_registry_json_after_every_save(), test_pull_failure_degrades_to_an_empty_registry(), test_pull_from_checkpoint_store_hydrates_a_missing_local_registry(), test_pull_is_a_noop_when_the_key_does_not_exist_remotely_yet(), test_pull_is_skipped_entirely_without_a_checkpoint_store(), test_pull_reconciles_with_durable_storage_even_when_local_already_exists()

### Community 97 - "Community 97"
Cohesion: 0.14
Nodes (11): _files(), localize_cache(), LocalizeReport, _raise(), _cache(), test_a_directory_that_cant_be_listed_fails_the_copy(), test_a_missing_source_raises(), test_a_rerun_only_fills_gaps() (+3 more)

### Community 98 - "Community 98"
Cohesion: 0.15
Nodes (9): fetch_gefs_ensemble_grib2_fields(), fetch_gefs_member_grib2_fields(), _gefs_member_url(), require_gdas_deps(), test_control_member_zero_uses_gec00_not_gep00(), test_fetch_gefs_ensemble_reads_multiple_real_distinct_members(), test_fetch_gefs_member_reads_the_real_noaa_archive(), test_member_out_of_range_raises() (+1 more)

### Community 99 - "Community 99"
Cohesion: 0.16
Nodes (11): _decode_one_sonde(), DropsondeFetchError, DropsondeProfile, fetch_and_parse_dropsonde_mission(), fetch_dropsonde_mission_tarball(), _ftp_connect(), list_dropsonde_missions(), _mission_dir() (+3 more)

### Community 100 - "Community 100"
Cohesion: 0.17
Nodes (16): _lon_close(), _members(), ref_bearing(), ref_displacement(), ref_haversine(), ref_offset(), rng(), test_array_geodesy_matches_the_per_point_formulas() (+8 more)

### Community 102 - "Community 102"
Cohesion: 0.13
Nodes (7): mlflow_client_from_env(), test_an_unreachable_server_is_skipped_fast(), test_builds_a_real_client_when_tracking_uri_is_set(), test_fail_fast_settings_never_override_explicit_ones(), test_mlflow_client_from_env_can_actually_reach_the_configured_server(), test_returns_none_when_tracking_uri_is_unset(), test_returns_none_without_mlflow_installed()

### Community 103 - "Community 103"
Cohesion: 0.15
Nodes (10): config_copy(), edit(), _image_layout(), _run(), test_a_missing_config_dir_is_refused(), test_an_image_without_configs_fails_at_import_and_says_why(), test_an_invalid_config_is_refused_with_a_clear_message(), test_edited_values_take_effect_at_runtime() (+2 more)

### Community 104 - "Community 104"
Cohesion: 0.13
Nodes (13): generate_season(), generate_track(), make_storm_spec(), StormSpec, wrap_longitude(), test_archive_spans_the_requested_seasons(), test_fields_have_matching_shapes_and_carry_a_flavor(), test_fixes_are_six_hourly_and_synoptic() (+5 more)

### Community 105 - "Community 105"
Cohesion: 0.14
Nodes (10): lr_factor(), transformer_optim(), TransformerOptim, TransformerOptimizer, test_a_short_stage_still_ends_on_the_floor(), test_config_values_are_validated(), test_cosine_decays_to_the_floor_on_the_last_update(), test_no_warmup_starts_at_the_peak() (+2 more)

### Community 106 - "Community 106"
Cohesion: 0.23
Nodes (15): evaluate_promotion(), complete_run(), good_metrics(), test_candidate_worse_than_incumbent_is_not_staged(), test_era5_flavor_metrics_cannot_gate_promotion(), test_first_candidate_is_staged(), test_incomplete_curriculum_blocks_promotion(), test_missing_metric_is_reported_as_a_failure() (+7 more)

### Community 107 - "Community 107"
Cohesion: 0.15
Nodes (9): _FakeS3Client, _make_samples(), test_a_longer_epoch_budget_never_returns_a_worse_val_loss(), test_early_stopping_halts_before_the_epoch_cap_on_a_real_overfitting_run(), test_run_diffusion_curriculum_uploads_a_checkpoint_and_registers_stage_b(), test_train_diffusion_stage_accepts_dropout_and_weight_decay(), test_train_diffusion_stage_produces_val_metrics_and_artifacts(), test_train_diffusion_stage_records_a_real_dropout_value_in_arch_params() (+1 more)

### Community 108 - "Community 108"
Cohesion: 0.10
Nodes (20): PROJECT_NUMBER, PROJECT_PAT, types, jobs, sync, name, on, issues (+12 more)

### Community 109 - "Community 109"
Cohesion: 0.22
Nodes (15): storm_relative_sequence(), test_extrapolation_continues_the_last_motion_vector(), test_fusion_weights_favour_the_lower_error_model(), test_displacement_to_latlon_round_trips_with_displacement_nm(), make_fix(), test_displacement_direction_matches_bearing(), test_displacement_magnitude_matches_haversine_distance(), test_displacement_nm_matches_storm_relative_sequence() (+7 more)

### Community 110 - "Community 110"
Cohesion: 0.19
Nodes (11): accessed(), _check_type(), config_dir(), ConfigError, fixed(), get(), get_list(), _load() (+3 more)

### Community 111 - "Community 111"
Cohesion: 0.21
Nodes (6): freeCycleLabel(), label(), runFreshCycle(), signIn(), cases, @playwright/test

### Community 112 - "Community 112"
Cohesion: 0.16
Nodes (17): answerRuns(), chip(), context(), cycleFor(), dateButton(), expectForm(), expectShowing(), fixture (+9 more)

### Community 113 - "Community 113"
Cohesion: 0.19
Nodes (13): _bytemap_path(), decode_ssmis_bytemap(), MicrowaveFetchError, _make_bytemap(), test_bytemap_path_matches_the_real_verified_layout(), test_bytemap_path_rejects_an_unknown_satellite(), test_decode_applies_the_real_scale_and_offset_per_variable(), test_decode_grid_matches_the_real_documented_cell_centres() (+5 more)

### Community 114 - "Community 114"
Cohesion: 0.14
Nodes (8): calibration_out(), drift_report_out(), calibration(), drift(), drift_all(), skew(), FeatureDriftOut, DriftReport

### Community 116 - "Community 116"
Cohesion: 0.19
Nodes (6): DEFAULT_AFTER_LOGIN, loginHref(), safeNext(), requireSignIn(), requireSignInLoad(), guard()

### Community 117 - "Community 117"
Cohesion: 0.14
Nodes (10): deterministic(), deterministic(), assert_operational_flavor(), CycleError, DeterministicForecast, extrapolate_fix(), fusion_weights(), test_extrapolation_needs_two_prior_fixes() (+2 more)

### Community 118 - "Community 118"
Cohesion: 0.12
Nodes (4): _Boto3Client, require_boto3(), _StorageClient, test_boto3_adapter_configures_the_client_for_the_given_endpoint()

### Community 119 - "Community 119"
Cohesion: 0.25
Nodes (12): cache_all_fixes(), make_fields(), make_track(), _task_for(), test_build_transformer_samples_empty_when_nothing_cached(), test_build_transformer_samples_rejects_a_cache_smaller_than_grid_size(), test_build_transformer_samples_trims_the_real_41x41_crop_to_grid_size(), test_run_transformer_curriculum_completes_both_stages() (+4 more)

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
Cohesion: 0.18
Nodes (8): get_cycle(), get_storm(), list_storms(), _overrides(), run_cycle(), _served_basins(), _storm_summary(), FixOut

### Community 124 - "Community 124"
Cohesion: 0.12
Nodes (16): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+8 more)

### Community 125 - "Community 125"
Cohesion: 0.12
Nodes (16): compilerOptions, allowJs, allowSyntheticDefaultImports, checkJs, forceConsistentCasingInFileNames, isolatedModules, lib, module (+8 more)

### Community 126 - "Community 126"
Cohesion: 0.18
Nodes (7): fetch_and_decode_ssmis_daily(), fetch_ssmis_daily_bytemap(), RSSFtpCredentials, SSMISDaily, test_credentials_from_env_raises_a_clear_error_when_missing(), test_credentials_from_env_reads_real_values(), test_fetch_and_decode_reads_a_real_recent_ssmis_file()

### Community 127 - "Community 127"
Cohesion: 0.12
Nodes (16): permissions, runs-on, steps, jobs, copilot-setup-steps, name, on, pull_request (+8 more)

### Community 128 - "Community 128"
Cohesion: 0.12
Nodes (9): _cron_run_offset_minutes(), _load(), test_a_config_change_redeploys_the_api(), test_both_images_copy_the_configs(), test_every_config_parses_and_has_no_duplicate_keys(), test_the_console_uses_the_same_scheduled_run_offset(), test_the_lead_times_match_the_api_s_own_copy(), test_the_load_shed_comment_still_describes_the_real_reduced_count() (+1 more)

### Community 129 - "Community 129"
Cohesion: 0.12
Nodes (5): client(), test_docs_route_is_unaffected(), test_theme_http_method_colors_are_distinct(), test_theme_never_uses_a_god_color(), _walk()

### Community 130 - "Community 130"
Cohesion: 0.12
Nodes (16): with, build-args, cache-from, cache-to, context, file, load, password (+8 more)

### Community 131 - "Community 131"
Cohesion: 0.12
Nodes (15): jobs, lint-and-validate, name, permissions, runs-on, steps, name, on (+7 more)

### Community 132 - "Community 132"
Cohesion: 0.13
Nodes (8): source_out(), health(), models(), sources(), HealthOut, SourceOut, DataSource, pretrain_only_sources()

### Community 133 - "Community 133"
Cohesion: 0.28
Nodes (8): NoiseSensitivityReport, _result(), test_is_load_bearing_above_threshold(), test_is_not_load_bearing_below_threshold(), test_relative_change_is_zero_when_losses_match(), test_relative_change_rejects_nonpositive_default_loss(), test_relative_change_sign_matches_direction_of_the_move(), test_run_noise_sensitivity_raises_without_val_storms()

### Community 134 - "Community 134"
Cohesion: 0.19
Nodes (6): _FakeS3Client, _make_samples(), test_run_fusion_curriculum_uploads_a_checkpoint_and_registers_stage_b(), test_train_fusion_stage_reduces_loss_and_produces_val_metrics(), test_train_fusion_stage_rejects_a_val_set_built_with_a_different_model_count(), test_train_fusion_stage_rejects_empty_samples()

### Community 135 - "Community 135"
Cohesion: 0.13
Nodes (15): scripts, build, cf:deploy, check, check:errors, check:warnings, check:watch, dev (+7 more)

### Community 136 - "Community 136"
Cohesion: 0.19
Nodes (12): loading, onInput(), open, query, results, bodyById, buildIndex(), excerptAround() (+4 more)

### Community 137 - "Community 137"
Cohesion: 0.13
Nodes (15): env, environment, if, name, needs, permissions, runs-on, timeout-minutes (+7 more)

### Community 138 - "Community 138"
Cohesion: 0.24
Nodes (11): validate(), make_tags(), test_malformed_dvc_version_is_rejected(), test_malformed_git_commit_is_rejected(), test_malformed_nwp_cycle_lag_is_rejected(), test_none_values_are_dropped_from_the_dict(), test_pretrain_flavor_tags_are_not_operational(), test_v2_1_adds_input_flavor_and_nwp_cycle_lag() (+3 more)

### Community 139 - "Community 139"
Cohesion: 0.14
Nodes (13): compilerOptions, allowJs, checkJs, esModuleInterop, forceConsistentCasingInFileNames, moduleResolution, resolveJsonModule, rewriteRelativeImportExtensions (+5 more)

### Community 140 - "Community 140"
Cohesion: 0.14
Nodes (13): images, options, diskSizeGb, machineType, steps, args, entrypoint, env (+5 more)

### Community 141 - "Community 141"
Cohesion: 0.14
Nodes (14): default, description, type, default, description, type, api, console (+6 more)

### Community 142 - "Community 142"
Cohesion: 0.19
Nodes (8): _mask_missing(), test_fetch_and_parse_reads_a_real_mission_end_to_end(), test_hardcoded_missing_sentinels_match_the_real_eccodes_constants(), test_list_dropsonde_missions_reads_the_real_archive(), test_mask_missing_leaves_real_values_untouched(), test_mask_missing_turns_the_double_sentinel_into_nan(), test_mask_missing_turns_the_long_sentinel_into_nan(), test_mission_dir_matches_the_real_verified_layout()

### Community 143 - "Community 143"
Cohesion: 0.19
Nodes (10): _consistency_model(), test_consistency_accepts_extra_conditioning(), test_consistency_boundary_condition_is_exact_at_step_zero(), test_consistency_multistep_sampling_matches_one_step_shape_and_is_deterministic(), test_consistency_one_step_sampling_produces_distinct_members(), test_gnn_message_passing_runs_over_a_small_graph(), test_gru_variant_builds(), test_invalid_cell_is_rejected() (+2 more)

### Community 144 - "Community 144"
Cohesion: 0.14
Nodes (7): build_diffusion(), __init__(), test_diffusion_accepts_extra_conditioning(), test_diffusion_default_dropout_matches_pre_166_behavior(), test_diffusion_dropout_is_real_but_inert_at_eval_time(), test_diffusion_sampling_clips_x0_to_bound_a_diverging_denoiser(), test_diffusion_sampling_produces_distinct_members()

### Community 145 - "Community 145"
Cohesion: 0.17
Nodes (12): IdTokenClaims, JwtClaims, OidcAddressClaim, OidcStandardClaims, UserProfile, Mandatory, RFC-3966, RFC-4627 (+4 more)

### Community 146 - "Community 146"
Cohesion: 0.15
Nodes (12): name, runs-on, timeout-minutes, concurrency, cancel-in-progress, group, jobs, build (+4 more)

### Community 147 - "Community 147"
Cohesion: 0.21
Nodes (7): build_consistency_model(), consistency_fn(), __init__(), sample(), skip_coeffs(), _cosine_schedule(), test_consistency_rejects_a_non_positive_step_count()

### Community 148 - "Community 148"
Cohesion: 0.15
Nodes (6): distill_consistency_model(), step_loss(), _pseudo_huber(), test_distillation_rejects_a_non_positive_epochs_or_patience(), test_distillation_restores_the_teachers_device_and_mode_even_if_training_raises(), test_distillation_trains_a_student_without_mutating_the_teachers_device()

### Community 149 - "Community 149"
Cohesion: 0.27
Nodes (6): PromotionError, TestSetBudget, test_budget_allows_a_limited_number_of_looks(), test_budget_exhaustion_raises(), test_budget_requires_a_justification(), test_budget_resets_across_seasons()

### Community 150 - "Community 150"
Cohesion: 0.19
Nodes (4): _build_joint_latent(), cycle_sample_seed(), _encode_group1(), test_cycle_sample_seed_is_stable_and_cycle_specific()

### Community 151 - "Community 151"
Cohesion: 0.23
Nodes (11): max, target, budgets, reduced, standard, max, target, assembly (+3 more)

### Community 152 - "Community 152"
Cohesion: 0.17
Nodes (4): local, notes, problems, remote

### Community 153 - "Community 153"
Cohesion: 0.20
Nodes (7): client(), test_a_registered_versions_arch_params_are_used(), test_a_version_without_arch_params_is_described_from_defaults(), test_a_versions_arch_params_change_what_is_described(), test_every_model_runs_its_example_input_and_reports_its_layers(), test_the_gnn_is_fed_the_real_lattice(), test_unknown_models_and_versions_are_404()

### Community 154 - "Community 154"
Cohesion: 0.17
Nodes (11): concurrency, cancel-in-progress, group, jobs, test-api, name, if, name (+3 more)

### Community 155 - "Community 155"
Cohesion: 0.17
Nodes (12): with, cache, cache-dependency-path, enable-cache, fetch-depth, if-no-files-found, include-hidden-files, name (+4 more)

### Community 156 - "Community 156"
Cohesion: 0.17
Nodes (6): test_mlflow_failure_degrades_to_local_only(), __getattr__(), test_mlflow_mirror_is_skipped_without_a_checkpoint_uri(), __getattr__(), test_mlflow_mirror_registers_model_then_version_with_a_real_source_uri(), create_model_version()

### Community 157 - "Community 157"
Cohesion: 0.18
Nodes (11): cycle, advisory_margin_minutes, advisory_offset_minutes, allow_estimated_vitals, allow_load_shedding, max_nwp_lag_hours, nominal_vitals_offset_minutes, nwp_lag_hours (+3 more)

### Community 158 - "Community 158"
Cohesion: 0.20
Nodes (10): limit, lower_is_better, limit, lower_is_better, thresholds, intensity_error_48h_kt, intensity_error_72h_kt, track_error_72h_nm (+2 more)

### Community 159 - "Community 159"
Cohesion: 0.20
Nodes (10): steps, EXPECT_GIT_SHA, GCP_CI_SERVICE_ACCOUNT, GCP_WIF_PROVIDER, env, id, if, name (+2 more)

### Community 160 - "Community 160"
Cohesion: 0.20
Nodes (10): name, outputs, runs-on, timeout-minutes, changes, deploy_api, deploy_console, plan (+2 more)

### Community 161 - "Community 161"
Cohesion: 0.40
Nodes (10): steps, steps, id, if, name, run, uses, working-directory (+2 more)

### Community 162 - "Community 162"
Cohesion: 0.22
Nodes (9): run, test-console, working-directory, defaults, if, name, needs, runs-on (+1 more)

### Community 163 - "Community 163"
Cohesion: 0.22
Nodes (9): BASE_SHA, BEFORE_SHA, DISPATCH_API, DISPATCH_CONSOLE, EVENT, EXPECT_GIT_SHA, HEAD_SHA, REF (+1 more)

### Community 164 - "Community 164"
Cohesion: 0.25
Nodes (8): 12, 120, 24, 36, 48, 72, 96, climatological_cone_nm

### Community 165 - "Community 165"
Cohesion: 0.25
Nodes (8): CP, 12, 120, 24, 36, 48, 72, 96

### Community 166 - "Community 166"
Cohesion: 0.25
Nodes (8): EP, 12, 120, 24, 36, 48, 72, 96

### Community 167 - "Community 167"
Cohesion: 0.25
Nodes (7): calibration_audit, cone_nominal_rate, intensity_nominal_rate, min_cases, verdict_margin, test_set_budget, max_evaluations_per_season

### Community 168 - "Community 168"
Cohesion: 0.25
Nodes (8): drift, min_samples, reference_flavor, shift_sigma, validation_loss, variance_ratio_limit, consecutive_required, threshold_fraction

### Community 169 - "Community 169"
Cohesion: 0.25
Nodes (8): promotion, flavor, new_basin_tolerance, primary_metric, reference_basin, require_manual_gate, split, basins()

### Community 170 - "Community 170"
Cohesion: 0.25
Nodes (4): gdas_likely_unpublished(), test_gdas_likely_unpublished_false_for_an_archived_storm(), test_gdas_likely_unpublished_false_once_real_typical_latency_has_passed(), test_gdas_likely_unpublished_true_within_real_typical_latency()

### Community 172 - "Community 172"
Cohesion: 0.29
Nodes (7): products, cone_percentile, landfall_threshold_nm, lead_hours, ri_alert_probability, ri_threshold_kt, ri_window_hours

### Community 173 - "Community 173"
Cohesion: 0.29
Nodes (7): skew_audit, alert_intensity_delta_kt, alert_track_delta_nm, audit_delay_days, lead_hours, min_samples, window_days

### Community 174 - "Community 174"
Cohesion: 0.57
Nodes (5): deploy-plan.sh script, touches(), touches_component(), touches_console(), why

### Community 175 - "Community 175"
Cohesion: 0.29
Nodes (7): env, IMAGE, JOB, PROJECT_ID, PUBLISH, REGION, REGISTRY

### Community 176 - "Community 176"
Cohesion: 0.29
Nodes (3): archive_atcf(), calibration_audit(), skew_audit()

### Community 177 - "Community 177"
Cohesion: 0.33
Nodes (6): build_transformer(), encode(), forward(), __init__(), test_transformer_emits_track_and_regime(), test_transformer_rejects_an_indivisible_grid()

### Community 178 - "Community 178"
Cohesion: 0.38
Nodes (3): oracle(), target_time(), worst_case_oracle()

### Community 181 - "Community 181"
Cohesion: 0.33
Nodes (6): ensemble, climatological_cone_nm_by_basin, members, min_members_for_ensemble_cone, reduced_members, underdispersion_fraction

### Community 182 - "Community 182"
Cohesion: 0.33
Nodes (6): triggers, data_volume_threshold, nightly_latent_hour_utc, preseason_date, scheduled_monthly_day, suppress_nightly_latent_during_active_storms

### Community 184 - "Community 184"
Cohesion: 0.33
Nodes (6): update_job, workflow_dispatch, default, description, type, inputs

### Community 185 - "Community 185"
Cohesion: 0.33
Nodes (6): on, pull_request, push, paths, branches, paths

### Community 186 - "Community 186"
Cohesion: 0.33
Nodes (4): basin_tags(), test_a_basin_validated_but_never_trained_on_is_not_verified(), test_a_run_from_before_the_counts_sets_no_basin_tags(), test_the_tags_say_what_was_trained_on_and_what_is_verified()

### Community 187 - "Community 187"
Cohesion: 0.47
Nodes (3): Threshold, _thresholds(), test_beat_rate_threshold_is_higher_is_better()

### Community 188 - "Community 188"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 189 - "Community 189"
Cohesion: 0.40
Nodes (3): WORLD_GEOJSON, WorldData, WorldFeatureProperties

### Community 190 - "Community 190"
Cohesion: 0.40
Nodes (4): allowBuilds, esbuild, workerd, minimumReleaseAgeExclude

### Community 194 - "Community 194"
Cohesion: 0.67
Nodes (4): max, target, diffusion, diffusion

### Community 195 - "Community 195"
Cohesion: 0.67
Nodes (4): max, target, fusion, fusion

### Community 196 - "Community 196"
Cohesion: 0.67
Nodes (4): max, target, postprocess, postprocess

### Community 197 - "Community 197"
Cohesion: 0.67
Nodes (4): max, target, preprocess, preprocess

### Community 198 - "Community 198"
Cohesion: 0.83
Nodes (3): graphify(), normalise_graph(), build-graph.sh script

### Community 199 - "Community 199"
Cohesion: 0.50
Nodes (3): uvx, graphify, graphify-mcp

### Community 201 - "Community 201"
Cohesion: 0.50
Nodes (3): torch_available(), pytest_collection_modifyitems(), test_require_torch_message_names_the_extra()

### Community 203 - "Community 203"
Cohesion: 0.67
Nodes (3): limit, lower_is_better, nhc_consensus_beat_rate_48h

### Community 204 - "Community 204"
Cohesion: 0.67
Nodes (3): track_error_120h_nm, limit, lower_is_better

### Community 205 - "Community 205"
Cohesion: 0.67
Nodes (3): track_error_48h_nm, limit, lower_is_better

## Knowledge Gaps
- **13 isolated node(s):** `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627`, `RFC-5322`, `RFC-5646` (+8 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2520 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Flavor` connect `Community 83` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 134`, `Community 138`, `Community 10`, `Community 11`, `Community 14`, `Community 15`, `Community 16`, `Community 19`, `Community 23`, `Community 153`, `Community 28`, `Community 29`, `Community 156`, `Community 32`, `Community 33`, `Community 34`, `Community 35`, `Community 36`, `Community 37`, `Community 42`, `Community 44`, `Community 48`, `Community 49`, `Community 53`, `Community 54`, `Community 57`, `Community 58`, `Community 60`, `Community 191`, `Community 63`, `Community 65`, `Community 193`, `Community 192`, `Community 69`, `Community 71`, `Community 200`, `Community 77`, `Community 81`, `Community 212`, `Community 90`, `Community 94`, `Community 95`, `Community 96`, `Community 104`, `Community 106`, `Community 107`, `Community 110`, `Community 114`, `Community 115`, `Community 117`, `Community 119`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Are the 236 inferred relationships involving `Flavor` (e.g. with `DemoState` and `drift()`) actually correct?**
  _`Flavor` has 236 INFERRED edges - model-reasoned connections that need verification._
- **What connects `./.svelte-kit/tsconfig.json`, `RFC-3966`, `RFC-4627` to the rest of the system?**
  _13 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.03628401626524867 - nodes in this community are weakly interconnected._
- **Why does `Track` connect `Community 3` to `Community 0`, `Community 1`, `Community 5`, `Community 133`, `Community 9`, `Community 10`, `Community 11`, `Community 14`, `Community 15`, `Community 19`, `Community 150`, `Community 28`, `Community 30`, `Community 33`, `Community 35`, `Community 36`, `Community 37`, `Community 42`, `Community 43`, `Community 44`, `Community 49`, `Community 52`, `Community 53`, `Community 54`, `Community 57`, `Community 61`, `Community 62`, `Community 71`, `Community 200`, `Community 75`, `Community 77`, `Community 78`, `Community 210`, `Community 82`, `Community 212`, `Community 83`, `Community 86`, `Community 218`, `Community 94`, `Community 104`, `Community 115`, `Community 119`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 124 inferred relationships involving `Track` (e.g. with `save_cycle_inputs()` and `StormState`) actually correct?**
  _`Track` has 124 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.03966942148760331 - nodes in this community are weakly interconnected._