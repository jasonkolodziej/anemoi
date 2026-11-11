<script lang="ts">
	/**
	 * The cookie banner: shown on a visitor's first page, and again from
	 * "Cookie settings" in the site footer (`site-footer.svelte`) or the
	 * mobile menu (`mobile-sidebar.svelte`). Until they choose, nothing
	 * optional is stored or loaded (`$lib/consent.svelte`).
	 *
	 * "Accept all" and "Necessary only" are the same size, side by side, so
	 * refusing is as easy as agreeing. "Choose" opens a toggle per category.
	 *
	 * Fixed to the bottom of the viewport on every form factor, above the
	 * page's own overlays (the full-page waiter included). On a short
	 * screen (a phone held sideways, with the categories open) the text
	 * scrolls inside the banner and the buttons stay in view. Drawn only after mount: the server can't know the choice,
	 * so rendering it there would flash the banner for visitors who
	 * already chose.
	 */
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import { consent } from '$lib/consent.svelte';

	let mounted = $state(false);
	onMount(() => (mounted = true));

	const visible = $derived(mounted && (consent.choice === null || consent.settingsOpen));

	let choosing = $state(false);
	let picked = $state({ preferences: false, analytics: false });

	// Reopened from settings: start from what was chosen, with the toggles out.
	$effect(() => {
		if (consent.settingsOpen) {
			picked = {
				preferences: consent.allows('preferences'),
				analytics: consent.allows('analytics'),
			};
			choosing = true;
		}
	});

	function save() {
		consent.decide(picked);
		choosing = false;
	}

	const categories = [
		{
			id: 'preferences',
			title: 'Preferences',
			body: 'Remembers the storms and forecasts you last viewed, in this browser only, so pages draw at once on your next visit.',
		},
		{
			id: 'analytics',
			title: 'Analytics',
			body: "Cloudflare Web Analytics counts page views and load times. It sets no cookies and doesn't follow you to other sites, but it loads Cloudflare's script from static.cloudflareinsights.com.",
		},
	] as const;
</script>

{#if visible}
	<div
		role="dialog"
		aria-modal="false"
		aria-labelledby="cookie-banner-title"
		aria-describedby="cookie-banner-body"
		data-testid="cookie-banner"
		class="pointer-events-none fixed inset-x-0 bottom-0 z-[60] flex justify-center px-4 pb-[max(1rem,env(safe-area-inset-bottom))]"
	>
		<div
			class="pointer-events-auto flex max-h-[calc(100dvh-2rem)] w-full max-w-2xl flex-col rounded-lg border border-border-strong bg-surface shadow-2xl"
		>
			<div class="min-h-0 overflow-y-auto px-4 pt-4 sm:px-5 sm:pt-5">
				<h2 id="cookie-banner-title" class="text-sm font-semibold text-text">
					Cookies and storage
				</h2>
				<p id="cookie-banner-body" class="mt-1.5 text-xs leading-relaxed text-text-muted">
					Anemoi stores only what it needs to work unless you allow more. Signing in sets a
					session cookie, and your choice here is kept in this browser. Nothing else is stored
					or loaded until you choose.
				</p>

				{#if choosing}
					<ul class="mt-3 space-y-2" data-testid="cookie-categories">
						<li class="flex items-start gap-3 rounded-md border border-border p-3">
							<input
								id="consent-necessary"
								type="checkbox"
								checked
								disabled
								class="mt-0.5 size-4 shrink-0 accent-action"
							/>
							<label for="consent-necessary" class="text-xs">
								<span class="font-medium text-text">Necessary</span>
								<span class="text-text-faint"> · always on</span>
								<span class="mt-0.5 block text-text-muted">
									Your sign-in session cookie, once you sign in, and this choice.
								</span>
							</label>
						</li>
						{#each categories as category (category.id)}
							<li class="flex items-start gap-3 rounded-md border border-border p-3">
								<input
									id="consent-{category.id}"
									type="checkbox"
									bind:checked={picked[category.id]}
									class="mt-0.5 size-4 shrink-0 accent-action"
								/>
								<label for="consent-{category.id}" class="text-xs">
									<span class="font-medium text-text">{category.title}</span>
									<span class="mt-0.5 block text-text-muted">{category.body}</span>
								</label>
							</li>
						{/each}
					</ul>
				{/if}
			</div>

			<div
				class="flex shrink-0 flex-col gap-2 p-4 pt-3 sm:flex-row sm:flex-wrap sm:justify-end sm:p-5 sm:pt-4"
			>
				{#if choosing}
					<Button class="sm:min-w-32" onclick={save}>Save choices</Button>
				{:else}
					<Button variant="outline" class="sm:mr-auto" onclick={() => (choosing = true)}>
						Choose…
					</Button>
				{/if}
				<Button class="sm:min-w-32" onclick={() => consent.necessaryOnly()}>Necessary only</Button>
				<Button class="sm:min-w-32" onclick={() => consent.acceptAll()}>Accept all</Button>
			</div>
		</div>
	</div>
{/if}
