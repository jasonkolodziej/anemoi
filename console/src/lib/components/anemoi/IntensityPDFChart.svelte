<script lang="ts">
  /** Intensity fan chart: 10/25/50/75/90th percentile wind speed by lead
   * time (§6.1 product suite). Drawn once on mount -- a single orchestrated
   * reveal, not per-element hover choreography (frontend-design guidance). */
  import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
  } from "$lib/components/ui/card";
  import type { IntensityPercentiles } from "$lib/api/types";
  import { saffirSimpson } from "$lib/utils";

  interface Props {
    pdf: IntensityPercentiles[];
    rapidIntensification?: boolean | null;
    riProbability?: number | null;
    skironCrps?: number | null;
  }
  let {
    pdf,
    rapidIntensification = null,
    riProbability = null,
    skironCrps = null,
  }: Props = $props();

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

  function bandPath(
    lo: keyof IntensityPercentiles,
    hi: keyof IntensityPercentiles,
  ): string {
    const top = sorted.map(
      (d, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(d[hi] as number)}`,
    );
    const bottom = [...sorted]
      .reverse()
      .map((d, i) => `L ${x(sorted.length - 1 - i)} ${y(d[lo] as number)}`);
    return [...top, ...bottom, "Z"].join(" ");
  }
  function linePath(key: keyof IntensityPercentiles): string {
    return sorted
      .map((d, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(d[key] as number)}`)
      .join(" ");
  }

  const gridLines = $derived.by(() => {
    const step = maxWind > 120 ? 40 : 20;
    const lines: number[] = [];
    for (let v = 0; v <= maxWind; v += step) lines.push(v);
    return lines;
  });

  // Real peak intensity -- the fused (p50) track's own maximum, not a
  // separate estimate. `reduce` rather than `Math.max(...)` so the lead
  // hour it occurs at comes along with the value.
  const peak = $derived(
    sorted.length === 0
      ? null
      : sorted.reduce((best, d) => (d.p50 > best.p50 ? d : best), sorted[0]),
  );
  const peakColor = $derived(
    peak ? saffirSimpson(peak.p50).color : "var(--color-fusion)",
  );

  const INTENSITY = [
    { h: 0, det: 85, p10: 85, p90: 85 },
    { h: 12, det: 92, p10: 87, p90: 98 },
    { h: 24, det: 100, p10: 90, p90: 111 },
    { h: 36, det: 108, p10: 94, p90: 122 },
    { h: 48, det: 115, p10: 97, p90: 131 },
    { h: 60, det: 118, p10: 98, p90: 134 },
    { h: 72, det: 118, p10: 96, p90: 133 },
    { h: 84, det: 112, p10: 88, p90: 126 },
    { h: 96, det: 88, p10: 62, p90: 108 },
    { h: 108, det: 62, p10: 40, p90: 84 },
    { h: 120, det: 48, p10: 30, p90: 66 },
  ] as const;

  const intensityPad = { top: 12, right: 14, bottom: 20, left: 40 };
  const intensityMin = Math.min(
    ...INTENSITY.flatMap((d) => [d.det, d.p10, d.p90]),
  );
  const intensityMax = Math.max(
    ...INTENSITY.flatMap((d) => [d.det, d.p10, d.p90]),
  );

  function intensityX(hours: number): number {
    return (
      intensityPad.left +
      (hours / 120) * (W - intensityPad.left - intensityPad.right)
    );
  }

  function intensityY(value: number): number {
    const range = intensityMax - intensityMin || 1;
    return (
      intensityPad.top +
      (1 - (value - intensityMin) / range) *
        (H - intensityPad.top - intensityPad.bottom)
    );
  }

  const intensityBand =
    "M" +
    INTENSITY.map((d) => `${intensityX(d.h)},${intensityY(d.p90)}`).join(" L") +
    " L" +
    [...INTENSITY]
      .reverse()
      .map((d) => `${intensityX(d.h)},${intensityY(d.p10)}`)
      .join(" L") +
    " Z";

  const indicatorCats = [64, 96, 137] as const;
  const indicatorHours = [0, 24, 48, 72, 96, 120] as const;
</script>

