import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export * from "$lib/utilities";

export function cn(...inputs: ClassValue[]): string {
	return twMerge(clsx(inputs));
}

//: Mirrors anemoi.time_utils.SYNOPTIC_HOURS -- every real cycle label must
//: land on one of these, or the API rejects it (require_synoptic). Exported
//: for the cycle date/time picker's hour selector (CycleDateTimePicker.svelte).
export const SYNOPTIC_HOURS = [0, 6, 12, 18] as const;

/** Most recent synoptic time at or before `d`. Mirrors
 * anemoi.time_utils.floor_synoptic -- a raw `new Date()` is essentially
 * never itself a synoptic time, so any caller building a *default* cycle
 * label (not a user-chosen one) needs this first, not `cycleLabel` alone,
 * or the API rejects it with "is not a 00/06/12/18Z synoptic time". */
export function floorSynoptic(d: Date): Date {
	const hour = Math.max(...SYNOPTIC_HOURS.filter((h) => h <= d.getUTCHours()));
	const floored = new Date(d);
	floored.setUTCHours(hour, 0, 0, 0);
	return floored;
}

/** Cycle label <-> Date. Mirrors anemoi.time_utils.cycle_label/parse_cycle_label.
 * Does NOT snap to a synoptic hour itself (mirrors the Python function
 * exactly, which also just formats whatever hour it's given) -- callers
 * building a *default* label from "now" must call `floorSynoptic` first. */
export function cycleLabel(d: Date): string {
	const pad = (n: number) => String(n).padStart(2, '0');
	return `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}_${pad(d.getUTCHours())}Z`;
}

/** Cycle label -> Date, the inverse of `cycleLabel`. Mirrors
 * anemoi.time_utils.parse_cycle_label. Returns `null` (not a throw) on a
 * malformed label -- callers (the date/time picker syncing with a
 * free-typed text field) need to keep working while the user is
 * mid-edit, not crash on every keystroke that isn't yet a full label. */
export function parseCycleLabel(label: string): Date | null {
	const m = /^(\d{4})(\d{2})(\d{2})_(\d{2})Z$/.exec(label.trim());
	if (!m) return null;
	const [, year, month, day, hour] = m.map(Number);
	const d = new Date(Date.UTC(year, month - 1, day, hour));
	// Reject e.g. "20260231" (Feb 31) rather than silently rolling over to
	// March -- Date.UTC() itself doesn't validate.
	if (d.getUTCFullYear() !== year || d.getUTCMonth() !== month - 1 || d.getUTCDate() !== day) {
		return null;
	}
	return d;
}

export function formatUtc(iso: string): string {
	const d = new Date(iso);
	const pad = (n: number) => String(n).padStart(2, '0');
	return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}Z`;
}

export function formatLatLon(lat: number, lon: number): string {
	const ns = lat >= 0 ? 'N' : 'S';
	const ew = lon >= 0 ? 'E' : 'W';
	return `${Math.abs(lat).toFixed(1)}°${ns} ${Math.abs(lon).toFixed(1)}°${ew}`;
}

/** Real, external, standard NHC Saffir-Simpson wind-speed classification
 * (knots) -- not this app's own invention, and deliberately a distinct
 * color axis from `$lib/branding`'s six god colors (each identifies one
 * model) and `--color-status-*` (model/cycle health): this is storm
 * *severity*, driven by a track point's real `wind_kt`, not either of
 * those. Every hex here is chosen to avoid colliding with a god/status
 * token, so a colored intensity dot is never mistakable for a specific
 * model's track line. */
export const SAFFIR_SIMPSON: { min: number; label: string; color: string }[] = [
	{ min: 137, label: 'CAT 5', color: '#9f1239' },
	{ min: 113, label: 'CAT 4', color: '#b91c1c' },
	{ min: 96, label: 'CAT 3', color: '#dc2626' },
	{ min: 83, label: 'CAT 2', color: '#f97316' },
	{ min: 64, label: 'CAT 1', color: '#facc15' },
	{ min: 34, label: 'TS', color: '#38bdf8' },
	{ min: 0, label: 'TD', color: '#64748b' },
];

/** The Saffir-Simpson bucket a real `windKt` value falls into. */
export function saffirSimpson(windKt: number): { min: number; label: string; color: string } {
	return SAFFIR_SIMPSON.find((c) => windKt >= c.min) ?? SAFFIR_SIMPSON[SAFFIR_SIMPSON.length - 1];
}

export function formatMinutes(min: number): string {
	const sign = min < 0 ? '-' : '';
	const abs = Math.abs(Math.round(min));
	const h = Math.floor(abs / 60);
	const m = abs % 60;
	return h > 0 ? `${sign}${h}h${String(m).padStart(2, '0')}m` : `${sign}${m}m`;
}
