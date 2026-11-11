<script lang="ts">
	import type { PageData } from './$types';
	import { Card, CardContent } from '$lib/components/ui/card';
	import { renderMermaidDiagrams } from '$lib/wiki/mermaid';
	import OnThisPage from '$lib/components/anemoi/OnThisPage.svelte';

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

<!-- justify-between (not a fixed gap) -- Card is capped at max-w-3xl for a
     readable line length instead of stretching to fill the layout's own
     widened flex-1 slot (docs/+layout.svelte), so whatever room that
     leaves goes entirely between it and OnThisPage, which lands flush
     against the far edge instead of hugging the content. Matches
     shadcn-svelte's /docs proportions: a fixed-width reading column with
     the On This Page rail pushed out to the gutter, not snug beside it. -->
<div class="flex justify-between gap-6">
	<Card class="w-full max-w-3xl">
		<CardContent class="pt-6">
			<div bind:this={contentEl} class="wiki-prose">
				<!-- eslint-disable-next-line svelte/no-at-html-tags -->
				{@html data.html}
			</div>
		</CardContent>
	</Card>
	<OnThisPage container={contentEl} refreshKey={data.slug} related={data.related} />
</div>
