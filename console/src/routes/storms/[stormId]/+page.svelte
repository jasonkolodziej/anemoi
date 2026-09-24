<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/state";
  import { getStorm, runCycle, getCycle, getSkew } from "$lib/api/endpoints";
  import { ApiError } from "$lib/api/client";
  import type { StormDetail, CycleResult, SkewReportOut } from "$lib/api/types";
  import { listRegistry } from "$lib/api/endpoints";
  import { pollWhileVisible } from "$lib/poll";
  import { setWaiterLoading } from "$lib/stores/waiter";
  import { Button } from "$lib/components/ui/button";
  import { Badge } from "$lib/components/ui/badge";
  import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
  } from "$lib/components/ui/card";
  import ConeMap from "$lib/components/anemoi/ConeMap.svelte";
  import ModelStatusPanel from "$lib/components/anemoi/ModelStatusPanel.svelte";
  import IntensityPDFChart from "$lib/components/anemoi/IntensityPDFChart.svelte";
  import RIFlagBanner from "$lib/components/anemoi/RIFlagBanner.svelte";
  import FlagsList from "$lib/components/anemoi/FlagsList.svelte";
  import CycleDateTimePicker from "$lib/components/anemoi/CycleDateTimePicker.svelte";
  import {
    cycleLabel,
    floorSynoptic,
    formatLatLon,
    formatUtc,
  } from "$lib/utils";

  const stormId = $derived(page.params.stormId!);

  let storm = $state<StormDetail | null>(null);
  let cycle = $state<CycleResult | null>(null);
  let error = $state<string | null>(null);
  let running = $state(false);
  let cycleInput = $state(cycleLabel(floorSynoptic(new Date())));
  let members = $state(20);
  let worstCase = $state(false);
  // Optional -- landfall_probability is null unless a coastal reference
  // point is supplied (postprocess.landfall_probability needs one to
  // measure ensemble members' closest approach against).
  let coastlineLat = $state<string>("");
  let coastlineLon = $state<string>("");
  // System-wide (not scoped to this storm) -- the real §4.6.3 ERA5T-vs-
  // operational skew audit, the same data /monitoring shows. Loaded
  // once, not re-fetched per storm/cycle switch.
  let skew = $state<SkewReportOut | null>(null);
  let skironCrps = $state<number | null>(null);
  // Shared between ConeMap (real per-model map lines) and
  // ModelStatusPanel (the Model Pantheon list) -- hovering either one
  // isolates the same model on both.
  let hoveredModel = $state<string | null>(null);

  async function load() {
    // A periodic poll must not clobber a cycle the user just ran, or a
    // fetch mid-flight from the *previous* poll landing after a newer
    // one started -- real staleness (this page never refreshed after
    // its initial mount before this fix) is a bigger risk than skipping
    // one tick while a run is genuinely in progress.
    if (running) return;
    error = null;
    setWaiterLoading(true);
    try {
      storm = await getStorm(stormId);
      if (storm.cycles.length > 0) {
        const last = [...storm.cycles].sort().at(-1)!;
        cycle = await getCycle(stormId, last);
      }
      getSkew()
        .then((r) => (skew = r))
        .catch(() => {});
    } catch (e) {
      error = e instanceof ApiError ? `${e.status}: ${e.message}` : String(e);
    } finally {
      setWaiterLoading(false);
    }
  }

  onMount(() => {
    load();
    listRegistry()
      .then((entries) => {
        const skiron = entries.find((entry) => entry.model === "skiron");
        skironCrps = skiron?.latest?.metrics.crps_48h ?? null;
      })
      .catch(() => {});
    // A live storm's own position/intensity, and whether some other
    // operator has already run the next cycle, can both change while
    // this page just sits open -- watching an active storm is exactly
    // the case this page is for, so it must not require a manual
    // reload to show that. Deliberately does not touch cycleInput/
    // members/coastlineLat/coastlineLon -- a poll must never overwrite
    // an in-progress form edit.
    return pollWhileVisible(load, 60_000);
  });

  async function handleRunCycle() {
    running = true;
    error = null;
    try {
      const lat = coastlineLat.trim() === "" ? null : Number(coastlineLat);
      const lon = coastlineLon.trim() === "" ? null : Number(coastlineLon);
      cycle = await runCycle(stormId, {
        cycle: cycleInput,
        members,
        worst_case: worstCase,
        ...(lat !== null &&
        lon !== null &&
        Number.isFinite(lat) &&
        Number.isFinite(lon)
          ? { coastline_lat: lat, coastline_lon: lon }
          : {}),
      });
      storm = await getStorm(stormId);
    } catch (e) {
      error = e instanceof ApiError ? `${e.status}: ${e.message}` : String(e);
    } finally {
      running = false;
    }
  }
</script>

