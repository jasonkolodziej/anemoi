import { test, expect } from '@playwright/test';
import {
	signUpViaMagicLink,
	addVirtualAuthenticator,
	listEmailFiles,
	waitForNewEmailLink,
	localD1,
	setRegistrationOpen,
} from './helpers/auth';

// Real coverage for the login/logout/passkey flows added by #171 and
// #201 -- these would have caught both of the real bugs found debugging
// a live "no passkey prompt, sign-out does nothing" report:
//
// 1. auth.ts configured D1 via a hand-built `{ dialect, type }` wrapper
//    instead of passing the raw binding, which left better-auth's
//    adapter unaware D1 has no interactive transactions -- signOut and
//    passkey registration both hung (Cloudflare eventually killed the
//    request) instead of erroring, because the thrown
//    "transactions not supported" error never reached a catch block as a
//    clean rejection.
// 2. buildSessionHeaders (auth-utils.ts) read any `?token=` query param
//    as an API key, including better-auth's own `?token=` on magic-link
//    verify links -- turning every real magic-link sign-in into a hard
//    500 before better-auth's handler ever consumed its own token.
//
// Runs serially (shared local email-fallback directory + shared D1 --
// see helpers/auth.ts and global-setup.ts) while other spec files still
// run in parallel with this one.
test.describe.configure({ mode: 'serial' });

