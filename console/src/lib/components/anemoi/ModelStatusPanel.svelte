<script lang="ts">
	/**
	 * Fusion contribution weights per model, in the brand's own listing
	 * order (north, south, east, west, then diagonals). Bar length is the
	 * weight; colour always the model's own god colour -- never reused
	 * elsewhere in this panel.
	 */
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { GODS, GOD_ORDER, colorFor } from '$lib/branding';

	interface Props {
		contributors: Record<string, number>;
	}
	let { contributors }: Props = $props();

	const rows = $derived(
		GOD_ORDER.map((slug) => {
			const g = GODS.find((x) => x.slug === slug)!;
			return { god: g, weight: contributors[g.architecture] ?? 0 };
		}).filter((r) => r.weight > 0)
	);
	const maxWeight = $derived(Math.max(...rows.map((r) => r.weight), 0.001));
</script>

<Card>
	<CardHeader>
		<CardTitle>Fusion contribution</CardTitle>
	</CardHeader>
	<CardContent class="space-y-2.5">
		{#if rows.length === 0}
			<p class="text-xs text-text-faint">No contributor weights on this cycle.</p>
		{/if}
		{#each rows as row (row.god.slug)}
			<div>
				<div class="mb-1 flex items-center justify-between text-xs">
					<span class="font-medium text-text">{row.god.name}</span>
					<span class="font-data text-text-muted">{(row.weight * 100).toFixed(0)}%</span>
				</div>
				<div class="h-1.5 w-full overflow-hidden rounded-full bg-surface-raised">
					<div
						class="h-full rounded-full"
						style={`width: ${(row.weight / maxWeight) * 100}%; background: ${colorFor(row.god.architecture)};`}
					></div>
				</div>
			</div>
		{/each}
		<p class="pt-1 text-[11px] text-text-faint">
			Fusion weights are inversely proportional to recent validation error (§6.1).
		</p>
	</CardContent>
</Card>
