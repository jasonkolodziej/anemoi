<script lang="ts">
  import { onMount } from "svelte";
  import { listStorms, getSchedule, health } from "$lib/api/endpoints";
  import { errorDetail, notifyError } from "$lib/notify";
  import { toast } from "svelte-sonner";
  import type { StormSummary, CyclePlanOut } from "$lib/api/types";
  import StormCard from "$lib/components/anemoi/StormCard.svelte";
  import CycleTimeline from "$lib/components/anemoi/CycleTimeline.svelte";
  import { cycleLabel } from "$lib/utils";
  import { pollWhileVisible } from "$lib/poll";
  import { setWaiterLoading } from "$lib/stores/waiter";
  import { recall, remember } from "$lib/lastKnown";
  import { Button } from "$lib/components/ui/button";
  import { page } from "$app/state";
  import { goto } from "$app/navigation";

  const OUTAGE = "Could not reach Anemoi-API";

  let storms = $state<StormSummary[] | null>(null);
  let plans = $state<CyclePlanOut[] | null>(null);
  let error = $state<string | null>(null);
  // Defaults to the safe assumption (demo) until /v1/health actually
  // answers -- never claims "real" before confirming it.
  let stateMode = $state<"demo" | "real">("demo");
  // True while the page shows what this browser remembered from its last
  // visit and the fresh answer hasn't landed yet.
  let refreshing = $state(false);

  // Basin filter (docs/multi_basin.md phase 4): one chip per basin with an
  // active storm, kept in the URL (?basin=EP) so a filtered list can be
  // shared or reloaded. Shown only when there's more than one basin.
  const BASIN_NAMES: Record<string, string> = {
    AL: "Atlantic",
    EP: "Eastern Pacific",
    CP: "Central Pacific",
    WP: "Western Pacific",
    IO: "North Indian",
    SH: "Southern Hemisphere",
  };
  const basinFilter = $derived(page.url.searchParams.get("basin")?.toUpperCase() ?? null);
  const basinCounts = $derived.by(() => {
    const counts = new Map<string, number>();
    for (const s of storms ?? []) counts.set(s.basin, (counts.get(s.basin) ?? 0) + 1);
    return [...counts.entries()].sort(([a], [b]) => a.localeCompare(b));
  });
  const shown = $derived(
    basinFilter ? (storms ?? []).filter((s) => s.basin === basinFilter) : (storms ?? []),
  );
  function setBasin(basin: string | null) {
    const url = new URL(page.url);
    if (basin) url.searchParams.set("basin", basin);
    else url.searchParams.delete("basin");
    goto(url, { replaceState: true, keepFocus: true, noScroll: true });
  }

  interface Remembered {
    date: string;
    storms: StormSummary[];
    plans: CyclePlanOut[] | null;
    stateMode: "demo" | "real";
  }

  // Real storm/intensity data and "today" itself both go stale on a tab
  // left open -- neither was ever re-fetched before, only loaded once at
  // mount. `getSchedule`'s own plan_day is a pure function of the date
  // (no wall-clock dependency once a date is picked, confirmed against
  // its real implementation), so re-deriving `today` fresh on every poll
  // is what actually fixes day rollover -- not a timer that just re-asks
  // for the same stale date forever.
  // See the storm page's own `load` -- a background poll must refresh
  // silently rather than raise the full-page waiter every minute (#185).
  async function load({ background = false }: { background?: boolean } = {}) {
    if (!background) setWaiterLoading(true);
    try {
      const today = cycleLabel(new Date()).slice(0, 8); // YYYYMMDD
      const isoDate = `${today.slice(0, 4)}-${today.slice(4, 6)}-${today.slice(6, 8)}`;
      // Settled one by one: the storm list is the page, and a cold start or
      // a 5xx on the schedule or health used to replace a perfectly good
      // (KV-served) storm list with "Could not reach Anemoi-API" (#212).
      const [s, sched, h] = await Promise.allSettled([
        listStorms(),
        getSchedule(isoDate),
        health(),
      ]);
      if (s.status === "rejected") throw s.reason;
      storms = s.value;
      if (sched.status === "fulfilled") plans = sched.value.plans;
      if (h.status === "fulfilled") stateMode = h.value.state_mode;
      error = null; // a later successful poll clears an earlier outage
      toast.dismiss(OUTAGE);
      remember("home", { date: today, storms: s.value, plans, stateMode });
    } catch (e) {
      error = errorDetail(e);
      // One toast however many polls fail (its id is the title); the last
      // storm list loaded stays on the page underneath it.
      notifyError(OUTAGE, e, () => load());
    } finally {
      if (!background) setWaiterLoading(false);
    }
  }

  onMount(() => {
    // Draw the last visit's storms at once and refresh behind them, rather
    // than a blank page under the waiter while the API answers. The
    // schedule is only reused for the same UTC day.
    const last = recall<Remembered>("home");
    if (last) {
      storms = last.storms;
      stateMode = last.stateMode;
      if (last.date === cycleLabel(new Date()).slice(0, 8)) plans = last.plans;
      refreshing = true;
      load({ background: true }).finally(() => (refreshing = false));
    } else {
      load();
    }
    return pollWhileVisible(() => load({ background: true }), 60_000);
  });
