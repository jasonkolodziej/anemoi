import { execFileSync } from 'node:child_process';

/**
 * Prepares the local D1 database (`anemoi_auth`, `wrangler dev`'s local
 * Miniflare copy -- these tests never touch `--remote`/production) for
 * the auth e2e suite:
 *
 * 1. Applies the real migrations (console/schemas/*.sql) -- idempotent
 *    (`CREATE TABLE IF NOT EXISTS`/`INSERT OR IGNORE`), safe to run
 *    against an already-migrated DB, and necessary on a fresh checkout
 *    that's never run `pnpm dev` before (no local D1 state yet).
 * 2. Opens registration -- closed by default (see auth.ts's own comment
 *    on why that's the correct posture), but these tests need to sign up
 *    fresh users via magic link. global-teardown.ts closes it again.
 *
 * Runs via `wrangler d1 execute ... --local`, the same real tool (not a
 * mocked DB layer) used to debug this exact auth flow by hand.
 */
export default async function globalSetup() {
	const run = (args: string[]) =>
		execFileSync('npx', ['wrangler', 'd1', 'execute', 'anemoi_auth', '--local', ...args], {
			cwd: import.meta.dirname + '/..',
			stdio: 'pipe',
		});

	run(['--file=./schemas/better-auth.sql']);
	try {
		run(['--file=./schemas/anemoi.sql']);
	} catch (err) {
		// anemoi.sql's `ALTER TABLE "user" ADD COLUMN "plan"` has no
		// `IF NOT EXISTS` equivalent in SQLite -- fine on a true fresh DB,
		// but re-running this suite locally (D1 state persists across runs)
		// hits it every time after the first. `cycle_runs`/its indexes are
		// already `IF NOT EXISTS`, so this is the only statement in the
		// file that can fail this way -- anything else re-throws.
		if (!String(err).includes('duplicate column name')) throw err;
	}
	run(['--command', "UPDATE registration_policy SET value = 'true' WHERE key = 'open_registration';"]);
}
