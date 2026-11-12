<script lang="ts">
	import type { ActivePin, ArchitectureOut, ModelVersionOut, RegistryEntry } from '$lib/api/types';
	import { colorFor, god } from '$lib/branding';
	import { displayShape, formatParams, formatShape } from './shapes';

	let {
		registry,
		pin,
		architectures,
		selected = $bindable(null),
		anchor = $bindable(null)
	}: {
		registry: RegistryEntry[];
		pin: ActivePin | null;
		architectures: Record<string, ArchitectureOut | undefined>;
		selected?: string | null;
		/** The selected model's node, for a popover to anchor to. */
		anchor?: SVGGElement | null;
	} = $props();

	// The pipeline left to right, in one coordinate space the SVG scales to
	// the page's width (and scrolls sideways when narrower than ~900 px).
	const W = 1700;
	const H = 520;
	const ROWS = [70, 190, 310, 430]; // centres of a four-node column
	const MID = 250;

	interface Node {
		id: string;
		cx: number;
		cy: number;
		w: number;
		h: number;
		title: string;
		sub?: string;
		model?: string;
	}

	const nodes: Node[] = [
		{ id: 'src-track', cx: 100, cy: ROWS[0], w: 180, h: 84, title: 'Working best-track', sub: 'TC-Vitals · HURDAT2' },
		{ id: 'src-gfs', cx: 100, cy: ROWS[1], w: 180, h: 84, title: 'GDAS / GFS t−6', sub: 'f006 · ERA5 in Stage A' },
		{ id: 'src-goes', cx: 100, cy: ROWS[2], w: 180, h: 84, title: 'GOES imagery', sub: 'not used by a model yet' },
		{ id: 'src-obs', cx: 100, cy: ROWS[3], w: 180, h: 84, title: 'Buoy / dropsonde', sub: 'not used by a model yet' },
		{ id: 'prep', cx: 340, cy: MID, w: 170, h: 84, title: 'Preprocessing', sub: 'feature engineering' },
		{ id: 'lstm', cx: 680, cy: ROWS[0], w: 250, h: 108, title: 'lstm', model: 'lstm' },
		{ id: 'cnn', cx: 680, cy: ROWS[1], w: 250, h: 108, title: 'cnn', model: 'cnn' },
		{ id: 'transformer', cx: 680, cy: ROWS[2], w: 250, h: 108, title: 'transformer', model: 'transformer' },
		{ id: 'gnn', cx: 680, cy: ROWS[3], w: 250, h: 108, title: 'gnn', model: 'gnn' },
		{ id: 'pinn', cx: 1000, cy: MID, w: 205, h: 108, title: 'pinn', model: 'pinn' },
		{ id: 'fusion', cx: 1290, cy: MID, w: 205, h: 108, title: 'fusion', model: 'fusion' },
		{ id: 'diffusion', cx: 1580, cy: MID, w: 205, h: 108, title: 'diffusion', model: 'diffusion' },
		{ id: 'post', cx: 1580, cy: 430, w: 205, h: 84, title: 'Post-processing', sub: 'cone · intensity · landfall · RI' }
	];
	const byId = new Map(nodes.map((n) => [n.id, n]));

	/** Which sources each model really reads (training.real_run*,
	 * training.real_inference_live): track history for the LSTM, the GFS
	 * crop for the gridded three, both for PINN's track candidate and
	 * environment vector. GOES and in-situ observations feed none yet. */
	const FEEDS: Record<string, string[]> = {
		lstm: ['src-track'],
		cnn: ['src-gfs'],
		transformer: ['src-gfs'],
		gnn: ['src-gfs'],
		pinn: ['src-track', 'src-gfs']
	};
	const USED_SOURCES = new Set(Object.values(FEEDS).flat());
	const GROUP1 = ['lstm', 'cnn', 'transformer', 'gnn'];

	type Where = 'target' | 'source' | 'middle';
	interface Edge {
		from: string;
		to: string;
		label?: () => string | null;
		at?: Where;
		/** When the beam leaves, in seconds: downstream edges pulse later. */
		delay: number;
	}
	const edges: Edge[] = [
		...['src-track', 'src-gfs', 'src-goes', 'src-obs'].map((s) => ({ from: s, to: 'prep', delay: 0 })),
		...GROUP1.map((m) => ({ from: 'prep', to: m, label: () => shapeOf(m, 'inputs'), at: 'target' as Where, delay: 0.5 })),
		...GROUP1.map((m) => ({ from: m, to: 'pinn', label: () => shapeOf(m, 'outputs'), at: 'source' as Where, delay: 1 })),
		{ from: 'pinn', to: 'fusion', label: () => shapeOf('pinn', 'outputs'), at: 'middle', delay: 1.5 },
		{ from: 'fusion', to: 'diffusion', label: () => shapeOf('fusion', 'outputs'), at: 'middle', delay: 2 },
		{ from: 'diffusion', to: 'post', label: () => 'members', at: 'middle', delay: 2.5 }
	];

	function closure(start: string, step: (id: string) => string[]): Set<string> {
		const seen = new Set<string>();
		const queue = [start];
		while (queue.length) {
			for (const next of step(queue.shift()!)) {
				if (!seen.has(next)) {
					seen.add(next);
					queue.push(next);
				}
			}
		}
		return seen;
	}
	const upstreamOf = (id: string) => closure(id, (n) => edges.filter((e) => e.to === n).map((e) => e.from));
	const downstreamOf = (id: string) => closure(id, (n) => edges.filter((e) => e.from === n).map((e) => e.to));

	/** The edges data takes to and from `focus`: through it, from the
	 * sources the models upstream of it really read. Everything else is muted. */
	function pathOf(focus: string): Set<Edge> {
		const before = new Set([...upstreamOf(focus), focus]);
		const after = new Set([focus, ...downstreamOf(focus)]);
		const sources = new Set([...before].filter((id) => id in FEEDS).flatMap((id) => FEEDS[id]));
		return new Set(
			edges.filter((e) => {
				if (e.from.startsWith('src-')) return before.has('prep') && sources.has(e.from);
				return (before.has(e.from) && before.has(e.to)) || (after.has(e.from) && after.has(e.to));
			})
		);
	}

	let hovered = $state<string | null>(null);
	const focus = $derived(hovered ?? selected);
	const onPath = $derived(focus ? pathOf(focus) : null);

	function flows(e: Edge): boolean {
		if (e.from.startsWith('src-') && !USED_SOURCES.has(e.from)) return false;
		return onPath === null || onPath.has(e);
	}

	function beamColor(e: Edge): string {
		const from = byId.get(e.from)?.model;
		return from ? colorFor(from) : 'var(--color-action)';
	}

	function shapeOf(model: string, which: 'inputs' | 'outputs'): string | null {
		const a = architectures[model];
		return a ? formatShape(displayShape(a[which][0].shape, a.batched)) : null;
	}

	function path(a: Node, b: Node): string {
		if (a.cx === b.cx) return `M ${a.cx} ${a.cy + a.h / 2} L ${b.cx} ${b.cy - b.h / 2}`;
		const x1 = a.cx + a.w / 2;
		const x2 = b.cx - b.w / 2;
		const mx = (x1 + x2) / 2;
		return `M ${x1} ${a.cy} C ${mx} ${a.cy}, ${mx} ${b.cy}, ${x2} ${b.cy}`;
	}

	function labelAt(a: Node, b: Node, at: Where): { x: number; y: number; anchor: string } {
		if (a.cx === b.cx) return { x: a.cx + 10, y: (a.cy + a.h / 2 + b.cy - b.h / 2) / 2 + 5, anchor: 'start' };
		if (at === 'target') return { x: b.cx - b.w / 2 - 10, y: b.cy - 8, anchor: 'end' };
		if (at === 'source') return { x: a.cx + a.w / 2 + 10, y: a.cy - 8, anchor: 'start' };
		return { x: (a.cx + a.w / 2 + b.cx - b.w / 2) / 2, y: a.cy - 10, anchor: 'middle' };
	}

	/** The version a model serves: the active pin's, else production, else the newest. */
	function served(model: string): ModelVersionOut | null {
		const entry = registry.find((e) => e.model === model);
		if (!entry) return null;
		const pinned = pin?.members[model];
		return entry.versions.find((v) => v.version === pinned) ?? entry.production ?? entry.latest ?? null;
	}

	/** A version registered before `trained_basins` was recorded trained on
	 * the Atlantic alone -- what the registry itself assumes
	 * (`ModelRegistry.trained_basins`, Decision Log 56). */
	function basins(v: ModelVersionOut | null): { trained: string[]; verified: string[] } {
		const split = (s?: string) => (s ? s.split(',').map((b) => b.trim()).filter(Boolean) : []);
		if (!v) return { trained: [], verified: [] };
		const trained = 'trained_basins' in v.tags ? split(v.tags['trained_basins']) : ['AL'];
		return { trained, verified: split(v.tags['verified_basins']) };
	}

	const nodeEls: Record<string, SVGGElement> = {};
	function select(model: string) {
		selected = model;
		anchor = nodeEls[model] ?? null;
	}
	function nodeOnPath(id: string): boolean {
		if (onPath === null || id === focus) return true;
		for (const e of onPath) if (e.from === id || e.to === id) return true;
		return false;
	}