</script>

<div class="mx-auto max-w-6xl px-6 py-8">
  <header class="mb-8">
    <h1 class="font-display text-2xl font-semibold text-text">
      Active storms
      {#if refreshing}
        <span class="ml-2 align-middle text-xs font-normal text-text-faint" data-testid="refreshing">Updating…</span>
      {/if}
    </h1>
    {#if stateMode === "real"}
      <p class="mt-1 text-sm text-text-muted">
        Real HURDAT2 archive + live NHC feed — anemoi.api.real_state.
      </p>
    {:else}
      <p class="mt-1 text-sm text-text-muted">
        Synthetic demo season — anemoi.data.synthetic.
      </p>
    {/if}
  </header>

  {#if error && storms === null}
    <p class="text-sm text-text-faint">The storm list isn't available right now.</p>
  {:else if storms === null}
    <p class="text-sm text-text-faint">Loading storms…</p>
  {:else if storms.length === 0}
    <p class="text-sm text-text-faint">
      {stateMode === "real"
        ? "No storms in the real HURDAT2 archive window."
        : "No storms in the current demo season."}
    </p>
  {:else}
    {#if basinCounts.length > 1}
      <div class="mb-4 flex flex-wrap gap-2" role="group" aria-label="Filter storms by basin">
        <Button
          size="sm"
          variant={basinFilter ? "outline" : "secondary"}
          aria-pressed={!basinFilter}
          onclick={() => setBasin(null)}>All <span class="font-data text-text-faint">{storms.length}</span></Button
        >
        {#each basinCounts as [basin, n] (basin)}
          <Button
            size="sm"
            variant={basinFilter === basin ? "secondary" : "outline"}
            aria-pressed={basinFilter === basin}
            title={BASIN_NAMES[basin] ?? basin}
            onclick={() => setBasin(basinFilter === basin ? null : basin)}
            >{basin} <span class="font-data text-text-faint">{n}</span></Button
          >
        {/each}
      </div>
    {/if}
    {#if shown.length === 0}
      <p class="text-sm text-text-faint">
        No active storms in the {BASIN_NAMES[basinFilter ?? ""] ?? basinFilter} basin.
        <button class="text-action hover:text-action-strong" onclick={() => setBasin(null)}>Show all</button>
      </p>
    {/if}
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {#each shown as storm (storm.storm_id)}
        <StormCard {storm} />
      {/each}
    </div>
  {/if}

  <section class="mt-10">
    <h2 class="font-display text-lg font-semibold text-text">
      Today's cycle schedule
    </h2>
    <p class="mt-1 text-sm text-text-muted">
      t+0:00 through the t+3:00 advisory, four synoptic cycles.
    </p>
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
