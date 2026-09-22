/**
 * The wind-god catalog and colour rules -- mirrors `anemoi.branding` exactly
 * (slugs, colours, architecture, persona). Kept as a static fallback so the
 * console can render its nav and empty states before the first successful
 * `GET /v1/models` call; once that call resolves, prefer its response as the
 * live source (a future rename in branding.py should not require a frontend
 * release, only a re-fetch).
 *
 * Colour rule (Branding wiki, "Colour rules"): these six colours plus
 * FUSION_COLOR are *data* colours -- a colour identifies exactly one model.
 * STRUCTURAL_COLORS exist only to close the eight-point wind rose in the
 * logo glyph and must never be applied to a track line, badge, or tag.
 */

export type Module = 'Anemoi-Core' | 'Anemoi-Spread' | 'Anemoi-Fusion';

export interface WindGod {
	slug: string;
	name: string;
	direction: 'N' | 'S' | 'E' | 'W' | 'NE' | 'NW';
	color: string;
	architecture: string;
	module: Module;
	persona: string;
	/** Short real architecture label, e.g. for a Model Pantheon subtitle
	 * -- unlike the other fields, not mirrored from `anemoi.branding`
	 * (it has no equivalent field), but not invented either: taken
	 * verbatim from each god's own wiki Model-Catalog.md section
	 * heading ("Boreas — LSTM / GRU — models/lstm.py" etc.). */
	role: string;
}

export const GODS: WindGod[] = [
	{
		slug: 'boreas',
		name: 'Boreas',
		direction: 'N',
		color: '#06B6D4',
		architecture: 'lstm',
		module: 'Anemoi-Core',
		persona: 'Fast, violent, first to arrive. The sprinter.',
		role: 'LSTM / GRU'
	},
	{
		slug: 'notus',
		name: 'Notus',
		direction: 'S',
		color: '#F59E0B',
		architecture: 'transformer',
		module: 'Anemoi-Core',
		persona: 'Heavy, deliberate, sees the whole sky. The strategist.',
		role: 'Transformer'
	},
	{
		slug: 'eurus',
		name: 'Eurus',
		direction: 'E',
		color: '#EF4444',
		architecture: 'gnn',
		module: 'Anemoi-Core',
		persona: 'Unpredictable, turbulent, inner-core specialist. The maverick.',
		role: 'GNN'
	},
	{
		slug: 'zephyrus',
		name: 'Zephyrus',
		direction: 'W',
		color: '#10B981',
		architecture: 'cnn',
		module: 'Anemoi-Core',
		persona: 'Gentle, visual, spring-like. The observer.',
		role: 'CNN / U-Net / ResNet'
	},
	{
		slug: 'kaikias',
		name: 'Kaikias',
		direction: 'NE',
		color: '#8B5CF6',
		architecture: 'pinn',
		module: 'Anemoi-Core',
		persona: 'Rigid, constrained, unyielding. The disciplinarian.',
		role: 'PINN / Neural ODE'
	},
	{
		slug: 'skiron',
		name: 'Skiron',
		direction: 'NW',
		color: '#EC4899',
		architecture: 'diffusion',
		module: 'Anemoi-Spread',
		persona: 'Generative, spreading, mist-like. The oracle.',
		role: 'Diffusion'
	}
];

export const FUSION_COLOR = '#F8FAFC';
export const FUNCTIONAL_COLORS = {
	Eye: '#F8FAFC', // oklch(98.42% 0.0034 247.86)
	Cirrus: '#94A3B8', // oklch(71.07% 0.0351 256.79)
	Cumulus: '#64748B', // oklch(55.44% 0.0407 257.42)
	Landfall: '#F43F5E', // oklch(64.50% 0.2154 16.44)
	Clear: '#22D3EE' // oklch(79.71% 0.1339 211.53)
} as const;
export const STRUCTURAL_COLORS: Record<'SE' | 'SW', string> = {
	SE: '#FB923C', // Euronotus -- oklch(75.76% 0.1590 55.93); structural-only, repurposed as Training in v3
	SW: '#A3E635' // Lips -- oklch(84.93% 0.2073 128.85); structural-only, repurposed as Degraded in v3
};
export const STATUS_COLORS = {
	online: FUNCTIONAL_COLORS.Clear,
	training: STRUCTURAL_COLORS.SE,
	degraded: STRUCTURAL_COLORS.SW
} as const;

const BY_SLUG = new Map(GODS.map((g) => [g.slug, g]));
const BY_ARCHITECTURE = new Map(GODS.map((g) => [g.architecture, g]));

/** Resolve a god by slug or architecture, case-insensitively. */
export function god(slugOrArchitecture: string): WindGod | undefined {
	const key = slugOrArchitecture.toLowerCase();
	return BY_SLUG.get(key) ?? BY_ARCHITECTURE.get(key);
}

export function colorFor(slugOrArchitecture: string): string {
	if (slugOrArchitecture === 'fusion') return FUSION_COLOR;
	return god(slugOrArchitecture)?.color ?? 'var(--color-text-faint)';
}

/** North, south, east, west, then the diagonals -- the order the logo glyph
 * assembles in and the order status panels list (Branding wiki). */
export const GOD_ORDER = ['boreas', 'notus', 'eurus', 'zephyrus', 'kaikias', 'skiron'];
