/**
 * API-key verification only (#171). This Worker never issues sessions,
 * passkeys, magic links, or OAuth -- that's console's job
 * (console/src/lib/server/auth.ts). Both Workers bind the same D1
 * database (`AUTH_DB`), so a key console issues via its `apiKey` plugin
 * verifies here without a second copy of the data.
 */
import { betterAuth } from 'better-auth';
import { apiKey } from '@better-auth/api-key';

function buildAuth(d1: D1Database, ctx: ExecutionContext) {
	return betterAuth({
		// Raw D1 binding, not a hand-built `{ dialect, type }` via
		// `kysely-d1` -- see console/src/lib/server/auth.ts's `buildAuth`
		// for the full explanation. Only this shape makes better-auth's adapter
		// factory auto-detect D1 and set `transaction: false`; the wrapped
		// form left it undefined, and at least one adapter code path opens
		// a `db.transaction()` regardless, which throws against D1 (no
		// interactive transactions) in a way that hangs the request instead
		// of rejecting cleanly.
		database: d1,
		advanced: {
			// better-auth's documented Workers setup: `runInBackground`
			// work goes to `waitUntil` instead of a floating promise the
			// runtime drops once the response is sent.
			backgroundTasks: { handler: (p) => ctx.waitUntil(p) },
			database: {
				// See console/src/lib/server/auth.ts -- skips a per-
				// instance PRAGMA introspection that, with a per-request
				// instance, would otherwise run on every request.
				validateSchema: false,
			},
		},
		plugins: [apiKey({ enableSessionForAPIKeys: true })],
	});
}

// `ReturnType<typeof buildAuth>` (not `typeof betterAuth` directly) so
// this stays the concrete type with the apiKey plugin's endpoints
// (`auth.api.verifyApiKey`) -- `betterAuth` itself is generic, so
// `ReturnType<typeof betterAuth>` alone collapses to the base
// `Auth<BetterAuthOptions>` and loses every plugin-specific method.
type AppAuth = ReturnType<typeof buildAuth>;

// No module-level cache, deliberately: a shared instance means one shared
// Kysely `ConnectionMutex` (SQLite dialects serialize every query), and
// `@better-auth/api-key` fires some of its expired-key cleanup without
// awaiting it. Once a request's response is sent Workers never resumes
// that leftover query, the mutex is never released, and every later
// query on the isolate hangs -- see console/src/lib/server/auth.ts's
// getAuth for the full write-up. Construction is a few ms, no I/O.
function getAuth(d1: D1Database, ctx: ExecutionContext): AppAuth {
	return buildAuth(d1, ctx);
}

/**
 * Resolve `X-Anemoi-Api-Key` to a customer's user id, or `null` if the
 * key is missing, unknown, revoked, or expired. Never throws -- an
 * unexpected verification error is treated the same as an invalid key
 * (reject), since the alternative is accidentally letting an anonymous
 * request through on an error.
 */
export async function verifyApiKey(
	d1: D1Database,
	ctx: ExecutionContext,
	key: string | null,
): Promise<string | null> {
	if (!key) return null;
	try {
		const auth = getAuth(d1, ctx);
		const result = await auth.api.verifyApiKey({ body: { key } });
		if (!result.valid || !result.key) return null;
		// `referenceId`, not `userId` -- the field this plugin version (1.7.7)
		// actually ships (confirmed against node_modules/@better-auth/api-key's
		// own ApiKey type; console/schemas/better-auth.sql's ported `userId`
		// column name was stale). Defaults to the owning user's id unless the
		// plugin is configured with `references: "organization"`, which it
		// isn't here.
		return result.key.referenceId;
	} catch (err) {
		console.error('verifyApiKey threw:', err);
		return null;
	}
}
