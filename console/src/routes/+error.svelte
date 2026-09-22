<script lang="ts">
	import { page } from '$app/state';
	import HurricaneIcon from '$lib/components/anemoi/HurricaneIcon.svelte';
</script>

<div class="mx-auto flex max-w-lg flex-col items-center gap-4 px-6 py-24 text-center">
	<HurricaneIcon size={40} />
	<p class="font-data text-sm text-text-faint">{page.status}</p>
	<h1 class="font-display text-xl font-semibold text-text">
		{page.error?.message ?? 'Page not found'}
	</h1>
	<p class="text-sm text-text-muted">
		There's no real forecast data at this address. Storms live at the root, not under
		<code class="font-data text-text-faint">/storms</code> on its own.
	</p>
	<a
		href="/"
		class="mt-2 rounded-md bg-action px-4 py-2 text-sm font-medium text-bg hover:bg-action-strong"
	>
		&larr; Active storms
	</a>
</div>
