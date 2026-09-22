<script lang="ts">
	/**
	 * Search input + results dropdown over the bundled wiki content (see
	 * $lib/wiki/search.ts). The MiniSearch index is only built the first
	 * time someone actually searches -- debounced, so typing quickly
	 * doesn't rebuild/query on every keystroke.
	 */
	import { searchWiki, type WikiSearchResult } from '$lib/wiki/search';

	let query = $state('');
	let results = $state<WikiSearchResult[]>([]);
	let open = $state(false);
	let loading = $state(false);
	let debounceHandle: ReturnType<typeof setTimeout> | undefined;

	function onInput() {
		open = true;
		clearTimeout(debounceHandle);
		if (!query.trim()) {
			results = [];
			return;
		}
		loading = true;
		debounceHandle = setTimeout(async () => {
			results = await searchWiki(query);
			loading = false;
		}, 150);
	}

	function close() {
		open = false;
	}
</script>

<svelte:window onclick={close} />

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="relative" onclick={(e) => e.stopPropagation()}>
	<input
		type="search"
		placeholder="Search the docs…"
		bind:value={query}
		oninput={onInput}
		onfocus={() => (open = true)}
		class="font-data w-full rounded-md border border-border-strong bg-bg px-3 py-2 text-sm text-text placeholder:text-text-faint focus-visible:outline-none"
	/>
	{#if open && query.trim()}
		<div class="absolute z-20 mt-1.5 w-full rounded-lg border border-border bg-surface py-1.5 shadow-lg">
			{#if loading}
				<p class="px-3 py-2 text-xs text-text-faint">Searching…</p>
			{:else if results.length === 0}
				<p class="px-3 py-2 text-xs text-text-faint">No matches for "{query}".</p>
			{:else}
				{#each results as r (r.slug)}
					<a
						href={`/docs/${r.slug}`}
						class="block px-3 py-2 hover:bg-surface-raised/60"
						onclick={() => (open = false)}
					>
						<p class="font-display text-sm font-medium text-text">{r.title}</p>
						<p class="mt-0.5 text-xs text-text-muted">{r.excerpt}</p>
					</a>
				{/each}
			{/if}
		</div>
	{/if}
</div>
