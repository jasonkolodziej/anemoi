import { redirect } from "@sveltejs/kit";
import { safeNext } from "$lib/auth-return";
import type { Guard } from "svelte-guard";

// Already signed in -- nothing to do on the login page itself. There was
// no redirect-away for this before; visiting /auth/login while signed in
// just re-rendered the sign-in form.
export const guard: Guard = ({ locals, url }) => {
	if (locals.user) {
		redirect(303, safeNext(url.searchParams.get("next")));
	}
	return true;
};
