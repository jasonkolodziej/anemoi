/**
 * What this browser has agreed to let the console store or load -- the
 * cookie banner's state (`components/site/cookie-banner.svelte`).
 *
 * Nothing optional runs until the visitor chooses. Two categories can be
 * turned on:
 *
 * - `preferences`: `lastKnown`'s copy of the last storms and forecasts each
 *   page drew, kept in localStorage so a return visit draws at once.
 * - `analytics`: Cloudflare Web Analytics' beacon script
 *   (`components/site/cloudflare-analytics.svelte`).
 *
 * Always on, because the site can't work without them: the sign-in session
 * cookie (set only once someone signs in) and this choice itself, which has
 * to be kept somewhere for the banner not to ask again on every page.
 *
 * Read straight from storage when this module loads in the browser, not in
 * a component's `onMount`: a child page's mount (the storm page recalling
 * its last cycle) runs before the root layout's, and has to see the choice.
 * The server never sees one, so it renders no banner and no beacon.
 */
import { browser } from '$app/environment';

export type ConsentCategory = 'preferences' | 'analytics';

export interface ConsentChoice {
	preferences: boolean;
	analytics: boolean;
	/** When the visitor chose, ISO 8601 -- so a later policy change can ask again. */
	decidedAt: string;
}

// Bump the version to ask everyone again (a new category, say).
export const CONSENT_KEY = 'anemoi:consent:v1';

/** localStorage keys that belong to the `preferences` category: lastKnown's
 * pages, and `UserState`'s extras (`user.context.svelte.ts`). */
const PREFERENCE_PREFIXES = ['anemoi:last:', 'user-extra-prefs'];

function readStored(): ConsentChoice | null {
	try {
		const raw = localStorage.getItem(CONSENT_KEY);
		if (raw === null) return null;
		const parsed = JSON.parse(raw) as Partial<ConsentChoice>;
		if (typeof parsed.preferences !== 'boolean' || typeof parsed.analytics !== 'boolean') {
			return null;
		}
		return {
			preferences: parsed.preferences,
			analytics: parsed.analytics,
			decidedAt: String(parsed.decidedAt ?? ''),
		};
	} catch {
		// Blocked storage reads as "not chosen yet": the banner asks, and
		// nothing optional runs.
		return null;
	}
}

function clearPreferenceStorage(): void {
	try {
		for (const key of Object.keys(localStorage)) {
			if (PREFERENCE_PREFIXES.some((prefix) => key.startsWith(prefix))) {
				localStorage.removeItem(key);
			}
		}
	} catch {
		/* nothing stored, or nothing reachable */
	}
}

class ConsentState {
	/** The visitor's choice, or null until they make one. */
	choice = $state<ConsentChoice | null>(browser ? readStored() : null);
	/** The banner reopened from "Cookie settings" after a choice was made. */
	settingsOpen = $state(false);

	allows(category: ConsentCategory): boolean {
		return this.choice?.[category] === true;
	}

	decide(choice: { preferences: boolean; analytics: boolean }): void {
		const hadAnalytics = this.allows('analytics');
		this.choice = { ...choice, decidedAt: new Date().toISOString() };
		this.settingsOpen = false;
		try {
			localStorage.setItem(CONSENT_KEY, JSON.stringify(this.choice));
		} catch {
			/* kept for this page only; the banner asks again next visit */
		}
		if (!choice.preferences) clearPreferenceStorage();
		// A script that has loaded can't be unloaded: start the page again
		// without it.
		if (hadAnalytics && !choice.analytics) location.reload();
	}

	acceptAll(): void {
		this.decide({ preferences: true, analytics: true });
	}

	necessaryOnly(): void {
		this.decide({ preferences: false, analytics: false });
	}

	openSettings(): void {
		this.settingsOpen = true;
	}
}

export const consent = new ConsentState();
