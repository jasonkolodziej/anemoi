/**
 * better-auth server instance (factory pattern).
 *
 * D1 bindings aren't available at module scope on Cloudflare Workers,
 * so the auth instance is created via `getAuth(event)` -- once per
 * request, never shared across requests (see `getAuth` for why).
 *
 * Includes:
 * - Passkey authentication (`@better-auth/passkey`)
 * - Magic link sign-in via Cloudflare Email Routing (`SEND_EMAIL` binding)
 * - API key generation for programmatic registry access
 * - GitHub + Google OAuth social providers
 * - Admin plugin for user management + RBAC
 * - Registration policy enforcement via `databaseHooks`
 */

import { passkey } from "@better-auth/passkey";
import { betterAuth } from "better-auth";
import { APIError } from "better-auth/api";
import { admin, emailOTP, magicLink } from "better-auth/plugins";
import { apiKey } from "@better-auth/api-key";
import { sveltekitCookies } from "better-auth/svelte-kit";
import { getRequestEvent } from "$app/server";
import type { RequestEvent } from "@sveltejs/kit";
import { sendMagicLinkEmail, sendVerificationOTPEmail } from "./email";
import { getDynamicHostInfo } from "./hosting";

// ─── Registration Policy Helper ──────────────────────────────────────────────

/**
 * Check whether open registration is enabled.
 *
 * 1. Query the `registration_policy` D1 table for `open_registration`.
 * 2. If no row or the query fails, fall back to the `OPEN_REGISTRATION`
 *    environment variable (default: `"false"`).
 */
async function checkRegistrationOpen(d1: D1Database): Promise<boolean> {
	try {
		const row = await d1
			.prepare("SELECT value FROM registration_policy WHERE key = ?")
			.bind("open_registration")
			.first<{ value: string }>();
		if (row) return row.value === "true";
	} catch {
		// D1 query failed — fall back to env
	}
	// Fallback to env var; default closed
	const openRegistration = String(process.env.OPEN_REGISTRATION ?? "false");
	return openRegistration === "true";
}

// ─── Auth Instance Factory ───────────────────────────────────────────────────

/**
 * One better-auth instance per request, memoized on the `Request` so
 * hooks.server.ts and a route handler in the same request (e.g.
 * routes/auth/logout/+server.ts) share it rather than building two.
 */
const _authByRequest = new WeakMap<Request, Auth>();

/**
 * Return this request's better-auth instance, or `null` when there's no
 * `AUTH_DB` binding (plain `vite dev`, prerendering).
 *
 * Deliberately NOT cached across requests (it used to be, once per
 * isolate) -- that cache was the real cause of the production hangs on
 * sign-out and the profile page's passkey list/registration ("Canceled"
 * in `wrangler tail`). Reproduced under `wrangler dev` (workerd, not
 * `vite dev`'s Node runtime, which is why it never showed up locally):
 *
 * 1. Kysely serializes every query through one per-instance
 *    `ConnectionMutex` whenever the dialect reports
 *    `supportsMultipleConnections === false` -- which SQLite, and so
 *    better-auth's D1 dialect, does (kysely 0.29 RuntimeDriver).
 * 2. `@better-auth/api-key`'s `listApiKeys` (and create/update/delete)
 *    fire `deleteAllExpiredApiKeys()` without awaiting it or handing it
 *    to `runInBackground`, so the endpoint responds while that DELETE is
 *    still holding the mutex.
 * 3. Workers never resumes a request's leftover I/O once its response is
 *    sent, so that DELETE never settles and the mutex is never released.
 *    Every later query on the shared instance -- the very next
 *    `list-user-passkeys`, `generate-register-options`, sign-out's
 *    session delete -- waits on it forever until the platform cancels.
 *
 * The profile page calls `apiKey.list()` right before
 * `listUserPasskeys`, which is exactly the observed "Passkeys:
 * Loading..." / stuck "Follow your browser's prompt..." / sign-out does
 * nothing sequence. A per-request instance gets its own Kysely instance
 * and mutex, so a stray background query can only ever affect the
 * request that started it (construction is ~5-10ms -- plugin setup, no
 * I/O). `advanced.backgroundTasks` below additionally hands the work
 * better-auth *does* route through `runInBackground` to `waitUntil`, per
 * better-auth's documented Cloudflare Workers setup, so it actually
 * completes instead of being dropped.
 */
