/**
 * Shared auth utilities for route guards and server hooks.
 *
 * Extracted from `hooks.server.ts` so that guard files can import them.
 */

import type { RequestEvent } from "@sveltejs/kit";
import { error } from "better-auth/api";

/**
 * Extract a registry token from all supported sources, in priority order:
 *
 *  1. `x-api-key` request header (standard better-auth API key header)
 *  2. `Authorization: Bearer <token>` request header
 *  3. `?token=<token>` URL query parameter (handy for CLI tools)
 *
 * Returns `null` when no token is present.
 */
export function extractRegistryToken(request: Request): string | null {
	const headers = request.headers;

	// 1. Dedicated API-key header (highest priority)
	const xApiKey = headers.get("x-api-key");
	if (xApiKey) return xApiKey;

	// 2. Authorization: Bearer <token>
	const bearer = extractBearerToken(headers.get("Authorization"));
	if (bearer) return bearer;

	// 3. ?token=<token> query parameter
	try {
		const url = new URL(request.url);
		const qToken = url.searchParams.get("token");
		if (qToken) return qToken;
	} catch {
		// Malformed URL — ignore
	}

	return null;
}

/**
 * Build a `Headers` object that better-auth's `getSession` will accept
 * for API-key-based session resolution.
 *
 * If the original request already carries an `x-api-key` header the
 * headers are returned as-is.  Otherwise we look for an
 * `Authorization: Bearer` token or a `?token=` query parameter and
 * forward it as `x-api-key` so the `apiKey` plugin (with
 * `enableSessionForAPIKeys`) can resolve a session from it.
 *
 * Cookies are always forwarded so cookie-based sessions keep working.
 */
export function buildSessionHeaders(request: Request): Headers {
	const headers = new Headers(request.headers);

	if (!headers.has("x-api-key")) {
		// better-auth's own routes use `?token=` for their own purpose --
		// magic-link verify and email verification both take a `?token=`
		// that means "the thing to verify," nothing to do with an API key.
		// This function used to read `?token=` unconditionally and forward
		// it as `x-api-key`, and since `hooks.server.ts` calls this (via
		// `getSession`) for *every* request including these, a real
		// magic-link verification link turned into a hard 500 ("Invalid
		// API key") before better-auth's own handler ever got to consume
		// its token (reproduced locally: `APIError: Invalid API key.` on
		// `GET /api/auth/magic-link/verify?token=...`). Skip the
		// query-param fallback specifically for better-auth's own
		// basePath; `Authorization: Bearer` still works there if a caller
		// genuinely needs bearer auth against it.
		const url = new URL(request.url);
		const token =
			extractBearerToken(headers.get("Authorization")) ??
			(url.pathname.startsWith("/api/auth/") ? null : safeQueryParam(request.url, "token"));

		if (token) {
			headers.set("x-api-key", token);
		}
	}

	return headers;
}

// ── Low-level helpers ────────────────────────────────────────────────────────

/** Extract a bearer token from the `Authorization` header. */
export function extractBearerToken(authHeader: string | null): string | null {
	if (!authHeader?.startsWith("Bearer ")) return null;
	return authHeader.slice(7);
}

/** Safely read a URL search parameter (returns `null` on malformed URLs). */
function safeQueryParam(url: string, param: string): string | null {
	try {
		return new URL(url).searchParams.get(param);
	} catch {
		return null;
	}
}

/**
 * Check if the user is authenticated and has the required role.
 *
 * @param event - The request event.
 * @param role - The required role.
 * @returns The authentication status, user, and role.
 */
export function checkAuth(event: RequestEvent): {
	session: boolean;
	user: boolean;
	role?: string | null;
} {
	return {
		session: Boolean(event.locals.session),
		user: Boolean(event.locals.user),
		role: event.locals.user?.role,
	};
}
