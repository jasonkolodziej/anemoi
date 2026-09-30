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

/**
 * Create or return the cached better-auth instance.
 *
 * Must be called with the D1 binding on every request (typically in
 * `hooks.server.ts` or the catch-all route handler).
 */
export function getAuth(
	d1: D1Database,
	hostInfo?: ReturnType<typeof getDynamicHostInfo>,
): ReturnType<typeof betterAuth> {
	if (_auth) return _auth as ReturnType<typeof betterAuth>;

	const dialect = new D1Dialect({ database: d1 });

	_auth = betterAuth({
		...hostInfo?.ba,
		database: {
			dialect,
			type: "sqlite" as const,
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
			google: {
				clientId: process.env.GOOGLE_CLIENT_ID ?? "",
				clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
			},
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
 * creation even when registration is closed.
 */
export function withAdminBypass<T>(fn: () => T): T {
	_adminBypassActive = true;
	try {
		return fn();
	} finally {
		_adminBypassActive = false;
	}
}

export type Auth = ReturnType<typeof getAuth>;
