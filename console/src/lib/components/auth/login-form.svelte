<script lang="ts">
	/**
	 * The actual sign-in UI: passkey, magic-link (superForm-powered), and
	 * GitHub OAuth, plus the handlers and error/sent state behind them.
	 * Split out of routes/auth/login/+page.svelte so the page chrome
	 * around it (heading, card, split-screen, whatever) is swappable
	 * without duplicating any of this -- see login-01.svelte (the
	 * original centered layout) and login-02.svelte (a split-screen
	 * alternate), both of which just wrap this with different styling.
	 *
	 * `form` is the SuperValidated magic-link form from
	 * routes/auth/login/+page.server.ts's `load` -- passed in rather than
	 * fetched here because only a route's own `load` can produce it
	 * (server-validated, needs the request), and this component doesn't
	 * know which route is rendering it.
	 */
	import { KeyRound, Mail } from "@lucide/svelte";
	import { Github } from "$lib/components/icons";
	import Loader from "@lucide/svelte/icons/loader";
	import { superForm, type SuperValidated, type Infer } from "sveltekit-superforms";
	import { arktype } from "sveltekit-superforms/adapters";
	import { goto } from "$app/navigation";
	import { authClient } from "$lib/auth-client";
	import { Button } from "$lib/components/ui/button/index";
	import * as Form from "$lib/components/ui/form/index";
	import { Input } from "$lib/components/ui/input/index";
	import { Separator } from "$lib/components/ui/separator/index";
	import { loginSchema, type LoginSchema } from "./login-schema";

	interface Props {
		form: SuperValidated<Infer<LoginSchema>>;
	}
	let { form: formProp }: Props = $props();

	let loading = $state(false);
	let errorMsg = $state("");
	let magicLinkSent = $state(false);

	// svelte-ignore state_referenced_locally -- intentional: superForm takes
	// the initial form data once and owns its own reactive state (`form`/
	// `formData`) from then on; re-reading `formProp` here on every change
	// would fight that, not fix anything (the standard pattern for this
	// library under Svelte 5 runes mode).
	const form = superForm(formProp, {
		validators: arktype(loginSchema),
		SPA: true,
		onUpdate: async ({ form: f }) => {
			if (!f.valid) return;
			await handleMagicLink(f.data.email);
		},
	});

	const { form: formData, enhance, submitting } = form;

	// ── Passkey sign-in ─────────────────────────────────────────────────────
	async function handlePasskeyLogin() {
		loading = true;
		errorMsg = "";
		try {
			const { error } = await authClient.signIn.passkey();
			if (error) {
				console.error("[auth:passkey] sign-in error:", error);
				errorMsg = error.message ?? "Passkey authentication failed";
				return;
			}
			// `invalidateAll` forces the root layout's `+layout.server.ts` load
			// to rerun -- it depends on `locals.user`, which SvelteKit doesn't
			// track as a navigation dependency on its own, so the top nav would
			// otherwise keep showing "Sign in" after a passkey login until a
			// full page reload (magic link/OAuth redirect through the browser
			// instead, so they don't need this).
			await goto("/profile", { invalidateAll: true });
		} catch (err) {
			console.error("[auth:passkey] unexpected error:", err);
			errorMsg = err instanceof Error ? err.message : "An unexpected error occurred";
		} finally {
			loading = false;
		}
	}

	// ── Magic link sign-in ──────────────────────────────────────────────────
	async function handleMagicLink(email: string) {
		loading = true;
		errorMsg = "";
		try {
			const { error } = await authClient.signIn.magicLink({
				email: email.trim(),
				callbackURL: "/profile",
			});
			if (error) {
				console.error("[auth:magic-link] sign-in error:", error);
				errorMsg = error.message ?? "Failed to send magic link";
				return;
			}
			magicLinkSent = true;
		} catch (err) {
			console.error("[auth:magic-link] unexpected error:", err);
			errorMsg = err instanceof Error ? err.message : "An unexpected error occurred";
		} finally {
			loading = false;
		}
	}

	// ── OAuth sign-in ───────────────────────────────────────────────────────
	// "google" dropped from the type -- no OAuth app registered yet, see the
	// template below.
	async function handleOAuth(provider: "github") {
		loading = true;
		errorMsg = "";
		try {
			await authClient.signIn.social({
				provider,
				callbackURL: "/profile",
			});
		} catch (err) {
			console.error(`[auth:oauth:${provider}] unexpected error:`, err);
			errorMsg = err instanceof Error ? err.message : "An unexpected error occurred";
			loading = false;
		}
	}
</script>

<div class="space-y-6">
	{#if errorMsg}
		<p class="text-destructive text-sm font-medium">{errorMsg}</p>
	{/if}

	{#if magicLinkSent}
		<div class="space-y-3 rounded-lg border p-4 text-center">
			<p class="text-sm font-medium">Check your email</p>
			<p class="text-muted-foreground text-xs">
				We sent a sign-in link to
				<strong>{$formData.email}</strong>. Click the link in the email to sign in.
			</p>
			<Button
				variant="link"
				onclick={() => {
					magicLinkSent = false;
				}}
			>
				Try a different method
			</Button>
		</div>
	{:else}
		<!-- Passkey -->
		<Button onclick={handlePasskeyLogin} disabled={loading} class="w-full gap-2">
			<KeyRound class="size-4" />
			{loading ? "Authenticating…" : "Sign in with Passkey"}
		</Button>

		<div class="relative">
			<div class="absolute inset-0 flex items-center">
				<Separator />
			</div>
			<div class="relative flex justify-center text-xs uppercase">
				<span class="bg-background text-muted-foreground px-2">or</span>
			</div>
		</div>

		<!-- Magic Link (superForm-powered) -->
		<form method="POST" use:enhance class="space-y-4">
			<Form.Field {form} name="email">
				<Form.Control>
					{#snippet children({ props })}
						<Form.Label>Email</Form.Label>
						<div class="flex gap-2">
							<Input
								{...props}
								type="email"
								placeholder="you@example.com"
								bind:value={$formData.email}
								disabled={loading || $submitting}
							/>
							<Form.Button
								variant="secondary"
								disabled={loading || $submitting}
								class="shrink-0 gap-2"
							>
								{#if $submitting}
									<Loader class="size-4 animate-spin" />
								{:else}
									<Mail class="size-4" />
								{/if}
								Send
							</Form.Button>
						</div>
					{/snippet}
				</Form.Control>
				<Form.FieldErrors />
			</Form.Field>
		</form>

		<div class="relative">
			<div class="absolute inset-0 flex items-center">
				<Separator />
			</div>
			<div class="relative flex justify-center text-xs uppercase">
				<span class="bg-background text-muted-foreground px-2">or continue with</span>
			</div>
		</div>

		<!-- OAuth -->
		<!--
			Google sign-in disabled for now -- no OAuth app registered yet
			(auth.ts's socialProviders.google is commented out too). Re-enable
			both together, and restore `grid-cols-2` below, once one exists.
		-->
		<div class="grid grid-cols-1 gap-2">
			<Button variant="outline" onclick={() => handleOAuth("github")} disabled={loading} class="gap-2">
				<Github class="size-4" />
				GitHub
			</Button>
		</div>
	{/if}
</div>
