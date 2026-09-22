<script lang="ts">
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { formatLatLon, formatUtc } from '$lib/utils';
	import type { StormSummary } from '$lib/api/types';

	interface Props {
		storm: StormSummary;
	}
	let { storm }: Props = $props();

	const qualityLabel: Record<string, string> = {
		working: 'working fix',
		final: 'final (archive)',
		emulated: 'emulated',
		estimated: 'extrapolated'
	};
</script>

<a href={`/storms/${storm.storm_id}`} class="hover-lift block">
	<Card class="h-full hover:border-border-strong">
		<CardHeader>
			<CardTitle>{storm.storm_id}</CardTitle>
			<span class="font-data text-xs text-text-faint">{storm.season}</span>
		</CardHeader>
		<CardContent class="space-y-2">
			<div class="flex items-baseline gap-2">
				<span class="font-data text-2xl font-medium text-text">{storm.latest_fix.max_wind_kt}</span>
				<span class="text-xs text-text-muted">kt · peak {storm.peak_wind_kt}kt</span>
			</div>
			<div class="font-data text-xs text-text-muted">
				{formatLatLon(storm.latest_fix.lat, storm.latest_fix.lon)}
			</div>
			<div class="flex items-center justify-between pt-1">
				<Badge variant="outline">{qualityLabel[storm.latest_fix.quality] ?? storm.latest_fix.quality}</Badge>
				<span class="font-data text-[11px] text-text-faint">{formatUtc(storm.latest_fix.valid_time)}</span>
			</div>
			{#if !storm.trained_basin}
				<Badge
					variant="outline"
					class="border-status-degraded/40 text-status-degraded"
					title="No trained model has seen a {storm.basin}-basin storm -- Atlantic-only training data"
				>
					{storm.basin} basin -- untrained
				</Badge>
			{/if}
			{#if storm.last_cycle}
				<div class="text-xs text-text-faint">last cycle <span class="font-data text-text-muted">{storm.last_cycle}</span></div>
			{/if}
		</CardContent>
	</Card>
</a>
