<script lang="ts">
	/** Intensity fan chart: 10/25/50/75/90th percentile wind speed by lead
	 * time (§6.1 product suite). Drawn once on mount -- a single orchestrated
	 * reveal, not per-element hover choreography (frontend-design guidance). */
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import type { IntensityPercentiles } from '$lib/api/types';

	interface Props {
		pdf: IntensityPercentiles[];
	}
	let { pdf }: Props = $props();

	const W = 560;
	const H = 200;
	const PAD = { top: 12, right: 12, bottom: 24, left: 34 };

	const sorted = $derived([...pdf].sort((a, b) => a.lead_hours - b.lead_hours));
	const maxWind = $derived(Math.max(...sorted.map((d) => d.p90), 40));
	const minWind = $derived(Math.min(...sorted.map((d) => d.p10), 0));

	function x(i: number): number {
		if (sorted.length <= 1) return PAD.left;
		return PAD.left + (i / (sorted.length - 1)) * (W - PAD.left - PAD.right);
	}
	function y(v: number): number {
		const range = maxWind - minWind || 1;
		return PAD.top + (1 - (v - minWind) / range) * (H - PAD.top - PAD.bottom);
	}

	function bandPath(lo: keyof IntensityPercentiles, hi: keyof IntensityPercentiles): string {
		const top = sorted.map((d, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(d[hi] as number)}`);
		const bottom = [...sorted]
			.reverse()
			.map((d, i) => `L ${x(sorted.length - 1 - i)} ${y(d[lo] as number)}`);
		return [...top, ...bottom, 'Z'].join(' ');
	}
	function linePath(key: keyof IntensityPercentiles): string {
		return sorted.map((d, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(d[key] as number)}`).join(' ');
	}

	const gridLines = $derived.by(() => {
		const step = maxWind > 120 ? 40 : 20;
		const lines: number[] = [];
		for (let v = 0; v <= maxWind; v += step) lines.push(v);
		return lines;
	});
</script>

<Card>
	<CardHeader>
		<CardTitle>Intensity (10th–90th percentile)</CardTitle>
	</CardHeader>
	<CardContent>
		{#if sorted.length === 0}
			<p class="text-xs text-text-faint">No ensemble products for this cycle.</p>
		{:else}
			<svg viewBox={`0 0 ${W} ${H}`} class="w-full" role="img" aria-label="Intensity forecast fan chart">
				{#each gridLines as gy (gy)}
					<line x1={PAD.left} x2={W - PAD.right} y1={y(gy)} y2={y(gy)} stroke="var(--color-border)" stroke-width="1" />
					<text x="4" y={y(gy) + 3} class="font-data" font-size="9" fill="var(--color-text-faint)">{gy}</text>
				{/each}
				<path d={bandPath('p10', 'p90')} fill="var(--color-boreas)" opacity="0.12" />
				<path d={bandPath('p25', 'p75')} fill="var(--color-boreas)" opacity="0.25" />
				<path d={linePath('p50')} fill="none" stroke="var(--color-boreas)" stroke-width="2" />
				{#each sorted as d, i (d.lead_hours)}
					<circle cx={x(i)} cy={y(d.p50)} r="2.5" fill="var(--color-boreas)" />
					<text
						x={x(i)}
						y={H - 6}
						text-anchor="middle"
						class="font-data"
						font-size="9"
						fill="var(--color-text-faint)">{d.lead_hours}h</text
					>
				{/each}
			</svg>
			<p class="mt-1 text-[11px] text-text-faint">Wind speed (kt) vs. forecast lead time.</p>
		{/if}
	</CardContent>
</Card>
