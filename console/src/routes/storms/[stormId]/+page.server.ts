import type { PageServerLoad } from "./$types";

// Reads (viewing a storm's forecast) stay open to anyone -- only the
// "Run cycle" action (routes/api/[...path]/+server.ts's proxy, gated on
// a session) needs a logged-in user, per #171's own framing. This load
// just hands the page `locals.user` so the button can check it and send
// an anonymous visitor to `/auth/login` instead of failing with a 401
// after a real click.
export const load: PageServerLoad = ({ locals }) => {
	return { user: locals.user };
};
