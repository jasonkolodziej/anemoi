import { redirect } from "@sveltejs/kit";
import type { Guard } from "svelte-guard";
import { loginHref } from "$lib/auth-return";

/**
 * A route guard (svelte-guard, see hooks.server.ts) for pages only a
 * signed-in user sees -- the Develop pages: architecture, registry,
 * monitoring, retraining. Runs on every request, client-side navigation
 * included, before any load, and sends an anonymous visitor to sign in
 * and then back to the page they asked for.
 */
export const requireSignIn: Guard = ({ locals, url }) => {
	if (!locals.user) {
		redirect(303, loginHref(url.pathname + url.search));
	}
	return true;
};
