<script lang="ts">
	/**
	 * The sidebar (+layout.svelte) is desktop-only (`hidden md:flex`) -- a
	 * fixed 224px rail eats over half of a phone viewport otherwise, which is
	 * exactly what shipped before this component existed. Below `md`,
	 * +layout.svelte's top bar renders this instead: a trigger that opens the
	 * same nav list as an off-canvas panel. bits-ui's Dialog gives focus
	 * trap/Escape/outside-click/scroll-lock for free -- this is a styled
	 * Dialog, not a hand-rolled one.
	 */
	import { Dialog } from 'bits-ui';
	import { page } from '$app/state';
	import { cn } from '$lib/utils';
	import HurricaneIcon from './HurricaneIcon.svelte';

	interface NavItem {
		href: string;
		label: string;
	}
	interface Props {
		nav: NavItem[];
	}
	let { nav }: Props = $props();
	let open = $state(false);

	function isActive(href: string): boolean {
		if (href === '/') return page.url.pathname === '/';
		return page.url.pathname.startsWith(href);
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Trigger
		aria-label="Open navigation"
		class="flex h-9 w-9 items-center justify-center rounded-md text-text-muted hover:bg-surface-raised hover:text-text"
	>
		<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
			<line x1="3" y1="6" x2="21" y2="6" />
			<line x1="3" y1="12" x2="21" y2="12" />
			<line x1="3" y1="18" x2="21" y2="18" />
		</svg>
	</Dialog.Trigger>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-bg/70" />
		<Dialog.Content
			class="fixed inset-y-0 left-0 z-50 flex w-72 max-w-[80vw] flex-col border-r border-border bg-surface outline-none"
		>
			<Dialog.Title class="sr-only">Navigation</Dialog.Title>
			<div class="flex items-center justify-between gap-2.5 border-b border-border px-4 py-4">
				<a href="/" onclick={() => (open = false)} class="flex items-center gap-2.5">
					<HurricaneIcon size={26} />
					<div>
						<p class="font-display text-sm font-semibold leading-none text-text">Anemoi</p>
						<p class="mt-1 text-[10px] leading-none text-text-faint">Many winds. One forecast.</p>
					</div>
				</a>
				<Dialog.Close
					aria-label="Close navigation"
					class="flex h-8 w-8 items-center justify-center rounded-md text-text-muted hover:bg-surface-raised hover:text-text"
				>
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
						<line x1="18" y1="6" x2="6" y2="18" />
						<line x1="6" y1="6" x2="18" y2="18" />
					</svg>
				</Dialog.Close>
			</div>
			<nav class="flex-1 space-y-0.5 overflow-y-auto p-2">
				{#each nav as item (item.href)}
					<a
						href={item.href}
						onclick={() => (open = false)}
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
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>
