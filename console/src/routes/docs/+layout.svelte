<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { LayoutData } from './$types';
	import DocsSections from '$lib/components/anemoi/DocsSections.svelte';
	import WikiSearch from '$lib/components/anemoi/WikiSearch.svelte';

	let { data, children }: { data: LayoutData; children: Snippet } = $props();
</script>

<div class="mx-auto max-w-6xl px-6 py-8">
	<!-- md:sticky -- without this, scrolling to read a page (or landing
	     directly on a deep #heading anchor) carries the search bar off the
	     top of <main>'s own scroll region right along with everything
	     above it. bg-bg so scrolled-past content doesn't show through
	     underneath -- deliberately full-width (not max-w-md, unlike the
	     input itself): a narrow sticky cover only blocks scrolled content
	     directly behind *it*, leaving the rest of this wide content column
	     (everything to the right of the search box) with nothing covering
	     that same vertical band at all, so scrolled-past text visibly
	     poked out beside the search box instead of under it. Desktop only:
	     below md, the app's own mobile header is already sticky at top-0
	     -- stacking a second top-0 sticky element there would collide
	     with it rather than stack below it. -->
	<div class="mb-6 md:sticky md:top-0 md:z-10 md:bg-bg md:pt-1 md:pb-4">
		<div class="max-w-md">
			<WikiSearch />
		</div>
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
