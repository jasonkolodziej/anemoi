<script lang="ts">
	import { onMount } from 'svelte';
	import { listStorms, getSchedule, health } from '$lib/api/endpoints';
	import { ApiError } from '$lib/api/client';
	import type { StormSummary, CyclePlanOut } from '$lib/api/types';
	import StormCard from '$lib/components/anemoi/StormCard.svelte';
	import CycleTimeline from '$lib/components/anemoi/CycleTimeline.svelte';
	import { cycleLabel } from '$lib/utils';

	let storms = $state<StormSummary[] | null>(null);
	let plans = $state<CyclePlanOut[] | null>(null);
	let error = $state<string | null>(null);
	// Defaults to the safe assumption (demo) until /v1/health actually
	// answers -- never claims "real" before confirming it.
	let stateMode = $state<'demo' | 'real'>('demo');

	onMount(async () => {
		try {
			const today = cycleLabel(new Date()).slice(0, 8); // YYYYMMDD
			const isoDate = `${today.slice(0, 4)}-${today.slice(4, 6)}-${today.slice(6, 8)}`;
			const [s, sched, h] = await Promise.all([listStorms(), getSchedule(isoDate), health()]);
			storms = s;
			plans = sched.plans;
			stateMode = h.state_mode;
		} catch (e) {
			error = e instanceof ApiError ? `${e.status}: ${e.message}` : String(e);
		}
	});
</script>

<div class="mx-auto max-w-6xl px-6 py-8">
	<header class="mb-8">
		<h1 class="font-display text-2xl font-semibold text-text">Active storms</h1>
		{#if stateMode === 'real'}
			<p class="mt-1 text-sm text-text-muted">Real HURDAT2 storms — anemoi.api.real_state.</p>
		{:else}
			<p class="mt-1 text-sm text-text-muted">Synthetic demo season — anemoi.data.synthetic.</p>
		{/if}
	</header>

	{#if error}
		<div class="rounded-md border border-eurus/30 bg-eurus/5 px-4 py-3 text-sm text-eurus">
			Could not reach Anemoi-API: {error}. Is <code class="font-data">python -m anemoi.api</code> running?
		</div>
	{:else if storms === null}
		<p class="text-sm text-text-faint">Loading storms…</p>
	{:else if storms.length === 0}
		<p class="text-sm text-text-faint">
			{stateMode === 'real' ? 'No storms in the real HURDAT2 archive window.' : 'No storms in the current demo season.'}
		</p>
	{:else}
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each storms as storm (storm.storm_id)}
				<StormCard {storm} />
			{/each}
		</div>
	{/if}

	<section class="mt-10">
		<h2 class="font-display text-lg font-semibold text-text">Today's cycle schedule</h2>
		<p class="mt-1 text-sm text-text-muted">t+0:00 through the t+3:00 advisory, four synoptic cycles.</p>
		<div class="mt-4 space-y-5">
			{#if plans === null && !error}
				<p class="text-sm text-text-faint">Loading schedule…</p>
			{:else if plans}
				{#each plans as plan (plan.label)}
					<CycleTimeline {plan} />
				{/each}
			{/if}
		</div>
	</section>
</div>
