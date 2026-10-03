import { redirect } from "@sveltejs/kit";
import type { Guard } from "svelte-guard";

// Same as auth/login/-guard.ts -- already signed in, no reason to see the
// registration form.
export const guard: Guard = ({ locals }) => {
	if (locals.user) {
		redirect(303, "/profile");
	}
	return true;
};
