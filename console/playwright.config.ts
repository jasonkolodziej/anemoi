import { defineConfig, devices } from '@playwright/test';

// Real browser tests against a real running console + a real running
// Anemoi-API demo server -- no mocked fetches. `webServer` starts both:
// the API first (console/src/lib/api/client.ts's BASE_URL already
// defaults to http://127.0.0.1:8000 with zero env setup, see
// .env.example), then a plain `vite dev` -- deliberately NOT `pnpm run
// dev`, which runs `sync-wiki` first and needs a real network clone of
// the wiki repo; these tests never touch /docs, so that's unrelated
// setup cost/flakiness this suite doesn't need.
export default defineConfig({
	testDir: './e2e',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 1 : 0,
	reporter: 'list',
	use: {
		baseURL: 'http://127.0.0.1:5173',
		trace: 'on-first-retry',
	},
	projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
	webServer: [
		{
			command: 'uv run python -m anemoi.api',
			cwd: '..',
			url: 'http://127.0.0.1:8000/v1/health',
			reuseExistingServer: !process.env.CI,
			timeout: 30_000,
		},
		{
			// Explicit PUBLIC_ANEMOI_API_URL, not left to inherit whatever
			// console/.env has locally (a dev machine's .env commonly points
			// at a deployed real-mode API instead of the local demo server --
			// found for real running this suite for the first time: the
			// browser silently fetched the deployed API instead of the local
			// one, which doesn't yet have this issue's new fields, at which
			// point the page crashed on `tags` being undefined instead of
			// missing -- see the optional-chaining fix on the registry page).
			command: 'pnpm exec vite dev --port 5173',
			url: 'http://127.0.0.1:5173',
			reuseExistingServer: !process.env.CI,
			timeout: 30_000,
			env: { PUBLIC_ANEMOI_API_URL: 'http://127.0.0.1:8000' },
		},
	],
});
