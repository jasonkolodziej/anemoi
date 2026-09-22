/**
 * TypeScript mirror of `anemoi.api.schemas` (see the wiki's API page in the
 * anemoi repo). Field names match the FastAPI response models exactly --
 * `CyclePayload` in particular is byte-for-byte the CLI's dissemination
 * JSON, so keep it that way rather than "improving" field names here.
 */

export interface WindGodOut {
	slug: string;
	name: string;
	direction: string;
	color: string;
	architecture: string;
	module: string;
	persona: string;
}

export interface ModelCatalog {
	gods: WindGodOut[];
	fusion_color: string;
	structural_colors: Record<string, string>;
}

export interface SourceOut {
	key: string;
	provider: string;
	role: 'operational' | 'pretrain_only' | 'labels_only';
	is_operational: boolean;
	typical_latency_minutes: number;
	max_latency_minutes: number;
	fmt: string;
	retention: string;
	notes: string;
}

export interface StageOut {
	stage: string;
	start: string;
	end_target: string;
	end_max: string;
}

export interface CyclePlanOut {
	label: string;
	target_time: string;
	cycle_start: string;
	advisory_deadline: string;
	core_ready_target: string;
	spread_ready_target: string;
	spread_ready_max: string;
	margin_target_minutes: number;
	margin_max_minutes: number;
	meets_advisory_deadline: boolean;
	vitals_estimated: boolean;
	load_shed: boolean;
	degraded: boolean;
	stages: StageOut[];
}

export interface ScheduleOut {
	date: string;
	worst_case: boolean;
	plans: CyclePlanOut[];
}

export interface ConeSegmentOut {
	lead_hours: number;
	lat: number;
	lon: number;
	radius_nm: number;
	basis: 'ensemble' | 'climatology';
}

/** Exact shape of CycleOutput.payload() -- the dissemination JSON. */
export interface CyclePayload {
	cycle: string;
	issued_at: string;
	advisory_deadline: string;
	nwp_cycle_lag_hours: number;
	vitals: 'observed' | 'estimated';
	ensemble_size: number;
	rapid_intensification: boolean;
	ri_probability: number;
	cone: ConeSegmentOut[];
	flags: string[];
}

export interface IntensityPercentiles {
	lead_hours: number;
	p10: number;
	p25: number;
	p50: number;
	p75: number;
	p90: number;
}

export interface TrackPointOut {
	lead_hours: number;
	lat: number;
	lon: number;
	wind_kt: number;
}

export interface CycleProducts {
	deterministic_track: TrackPointOut[];
	contributors: Record<string, number>;
	intensity_pdf: IntensityPercentiles[];
	landfall_probability: number | null;
	notes: string[];
	degraded: boolean;
}

export interface CycleResult {
	storm_id: string;
	payload: CyclePayload;
	products: CycleProducts;
	on_time: boolean;
}

export interface FixOut {
	valid_time: string;
	lat: number;
	lon: number;
	max_wind_kt: number;
	min_pressure_mb: number;
	quality: 'working' | 'final' | 'emulated' | 'estimated';
}

export interface StormSummary {
	storm_id: string;
	season: number;
	active: boolean;
	latest_fix: FixOut;
	peak_wind_kt: number;
	last_cycle: string | null;
}

export interface StormDetail extends StormSummary {
	history: FixOut[];
	cycles: string[];
}

export interface RunCycleRequest {
	cycle: string;
	lat?: number | null;
	lon?: number | null;
	wind_kt?: number | null;
	members?: number;
	worst_case?: boolean;
	coastline_lat?: number | null;
	coastline_lon?: number | null;
}

export interface ModelVersionOut {
	name: string;
	version: number;
	stage: 'none' | 'staging' | 'production' | 'archived';
	run_id: string;
	metrics: Record<string, number>;
	created_at: string;
	tags: Record<string, string>;
	input_flavor: string;
	latent_signature: string | null;
	checkpoint_uri: string | null;
}

export interface RegistryEntry {
	model: string;
	latest: ModelVersionOut | null;
	production: ModelVersionOut | null;
	versions: ModelVersionOut[];
}

export interface ActivePin {
	label: string;
	latent_signature: string;
	members: Record<string, number>;
}

export interface FeatureDriftOut {
	name: string;
	standardized_shift: number;
	variance_ratio: number;
	drifted: boolean;
}

export interface DriftReportOut {
	model: string;
	flavor: string;
	generated_at: string;
	features: FeatureDriftOut[];
	n_live: number;
	alert: boolean;
	summary: string;
}

export interface SkewReportOut {
	lead_hours: number;
	n: number;
	window_start: string;
	window_end: string;
	mean_track_delta_nm: number;
	mean_abs_intensity_delta_kt: number;
	intensity_bias_kt: number;
	alert: boolean;
	reasons: string[];
}

export interface RetrainJobOut {
	model: string;
	reason: string;
	mode: string;
	cascaded: boolean;
	note: string;
	trigger_tag: string;
}

export interface HealthOut {
	status: string;
	api_version: string;
	anemoi_version: string;
	torch_available: boolean;
	/** "demo" (synthetic, always available) or "real" (real HURDAT2 storms + real trained models). */
	state_mode: 'demo' | 'real';
}

export interface StreamMessage {
	type: 'cycle' | 'error';
	data?: CycleResult;
	detail?: string;
}
