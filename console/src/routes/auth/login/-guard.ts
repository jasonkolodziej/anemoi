import { redirect } from "@sveltejs/kit";
import type { Guard } from "svelte-guard";

// Already signed in -- nothing to do on the login page itself. There was
// no redirect-away for this before; visiting /auth/login while signed in
// just re-rendered the sign-in form.
export const guard: Guard = ({ locals }) => {
	if (locals.user) {
		redirect(303, "/profile");
	}
	return true;
};
