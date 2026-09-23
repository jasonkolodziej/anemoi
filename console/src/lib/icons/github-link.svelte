<script lang="ts">
  import { onMount } from "svelte";
  // import { siteConfig } from "$lib/registry/blocks/navigation/components/site.context.svelte";
  import Button from "$lib/components/ui/button/button.svelte";
  import GithubIcon from "./github.svelte";
  import { goto } from "$app/navigation";

  async function getGithubStarCount() {
    try {
      const res = await fetch("https://ungh.cc/repos/huntabyte/shadcn-svelte");
      const data = (await res.json()) as { repo?: { stars?: number } };
      return data.repo?.stars ?? 0;
    } catch (error) {
      console.error(error);
      return 0;
    }
  }

  // onMount(async () => {
  // 	stars = await getGithubStarCount();
  // });

  let { href, stars = $bindable(0) }: { href: string; stars?: number } =
    $props();
</script>

<Button
  size="sm"
  variant="ghost"
  class="h-8 shadow-none"
  onclick={() => goto(href)}
>
  <GithubIcon class="inline-block text-muted-foreground" />
  <span class="text-muted-foreground inline-flex text-xs tabular-nums">
    {stars >= 1000 ? `${(stars / 1000).toFixed(1)}k` : stars.toLocaleString()}
  </span>
</Button>
