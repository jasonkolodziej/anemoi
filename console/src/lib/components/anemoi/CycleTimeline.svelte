<script lang="ts">
	/** Horizontal stage timeline for one CyclePlan -- t+0:00 through the
	 * advisory deadline, target duration solid, max-budget overrun hatched.
	 * Per-segment detail is a real shadcn `Tooltip` (bits-ui, real hover/
	 * focus positioning) rather than the browser's own `title` attribute --
	 * found for real in the branding-proposal review: the native tooltip's
	 * placement is left to the browser and clipped/overlapped the next
	 * stage's own label in this card's real narrow width. */
	import type { CyclePlanOut } from '$lib/api/types';
	import { formatUtc } from '$lib/utils';
	import * as Tooltip from '$lib/components/ui/tooltip';

	interface Props {
		plan: CyclePlanOut;
	}
	let { plan }: Props = $props();

	const stageLabel: Record<string, string> = {
		assembly: 'Assembly',
		preprocess: 'Preprocess',
		deterministic: 'Deterministic',
		fusion: 'Fusion',
		diffusion: 'Diffusion',
		postprocess: 'Post-process'
	};

	const t0 = $derived(new Date(plan.cycle_start).getTime());
	const deadline = $derived(new Date(plan.advisory_deadline).getTime());
	const totalMs = $derived(deadline - t0);

	function pct(iso: string): number {
		return Math.max(0, Math.min(100, ((new Date(iso).getTime() - t0) / totalMs) * 100));
	}
</script>

<div class="space-y-2">
	<div class="flex items-center justify-between text-xs">
		<span class="font-data text-text-muted">{plan.label}</span>
		<span
			class="font-data"
			class:text-zephyrus={plan.meets_advisory_deadline}
			class:text-eurus={!plan.meets_advisory_deadline}
		>
			{plan.meets_advisory_deadline ? 'meets advisory deadline' : 'misses advisory deadline'}
		</span>
	</div>
	<!-- Relies on the single `Tooltip.Provider` at the root layout
	     (+layout.svelte) -- bits-ui's own singleton-tooltip model expects
	     exactly one, not one per component. -->
	<div class="relative h-6 w-full overflow-hidden rounded-sm bg-surface-raised">
		{#each plan.stages as stage (stage.stage)}
			<Tooltip.Root>
				<Tooltip.Trigger
					aria-label={`${stageLabel[stage.stage] ?? stage.stage}: ${formatUtc(stage.start)} to ${formatUtc(stage.end_target)}`}
					class="absolute top-0 h-full border-0 border-r border-bg/60 bg-action/25 p-0"
					style={`left: ${pct(stage.start)}%; width: ${pct(stage.end_target) - pct(stage.start)}%;`}
				></Tooltip.Trigger>
				<Tooltip.Content side="top">
					<p class="font-data">
						{stageLabel[stage.stage] ?? stage.stage}: {formatUtc(stage.start)} → {formatUtc(
							stage.end_target
						)}
					</p>
				</Tooltip.Content>
			</Tooltip.Root>
			<Tooltip.Root>
				<Tooltip.Trigger
					aria-label={`${stageLabel[stage.stage] ?? stage.stage} max budget: through ${formatUtc(stage.end_max)}`}
					class="absolute top-0 h-full border-0 bg-[repeating-linear-gradient(45deg,color-mix(in_oklab,var(--color-action)_18%,transparent),color-mix(in_oklab,var(--color-action)_18%,transparent)_3px,transparent_3px,transparent_6px)] p-0"
					style={`left: ${pct(stage.end_target)}%; width: ${pct(stage.end_max) - pct(stage.end_target)}%;`}
				></Tooltip.Trigger>
				<Tooltip.Content side="top">
					<p class="font-data">
						{stageLabel[stage.stage] ?? stage.stage} max budget: through {formatUtc(
							stage.end_max
						)}
					</p>
				</Tooltip.Content>
			</Tooltip.Root>
		{/each}
		<div class="absolute top-0 h-full w-px bg-fusion/70" style="left: 100%"></div>
	</div>
	<div class="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-text-faint">
		{#each plan.stages as stage (stage.stage)}
			<span>{stageLabel[stage.stage] ?? stage.stage}</span>
		{/each}
		<span class="text-fusion/80">advisory {formatUtc(plan.advisory_deadline)}</span>
	</div>
</div>
