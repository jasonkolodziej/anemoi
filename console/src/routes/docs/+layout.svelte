<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { LayoutData } from './$types';
	import DocsSections from '$lib/components/anemoi/DocsSections.svelte';
	import WikiSearch from '$lib/components/anemoi/WikiSearch.svelte';

	let { data, children }: { data: LayoutData; children: Snippet } = $props();
</script>

<div class="mx-auto max-w-360 px-6 py-8 lg:px-10">
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
	     with it rather than stack below it. top-0 here is relative to
	     <main>'s own scroll container (overflow-y-auto, +layout.svelte),
	     not the viewport -- the site header lives outside that scroll
	     container as a normal-flow sibling, so this never collides with
	     it even though both are nominally "sticky top-0". -->
	<div class="mb-6 md:sticky md:top-0 md:z-10 md:bg-bg md:pt-1 md:pb-4">
		<div class="max-w-md">
			<WikiSearch />
		</div>
	</div>
	<!-- flex-col below lg -- DocsSections' own <details> takes over there;
	     the lg:flex-row split (sticky Sections rail + content) only makes
	     sense once there's room for it. Wider gaps than the rest of the
	     app (xl:gap-16) -- #171's top nav freed up the ~224px a permanent
	     left sidebar used to cost every route, so this is the one place
	     with enough room to actually use it (shadcn-svelte's own /docs is
	     the reference this was built from -- see docs/[slug]/+page.svelte
	     for the matching content-width cap + On This Page rail pushed to
	     the far edge, same idea). -->
	<div class="flex flex-col gap-6 lg:flex-row lg:gap-10 xl:gap-16">
		<DocsSections sections={data.sections} />
		<div class="min-w-0 flex-1">
			{@render children()}
		</div>
	</div>
</div>
