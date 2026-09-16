<script lang="ts">
	import { cn } from '$lib/utils';
	import type { HTMLAttributes } from 'svelte/elements';
	interface Props extends HTMLAttributes<HTMLTableCellElement> {
		class?: string;
	}
	let { class: className, children, ...rest }: Props = $props();
</script>

<td class={cn('px-3 py-2.5 align-middle text-text', className)} {...rest}>
	{@render children?.()}
</td>
