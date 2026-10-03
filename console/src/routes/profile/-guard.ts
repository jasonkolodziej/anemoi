import { redirect } from "@sveltejs/kit";
import type { Guard } from "svelte-guard";

// Runs in hooks.server.ts on every request to /profile (including
// client-side navigation), before any load function -- unlike a load,
// this is re-checked even when SvelteKit wouldn't otherwise rerun one
// (e.g. a session that expired mid-visit, signed out from another tab).
// Replaces the inline `if (!locals.user) redirect(...)` that used to
// live in +page.server.ts.
export const guard: Guard = ({ locals }) => {
	if (!locals.user) {
		redirect(303, "/auth/login");
	}
	return true;
};
