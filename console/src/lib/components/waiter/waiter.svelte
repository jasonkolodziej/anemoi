<script lang="ts">
  // import { mode } from "mode-watcher";
  // import { Plane, SpinLine } from "svelte-loading-spinners";
  import { navigating } from "$app/state";
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

  let isBusy = $derived(Boolean(loading) || $waiterLoading || navigating.complete !== null);
</script>

{#if isBusy}
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
{:else}
  {@render children?.()}
{/if}

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
