<script lang="ts">
	import type { PageData } from './$types';
	import { Card, CardContent } from '$lib/components/ui/card';
	import WikiSearch from '$lib/components/anemoi/WikiSearch.svelte';

	let { data }: { data: PageData } = $props();
</script>

<div class="mx-auto max-w-5xl px-6 py-8">
	<header class="mb-6">
		<h1 class="font-display text-2xl font-semibold text-text">Docs</h1>
		<p class="mt-1 text-sm text-text-muted">
			The Anemoi wiki, rendered here -- same source, kept in sync at build time.
		</p>
	</header>

	<div class="mb-8 max-w-md">
		<WikiSearch />
	</div>

	<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
		{#each data.pages as page (page.slug)}
			<a href={`/docs/${page.slug}`} class="hover-lift block">
				<Card class="h-full">
					<CardContent class="pt-4">
						<p class="font-display text-sm font-semibold text-text">{page.title}</p>
					</CardContent>
				</Card>
			</a>
		{/each}
	</div>
</div>
