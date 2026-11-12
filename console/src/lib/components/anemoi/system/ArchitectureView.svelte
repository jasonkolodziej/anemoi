<script lang="ts">
	import type { ArchitectureOut } from '$lib/api/types';
	import { colorFor, god } from '$lib/branding';
	import { displayShape, formatParams, formatShape, stagesOf, type Stage } from './shapes';

	let {
		arch,
		onclose,
		class: className = ''
	}: {
		arch: ArchitectureOut;
		/** Shows a close button, for the popover on large screens. */
		onclose?: () => void;
		class?: string;
	} = $props();

	const color = $derived(colorFor(arch.model));
	const stages = $derived(stagesOf(arch));
	const inputs = $derived(arch.inputs.map((t) => ({ ...t, shape: displayShape(t.shape, arch.batched) })));
	const outputs = $derived(arch.outputs.map((t) => ({ ...t, shape: displayShape(t.shape, arch.batched) })));

	let selected = $state<string | null>(null);
	// The details panel follows the last block hovered or clicked and keeps
	// it after the pointer leaves, so the pointer can move onto the panel to
	// scroll it. "Built with" in its header goes back to the build settings.
	let hovered = $state<string | null>(null);
	function showBuiltWith() {
		hovered = null;
		selected = null;
	}
	const focus = $derived(stages.find((s) => s.key === (hovered ?? selected)) ?? null);
	// Module paths are shown relative to the block's container, so
	// encoder.layers.1.norm1 reads "1.norm1" under encoder.layers.0–5.
	const focusPrefix = $derived(focus ? focus.key.split('.').slice(0, -1).join('.') : '');
	const relative = (path: string) =>
		focusPrefix && path.startsWith(focusPrefix + '.') ? path.slice(focusPrefix.length + 1) : path;
	const focusTop = $derived(focus?.children.length ? Math.min(...focus.children.map((c) => c.depth)) : 0);

	// Block geometry: a box per stage, sized by its output shape on a log
	// scale (a 41×41 field and a 256-wide vector both need to fit on screen).
	const H = 220; // drawing height
	const GAP = 34;
	const log = (n: number) => Math.log2(Math.max(n, 1));

	interface Box {
		w: number; // front face width
		h: number; // front face height
		d: number; // depth, drawn up and to the right
	}

	function boxFor(shape: number[] | null): Box {
		if (!shape || shape.length === 0) return { w: 10, h: 40, d: 10 };
		if (shape.length === 1) return { w: 10, h: clamp(log(shape[0]) * 14, 24, 150), d: 10 };
		if (shape.length === 2) {
			const [a, b] = shape;
			return { w: clamp(log(a) * 8, 12, 60), h: clamp(log(b) * 14, 24, 150), d: 10 };
		}
		const [c, h, w] = shape.slice(-3);
		return { w: clamp(log(w) * 12, 14, 80), h: clamp(log(h) * 14, 18, 110), d: clamp(log(c) * 7, 8, 64) };
	}

	function clamp(v: number, lo: number, hi: number) {
		return Math.min(hi, Math.max(lo, v));
	}

	interface Placed {
		key: string;
		kind: 'input' | 'stage' | 'output';
		label: string;
		sub: string;
		shape: number[] | null;
		box: Box;
		x: number;
		stage?: Stage;
	}

	const placed = $derived.by(() => {
		const items: Omit<Placed, 'x'>[] = [
			...inputs.map((t, i) => ({
				key: `in-${i}`, kind: 'input' as const, label: t.name, sub: 'input', shape: t.shape, box: boxFor(t.shape)
			})),
			...stages.map((s) => ({
				key: s.key, kind: 'stage' as const, label: s.label, sub: s.type, shape: s.shape, box: boxFor(s.shape), stage: s
			})),
			...outputs.map((t, i) => ({
				key: `out-${i}`, kind: 'output' as const, label: t.name, sub: 'output', shape: t.shape, box: boxFor(t.shape)
			}))
		];
		// Each block takes the room its box or its widest label needs
		// (~6.5 px a character at these sizes), so long names don't collide.
		const labelWidth = (item: Omit<Placed, 'x'>) =>
			Math.max(item.label.length, item.sub.length, formatShape(item.shape).length) * 6.5;
		let x = 16;
		return items.map((item) => {
			const room = Math.max(item.box.w + item.box.d * 0.8, labelWidth(item));
			const p = { ...item, x: x + (room - item.box.w - item.box.d * 0.8) / 2 };
			x += room + GAP;
			return p;
		});
	});
	const width = $derived(placed.length ? placed[placed.length - 1].x + 60 : 400);
	const baseline = H - 40;

	function faces(p: Placed) {
		const { w, h, d } = p.box;
		const x = p.x;
		const y = baseline - h;
		const dx = d * 0.8;
		const dy = d * 0.6;
		return {
			front: `${x},${y} ${x + w},${y} ${x + w},${baseline} ${x},${baseline}`,
			top: `${x},${y} ${x + dx},${y - dy} ${x + w + dx},${y - dy} ${x + w},${y}`,
			side: `${x + w},${y} ${x + w + dx},${y - dy} ${x + w + dx},${baseline - dy} ${x + w},${baseline}`,
			cx: x + (w + dx) / 2,
			right: x + w + dx,
			midY: baseline - h / 2
		};
	}

	const params = $derived(
		Object.entries(arch.arch_params).filter(([k]) => k !== 'lead_hours')
	);
	const g = $derived(god(arch.model));
