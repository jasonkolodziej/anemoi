<script lang="ts">
	import { onMount } from 'svelte';
	import { getRetrainTriggers } from '$lib/api/endpoints';
	import { ApiError } from '$lib/api/client';
	import type { RetrainJobOut } from '$lib/api/types';
	import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '$lib/components/ui/table';
	import { Badge } from '$lib/components/ui/badge';
	import { colorFor } from '$lib/branding';

	let jobs = $state<RetrainJobOut[] | null>(null);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			jobs = await getRetrainTriggers();
		} catch (e) {
			error = e instanceof ApiError ? `${e.status}: ${e.message}` : String(e);
		}
	});
</script>

<div class="mx-auto max-w-5xl px-6 py-8">
	<header class="mb-6">
		<h1 class="font-display text-2xl font-semibold text-text">Retraining triggers</h1>
		<p class="mt-1 text-sm text-text-muted">
			What <span class="font-data">evaluate_all()</span> would schedule right now. Read-only — launching a run is an orchestration
			decision, not a synchronous request (see docs/api.md, "The one mutating route").
		</p>
	</header>

	{#if error}
		<div class="rounded-md border border-eurus/30 bg-eurus/5 px-4 py-3 text-sm text-eurus">{error}</div>
	{:else if jobs === null}
		<p class="text-sm text-text-faint">Loading…</p>
	{:else if jobs.length === 0}
		<p class="text-sm text-text-faint">No pending triggers — nothing drifted, skewed, or scheduled today.</p>
	{:else}
		<Table>
			<TableHeader>
				<TableRow>
					<TableHead>Model</TableHead>
					<TableHead>Reason</TableHead>
					<TableHead>Mode</TableHead>
					<TableHead>Cascaded</TableHead>
					<TableHead>Note</TableHead>
				</TableRow>
			</TableHeader>
			<TableBody>
				{#each jobs as job, i (job.model + i)}
					<TableRow>
						<TableCell>
							<span class="flex items-center gap-2">
								<span class="h-2 w-2 rounded-full" style={`background: ${colorFor(job.model)}`}></span>
								<span class="font-data">{job.model}</span>
							</span>
						</TableCell>
						<TableCell><Badge variant="outline">{job.reason}</Badge></TableCell>
						<TableCell class="font-data text-text-muted">{job.mode}</TableCell>
						<TableCell>{job.cascaded ? 'yes' : '—'}</TableCell>
						<TableCell class="text-xs text-text-faint">{job.note}</TableCell>
					</TableRow>
				{/each}
			</TableBody>
		</Table>
	{/if}
</div>
