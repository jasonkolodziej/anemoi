import type { RequestEvent } from "@sveltejs/kit";
import type { BetterAuthOptions } from "better-auth";

/**
 * Dynamic host information for better-auth.
 *
 * This is used to build the baseURL and trustedOrigins for better-auth.
 * It is dynamic because it needs to be different for local development
 * and production.
 */
export type DynamicHostInfo = {
	ba: Pick<BetterAuthOptions, "baseURL" | "trustedOrigins">;
	rpId: string;
};

/**
 * Get the dynamic host information for better-auth.
 *
 * This is used to build the baseURL and trustedOrigins for better-auth.
 * It is dynamic because it needs to be different for local development
 * and production.
 */
export function getDynamicHostInfo(event: RequestEvent): DynamicHostInfo {
	const _url = new URL(event.request.url);

	// Derive the rpId from the request hostname when no explicit override is set.
	// WebAuthn requires rpId to be a registrable suffix of the page's effective
	// domain, so we always derive it from the actual request host.
	// - `vite dev` / `pnpm preview` / `pnpm preview:remote` → "localhost"
	// - production (wrangler deploy) → "anemoi.systems"
	// Passkeys are scoped to their registration rpId, so a passkey registered on
	// "anemoi.systems" cannot be used on "localhost" and vice versa.
	const rpId = process.env.RP_ID ?? _url.hostname;

	if (import.meta.env.DEV) {
		// `vite dev` or `vite build --mode=development` (pnpm preview / preview:remote)
		const localBase = `${_url.protocol}//${_url.host}`;
		return {
			ba: {
				baseURL: localBase,
				trustedOrigins: [localBase],
			},
			rpId,
		};
	}

	// Production build served by `wrangler deploy`.
	return {
		ba: {
			baseURL: process.env.BETTER_AUTH_BASE_URL ?? "https://anemoi.systems",
			trustedOrigins: [
				process.env.BETTER_AUTH_BASE_URL ?? "https://anemoi.systems",
			],
		},
		rpId,
	};
}
