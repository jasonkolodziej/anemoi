/**
 * The last API answer each page rendered, kept in this browser so a return
 * visit can draw it immediately and refresh in the background, instead of
 * a blank page behind the full-page waiter until the API answers.
 *
 * Per-browser convenience only: it never decides what's true, every page
 * still re-fetches on mount, and storage that is unavailable (private
 * windows, blocked site data) or holds something unparseable just reads as
 * "nothing remembered".
 */

// Bump the version when a stored API shape changes incompatibly.
const PREFIX = 'anemoi:last:v1:';

export function recall<T>(key: string): T | null {
	try {
		const raw = localStorage.getItem(PREFIX + key);
		return raw === null ? null : (JSON.parse(raw) as T);
	} catch {
		return null;
	}
}

export function remember(key: string, value: unknown): void {
	try {
		localStorage.setItem(PREFIX + key, JSON.stringify(value));
	} catch {
		/* quota or blocked storage -- the page works the same without it */
	}
}
