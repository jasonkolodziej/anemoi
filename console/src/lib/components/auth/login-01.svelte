<script lang="ts">
	/**
	 * Centered single-column sign-in page -- the original layout, now just
	 * chrome around login-form.svelte (see that file for the actual form
	 * logic). The alternate split-screen layout is login-02.svelte; the
	 * page (routes/auth/login/+page.svelte) picks one of the two.
	 */
	import type { SuperValidated, Infer } from "sveltekit-superforms";
	import LoginForm from "./login-form.svelte";
	import type { LoginSchema } from "./login-schema";

	interface Props {
		form: SuperValidated<Infer<LoginSchema>>;
	}
	let { form }: Props = $props();
</script>

<div class="flex min-h-svh items-center justify-center px-4">
	<div class="w-full max-w-sm space-y-6">
		<div class="space-y-2 text-center">
			<h1 class="text-2xl font-semibold tracking-tight">Sign In</h1>
			<p class="text-muted-foreground text-sm">Choose your preferred sign-in method.</p>
		</div>

		<LoginForm {form} />

		<p class="text-muted-foreground text-center text-sm">
			Don't have an account?
			<a href="/auth/register" class="text-primary underline">Register</a>
		</p>
	</div>
</div>
