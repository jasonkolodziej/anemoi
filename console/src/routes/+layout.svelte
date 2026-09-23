<script lang="ts">
  import { onMount } from "svelte";
  import "../app.css";
  import { page } from "$app/state";
  import HurricaneIcon from "$lib/components/anemoi/HurricaneIcon.svelte";
  import MobileNav from "$lib/components/anemoi/MobileNav.svelte";
  import { health } from "$lib/api/endpoints";
  import { cn } from "$lib/utils";
  import Waiter from "$lib/components/waiter/waiter.svelte";
  import { GithubLink } from "$lib/icons";
  import Github from "$lib/icons/github.svelte";

  let { children } = $props();

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

  function isActive(href: string): boolean {
    if (href === "/") return page.url.pathname === "/";
    return page.url.pathname.startsWith(href);
  }
  let version = $derived(anemoiVersion);
</script>

<!-- md:h-screen (not min-h-screen) + main's own md:overflow-y-auto is what
     actually makes main the scroll container on desktop, keeping aside
     fixed in place -- min-h-screen alone lets the whole flex row just grow
     past the viewport together, so the real scroll happens on <html>
     instead and aside/main scroll away as one unit. Never surfaced before
     docs was the first page with genuinely tall content. Mobile keeps
     min-h-screen/normal document scroll -- the sticky header works fine
     with that, no container trick needed. -->
<div class="flex min-h-screen flex-col md:h-screen md:flex-row">
  <!-- Desktop: persistent rail. A fixed 224px sidebar eats over half a
	     phone viewport, so this is `md:`-and-up only -- see MobileNav for
	     the small-screen equivalent below. -->
  <Waiter
    fullPage={true}
    carriageWidth="0.5em"
    iconComponent={{
      component: HurricaneIcon,
      props: {
        spinning: "teeter-spin",
        class: "pb-4",
      },
    }}
  >
    <aside
      class="hidden w-56 shrink-0 flex-col border-r border-border bg-surface pt-[env(safe-area-inset-top)] md:flex"
    >
      <a
        href="/"
        class="flex items-center gap-2.5 border-b border-border px-4 py-4"
      >
        <HurricaneIcon size={26} />
        <div>
          <p class="font-display text-sm font-semibold leading-none text-text">
            Anemoi
          </p>
          <p class="text-[10px] leading-none text-text-faint mt-1">
            Many winds. One forecast.
          </p>
        </div>
      </a>
      <nav class="flex-1 space-y-0.5 overflow-y-auto p-2">
        {#each nav as item (item.href)}
          <a
            href={item.href}
            class={cn(
              "block rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive(item.href)
                ? "bg-surface-raised text-text"
                : "text-text-muted hover:bg-surface-raised/60 hover:text-text",
            )}
          >
            {item.label}
          </a>
        {/each}
      </nav>
      <div class="border-t border-border p-3 text-[10px] text-text-faint">
        {version ? `v${version} · ` : ""}

        <Github class="inline-block size-2.5 text-text-faint mr-1" />
        <a
          href="https://github.com/jasonkolodziej/anemoi"
          class="text-text-faint hover:text-text"
          target="_blank"
          rel="noopener noreferrer">jasonkolodziej/anemoi</a
        >
      </div>
    </aside>

    <!-- Mobile: a slim top bar + off-canvas drawer instead of the rail. -->
    <header
      class="sticky top-0 z-30 flex items-center justify-between gap-2 border-b border-border bg-surface px-4 pt-[calc(env(safe-area-inset-top)+0.75rem)] pb-3 md:hidden"
    >
      <a href="/" class="flex items-center gap-2">
        <HurricaneIcon size={22} />
        <p class="font-display text-sm font-semibold leading-none text-text">
          Anemoi
        </p>
      </a>
      <MobileNav {nav} {anemoiVersion} />
    </header>

    <main class="min-w-0 flex-1 md:overflow-y-auto">
      {@render children?.()}
    </main>
  </Waiter>
</div>
