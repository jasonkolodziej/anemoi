<script lang="ts">
  // Split-screen alternate to login-01.svelte -- same login-form.svelte,
  // different chrome. The page (routes/auth/login/+page.svelte) picks one
  // of the two.
  import GalleryVerticalEndIcon from "@lucide/svelte/icons/gallery-vertical-end";
  import LoginForm from "$lib/components/auth/login-form.svelte";
  import type { SuperValidated, Infer } from "sveltekit-superforms";
  import type { LoginSchema } from "$lib/components/auth/login-schema";

  interface Props {
    form: SuperValidated<Infer<LoginSchema>>;
  }
  let { form }: Props = $props();
</script>

<div class="grid min-h-svh lg:grid-cols-2">
  <div class="flex flex-col gap-4 p-6 md:p-10">
    <div class="flex justify-center gap-2 md:justify-start">
      <a href="##" class="flex items-center gap-2 font-medium">
        <div
          class="flex size-6 items-center justify-center rounded-md bg-primary text-primary-foreground"
        >
          <GalleryVerticalEndIcon class="size-4" />
        </div>
        Acme Inc.
      </a>
    </div>
    <div class="flex flex-1 items-center justify-center">
      <div class="w-full max-w-xs">
        <LoginForm {form} />
      </div>
    </div>
  </div>
  <div class="relative hidden bg-muted lg:block">
    <img
      src="/placeholder.svg"
      alt="placeholder"
      class="absolute inset-0 h-full w-full object-cover dark:brightness-[0.2] dark:grayscale"
    />
  </div>
</div>
