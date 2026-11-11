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

/** Minutes after its synoptic time that a cycle is scheduled to run:
 * anemoi-api-real's cron (`30 1,7,13,19 * * *`, docker/api/wrangler.jsonc)
 * fires at t+1:30. Kept in sync by hand. */
export const CYCLE_RUN_DELAY_MIN = 90;

/** How far past a storm's latest fix a cycle may start before the API
 * refuses it as outside the storm's track. Mirrors
 * anemoi.api.cycle_policy.LIFETIME_GRACE; kept in sync by hand. */
export const CYCLE_LIFETIME_GRACE_H = 12;

const SIX_HOURS_MS = 6 * 3_600_000;

/** The cycle the storm page's "Run a new cycle" form offers until the user
 * picks one: the synoptic cycle the clock is in, while that is still inside
 * the storm's track; for a storm whose track ended long ago, its newest
 * cycle it doesn't have yet (else its last fix's), since today's label would
 * only be refused. Recomputed as the clock and the storm move, so a page
 * left open doesn't keep offering the cycle it was opened in. */
export function defaultCycleToRun(
	storm: { latest_fix: { valid_time: string }; history: { valid_time: string }[]; cycles: string[] } | null,
	now: Date,
): string {
	const current = floorSynoptic(now);
	if (!storm) return cycleLabel(current);
	const latest = new Date(storm.latest_fix.valid_time);
	if (current.getTime() <= latest.getTime() + CYCLE_LIFETIME_GRACE_H * 3_600_000) {
		return cycleLabel(current);
	}
	const first = new Date(storm.history[0]?.valid_time ?? storm.latest_fix.valid_time);
	const have = new Set(storm.cycles);
	for (let t = floorSynoptic(latest); t >= first; t = new Date(t.getTime() - SIX_HOURS_MS)) {
		if (!have.has(cycleLabel(t))) return cycleLabel(t);
	}
	return cycleLabel(floorSynoptic(latest));
}

/** The first and last cycle the API will run for this storm right now, or
 * null when there is none. From its first fix, to whichever comes first:
 * `CYCLE_LIFETIME_GRACE_H` past its latest fix (`cycle_policy.check_run`),
 * or the synoptic time the clock is in (`RealState._check_not_started`
 * refuses a cycle that hasn't begun). A day outside this range, picked from
 * the calendar, could only be refused. */
export function runnableCycleRange(
	storm: { latest_fix: { valid_time: string }; history: { valid_time: string }[] } | null,
	now: Date,
): { first: Date; last: Date } | null {
	if (!storm) return null;
	const firstFix = new Date(storm.history[0]?.valid_time ?? storm.latest_fix.valid_time);
	// Rounded up: a fix off the synoptic hours still can't start a cycle
	// before it.
	const first = floorSynoptic(firstFix);
	if (first < firstFix) first.setTime(first.getTime() + SIX_HOURS_MS);
	const graceEnd = new Date(
		new Date(storm.latest_fix.valid_time).getTime() + CYCLE_LIFETIME_GRACE_H * 3_600_000,
	);
	const last = floorSynoptic(graceEnd < now ? graceEnd : now);
	return first <= last ? { first, last } : null;
}

/** Why `label` can't be run as typed, or null when it's a well-formed
 * synoptic cycle label. */
export function cycleLabelProblem(label: string): string | null {
	const parsed = parseCycleLabel(label);
	if (!parsed) return 'Enter a cycle as YYYYMMDD_HHZ, e.g. 20261015_12Z.';
	if (!(SYNOPTIC_HOURS as readonly number[]).includes(parsed.getUTCHours())) {
		return 'Cycles start at 00, 06, 12 or 18Z.';
	}
	return null;
}

/** "08/12Z": day-of-month and hour, UTC -- a forecast point's valid time,
 * compact enough for a map label. */
export function formatDayHourZ(d: Date): string {
	const pad = (n: number) => String(n).padStart(2, '0');
	return `${pad(d.getUTCDate())}/${pad(d.getUTCHours())}Z`;
}

/** Valid time of a forecast lead from a cycle label, or null if the label
 * doesn't parse. */
export function leadValidTime(cycle: string, leadHours: number): Date | null {
	const start = parseCycleLabel(cycle);
	return start ? new Date(start.getTime() + leadHours * 3_600_000) : null;
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
