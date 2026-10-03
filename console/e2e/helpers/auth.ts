import { readdirSync, statSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { BrowserContext, Page } from '@playwright/test';

const EMAIL_DIR = join(import.meta.dirname, '../../.wrangler/tmp/email');

/**
 * better-auth's `SEND_EMAIL` binding has no real email provider in local
 * dev (console/src/lib/server/email.ts) -- Miniflare's own `send_email`
 * simulator writes each outgoing email to a real HTML file on disk
 * instead, under a per-worker-instance subdirectory. There's no stable
 * "wait for the email to X" event to hook, so this polls for a file that
 * didn't exist in `before` (captured immediately before triggering the
 * send) until one shows up, then pulls the magic-link verify URL out of
 * it -- the same file the recipient's email client would've rendered.
 */
function listEmailFiles(): Set<string> {
	const files = new Set<string>();
	let instanceDirs: string[] = [];
	try {
		instanceDirs = readdirSync(EMAIL_DIR);
	} catch {
		return files; // directory doesn't exist yet -- no emails sent so far
	}
	for (const dir of instanceDirs) {
		const htmlDir = join(EMAIL_DIR, dir, 'email-html');
		try {
			for (const f of readdirSync(htmlDir)) files.add(join(htmlDir, f));
		} catch {
			// this instance dir has no email-html subdir -- skip
		}
	}
	return files;
}

export async function waitForNewEmailLink(before: Set<string>, timeoutMs = 10_000): Promise<string> {
	const deadline = Date.now() + timeoutMs;
	while (Date.now() < deadline) {
		const after = listEmailFiles();
		const newFiles = [...after].filter((f) => !before.has(f));
		if (newFiles.length > 0) {
			// Newest by mtime -- in case a prior test's file lingered and
			// `before` somehow missed it, the just-sent one is always latest.
			newFiles.sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs);
			const html = readFileSync(newFiles[0], 'utf8');
			const match = html.match(/https?:\/\/[^"\s]*\/api\/auth\/magic-link\/verify\?[^"\s]*/);
			if (match) return match[0];
		}
		await new Promise((r) => setTimeout(r, 150));
	}
	throw new Error('Timed out waiting for a magic-link email to appear in .wrangler/tmp/email');
}

export { listEmailFiles };

/**
 * Signs up/in a brand-new user via magic link entirely through the real
 * API (no UI form-filling here -- login-form.spec-level tests cover that
 * surface; this is the fast path other tests build a signed-in session
 * on top of). Leaves the page navigated to `/profile`.
 */
export async function signUpViaMagicLink(page: Page, email: string): Promise<void> {
	const before = listEmailFiles();
	const res = await page.request.post('/api/auth/sign-in/magic-link', {
		data: { email, callbackURL: '/profile' },
	});
	if (!res.ok()) throw new Error(`sign-in/magic-link failed: ${res.status()} ${await res.text()}`);

	const link = await waitForNewEmailLink(before);
	await page.goto(link);
	await page.waitForURL('**/profile');
}

/**
 * Attaches a CDP virtual WebAuthn authenticator to the page's browser
 * context -- this is what lets `navigator.credentials.create()`/`.get()`
 * succeed in a headless/CI browser with no physical device, simulating a
 * person approving their platform's native passkey prompt (Touch ID,
 * Windows Hello, ...). `automaticPresenceSimulation: true` means it
 * auto-approves rather than needing a separate "simulate user presence"
 * call.
 */
export async function addVirtualAuthenticator(context: BrowserContext, page: Page) {
	const cdp = await context.newCDPSession(page);
	await cdp.send('WebAuthn.enable');
	const { authenticatorId } = await cdp.send('WebAuthn.addVirtualAuthenticator', {
		options: {
			protocol: 'ctap2',
			transport: 'internal',
			hasResidentKey: true,
			hasUserVerification: true,
			isUserVerified: true,
			automaticPresenceSimulation: true,
		},
	});
	return { cdp, authenticatorId };
}