</script>

{#snippet block(p: Placed, f: ReturnType<typeof faces>, active: boolean)}
	<polygon points={f.side} fill={color} fill-opacity={active ? 0.35 : 0.14} class="stroke-border-strong" />
	<polygon points={f.top} fill={color} fill-opacity={active ? 0.45 : 0.2} class="stroke-border-strong" />
	<polygon
		points={f.front}
		fill={p.kind === 'stage' ? color : 'transparent'}
		fill-opacity={active ? 0.3 : 0.08}
		stroke={p.kind === 'stage' ? color : 'var(--color-text-faint)'}
		stroke-dasharray={p.kind === 'stage' ? undefined : '4 3'}
		stroke-width={active ? 2 : 1.2}
	/>
	{#if p.stage && p.stage.repeat > 1}
		<text x={f.cx} y={baseline - p.box.h - p.box.d * 0.6 - 8} text-anchor="middle" class="fill-text-muted font-data text-[10px]">×{p.stage.repeat}</text>
	{/if}
	<text x={f.cx} y={baseline + 16} text-anchor="middle" class="fill-text font-data text-[11px]">{formatShape(p.shape)}</text>
	<text x={f.cx} y={baseline + 30} text-anchor="middle" class="fill-text-muted text-[11px]">{p.label}</text>
	<text x={f.cx} y={baseline + 43} text-anchor="middle" class="fill-text-faint text-[10px]">{p.sub}</text>
{/snippet}

<section class={`rounded-lg border border-border bg-surface p-4 ${className}`}>
	<header class="mb-3 flex flex-wrap items-baseline gap-x-3 gap-y-1">
		<span class="h-3 w-3 self-center rounded-full" style={`background: ${color}`}></span>
		<h2 class="font-display text-lg font-semibold text-text">
			{g?.name ?? arch.model}
			<span class="font-data text-sm font-normal text-text-muted">{arch.model}</span>
		</h2>
		<span class="font-data text-xs text-text-faint">
			{arch.version !== null ? `v${arch.version} · ${arch.stage}` : 'no registered version'}
			· {formatParams(arch.total_params)} parameters
			· {arch.lead_hours.length} leads × 3 out
		</span>
		{#if onclose}
			<button
				type="button"
				onclick={onclose}
				aria-label="Close"
				class="ml-auto rounded px-2 py-0.5 text-text-faint hover:bg-surface-raised hover:text-text"
			>✕</button>
		{/if}
	</header>

	{#if arch.defaults}
		<p class="mb-3 rounded border border-lips/30 bg-lips/5 px-3 py-2 text-xs text-lips">
			{arch.version !== null
				? `v${arch.version} was registered before versions recorded how they were built, so this is the builder's defaults, not necessarily that version.`
				: 'No registered version: this is the builder’s defaults.'}
		</p>
	{/if}

	<div class="grid gap-x-6 gap-y-4 lg:grid-cols-[minmax(0,auto)_22rem]">
		<div class="min-w-0">
			<div class="overflow-x-auto">
				<svg
					viewBox={`0 0 ${width} ${H + 56}`}
					class="block h-auto"
					style={`width: ${width}px; max-width: 100%; min-width: ${Math.round(width * 0.7)}px`}
					role="group"
					aria-label={`${arch.model} layers`}
				>
					{#each placed as p, i (p.key)}
						{@const f = faces(p)}
						{@const active = p.key === selected || p.key === hovered}
						{#if i < placed.length - 1}
							<line
								x1={f.right + 4} y1={baseline - 20} x2={placed[i + 1].x - 6} y2={baseline - 20}
								class="stroke-text-faint" stroke-width="1.2" marker-end="url(#arrow)"
							/>
						{/if}
						{#if p.kind === 'stage'}
							<g
								role="button"
								tabindex="0"
								aria-pressed={selected === p.key}
								aria-label={`${p.label}, ${p.sub}, output ${formatShape(p.shape)}`}
								class="cursor-pointer outline-none"
								onmouseenter={() => (hovered = p.key)}
								onfocus={() => (hovered = p.key)}
								onclick={() => (selected = selected === p.key ? null : p.key)}
								onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (selected = selected === p.key ? null : p.key)}
							>
								{@render block(p, f, active)}
							</g>
						{:else}
							<g aria-hidden="true">{@render block(p, f, active)}</g>
						{/if}
					{/each}
					<defs>
						<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
							<path d="M 0 0 L 10 5 L 0 10 z" class="fill-text-faint" />
						</marker>
					</defs>
				</svg>
			</div>

		</div>
		<!-- As tall as the drawing at most; a big block's module list scrolls
		     here instead of stretching the popover past the screen. -->
		<div class="min-w-0 overflow-auto lg:max-h-[19rem] lg:border-l lg:border-border lg:pl-6">
			<!-- Stays put while the module list scrolls under it. -->
			<div class="sticky top-0 left-0 z-10 bg-surface pb-2">
				<div class="flex items-baseline gap-2">
					<h3 class="text-xs font-semibold tracking-wide text-text-muted uppercase">
						{focus ? `${focus.label} · ${focus.type}` : 'Built with'}
					</h3>
					{#if focus}
						<button type="button" onclick={showBuiltWith} class="ml-auto text-xs whitespace-nowrap text-action hover:text-action-strong">
							Built with
						</button>
					{/if}
				</div>
				{#if focus}
					<p class="mt-2 font-data text-xs text-text-faint">
						out {formatShape(focus.shape)} · {formatParams(focus.params)} params
					</p>
				{/if}
			</div>
			{#if focus}
				{#if focus.children.length}
					<table class="w-full font-data text-xs whitespace-nowrap">
						<tbody>
							{#each focus.children as c (c.path)}
								<tr class="border-t border-border">
									<td class="py-1 pr-2 text-text-muted" style={`padding-left: ${(c.depth - focusTop) * 12}px`} title={c.path}>{relative(c.path)}</td>
									<td class="py-1 pr-2 text-text">{c.type}</td>
									<td class="py-1 pr-2 text-text-muted">{formatShape(displayShape(c.output_shape, arch.batched))}</td>
									<td class="py-1 text-right text-text-faint">{c.own_params ? formatParams(c.own_params) : ''}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<p class="text-xs text-text-faint">A single {focus.type}, no submodules.</p>
				{/if}
			{:else}
				<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 font-data text-xs">
					{#each params as [k, v] (k)}
						<dt class="text-text-muted">{k}</dt>
						<dd class="text-text">{Array.isArray(v) ? v.join(' × ') : String(v)}</dd>
					{/each}
					<dt class="text-text-muted">lead_hours</dt>
					<dd class="text-text">{arch.lead_hours.join(', ')}</dd>
				</dl>
				<p class="mt-2 text-xs text-text-faint">Hover or click a block for what's inside it.</p>
			{/if}
		</div>
	</div>
	<!-- contain: inline-size -- this text wraps to the width the drawing sets
	     rather than widening the popover to its own one-line length. -->
	<div class="mt-4 border-t border-border pt-3 text-xs text-text-muted [contain:inline-size]">
			<h3 class="mb-2 text-xs font-semibold tracking-wide uppercase">How this is drawn</h3>
			<p>
				The API builds this exact version from the parameters it was registered with, runs one input of
				the shape training feeds it, and records each module's output. Box sizes follow those shapes on a
				log scale; the batch dimension is left out. Weights aren't loaded: shapes and parameter counts don't
				depend on them.
			</p>
	</div>
</section>
