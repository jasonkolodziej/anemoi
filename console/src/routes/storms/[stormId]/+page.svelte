<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { getStorm, runCycle, getCycle } from '$lib/api/endpoints';
	import { ApiError } from '$lib/api/client';
	import type { StormDetail, CycleResult } from '$lib/api/types';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import ConeMap from '$lib/components/anemoi/ConeMap.svelte';
	import ModelStatusPanel from '$lib/components/anemoi/ModelStatusPanel.svelte';
	import IntensityPDFChart from '$lib/components/anemoi/IntensityPDFChart.svelte';
	import RIFlagBanner from '$lib/components/anemoi/RIFlagBanner.svelte';
	import FlagsList from '$lib/components/anemoi/FlagsList.svelte';
	import CycleDateTimePicker from '$lib/components/anemoi/CycleDateTimePicker.svelte';
	import { cycleLabel, floorSynoptic, formatLatLon, formatUtc } from '$lib/utils';

	const stormId = $derived(page.params.stormId!);

	let storm = $state<StormDetail | null>(null);
	let cycle = $state<CycleResult | null>(null);
	let error = $state<string | null>(null);
	let running = $state(false);
	let cycleInput = $state(cycleLabel(floorSynoptic(new Date())));
	let members = $state(20);
	let worstCase = $state(false);

	async function load() {
		error = null;
		try {
			storm = await getStorm(stormId);
			if (storm.cycles.length > 0) {
				const last = [...storm.cycles].sort().at(-1)!;
				cycle = await getCycle(stormId, last);
			}
		} catch (e) {
			error = e instanceof ApiError ? `${e.status}: ${e.message}` : String(e);
		}
	}

	onMount(load);

	async function handleRunCycle() {
		running = true;
		error = null;
		try {
			cycle = await runCycle(stormId, { cycle: cycleInput, members, worst_case: worstCase });
			storm = await getStorm(stormId);
		} catch (e) {
			error = e instanceof ApiError ? `${e.status}: ${e.message}` : String(e);
		} finally {
			running = false;
		}
	}
</script>

<div class="mx-auto max-w-6xl px-6 py-8">
	<a href="/" class="text-xs text-text-muted hover:text-text">&larr; Active storms</a>

	{#if error}
		<div class="mt-4 rounded-md border border-eurus/30 bg-eurus/5 px-4 py-3 text-sm text-eurus">{error}</div>
	{/if}

	{#if storm}
		<header class="mt-2 mb-6 flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="font-display text-2xl font-semibold text-text">{storm.storm_id}</h1>
				<p class="mt-1 font-data text-sm text-text-muted">
					{formatLatLon(storm.latest_fix.lat, storm.latest_fix.lon)} · {storm.latest_fix.max_wind_kt}kt · {formatUtc(storm.latest_fix.valid_time)}
				</p>
			</div>
			<div class="flex flex-wrap items-end gap-2">
				<div>
					<label for="cycle-input" class="mb-1 block text-[11px] text-text-faint">cycle label</label>
					<input
						id="cycle-input"
						bind:value={cycleInput}
						class="font-data w-40 rounded-md border border-border-strong bg-bg px-2.5 py-1.5 text-xs text-text"
					/>
				</div>
				<CycleDateTimePicker bind:value={cycleInput} />
				<div>
					<label for="members-input" class="mb-1 block text-[11px] text-text-faint">members</label>
					<input
						id="members-input"
						type="number"
						bind:value={members}
						min="1"
						max="100"
						class="font-data w-20 rounded-md border border-border-strong bg-bg px-2.5 py-1.5 text-xs text-text"
					/>
				</div>
				<Button onclick={handleRunCycle} disabled={running}>
					{running ? 'Running…' : 'Run cycle'}
				</Button>
			</div>
		</header>

		{#if cycle}
			<div class="mb-6">
				<RIFlagBanner flagged={cycle.payload.rapid_intensification} probability={cycle.payload.ri_probability} />
			</div>

			<div class="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
				<div class="space-y-6">
					<ConeMap history={storm.history} forecastTrack={cycle.products.deterministic_track} cone={cycle.payload.cone} />
					<IntensityPDFChart pdf={cycle.products.intensity_pdf} />
				</div>
				<div class="space-y-6">
					<ModelStatusPanel contributors={cycle.products.contributors} />
					<Card>
						<CardHeader><CardTitle>Cycle status</CardTitle></CardHeader>
						<CardContent class="space-y-2 text-xs">
							<div class="flex justify-between"><span class="text-text-faint">vitals</span><Badge variant="outline">{cycle.payload.vitals}</Badge></div>
							<div class="flex justify-between"><span class="text-text-faint">NWP lag</span><span class="font-data text-text">{cycle.payload.nwp_cycle_lag_hours}h</span></div>
							<div class="flex justify-between"><span class="text-text-faint">ensemble</span><span class="font-data text-text">{cycle.payload.ensemble_size} members</span></div>
							<div class="flex justify-between"><span class="text-text-faint">landfall prob.</span><span class="font-data text-text">{cycle.products.landfall_probability !== null ? `${(cycle.products.landfall_probability * 100).toFixed(0)}%` : '—'}</span></div>
							<div class="flex justify-between"><span class="text-text-faint">delivered</span><Badge variant={cycle.on_time ? 'outline' : 'default'}>{cycle.on_time ? 'on time' : 'late'}</Badge></div>
						</CardContent>
					</Card>
					<Card>
						<CardHeader><CardTitle>Flags &amp; notes</CardTitle></CardHeader>
						<CardContent>
							<FlagsList flags={cycle.payload.flags} notes={cycle.products.notes} />
						</CardContent>
					</Card>
				</div>
			</div>
		{:else}
			<Card>
				<CardContent class="py-8 text-center text-sm text-text-faint">
					No cycle has been run for this storm yet. Set a cycle label and run one above.
				</CardContent>
			</Card>
		{/if}

		{#if storm.cycles.length > 0}
			<section class="mt-8">
				<h2 class="font-display text-sm font-semibold text-text">Past cycles</h2>
				<div class="mt-2 flex flex-wrap gap-2">
					{#each [...storm.cycles].sort().reverse() as label (label)}
						<button
							class="font-data rounded-sm border border-border-strong px-2 py-1 text-xs text-text-muted hover:bg-surface-raised hover:text-text"
							onclick={async () => (cycle = await getCycle(stormId, label))}
						>
							{label}
						</button>
					{/each}
				</div>
			</section>
		{/if}
	{:else if !error}
		<p class="mt-6 text-sm text-text-faint">Loading storm…</p>
	{/if}
</div>
