import { superValidate } from "sveltekit-superforms";
import { arktype } from "sveltekit-superforms/adapters";
import type { PageServerLoad } from "./$types";
import { loginSchema } from "./schema";

export const load: PageServerLoad = async () => {
	const form = await superValidate(arktype(loginSchema));
	return { form };
};
