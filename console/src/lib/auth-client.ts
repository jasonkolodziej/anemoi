/**
 * better-auth client instance.
 *
 * Provides reactive auth state and methods for the browser:
 * - Passkey sign-in/registration
 * - Magic link sign-in
 * - OAuth social sign-in (GitHub, Google)
 * - API key management
 * - Admin user management (list, ban, create, etc.)
 */

import { passkeyClient } from "@better-auth/passkey/client";
import { apiKeyClient } from "@better-auth/api-key/client";
import {
	adminClient,
	emailOTPClient,
	magicLinkClient,
} from "better-auth/client/plugins";
import { createAuthClient } from "better-auth/svelte";

export const authClient = createAuthClient({
	plugins: [
		passkeyClient(),
		magicLinkClient(),
		emailOTPClient(),
		apiKeyClient(),
		adminClient(),
	],
});
