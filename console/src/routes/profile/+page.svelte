<script lang="ts">
	import { goto } from "$app/navigation";
	import { authClient } from "$lib/auth-client";
	import { Button } from "$lib/components/ui/button";
	import {
		Card,
		CardContent,
		CardDescription,
		CardFooter,
		CardHeader,
		CardTitle,
	} from "$lib/components/ui/card";
	import { Separator } from "$lib/components/ui/separator";
	import type { PageData } from "./$types";

	let { data }: { data: PageData } = $props();

	type ApiKeySummary = {
		id: string;
		name: string | null;
		start: string | null;
		createdAt: string | Date;
	};

	let keys = $state<ApiKeySummary[]>([]);
	let loadingKeys = $state(true);
	let creating = $state(false);
	let revealedKey = $state<string | null>(null);
	let errorMsg = $state("");

	// Call anemoi-api-real with this key to run forecast cycles and read
	// storm data -- see docs/api.md ("Authentication and versioning").
	async function loadKeys() {
		loadingKeys = true;
		try {
			const { data: list, error } = await authClient.apiKey.list();
			if (error) {
				errorMsg = error.message ?? "Failed to load API keys";
				return;
			}
			keys = (list?.apiKeys ?? []) as ApiKeySummary[];
		} finally {
			loadingKeys = false;
		}
	}

	async function createKey() {
		creating = true;
		errorMsg = "";
		try {
			const { data: created, error } = await authClient.apiKey.create({
				name: `console-${new Date().toISOString().slice(0, 10)}`,
			});
			if (error) {
				errorMsg = error.message ?? "Failed to create API key";
				return;
			}
			// The full secret is only ever returned here, once.
			revealedKey = created?.key ?? null;
			await loadKeys();
		} finally {
			creating = false;
		}
	}

	async function deleteKey(id: string) {
		const { error } = await authClient.apiKey.delete({ keyId: id });
		if (error) {
			errorMsg = error.message ?? "Failed to delete API key";
			return;
		}
		await loadKeys();
	}

	async function signOut() {
		await fetch("/auth/logout", { method: "POST" });
		await goto("/");
	}

	loadKeys();
</script>

<div class="mx-auto flex max-w-lg flex-col gap-6 px-4 py-10">
	<Card>
		<CardHeader>
			<CardTitle>{data.user.name}</CardTitle>
			<CardDescription>{data.user.email}</CardDescription>
		</CardHeader>
		<CardFooter>
			<Button variant="outline" onclick={signOut}>Sign out</Button>
		</CardFooter>
	</Card>

	<Card>
		<CardHeader>
			<CardTitle>API keys</CardTitle>
			<CardDescription>
				Use an API key to call anemoi-api-real programmatically (the
				<code>X-Anemoi-Api-Key</code> header). Keys are shown in full only
				once, right after creation.
			</CardDescription>
		</CardHeader>
		<CardContent class="flex flex-col gap-4">
			{#if errorMsg}
				<p class="text-destructive text-sm">{errorMsg}</p>
			{/if}

			{#if revealedKey}
				<div class="bg-muted space-y-2 rounded-md border p-3">
					<p class="text-sm font-medium">Copy this key now -- it won't be shown again.</p>
					<code class="block text-xs break-all">{revealedKey}</code>
					<Button
						variant="link"
						class="h-auto p-0 text-xs"
						onclick={() => (revealedKey = null)}
					>
						Dismiss
					</Button>
				</div>
				<Separator />
			{/if}

			{#if loadingKeys}
				<p class="text-muted-foreground text-sm">Loading…</p>
			{:else if keys.length === 0}
				<p class="text-muted-foreground text-sm">No API keys yet.</p>
			{:else}
				<ul class="flex flex-col gap-2">
					{#each keys as key (key.id)}
						<li class="flex items-center justify-between gap-2 text-sm">
							<span>
								{key.name ?? "Untitled"}
								<span class="text-muted-foreground">
									({key.start ?? "…"}…)
								</span>
							</span>
							<Button
								variant="ghost"
								size="sm"
								onclick={() => deleteKey(key.id)}
							>
								Revoke
							</Button>
						</li>
					{/each}
				</ul>
			{/if}
		</CardContent>
		<CardFooter>
			<Button onclick={createKey} disabled={creating}>
				{creating ? "Generating…" : "Generate new key"}
			</Button>
		</CardFooter>
	</Card>
</div>
