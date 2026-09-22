<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import HurricaneIcon from '$lib/components/anemoi/HurricaneIcon.svelte';
	import MobileNav from '$lib/components/anemoi/MobileNav.svelte';
	import { cn } from '$lib/utils';

	let { children } = $props();

	const nav = [
		{ href: '/', label: 'Storms' },
		{ href: '/models', label: 'Models' },
		{ href: '/sources', label: 'Sources' },
		{ href: '/registry', label: 'Registry' },
		{ href: '/monitoring', label: 'Monitoring' },
		{ href: '/retraining', label: 'Retraining' },
		{ href: '/docs', label: 'Docs' }
	];

	function isActive(href: string): boolean {
		if (href === '/') return page.url.pathname === '/';
		return page.url.pathname.startsWith(href);
	}
</script>

<div class="flex min-h-screen flex-col md:flex-row">
	<!-- Desktop: persistent rail. A fixed 224px sidebar eats over half a
	     phone viewport, so this is `md:`-and-up only -- see MobileNav for
	     the small-screen equivalent below. -->
	<aside
		class="bubble hidden w-56 shrink-0 flex-col border-r border-border/60 pt-[env(safe-area-inset-top)] md:flex"
	>
		<a href="/" class="flex items-center gap-2.5 border-b border-border px-4 py-4">
			<HurricaneIcon size={26} />
			<div>
				<p class="font-display text-sm font-semibold leading-none text-text">Anemoi</p>
				<p class="text-[10px] leading-none text-text-faint mt-1">Many winds. One forecast.</p>
			</div>
		</a>
		<nav class="flex-1 space-y-0.5 p-2">
			{#each nav as item (item.href)}
				<a
					href={item.href}
					class={cn(
						'block rounded-md px-3 py-2 text-sm font-medium transition-colors',
						isActive(item.href)
							? 'bg-surface-raised text-text'
							: 'text-text-muted hover:bg-surface-raised/60 hover:text-text'
					)}
				>
					{item.label}
				</a>
			{/each}
		</nav>
		<div class="border-t border-border p-3 text-[10px] text-text-faint">
			Scope v2.1 · Reference implementation
		</div>
	</aside>

	<!-- Mobile: a slim top bar + off-canvas drawer instead of the rail. -->
	<header
		class="bubble sticky top-0 z-30 flex items-center justify-between gap-2 border-b border-border/60 px-4 pt-[calc(env(safe-area-inset-top)+0.75rem)] pb-3 md:hidden"
	>
		<a href="/" class="flex items-center gap-2">
			<HurricaneIcon size={22} />
			<p class="font-display text-sm font-semibold leading-none text-text">Anemoi</p>
		</a>
		<MobileNav {nav} />
	</header>

	<main class="min-w-0 flex-1 overflow-y-auto">
		{@render children?.()}
	</main>
</div>
