<script lang="ts">
	import type { ActivePin, ArchitectureOut, ModelVersionOut, RegistryEntry, SourceOut } from '$lib/api/types';
	import { colorFor, god } from '$lib/branding';
	import { displayShape, formatParams, formatShape } from './shapes';
	import { byUse, readersOf, sourceName, usedByText, useOf, type SourceUse } from './source-use';

	let {
		registry,
		pin,
		architectures,
		sources,
		sourcesFailed = false,
		selected = $bindable(null),
		anchor = $bindable(null)
	}: {
		registry: RegistryEntry[];
		pin: ActivePin | null;
		architectures: Record<string, ArchitectureOut | undefined>;
		/** The /v1/sources rows, or null while they aren't known. */
		sources: SourceOut[] | null;
		/** Null because the request failed, rather than because it is still out. */
		sourcesFailed?: boolean;
		selected?: string | null;
		/** The selected model's node, for a popover to anchor to. */
		anchor?: SVGGElement | null;
	} = $props();

	// The pipeline left to right, in one coordinate space. On a large screen
	// the SVG scales to the page's width; on a smaller one it keeps the size
	// it has there and its container scrolls sideways.
	const W = 1840;
	const SOURCE = { cx: 126, w: 232, h: 52, pitch: 62 };
	const PAD = 14;
	// Tall enough for the ten sources registered today, so the graph doesn't
	// change height when they arrive. An eleventh makes it taller.
	const MIN_H = 10 * SOURCE.pitch + 2 * PAD;
	const H = $derived(Math.max(MIN_H, (sources?.length ?? 0) * SOURCE.pitch + 2 * PAD));
	const MID = $derived(H / 2);

	interface Node {
		id: string;
		cx: number;
		cy: number;
		w: number;
		h: number;
		title: string;
		sub?: string;
		model?: string;
		/** A data source: how it is used. `pending` is the stand-in drawn
		 * while the sources aren't known. */
		use?: SourceUse | 'pending';
		/** A data source: the models that read it. */
		readers?: string[];
		/** A data source: what its role adds to the picture, if anything. */
		tag?: string;
	}

	const SRC = 'src:';

	// Every registered source, and who reads it, comes from /v1/sources
	// (`used_by`): the mapping is written once, on the API.
	const sourceNodes = $derived.by((): Node[] => {
		const box = { cx: SOURCE.cx, w: SOURCE.w };
		if (!sources) {
			// One stand-in, so the pipeline still has a start. It says
			// nothing about what feeds what.
			const sub = sourcesFailed ? 'not available right now' : 'loading…';
			return [{ ...box, id: SRC, cy: MID, h: 84, title: 'Data sources', sub, use: 'pending', readers: [] }];
		}
		const top = (H - sources.length * SOURCE.pitch) / 2;
		return byUse(sources).map((s, i) => ({
			...box,
			id: SRC + s.key,
			cy: top + SOURCE.pitch * (i + 0.5),
			h: SOURCE.h,
			title: sourceName(s.key),
			sub: s.used_by ? usedByText(s.used_by) : 'use not reported',
			use: useOf(s),
			readers: readersOf(s),
			// The role is the only thing that tells ERA5 from GDAS/GFS here:
			// the same models read both, ERA5 in Stage A pretraining alone.
			tag: s.role === 'pretrain_only' ? 'Stage A' : undefined
		}));
	});

	const nodes = $derived.by((): Node[] => {
		const rows = [-198, -66, 66, 198].map((dy) => MID + dy); // a four-node column
		return [
			...sourceNodes,
			{ id: 'prep', cx: 418, cy: MID, w: 160, h: 84, title: 'Preprocessing', sub: 'feature engineering' },
			{ id: 'lstm', cx: 753, cy: rows[0], w: 250, h: 108, title: 'lstm', model: 'lstm' },
			{ id: 'cnn', cx: 753, cy: rows[1], w: 250, h: 108, title: 'cnn', model: 'cnn' },
			{ id: 'transformer', cx: 753, cy: rows[2], w: 250, h: 108, title: 'transformer', model: 'transformer' },
			{ id: 'gnn', cx: 753, cy: rows[3], w: 250, h: 108, title: 'gnn', model: 'gnn' },
			{ id: 'pinn', cx: 1084, cy: MID, w: 228, h: 108, title: 'pinn', model: 'pinn' },
			{ id: 'fusion', cx: 1397, cy: MID, w: 228, h: 108, title: 'fusion', model: 'fusion' },
			{ id: 'diffusion', cx: 1710, cy: MID, w: 228, h: 108, title: 'diffusion', model: 'diffusion' },
			{ id: 'post', cx: 1710, cy: MID + 180, w: 228, h: 84, title: 'Post-processing', sub: 'cone · intensity · landfall · RI' }
		];
	});
	const byId = $derived(new Map(nodes.map((n) => [n.id, n])));

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
	/** From preprocessing on, which doesn't depend on the sources. */
	const flow: Edge[] = [
		...GROUP1.map((m) => ({ from: 'prep', to: m, label: () => shapeOf(m, 'inputs'), at: 'target' as Where, delay: 0.5 })),
		...GROUP1.map((m) => ({ from: m, to: 'pinn', label: () => shapeOf(m, 'outputs'), at: 'source' as Where, delay: 1 })),
		{ from: 'pinn', to: 'fusion', label: () => shapeOf('pinn', 'outputs'), at: 'middle', delay: 1.5 },
		{ from: 'fusion', to: 'diffusion', label: () => shapeOf('fusion', 'outputs'), at: 'middle', delay: 2 },
		{ from: 'diffusion', to: 'post', label: () => 'members', at: 'middle', delay: 2.5 }
	];
	const edges = $derived<Edge[]>([
		// Labels and verification never reach a model's input, so those
		// sources stand apart, with no edge into the pipeline.
		...sourceNodes.filter((n) => n.use !== 'reference').map((n) => ({ from: n.id, to: 'prep', delay: 0 })),
		...flow
	]);

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
	const upstreamOf = (id: string) => closure(id, (n) => flow.filter((e) => e.to === n).map((e) => e.from));
	const downstreamOf = (id: string) => closure(id, (n) => flow.filter((e) => e.from === n).map((e) => e.to));

	/** The edges data takes to and from `focus`; everything else is muted.
	 * For a model: through it, from the sources the models at or upstream
	 * of it read. For a source: into the models that read it, and on from
	 * them. */
	function pathOf(focus: Node): Set<Edge> {
		if (focus.readers) {
			const readers = new Set(focus.readers);
			const after = new Set(focus.readers.flatMap((m) => [m, ...downstreamOf(m)]));
			return new Set(
				edges.filter(
					(e) =>
						e.from === focus.id ||
						(e.from === 'prep' && readers.has(e.to)) ||
						(after.has(e.from) && after.has(e.to))
				)
			);
		}
		const before = new Set([...upstreamOf(focus.id), focus.id]);
		const after = new Set([focus.id, ...downstreamOf(focus.id)]);
		return new Set(
			edges.filter((e) => {
				const readers = byId.get(e.from)?.readers;
				if (readers) return readers.some((m) => before.has(m));
				return (before.has(e.from) && before.has(e.to)) || (after.has(e.from) && after.has(e.to));
			})
		);
	}

	let hovered = $state<string | null>(null);
	const focus = $derived(byId.get(hovered ?? selected ?? ''));
	const onPath = $derived(focus ? pathOf(focus) : null);

	/** Whether anything travels the edge at all: not from a source no model
	 * reads, or one whose use isn't known. */
	function carries(e: Edge): boolean {
		const use = byId.get(e.from)?.use;
		return use === undefined || use === 'input';
	}
	const lit = (e: Edge) => onPath === null || onPath.has(e);

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

	// $state although nothing reacts to it: bind:this into a plain object
	// logs binding_property_non_reactive on every render in development.
	const nodeEls = $state<Record<string, SVGGElement>>({});
	function select(model: string) {
		selected = model;
		anchor = nodeEls[model] ?? null;
	}
	function nodeOnPath(id: string): boolean {
		if (onPath === null || id === focus?.id) return true;
		for (const e of onPath) if (e.from === id || e.to === id) return true;
		return false;
	}

	// Narrower than the graph, the container scrolls sideways. Nothing in a
	// phone browser shows that, so the cut edge reads as the end of the
	// drawing: fade the side there is more on, and say so under the graph.
	let scroller = $state<HTMLDivElement | null>(null);
	let more = $state({ left: false, right: false });
	function measure() {
		if (!scroller) return;
		const hidden = scroller.scrollWidth - scroller.clientWidth;
		more = { left: scroller.scrollLeft > 1, right: scroller.scrollLeft < hidden - 1 };
	}
	$effect(() => {
		if (!scroller) return;
		const observer = new ResizeObserver(measure);
		observer.observe(scroller);
		return () => observer.disconnect();
	});

	const LEGEND: { use: SourceUse; text: string }[] = [
		{ use: 'input', text: 'feeds a model' },
		{ use: 'reference', text: 'labels or verification only, never a model input' },
		{ use: 'unused', text: 'not used yet' }
	];
	// Only the states that are drawn: none while the sources are loading,
	// and none of these three from an API that doesn't send `used_by`.
	const drawn = $derived(new Set(sourceNodes.map((n) => n.use)));
	const legend = $derived(LEGEND.filter((item) => drawn.has(item.use)));
