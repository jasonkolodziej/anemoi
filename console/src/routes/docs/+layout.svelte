<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { LayoutData } from './$types';
	import DocsSections from '$lib/components/anemoi/DocsSections.svelte';
	import WikiSearch from '$lib/components/anemoi/WikiSearch.svelte';

	let { data, children }: { data: LayoutData; children: Snippet } = $props();
</script>

<div class="mx-auto max-w-6xl px-6 py-8">
	<div class="mb-6 max-w-md">
		<WikiSearch />
	</div>
	<!-- flex-col below lg -- DocsSections' own <details> takes over there;
	     the lg:flex-row split (sticky Sections rail + content) only makes
	     sense once there's room for it. -->
	<div class="flex flex-col gap-6 lg:flex-row lg:gap-8">
		<DocsSections sections={data.sections} />
		<div class="min-w-0 flex-1">
			{@render children()}
		</div>
	</div>
</div>
