<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import HurricaneIcon from '$lib/components/anemoi/HurricaneIcon.svelte';
	import { cn } from '$lib/utils';

	let { children } = $props();

	const nav = [
		{ href: '/', label: 'Storms' },
		{ href: '/models', label: 'Models' },
		{ href: '/sources', label: 'Sources' },
		{ href: '/registry', label: 'Registry' },
		{ href: '/monitoring', label: 'Monitoring' },
		{ href: '/retraining', label: 'Retraining' }
	];

	function isActive(href: string): boolean {
		if (href === '/') return page.url.pathname === '/';
		return page.url.pathname.startsWith(href);
	}
</script>

<div class="flex min-h-screen">
	<aside class="flex w-56 shrink-0 flex-col border-r border-border bg-surface">
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
	<main class="min-w-0 flex-1 overflow-y-auto">
		{@render children?.()}
	</main>
</div>
