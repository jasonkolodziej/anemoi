/**
 * Run `fn` every `intervalMs` while the tab is visible, and once more as soon
 * as a hidden tab becomes visible again. Every API request wakes the billed
 * API container and restarts its 5-minute sleep timer, so a forgotten
 * background tab polling every minute would keep it awake indefinitely (#172).
 * Returns a cleanup function, suitable as an `onMount` return value.
 */
export function pollWhileVisible(fn: () => void, intervalMs: number): () => void {
	const interval = setInterval(() => {
		if (!document.hidden) fn();
	}, intervalMs);
	const onVisibilityChange = () => {
		if (!document.hidden) fn();
	};
	document.addEventListener('visibilitychange', onVisibilityChange);
	return () => {
		clearInterval(interval);
		document.removeEventListener('visibilitychange', onVisibilityChange);
	};
}
