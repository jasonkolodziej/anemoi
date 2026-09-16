<script lang="ts">
	import { onMount } from 'svelte';
	import { listRegistry, getActivePin } from '$lib/api/endpoints';
	import { ApiError } from '$lib/api/client';
	import type { RegistryEntry, ActivePin } from '$lib/api/types';
	import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '$lib/components/ui/table';
	import { Badge } from '$lib/components/ui/badge';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { colorFor } from '$lib/branding';
	import { formatUtc } from '$lib/utils';

	let entries = $state<RegistryEntry[] | null>(null);
	let pin = $state<ActivePin | null>(null);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			[entries, pin] = await Promise.all([listRegistry(), getActivePin()]);
		} catch (e) {
			error = e instanceof ApiError ? `${e.status}: ${e.message}` : String(e);
		}
	});
</script>

<div class="mx-auto max-w-5xl px-6 py-8">
	<header class="mb-6">
		<h1 class="font-display text-2xl font-semibold text-text">Model registry</h1>
		<p class="mt-1 text-sm text-text-muted">Versions, stages, and the active model-set pin (§5.7).</p>
	</header>

	{#if error}
		<div class="rounded-md border border-eurus/30 bg-eurus/5 px-4 py-3 text-sm text-eurus">{error}</div>
	{:else}
		{#if pin}
			<Card class="mb-6">
				<CardHeader><CardTitle>Active pin — {pin.label}</CardTitle></CardHeader>
				<CardContent>
					<p class="mb-3 font-data text-xs text-text-faint">latent signature: {pin.latent_signature}</p>
					<div class="flex flex-wrap gap-2">
						{#each Object.entries(pin.members) as [model, version] (model)}
							<Badge variant="outline">
								<span class="h-1.5 w-1.5 rounded-full" style={`background: ${colorFor(model)}`}></span>
								{model} v{version}
							</Badge>
						{/each}
					</div>
				</CardContent>
			</Card>
		{/if}

		{#if entries === null}
			<p class="text-sm text-text-faint">Loading…</p>
		{:else}
			<Table>
				<TableHeader>
					<TableRow>
						<TableHead>Model</TableHead>
						<TableHead>Latest</TableHead>
						<TableHead>Production</TableHead>
						<TableHead>Metrics</TableHead>
						<TableHead>Registered</TableHead>
					</TableRow>
				</TableHeader>
				<TableBody>
					{#each entries as e (e.model)}
						<TableRow>
							<TableCell>
								<span class="flex items-center gap-2">
									<span class="h-2 w-2 rounded-full" style={`background: ${colorFor(e.model)}`}></span>
									<span class="font-data">{e.model}</span>
								</span>
							</TableCell>
							<TableCell class="font-data">v{e.latest?.version ?? '—'}</TableCell>
							<TableCell>
								{#if e.production}
									<Badge variant="outline">v{e.production.version} production</Badge>
								{:else}
									<span class="text-text-faint">not promoted</span>
								{/if}
							</TableCell>
							<TableCell class="font-data text-xs text-text-muted">
								{#if e.latest}
									{Object.entries(e.latest.metrics).map(([k, v]) => `${k}=${v.toFixed(2)}`).join(', ')}
								{/if}
							</TableCell>
							<TableCell class="font-data text-xs text-text-faint">
								{e.latest ? formatUtc(e.latest.created_at) : '—'}
							</TableCell>
						</TableRow>
					{/each}
				</TableBody>
			</Table>
		{/if}
	{/if}
</div>
