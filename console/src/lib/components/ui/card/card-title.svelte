<script lang="ts">
	import { cn } from '$lib/utils';
	import type { HTMLAttributes } from 'svelte/elements';

	interface Props extends HTMLAttributes<HTMLHeadingElement> {
		class?: string;
	}
	let { class: className, children, ...rest }: Props = $props();
</script>

<h3 class={cn('font-display text-sm font-semibold tracking-tight text-text', className)} {...rest}>
	{@render children?.()}
</h3>