export function getAuth(event: RequestEvent): Auth | null {
	const cached = _authByRequest.get(event.request);
	if (cached) return cached;

	const d1 = event.platform?.env?.AUTH_DB;
	if (!d1) return null;

	const ctx = event.platform?.ctx;
	const auth = buildAuth(d1, getDynamicHostInfo(event), ctx ? (p) => ctx.waitUntil(p) : undefined);
	_authByRequest.set(event.request, auth);
	return auth;
}

function buildAuth(
	d1: D1Database,
	hostInfo: ReturnType<typeof getDynamicHostInfo>,
	waitUntil: ((promise: Promise<unknown>) => void) | undefined,
) {
	return betterAuth({
		...hostInfo.ba,
		// Passing the raw D1 binding (not a hand-built `{ dialect, type }`
		// via the third-party `kysely-d1` package, which this used to do)
		// is what makes better-auth's own adapter factory auto-detect D1 --
		// confirmed in its source (@better-auth/kysely-adapter's
		// createKyselyAdapter): detection is a duck-type check for
		// `"batch" in db && "exec" in db && "prepare" in db`, which only a
		// bare D1Database satisfies, not a `{ dialect, type }` wrapper. Only
		// that branch sets `transaction: false` and swaps in better-auth's
		// own D1-aware dialect -- D1 has no interactive transactions
		// (`beginTransaction()` just throws "not supported").
		database: d1,
		advanced: {
			// better-auth's documented hook for serverless runtimes:
			// `ctx.context.runInBackground(...)` work (deferred API-key
			// updates, etc.) goes to `waitUntil` so Workers keeps the
			// request alive until it finishes. Undefined in `vite dev`,
			// where better-auth falls back to a plain floating promise.
			backgroundTasks: waitUntil ? { handler: waitUntil } : undefined,
			database: {
				// Skip better-auth's runtime schema check in production:
				// every "transactional" operation awaits a `PRAGMA
				// table_info` introspection of every better-auth table on
				// a cold instance -- with a per-request instance (see
				// getAuth) that would be every request. The schema is
				// managed by console/schemas/*.sql instead.
				// `pnpm test:e2e:workerd` turns it back on (the var below)
				// so drift between those files and what the installed
				// plugins write fails the suite, not production.
				validateSchema: process.env.BETTER_AUTH_VALIDATE_SCHEMA === "true",
			},
		},
		// Caches the session + user payload in a signed cookie so
		// `auth.api.getSession()` (hooks.server.ts, called on every request)
		// skips the D1 round-trip for a signed-in user as long as the cache
		// is fresh -- confirmed in better-auth's own source
		// (api/routes/session.mjs) that an anonymous request already
		// short-circuits before touching the DB, so this specifically cuts
		// per-request D1 load for authenticated traffic, which is now most
		// page views since the top nav reads `locals.user` everywhere.
		// Trade-off: a role/ban change (admin plugin) or a server-side
		// session revocation won't show up in `locals.user` until the cache
		// expires -- 5 minutes is the library default and fine for this
		// console's traffic; shorten it if that staleness window matters
		// more than the D1 savings.
		session: {
			cookieCache: {
				enabled: true,
				maxAge: 5 * 60,
			},
		},
		// #171: the plan every customer is on. No paid values exist yet --
		// this exists now so Phase 2 (quota enforcement) and Phase 3 (Stripe
		// tiers) are additive later instead of needing a schema migration
		// plus a backfill once real customers exist. `input: false` keeps a
		// client from setting their own plan via sign-up/update-user.
		user: {
			additionalFields: {
				plan: {
					type: "string",
					defaultValue: "free",
					input: false,
				},
			},
		},
		socialProviders: {
			github: {
				clientId: process.env.GITHUB_CLIENT_ID ?? "",
				clientSecret: process.env.GITHUB_CLIENT_SECRET ?? "",
			},
			// Google sign-in disabled for now -- no OAuth app registered yet
			// (GOOGLE_CLIENT_ID/SECRET unset). Re-enable by uncommenting here
			// and in the login/register pages' OAuth button grid once one
			// exists.
			// google: {
			// 	clientId: process.env.GOOGLE_CLIENT_ID ?? "",
			// 	clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
			// },
		},
		plugins: [
			passkey({
				rpID: hostInfo.rpId,
				rpName: "Anemoi",
			}),
			magicLink({
				sendMagicLink: async ({ email, url }) => {
					await sendMagicLinkEmail(email, url);
				},
			}),
			emailOTP({
				async sendVerificationOTP({ email, otp, type }) {
					await sendVerificationOTPEmail(email, otp, type);
				},
			}),
			apiKey({ enableSessionForAPIKeys: true }),
			admin({
				defaultRole: "user",
				// Seed admin: set ADMIN_USER_IDS env var to a comma-separated
				// list of user IDs that should always have admin access.
				// After first sign-up, grab the user ID from D1 and set it here.
				// Alternatively, run: UPDATE user SET role = 'admin' WHERE email = 'you@example.com'
				adminUserIds: (process.env.ADMIN_USER_IDS ?? "")
					.split(",")
					.map((id) => id.trim())
					.filter(Boolean),
			}),
			// Must be last: makes `auth.api.*` calls made directly from
			// SvelteKit server code (routes/auth/logout/+server.ts's
			// `auth.api.signOut()`) set/clear cookies on the real SvelteKit
			// response instead of only on an internal Response object.
			sveltekitCookies(getRequestEvent),
		],

		// ── Registration policy enforcement ───────────────────────────────
		databaseHooks: {
			user: {
				create: {
					before: async (user) => {
						// Admin-created users bypass the policy.
						// The admin plugin's `/admin/create-user` endpoint already
						// requires an authenticated admin session, so we check whether
						// the user record was explicitly flagged as admin-created.
						// Since databaseHooks don't receive the request context directly,
						// we rely on the `_adminBypass` flag set in the before-hook
						// middleware below. The flag is stored on the module-scoped
						// variable which is safe because Workers process one request
						// at a time per isolate.
						if (_adminBypassActive) {
							return { data: user };
						}

						const isOpen = await checkRegistrationOpen(d1);
						if (!isOpen) {
							throw new APIError("FORBIDDEN", {
								message: "Registration is currently closed. Contact an admin.",
							});
						}
						return { data: user };
					},
				},
			},
		},
	});
}

// ── Admin bypass flag ────────────────────────────────────────────────────────
// Workers isolates are single-threaded, so a module-level boolean is safe
// as a request-scoped flag. It's set before the admin create-user call
// and cleared immediately after.

let _adminBypassActive = false;

/**
 * Temporarily enable the admin bypass for registration policy.
 *
 * Call this around `auth.api.createUser()` invocations from admin
 * endpoints so that `databaseHooks.user.create.before` allows the
 * creation even when registration is closed. `fn` is always async in
 * practice (`createUser` returns a Promise) -- `await`ed here, not just
 * returned, so the flag stays set until the hook it's meant to influence
 * actually runs. A bare `return fn()` let `finally` clear the flag the
 * instant the promise was created, before `databaseHooks.user.create
 * .before` ever read it, silently defeating the bypass for its one real
 * use case (Copilot review, PR #197).
 */
export async function withAdminBypass<T>(fn: () => Promise<T>): Promise<T> {
	_adminBypassActive = true;
	try {
		return await fn();
	} finally {
		_adminBypassActive = false;
	}
}

export type Auth = ReturnType<typeof buildAuth>;
