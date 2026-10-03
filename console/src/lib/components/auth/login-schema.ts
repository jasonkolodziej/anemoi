import { type } from "arktype";

/**
 * Magic-link sign-in form schema.
 *
 * Only the magic-link flow has a typed field; passkey and OAuth
 * are button-only actions handled outside the form.
 */
export const loginSchema = type({
	email: "string.email",
});

export type LoginSchema = typeof loginSchema;
