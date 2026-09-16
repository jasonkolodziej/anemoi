<script lang="ts" module>
	import { type VariantProps, tv } from 'tailwind-variants';

	export const buttonVariants = tv({
		base: 'inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 whitespace-nowrap',
		variants: {
			variant: {
				default: 'bg-action text-bg hover:bg-action-strong',
				outline:
					'border border-border-strong bg-transparent text-text hover:bg-surface-raised',
				ghost: 'bg-transparent text-text-muted hover:bg-surface-raised hover:text-text',
				destructive: 'bg-transparent text-eurus border border-eurus/40 hover:bg-eurus/10'
			},
			size: {
				default: 'h-9 px-3.5',
				sm: 'h-8 px-3 text-xs',
				icon: 'h-9 w-9'
			}
		},
		defaultVariants: { variant: 'default', size: 'default' }
	});

	export type ButtonVariant = VariantProps<typeof buttonVariants>['variant'];
	export type ButtonSize = VariantProps<typeof buttonVariants>['size'];
</script>

<script lang="ts">
	import { cn } from '$lib/utils';
	import type { HTMLButtonAttributes } from 'svelte/elements';

	interface Props extends HTMLButtonAttributes {
		variant?: ButtonVariant;
		size?: ButtonSize;
		class?: string;
	}

	let {
		variant = 'default',
		size = 'default',
		class: className,
		children,
		...rest
	}: Props = $props();
</script>

<button class={cn(buttonVariants({ variant, size }), className)} {...rest}>
	{@render children?.()}
</button>
