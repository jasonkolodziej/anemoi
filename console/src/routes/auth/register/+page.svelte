<script lang="ts">
  import { Mail } from "@lucide/svelte";
  import { Github } from "$lib/components/icons";
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
  import { Input } from "$lib/components/ui/input";
  import { Label } from "$lib/components/ui/label";
  import { Separator } from "$lib/components/ui/separator";

  let loading = $state(false);
  let errorMsg = $state("");
  let magicLinkEmail = $state("");
  let magicLinkSent = $state(false);

  // ── Magic link sign-up ──────────────────────────────────────────────────
  async function handleMagicLink() {
    if (!magicLinkEmail.trim()) {
      errorMsg = "Please enter your email address.";
      return;
    }
    loading = true;
    errorMsg = "";
    try {
      const { error } = await authClient.signIn.magicLink({
        email: magicLinkEmail.trim(),
        callbackURL: "/profile",
      });
      if (error) {
        console.error("[auth:register:magic-link] sign-up error:", error);
        errorMsg = error.message ?? "Failed to send magic link";
        return;
      }
      magicLinkSent = true;
    } catch (err) {
      console.error("[auth:register:magic-link] unexpected error:", err);
      errorMsg =
        err instanceof Error ? err.message : "An unexpected error occurred";
    } finally {
      loading = false;
    }
  }

  // ── OAuth sign-up ───────────────────────────────────────────────────────
  async function handleOAuth(provider: "github" | "google") {
    loading = true;
    errorMsg = "";
    try {
      await authClient.signIn.social({
        provider,
        callbackURL: "/profile",
      });
    } catch (err) {
      console.error(`[auth:register:oauth:${provider}] unexpected error:`, err);
      errorMsg =
        err instanceof Error ? err.message : "An unexpected error occurred";
      loading = false;
    }
  }
</script>

<div class="flex min-h-svh items-center justify-center px-4">
  <Card class="w-full max-w-sm">
    <CardHeader class="text-center">
      <CardTitle class="text-2xl">Create Account</CardTitle>
      <CardDescription>
        Sign up with your email or a social account. You can add a passkey later
        from account settings.
      </CardDescription>
    </CardHeader>
    <CardContent class="flex flex-col gap-4">
      {#if errorMsg}
        <p class="text-destructive text-sm">{errorMsg}</p>
      {/if}

      {#if magicLinkSent}
        <div class="rounded-md border p-4 text-center">
          <p class="text-sm font-medium">Check your email</p>
          <p class="text-muted-foreground mt-1 text-xs">
            We sent a sign-up link to <strong>{magicLinkEmail}</strong>. Click
            the link in the email to create your account.
          </p>
          <Button
            variant="link"
            class="mt-2"
            onclick={() => {
              magicLinkSent = false;
            }}
          >
            Try a different method
          </Button>
        </div>
      {:else}
        <!-- Magic Link -->
        <div class="flex flex-col gap-2">
          <Label for="register-email">Email</Label>
          <div class="flex gap-2">
            <Input
              id="register-email"
              type="email"
              placeholder="you@example.com"
              bind:value={magicLinkEmail}
              disabled={loading}
              onkeydown={(e: KeyboardEvent) =>
                e.key === "Enter" && handleMagicLink()}
            />
            <Button
              variant="secondary"
              onclick={handleMagicLink}
              disabled={loading || !magicLinkEmail.trim()}
            >
              <Mail class="mr-1 h-4 w-4" />
              Send
            </Button>
          </div>
          <p class="text-muted-foreground text-xs">
            We'll email you a magic link to create your account.
          </p>
        </div>

        <div class="relative">
          <div class="absolute inset-0 flex items-center">
            <Separator />
          </div>
          <div class="relative flex justify-center text-xs uppercase">
            <span class="bg-card text-muted-foreground px-2"
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
          >
            <Github class="mr-2 h-4 w-4" />
            GitHub
          </Button>
          <Button
            variant="outline"
            onclick={() => handleOAuth("google")}
            disabled={loading}
          >
            <svg class="mr-2 h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
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
    </CardContent>
    <CardFooter class="justify-center">
      <p class="text-muted-foreground text-sm">
        Already have an account?
        <a href="/auth/login" class="text-primary underline">Sign in</a>
      </p>
    </CardFooter>
  </Card>
</div>
