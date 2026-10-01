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
        <!--
          Google sign-in disabled for now -- no OAuth app registered yet
          (auth.ts's socialProviders.google is commented out too). Re-enable
          both together, and restore `grid-cols-2` below, once one exists.
        -->
        <div class="grid grid-cols-1 gap-2">
          <Button
            variant="outline"
            onclick={() => handleOAuth("github")}
            disabled={loading}
          >
            <Github class="mr-2 h-4 w-4" />
            GitHub
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
