<script lang="ts">
	/**
	 * Track + cone of uncertainty, plotted as a local equirectangular
	 * projection (cos(lat)-corrected) rather than a tile map -- at synoptic
	 * scale (a few hundred nm) the distortion is negligible, and it keeps
	 * this console self-contained with no external tile dependency.
	 *
	 * The forecast track is drawn in the Fusion neutral colour: it *is* the
	 * consensus of all six models, so it takes the "no single god" colour by
	 * the same logic the brief gives Anemoi-Fusion itself.
	 */
	import type { ConeSegmentOut, FixOut, TrackPointOut } from '$lib/api/types';

	interface Props {
		history: FixOut[];
		forecastTrack: TrackPointOut[];
		cone: ConeSegmentOut[];
	}
	let { history, forecastTrack, cone }: Props = $props();

	const W = 640;
	const H = 380;
	const PAD = 28;
	const NM_PER_DEG_LAT = 60;

	const allPoints = $derived([
		...history.map((f) => ({ lat: f.lat, lon: f.lon })),
		...forecastTrack.map((t) => ({ lat: t.lat, lon: t.lon })),
		...cone.map((c) => ({ lat: c.lat, lon: c.lon }))
	]);

	const bounds = $derived.by(() => {
		if (allPoints.length === 0) return { minLat: 0, maxLat: 1, minLon: 0, maxLon: 1 };
		const lats = allPoints.map((p) => p.lat);
		const lons = allPoints.map((p) => p.lon);
		const pad = 1.5;
		return {
			minLat: Math.min(...lats) - pad,
			maxLat: Math.max(...lats) + pad,
			minLon: Math.min(...lons) - pad,
			maxLon: Math.max(...lons) + pad
		};
	});

	const midLatCos = $derived(Math.cos(((bounds.minLat + bounds.maxLat) / 2) * (Math.PI / 180)));

	function project(lat: number, lon: number): { x: number; y: number } {
		const spanLat = bounds.maxLat - bounds.minLat || 1;
		const spanLon = (bounds.maxLon - bounds.minLon) * midLatCos || 1;
		const scale = Math.min((W - PAD * 2) / spanLon, (H - PAD * 2) / spanLat);
		const x = W / 2 + (lon - (bounds.minLon + bounds.maxLon) / 2) * midLatCos * scale;
		const y = H / 2 - (lat - (bounds.minLat + bounds.maxLat) / 2) * scale;
		return { x, y };
	}

	function nmToPx(nm: number): number {
		const spanLat = bounds.maxLat - bounds.minLat || 1;
		const scale = (H - PAD * 2) / spanLat;
		return (nm / NM_PER_DEG_LAT) * scale;
	}

	const historyPath = $derived(
		history.map((f, i) => {
			const p = project(f.lat, f.lon);
			return `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`;
		}).join(' ')
	);
	const forecastPath = $derived(
		forecastTrack.map((t, i) => {
			const p = project(t.lat, t.lon);
			return `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`;
		}).join(' ')
	);
	const forecastLength = $derived(forecastTrack.length * 40); // rough stroke length for the reveal animation
</script>

<svg viewBox={`0 0 ${W} ${H}`} class="w-full rounded-md border border-border bg-surface" role="img" aria-label="Storm track and cone of uncertainty">
	<defs>
		<pattern id="graticule" width="40" height="40" patternUnits="userSpaceOnUse">
			<path d="M 40 0 L 0 0 0 40" fill="none" stroke="var(--color-border)" stroke-width="0.5" />
		</pattern>
	</defs>
	<rect width={W} height={H} fill="url(#graticule)" />

	<!-- Cone of uncertainty: overlapping circles per lead time, dashed ring
	     when the segment fell back to climatology (build_cone's honesty guard). -->
	{#each cone as seg (seg.lead_hours)}
		{@const p = project(seg.lat, seg.lon)}
		<circle
			cx={p.x}
			cy={p.y}
			r={nmToPx(seg.radius_nm)}
			fill="var(--color-fusion)"
			opacity="0.05"
		/>
		<circle
			cx={p.x}
			cy={p.y}
			r={nmToPx(seg.radius_nm)}
			fill="none"
			stroke="var(--color-fusion)"
			stroke-width="1"
			stroke-dasharray={seg.basis === 'climatology' ? '3 3' : 'none'}
			opacity="0.35"
		/>
	{/each}

	<!-- Historical (archive) track -->
	<path d={historyPath} fill="none" stroke="var(--color-text-faint)" stroke-width="1.5" stroke-dasharray="2 3" />

	<!-- Forecast track -- fusion consensus, single reveal on mount -->
	<path
		d={forecastPath}
		fill="none"
		stroke="var(--color-fusion)"
		stroke-width="2.5"
		stroke-linecap="round"
		style={`--cone-length: ${forecastLength}px; stroke-dasharray: var(--cone-length); animation: cone-draw 900ms ease-out forwards;`}
	/>
	{#each forecastTrack as t (t.lead_hours)}
		{@const p = project(t.lat, t.lon)}
		<circle cx={p.x} cy={p.y} r="3" fill="var(--color-bg)" stroke="var(--color-fusion)" stroke-width="1.5" />
		<text x={p.x + 6} y={p.y - 6} class="font-data" font-size="9" fill="var(--color-text-faint)">{t.lead_hours}h</text>
	{/each}

	{#if history.length > 0}
		{@const p = project(history[history.length - 1].lat, history[history.length - 1].lon)}
		<circle cx={p.x} cy={p.y} r="4.5" fill="var(--color-action)" />
	{/if}
</svg>
<div class="mt-2 flex flex-wrap items-center gap-4 text-[11px] text-text-faint">
	<span class="flex items-center gap-1.5"><span class="h-2 w-2 rounded-full bg-action"></span>current fix</span>
	<span class="flex items-center gap-1.5"><span class="inline-block h-px w-4 border-t border-dashed border-text-faint"></span>archive track</span>
	<span class="flex items-center gap-1.5"><span class="h-2 w-2 rounded-full bg-fusion"></span>forecast (fusion)</span>
	<span class="flex items-center gap-1.5"><span class="h-2 w-2 rounded-full bg-fusion opacity-20"></span>cone (dashed = climatology fallback)</span>
</div>
