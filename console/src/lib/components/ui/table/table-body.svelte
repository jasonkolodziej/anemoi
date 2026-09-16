<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	let { children, ...rest }: HTMLAttributes<HTMLTableSectionElement> = $props();
</script>

<tbody {...rest}>
	{@render children?.()}
</tbody>
