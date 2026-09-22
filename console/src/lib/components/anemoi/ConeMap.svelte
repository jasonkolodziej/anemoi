<script lang="ts">
	/**
	 * Track + cone of uncertainty on a real interactive MapLibre map
	 * (svelte-maplibre-gl -- https://svelte-maplibre-gl.mierune.dev/docs/
	 * quickstart), replacing the previous hand-rolled equirectangular SVG
	 * projection. Pan/zoom is the point of this change -- the old
	 * self-contained "zero runtime network calls" approach (a bundled
	 * Natural Earth coastline extract) is deliberately traded away here
	 * for a real basemap; `dark-matter-gl-style` (CartoDB, no API key)
	 * keeps the map itself matching this app's dark theme rather than
	 * introducing a jarring light/satellite basemap.
	 *
	 * "Keep the current styling usage": every data layer's color is
	 * still this app's actual brand tokens (`--color-fusion`,
	 * `--color-action`, `--color-text-faint`, `--color-bg`), not new
	 * hardcoded hex -- `resolveColor` reads them from the DOM at runtime
	 * (MapLibre paint properties need real color strings, not a raw
	 * `var(--x)` reference, since the GL renderer parses them itself
	 * rather than going through the browser's CSS cascade). The legend
	 * now floats over the map itself (bottom-left), not below it.
	 *
	 * Cone circles are real geodesic polygons (`geoCircle`), not
	 * MapLibre's screen-space `circle-radius` -- a 300nm cone must shrink/
	 * grow with the map's real geographic scale when zooming, the same
	 * real-distance correctness the old `nmToPx` conversion had.
	 *
	 * Layout/interaction (in-map legend, a pulsing current-fix marker,
	 * per-model tracks) is deliberately modeled on the original
	 * branding-brief concept mock's `WindRoseMap` -- but only where real
	 * data supports it. Per-model tracks *are* real (`per_model_tracks`
	 * per contributing Group 1 model, keyed by architecture slug):
	 * `training.real_inference_cycle.build_real_deterministic_fn`
	 * already computes each model's own prediction before fusing them,
	 * it just used to be discarded once fusion had it -- surfaced
	 * end-to-end for this. The concept mock's raw Skiron ensemble-member
	 * polylines are a different story: `ConeSegmentOut` is one aggregate
	 * radius per lead time, not per-member positions, so there is no
	 * real per-member geometry to draw -- the cone-circle rendering
	 * already here is the honest equivalent of that spread, and its own
	 * legend entry says so ("cone/spread"). The legend itself is real
	 * and clickable (each entry toggles its own layer's real MapLibre
	 * `visibility`), not just a static key the way the concept mock's
	 * map-embedded legend was.
	 *
	 * "Wind Rose Projection" v1.2 pass: adopted the concept's real-data
	 * ideas, not its literal geometry. Each forecast point's dot is now
	 * colored by its own real `wind_kt` (`$lib/utils.SAFFIR_SIMPSON`, the
	 * real external NHC classification, not this app's invention), the
	 * current-fix pulse rate now scales with real `max_wind_kt`, and a
	 * real landfall reference marker renders at `CyclePayload.
	 * coastline_lat/lon` when the cycle was run with one. Deliberately
	 * NOT adopted: concentric fixed-radius "lead time" rings around the
	 * current fix -- on a real geographic map (unlike the concept's
	 * stylized SVG) a storm's real ground speed varies, so a static ring
	 * at some radius doesn't correspond to "reachable by hour N" in any
	 * honest way; drawing one would be a real, if subtle, fabrication.
	 */
	import 'svelte-maplibre-gl/vite';
	import { onMount, untrack } from 'svelte';
	import type { Map as MaplibreMap, ExpressionSpecification } from 'maplibre-gl';
	import {
		MapLibre,
		GeoJSONSource,
		FillLayer,
		LineLayer,
		CircleLayer,
		SymbolLayer,
		Marker,
		AttributionControl,
	} from 'svelte-maplibre-gl';
	import type { ConeSegmentOut, FixOut, TrackPointOut } from '$lib/api/types';
	import { cn, SAFFIR_SIMPSON, saffirSimpson } from '$lib/utils';
	import { colorFor } from '$lib/branding';

	interface Props {
		history: FixOut[];
		forecastTrack: TrackPointOut[];
		cone: ConeSegmentOut[];
		perModelTracks?: Record<string, TrackPointOut[]>;
		/** Bindable so a sibling panel (Model Pantheon) can drive which
		 * model's track is isolated on the map, and vice versa -- real
		 * cross-component hover-to-isolate, the concept mock's own
		 * `hovered` state, now backed by real per-model geometry. */
		hoveredModel?: string | null;
		/** The real coastal reference point `landfall_probability` was
		 * computed against (`CyclePayload.coastline_lat/lon`) -- null
		 * whenever the cycle didn't request one. */
		coastlineLat?: number | null;
		coastlineLon?: number | null;
		/** `CyclePayload.cycle` -- the real identity of the cycle currently
		 * loaded, used only to decide *when* to auto-fit the map (see the
		 * fitBounds effect below), not rendered. */
		cycleLabel?: string | null;
	}
	let {
		history,
		forecastTrack,
		cone,
		perModelTracks = {},
		hoveredModel = $bindable(null),
		coastlineLat = null,
		coastlineLon = null,
		cycleLabel = null,
	}: Props = $props();

	const DARK_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
	const NM_TO_KM = 1.852;
	const EARTH_RADIUS_KM = 6371.0088;

	// Resolves a CSS custom property (as authored on :root, e.g. an
	// oklch() value) to the browser-normalized rgb() string MapLibre's own
	// color parser can read -- var(--x) itself only means something to the
	// browser's CSS cascade, not to MapLibre's paint-property parser.
	function resolveColor(varName: string): string {
		const el = document.createElement('span');
		el.style.color = `var(${varName})`;
		document.body.appendChild(el);
		const rgb = getComputedStyle(el).color;
		el.remove();
		return rgb;
	}

	let colors = $state({
		fusion: '#f8fafc',
		action: '#60a5fa',
		textFaint: '#64748b',
		bg: '#0a0e17',
		statusDegraded: '#fb923c',
	});

	onMount(() => {
		colors = {
			fusion: resolveColor('--color-fusion'),
			action: resolveColor('--color-action'),
			textFaint: resolveColor('--color-text-faint'),
			bg: resolveColor('--color-bg'),
			statusDegraded: resolveColor('--color-status-degraded'),
		};
	});

	// Standard spherical destination-point formula (bearing swept 0..360)
	// -- the same real-world-distance circle Turf.js's `circle()` produces.
	function geoCircle(lat: number, lon: number, radiusNm: number, points = 64): [number, number][] {
		const angularDist = (radiusNm * NM_TO_KM) / EARTH_RADIUS_KM;
		const latRad = (lat * Math.PI) / 180;
		const lonRad = (lon * Math.PI) / 180;
		const ring: [number, number][] = [];
		for (let i = 0; i <= points; i++) {
			const bearing = (i / points) * 2 * Math.PI;
			const lat2 = Math.asin(
				Math.sin(latRad) * Math.cos(angularDist) +
					Math.cos(latRad) * Math.sin(angularDist) * Math.cos(bearing),
			);
			const lon2 =
				lonRad +
				Math.atan2(
					Math.sin(bearing) * Math.sin(angularDist) * Math.cos(latRad),
					Math.cos(angularDist) - Math.sin(latRad) * Math.sin(lat2),
				);
			ring.push([(lon2 * 180) / Math.PI, (lat2 * 180) / Math.PI]);
		}
		return ring;
	}

	const coneFeatures = $derived({
		type: 'FeatureCollection' as const,
		features: cone.map((seg) => ({
			type: 'Feature' as const,
			properties: { basis: seg.basis },
			geometry: { type: 'Polygon' as const, coordinates: [geoCircle(seg.lat, seg.lon, seg.radius_nm)] },
		})),
	});

	const historyLine = $derived({
		type: 'Feature' as const,
		properties: {},
		geometry: {
			type: 'LineString' as const,
			coordinates: history.map((f) => [f.lon, f.lat]),
		},
	});

	const forecastLine = $derived({
		type: 'Feature' as const,
		properties: {},
		geometry: {
			type: 'LineString' as const,
			coordinates: forecastTrack.map((t) => [t.lon, t.lat]),
		},
	});

	// Real Saffir-Simpson step expression (`$lib/utils.SAFFIR_SIMPSON`,
	// ascending by threshold -- MapLibre's own `step` requires that
	// order) -- each forecast point's dot is colored by its own real
	// `wind_kt`, the map-side half of "intensity indication".
	const intensityColorExpr: ExpressionSpecification = (() => {
		const ascending = [...SAFFIR_SIMPSON].sort((a, b) => a.min - b.min);
		const expr: unknown[] = ['step', ['get', 'wind_kt'], ascending[0].color];
		for (let i = 1; i < ascending.length; i++) expr.push(ascending[i].min, ascending[i].color);
		return expr as ExpressionSpecification;
	})();

	const forecastPoints = $derived({
		type: 'FeatureCollection' as const,
		features: forecastTrack.map((t) => ({
			type: 'Feature' as const,
			properties: {
				label: `${t.lead_hours}h · ${t.wind_kt.toFixed(0)}kt · ${saffirSimpson(t.wind_kt).label}`,
				lead_hours: t.lead_hours,
				wind_kt: t.wind_kt,
			},
			geometry: { type: 'Point' as const, coordinates: [t.lon, t.lat] },
		})),
	});

	const currentFix = $derived(history.length > 0 ? history[history.length - 1] : null);

	// Wind-speed-scaled pulse: a real, monotonic mapping from the current
	// fix's own `max_wind_kt` to the marker's ping animation duration --
	// stronger storms pulse faster. Clamped to a sane range so a very weak
	// (or, at the top end, a Cat 5) storm still reads as an animation, not
	// a flicker or a near-static marker.
	const pulseMs = $derived(
		currentFix ? Math.max(700, Math.min(2600, 2600 - currentFix.max_wind_kt * 11)) : 2000,
	);

	// Wind speed per forecast point is real (`TrackPointOut.wind_kt`),
	// surfaced directly in each point's permanent label below instead of
	// behind a hover popup (tried first; MapLibre's per-layer mouseenter
	// hit-test never fired reliably against the small 4px circles in
	// real browser testing, and the always-visible label already
	// surfaces the same information without needing it).

	const modelSlugs = $derived(Object.keys(perModelTracks));

	// One Feature per model rather than one shared FeatureCollection --
	// `hoveredModel` needs each model's own layer independently
	// dimmable/highlightable via its own `line-opacity`/`line-width`, not
	// a single shared paint expression across all of them.
	const perModelLines = $derived(
		modelSlugs.map((slug) => ({
			slug,
			color: colorFor(slug),
			feature: {
				type: 'Feature' as const,
				properties: {},
				geometry: {
					type: 'LineString' as const,
					coordinates: perModelTracks[slug].map((t) => [t.lon, t.lat]),
				},
			},
		})),
	);

	const bounds = $derived.by((): [[number, number], [number, number]] | null => {
		const points = [
			...history.map((f) => [f.lon, f.lat] as [number, number]),
			...forecastTrack.map((t) => [t.lon, t.lat] as [number, number]),
			...cone.map((c) => [c.lon, c.lat] as [number, number]),
			...(coastlineLat !== null && coastlineLon !== null
				? [[coastlineLon, coastlineLat] as [number, number]]
				: []),
		];
		if (points.length === 0) return null;
		const lons = points.map((p) => p[0]);
		const lats = points.map((p) => p[1]);
		return [
			[Math.min(...lons), Math.min(...lats)],
			[Math.max(...lons), Math.max(...lats)],
		];
	});

	// A real, clickable legend (not just a static key) -- each entry
	// toggles its own layer's visibility via MapLibre's `visibility`
	// layout property, which just hides/shows already-rendered geometry
	// (no re-fetch, no source rebuild). "Spread" has no separate toggle
	// of its own: the cone *is* this app's real representation of
	// spread (see the module docstring for why raw per-member polylines
	// -- what the concept mock drew -- aren't real data here), so
	// toggling "cone" toggles the same thing.
	let visible = $state({
		currentFix: true,
		archiveTrack: true,
		forecast: true,
		cone: true,
		models: true,
		landfall: true,
	});
	function vis(on: boolean): 'visible' | 'none' {
		return on ? 'visible' : 'none';
	}

	let map = $state<MaplibreMap | undefined>();
	// A plain boolean, not `map` itself -- `bind:map` gets rewritten by
	// MapLibre.svelte's own internal move/zoom listener on every pan (it
	// keeps the binding live for imperative access), and a raw `$state`/
	// `$bindable` write always signals "changed" to a directly-dependent
	// effect regardless of reference equality. `$derived` output, unlike
	// that, is compared by value before propagating -- `mapReady` only
	// actually changes once (false -> true, on mount), so depending on it
	// instead of `map` breaks what was an infinite fitBounds loop, found
	// for real: every user pan re-ran this effect, which called
	// fitBounds again, which fired another move event, forever
	// (`effect_update_depth_exceeded`).
	const mapReady = $derived(!!map);

	// A plain (non-reactive) last-fitted-*cycle* guard -- deliberately NOT
	// keyed on the bounds *value* anymore. It was originally (comparing
	// JSON.stringify(bounds) against the last-fitted string), which closed
	// a real infinite-loop bug (fitBounds's own move/moveend events fed
	// back into MapLibre.svelte's internal center/zoom<->camera sync
	// effect closely enough that this effect kept re-scheduling several
	// times for the *same* bounds before settling, tripping Svelte's
	// effect_update_depth_exceeded guard) -- but it had a second, real bug
	// that only surfaced once the storm detail page started polling for
	// fresh data every 60s (console_production_hardening's periodic-
	// refresh fix): a *live* storm's real history/latest_fix genuinely
	// shifts a little on some polls, which changes `bounds`'s real value
	// even though the user is still looking at the exact same cycle --
	// found live against EP172026, an active storm, reported as "the map
	// resets on its own, especially noticeable mid-scroll/touch" (the
	// background poll firing is not actually caused by the touch, it just
	// lands then, so it reads as the touch triggering it). Re-fitting on
	// every real data refresh fights the user's own pan/zoom. Keying on
	// `cycleLabel` instead fits exactly once per cycle the user actually
	// loaded (first view, running a new one, clicking a past-cycle button)
	// and never again while a background poll quietly refreshes the same
	// cycle's storm history underneath them.
	let lastFittedCycle: string | null | undefined;

	$effect(() => {
		if (!mapReady || !bounds) return;
		if (cycleLabel === lastFittedCycle) return;
		lastFittedCycle = cycleLabel;
		const m = untrack(() => map);
		m?.fitBounds(bounds, { padding: 48, duration: 0 });
	});
