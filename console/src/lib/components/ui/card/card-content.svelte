<script lang="ts">
	import { cn } from '$lib/utils';
	import type { HTMLAttributes } from 'svelte/elements';

	interface Props extends HTMLAttributes<HTMLDivElement> {
		class?: string;
	}
	let { class: className, children, ...rest }: Props = $props();
</script>

<div class={cn('px-4 pb-4', className)} {...rest}>
	{@render children?.()}
</div>
