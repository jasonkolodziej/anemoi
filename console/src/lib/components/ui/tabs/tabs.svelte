<script lang="ts" module>
	export interface TabItem {
		value: string;
		label: string;
	}
</script>

<script lang="ts">
	import { Tabs as TabsPrimitive } from 'bits-ui';
	import { cn } from '$lib/utils';

	interface Props {
		items: TabItem[];
		value: string;
		onValueChange?: (v: string) => void;
		class?: string;
		children?: import('svelte').Snippet<[{ value: string }]>;
	}

	let { items, value = $bindable(), onValueChange, class: className, children }: Props = $props();
</script>

<TabsPrimitive.Root bind:value {onValueChange} class={cn('w-full', className)}>
	<TabsPrimitive.List
		class="inline-flex items-center gap-1 rounded-md border border-border bg-surface p-1"
	>
		{#each items as item (item.value)}
			<TabsPrimitive.Trigger
				value={item.value}
				class="rounded-sm px-3 py-1.5 text-xs font-medium text-text-muted transition-colors data-[state=active]:bg-surface-raised data-[state=active]:text-text"
			>
				{item.label}
			</TabsPrimitive.Trigger>
		{/each}
	</TabsPrimitive.List>
	{#each items as item (item.value)}
		<TabsPrimitive.Content value={item.value} class="pt-4">
			{@render children?.({ value: item.value })}
		</TabsPrimitive.Content>
	{/each}
</TabsPrimitive.Root>
