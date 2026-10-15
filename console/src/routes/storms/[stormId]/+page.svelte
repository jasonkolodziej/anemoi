<script lang="ts">
  import { onMount, untrack } from "svelte";
  import { page } from "$app/state";
  import { goto } from "$app/navigation";
  import type { PageData } from "./$types";
  import { getStorm, runCycle, getCycle, getSkew } from "$lib/api/endpoints";
  import { ApiError } from "$lib/api/client";
  import type { StormDetail, CycleResult, SkewReportOut } from "$lib/api/types";
  import { listRegistry } from "$lib/api/endpoints";
  import { pollWhileVisible } from "$lib/poll";
  import { setWaiterLoading } from "$lib/stores/waiter";
  import { recall, remember } from "$lib/lastKnown";
  import { loginHref } from "$lib/auth-return";
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
    cn,
    CYCLE_RUN_DELAY_MIN,
    cycleLabel,
    cycleLabelProblem,
    defaultCycleToRun,
    floorSynoptic,
    formatLatLon,
    formatUtc,
    parseCycleLabel,
  } from "$lib/utils";

  let { data }: { data: PageData } = $props();

  const stormId = $derived(page.params.stormId!);

  // The real full ensemble `inference.scheduler` runs
  // (DEFAULT_ENSEMBLE_MEMBERS). `run_cycle` only ever uses a request as a
  // cap, so anything above this was accepted and then silently reduced
  // (#187); the API now refuses it outright.
  const MAX_MEMBERS = 50;

  let storm = $state<StormDetail | null>(null);
  let cycle = $state<CycleResult | null>(null);
  // The cycle the user is deliberately looking at -- one they picked from
  // Past cycles, or one they just ran. `null` means "follow the newest",
  // which is the right default on first open. Without this the 60s poll
  // pulled the view back to the newest label every tick, usually landing
  // on a climatology-fallback cycle the user hadn't asked to see (#186).
  let viewedLabel = $state<string | null>(null);
  let error = $state<string | null>(null);
  let running = $state(false);
  // Advanced on every load/poll, so "is the next cycle due yet" and the
  // form's default cycle move with the clock while the page sits open.
  let now = $state(new Date());
  // The cycle the user typed or picked in the run form; `null` until they
  // do, and the form follows `defaultCycleToRun` -- which moves with the
  // clock and the storm. A label fixed at mount kept offering the cycle the
  // page was opened in, hours later: usually one the storm already had, so
  // "Run cycle" could only 409.
  let cycleDraft = $state<string | null>(null);
  let members = $state(MAX_MEMBERS);
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

  const latestLabel = $derived(
    storm && storm.cycles.length > 0
      ? [...storm.cycles].sort().at(-1)!
      : null,
  );

  const cycleInput = $derived(cycleDraft ?? defaultCycleToRun(storm, now));
  const cycleProblem = $derived(cycleLabelProblem(cycleInput));
  // A label this storm already has can't be run again (409 `exists`,
  // #212): the form offers to show it instead.
  const cycleExists = $derived(
    cycleProblem === null && storm !== null && storm.cycles.includes(cycleInput),
  );

  function setCycleInput(value: string) {
    cycleDraft = value;
    // A banner left by the last attempt is about a cycle no longer asked for.
    error = null;
  }

  function describe(e: unknown): string {
    return e instanceof ApiError ? `${e.status}: ${e.message}` : String(e);
  }

  // The synoptic cycle the clock is in, when this active storm doesn't have
  // it yet -- e.g. at 07:00Z the 06Z cycle exists on the calendar but the
  // cron only runs it at 07:30Z, so the newest forecast is still 00Z. Said
  // out loud because otherwise nothing on the page explains why the latest
  // fix (06Z) is newer than the forecast shown.
  const pendingCycle = $derived.by(() => {
    if (!storm?.active) return null;
    const label = cycleLabel(floorSynoptic(now));
    if (latestLabel !== null && latestLabel >= label) return null;
    const start = parseCycleLabel(label);
    if (!start) return null;
    const due = new Date(start.getTime() + CYCLE_RUN_DELAY_MIN * 60_000);
    const lateMin = (now.getTime() - due.getTime()) / 60_000;
    // A run takes minutes; well past that, it most likely failed.
    const status = lateMin < 0 ? "scheduled" : lateMin < 45 ? "running" : "overdue";
    return { label, due, status };
  });

  // #214: what the cycle actually ran on, in words.
  const FIX_SOURCE_TEXT: Record<string, string> = {
    tcvitals: "the storm's TC-Vitals fix at the cycle time",
    final_best_track: "the final best-track fix (an archive storm — not an as-issued forecast)",
    extrapolated: "a fix extrapolated from earlier ones (vitals hadn't landed)",
    persisted: "the last earlier fix, held in place (too little history to extrapolate)",
  };
  const FUSION_TEXT: Record<string, string> = {
    learned: "all five models, combined by the learned fusion",
    inverse_error: "the models available, combined by their validation error",
    synthetic: "no trained model could run — a straight-line placeholder",
    demo: "demo models",
  };

  function formatHourMinute(d: Date): string {
    const pad = (n: number) => String(n).padStart(2, "0");
    const local = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}Z (${local} your time)`;
  }

  const viewingOlderCycle = $derived(
    viewedLabel !== null && latestLabel !== null && viewedLabel !== latestLabel,
  );

  // `background` is a real distinction, not a style preference: a poll the
  // user never asked for must not raise the full-page waiter over the page
  // they are reading, once a minute, blocking clicks while it shows (#185).
  async function load({ background = false }: { background?: boolean } = {}) {
    // A periodic poll must not clobber a cycle the user just ran, or a
    // fetch mid-flight from the *previous* poll landing after a newer
    // one started -- real staleness (this page never refreshed after
    // its initial mount before this fix) is a bigger risk than skipping
    // one tick while a run is genuinely in progress.
    if (running) return;
    // Every await below re-checks this: a response for the storm the page
    // showed before a client-side switch must not land on the new one.
    const id = stormId;
    now = new Date();
    error = null;
    if (!background) setWaiterLoading(true);
    try {
      // When the label to show is already known (a pinned one, or the
      // newest from the last poll or visit), fetch it alongside the storm
      // rather than after it; only a label the storm turns out to have
      // moved past needs a second round trip.
      const known = viewedLabel ?? latestLabel;
      const [s, early] = await Promise.all([
        getStorm(id),
        known ? getCycle(id, known).catch(() => null) : null,
      ]);
      if (id !== stormId) return;
      storm = s;
      remember(`storm:${id}`, s);
      // Refresh whichever cycle is actually being viewed. Only follow the
      // newest label while the user hasn't pinned one (#186).
      const label = viewedLabel ?? latestLabel;
      if (label) {
        const fetched = label === known && early ? early : await getCycle(id, label);
        // The user may have picked another cycle while this was in flight.
        if (id !== stormId || label !== (viewedLabel ?? latestLabel)) return;
        cycle = fetched;
        remember(`cycle:${id}`, fetched);
      }
      getSkew()
        .then((r) => (skew = r))
        .catch(() => {});
    } catch (e) {
      if (id === stormId) error = describe(e);
    } finally {
      if (!background) setWaiterLoading(false);
    }
  }

  // Only the newest click's answer is shown, so clicking two chips in
  // quick succession can't end on the first.
  let viewRequest = 0;

  async function viewCycle(label: string | null) {
    const target = label ?? latestLabel;
    if (!target) return;
    const id = stormId;
    const request = ++viewRequest;
    error = null;
    try {
      const fetched = await getCycle(id, target);
      if (id !== stormId || request !== viewRequest) return;
      // Pinned only once the cycle has loaded: pinning first left the
      // chip and "Viewing an older cycle" claiming a cycle the panel and
      // map weren't showing whenever the fetch failed.
      viewedLabel = label;
      cycle = fetched;
    } catch (e) {
      if (id === stormId && request === viewRequest) error = describe(e);
    }
  }

  // Everything on this page belongs to one storm. Moving to another is a
  // client-side navigation on the same route, which reuses this component
  // rather than mounting a new one -- so start the new storm from nothing
  // here, or its page showed the last storm's pinned cycle, form, and error.
  function openStorm(id: string) {
    storm = null;
    cycle = null;
    viewedLabel = null;
    error = null;
    running = false;
    cycleDraft = null;
    members = MAX_MEMBERS;
    worstCase = false;
    coastlineLat = "";
    coastlineLon = "";
    hoveredModel = null;
    viewRequest++;
    // Draw this storm as it was on the last visit and refresh behind it,
    // rather than an empty page under the waiter while the API answers.
    const lastStorm = recall<StormDetail>(`storm:${id}`);
    if (lastStorm?.storm_id === id) {
      storm = lastStorm;
      const lastCycle = recall<CycleResult>(`cycle:${id}`);
      if (lastCycle?.payload.cycle === latestLabel) cycle = lastCycle;
    }
    load({ background: storm !== null });
  }

  $effect(() => {
    const id = stormId;
    untrack(() => openStorm(id));
  });

  onMount(() => {
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
    // reload to show that. Deliberately does not touch cycleDraft/
    // members/coastlineLat/coastlineLon -- a poll must never overwrite
    // an in-progress form edit (the default cycle it advances is only
    // shown until the user picks one).
    return pollWhileVisible(() => load({ background: true }), 60_000);
  });

  async function handleRunCycle() {
    // #171: anemoi-api-real now rejects an unauthenticated cycle POST
    // (the proxy 401s), and anonymous visitors have no way to authenticate
    // a fetch -- send them to log in instead of a raw error surfacing
    // from a click that could never have worked.
    if (!data.user) {
      // Back to this storm afterwards, not /profile.
      await goto(loginHref(`/storms/${stormId}`));
      return;
    }
    if (cycleProblem !== null || cycleExists) return;
    const id = stormId;
    running = true;
    error = null;
    try {
      const lat = coastlineLat.trim() === "" ? null : Number(coastlineLat);
      const lon = coastlineLon.trim() === "" ? null : Number(coastlineLon);
      // `max` on a number input bounds the spinner, not what can be typed
      // or pasted -- clamp for real, so the request can't be refused by
      // the API's own bound (#187).
      members = Math.min(Math.max(Math.round(members), 1), MAX_MEMBERS);
      const result = await runCycle(id, {
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
      // A cycle the user deliberately ran is the one they want to see,
      // even when a newer label already exists (#186) -- but only once it
      // exists. Pinning before the await meant a failed run left the view
      // pinned to a label that was never created, and every 60s poll then
      // 404'd on it and rewrote `error` (Copilot review, #190).
      // A result for a storm the user has since left belongs to that storm
      // only (Copilot review, #217).
      if (id !== stormId) return;
      cycle = result;
      // The label the API actually stored, not what was typed: it accepts
      // `20261015_6Z` and stores `20261015_06Z`, and pinning the typed form
      // made every later poll 404 on a label that doesn't exist (#212).
      viewedLabel = result.payload.cycle;
      viewRequest++;
      const fresh = await getStorm(id, { fresh: true });
      if (id === stormId) storm = fresh;
    } catch (e) {
      if (id !== stormId) return;
      error = describe(e);
      // A 409 usually means the storm has moved on since this page last
      // read it (the cron, or another visitor, ran that cycle): re-read it
      // so Past cycles lists it and the form offers to show it.
      if (e instanceof ApiError && e.status === 409) {
        getStorm(id, { fresh: true })
          .then((s) => {
            if (id === stormId) storm = s;
          })
          .catch(() => {});
      }
    } finally {
      if (id === stormId) running = false;
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
      data-testid="page-error"
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
          <span class="font-sans text-xs text-text-faint">latest fix</span>
          {formatLatLon(storm.latest_fix.lat, storm.latest_fix.lon)} · {storm
            .latest_fix.max_wind_kt}kt · {formatUtc(
            storm.latest_fix.valid_time,
          )}
        </p>
        {#if cycle || pendingCycle}
        <div
          class="mt-3 max-w-xl rounded-md border border-border-strong bg-surface-raised px-4 py-3 text-sm"
          data-testid="cycle-context"
        >
          {#if cycle}
            <p class="text-text">
              Showing forecast cycle
              <span class="font-data font-medium">{cycle.payload.cycle}</span>
              {#if cycle.payload.cycle === latestLabel}
                <span class="text-text-muted">— the latest run</span>
              {:else}
                <span class="text-status-degraded"
                  >— an older run; the latest is
                  <span class="font-data">{latestLabel}</span></span
                >
                <button
                  class="ml-1 text-fusion underline underline-offset-2 hover:text-text"
                  onclick={() => viewCycle(null)}>Show latest</button
                >
              {/if}
            </p>
            {#if cycle.run?.source === "manual"}
              <p class="mt-1 text-xs text-status-degraded" data-testid="manual-run">
                A manual run{cycle.run.overrides.length > 0
                  ? ` (changed: ${cycle.run.overrides.join(", ")})`
                  : ""}, not the scheduled one — the scheduled run replaces it.
              </p>
            {/if}
            {#if cycle.provenance}
              <p class="mt-1 text-xs text-text-muted" data-testid="cycle-provenance">
                Started from {FIX_SOURCE_TEXT[cycle.provenance.fix_source]};
                {FUSION_TEXT[cycle.provenance.fusion] ?? cycle.provenance.fusion}.
              </p>
            {/if}
            <p class="mt-1 text-xs text-text-muted">
              Map times are when each forecast point is valid, counted from
              {cycle.payload.cycle.slice(-3)} — not from the latest fix ({formatUtc(
                storm.latest_fix.valid_time,
              )}).
            </p>
          {/if}
          {#if pendingCycle}
            <p class={cn("text-xs text-text-muted", cycle && "mt-1")} data-testid="pending-cycle">
              The <span class="font-data">{pendingCycle.label}</span> cycle hasn't
              run yet —
              {#if pendingCycle.status === "scheduled"}
                it's scheduled for {formatHourMinute(pendingCycle.due)}.
              {:else if pendingCycle.status === "running"}
                it started at {formatHourMinute(pendingCycle.due)} and should appear
                within a few minutes.
              {:else}
                it was due at {formatHourMinute(pendingCycle.due)} and is overdue;
                the scheduled run may have failed.
              {/if}
            </p>
          {/if}
        </div>
        {/if}
      </div>
      <!-- A form for running another cycle, not a readout of the one shown
           below: its label follows the current synoptic time (see
           `defaultCycleToRun`), which is usually newer than the newest
           cycle run so far, until the user picks one. -->
      <fieldset
        class="flex flex-wrap items-end gap-2 rounded-md border border-border px-3 pt-1 pb-3"
      >
        <legend class="px-1 text-[11px] text-text-faint">Run a new cycle</legend>
        <div>
          <label
            for="cycle-input"
            class="mb-1 block text-[11px] text-text-faint">cycle to run</label
          >
          <input
            id="cycle-input"
            bind:value={() => cycleInput, setCycleInput}
            class="font-data w-40 rounded-md border border-border-strong bg-bg px-2.5 py-1.5 text-xs text-text"
          />
        </div>
        <CycleDateTimePicker bind:value={() => cycleInput, setCycleInput} />
        <div>
          <label
            for="members-input"
            class="mb-1 block text-[11px] text-text-faint"
            >members (max {MAX_MEMBERS})</label
          >
          <!-- Capped at the real full ensemble the scheduler runs, not an
               arbitrary UI bound: `run_cycle` only ever applies this as a
               cap, so a larger number was accepted and then silently
               reduced to 20 (#187). The API refuses it now too. -->
          <input
            id="members-input"
            type="number"
            bind:value={members}
            min="1"
            max={MAX_MEMBERS}
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
        <Button
          onclick={handleRunCycle}
          disabled={running || cycleProblem !== null || cycleExists}
        >
          {running ? "Running…" : "Run cycle"}
        </Button>
        {#if !data.user}
          <p class="w-full text-[11px] text-text-muted" data-testid="sign-in-to-run">
            Running a cycle needs an account —
            <a
              href={loginHref(`/storms/${stormId}`)}
              class="text-fusion underline underline-offset-2 hover:text-text">sign in</a
            >
            and you'll come back here.
          </p>
        {/if}
        {#if cycleProblem}
          <p class="w-full text-[11px] text-status-degraded" data-testid="cycle-input-problem">
            {cycleProblem}
          </p>
        {:else if cycleExists}
          <p class="w-full text-[11px] text-text-muted" data-testid="cycle-exists">
            <span class="font-data">{cycleInput}</span> has already run{cycleInput ===
            cycle?.payload.cycle
              ? " — it's the one shown"
              : ""}.
            {#if cycleInput !== cycle?.payload.cycle}
              <button
                class="ml-1 text-fusion underline underline-offset-2 hover:text-text"
                onclick={() => viewCycle(cycleInput === latestLabel ? null : cycleInput)}
                >View it</button
              >
            {/if}
          </p>
        {/if}
      </fieldset>
    </header>


    {#if cycle}
      <div class="mb-6">
        <RIFlagBanner
          flagged={cycle.payload.rapid_intensification}
          probability={cycle.payload.ri_probability}
          lo={cycle.payload.ri_probability_lo}
          hi={cycle.payload.ri_probability_hi}
          uncertain={cycle.payload.ri_uncertain}
          ensembleSize={cycle.payload.ensemble_size}
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
        <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h2 class="font-display text-sm font-semibold text-text">
            Past cycles
          </h2>
          {#if viewingOlderCycle}
            <p class="text-[11px] text-text-muted">
              Viewing an older cycle — background refresh won't move you.
              <button
                class="text-fusion underline underline-offset-2 hover:text-text"
                onclick={() => viewCycle(null)}
              >
                Back to latest
              </button>
            </p>
          {/if}
        </div>
        <div class="mt-2 flex flex-wrap gap-2" data-testid="past-cycles">
          {#each [...storm.cycles].sort().reverse() as label (label)}
            <button
              class={cn(
                "font-data rounded-sm border px-2 py-1 text-xs",
                label === (viewedLabel ?? latestLabel)
                  ? "border-fusion bg-surface-raised text-text"
                  : "border-border-strong text-text-muted hover:bg-surface-raised hover:text-text",
              )}
              aria-current={label === (viewedLabel ?? latestLabel)
                ? "true"
                : undefined}
              onclick={() => viewCycle(label)}
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
