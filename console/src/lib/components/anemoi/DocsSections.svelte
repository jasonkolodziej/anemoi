<script lang="ts">
	/**
	 * The "Sections" nav for /docs/* -- categories parsed at build time from
	 * the wiki's own Home.md "## Page index" (scripts/sync-wiki.mjs's
	 * parseSections), not duplicated by hand. `data-slot="sidebar-wrapper"`/
	 * `"sidebar"` match shadcn-svelte's own Sidebar component's DOM
	 * convention (github.com/shadcn-svelte, /docs/forms reference) -- this
	 * is a lighter, purpose-built version of it rather than the full
	 * generic collapsible/icon-mode/cookie-persisted primitive system,
	 * same call as MobileNav's over the full shadcn Sidebar earlier.
	 *
	 * lg+: a persistent sticky rail. Below that: a native <details>
	 * disclosure -- zero JS needed for the mobile case, no extra state to
	 * wire up for something this simple.
	 */
	import { page } from '$app/state';
	import { cn } from '$lib/utils';

	interface SectionPage {
		slug: string;
		title: string;
	}
	interface Section {
		name: string;
		pages: SectionPage[];
	}
	interface Props {
		sections: Section[];
	}
	let { sections }: Props = $props();

	function isActive(slug: string): boolean {
		return page.params.slug === slug;
	}
</script>

{#snippet sectionList()}
	{#each sections as section (section.name)}
		<div class="mb-4 last:mb-0">
			<p class="font-display mb-1.5 px-2 text-[11px] font-semibold tracking-wide text-text-faint uppercase">
				{section.name}
			</p>
			<ul class="space-y-0.5">
				{#each section.pages as p (p.slug)}
					<li>
						<a
							href={`/docs/${p.slug}`}
							class={cn(
								'block rounded-md px-2 py-1.5 text-sm transition-colors',
								isActive(p.slug)
									? 'bg-surface-raised text-text'
									: 'text-text-muted hover:bg-surface-raised/60 hover:text-text'
							)}
						>
							{p.title}
						</a>
					</li>
				{/each}
			</ul>
		</div>
	{/each}
{/snippet}

<div data-slot="sidebar-wrapper" class="hidden w-56 shrink-0 lg:block">
	<nav
		data-slot="sidebar"
		class="sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto rounded-lg border border-border bg-surface p-3"
	>
		{@render sectionList()}
	</nav>
</div>

<details data-slot="sidebar-wrapper" class="mb-6 rounded-lg border border-border bg-surface p-3 lg:hidden">
	<summary class="font-display cursor-pointer text-sm font-medium text-text">Sections</summary>
	<nav data-slot="sidebar" class="mt-3">
		{@render sectionList()}
	</nav>
</details>
