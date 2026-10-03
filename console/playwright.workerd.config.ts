import { defineConfig, devices } from '@playwright/test';

// The auth suite again, but against the *built* Worker under `wrangler
// dev` (workerd) instead of `vite dev` (Node). The sign-out/passkey hang
// fixed in src/lib/server/auth.ts's getAuth only exists on the Workers
// runtime -- Node happily resumes a request's leftover background query
// after the response is sent, workerd never does -- so the default
// config's suite passed the whole time production was hanging.
//
// Needs a prior `pnpm build`. `--local-upstream` keeps the request host
// `localhost` (wrangler dev otherwise rewrites it to wrangler.jsonc's
// route, anemoi.systems) so baseURL/rpId/WebAuthn's secure-context check
// all line up with the browser's origin. `/api/v1/*` 500s in the server
// log are expected: the anemoi-api-real service binding isn't running.
export default defineConfig({
	testDir: './e2e',
	testMatch: 'auth.spec.ts',
	reporter: 'list',
	globalSetup: './e2e/global-setup.ts',
	globalTeardown: './e2e/global-teardown.ts',
	use: { baseURL: 'http://localhost:8787', trace: 'retain-on-failure' },
	projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
	webServer: {
		command:
			'pnpm exec wrangler dev --port 8787 --local-upstream localhost:8787' +
			' --var BETTER_AUTH_BASE_URL:http://localhost:8787' +
			' --var BETTER_AUTH_SECRET:e2e-only-not-a-real-secret-0123456789' +
			' --var OPEN_REGISTRATION:true',
		url: 'http://localhost:8787/api/auth/ok',
		reuseExistingServer: false,
		timeout: 60_000,
	},
});
