<script lang="ts">
	import { onMount } from 'svelte';
	import { getSources } from '$lib/api/endpoints';
	import { errorDetail, notifyError } from '$lib/notify';
	import type { SourceOut } from '$lib/api/types';
	import { usedByText } from '$lib/components/anemoi/system/source-use';
	import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '$lib/components/ui/table';
	import { Badge } from '$lib/components/ui/badge';

	let sources = $state<SourceOut[] | null>(null);
	let error = $state<string | null>(null);

	async function load() {
		error = null;
		try {
			sources = await getSources();
		} catch (e) {
			error = errorDetail(e);
			notifyError('Could not load the data sources', e, load);
		}
	}

	onMount(load);

	// An API from before `used_by` leaves it out of every row. Each cell then
	// shows a dash; this says why, once, where a sighted reader sees it.
	const unreported = $derived(sources?.some((s) => !s.used_by) ?? false);

	function fmtMinutes(m: number): string {
		return m >= 60 ? `${(m / 60).toFixed(1)}h` : `${m.toFixed(0)}m`;
	}
</script>

{#snippet role(s: SourceOut)}
	<Badge variant={s.is_operational ? 'outline' : 'default'}>{s.role}</Badge>
{/snippet}

{#snippet usedBy(s: SourceOut)}
	{#if s.used_by}
		<span class={s.used_by.length ? 'text-text' : 'text-text-muted'}>{usedByText(s.used_by)}</span>
	{:else}
		<!-- An API from before `used_by` doesn't send it. That is unknown,
		     and must not read as "not used yet". -->
		<span aria-hidden="true" class="text-text-faint">{usedByText(s.used_by)}</span>
		<span class="sr-only">not reported by this API</span>
	{/if}
{/snippet}

<div class="mx-auto max-w-6xl px-6 py-8">
	<header class="mb-6">
		<h1 class="font-display text-2xl font-semibold text-text">Data sources</h1>
		<p class="mt-1 max-w-3xl text-sm text-text-muted">
			§4.1 registry. <span class="text-text">Role</span> is what a source may be used for: only
			<Badge variant="outline">operational</Badge> sources may be read during a forecast cycle, whether or not
			anything reads them yet. <span class="text-text">Used by</span> is who uses each source today.
		</p>
	</header>

	{#if error}
		<p class="text-sm text-text-faint">The data sources aren't available right now.</p>
	{:else if sources === null}
		<p class="text-sm text-text-faint">Loading…</p>
	{:else}
		{#if unreported}
			<p class="mb-4 text-sm text-text-muted">This API doesn't say what uses each source, so Used by shows a dash.</p>
		{/if}
		<!-- Narrower than the table: one block per source. Seven columns
		     don't fit a phone, and a table scrolled sideways shows a
		     source's key or what uses it, not both. -->
		<ul class="divide-y divide-border border-y border-border lg:hidden">
			{#each sources as s (s.key)}
				<li class="py-3">
					<h2 class="font-data text-sm text-text">{s.key}</h2>
					<dl class="mt-2 grid grid-cols-[auto_1fr] items-baseline gap-x-4 gap-y-1.5 text-sm">
						<dt class="text-text-faint">Role</dt>
						<dd>{@render role(s)}</dd>
						<dt class="text-text-faint">Used by</dt>
						<dd>{@render usedBy(s)}</dd>
						<dt class="text-text-faint">Provider</dt>
						<dd class="text-text-muted">{s.provider}</dd>
						<dt class="text-text-faint">Latency</dt>
						<dd class="font-data text-text-muted">
							{fmtMinutes(s.typical_latency_minutes)} typical · {fmtMinutes(s.max_latency_minutes)} max
						</dd>
						<dt class="text-text-faint">Format</dt>
						<dd class="text-text-muted">{s.fmt}</dd>
					</dl>
				</li>
			{/each}
		</ul>

		<div class="hidden lg:block">
			<Table>
				<TableHeader>
					<TableRow>
						<TableHead>Source</TableHead>
						<TableHead>Provider</TableHead>
						<TableHead>Role</TableHead>
						<TableHead>Used by</TableHead>
						<TableHead class="whitespace-normal">Typical latency</TableHead>
						<TableHead class="whitespace-normal">Max latency</TableHead>
						<TableHead>Format</TableHead>
					</TableRow>
				</TableHeader>
				<TableBody>
					{#each sources as s (s.key)}
						<TableRow>
							<TableCell class="font-data">{s.key}</TableCell>
							<!-- Provider and format wrap, inside a word if they must
							     (`data.real_microwave)`), and so do the two latency
							     headings: on one line each they pushed the last
							     columns off the right edge. -->
							<TableCell class="min-w-44 whitespace-normal wrap-anywhere text-text-muted">{s.provider}</TableCell>
							<TableCell>{@render role(s)}</TableCell>
							<TableCell>{@render usedBy(s)}</TableCell>
							<TableCell class="font-data">{fmtMinutes(s.typical_latency_minutes)}</TableCell>
							<TableCell class="font-data">{fmtMinutes(s.max_latency_minutes)}</TableCell>
							<TableCell class="min-w-28 whitespace-normal wrap-anywhere text-text-faint">{s.fmt}</TableCell>
						</TableRow>
					{/each}
				</TableBody>
			</Table>
		</div>
	{/if}
</div>
