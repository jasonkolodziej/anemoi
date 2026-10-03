/**
 * API-key verification only (#171). This Worker never issues sessions,
 * passkeys, magic links, or OAuth -- that's console's job
 * (console/src/lib/server/auth.ts). Both Workers bind the same D1
 * database (`AUTH_DB`), so a key console issues via its `apiKey` plugin
 * verifies here without a second copy of the data.
 */
import { betterAuth } from 'better-auth';
import { apiKey } from '@better-auth/api-key';

function buildAuth(d1: D1Database) {
	return betterAuth({
		// Raw D1 binding, not a hand-built `{ dialect, type }` via
		// `kysely-d1` -- see console/src/lib/server/auth.ts's `getAuth` for
		// the full explanation. Only this shape makes better-auth's adapter
		// factory auto-detect D1 and set `transaction: false`; the wrapped
		// form left it undefined, and at least one adapter code path opens
		// a `db.transaction()` regardless, which throws against D1 (no
		// interactive transactions) in a way that hangs the request instead
		// of rejecting cleanly. Real correctness fix regardless, though
		// the `validateSchema: false` below turned out to be what
		// actually explains the intermittent "Canceled" hangs -- see its
		// comment in console/src/lib/server/auth.ts (same mechanism, same
		// fix, applies here too since this also goes through better-auth's
		// kysely adapter against the same D1).
		database: d1,
		advanced: {
			database: {
				// See console/src/lib/server/auth.ts's getAuth for the
				// full explanation: better-auth's kysely adapter awaits a
				// real D1-introspection schema check before every
				// "transactional" operation by default, which is slow on
				// a cold isolate and was causing intermittent production
				// hangs. The schema is verified correct, so disabling
				// this removes the tax entirely.
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
let _auth: AppAuth | undefined;

function getAuth(d1: D1Database): AppAuth {
	if (_auth) return _auth;
	_auth = buildAuth(d1);
	return _auth;
}

/**
 * Resolve `X-Anemoi-Api-Key` to a customer's user id, or `null` if the
 * key is missing, unknown, revoked, or expired. Never throws -- an
 * unexpected verification error is treated the same as an invalid key
 * (reject), since the alternative is accidentally letting an anonymous
 * request through on an error.
 */
export async function verifyApiKey(d1: D1Database, key: string | null): Promise<string | null> {
	if (!key) return null;
	try {
		const auth = getAuth(d1);
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