</script>

<div class="overflow-x-auto">
	<svg viewBox={`0 0 ${W} ${H}`} class="h-auto w-full min-w-[900px]" role="group" aria-label="Anemoi system">
		<defs>
			<marker id="sys-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
				<path d="M 0 0 L 10 5 L 0 10 z" class="fill-text-faint" />
			</marker>
		</defs>

		{#each edges as e (e.from + e.to)}
			{@const a = byId.get(e.from)!}
			{@const b = byId.get(e.to)!}
			{@const live = flows(e)}
			{@const unusedSource = e.from.startsWith('src-') && !USED_SOURCES.has(e.from)}
			{@const label = e.label?.()}
			<path
				d={path(a, b)}
				fill="none"
				class="stroke-border-strong transition-opacity duration-300"
				stroke-width="1.4"
				stroke-dasharray={unusedSource ? '5 6' : undefined}
				opacity={live ? 1 : 0.35}
				marker-end="url(#sys-arrow)"
			/>
			<!-- The beam: a short bright dash running the edge's length once
			     a cycle, later the further downstream the edge is. -->
			<path
				d={path(a, b)}
				fill="none"
				pathLength="100"
				class="beam"
				class:beam-muted={!live}
				stroke={beamColor(e)}
				stroke-width="3.5"
				stroke-linecap="round"
				style={`animation-delay: ${e.delay}s; color: ${beamColor(e)}`}
			/>
			{#if label}
				{@const l = labelAt(a, b, e.at ?? 'middle')}
				<text
					x={l.x} y={l.y} text-anchor={l.anchor}
					class={`font-data text-[15px] transition-opacity duration-300 ${live && onPath ? 'fill-text' : 'fill-text-faint'}`}
					opacity={live ? 1 : 0.4}
				>{label}</text>
			{/if}
		{/each}

		{#each nodes as n (n.id)}
			{@const x = n.cx - n.w / 2}
			{@const y = n.cy - n.h / 2}
			{@const dim = !nodeOnPath(n.id)}
			{#if n.model}
				{@const model = n.model}
				{@const v = served(model)}
				{@const a = architectures[model]}
				{@const g = god(model)}
				{@const color = colorFor(model)}
				{@const b = basins(v)}
				{@const err = v?.metrics['track_error_48h_nm']}
				{@const active = selected === model || hovered === model}
				<g
					bind:this={nodeEls[model]}
					data-model-node={model}
					role="button"
					tabindex="0"
					aria-pressed={selected === model}
					aria-label={`${g?.name ?? model} (${model})`}
					class="cursor-pointer outline-none transition-opacity duration-300"
					opacity={dim ? 0.45 : 1}
					onclick={() => select(model)}
					onkeydown={(ev) => {
						if (ev.key === 'Enter' || ev.key === ' ') {
							ev.preventDefault();
							select(model);
						}
					}}
					onmouseenter={() => (hovered = model)}
					onmouseleave={() => (hovered = null)}
				>
					<rect
						x={x} y={y} width={n.w} height={n.h} rx="8"
						class="fill-surface"
						stroke={active ? color : 'var(--color-border-strong)'}
						stroke-width={selected === model ? 3 : active ? 2 : 1.2}
					/>
					<rect x={x} y={y} width="6" height={n.h} rx="3" fill={color} />
					<text x={x + 18} y={y + 28} class="fill-text font-display text-[19px] font-semibold">
						{g?.name ?? (model === 'fusion' ? 'Fusion' : model)}<tspan dx="8" class="fill-text-muted font-data text-[14px] font-normal">{model}</tspan>
					</text>
					<text x={x + 18} y={y + 52} class="fill-text-muted font-data text-[15px]">
						{v ? `v${v.version} · ${v.stage}` : 'not registered'}{a ? ` · ${formatParams(a.total_params)}` : ''}
					</text>
					<text x={x + 18} y={y + 74} class="fill-text-faint font-data text-[15px]">
						{err !== undefined ? `48 h track ${Math.round(err)} nm` : '48 h track —'}
					</text>
					<text x={x + 18} y={y + 96} class="font-data text-[15px]">
						{#each ['AL', 'EP', 'CP'] as basin, i (basin)}
							<tspan
								dx={i ? 10 : 0}
								class={b.verified.includes(basin) ? 'fill-clear' : b.trained.includes(basin) ? 'fill-lips' : 'fill-text-faint'}
							>{basin}{b.verified.includes(basin) ? '✓' : ''}</tspan>
						{/each}
					</text>
					{#if a?.defaults}
						<text x={x + n.w - 12} y={y + 24} text-anchor="end" class="fill-lips text-[13px]">defaults</text>
					{/if}
				</g>
			{:else}
				{@const unused = n.id.startsWith('src-') && !USED_SOURCES.has(n.id)}
				<g class="transition-opacity duration-300" opacity={dim || unused ? 0.45 : 1}>
					<rect
						x={x} y={y} width={n.w} height={n.h} rx="8"
						class="fill-bg stroke-border" stroke-width="1.2"
						stroke-dasharray={unused ? '5 5' : undefined}
					/>
					<text x={n.cx} y={n.cy - 4} text-anchor="middle" class="fill-text text-[16px]">{n.title}</text>
					{#if n.sub}
						<text x={n.cx} y={n.cy + 20} text-anchor="middle" class="fill-text-faint text-[14px]">{n.sub}</text>
					{/if}
				</g>
			{/if}
		{/each}
	</svg>
</div>

<style>
	/* pathLength="100" on each beam: one 18-unit dash with a gap longer than
	   the path, so only one dash is ever on it. It enters at the start
	   (offset 18), leaves past the end (offset -100), and waits there. */
	.beam {
		stroke-dasharray: 18 200;
		stroke-dashoffset: 18;
		opacity: 0.9;
		filter: drop-shadow(0 0 5px currentColor) drop-shadow(0 0 2px currentColor);
		animation: beam 3s linear infinite;
		transition: opacity 300ms;
	}
	.beam-muted {
		opacity: 0;
	}
	@keyframes beam {
		/* Runs the edge in the first half of the cycle, then rests, so the
		   pulses read as one wave moving down the pipeline. */
		0% {
			stroke-dashoffset: 18;
		}
		50%,
		100% {
			stroke-dashoffset: -100;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.beam {
			animation: none;
			opacity: 0;
		}
	}
</style>
