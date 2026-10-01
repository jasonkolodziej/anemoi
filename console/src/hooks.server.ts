import { building } from "$app/environment";
import { svelteKitHandler } from "better-auth/svelte-kit";
import type { Handle } from "@sveltejs/kit";
import { setSendEmailBinding } from "$lib/server/email";
import { getDynamicHostInfo } from "$lib/server/hosting";
import { getAuth } from "$lib/server/auth";
import { buildSessionHeaders } from "$lib/server/auth-utils";

/**
 * Populates `event.locals.session`/`user`, then delegates to
 * `svelteKitHandler` -- which itself intercepts `/api/auth/*` (better-
 * auth's default `basePath`) internally and calls `resolve(event)` for
 * everything else. No separate catch-all route needed.
 * https://www.better-auth.com/docs/integrations/svelte-kit
 *
 * `buildSessionHeaders` (auth-utils.ts) resolves a session from the
 * request's cookie first, falling back to `x-api-key`/`Authorization:
 * Bearer`/`?token=` -- the same request can carry either a browser
 * session or a bearer API key, and this is the one place that ambiguity
 * gets resolved for the whole app.
 */
export const handle: Handle = async ({ event, resolve }) => {
	setSendEmailBinding(event.platform?.env?.SEND_EMAIL);

	const d1 = event.platform?.env?.AUTH_DB;
	if (!d1) {
		// Local `vite dev` without `wrangler dev --remote` has no D1 binding
		// at all -- treat every request as anonymous rather than throw.
		event.locals.session = null;
		event.locals.user = null;
		return resolve(event);
	}

	const auth = getAuth(d1, getDynamicHostInfo(event));
	const result = await auth.api.getSession({
		headers: buildSessionHeaders(event.request),
	});

	event.locals.session = result?.session ?? null;
	event.locals.user = result?.user ?? null;

	return svelteKitHandler({ event, resolve, auth, building });
};
