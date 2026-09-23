<script lang="ts">
  // import { mode } from "mode-watcher";
  // import { Plane, SpinLine } from "svelte-loading-spinners";
  import { navigating } from "$app/state";
  import { cn, type PrimitiveDivAttributes } from "$lib/utils";
  import type { SvelteComponent } from "svelte";

  type WaiterProps = PrimitiveDivAttributes & {
    size?: number;
    message?: string;
    fullPage?: boolean;
    iconComponent?: typeof SvelteComponent;
  };

  let {
    class: klass,
    fullPage,
    children,
    size = 60,
    message = "Please wait...",
    iconComponent: IconComponent,
    ...rest
  }: WaiterProps = $props();

  let isNavigating = $derived(navigating.complete !== null);
</script>

{#if isNavigating}
  <div
    class={cn(
      fullPage
        ? "fixed top-0 left-0 flex h-full w-full flex-1 flex-col items-center justify-center"
        : "",
      klass,
    )}
    {...rest}
  >
    <!-- <SpinLine
      {size}
      color={mode.current === "dark" ? "#fff" : "#27272a"}
      unit="px"
    /> -->
    {#if IconComponent}
      <IconComponent {size} />
    {/if}
    <p class="text-muted-foreground text-sm">{message}</p>
  </div>
{:else}
  {@render children?.()}
{/if}
