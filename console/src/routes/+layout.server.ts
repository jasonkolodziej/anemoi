import type { LayoutServerLoad } from "./$types";

// Hands every page `locals.user` (hydrated in hooks.server.ts) so the top
// nav can show "Sign in" vs. the signed-in user without each route having
// to load it separately -- same pattern as storms/[stormId]/+page.server.ts.
export const load: LayoutServerLoad = ({ locals }) => {
	return { user: locals.user };
};
