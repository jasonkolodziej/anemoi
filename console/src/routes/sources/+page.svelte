<script lang="ts">
	import { onMount } from 'svelte';
	import { getSources } from '$lib/api/endpoints';
	import { ApiError } from '$lib/api/client';
	import type { SourceOut } from '$lib/api/types';
	import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '$lib/components/ui/table';
	import { Badge } from '$lib/components/ui/badge';

	let sources = $state<SourceOut[] | null>(null);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			sources = await getSources();
		} catch (e) {
			error = e instanceof ApiError ? `${e.status}: ${e.message}` : String(e);
		}
	});

	function fmtMinutes(m: number): string {
		return m >= 60 ? `${(m / 60).toFixed(1)}h` : `${m.toFixed(0)}m`;
	}
</script>

<div class="mx-auto max-w-5xl px-6 py-8">
	<header class="mb-6">
		<h1 class="font-display text-2xl font-semibold text-text">Data sources</h1>
		<p class="mt-1 text-sm text-text-muted">
			§4.1 registry. Only <Badge variant="outline">operational</Badge> sources may be read during a forecast cycle.
		</p>
	</header>

	{#if error}
		<div class="rounded-md border border-eurus/30 bg-eurus/5 px-4 py-3 text-sm text-eurus">{error}</div>
	{:else if sources === null}
		<p class="text-sm text-text-faint">Loading…</p>
	{:else}
		<Table>
			<TableHeader>
				<TableRow>
					<TableHead>Source</TableHead>
					<TableHead>Provider</TableHead>
					<TableHead>Role</TableHead>
					<TableHead>Typical latency</TableHead>
					<TableHead>Max latency</TableHead>
					<TableHead>Format</TableHead>
				</TableRow>
			</TableHeader>
			<TableBody>
				{#each sources as s (s.key)}
					<TableRow>
						<TableCell class="font-data">{s.key}</TableCell>
						<TableCell class="text-text-muted">{s.provider}</TableCell>
						<TableCell><Badge variant={s.is_operational ? 'outline' : 'default'}>{s.role}</Badge></TableCell>
						<TableCell class="font-data">{fmtMinutes(s.typical_latency_minutes)}</TableCell>
						<TableCell class="font-data">{fmtMinutes(s.max_latency_minutes)}</TableCell>
						<TableCell class="text-text-faint">{s.fmt}</TableCell>
					</TableRow>
				{/each}
			</TableBody>
		</Table>
	{/if}
</div>
