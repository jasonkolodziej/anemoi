<script lang="ts">
	import { cn } from '$lib/utils';
	import type { HTMLAttributes } from 'svelte/elements';
	interface Props extends HTMLAttributes<HTMLTableRowElement> {
		class?: string;
	}
	let { class: className, children, ...rest }: Props = $props();
</script>

<tr class={cn('border-b border-border last:border-0 hover:bg-surface-raised/60', className)} {...rest}>
	{@render children?.()}
</tr>
