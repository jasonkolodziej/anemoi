<script lang="ts">
	/**
	 * "Model Pantheon" -- fusion contribution weights per model, in the
	 * brand's own listing order (north, south, east, west, then
	 * diagonals). Richer than a plain weight-bar list, modeled on the
	 * original branding-brief concept mock's own "Model Pantheon" panel
	 * (direction badge, persona, hover-to-highlight) -- but only using
	 * real data already defined in `$lib/branding` (persona/direction/
	 * architecture mirror `anemoi.branding` exactly) or returned by the
	 * API (`contributors`). The concept mock also showed per-model
	 * latency; there's no real per-model timing anywhere in the API
	 * response today, so unlike weight/persona/direction this isn't
	 * fabricated here.
	 *
	 * `hoveredModel` is bindable (keyed by architecture slug, e.g.
	 * "lstm", matching `CycleProducts.per_model_tracks`'s own keys) so
	 * ConeMap.svelte's real per-model map lines and this panel's rows
	 * drive the same hover-to-isolate state either direction -- the
	 * concept mock's own "hover a god to isolate its track" note, now
	 * backed by real per-model geometry instead of a static claim with
	 * nothing behind it.
	 *
	 * `missingModelReasons` (real, not derived -- see `CycleProducts`'s
	 * own doc comment) answers "why isn't this god weighing in" for a
	 * *partial* cycle: previously the only way to see this was a full
	 * cycle failure (every model skipped); the common case of a few
	 * models contributing and a few not had its own real reasons
	 * discarded the moment at least one model succeeded.
	 */
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { GODS, GOD_ORDER, colorFor } from '$lib/branding';

	interface Props {
		contributors: Record<string, number>;
		missingModelReasons?: Record<string, string>;
		hoveredModel?: string | null;
	}
	let {
		contributors,
		missingModelReasons = {},
		hoveredModel = $bindable(null),
	}: Props = $props();

	const rows = $derived(
		GOD_ORDER.map((slug) => {
			const g = GODS.find((x) => x.slug === slug)!;
			return { god: g, weight: contributors[g.architecture] ?? 0 };
		}).filter((r) => r.weight > 0)
	);
	const maxWeight = $derived(Math.max(...rows.map((r) => r.weight), 0.001));

	const missingRows = $derived(
		GOD_ORDER.map((slug) => GODS.find((x) => x.slug === slug)!)
			.filter((g) => g.architecture in missingModelReasons)
			.map((g) => ({ god: g, reason: missingModelReasons[g.architecture] }))
	);
</script>

<Card>
	<CardHeader>
		<CardTitle>Model Pantheon</CardTitle>
	</CardHeader>
	<CardContent class="space-y-1">
		{#if rows.length === 0}
			<p class="text-xs text-text-faint">No contributor weights on this cycle.</p>
		{/if}
		{#each rows as row (row.god.slug)}
			<div
				role="group"
				onmouseenter={() => (hoveredModel = row.god.architecture)}
				onmouseleave={() => (hoveredModel = null)}
				class="rounded-md border px-2.5 py-2 transition-colors"
				style={`border-color: ${hoveredModel === row.god.architecture ? colorFor(row.god.architecture) : 'transparent'}; background: ${hoveredModel === row.god.architecture ? 'var(--color-surface-raised)' : 'transparent'};`}
			>
				<div class="flex items-baseline justify-between gap-2">
					<span class="flex items-center gap-1.5">
						<span
							class="h-2 w-2 shrink-0 rounded-full"
							style={`background: ${colorFor(row.god.architecture)}`}
						></span>
						<span class="text-xs font-medium text-text">{row.god.name}</span>
						<span class="font-data text-[10px] text-text-faint">{row.god.direction}</span>
					</span>
					<span class="font-data text-xs text-text-muted">{(row.weight * 100).toFixed(0)}%</span>
				</div>
				<div class="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface-raised">
					<div
						class="h-full rounded-full transition-[width]"
						style={`width: ${(row.weight / maxWeight) * 100}%; background: ${colorFor(row.god.architecture)};`}
					></div>
				</div>
				{#if hoveredModel === row.god.architecture}
					<p class="mt-1.5 text-[11px] text-text-faint">{row.god.persona}</p>
				{/if}
			</div>
		{/each}

		{#if missingRows.length > 0}
			<div class="mt-3 space-y-1 border-t border-border pt-3">
				<p class="font-display text-[11px] font-semibold tracking-wide text-text-faint uppercase">
					Not weighing in
				</p>
				{#each missingRows as row (row.god.slug)}
					<div class="flex items-baseline justify-between gap-2 py-0.5 opacity-60">
						<span class="flex items-center gap-1.5">
							<span class="h-2 w-2 shrink-0 rounded-full border border-border-strong"></span>
							<span class="text-xs font-medium text-text-muted">{row.god.name}</span>
							<span class="font-data text-[10px] text-text-faint">{row.god.direction}</span>
						</span>
						<span class="text-[11px] text-text-faint">{row.reason}</span>
					</div>
				{/each}
			</div>
		{/if}

		<p class="pt-1 text-[11px] text-text-faint">
			Fusion weights are inversely proportional to recent validation error (§6.1). Hover a
			row to isolate its track on the map.
		</p>
	</CardContent>
</Card>
