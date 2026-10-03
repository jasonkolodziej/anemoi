import { execFileSync } from 'node:child_process';

/**
 * Restores the local D1 registration policy to its real default (closed)
 * after the auth e2e suite -- see global-setup.ts. Local-only; never
 * touches `--remote`/production.
 */
export default async function globalTeardown() {
	execFileSync(
		'npx',
		[
			'wrangler',
			'd1',
			'execute',
			'anemoi_auth',
			'--local',
			'--command',
			"UPDATE registration_policy SET value = 'false' WHERE key = 'open_registration';",
		],
		{ cwd: import.meta.dirname + '/..', stdio: 'pipe' },
	);
}
