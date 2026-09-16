<script lang="ts">
	import { onMount } from 'svelte';
	import { getModels } from '$lib/api/endpoints';
	import { ApiError } from '$lib/api/client';
	import { GODS as STATIC_GODS, FUSION_COLOR } from '$lib/branding';
	import type { ModelCatalog } from '$lib/api/types';
	import { Card, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';

	let catalog = $state<ModelCatalog | null>(null);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			catalog = await getModels();
		} catch (e) {
			error = e instanceof ApiError ? `${e.status}: ${e.message}` : String(e);
		}
	});

	const gods = $derived(catalog?.gods ?? STATIC_GODS);
</script>

<div class="mx-auto max-w-5xl px-6 py-8">
	<header class="mb-6">
		<h1 class="font-display text-2xl font-semibold text-text">The Anemoi</h1>
		<p class="mt-1 text-sm text-text-muted">
			Six architectures, personified. The god name is the identifier everywhere except the module itself.
		</p>
	</header>

	{#if error}
		<div class="mb-6 rounded-md border border-eurus/30 bg-eurus/5 px-4 py-3 text-sm text-eurus">
			Could not reach Anemoi-API ({error}) — showing the static branding fallback.
		</div>
	{/if}

	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
		{#each gods as god (god.slug)}
			<Card>
				<CardContent class="pt-4">
					<div class="mb-3 flex items-center gap-3">
						<span class="h-3 w-3 rounded-full" style={`background: ${god.color}`}></span>
						<h2 class="font-display text-lg font-semibold text-text">{god.name}</h2>
						<Badge variant="outline">{god.direction}</Badge>
					</div>
					<p class="text-sm text-text-muted">{god.persona}</p>
					<div class="mt-3 flex items-center gap-4 text-xs text-text-faint">
						<span class="font-data">{god.architecture}</span>
						<span>·</span>
						<span>{god.module}</span>
					</div>
				</CardContent>
			</Card>
		{/each}
		<Card>
			<CardContent class="pt-4">
				<div class="mb-3 flex items-center gap-3">
					<span class="h-3 w-3 rounded-full border border-border-strong" style={`background: ${catalog?.fusion_color ?? FUSION_COLOR}`}></span>
					<h2 class="font-display text-lg font-semibold text-text">Fusion</h2>
					<Badge variant="outline">consensus</Badge>
				</div>
				<p class="text-sm text-text-muted">
					Not a god — the consensus of all six, weighted by rolling validation skill. Takes the neutral Eye colour rather than a direction.
				</p>
			</CardContent>
		</Card>
	</div>
</div>
