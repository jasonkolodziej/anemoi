<script lang="ts">
	/**
	 * Rapid intensification is the single most safety-critical signal this
	 * console shows. Deliberately outside the god/structural colour system --
	 * a high-contrast placard (Fusion's near-white, inverted) with a slow
	 * pulse, the one bold motion moment in this app (frontend-design:
	 * "spend your boldness in one place").
	 */
	interface Props {
		flagged: boolean;
		probability: number;
	}
	let { flagged, probability }: Props = $props();
</script>

{#if flagged}
	<div
		class="flex items-center gap-3 rounded-lg border border-fusion/30 bg-fusion px-4 py-3 text-bg motion-safe:animate-[ri-pulse_2.4s_ease-in-out_infinite]"
	>
		<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
			<path
				d="M12 2 L22 20 H2 Z"
				stroke="currentColor"
				stroke-width="2"
				stroke-linejoin="round"
				fill="none"
			/>
			<line x1="12" y1="9" x2="12" y2="14" stroke="currentColor" stroke-width="2" />
			<circle cx="12" cy="17" r="1" fill="currentColor" />
		</svg>
		<div class="flex-1">
			<p class="font-display text-sm font-semibold">Rapid intensification flagged</p>
			<p class="text-xs opacity-80">≥30kt gain in 24h across {(probability * 100).toFixed(0)}% of ensemble members</p>
		</div>
	</div>
{:else}
	<div class="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3">
		<div class="h-2 w-2 rounded-full bg-text-faint"></div>
		<p class="text-xs text-text-muted">
			No rapid intensification signal — {(probability * 100).toFixed(0)}% of members show ≥30kt/24h
		</p>
	</div>
{/if}
