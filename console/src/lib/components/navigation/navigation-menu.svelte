<script lang="ts" module>
	import type { Component } from "svelte";

	/** A dropdown's sub-item -- either an icon + label row (set `icon`) or
	 * a title + description row (set `description`, the common case). */
	export interface NavSubItem {
		href: string;
		title: string;
		description?: string;
		icon?: Component<Record<string, unknown>>;
	}

	export interface NavLinkEntry {
		type?: "link";
		href: string;
		label: string;
	}

	export interface NavDropdownEntry {
		type: "dropdown";
		label: string;
		items: NavSubItem[];
		/** 2 for a wider grid (the "Components" pattern); 1 (default) for
		 * a simple stacked list (the "Getting started" pattern). */
		columns?: 1 | 2;
	}

	export type NavEntry = NavLinkEntry | NavDropdownEntry;
</script>

<script lang="ts">
	/**
	 * Data-driven top nav bar -- generalized from a hardcoded shadcn-svelte
	 * navigation-menu demo (Getting started / Components / With Icon /
	 * Docs) into a reusable component: a `NavEntry[]` in, the same two
	 * patterns the demo showed (a plain link, or a dropdown of either
	 * title+description rows or icon+label rows) out. site-header.svelte
	 * is the first real consumer -- currently all plain links, but the
	 * dropdown path exists for when a nav item (e.g. Docs) grows
	 * sub-links without needing a different component.
	 */
	import * as NavigationMenu from "$lib/components/ui/navigation-menu/index.js";
	import { cn } from "$lib/utils";

	interface Props {
		items: NavEntry[];
		/** Highlights a plain-link entry as the current route. Left to the
		 * caller rather than baked in here -- "active" depends on the route
		 * tree each caller renders against (see site-header.svelte and
		 * mobile-sidebar.svelte, which both define their own). */
		isActive?: (href: string) => boolean;
		class?: string;
	}
	let { items, isActive, class: className }: Props = $props();
</script>

{#snippet subItem(item: NavSubItem)}
	<li>
		<NavigationMenu.Link href={item.href} class={item.icon ? "flex-row items-center gap-2" : undefined}>
			{#if item.icon}
				<item.icon />
				{item.title}
			{:else}
				<div class="flex flex-col gap-1 text-sm">
					<div class="font-medium leading-none">{item.title}</div>
					{#if item.description}
						<div class="text-muted-foreground line-clamp-2">{item.description}</div>
					{/if}
				</div>
			{/if}
		</NavigationMenu.Link>
	</li>
{/snippet}

<NavigationMenu.Root viewport={false} class={cn("max-w-none", className)}>
	<NavigationMenu.List class="gap-0.5">
		{#each items as entry (entry.type === "dropdown" ? entry.label : entry.href)}
			{#if entry.type === "dropdown"}
				<NavigationMenu.Item>
					<NavigationMenu.Trigger>{entry.label}</NavigationMenu.Trigger>
					<NavigationMenu.Content>
						<ul class={cn("w-80", entry.columns === 2 && "w-125 grid grid-cols-2 gap-2")}>
							{#each entry.items as item (item.href)}
								{@render subItem(item)}
							{/each}
						</ul>
					</NavigationMenu.Content>
				</NavigationMenu.Item>
			{:else}
				<NavigationMenu.Item>
					<NavigationMenu.Link
						href={entry.href}
						active={isActive?.(entry.href)}
						class={cn(
							"px-3 py-1.5 text-sm font-medium",
							isActive?.(entry.href)
								? "bg-surface-raised text-text"
								: "text-text-muted hover:text-text",
						)}
					>
						{entry.label}
					</NavigationMenu.Link>
				</NavigationMenu.Item>
			{/if}
		{/each}
	</NavigationMenu.List>
</NavigationMenu.Root>