</script>

<!-- The mark that tells the three states apart without colour: a solid
     dot, a tick, an open dashed ring. Drawn around (0, 0). -->
{#snippet mark(use: Node['use'])}
	<g aria-hidden="true">
		{#if use === 'input'}
			<circle r="5.5" class="fill-action" />
		{:else if use === 'reference'}
			<path d="M -6 0.5 L -2 4.5 L 6 -4.5" fill="none" class="stroke-text-muted" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
		{:else if use === 'unused'}
			<circle r="5.5" fill="none" class="stroke-text-muted" stroke-width="1.6" stroke-dasharray="2.4 2.6" />
		{/if}
	</g>
{/snippet}

<div class="relative">
	<div bind:this={scroller} onscroll={measure} class="overflow-x-auto">
		<svg viewBox={`0 0 ${W} ${H}`} class="h-auto w-full min-w-[1080px] lg:min-w-0" role="group" aria-label="Anemoi system">
			<defs>
				<marker id="sys-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
					<path d="M 0 0 L 10 5 L 0 10 z" class="fill-text-faint" />
				</marker>
			</defs>

			{#each edges as e (e.from + e.to)}
				{@const a = byId.get(e.from)!}
				{@const b = byId.get(e.to)!}
				{@const flowing = carries(e)}
				{@const live = flowing && lit(e)}
				{@const label = e.label?.()}
				<!-- Dashed when nothing is known to travel it: a source nothing
				     reads yet, the stand-in, or a source whose use the API
				     didn't say. A solid edge would claim that last one feeds
				     the models, labels-only best-track included. -->
				<path
					d={path(a, b)}
					data-edge={`${e.from}>${e.to}`}
					fill="none"
					class="stroke-border-strong transition-opacity duration-300"
					stroke-width="1.4"
					stroke-dasharray={a.use && a.use !== 'input' ? '5 6' : undefined}
					opacity={lit(e) ? 1 : 0.35}
					marker-end="url(#sys-arrow)"
				/>
				{#if flowing}
					<!-- The beam: a short bright dash running the edge's length
					     once a cycle, later the further downstream the edge is. -->
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
				{/if}
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
				{:else if n.use === 'pending'}
					<g data-sources-pending>
						<rect
							x={x} y={y} width={n.w} height={n.h} rx="8"
							class="fill-bg stroke-border-strong" stroke-width="1.2" stroke-dasharray="5 5"
						/>
						<text x={n.cx} y={n.cy - 4} text-anchor="middle" class="fill-text-muted text-[16px]">{n.title}</text>
						<text x={n.cx} y={n.cy + 20} text-anchor="middle" class="fill-text-muted text-[14px]">{n.sub}</text>
					</g>
				{:else if n.use}
					{@const quiet = n.use === 'unused' || n.use === 'unknown'}
					{@const marked = n.use !== 'unknown'}
					{@const read = n.use === 'input'}
					<!-- Hovering a source a model reads lights those models. It
					     isn't a button: there is nothing more to open, and its
					     second line says the same in words. A source nothing
					     reads doesn't answer the pointer, or crossing the column
					     would dim the whole graph. -->
					<g
						data-source-node={n.id.slice(SRC.length)}
						data-use={n.use}
						role="img"
						aria-label={`${n.title}: ${n.sub}${n.tag ? `, ${n.tag}` : ''}`}
						class="transition-opacity duration-300"
						opacity={dim ? 0.45 : 1}
						onmouseenter={read ? () => (hovered = n.id) : undefined}
						onmouseleave={read ? () => (hovered = null) : undefined}
					>
						<rect
							x={x} y={y} width={n.w} height={n.h} rx="8"
							class={`fill-bg ${hovered === n.id ? 'stroke-text-faint' : 'stroke-border-strong'}`}
							stroke-width="1.2"
							stroke-dasharray={n.use === 'unused' ? '5 5' : undefined}
						/>
						{#if marked}
							<g transform={`translate(${x + 21} ${y + 19})`}>{@render mark(n.use)}</g>
						{/if}
						<text x={x + (marked ? 36 : 14)} y={y + 24} class={`text-[15px] ${quiet ? 'fill-text-muted' : 'fill-text'}`}>{n.title}</text>
						<text x={x + 14} y={y + 43} class="fill-text-muted text-[14px]">{n.sub}</text>
						{#if n.tag}
							<text x={x + n.w - 12} y={y + 24} text-anchor="end" class="fill-text-muted text-[13px]">{n.tag}</text>
						{/if}
					</g>
				{:else}
					<g class="transition-opacity duration-300" opacity={dim ? 0.45 : 1}>
						<rect x={x} y={y} width={n.w} height={n.h} rx="8" class="fill-bg stroke-border" stroke-width="1.2" />
						<text x={n.cx} y={n.cy - 4} text-anchor="middle" class="fill-text text-[16px]">{n.title}</text>
						{#if n.sub}
							<text x={n.cx} y={n.cy + 20} text-anchor="middle" class="fill-text-faint text-[14px]">{n.sub}</text>
						{/if}
					</g>
				{/if}
			{/each}
		</svg>
	</div>
	{#if more.left}
		<div class="pointer-events-none absolute inset-y-0 left-0 w-10 bg-linear-to-r from-bg to-transparent"></div>
	{/if}
	{#if more.right}
		<div class="pointer-events-none absolute inset-y-0 right-0 w-10 bg-linear-to-l from-bg to-transparent"></div>
	{/if}
</div>

<div class="mt-2 space-y-1.5 px-1 text-xs text-text-muted">
	{#if more.left || more.right}
		<p>Scroll the graph sideways to follow the pipeline.</p>
	{/if}
	{#if legend.length}
		<ul class="flex flex-wrap items-center gap-x-5 gap-y-1.5" aria-label="How a data source is drawn">
			{#each legend as item (item.use)}
				<li class="flex items-center gap-2">
					<svg viewBox="0 0 34 20" class="h-4 w-[27px] shrink-0" aria-hidden="true">
						<rect
							x="1" y="1" width="32" height="18" rx="5"
							class="fill-bg stroke-text-faint" stroke-width="1.2"
							stroke-dasharray={item.use === 'unused' ? '4 3.5' : undefined}
						/>
						<g transform="translate(17 10)">{@render mark(item.use)}</g>
					</svg>
					{item.text}
				</li>
			{/each}
		</ul>
	{/if}
	{#if drawn.has('unknown')}
		<p>This API doesn't say what uses each source, so none is drawn as feeding a model.</p>
	{/if}
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