<Card>
  <CardHeader>
    <CardTitle>Intensity (10th-90th percentile)</CardTitle>
  </CardHeader>
  <CardContent>
    {#if sorted.length === 0}
      <p class="text-xs text-text-faint">
        No ensemble products for this cycle.
      </p>
    {:else}
      <svg
        viewBox={`0 0 ${W} ${H + 36}`}
        class="w-full pt-2"
        role="img"
        aria-label="Intensity forecast fan chart"
      >
        {#each gridLines as gy (gy)}
          <line
            x1={PAD.left}
            x2={W - PAD.right}
            y1={y(gy)}
            y2={y(gy)}
            stroke="var(--color-border)"
            stroke-width="1"
          />
          <text
            x="4"
            y={y(gy) + 3}
            class="font-data"
            font-size="9"
            fill="var(--color-text-faint)">{gy}</text
          >
        {/each}
        <path d={bandPath("p10", "p90")} fill={peakColor} opacity="0.09" />
        <path d={bandPath("p25", "p75")} fill={peakColor} opacity="0.18" />
        <path
          d={linePath("p50")}
          fill="none"
          stroke="var(--color-text-faint)"
          opacity="0.18"
          stroke-width="3"
        />
        {#each sorted.slice(1) as d, i}
          <line
            x1={x(i)}
            x2={x(i + 1)}
            y1={y(sorted[i].p50)}
            y2={y(d.p50)}
            stroke={saffirSimpson((sorted[i].p50 + d.p50) / 2).color}
            stroke-width="3"
            stroke-linecap="round"
          />
        {/each}
        <path
          d={linePath("p50")}
          fill="none"
          stroke={peakColor}
          stroke-width="1.25"
        />
        {#each sorted as d, i (d.lead_hours)}
          <circle
            cx={x(i)}
            cy={y(d.p50)}
            r="2.5"
            fill={saffirSimpson(d.p50).color}
          />
          <text
            x={x(i)}
            y={H - 6}
            text-anchor="middle"
            class="font-data"
            font-size="9"
            fill="var(--color-text-faint)">{d.lead_hours}h</text
          >
        {/each}
        {#each indicatorCats as kt}
          <g>
            <line
              x1={intensityPad.left}
              x2={W - intensityPad.right}
              y1={intensityY(kt) + 4}
              y2={intensityY(kt) + 4}
              stroke="var(--color-border)"
              stroke-dasharray="2 6"
            />
            <text
              x={W - intensityPad.right - 2}
              y={intensityY(kt)}
              text-anchor="end"
              class="font-data"
              font-size="9"
              fill={saffirSimpson(kt).color}
            >
              {kt === 64 ? "CAT 1" : kt === 96 ? "CAT 3" : "CAT 5"} · {kt}kt
            </text>
          </g>
        {/each}

        <!-- {#each indicatorHours as h}
          <text
            x={intensityX(h)}
            y={H + 5}
            text-anchor="middle"
            class="font-data"
            font-size="9.5"
            fill="var(--color-text-faint)"
          >
            {h === 0 ? "now" : `+${h}h`}
          </text>
        {/each} -->

        <path
          d={intensityBand}
          fill={peakColor}
          fill-opacity="0.12"
          stroke={peakColor}
          stroke-opacity="0.28"
          stroke-width="1"
        />
        <polyline
          points={INTENSITY.map(
            (d) => `${intensityX(d.h)},${intensityY(d.det)}`,
          ).join(" ")}
          fill="none"
          stroke="var(--color-eye)"
          stroke-width="3"
          stroke-linecap="round"
        />
        {#each INTENSITY.filter((d) => d.h % 24 === 0) as d (d.h)}
          <circle
            cx={intensityX(d.h)}
            cy={intensityY(d.det)}
            r="4"
            fill={saffirSimpson(d.det).color}
            stroke="var(--color-surface)"
            stroke-width="2"
          />
        {/each}
        <text
          x={intensityPad.left}
          y={H + 18}
          class="font-data"
          font-size="10"
          fill="var(--color-text-faint)"
        >
          max wind (kt) · line: Anemoi-Core · band: Skiron p10-p90
        </text>
      </svg>
      <p class="mt-1 text-[11px] text-text-faint">
        Wind speed (kt) vs. forecast lead time.
      </p>
      {#if peak}
        <div class="mt-3 border-t border-border pt-3">
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div
              class="rounded-md border-none border-border/60 bg-surface/50 px-3 py-2"
            >
              <p class="text-sm text-text-faint text-capitalize">
                Peak Intensity
              </p>
              <div class="mt-1 flex items-baseline gap-2">
                <span
                  class="font-data text-lg font-semibold"
                  style={`color: ${peakColor}`}
                >
                  {peak.p50.toFixed(0)}kt
                </span>
                <span
                  class="font-data rounded-sm px-1.5 py-0.5 text-[10px] font-medium text-bg"
                  style={`background: ${saffirSimpson(peak.p50).color}`}
                >
                  {saffirSimpson(peak.p50).label}
                </span>
              </div>
              <p class="mt-1 text-[11px] text-text-faint">
                at +{peak.lead_hours}h
              </p>
            </div>

            <div
              class="rounded-md border-none border-border/60 bg-surface/50 px-3 py-2"
            >
              <p class="text-sm text-text-faint">RI flag</p>
              {#if rapidIntensification !== null}
                <div class="mt-1 flex items-center gap-2">
                  <span
                    class="font-data text-lg font-semibold {rapidIntensification
                      ? 'text-status-degraded'
                      : 'text-status-online'}"
                  >
                    {rapidIntensification ? "flagged" : "clear"}
                  </span>
                  <span
                    class="font-data rounded-sm px-1.5 py-0.5 text-[10px] font-medium text-bg"
                    style={`background: ${rapidIntensification ? "var(--color-status-degraded)" : "var(--color-status-online)"}`}
                  >
                    {riProbability !== null
                      ? `${(riProbability * 100).toFixed(0)}%`
                      : "—"}
                  </span>
                </div>
                <p class="mt-1 text-[11px] text-text-faint">
                  30kt/24h threshold
                </p>
              {:else}
                <p class="mt-1 text-[11px] text-text-faint">not available</p>
              {/if}
            </div>

            <div
              class="rounded-md border-none border-border/60 bg-surface/50 px-3 py-2"
            >
              <p class="text-sm text-text-faint">Skiron CRPS</p>
              {#if skironCrps !== null}
                <div class="mt-1 flex items-baseline gap-2">
                  <span class="font-data text-lg font-semibold text-text"
                    >{skironCrps.toFixed(2)}</span
                  >
                  <span class="text-[11px] text-text-faint"
                    >target &lt; 0.30</span
                  >
                </div>
              {:else}
                <p class="mt-1 text-[11px] text-text-faint">not available</p>
              {/if}
            </div>
          </div>
        </div>
      {/if}
    {/if}
  </CardContent>
</Card>
