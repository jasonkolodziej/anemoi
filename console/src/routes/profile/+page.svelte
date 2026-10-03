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

	type PasskeySummary = {
		id: string;
		name: string | null;
		createdAt: string | Date;
		deviceType: string;
	};

	let keys = $state<ApiKeySummary[]>([]);
	let loadingKeys = $state(true);
	let creating = $state(false);
	let revealedKey = $state<string | null>(null);
	let errorMsg = $state("");

	let passkeys = $state<PasskeySummary[]>([]);
	let loadingPasskeys = $state(true);
	let addingPasskey = $state(false);
	let passkeyErrorMsg = $state("");

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

	// @better-auth/passkey's `addPasskey`/`listUserPasskeys` are typed on
	// `authClient.passkey.*`, but `deletePasskey`/`updatePasskey` aren't
	// (confirmed against the installed package's own client.d.mts, despite
	// its server-side doc comments claiming otherwise) -- called through
	// the generic `authClient.$fetch` escape hatch instead, against the
	// real server endpoint paths/body shapes (node_modules/@better-auth/
	// passkey/dist/index.mjs).
	async function loadPasskeys() {
		loadingPasskeys = true;
		try {
			const { data: list, error } = await authClient.$fetch<PasskeySummary[]>(
				"/passkey/list-user-passkeys",
				{ method: "GET" },
			);
			if (error) {
				passkeyErrorMsg = error.message ?? "Failed to load passkeys";
				return;
			}
			passkeys = list ?? [];
		} finally {
			loadingPasskeys = false;
		}
	}

	async function addPasskey() {
		addingPasskey = true;
		passkeyErrorMsg = "";
		try {
			const { error } = await authClient.passkey.addPasskey({
				name: `${navigator.platform || "device"}-${new Date().toISOString().slice(0, 10)}`,
			});
			if (error) {
				passkeyErrorMsg = error.message ?? "Failed to add passkey";
				return;
			}
			await loadPasskeys();
		} catch (err) {
			// A cancelled WebAuthn ceremony (user dismissed the browser
			// prompt) throws rather than returning `error` -- not a real
			// failure worth surfacing as one.
			if (!(err instanceof Error && err.name === "NotAllowedError")) {
				passkeyErrorMsg = err instanceof Error ? err.message : "Failed to add passkey";
			}
		} finally {
			addingPasskey = false;
		}
	}

	async function removePasskey(id: string) {
		const { error } = await authClient.$fetch("/passkey/delete-passkey", {
			method: "POST",
			body: { id },
		});
		if (error) {
			passkeyErrorMsg = error.message ?? "Failed to remove passkey";
			return;
		}
		await loadPasskeys();
	}

	async function signOut() {
		await fetch("/auth/logout", { method: "POST" });
		// See login/+page.svelte's handlePasskeyLogin -- the root layout's
		// user data doesn't refresh on its own after an in-app auth change.
		await goto("/", { invalidateAll: true });
	}

	loadKeys();
	loadPasskeys();
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

	<Card>
		<CardHeader>
			<CardTitle>Passkeys</CardTitle>
			<CardDescription>
				Sign in with your device's screen lock or security key instead of
				your current sign-in method. Add one as a backup so losing access
				to that method doesn't lock you out.
			</CardDescription>
		</CardHeader>
		<CardContent class="flex flex-col gap-4">
			{#if passkeyErrorMsg}
				<p class="text-destructive text-sm">{passkeyErrorMsg}</p>
			{/if}

			{#if loadingPasskeys}
				<p class="text-muted-foreground text-sm">Loading…</p>
			{:else if passkeys.length === 0}
				<p class="text-muted-foreground text-sm">No passkeys yet.</p>
			{:else}
				<ul class="flex flex-col gap-2">
					{#each passkeys as passkey (passkey.id)}
						<li class="flex items-center justify-between gap-2 text-sm">
							<span>
								{passkey.name ?? "Untitled"}
								<span class="text-muted-foreground">
									({passkey.deviceType})
								</span>
							</span>
							<Button
								variant="ghost"
								size="sm"
								onclick={() => removePasskey(passkey.id)}
							>
								Remove
							</Button>
						</li>
					{/each}
				</ul>
			{/if}
		</CardContent>
		<CardFooter>
			<Button onclick={addPasskey} disabled={addingPasskey}>
				{addingPasskey ? "Follow your browser's prompt…" : "Add a passkey"}
			</Button>
		</CardFooter>
	</Card>
</div>
