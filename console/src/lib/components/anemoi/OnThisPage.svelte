<script lang="ts">
	/**
	 * The right-hand "On This Page" rail from shadcn-svelte's docs
	 * (/docs/forms reference, `data-slot="sidebar-wrapper"`). Categories
	 * (Concepts/Data/Training/etc) live in the main app sidebar now, not
	 * here -- this instead lists the *pages* within the current page's own
	 * category (e.g. "System Architecture", "Data Sources"), with the
	 * active page's own subsections nested and scroll-spied underneath it.
	 * Falls back to a single-page pseudo-category (no sibling pages, just
	 * this page's own headings) for pages the wiki's index doesn't
	 * categorise (Home, and anything the wiki author hasn't sorted yet).
	 */
	import sections from '$lib/wiki-content/sections.json';
	import { cn } from '$lib/utils';

	interface Heading {
		id: string;
		text: string;
		level: number;
	}
	interface Props {
		currentSlug: string;
		currentTitle: string;
		container: HTMLElement | undefined;
	}
	let { currentSlug, currentTitle, container }: Props = $props();

	const category = $derived(
		sections.find((s) => s.pages.some((p) => p.slug === currentSlug)) ?? {
			name: currentTitle,
			pages: [{ slug: currentSlug, title: currentTitle }]
		}
	);

	let headings = $state<Heading[]>([]);
	let activeId = $state('');

	$effect(() => {
		currentSlug;
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

<div data-slot="sidebar-wrapper" class="hidden w-56 shrink-0 xl:block">
	<nav data-slot="sidebar" class="sticky top-20">
		<p class="font-display mb-2 text-[11px] font-semibold tracking-wide text-text-faint uppercase">
			On This Page
		</p>
		<ul class="space-y-1">
			{#each category.pages as p (p.slug)}
				<li>
					<a
						href={`/docs/${p.slug}`}
						class={cn(
							'block py-1 text-xs font-medium transition-colors',
							p.slug === currentSlug ? 'text-text' : 'text-text-muted hover:text-text'
						)}
					>
						{p.title}
					</a>
					{#if p.slug === currentSlug && headings.length > 0}
						<ul class="mt-1 space-y-1 border-l border-border">
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
					{/if}
				</li>
			{/each}
		</ul>
	</nav>
</div>
