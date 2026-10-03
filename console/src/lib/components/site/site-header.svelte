<script lang="ts">
	/**
	 * The site-wide top header -- migrated out of the root +layout.svelte
	 * (logo, desktop navigation-menu bar, GitHub/version line, sign-in/
	 * profile, and the mobile drawer trigger). `sticky top-0` here is
	 * relative to <main>'s own scroll container (overflow-y-auto,
	 * +layout.svelte), not the viewport -- living outside that scroll
	 * container as a normal-flow sibling of <main> is what makes this
	 * never collide with the docs route's own sticky search bar despite
	 * both nominally being "sticky top-0" (see docs/+layout.svelte).
	 * Rendered once in +layout.svelte; MobileSidebar is nested inside this
	 * rather than rendered as a layout-level sibling because that's where
	 * its trigger button actually sits in the header's own flex row.
	 */
	import { page } from "$app/state";
	import HurricaneIcon from "$lib/components/anemoi/HurricaneIcon.svelte";
	import MobileSidebar from "./mobile-sidebar.svelte";
	import NavMenu, { type NavEntry } from "$lib/components/navigation/navigation-menu.svelte";
	import { Button } from "$lib/components/ui/button";
	import Github from "$lib/icons/github.svelte";
	import { UserContext } from "$lib/user.context.svelte";

	interface NavItem {
		href: string;
		label: string;
	}
	interface Props {
		nav: NavItem[];
		/** Real /v1/health.anemoi_version, fetched once by +layout.svelte --
		 * null until that resolves. Not fetched here too; one shared value
		 * for both this bar and MobileSidebar's drawer. */
		anemoiVersion?: string | null;
	}
	let { nav, anemoiVersion = null }: Props = $props();

	// `nav`'s plain {href, label} shape is already a valid NavLinkEntry
	// (its `type` defaults to "link") -- no transform needed to hand it to
	// the generalized nav-menu component.
	let items = $derived(nav as NavEntry[]);

	function isActive(href: string): boolean {
		if (href === "/") return page.url.pathname === "/";
		return page.url.pathname.startsWith(href);
	}

	const userState = UserContext.get();
</script>

<header
	class="sticky top-0 z-30 shrink-0 border-b border-border bg-surface pt-[env(safe-area-inset-top)]"
>
	<div class="flex items-center gap-3 px-4 py-3 md:px-6">
		<a href="/" class="flex shrink-0 items-center gap-2.5">
			<HurricaneIcon size={24} />
			<div class="hidden sm:block">
				<p class="font-display text-sm font-semibold leading-none text-text">
					Anemoi
				</p>
				<p class="mt-1 text-[10px] leading-none text-text-faint">
					Many winds. One forecast.
				</p>
			</div>
		</a>

		<NavMenu {items} {isActive} class="hidden flex-1 justify-center md:flex" />

		<div class="ml-auto hidden shrink-0 items-center gap-3 md:flex">
			<p class="text-[10px] text-text-faint">
				{anemoiVersion ? `v${anemoiVersion} · ` : ""}
				<Github class="inline-block size-2.5 text-text-faint mr-1" />
				<a
					href="https://github.com/jasonkolodziej/anemoi"
					class="text-text-faint hover:text-text"
					target="_blank"
					rel="noopener noreferrer">jasonkolodziej/anemoi</a
				>
			</p>
			{#if userState.isAuthenticated}
				<a
					href="/profile"
					class="flex items-center gap-2 rounded-md px-2 py-1 text-sm font-medium text-text-muted transition-colors hover:bg-surface-raised hover:text-text"
				>
					<span
						class="flex size-6 items-center justify-center rounded-full bg-surface-raised text-[10px] font-semibold text-text"
					>
						{userState.initials}
					</span>
					{userState.displayName}
				</a>
			{:else}
				<Button href="/auth/login" size="sm">Sign in</Button>
			{/if}
		</div>

		<div class="ml-auto md:hidden">
			<MobileSidebar {nav} {anemoiVersion} />
		</div>
	</div>
</header>
