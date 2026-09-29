<script lang="ts">
  // import { mode } from "mode-watcher";
  // import { Plane, SpinLine } from "svelte-loading-spinners";
  import { afterNavigate, beforeNavigate } from "$app/navigation";
  import { cn, type PrimitiveDivAttributes } from "$lib/utils";
  import { waiterLoading } from "$lib/stores/waiter";
  import type { Component } from "svelte";

  type IconConfig = {
    component: Component<Record<string, unknown>>;
    props?: Record<string, unknown>;
  };

  type WaiterProps = PrimitiveDivAttributes & {
    size?: number;
    message?: string;
    messageClass?: string;
    carriageWidth?: string;
    fullPage?: boolean;
    loading?: boolean;
    iconComponent?: Component<Record<string, unknown>> | IconConfig;
  };

  let {
    class: klass,
    fullPage,
    children,
    size = 60,
    message = "Please wait...",
    messageClass,
    carriageWidth = "0.08em",
    loading = false,
    iconComponent: IconComponent,
    ...rest
  }: WaiterProps = $props();

  const messageLength = $derived(Math.max(message.length, 1));

  const iconDefinition = $derived(
    typeof IconComponent === "object" &&
      IconComponent !== null &&
      "component" in IconComponent
      ? IconComponent
      : { component: IconComponent, props: undefined },
  );

  let routeLoading = $state(false);

  beforeNavigate(() => {
    routeLoading = true;
  });

  afterNavigate(() => {
    routeLoading = false;
  });

  let isBusy = $derived(Boolean(loading) || $waiterLoading || routeLoading);
</script>

<div class={cn(fullPage ? "contents" : "relative", klass)} {...rest}>
  {@render children?.()}

  {#if isBusy}
    <!-- The dim is what makes this read as a loading state rather than a
         rendering glitch: before it, "Please wait..." and the spinner
         floated over a fully-lit map with nothing behind them (#185).
         Translucent, so the page underneath stays recognisable -- you can
         see what is being loaded, you just can't mistake it for ready.
         `z-50` puts it above the sticky mobile header (`z-30`); an overlay
         that renders *under* page chrome is worse than none. Clicks are
         blocked deliberately: while this is up the page is mid-fetch and
         acting on it would race the response. -->
    <div
      class={cn(
        "bg-bg/70 backdrop-blur-[2px] motion-safe:transition-opacity",
        fullPage
          ? "fixed top-0 left-0 z-50 flex h-full w-full flex-col items-center justify-center"
          : "absolute inset-0 z-50 flex flex-col items-center justify-center",
      )}
    >
      <!-- <SpinLine
        {size}
        color={mode.current === "dark" ? "#fff" : "#27272a"}
        unit="px"
      /> -->
      {#if iconDefinition.component}
        <iconDefinition.component {size} {...iconDefinition.props} />
      {/if}
      <p
        class={cn(
          "text-muted-foreground text-sm waiter-terminal-text",
          messageClass,
        )}
        style={`--waiter-message-ch: ${messageLength}ch; --waiter-typing-steps: ${messageLength}; --waiter-caret-width: ${carriageWidth};`}
      >
        {message}
      </p>
    </div>
  {/if}
</div>

<style>
  .waiter-terminal-text {
    display: block;
    white-space: nowrap;
    overflow: hidden;
    width: 0;
    border-right: var(--waiter-caret-width, 0.08em) solid currentColor;
    animation:
      waiter-type 2.6s steps(var(--waiter-typing-steps), end) infinite,
      waiter-caret 850ms step-end infinite;
  }

  @keyframes waiter-type {
    0%,
    12% {
      width: 0;
    }

    62%,
    78% {
      width: var(--waiter-message-ch);
    }

    100% {
      width: 0;
    }
  }

  @keyframes waiter-caret {
    0%,
    49% {
      border-right-color: var(--color-eye);
    }

    50%,
    100% {
      border-right-color: transparent;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .waiter-terminal-text {
      width: auto;
      animation: waiter-caret 1200ms step-end infinite;
    }
  }
</style>
