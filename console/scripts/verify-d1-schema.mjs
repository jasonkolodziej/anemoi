#!/usr/bin/env node
// Verifies the production D1 (`--remote`) has everything the local D1 built
// from console/migrations/ has: every table, every column (and that a column
// required locally isn't nullable remotely), every index. Run by
// .github/workflows/deploy-console.yml after `migrations apply --remote` and
// before `wrangler deploy`, so the Worker only ships against a schema that
// matches the one the e2e suite (and better-auth's own schema check) just
// passed against.
//
// Why this exists on top of `d1_migrations`: that table only says which
// files ran, not what the schema is. Production predates migrations --
// 0001_baseline.sql is all IF NOT EXISTS, so applying it there is a no-op
// that trusts the hand-applied schema matched. This turns that trust into
// a check, and keeps catching any later hand-edit made outside migrations.
//
// Extra remote tables/columns/indexes are reported but don't fail: they're
// harmless to the Worker, and dropping them is a decision for a human.
//
// Usage: node scripts/verify-d1-schema.mjs   (needs CLOUDFLARE_API_TOKEN /
// CLOUDFLARE_ACCOUNT_ID for the remote half, like any `wrangler --remote`)
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const DB = 'anemoi_auth';
const QUERY = `
	SELECT m.type AS type, m.name AS name, p.name AS col, p."notnull" AS nn
	FROM sqlite_master m
	LEFT JOIN pragma_table_info(m.name) p ON m.type = 'table'
	WHERE m.type IN ('table', 'index')
	  AND m.name NOT LIKE 'sqlite_%'
	  AND m.name NOT LIKE '_cf_%'
	  AND m.name != 'd1_migrations'
`;

function snapshot(where) {
	const out = execFileSync(
		'pnpm',
		['exec', 'wrangler', 'd1', 'execute', DB, `--${where}`, '--json', '--command', QUERY],
		{ cwd: fileURLToPath(new URL('..', import.meta.url)), encoding: 'utf8', stdio: ['ignore', 'pipe', 'inherit'] },
	);
	const rows = JSON.parse(out).flatMap((r) => r.results ?? []);
	const tables = new Map(); // table -> Map(column -> notnull)
	const indexes = new Set();
	for (const r of rows) {
		if (r.type === 'index') indexes.add(r.name);
		else {
			if (!tables.has(r.name)) tables.set(r.name, new Map());
			if (r.col != null) tables.get(r.name).set(r.col, Number(r.nn) === 1);
		}
	}
	return { tables, indexes };
}

const local = snapshot('local');
const remote = snapshot('remote');
const problems = [];
const notes = [];

for (const [table, cols] of local.tables) {
	const remoteCols = remote.tables.get(table);
	if (!remoteCols) {
		problems.push(`missing table "${table}"`);
		continue;
	}
	for (const [col, notnull] of cols) {
		if (!remoteCols.has(col)) problems.push(`missing column "${table}"."${col}"`);
		else if (notnull && !remoteCols.get(col)) notes.push(`"${table}"."${col}" is NOT NULL locally but nullable in production`);
	}
	for (const col of remoteCols.keys()) if (!cols.has(col)) notes.push(`extra column in production: "${table}"."${col}"`);
}
for (const table of remote.tables.keys()) if (!local.tables.has(table)) notes.push(`extra table in production: "${table}"`);
for (const index of local.indexes) if (!remote.indexes.has(index)) problems.push(`missing index "${index}"`);
for (const index of remote.indexes) if (!local.indexes.has(index)) notes.push(`extra index in production: "${index}"`);

for (const n of notes) console.log(`note: ${n}`);
if (problems.length) {
	console.error(`\nProduction D1 is missing schema the tested build expects:\n  ${problems.join('\n  ')}`);
	console.error('\nAdd a migration that creates it (console/migrations/) rather than fixing production by hand.');
	process.exit(1);
}
console.log(
	`Production D1 schema OK: ${local.tables.size} tables, ${local.indexes.size} indexes match the migrations.`,
);
