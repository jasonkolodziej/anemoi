import { getAuth } from "$lib/server/auth";
import { getDynamicHostInfo } from "$lib/server/hosting";
import type { RequestHandler } from "./$types";

/**
 * POST /auth/logout
 *
 * Signs out the user via better-auth (revokes session) and
 * redirects to `/`.
 */
export const POST: RequestHandler = async (event) => {
	const { request, platform } = event;
	const d1 = platform?.env?.AUTH_DB;
	if (d1) {
		try {
			// hostInfo passed explicitly (not `getAuth(d1)` alone): if this
			// is the first call to hit a fresh isolate, an omitted hostInfo
			// would otherwise cache an instance with no baseURL/rpId for
			// every request after it (Copilot review, PR #197; see
			// getAuth's own comment on why the cache is keyed by baseURL).
			const auth = getAuth(d1, getDynamicHostInfo(event));
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
