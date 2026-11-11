import { execFileSync } from 'node:child_process';

/**
 * Prepares the local D1 database (`anemoi_auth`, `wrangler dev`'s local
 * Miniflare copy -- these tests never touch `--remote`/production) for
 * the auth e2e suite:
 *
 * 1. Applies console/migrations/ with the same `wrangler d1 migrations
 *    apply` the deploy workflow runs against production -- only the ones
 *    this local DB hasn't recorded yet, so it's safe on every run and
 *    builds the full schema on a fresh checkout or CI runner.
 * 2. Opens registration -- closed by default (see auth.ts's own comment
 *    on why that's the correct posture), but these tests need to sign up
 *    fresh users via magic link. global-teardown.ts closes it again.
 */
export default async function globalSetup() {
	const wrangler = (args: string[]) =>
		execFileSync('npx', ['wrangler', 'd1', ...args], {
			cwd: import.meta.dirname + '/..',
			// Non-TTY stdio is also what makes `migrations apply` skip its
			// interactive "apply N migrations?" confirmation.
			stdio: 'pipe',
		});

	wrangler(['migrations', 'apply', 'anemoi_auth', '--local']);
	wrangler([
		'execute',
		'anemoi_auth',
		'--local',
		'--command',
		"UPDATE registration_policy SET value = 'true' WHERE key = 'open_registration';",
	]);
}
