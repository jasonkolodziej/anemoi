<script lang="ts">
	// Styling and form logic are split across lib/components/auth/:
	// login-form.svelte (the actual sign-in UI/handlers) is wrapped by
	// either login-01.svelte (centered, current default) or login-02.svelte
	// (split-screen alternate) -- swap the import below to switch.
	import Login from "$lib/components/auth/login-01.svelte";
	import type { PageData } from "./$types";

	let { data }: { data: PageData } = $props();
</script>

<Login form={data.form} />
