<script lang="ts">
	import { onMount } from 'svelte';
	import { getActivePin, getArchitecture, getSources, listRegistry } from '$lib/api/endpoints';
	import { errorDetail, notifyError } from '$lib/notify';
	import type { ActivePin, ArchitectureOut, RegistryEntry, SourceOut } from '$lib/api/types';
	import SystemGraph from '$lib/components/anemoi/system/SystemGraph.svelte';
	import ArchitectureView from '$lib/components/anemoi/system/ArchitectureView.svelte';
	import { formatParams } from '$lib/components/anemoi/system/shapes';
	import * as Popover from '$lib/components/ui/popover';
	import { MediaQuery } from 'svelte/reactivity';

	const MODELS = ['lstm', 'cnn', 'transformer', 'gnn', 'pinn', 'fusion', 'diffusion'];

	let registry = $state<RegistryEntry[]>([]);
	let pin = $state<ActivePin | null>(null);
	let architectures = $state<Record<string, ArchitectureOut | undefined>>({});
	let failed = $state<Record<string, string>>({});
	let sources = $state<SourceOut[] | null>(null);
	let sourcesFailed = $state(false);
	let loading = $state(true);
	let selected = $state<string | null>(null);
	let anchor = $state<SVGGElement | null>(null);

	// Large screens: the layers open in a popover laid over the system graph,
	// the page itself never scrolls for it. Smaller ones: below the graph.
	const large = new MediaQuery('min-width: 1024px');
	let popoverOpen = $state(false);
	$effect(() => {
		if (large.current && selected && anchor) popoverOpen = true;
	});
	function closePopover() {
		popoverOpen = false;
		selected = null; // the beams come back for the whole system
	}
	// The popover's top edge: the graph card's top, or just under the sticky
	// site header when the card's top has scrolled out of view, centred on the
	// card. Its width follows its contents (the model's drawing and Built
	// with), up to the screen's; its height is capped to the screen and it
	// scrolls inside itself. contextElement makes floating-ui re-measure this
	// virtual anchor on scroll and resize.
	const HEADER_PX = 72;
	let graphEl = $state<HTMLDivElement | null>(null);
	const measurable = $derived(
		anchor && graphEl
			? {
					contextElement: graphEl,
					getBoundingClientRect: () => {
						const graph = graphEl!.getBoundingClientRect();
						return new DOMRect(graph.x, Math.max(graph.top, HEADER_PX), graph.width, 0);
					}
				}
			: null
	);

	async function load() {
		failed = {};
		loading = true;
		try {
			[registry, pin] = await Promise.all([listRegistry(), getActivePin()]);
		} catch (e) {
			notifyError('Could not read the registry', e, load);
		}
		// Each is built on the API from the version's own parameters; one
		// failing (or a version that can't be built) doesn't hide the rest.
		await Promise.all(
			MODELS.map(async (m) => {
				try {
					architectures[m] = await getArchitecture(m);
				} catch (e) {
					failed[m] = errorDetail(e);
				}
			})
		);
		loading = false;
		// One toast for every model that couldn't be described, not one each.
		const names = Object.keys(failed);
		if (names.length) {
			notifyError(
				`Could not describe ${names.length === 1 ? names[0] : `${names.length} models`}`,
				new Error(names.map((n) => `${n}: ${failed[n]}`).join('; ')),
				load
			);
		}
	}

	// The graph's left column: every registered source and which models read
	// it (`used_by`). Its own request with its own retry, like the registry
	// and each model above: the rest of the graph is drawn without it, with
	// one stand-in node where the sources go.
	async function loadSources() {
		sourcesFailed = false;
		try {
			sources = await getSources();
		} catch (e) {
			sourcesFailed = true;
			notifyError('Could not load the data sources', e, loadSources);
		}
	}

	onMount(() => {
		load();
		loadSources();
	});

	const total = $derived(
		Object.values(architectures).reduce((sum, a) => sum + (a?.total_params ?? 0), 0)
	);
	const current = $derived(selected ? architectures[selected] : undefined);
</script>

<div class="mx-auto max-w-6xl px-6 py-8">
	<header class="mb-6">
		<h1 class="font-display text-2xl font-semibold text-text">Architecture</h1>
		<p class="mt-1 max-w-3xl text-sm text-text-muted">
			The system as it is serving now: each model node is the version the active pin serves, read from the
			registry, and each model's layers are built from that version's own parameters. The <a href="/docs/Home#system-at-a-glance" class="text-action hover:text-action-strong">overview diagram</a>
			in the docs is the plain version.
		</p>
		{#if total}
			<p class="mt-2 font-data text-xs text-text-faint">
				{pin ? `pin ${pin.label} · ` : ''}{formatParams(total)} parameters across {Object.keys(architectures).length} models
			</p>
		{/if}
	</header>

	<div bind:this={graphEl} class="mb-6 rounded-lg border border-border bg-bg p-3">
		<SystemGraph {registry} {pin} {architectures} {sources} {sourcesFailed} bind:selected bind:anchor />
		<p class="mt-2 px-1 text-xs text-text-faint">
			Select a model to open its layers; the beams show where data flows in a forecast cycle, and selecting a model
			mutes every path it isn't on. Basins: <span class="text-clear">✓ verified</span> (beats persistence there) ·
			<span class="text-lips">trained</span> · not trained. Edge labels are the shapes each model is fed and
			returns, batch left out.
		</p>
	</div>

	{#if large.current}
		<Popover.Root
			bind:open={popoverOpen}
			onOpenChange={(open) => {
				if (!open) selected = null;
			}}
		>
			<Popover.Content
				customAnchor={measurable}
				side="bottom"
				sideOffset={0}
				collisionPadding={16}
				avoidCollisions={false}
				class="max-h-[calc(100vh-5.5rem)] w-fit max-w-[calc(100vw-4rem)] overflow-y-auto bg-transparent p-0 shadow-2xl ring-0"
			>
				<div>
					{#if selected && current}
						<ArchitectureView arch={current} onclose={closePopover} />
					{:else if selected && failed[selected]}
						<div class="rounded-md border border-border bg-surface px-4 py-3 text-sm text-text-faint">
							{selected} couldn\'t be described right now.
						</div>
					{:else if selected}
						<div class="rounded-md border border-border bg-surface px-4 py-3 text-sm text-text-faint">
							Building {selected}…
						</div>
					{/if}
				</div>
			</Popover.Content>
		</Popover.Root>
	{:else if selected && current}
		<ArchitectureView arch={current} />
	{:else if selected && failed[selected]}
		<p class="text-sm text-text-faint">
			{selected} couldn\'t be described right now.
		</p>
	{:else if loading}
		<p class="text-sm text-text-faint">Building the served models…</p>
	{/if}
</div>
