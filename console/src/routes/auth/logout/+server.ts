import { getAuth } from "$lib/server/auth";
import type { RequestHandler } from "./$types";

/**
 * POST /auth/logout
 *
 * Signs out the user via better-auth (revokes session) and
 * redirects to `/`.
 */
export const POST: RequestHandler = async (event) => {
	const { request, locals } = event;
	const requestId = locals.requestId;
	// Same per-request instance hooks.server.ts already built.
	const auth = getAuth(event);
	if (auth) {
		try {
			console.log(`[logout ${requestId}] calling auth.api.signOut`);
			// Revoke the session using the request cookies
			await auth.api.signOut({
				headers: request.headers,
			});
			console.log(`[logout ${requestId}] signOut resolved`);
		} catch (err) {
			console.error(`[logout ${requestId}] Logout failed:`, err);
		}
	}

	return new Response(null, {
		status: 303,
		headers: {
			Location: "/",
		},
	});
};
