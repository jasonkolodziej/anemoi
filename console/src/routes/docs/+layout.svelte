<script lang="ts">
	import type { Snippet } from 'svelte';
	import WikiSearch from '$lib/components/anemoi/WikiSearch.svelte';

	let { children }: { children: Snippet } = $props();
</script>

<div class="mx-auto max-w-6xl px-6 py-8">
	<div class="mb-6 max-w-md">
		<WikiSearch />
	</div>
	{@render children()}
</div>
