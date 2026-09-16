import { apiFetch } from './client';
import type {
	ActivePin,
	CycleResult,
	DriftReportOut,
	HealthOut,
	ModelCatalog,
	RegistryEntry,
	RetrainJobOut,
	RunCycleRequest,
	ScheduleOut,
	SkewReportOut,
	SourceOut,
	StormDetail,
	StormSummary
} from './types';

export const health = () => apiFetch<HealthOut>('/v1/health');
export const getModels = () => apiFetch<ModelCatalog>('/v1/models');
export const getSources = () => apiFetch<SourceOut[]>('/v1/sources');

export const getSchedule = (date: string, worstCase = false) =>
	apiFetch<ScheduleOut>('/v1/schedule', { query: { date, worst_case: worstCase } });

export const listStorms = () => apiFetch<StormSummary[]>('/v1/storms');
export const getStorm = (stormId: string) => apiFetch<StormDetail>(`/v1/storms/${stormId}`);

export const runCycle = (stormId: string, body: RunCycleRequest) =>
	apiFetch<CycleResult>(`/v1/storms/${stormId}/cycles`, {
		method: 'POST',
		body: JSON.stringify(body)
	});

export const getCycle = (stormId: string, cycle: string) =>
	apiFetch<CycleResult>(`/v1/storms/${stormId}/cycles/${cycle}`);

export const listRegistry = () => apiFetch<RegistryEntry[]>('/v1/registry');
export const getModelRegistry = (model: string) => apiFetch<RegistryEntry>(`/v1/registry/${model}`);
export const getActivePin = () => apiFetch<ActivePin | null>('/v1/registry/pins/active');

export const getDriftAll = () => apiFetch<DriftReportOut[]>('/v1/monitoring/drift');
export const getDrift = (model: string) => apiFetch<DriftReportOut>(`/v1/monitoring/drift/${model}`);
export const getSkew = (leadHours = 48) =>
	apiFetch<SkewReportOut>('/v1/monitoring/skew', { query: { lead_hours: leadHours } });

export const getRetrainTriggers = () => apiFetch<RetrainJobOut[]>('/v1/retraining/triggers');
