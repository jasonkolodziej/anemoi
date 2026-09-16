<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	let { children, ...rest }: HTMLAttributes<HTMLTableSectionElement> = $props();
</script>

<thead class="border-b border-border" {...rest}>
	{@render children?.()}
</thead>
