<script lang="ts">
	/**
	 * Cloudflare Web Analytics' beacon, loaded only once the visitor allows
	 * the cookie banner's `analytics` category (`$lib/consent.svelte`).
	 *
	 * Cloudflare can inject this beacon into every page at its edge on its
	 * own (the site's "automatic setup"). That can't wait for consent, so
	 * the site must be set to JS-snippet installation in the Cloudflare
	 * dashboard, with its token in `PUBLIC_CF_WEB_ANALYTICS_TOKEN` (see
	 * console/README.md). With no token, nothing loads.
	 */
	import { env } from '$env/dynamic/public';
	import { consent } from '$lib/consent.svelte';

	const BEACON_SRC = 'https://static.cloudflareinsights.com/beacon.min.js';

	const token = env.PUBLIC_CF_WEB_ANALYTICS_TOKEN;

	$effect(() => {
		if (!token || !consent.allows('analytics')) return;
		if (document.querySelector(`script[src="${BEACON_SRC}"]`)) return;
		const script = document.createElement('script');
		script.defer = true;
		script.src = BEACON_SRC;
		script.dataset.cfBeacon = JSON.stringify({ token });
		document.head.appendChild(script);
		// Withdrawing consent reloads the page (`ConsentState.decide`): a
		// loaded script can't be taken back out.
	});
</script>
