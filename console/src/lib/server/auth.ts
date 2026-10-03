/**
 * better-auth server instance (factory pattern).
 *
 * D1 bindings aren't available at module scope on Cloudflare Workers,
 * so the auth instance is created lazily via `getAuth(d1)` and cached
 * for the lifetime of the worker isolate.
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
import { D1Dialect } from "kysely-d1";
import { sendMagicLinkEmail, sendVerificationOTPEmail } from "./email";
import type { getDynamicHostInfo } from "./hosting";

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

let _auth: unknown;
let _authCacheKey: string | undefined;

/**
 * Create or return the cached better-auth instance.
 *
 * Must be called with the D1 binding on every request (typically in
 * `hooks.server.ts` or a route handler -- always pass `hostInfo` when one
 * is available; see below).
 *
 * Cached per `hostInfo`'s resolved `baseURL`, not just once per isolate:
 * this console is served from two origins (`anemoi.systems` and
 * `anemoi-console.*.workers.dev`, both live per `wrangler.jsonc`), and
 * `passkey({ rpID })`/`baseURL`/`trustedOrigins` all derive from
 * `hostInfo`. Caching unconditionally on the first call froze the whole
 * isolate's auth config to whichever origin happened to hit it first --
 * WebAuthn rejects a passkey ceremony against a mismatched `rpId`, so
 * passkey registration/verification on the *other* origin would silently
 * fail for the rest of that isolate's life (Copilot review, PR #197).
 */
export function getAuth(
	d1: D1Database,
	hostInfo?: ReturnType<typeof getDynamicHostInfo>,
): ReturnType<typeof betterAuth> {
	// `BetterAuthOptions.baseURL`'s type also allows a dynamic-resolver
	// config object, not just a string -- `hosting.ts` only ever
	// constructs it as a plain string, so narrow rather than widen
	// `cacheKey` to match.
	const cacheKey = typeof hostInfo?.ba.baseURL === 'string' ? hostInfo.ba.baseURL : '';
	if (_auth && _authCacheKey === cacheKey) return _auth as ReturnType<typeof betterAuth>;
	_authCacheKey = cacheKey;

	const dialect = new D1Dialect({ database: d1 });

	_auth = betterAuth({
		...hostInfo?.ba,
		database: {
			dialect,
			type: "sqlite" as const,
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
				rpID: hostInfo?.rpId ?? process.env.RP_ID,
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

	return _auth as ReturnType<typeof betterAuth>;
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

export type Auth = ReturnType<typeof getAuth>;
