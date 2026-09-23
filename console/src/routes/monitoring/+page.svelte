<script lang="ts">
	import { onMount } from 'svelte';
	import { getDriftAll, getSkew } from '$lib/api/endpoints';
	import { ApiError } from '$lib/api/client';
	import type { DriftReportOut, SkewReportOut } from '$lib/api/types';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { colorFor } from '$lib/branding';
	import { BarChart } from 'layerchart';
	import * as Chart from '$lib/components/ui/chart';
	import type { ChartConfig } from '$lib/components/ui/chart';

	let drift = $state<DriftReportOut[] | null>(null);
	let skew = $state<SkewReportOut | null>(null);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			[drift, skew] = await Promise.all([getDriftAll(), getSkew()]);
		} catch (e) {
			error = e instanceof ApiError ? `${e.status}: ${e.message}` : String(e);
		}
	});

	// Real per-feature drift is already computed server-side
	// (`FeatureDriftOut.standardized_shift`) -- it was only ever rendered
	// as a scrolling list of numbers, and only for the alerting subset.
	// This charts every feature the model tracks, not just the drifted
	// ones, so "how close is this to alerting" is visible before it
	// alerts. There is no historical snapshot to chart a trend *over
	// time* against (`DriftReportOut` is a live snapshot, not a series --
	// see `cycle_store.save_drift_live`), so this deliberately stays a
	// per-feature magnitude chart rather than fabricating a time axis
	// with only one real point on it.
	const shiftConfig: ChartConfig = {
		shift: { label: 'standardized shift (σ)', color: 'var(--color-fusion)' }
	};
</script>

<div class="mx-auto max-w-5xl px-6 py-8">
	<header class="mb-6">
		<h1 class="font-display text-2xl font-semibold text-text">Monitoring</h1>
		<p class="mt-1 text-sm text-text-muted">Train/serve drift and the ERA5T-vs-operational skew audit (§4.6.3).</p>
	</header>

	{#if error}
		<div class="rounded-md border border-eurus/30 bg-eurus/5 px-4 py-3 text-sm text-eurus">{error}</div>
	{:else}
		{#if skew}
			<Card class="mb-6">
				<CardHeader>
					<CardTitle>Skew audit — {skew.lead_hours}h lead</CardTitle>
					<Badge variant={skew.alert ? 'default' : 'outline'}>{skew.alert ? 'alert' : 'nominal'}</Badge>
				</CardHeader>
				<CardContent class="grid grid-cols-1 gap-4 text-xs sm:grid-cols-3">
					<div><p class="text-text-faint">mean track delta</p><p class="font-data mt-1 text-text">{skew.mean_track_delta_nm.toFixed(1)} nm</p></div>
					<div><p class="text-text-faint">mean |intensity delta|</p><p class="font-data mt-1 text-text">{skew.mean_abs_intensity_delta_kt.toFixed(1)} kt</p></div>
					<div><p class="text-text-faint">samples</p><p class="font-data mt-1 text-text">{skew.n}</p></div>
					{#each skew.reasons as reason (reason)}
						<p class="text-text-muted sm:col-span-3">{reason}</p>
					{/each}
				</CardContent>
			</Card>
		{/if}

		{#if drift === null}
			<p class="text-sm text-text-faint">Loading drift reports…</p>
		{:else}
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				{#each drift as report (report.model)}
					<Card>
						<CardHeader>
							<CardTitle>
								<span class="flex items-center gap-2">
									<span class="h-2 w-2 rounded-full" style={`background: ${colorFor(report.model)}`}></span>
									{report.model}
								</span>
							</CardTitle>
							<Badge variant={report.alert ? 'default' : 'outline'}>{report.alert ? 'drifted' : 'stable'}</Badge>
						</CardHeader>
						<CardContent>
							<p class="text-xs text-text-muted">{report.summary}</p>
							{#if report.features.length > 0}
								<Chart.Container
									config={shiftConfig}
									class="mt-3 w-full"
									style={`height:${Math.max(140, report.features.length * 26)}px`}
								>
									<BarChart
										data={report.features}
										orientation="horizontal"
										y="name"
										padding={{ left: 84 }}
										c={(f: (typeof report.features)[number]) =>
											f.drifted ? 'drifted' : 'stable'}
										cDomain={['stable', 'drifted']}
										cRange={['var(--color-fusion)', 'var(--color-status-degraded)']}
										series={[
											{
												key: 'shift',
												value: (f: (typeof report.features)[number]) => f.standardized_shift
											}
										]}
									>
										{#snippet tooltip()}
											<Chart.Tooltip labelKey="name" />
										{/snippet}
									</BarChart>
								</Chart.Container>
							{/if}
						</CardContent>
					</Card>
				{/each}
			</div>
		{/if}
	{/if}
</div>
