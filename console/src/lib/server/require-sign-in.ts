import { redirect } from "@sveltejs/kit";
import type { Guard } from "svelte-guard";
import type { ServerLoad } from "@sveltejs/kit";
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

/**
 * The same check as a server `load`, for each Develop page's
 * +page.server.ts. The guard alone only runs when the browser asks the
 * server for something: a direct visit does, but a client-side navigation
 * (Develop → Registry from any page) to a page with no server load never
 * does, so the page rendered for a signed-out visitor. A server load makes
 * every navigation to the page a server request, which the guard and this
 * both see.
 */
export const requireSignInLoad: ServerLoad = ({ locals, url }) => {
	if (!locals.user) {
		redirect(303, loginHref(url.pathname + url.search));
	}
	return {};
};