<div class="mx-auto max-w-6xl px-6 py-8">
  <a href="/" class="text-xs text-text-muted hover:text-text"
    >&larr; Active storms</a
  >

  {#if error}
    <div
      class="mt-4 rounded-md border border-eurus/30 bg-eurus/5 px-4 py-3 text-sm text-eurus"
    >
      {error}
    </div>
  {/if}

  {#if storm}
    <header class="mt-2 mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <div class="flex items-center gap-2">
          <h1 class="font-display text-2xl font-semibold text-text">
            {storm.storm_id}
            {#if storm.name}
              <span class="font-normal text-text-muted">{storm.name}</span>
            {/if}
          </h1>
          {#if !storm.trained_basin}
            <span
              class="font-data rounded-full border border-status-degraded/40 px-2 py-0.5 text-[10px] tracking-wide text-status-degraded uppercase"
              title="No trained model has seen a {storm.basin}-basin storm -- every model here was trained on Atlantic storms only, so this forecast is a genuine out-of-distribution extrapolation"
            >
              {storm.basin} basin -- untrained
            </span>
          {/if}
          {#if cycle}
            {@const nContributing = Object.keys(
              cycle.products.contributors,
            ).length}
            {@const nTotal =
              nContributing +
              Object.keys(cycle.products.missing_model_reasons).length}
            {#if nTotal > 0}
              <span
                class="font-data rounded-full border px-2 py-0.5 text-[10px] tracking-wide uppercase"
                class:border-status-online={nContributing === nTotal}
                class:text-status-online={nContributing === nTotal}
                class:border-border-strong={nContributing !== nTotal}
                class:text-text-faint={nContributing !== nTotal}
              >
                {nContributing}/{nTotal} models contributing
              </span>
            {/if}
          {/if}
        </div>
        <p class="mt-1 font-data text-sm text-text-muted">
          {formatLatLon(storm.latest_fix.lat, storm.latest_fix.lon)} · {storm
            .latest_fix.max_wind_kt}kt · {formatUtc(
            storm.latest_fix.valid_time,
          )}
        </p>
      </div>
      <div class="flex flex-wrap items-end gap-2">
        <div>
          <label
            for="cycle-input"
            class="mb-1 block text-[11px] text-text-faint">cycle label</label
          >
          <input
            id="cycle-input"
            bind:value={cycleInput}
            class="font-data w-40 rounded-md border border-border-strong bg-bg px-2.5 py-1.5 text-xs text-text"
          />
        </div>
        <CycleDateTimePicker bind:value={cycleInput} />
        <div>
          <label
            for="members-input"
            class="mb-1 block text-[11px] text-text-faint">members</label
          >
          <input
            id="members-input"
            type="number"
            bind:value={members}
            min="1"
            max="100"
            class="font-data w-20 rounded-md border border-border-strong bg-bg px-2.5 py-1.5 text-xs text-text"
          />
        </div>
        <div>
          <label
            for="coastline-lat-input"
            class="mb-1 block text-[11px] text-text-faint"
          >
            coastline lat/lon <span class="normal-case text-text-faint/70"
              >(landfall, optional)</span
            >
          </label>
          <div class="flex gap-1">
            <input
              id="coastline-lat-input"
              type="text"
              inputmode="decimal"
              placeholder="lat"
              bind:value={coastlineLat}
              class="font-data w-16 rounded-md border border-border-strong bg-bg px-2 py-1.5 text-xs text-text"
            />
            <input
              id="coastline-lon-input"
              type="text"
              inputmode="decimal"
              placeholder="lon"
              bind:value={coastlineLon}
              class="font-data w-16 rounded-md border border-border-strong bg-bg px-2 py-1.5 text-xs text-text"
            />
          </div>
        </div>
        <Button onclick={handleRunCycle} disabled={running}>
          {running ? "Running…" : "Run cycle"}
        </Button>
      </div>
    </header>

    {#if cycle}
      <div class="mb-6">
        <RIFlagBanner
          flagged={cycle.payload.rapid_intensification}
          probability={cycle.payload.ri_probability}
        />
      </div>

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        <div class="space-y-6">
          <Card>
            <CardHeader class="border-none"
              ><CardTitle>Wind Rose Projection</CardTitle></CardHeader
            >
            <CardContent>
              <ConeMap
                history={storm.history}
                forecastTrack={cycle.products.deterministic_track}
                cone={cycle.payload.cone}
                perModelTracks={cycle.products.per_model_tracks}
                coastlineLat={cycle.payload.coastline_lat}
                coastlineLon={cycle.payload.coastline_lon}
                cycleLabel={cycle.payload.cycle}
                bind:hoveredModel
              />
            </CardContent>
          </Card>
          <IntensityPDFChart
            pdf={cycle.products.intensity_pdf}
            rapidIntensification={cycle.payload.rapid_intensification}
            riProbability={cycle.payload.ri_probability}
            {skironCrps}
            perModelTracks={cycle.products.per_model_tracks}
            bind:hoveredModel
          />
        </div>
        <div class="space-y-6">
          <ModelStatusPanel
            contributors={cycle.products.contributors}
            missingModelReasons={cycle.products.missing_model_reasons}
            bind:hoveredModel
          />
          <Card>
            <CardHeader><CardTitle>Cycle status</CardTitle></CardHeader>
            <CardContent class="space-y-2 pt-2 text-xs">
              <div class="flex justify-between">
                <span class="text-text-faint">vitals</span><Badge
                  variant="outline">{cycle.payload.vitals}</Badge
                >
              </div>
              <div class="flex justify-between">
                <span class="text-text-faint">NWP lag</span><span
                  class="font-data text-text"
                  >{cycle.payload.nwp_cycle_lag_hours}h</span
                >
              </div>
              <div class="flex justify-between">
                <span class="text-text-faint">ensemble</span><span
                  class="font-data text-text"
                  >{cycle.payload.ensemble_size} members</span
                >
              </div>
              <div class="flex justify-between">
                <span class="text-text-faint">delivered</span><Badge
                  variant={cycle.on_time ? "outline" : "default"}
                  >{cycle.on_time ? "on time" : "late"}</Badge
                >
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Landfall Projection</CardTitle></CardHeader>
            <CardContent class="space-y-2 pt-2 text-xs">
              {#if cycle.products.landfall_probability !== null}
                <div class="flex items-baseline justify-between">
                  <span class="text-text-faint">probability</span>
                  <span
                    class="font-data text-xl font-medium"
                    class:text-status-degraded={cycle.products
                      .landfall_probability > 0.35}
                    class:text-text={cycle.products.landfall_probability <=
                      0.35}
                  >
                    {(cycle.products.landfall_probability * 100).toFixed(0)}%
                  </span>
                </div>
                <div class="flex justify-between">
                  <span class="text-text-faint">reference point</span>
                  <span class="font-data text-text"
                    >{formatLatLon(
                      cycle.payload.coastline_lat ?? 0,
                      cycle.payload.coastline_lon ?? 0,
                    )}</span
                  >
                </div>
                <div class="flex justify-between">
                  <span class="text-text-faint">threshold</span>
                  <span class="font-data text-text">60nm, any lead</span>
                </div>
                <p class="pt-1 text-[11px] text-text-faint">
                  Fraction of Skiron ensemble members passing within 60nm of the
                  reference point at any forecast lead.
                </p>
              {:else}
                <p class="text-text-faint">
                  No coastal reference point was set for this cycle -- enter one
                  above ("coastline lat/lon") and re-run to get a real landfall
                  probability.
                </p>
              {/if}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Flags &amp; notes</CardTitle></CardHeader>
            <CardContent class="pt-2">
              <FlagsList
                flags={cycle.payload.flags}
                notes={cycle.products.notes}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    {:else}
      <Card>
        <CardContent class="py-8 text-center text-sm text-text-faint">
          No cycle has been run for this storm yet. Set a cycle label and run
          one above.
        </CardContent>
      </Card>
    {/if}

    {#if skew}
      <Card class="mt-8">
        <CardHeader>
          <CardTitle>Verification</CardTitle>
          <div class="flex items-center gap-2">
            <Badge variant={skew.alert ? "default" : "outline"}
              >{skew.alert ? "alert" : "nominal"}</Badge
            >
            <a
              href="/monitoring"
              class="text-[11px] text-text-faint hover:text-text-muted"
              >full monitoring &rarr;</a
            >
          </div>
        </CardHeader>
        <CardContent class="pt-2">
          <p class="mb-3 text-[11px] text-text-faint">
            System-wide {skew.lead_hours}h-lead ERA5T-vs-operational skew audit
            (§4.6.3) -- not specific to {storm.storm_id}, the same rolling
            window every storm's page shows.
          </p>
          <div class="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
            <div>
              <p class="text-text-faint">mean track delta</p>
              <p class="font-data mt-1 text-sm text-text">
                {skew.mean_track_delta_nm.toFixed(1)} nm
              </p>
            </div>
            <div>
              <p class="text-text-faint">mean |intensity delta|</p>
              <p class="font-data mt-1 text-sm text-text">
                {skew.mean_abs_intensity_delta_kt.toFixed(1)} kt
              </p>
            </div>
            <div>
              <p class="text-text-faint">intensity bias</p>
              <p class="font-data mt-1 text-sm text-text">
                {skew.intensity_bias_kt >= 0
                  ? "+"
                  : ""}{skew.intensity_bias_kt.toFixed(1)} kt
              </p>
            </div>
            <div>
              <p class="text-text-faint">samples</p>
              <p class="font-data mt-1 text-sm text-text">{skew.n}</p>
            </div>
          </div>
          {#each skew.reasons as reason (reason)}
            <p class="mt-3 text-[11px] text-text-muted">{reason}</p>
          {/each}
        </CardContent>
      </Card>
    {/if}

    {#if storm.cycles.length > 0}
      <section class="mt-8">
        <h2 class="font-display text-sm font-semibold text-text">
          Past cycles
        </h2>
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
