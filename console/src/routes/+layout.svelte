<script lang="ts">
  import { onMount } from "svelte";
  import type { Snippet } from "svelte";
  import "../app.css";
  import HurricaneIcon from "$lib/components/anemoi/HurricaneIcon.svelte";
  import SiteHeader from "$lib/components/site/site-header.svelte";
  import { health } from "$lib/api/endpoints";
  import Waiter from "$lib/components/waiter/waiter.svelte";
  import * as Tooltip from "$lib/components/ui/tooltip/index.js";
  import { UserContext, UserState } from "$lib/user.context.svelte";
  import type { LayoutData } from "./$types";

  let { data, children }: { data: LayoutData; children: Snippet } = $props();

  // Root-level identity: hydrated from `locals.user` (hooks.server.ts) via
  // +layout.server.ts, kept live across client-side nav by the `$effect`
  // below (see login/+page.svelte and profile/+page.svelte's
  // `invalidateAll` calls -- that's what makes `data.user` change at all).
  // Seeding the constructor with `data.user` directly only captures its
  // initial value (`state_referenced_locally`) -- the effect below runs
  // immediately on mount too, so leaving the constructor unseeded loses
  // nothing and keeps `data.user` reads inside a reactive closure.
  const userState = new UserState();
  UserContext.set(userState);
  $effect(() => {
    if (data.user) userState.login(data.user);
    else userState.logout();
  });

  // The footer used to hardcode "Reference implementation" with no real
  // version at all -- found for real: a package version bump (2.1.0 ->
  // 2.2.0) had nothing in the UI to reflect it, so nobody could tell
  // which build was actually deployed just by looking. "Scope v2.1" is a
  // separate, real fact from the package version -- it names the
  // external spec this implementation targets, which this session's own
  // amendment didn't change (recorded as Decision-Log deviations *within*
  // v2.1, not a new scope version) -- so it stays hardcoded on purpose,
  // not stale. The version number is the part that must come from
  // /v1/health, not a string literal, or this goes stale again the next
  // time pyproject.toml's version changes.
  let anemoiVersion = $state<string | null>(null);
  onMount(() => {
    health()
      .then((h) => (anemoiVersion = h.anemoi_version))
      .catch(() => {});
  });

  const nav = [
    { href: "/", label: "Storms" },
    { href: "/models", label: "Models" },
    { href: "/sources", label: "Sources" },
    { href: "/registry", label: "Registry" },
    { href: "/monitoring", label: "Monitoring" },
    { href: "/retraining", label: "Retraining" },
    { href: "/docs", label: "Docs" },
  ];
</script>

<Tooltip.Provider delayDuration={150}>
<div class="flex min-h-screen flex-col md:h-screen">
  <!-- `md:h-screen` + `shrink-0` on SiteHeader (site/site-header.svelte)
       + `flex-1 overflow-y-auto` on main (no manual height math) is what
       makes main the scroll container on desktop instead of <html>.
       SiteHeader lives outside the Waiter below -- unlike the old layout,
       which wrapped aside+header+main together -- so the loading overlay
       can never block the nav or the sign-in button again (#waiter
       full-page bug). -->
  <SiteHeader {nav} {anemoiVersion} />

  <main class="min-w-0 flex-1 md:overflow-y-auto">
    <Waiter
      class="h-full"
      carriageWidth="0.5em"
      iconComponent={{
        component: HurricaneIcon,
        props: {
          spinning: "teeter-spin",
          class: "pb-4",
        },
      }}
    >
      {@render children?.()}
    </Waiter>
  </main>
</div>
</Tooltip.Provider>
