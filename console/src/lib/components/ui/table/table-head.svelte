<script lang="ts">
	import { cn } from '$lib/utils';
	import type { HTMLAttributes } from 'svelte/elements';
	interface Props extends HTMLAttributes<HTMLTableCellElement> {
		class?: string;
	}
	let { class: className, children, ...rest }: Props = $props();
</script>

<th
	class={cn(
		'h-9 px-3 text-left align-middle text-xs font-medium text-text-faint',
		className
	)}
	{...rest}
>
	{@render children?.()}
</th>
