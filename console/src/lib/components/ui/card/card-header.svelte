<script lang="ts">
	import { cn } from '$lib/utils';
	import type { HTMLAttributes } from 'svelte/elements';

	interface Props extends HTMLAttributes<HTMLDivElement> {
		class?: string;
	}
	let { class: className, children, ...rest }: Props = $props();
</script>

<div class={cn('flex items-baseline justify-between gap-3 border-b border-border px-4 py-3', className)} {...rest}>
	{@render children?.()}
</div>
