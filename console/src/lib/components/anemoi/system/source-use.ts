// What the console makes of `used_by` on a /v1/sources row. The mapping
// itself (which model reads which source) is written once, on the API
// (data/sources.py); the console reads it through here and keeps no copy
// that could fall behind it.

/** The `used_by` entry for a source kept for verifying forecasts. */
const VERIFICATION = 'verification';

/** A model key as it reads in a sentence. A model the API gains before
 * the console knows its name is shown by its key. */
const MODEL_NAMES: Record<string, string> = {
	lstm: 'LSTM',
	cnn: 'CNN',
	transformer: 'Transformer',
	gnn: 'GNN',
	pinn: 'PINN'
};

/** `used_by` in words: "LSTM · PINN", "labels · verification",
 * "verification only", "not used yet", or a dash when the API didn't say. */
export function usedByText(usedBy: string[] | undefined): string {
	if (!usedBy) return '—';
	if (usedBy.length === 0) return 'not used yet';
	if (usedBy.length === 1 && usedBy[0] === VERIFICATION) return 'verification only';
	return usedBy.map((u) => MODEL_NAMES[u] ?? u).join(' · ');
}