</script>

<div class="relative">
<MapLibre
	bind:map
	class="h-[380px] w-full rounded-md border border-border"
	style={DARK_STYLE}
	attributionControl={false}
>
	<!-- Moved off bottom-left (MapLibre's default) -- that's exactly
	     where the real, clickable legend below now lives, and the two
	     controls overlapping there was a real, found-for-real bug: the
	     attribution link's own click target sat on top of the legend's
	     "cone/spread" toggle at the map's default size, silently
	     swallowing clicks meant for the legend. -->
	<AttributionControl compact position="top-right" />

	<GeoJSONSource data={coneFeatures}>
		<FillLayer
			layout={{ visibility: vis(visible.cone) }}
			paint={{ 'fill-color': colors.fusion, 'fill-opacity': 0.05 }}
		/>
		<LineLayer
			filter={['==', ['get', 'basis'], 'climatology']}
			layout={{ visibility: vis(visible.cone) }}
			paint={{ 'line-color': colors.fusion, 'line-width': 1, 'line-opacity': 0.35, 'line-dasharray': [2, 2] }}
		/>
		<LineLayer
			filter={['!=', ['get', 'basis'], 'climatology']}
			layout={{ visibility: vis(visible.cone) }}
			paint={{ 'line-color': colors.fusion, 'line-width': 1, 'line-opacity': 0.35 }}
		/>
	</GeoJSONSource>

	<GeoJSONSource data={historyLine}>
		<LineLayer
			layout={{ visibility: vis(visible.archiveTrack) }}
			paint={{ 'line-color': colors.textFaint, 'line-width': 1.5, 'line-dasharray': [2, 3] }}
		/>
	</GeoJSONSource>

	<!-- Per-model tracks, drawn under the fused consensus track (below)
	     so the consensus stays the visually dominant line -- real per-
	     model geometry, see the module docstring. `hoveredModel` is bound
	     from Model Pantheon's own hover (dims the rest of these lines to
	     25%) -- one-directional, not two-way: MapLibre's per-layer
	     mouseenter hit-testing on these lines didn't fire reliably in
	     real browser testing (the same finding as the forecast-point
	     hover popup, tried and dropped earlier in this file's history),
	     and the original concept mock's own hover only ever lived on the
	     panel side anyway, never on the map lines themselves. -->
	{#each perModelLines as { slug, color, feature } (slug)}
		<GeoJSONSource data={feature}>
			<LineLayer
				layout={{ visibility: vis(visible.models) }}
				paint={{
					'line-color': color,
					'line-width': hoveredModel === slug ? 3 : 2,
					'line-opacity': hoveredModel === null ? 0.6 : hoveredModel === slug ? 1 : 0.25,
				}}
			/>
		</GeoJSONSource>
	{/each}

	<GeoJSONSource data={forecastLine}>
		<LineLayer
			paint={{ 'line-color': colors.fusion, 'line-width': 2.5 }}
			layout={{ 'line-cap': 'round', visibility: vis(visible.forecast) }}
		/>
	</GeoJSONSource>

	<GeoJSONSource data={forecastPoints}>
		<CircleLayer
			layout={{ visibility: vis(visible.forecast) }}
			paint={{
				'circle-radius': 5,
				'circle-color': intensityColorExpr,
				'circle-stroke-color': colors.bg,
				'circle-stroke-width': 1.5,
			}}
		/>
		<SymbolLayer
			layout={{
				'text-field': ['get', 'label'],
				'text-size': 10,
				'text-offset': [0.9, -0.6],
				'text-anchor': 'left',
				visibility: vis(visible.forecast),
			}}
			paint={{ 'text-color': colors.textFaint }}
		/>
	</GeoJSONSource>

	{#if currentFix && visible.currentFix}
		<Marker lnglat={[currentFix.lon, currentFix.lat]}>
			{#snippet content()}
				<span class="relative flex h-3 w-3">
					<span
						class="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60"
						style={`background: ${colors.action}; animation-duration: ${pulseMs}ms`}
					></span>
					<span class="relative block h-3 w-3 rounded-full" style={`background: ${colors.action}`}></span>
				</span>
			{/snippet}
		</Marker>
	{/if}

	{#if coastlineLat !== null && coastlineLon !== null && visible.landfall}
		<Marker lnglat={[coastlineLon, coastlineLat]}>
			{#snippet content()}
				<svg width="16" height="16" viewBox="0 0 16 16" aria-label="Landfall reference point">
					<path d="M8 1 L14.5 14 L1.5 14 Z" fill={colors.statusDegraded} stroke={colors.bg} stroke-width="1.5" />
				</svg>
			{/snippet}
		</Marker>
	{/if}
</MapLibre>

<div
	class="absolute bottom-3 left-3 flex flex-wrap items-center gap-x-1 gap-y-1 rounded-md border border-border bg-bg/85 px-1.5 py-1 text-[11px] text-text-faint backdrop-blur-sm"
>
	<button
		type="button"
		aria-pressed={visible.currentFix}
		onclick={() => (visible.currentFix = !visible.currentFix)}
		class={cn(
			'flex items-center gap-1.5 rounded px-1 py-0.5 transition-colors hover:bg-surface-raised',
			!visible.currentFix && 'opacity-40',
		)}
	>
		<span class="h-2 w-2 rounded-full bg-action"></span>current fix
	</button>
	<button
		type="button"
		aria-pressed={visible.archiveTrack}
		onclick={() => (visible.archiveTrack = !visible.archiveTrack)}
		class={cn(
			'flex items-center gap-1.5 rounded px-1 py-0.5 transition-colors hover:bg-surface-raised',
			!visible.archiveTrack && 'opacity-40',
		)}
	>
		<span class="inline-block h-px w-4 border-t border-dashed border-text-faint"></span>archive track
	</button>
	<button
		type="button"
		aria-pressed={visible.forecast}
		onclick={() => (visible.forecast = !visible.forecast)}
		class={cn(
			'flex items-center gap-1.5 rounded px-1 py-0.5 transition-colors hover:bg-surface-raised',
			!visible.forecast && 'opacity-40',
		)}
	>
		<span class="h-2 w-2 rounded-full bg-fusion"></span>forecast (fusion)
	</button>
	<button
		type="button"
		aria-pressed={visible.cone}
		onclick={() => (visible.cone = !visible.cone)}
		class={cn(
			'flex items-center gap-1.5 rounded px-1 py-0.5 transition-colors hover:bg-surface-raised',
			!visible.cone && 'opacity-40',
		)}
	>
		<span class="h-2 w-2 rounded-full bg-fusion opacity-20"></span>cone/spread (dashed = climatology fallback)
	</button>
	{#if modelSlugs.length > 0}
		<button
			type="button"
			aria-pressed={visible.models}
			onclick={() => (visible.models = !visible.models)}
			class={cn(
				'flex items-center gap-1.5 rounded px-1 py-0.5 transition-colors hover:bg-surface-raised',
				!visible.models && 'opacity-40',
			)}
		>
			<span class="h-2 w-2 rounded-full" style={`background: ${colors.textFaint}`}></span>individual model tracks
		</button>
	{/if}
	{#if coastlineLat !== null && coastlineLon !== null}
		<button
			type="button"
			aria-pressed={visible.landfall}
			onclick={() => (visible.landfall = !visible.landfall)}
			class={cn(
				'flex items-center gap-1.5 rounded px-1 py-0.5 transition-colors hover:bg-surface-raised',
				!visible.landfall && 'opacity-40',
			)}
		>
			<span class="h-2 w-2 rounded-full" style={`background: ${colors.statusDegraded}`}></span>landfall reference
		</button>
	{/if}
</div>
</div>

<style>
	/* MapLibre's own AttributionControl ships hardcoded as a white pill
	   (`hsla(0,0%,100%,.5)`, maplibre-gl.css) -- CARTO/OSM's terms require
	   real attribution to stay visible, so this restyles it to the dark
	   theme rather than hiding it outright. It's rendered by the library
	   itself outside this component's own markup, so a scoped <style>
	   block can't reach it without :global(). */
	:global(.maplibregl-ctrl-attrib) {
		background-color: var(--color-surface) !important;
		color: var(--color-text-faint) !important;
		border-radius: 0.375rem;
	}
	:global(.maplibregl-ctrl-attrib a) {
		color: var(--color-text-faint) !important;
	}
	:global(.maplibregl-ctrl-attrib-button) {
		background-color: transparent !important;
		filter: invert(1) grayscale(1) opacity(0.6);
	}
</style>
