<script lang="ts">
	/**
	 * The right-hand "On This Page" rail from shadcn-svelte's docs
	 * (/docs/forms reference, `data-slot="sidebar-wrapper"`) -- scroll-spied
	 * headings extracted from the rendered wiki content at runtime (ids
	 * already present, see rehype-slug in scripts/sync-wiki.mjs), plus a
	 * "Related" section from each page's own trailing `Related: [...]`
	 * line (scripts/sync-wiki.mjs's extractRelated -- stripped out of the
	 * rendered content itself, so it doesn't show twice). xl+ only: below
	 * that there isn't room for a third column without squeezing the
	 * actual content, and on tablet/mobile scrolling to find a section is
	 * fine.
	 */
	import { cn } from '$lib/utils';

	interface Heading {
		id: string;
		text: string;
		level: number;
	}
	interface RelatedPage {
		slug: string;
		title: string;
	}
	interface Props {
		container: HTMLElement | undefined;
		// Included only so this $effect re-runs on navigation between two
		// /docs/[slug] pages -- `container` itself is the same DOM node
		// across navigations (the route component is reused), so it alone
		// wouldn't retrigger extraction when the slug changes.
		refreshKey: string;
		related?: RelatedPage[];
	}
	let { container, refreshKey, related = [] }: Props = $props();

	let headings = $state<Heading[]>([]);
	let activeId = $state('');

	$effect(() => {
		refreshKey;
		if (!container) {
			headings = [];
			return;
		}

		const els = Array.from(container.querySelectorAll<HTMLElement>('h2, h3'));
		headings = els.map((el) => ({
			id: el.id,
			text: el.textContent ?? '',
			level: el.tagName === 'H3' ? 3 : 2
		}));
		if (els.length === 0) return;

		const observer = new IntersectionObserver(
			(entries) => {
				const visible = entries.find((e) => e.isIntersecting);
				if (visible) activeId = visible.target.id;
			},
			{ rootMargin: '-80px 0px -70% 0px' }
		);
		for (const el of els) observer.observe(el);
		return () => observer.disconnect();
	});
</script>

{#if headings.length > 0 || related.length > 0}
	<div data-slot="sidebar-wrapper" class="hidden w-48 shrink-0 xl:block">
		<nav data-slot="sidebar" class="sticky top-20 space-y-6 bg-bg py-1">
			{#if headings.length > 0}
				<div>
					<p class="font-display mb-2 text-[11px] font-semibold tracking-wide text-text-faint uppercase">
						On This Page
					</p>
					<ul class="space-y-1 border-l border-border">
						{#each headings as h (h.id)}
							<li style={h.level === 3 ? 'padding-left: 1.5rem' : 'padding-left: 0.75rem'}>
								<a
									href={`#${h.id}`}
									class={cn(
										'-ml-px block border-l py-0.5 text-xs transition-colors',
										activeId === h.id
											? 'border-action text-text'
											: 'border-transparent text-text-faint hover:text-text-muted'
									)}
								>
									{h.text}
								</a>
							</li>
						{/each}
					</ul>
				</div>
			{/if}
			{#if related.length > 0}
				<div>
					<p class="font-display mb-2 text-[11px] font-semibold tracking-wide text-text-faint uppercase">
						Related
					</p>
					<ul class="space-y-1">
						{#each related as r (r.slug)}
							<li>
								<a href={`/docs/${r.slug}`} class="block py-0.5 text-xs text-text-muted transition-colors hover:text-text">
									{r.title}
								</a>
							</li>
						{/each}
					</ul>
				</div>
			{/if}
		</nav>
	</div>
{/if}
