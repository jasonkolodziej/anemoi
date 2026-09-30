import { getAuth } from "$lib/server/auth";
import type { RequestHandler } from "./$types";

/**
 * POST /auth/logout
 *
 * Signs out the user via better-auth (revokes session) and
 * redirects to `/`.
 */
export const POST: RequestHandler = async ({ request, platform }) => {
	const d1 = platform?.env?.AUTH_DB;
	if (d1) {
		try {
			const auth = getAuth(d1);
			// Revoke the session using the request cookies
			await auth.api.signOut({
				headers: request.headers,
			});
		} catch (err) {
			console.error("Logout failed:", err);
		}
	}

	return new Response(null, {
		status: 303,
		headers: {
			Location: "/",
		},
	});
};
