<script lang="ts">
	import type { PageData } from './$types';
	import { Card, CardContent } from '$lib/components/ui/card';
	import { renderMermaidDiagrams } from '$lib/wiki/mermaid';

	let { data }: { data: PageData } = $props();
	let contentEl = $state<HTMLDivElement>();

	// Navigating between /docs/[slug] pages reuses this component instance
	// (same route, different params) -- onMount alone would only fire once,
	// on the very first doc page visited, and never again on subsequent
	// client-side navigations to a different slug. $effect re-runs whenever
	// data.html changes, which covers both the first render and every nav.
	$effect(() => {
		data.html;
		if (contentEl) renderMermaidDiagrams(contentEl);
	});
</script>

<svelte:head>
	<title>{data.title} · Anemoi Docs</title>
</svelte:head>

<div class="mx-auto max-w-3xl px-6 py-8">
	<a href="/docs" class="text-xs text-text-muted hover:text-text">&larr; Docs</a>
	<Card class="mt-4">
		<CardContent class="pt-6">
			<div bind:this={contentEl} class="wiki-prose">
				<!-- eslint-disable-next-line svelte/no-at-html-tags -->
				{@html data.html}
			</div>
		</CardContent>
	</Card>
</div>
