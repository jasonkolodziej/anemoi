import type { PageServerLoad } from "./$types";

// Access control itself lives in ./-guard.ts (svelte-guard, runs in
// hooks.server.ts before any load) -- by the time this runs, an
// anonymous request has already been redirected to /auth/login, so
// `locals.user` is guaranteed non-null here.
export const load: PageServerLoad = ({ locals }) => {
	return { user: locals.user! };
};
