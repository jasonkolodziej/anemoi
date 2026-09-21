import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export * from "$lib/utilities";

export function cn(...inputs: ClassValue[]): string {
	return twMerge(clsx(inputs));
}

//: Mirrors anemoi.time_utils.SYNOPTIC_HOURS -- every real cycle label must
//: land on one of these, or the API rejects it (require_synoptic).
const SYNOPTIC_HOURS = [0, 6, 12, 18] as const;

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

export function formatMinutes(min: number): string {
	const sign = min < 0 ? '-' : '';
	const abs = Math.abs(Math.round(min));
	const h = Math.floor(abs / 60);
	const m = abs % 60;
	return h > 0 ? `${sign}${h}h${String(m).padStart(2, '0')}m` : `${sign}${m}m`;
}
