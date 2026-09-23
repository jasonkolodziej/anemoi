<script lang="ts">
  /** Intensity fan chart: 10/25/50/75/90th percentile wind speed by lead
   * time (§6.1 product suite), built on shadcn-svelte's Area Chart
   * (layerchart) per the console-visuals proposal.
   *
   * v1 of this component drew the real `pdf`-derived band correctly, but
   * a second chart -- a hardcoded `INTENSITY` array of made-up
   * percentiles, drawn on the exact same axes -- was left over from an
   * early prototype and shipped alongside it, so the card showed two
   * unrelated, mismatched bands overlapping (a real bug independent of
   * any restyling: fabricated data presented next to real data). That
   * array is gone; every number this component draws now traces back to
   * a real prop.
   *
   * "Rethink what's shown" (the proposal's own todo): the old Skiron
   * p10-p90 band alone answers "how much does the ensemble spread say we
   * don't know", but says nothing about how much the *fused* contributing
   * models actually disagree with each other. `per_model_tracks` (each
   * Group 1 model's own pre-fusion prediction, keyed by architecture
   * slug) already answers that -- it's the same real data ConeMap draws
   * as per-model tracks on the map, just never passed to this chart
   * before. Plotting each model's own `wind_kt` here is the honest
   * intensity-side equivalent of that, using the same `colorFor` palette
   * and the same `hoveredModel` cross-highlight ConeMap and
   * ModelStatusPanel already share.
   */
  import { Area, AnnotationLine, AreaChart } from "layerchart";
  import * as Chart from "$lib/components/ui/chart";
  import type { ChartConfig } from "$lib/components/ui/chart";
  import * as Card from "$lib/components/ui/card/index.js";
  import type { IntensityPercentiles, TrackPointOut } from "$lib/api/types";
  import { saffirSimpson } from "$lib/utils";
  import { colorFor } from "$lib/branding";

  interface Props {
    pdf: IntensityPercentiles[];
    rapidIntensification?: boolean | null;
    riProbability?: number | null;
    skironCrps?: number | null;
    perModelTracks?: Record<string, TrackPointOut[]>;
    hoveredModel?: string | null;
  }
  let {
    pdf,
    rapidIntensification = null,
    riProbability = null,
    skironCrps = null,
    perModelTracks = {},
    hoveredModel = $bindable(null),
  }: Props = $props();

  const sorted = $derived([...pdf].sort((a, b) => a.lead_hours - b.lead_hours));
  const modelSlugs = $derived(Object.keys(perModelTracks));

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

  const chartConfig = $derived<ChartConfig>({
    band90: { label: "p10-p90 (Skiron)", color: "var(--color-fusion)" },
    band50: { label: "p25-p75 (Skiron)", color: "var(--color-fusion)" },
    median: { label: "median (Skiron)", color: peakColor },
    ...Object.fromEntries(
      modelSlugs.map((slug) => [slug, { label: slug, color: colorFor(slug) }]),
    ),
  });

  // Explicitly widened: each series legitimately carries its own `data`
  // (the Skiron bands from `sorted`, each model's own line from
  // `perModelTracks`) -- real heterogeneous per-series data the
  // underlying `Area` component supports at runtime, but `AreaChart`'s
  // single `TData` generic (inferred from the chart's own top-level
  // `data` prop) can't express across a mixed series array.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const series: any[] = $derived([
    {
      key: "band90",
      data: sorted,
      color: "var(--color-fusion)",
      props: {
        y0: (d: IntensityPercentiles) => d.p10,
        y1: (d: IntensityPercentiles) => d.p90,
        fillOpacity: 0.1,
        line: false,
      },
    },
    {
      key: "band50",
      data: sorted,
      color: "var(--color-fusion)",
      props: {
        y0: (d: IntensityPercentiles) => d.p25,
        y1: (d: IntensityPercentiles) => d.p75,
        fillOpacity: 0.2,
        line: false,
      },
    },
    {
      key: "median",
      data: sorted,
      value: (d: IntensityPercentiles) => d.p50,
      color: peakColor,
      props: { fillOpacity: 0, line: { class: "stroke-2" } },
    },
    ...modelSlugs.map((slug) => ({
      key: slug,
      data: perModelTracks[slug],
      value: (d: TrackPointOut) => d.wind_kt,
      color: colorFor(slug),
      props: {
        fillOpacity: 0,
        line: true,
        opacity: hoveredModel === null || hoveredModel === slug ? 0.85 : 0.2,
      },
    })),
  ]);

  const indicatorCats = [
    { kt: 64, label: "CAT 1" },
    { kt: 96, label: "CAT 3" },
    { kt: 137, label: "CAT 5" },
  ] as const;
</script>

<Card.Root>
  <Card.Header>
    <Card.Title>Intensity (10th-90th percentile)</Card.Title>
    <Card.Description
      >Forecast intensity distribution over lead time</Card.Description
    >
  </Card.Header>
  <Card.Content>
    {#if sorted.length === 0}
      <p class="text-xs text-text-faint">
        No ensemble products for this cycle.
      </p>
    {:else}
      <Chart.Container config={chartConfig} class="min-h-60 w-full p-2">
        <AreaChart
          data={sorted}
          x="lead_hours"
          {series}
          props={{
            xAxis: {
              format: (v: number) => `${v}h`,
              ticks: sorted.map((d) => d.lead_hours),
            },
            yAxis: { format: (v: number) => `${v}` },
          }}
        >
          {#snippet marks({ context }: { context: any })}
            {#each context.series.visibleSeries as s (s.key)}
              <Area seriesKey={s.key} {...s.props} />
            {/each}
            {#each indicatorCats as cat (cat.kt)}
              <AnnotationLine
                y={cat.kt}
                label={`${cat.label} · ${cat.kt}kt`}
                class="stroke-border/50"
                props={{
                  line: { "stroke-dasharray": "2 6" },
                  label: { class: "fill-text-faint text-[9px]" },
                }}
              />
            {/each}
          {/snippet}
          {#snippet tooltip()}
            <Chart.Tooltip
              labelKey="lead_hours"
              labelFormatter={(v: number) => `Lead time: +${v}h`}
            />
          {/snippet}
        </AreaChart>
      </Chart.Container>

      {#if peak}
        <div class="mt-3 border-t border-border pt-3">
          <div class="grid gap-3 grid-cols-3">
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
  </Card.Content>
</Card.Root>
