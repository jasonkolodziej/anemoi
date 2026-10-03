import { building } from "$app/environment";
import { sequence } from "@sveltejs/kit/hooks";
import { svelteKitHandler } from "better-auth/svelte-kit";
import { createGuardHook } from "svelte-guard";
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
 *
 * `/api/auth/*` requests skip the `getSession()` call below entirely --
 * found doing a latency pass on this route (user-reported: "too much
 * latency"). `isAuthPath` (see below) means `svelteKitHandler` hands
 * these straight to `auth.handler(request)` and returns *without ever
 * calling `resolve(event)`* -- so nothing downstream (no +page.server.ts
 * load, no other hook) ever reads `event.locals.session`/`user` for this
 * branch; populating them was a second, fully wasted session resolution
 * (a cookie-cache decode+verify, or a D1 round-trip on a cache miss) on
 * top of the one `auth.handler()` already does internally for whichever
 * specific endpoint needs it. Confirmed via `better-auth/svelte-kit`'s
 * own `isAuthPath` (same same-origin + `/api/auth` prefix check
 * `svelteKitHandler` uses) so this can decide *before* doing that
 * redundant work rather than after.
 */
const authHandle: Handle = async ({ event, resolve }) => {
	// Short id so staged logs from one request (here, auth.ts's getAuth,
	// routes/auth/logout/+server.ts) can be told apart in `wrangler tail`
	// when several auth requests are in flight on the same isolate --
	// chasing an intermittent production hang (#171 follow-up) that
	// showed "Canceled" in tail with no exception, and never reproduced
	// locally. `verbose` is scoped to the paths that have actually hung
	// (better-auth's own handler, our own logout route) -- every other
	// request on this app (storm data, docs, static assets) would just
	// be noise.
	const requestId = crypto.randomUUID().slice(0, 8);
	event.locals.requestId = requestId;
	const isBetterAuthRoute = event.url.pathname.startsWith("/api/auth/");
	const verbose = isBetterAuthRoute || event.url.pathname === "/auth/logout";
	const startedAt = Date.now();
	if (verbose) console.log(`[authHandle ${requestId}] ${event.request.method} ${event.url.pathname}`);

	// `adapter-cloudflare` throws on any `platform.env` access during
	// prerendering (no real bindings exist at build time) -- this console
	// still prerenders `/docs/[slug]` (opts into `ssr = true`, see its own
	// README), so a plain `pnpm build` hit this for real: "Cannot access
	// platform.env.SEND_EMAIL in a prerenderable route". `building` (set
	// only during `vite build`, not `vite dev` or a deployed request) is
	// also what's passed to `svelteKitHandler` below for the same reason.
	if (building) {
		event.locals.session = null;
		event.locals.user = null;
		return resolve(event);
	}

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
	if (verbose) console.log(`[authHandle ${requestId}] getAuth resolved at +${Date.now() - startedAt}ms`);

	if (isBetterAuthRoute) {
		// See the function doc comment -- locals are never read for this
		// branch, so resolving them here would just be a second session
		// lookup on top of the one auth.handler() does itself.
		event.locals.session = null;
		event.locals.user = null;
	} else {
		const result = await auth.api.getSession({
			headers: buildSessionHeaders(event.request),
		});
		event.locals.session = result?.session ?? null;
		event.locals.user = result?.user ?? null;
	}
	if (verbose)
		console.log(
			`[authHandle ${requestId}] locals resolved at +${Date.now() - startedAt}ms (user=${event.locals.user?.id ?? "none"}${isBetterAuthRoute ? ", skipped -- better-auth route" : ""})`,
		);

	const response = await svelteKitHandler({ event, resolve, auth, building });
	if (verbose)
		console.log(`[authHandle ${requestId}] svelteKitHandler resolved at +${Date.now() - startedAt}ms (status=${response.status})`);
	return response;
};

// `-guard.ts` files under src/routes/** (e.g. profile/-guard.ts,
// auth/login/-guard.ts) -- see https://github.com/mehdikhody/svelte-guard.
// `sequence(authHandle, guardHook)` is load-bearing order: guards read
// `event.locals.session`/`user`, which only exist once authHandle above
// has run, so the guard hook must come second. During `building`,
// authHandle's early return still flows into this hook (sequence wires
// `resolve` to call the next handle) -- harmless, since every guard here
// only inspects `locals`, never `platform.env`.
const guards = import.meta.glob("./routes/**/-guard.*");

export const handle: Handle = sequence(authHandle, createGuardHook(guards));
