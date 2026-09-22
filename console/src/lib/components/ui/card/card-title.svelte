<script lang="ts">
	import { cn } from '$lib/utils';
	import type { HTMLAttributes } from 'svelte/elements';

	interface Props extends HTMLAttributes<HTMLHeadingElement> {
		class?: string;
	}
	let { class: className, children, ...rest }: Props = $props();
</script>

<h3
	class={cn(
		'font-display text-[13px] font-medium tracking-[0.08em] text-text-muted uppercase',
		className,
	)}
	{...rest}
>
	{@render children?.()}
</h3>
