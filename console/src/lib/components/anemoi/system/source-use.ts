import type { SourceOut } from '$lib/api/types';

// What the console makes of `used_by` on a /v1/sources row. The mapping
// itself (which model reads which source) is written once, on the API
// (data/sources.py); the Sources page and the system graph both read it
// through here, so neither keeps a copy that could fall behind it.

/** The two `used_by` entries that aren't a model. */
const LABELS = 'labels';
const VERIFICATION = 'verification';

/** The models in `used_by`'s vocabulary (`SourceOut.used_by`), as each
 * reads in a sentence. */
const MODEL_NAMES: Record<string, string> = {
	lstm: 'LSTM',
	cnn: 'CNN',
	transformer: 'Transformer',
	gnn: 'GNN',
	pinn: 'PINN'
};
const MODELS = new Set(Object.keys(MODEL_NAMES));

/**
 * - `input`: at least one model reads it.
 * - `reference`: labels or verification, and never a model input.
 * - `unused`: registered, and nothing uses it yet.
 * - `unknown`: the console can't tell. An API deployed before `used_by`
 *   existed leaves the field out, which is not the same as an empty list;
 *   a newer one may send an entry this console doesn't know.
 */
export type SourceUse = 'input' | 'reference' | 'unused' | 'unknown';

/** The models that read the source as an input, in the API's order. Only
 * the vocabulary's model names count: an entry this console doesn't know
 * may not be a model at all, and drawing it as one would claim data flows
 * into the pipeline that doesn't. */
export function readersOf(source: SourceOut): string[] {
	return (source.used_by ?? []).filter((u) => MODELS.has(u));
}

export function useOf(source: SourceOut): SourceUse {
	if (!source.used_by) return 'unknown';
	if (source.used_by.length === 0) return 'unused';
	if (readersOf(source).length) return 'input';
	return source.used_by.every((u) => u === LABELS || u === VERIFICATION) ? 'reference' : 'unknown';
}

/** Whether `used_by` has an entry outside its vocabulary. */
export function hasUnknownEntry(source: SourceOut): boolean {
	return (source.used_by ?? []).some((u) => !MODELS.has(u) && u !== LABELS && u !== VERIFICATION);
}

/** `used_by` in words: "LSTM · PINN", "labels · verification",
 * "verification only", "not used yet", or a dash when the API didn't say.
 * An entry outside the vocabulary is shown by its key. */
export function usedByText(usedBy: string[] | undefined): string {
	if (!usedBy) return '—';
	if (usedBy.length === 0) return 'not used yet';
	if (usedBy.length === 1 && usedBy[0] === VERIFICATION) return 'verification only';
	return usedBy.map((u) => MODEL_NAMES[u] ?? u).join(' · ');
}

/** What a source is called on the system graph. One the console has no
 * name for is drawn under its registry key. */
const SOURCE_NAMES: Record<string, string> = {
	besttrack_working: 'Working best-track',
	besttrack_final: 'Final best-track',
	gdas_gfs: 'GDAS / GFS t−6',
	era5: 'ERA5',
	goes: 'GOES imagery',
	microwave: 'Microwave imagery',
	sst_ohc: 'SST / OHC',
	ensemble_perturbations: 'GEFS perturbations',
	dropsonde: 'Dropsondes',
	ndbc: 'NDBC buoys'
};

export function sourceName(key: string): string {
	return SOURCE_NAMES[key] ?? key;
}

const ORDER: SourceUse[] = ['input', 'reference', 'unused', 'unknown'];

/** The sources in the order the graph stacks them: what feeds a model
 * first, then labels and verification, then what nothing uses yet. Within
 * each, the API's own order. */
export function byUse(sources: SourceOut[]): SourceOut[] {
	return sources
		.map((source, i) => ({ source, i, rank: ORDER.indexOf(useOf(source)) }))
		.sort((a, b) => a.rank - b.rank || a.i - b.i)
		.map((entry) => entry.source);
}