function freshEmail(label: string): string {
	return `e2e-${label}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
}

test('magic-link sign-up lands on /profile with the right identity', async ({ page }) => {
	const email = freshEmail('magic-link');
	await signUpViaMagicLink(page, email);

	await expect(page.getByText(email)).toBeVisible();
	await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible();
});

test('sign out actually revokes the session, not just the client-side view', async ({ page }) => {
	const email = freshEmail('signout');
	await signUpViaMagicLink(page, email);

	await page.getByRole('button', { name: 'Sign out' }).click();
	await page.waitForURL('**/');

	// The real regression: production showed "Canceled" for this request
	// and the user stayed signed in no matter how many times they clicked.
	// Checking the server's own view of the session (not just where the
	// browser ended up) is what actually proves it was revoked.
	const res = await page.request.get('/api/auth/get-session');
	expect(await res.json()).toBeNull();
});

test('add a passkey via a real WebAuthn ceremony, then remove it', async ({ page, context }) => {
	const email = freshEmail('passkey-add');
	await signUpViaMagicLink(page, email);
	await addVirtualAuthenticator(context, page);

	await expect(page.getByText('No passkeys yet.')).toBeVisible();

	await page.getByRole('button', { name: 'Add a passkey' }).click();
	// The real regression: this never got past "Follow your browser's
	// prompt..." because the options fetch that must resolve before
	// `navigator.credentials.create()` is even called hung forever. A
	// generous timeout here is the point -- a hang should fail loudly,
	// not pass by accident.
	await expect(page.getByRole('button', { name: 'Add a passkey' })).toBeVisible({ timeout: 15_000 });

	await expect(page.getByText('No passkeys yet.')).toHaveCount(0);
	await expect(page.getByText('(singleDevice)')).toBeVisible();

	await page.getByRole('button', { name: 'Remove' }).click();
	await expect(page.getByText('No passkeys yet.')).toBeVisible();
});

test('sign in with a previously-added passkey', async ({ page, context }) => {
	const email = freshEmail('passkey-signin');
	await signUpViaMagicLink(page, email);
	await addVirtualAuthenticator(context, page);

	await page.getByRole('button', { name: 'Add a passkey' }).click();
	await expect(page.getByText('(singleDevice)')).toBeVisible({ timeout: 15_000 });

	await page.getByRole('button', { name: 'Sign out' }).click();
	await page.waitForURL('**/');

	await page.goto('/auth/login');
	await page.getByRole('button', { name: 'Sign in with Passkey' }).click();

	// The passkey ceremony round-trips back to /profile under the same
	// identity -- the reciprocal of the add-passkey test above, and the
	// one direction that was already confirmed working before the D1 fix
	// (sign-in uses a different, non-transactional endpoint than
	// registration does), so this also guards against that asymmetry
	// regressing.
	await page.waitForURL('**/profile');
	await expect(page.getByText(email)).toBeVisible();
});

test('profile redirects an anonymous visitor to sign in', async ({ page }) => {
	await page.goto('/profile');
	await page.waitForURL('**/auth/login');
});

test('login redirects an already-signed-in visitor to their profile', async ({ page }) => {
	const email = freshEmail('login-guard');
	await signUpViaMagicLink(page, email);

	await page.goto('/auth/login');
	await page.waitForURL('**/profile');
	await expect(page.getByText(email)).toBeVisible();
});

// ── Shared-instance hang (getAuth in src/lib/server/auth.ts) ──────────────
// The real production bug behind "Passkeys: Loading..." / a stuck "Follow
// your browser's prompt..." / sign-out doing nothing: `api-key/list` left a
// fire-and-forget DELETE holding Kysely's connection mutex on an auth
// instance shared by every request, and on workerd that DELETE never
// settles, so every later D1 query hung. Only `pnpm test:e2e:workerd`
// (the built Worker on workerd) can reproduce it -- under `vite dev`'s
// Node runtime these pass either way -- but they're cheap enough to run
// in both. Short per-request timeouts on purpose: a hang must fail fast
// and say which call hung, not ride the 30s test timeout.

const QUICK = { timeout: 5_000 };

test('api-key list then passkey list, repeatedly, never wedges later requests', async ({ page }) => {
	const email = freshEmail('wedge');
	await signUpViaMagicLink(page, email);

	// The exact order the profile page issues them in, several rounds so a
	// leaked lock from round N shows up in round N+1.
	for (let round = 0; round < 3; round++) {
		const keys = await page.request.get('/api/auth/api-key/list', QUICK);
		expect(keys.status(), `api-key/list, round ${round}`).toBe(200);
		const passkeys = await page.request.get('/api/auth/passkey/list-user-passkeys', QUICK);
		expect(passkeys.status(), `passkey/list-user-passkeys, round ${round}`).toBe(200);
	}

	// The first D1 write of a passkey registration, and sign-out's session
	// delete -- the other two calls that hung in production.
	const options = await page.request.get('/api/auth/passkey/generate-register-options', QUICK);
	expect(options.status(), 'passkey/generate-register-options').toBe(200);

	const signOut = await page.request.post('/auth/logout', { ...QUICK, maxRedirects: 0 });
	expect(signOut.status(), 'POST /auth/logout').toBe(303);
	const session = await page.request.get('/api/auth/get-session', QUICK);
	expect(await session.json()).toBeNull();
});

test('profile: create an API key, add a passkey, then sign out, all on one page', async ({ page, context }) => {
	const email = freshEmail('profile-flow');
	await signUpViaMagicLink(page, email);
	await addVirtualAuthenticator(context, page);

	// Passkey list must finish loading after the page's own api-key list.
	await expect(page.getByText('No passkeys yet.')).toBeVisible(QUICK);

	// api-key create also fires the background expired-key DELETE.
	await page.getByRole('button', { name: 'Generate new key' }).click();
	await expect(page.getByText("Copy this key now -- it won't be shown again.")).toBeVisible(QUICK);

	await page.getByRole('button', { name: 'Add a passkey' }).click();
	await expect(page.getByText('(singleDevice)')).toBeVisible({ timeout: 15_000 });

	await page.getByRole('button', { name: 'Sign out' }).click();
	await page.waitForURL('**/', QUICK);
	const session = await page.request.get('/api/auth/get-session', QUICK);
	expect(await session.json()).toBeNull();
});

test('sign out revokes the session row itself, not just the cookies', async ({ page, browser }) => {
	const email = freshEmail('revoke');
	await signUpViaMagicLink(page, email);

	// Replay the pre-logout session token without the signed cookie cache
	// (better-auth.session_data) in a separate context: if signOut only
	// cleared cookies but left the D1 session row, this would still be a
	// valid session for up to the session's full lifetime.
	const token = (await page.context().cookies()).find((c) => c.name === 'better-auth.session_token');
	expect(token, 'session token cookie after sign-in').toBeTruthy();

	await page.getByRole('button', { name: 'Sign out' }).click();
	await page.waitForURL('**/', QUICK);

	const replay = await browser.newContext();
	try {
		await replay.addCookies([{ ...token! }]);
		const res = await replay.request.get(new URL('/api/auth/get-session', page.url()).toString(), QUICK);
		expect(await res.json()).toBeNull();
	} finally {
		await replay.close();
	}
});

test("better-auth's schema check passes against schemas/*.sql", async ({ page }) => {
	// Under `pnpm test:e2e:workerd`, BETTER_AUTH_VALIDATE_SCHEMA=true makes
	// every transactional better-auth call first diff the live local D1
	// (built from schemas/*.sql by global-setup.ts) against what the
	// installed plugins write; a mismatch throws SchemaMismatchError and
	// the call 500s with the missing table/column named in the server log.
	// The check diffs every table at once, so any transactional call trips
	// it; these just make the test's intent explicit rather than relying
	// on the other tests failing with a less obvious error.
	const email = freshEmail('schema');
	await signUpViaMagicLink(page, email);

	// Origin header: better-auth's CSRF check rejects a cookie-authenticated
	// POST without one (the browser would send it; page.request doesn't).
	const created = await page.request.post('/api/auth/api-key/create', {
		...QUICK,
		headers: { origin: new URL(page.url()).origin },
		data: { name: 'schema-check' },
	});
	expect(created.status(), await created.text()).toBe(200);
	const passkeys = await page.request.get('/api/auth/passkey/list-user-passkeys', QUICK);
	expect(passkeys.status(), await passkeys.text()).toBe(200);
});

// ── Registration policy + admin bypass (auth.ts databaseHooks) ────────────
// The bypass used to be a module-level flag, which isn't request-scoped on
// Workers (one isolate serves concurrent requests) and was never actually
// set by anything -- so an admin's `/admin/create-user` was rejected too
// whenever registration was closed. It's now keyed off the endpoint path.

test.describe('with registration closed', () => {
	test.beforeAll(() => setRegistrationOpen(false));
	test.afterAll(() => setRegistrationOpen(true));

	test('a new magic-link sign-up is rejected', async ({ page }) => {
		const email = freshEmail('closed-signup');
		const before = listEmailFiles();
		const res = await page.request.post('/api/auth/sign-in/magic-link', {
			...QUICK,
			data: { email, callbackURL: '/profile' },
		});
		expect(res.ok()).toBe(true); // sending the link is fine...
		await page.goto(await waitForNewEmailLink(before));
		// ...but verifying it must not create the user or a session.
		const session = await page.request.get('/api/auth/get-session', QUICK);
		expect(await session.json()).toBeNull();
	});

	test('an admin can still create a user; a non-admin cannot', async ({ page, browser }) => {
		// The admin signs up while registration is open, is promoted in D1,
		// then signs in again so the session (and its cookie cache) carries
		// the new role.
		const adminEmail = freshEmail('admin');
		setRegistrationOpen(true);
		await signUpViaMagicLink(page, adminEmail);
		const plainEmail = freshEmail('not-admin');
		const plain = await browser.newContext({ baseURL: new URL(page.url()).origin });
		const plainPage = await plain.newPage();
		await signUpViaMagicLink(plainPage, plainEmail);
		setRegistrationOpen(false);
		localD1(`UPDATE "user" SET role = 'admin' WHERE email = '${adminEmail}';`);
		await page.context().clearCookies();
		await signUpViaMagicLink(page, adminEmail);

		const headers = { origin: new URL(page.url()).origin };
		const target = freshEmail('admin-created');
		const created = await page.request.post('/api/auth/admin/create-user', {
			...QUICK,
			headers,
			data: { email: target, name: 'Admin Created', password: 'not-used-0123456789' },
		});
		expect(created.status(), await created.text()).toBe(200);
		expect((await created.json()).user.email).toBe(target);

		try {
			const denied = await plainPage.request.post('/api/auth/admin/create-user', {
				...QUICK,
				headers,
				data: { email: freshEmail('should-not-exist'), name: 'Nope', password: 'not-used-0123456789' },
			});
			expect(denied.status()).toBe(403);
		} finally {
			await plain.close();
		}
	});
});
