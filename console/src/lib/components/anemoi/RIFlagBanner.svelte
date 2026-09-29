<script lang="ts">
	/**
	 * Rapid intensification is the single most safety-critical signal this
	 * console shows. Deliberately outside the god/structural colour system --
	 * a high-contrast placard (Fusion's near-white, inverted) with a slow
	 * pulse, the one bold motion moment in this app (frontend-design:
	 * "spend your boldness in one place").
	 *
	 * Three states, not two (#188). `probability` is a fraction of a finite
	 * ensemble, and the alert threshold is a hard cut at 30% -- so when the
	 * 95% interval spans the threshold, neither "flagged" nor "no signal" is
	 * a true statement, and presenting either one is the actual defect. The
	 * third state says so rather than picking a side of a coin flip.
	 *
	 * `lo`/`hi`/`uncertain` are null on cycles served before #188, which are
	 * still readable from R2 -- those fall back to the original two states.
	 */
	interface Props {
		flagged: boolean;
		probability: number;
		lo?: number | null;
		hi?: number | null;
		uncertain?: boolean | null;
		ensembleSize?: number | null;
	}
	let {
		flagged,
		probability,
		lo = null,
		hi = null,
		uncertain = null,
		ensembleSize = null,
	}: Props = $props();

	const pct = (v: number) => `${(v * 100).toFixed(0)}%`;
	const range = $derived(
		lo !== null && hi !== null ? `${pct(lo)}–${pct(hi)}` : null,
	);
	const membersNote = $derived(
		ensembleSize !== null ? ` from ${ensembleSize} members` : "",
	);
</script>

{#if uncertain}
	<!-- Amber, not the bold placard: this is "we cannot tell", which must not
	     read as an all-clear and must not read as an alarm either. -->
	<div
		class="flex items-center gap-3 rounded-lg border border-status-degraded/40 bg-status-degraded/10 px-4 py-3"
	>
		<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true" class="shrink-0 text-status-degraded">
			<circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2" />
			<line x1="12" y1="7" x2="12" y2="13" stroke="currentColor" stroke-width="2" />
			<circle cx="12" cy="16.5" r="1" fill="currentColor" />
		</svg>
		<div class="flex-1">
			<p class="font-display text-sm font-semibold text-status-degraded">
				Rapid intensification undetermined
			</p>
			<p class="text-xs text-text-muted">
				{pct(probability)} of members show ≥30kt/24h{membersNote}, but the 95%
				range{range ? ` (${range})` : ""} spans the 30% alert threshold — too few members
				to tell which side this is on.
			</p>
		</div>
	</div>
{:else if flagged}
	<div
		class="flex items-center gap-3 rounded-lg border border-fusion/30 bg-fusion px-4 py-3 text-bg motion-safe:animate-[ri-pulse_2.4s_ease-in-out_infinite]"
	>
		<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true" class="shrink-0">
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
			<p class="text-xs opacity-80">
				≥30kt gain in 24h across {pct(probability)} of ensemble members{range
					? ` (95% range ${range})`
					: ""}
			</p>
		</div>
	</div>
{:else}
	<div class="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3">
		<div class="h-2 w-2 shrink-0 rounded-full bg-text-faint"></div>
		<p class="text-xs text-text-muted">
			No rapid intensification signal — {pct(probability)} of members show ≥30kt/24h{range
				? ` (95% range ${range})`
				: ""}
		</p>
	</div>
{/if}
