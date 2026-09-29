<script lang="ts" module>
	import { type VariantProps, tv } from 'tailwind-variants';

	export const badgeVariants = tv({
		// `w-fit` and `shrink-0` are load-bearing, not decoration, and are in
		// shadcn's own badge base for the same reason: `inline-flex` alone
		// still stretches when the badge is a grid or flex child, which
		// `CardHeader` (a `grid` with stretch justification) makes it. Every
		// badge on Monitoring rendered as a full-card-width bordered bar.
		base: 'inline-flex w-fit shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-sm border px-2 py-0.5 text-xs font-medium leading-none',
		variants: {
			variant: {
				default: 'border-border-strong bg-surface-raised text-text-muted',
				outline: 'border-border-strong bg-transparent text-text-muted',
				solid: 'border-transparent bg-action text-bg'
			}
		},
		defaultVariants: { variant: 'default' }
	});

	export type BadgeVariant = VariantProps<typeof badgeVariants>['variant'];
</script>

<script lang="ts">
	import { cn } from '$lib/utils';
	import type { HTMLAttributes } from 'svelte/elements';

	interface Props extends HTMLAttributes<HTMLSpanElement> {
		variant?: BadgeVariant;
		class?: string;
	}

	let { variant = 'default', class: className, children, ...rest }: Props = $props();
</script>

<span class={cn(badgeVariants({ variant }), className)} {...rest}>
	{@render children?.()}
</span>
