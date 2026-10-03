import { test, expect } from '@playwright/test';
import { signUpViaMagicLink, addVirtualAuthenticator } from './helpers/auth';

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
