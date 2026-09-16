<script lang="ts">
	/**
	 * Degraded-mode flags -- the fixed vocabulary from docs/api.md ("The flag
	 * vocabulary") and the wiki's API page.
	 * Matches by prefix; an unrecognised flag still renders (opaque reason)
	 * rather than being dropped, so a new flag in a future anemoi release
	 * doesn't silently disappear from the console.
	 */
	interface Props {
		flags: string[];
		notes?: string[];
	}
	let { flags, notes = [] }: Props = $props();

	function describe(flag: string): string {
		if (flag === 'vitals=estimated') return 'Cycle ran on an extrapolated fix — TC-Vitals arrived late.';
		if (flag.startsWith('nwp_stale=')) return `NWP input is staler than the nominal t−6 cycle (${flag.split('=')[1]}).`;
		if (flag.startsWith('missing:')) return `Expected source unavailable: ${flag.split(':')[1]}.`;
		if (flag.startsWith('spread_fallback:')) return `Anemoi-Spread failed (${flag.split(':')[1]}) — climatological ensemble substituted.`;
		return flag;
	}
</script>

{#if flags.length === 0 && notes.length === 0}
	<p class="text-xs text-text-faint">No degraded-mode flags on this cycle.</p>
{:else}
	<ul class="space-y-1.5">
		{#each flags as flag (flag)}
			<li class="flex items-start gap-2 text-xs">
				<span class="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-action"></span>
				<span class="text-text-muted">{describe(flag)}</span>
			</li>
		{/each}
		{#each notes as note (note)}
			<li class="flex items-start gap-2 text-xs">
				<span class="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-text-faint"></span>
				<span class="text-text-faint">{note}</span>
			</li>
		{/each}
	</ul>
{/if}
