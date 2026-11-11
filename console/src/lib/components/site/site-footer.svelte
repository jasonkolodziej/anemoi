<script lang="ts">
	/**
	 * The site footer: "Cookie settings", which reopens the cookie banner
	 * (`$lib/consent.svelte`). A strip under the scrolling `main` on desktop
	 * (the layout's column is `md:h-screen`), and the last thing on the page
	 * on a phone, where the mobile menu has the same button.
	 */
	import { consent } from "$lib/consent.svelte";
</script>

<footer
	class="flex shrink-0 justify-end border-t border-border px-4 py-1.5 pb-[max(0.375rem,env(safe-area-inset-bottom))] text-[10px] text-text-faint sm:px-6"
>
	<button
		type="button"
		class="text-text-faint hover:text-text"
		onclick={() => consent.openSettings()}>Cookie settings</button
	>
</footer>
