<script lang="ts">
	import { cn } from '$lib/utils';
	import type { HTMLAttributes } from 'svelte/elements';

	interface Props extends HTMLAttributes<HTMLTableElement> {
		class?: string;
	}
	let { class: className, children, ...rest }: Props = $props();
</script>

<div class="w-full overflow-x-auto">
	<table class={cn('w-full caption-bottom text-sm', className)} {...rest}>
		{@render children?.()}
	</table>
</div>
