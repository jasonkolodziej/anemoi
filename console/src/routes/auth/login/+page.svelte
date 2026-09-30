<script lang="ts">
  import { KeyRound, Mail } from "@lucide/svelte";
  import { Github } from "$lib/components/icons";
  import Loader from "@lucide/svelte/icons/loader";
  import { superForm } from "sveltekit-superforms";
  import { arktype } from "sveltekit-superforms/adapters";
  import { goto } from "$app/navigation";
  import { authClient } from "$lib/auth-client";
  import { Button } from "$lib/components/ui/button/index";
  import * as Form from "$lib/components/ui/form/index";
  import { Input } from "$lib/components/ui/input/index";
  import { Separator } from "$lib/components/ui/separator/index";
  import type { PageData } from "./$types";
  import { loginSchema } from "./schema";

  let { data }: { data: PageData } = $props();

  let loading = $state(false);
  let errorMsg = $state("");
  let magicLinkSent = $state(false);

  const form = superForm(data.form, {
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
      // window.location.href = "/admin";
      await goto("/profile");
    } catch (err) {
      console.error("[auth:passkey] unexpected error:", err);
      errorMsg =
        err instanceof Error ? err.message : "An unexpected error occurred";
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
      errorMsg =
        err instanceof Error ? err.message : "An unexpected error occurred";
    } finally {
      loading = false;
    }
  }

  // ── OAuth sign-in ───────────────────────────────────────────────────────
  async function handleOAuth(provider: "github" | "google") {
    loading = true;
    errorMsg = "";
    try {
      await authClient.signIn.social({
        provider,
        callbackURL: "/profile",
      });
    } catch (err) {
      console.error(`[auth:oauth:${provider}] unexpected error:`, err);
      errorMsg =
        err instanceof Error ? err.message : "An unexpected error occurred";
      loading = false;
    }
  }
</script>

<div class="flex min-h-svh items-center justify-center px-4">
  <div class="w-full max-w-sm space-y-6">
    <div class="space-y-2 text-center">
      <h1 class="text-2xl font-semibold tracking-tight">Sign In</h1>
      <p class="text-muted-foreground text-sm">
        Choose your preferred sign-in method.
      </p>
    </div>

    {#if errorMsg}
      <p class="text-destructive text-sm font-medium">{errorMsg}</p>
    {/if}

    {#if magicLinkSent}
      <div class="space-y-3 rounded-lg border p-4 text-center">
        <p class="text-sm font-medium">Check your email</p>
        <p class="text-muted-foreground text-xs">
          We sent a sign-in link to
          <strong>{$formData.email}</strong>. Click the link in the email to
          sign in.
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
      <Button
        onclick={handlePasskeyLogin}
        disabled={loading}
        class="w-full gap-2"
      >
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
          <span class="bg-background text-muted-foreground px-2"
            >or continue with</span
          >
        </div>
      </div>

      <!-- OAuth -->
      <div class="grid grid-cols-2 gap-2">
        <Button
          variant="outline"
          onclick={() => handleOAuth("github")}
          disabled={loading}
          class="gap-2"
        >
          <Github class="size-4" />
          GitHub
        </Button>
        <Button
          variant="outline"
          onclick={() => handleOAuth("google")}
          disabled={loading}
          class="gap-2"
        >
          <svg class="size-4" viewBox="0 0 24 24" fill="currentColor">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          Google
        </Button>
      </div>
    {/if}

    <p class="text-muted-foreground text-center text-sm">
      Don't have an account?
      <a href="/auth/register" class="text-primary underline">Register</a>
    </p>
  </div>
</div>
