import { execFileSync } from 'node:child_process';
import { closeSync, openSync, readdirSync, readFileSync, statSync, unlinkSync } from 'node:fs';
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

const EMAIL_LOCK = join(EMAIL_DIR, '..', 'e2e-email.lock');
const STALE_LOCK_MS = 30_000;

/**
 * Runs `fn` -- trigger one email, then read it with `waitForNewEmailLink`
 * -- while no other worker does the same. The simulator's files don't name
 * their recipient, so "the newest new file" is only this worker's email if
 * nobody else sent one meanwhile: with specs signing in in parallel, a
 * worker otherwise followed another's magic link and signed in as them.
 * A lock file shared by every worker; one older than `STALE_LOCK_MS` (a
 * worker killed holding it) is taken over.
 */
export async function withEmailLock<T>(fn: () => Promise<T>): Promise<T> {
	const deadline = Date.now() + 60_000;
	for (;;) {
		try {
			closeSync(openSync(EMAIL_LOCK, 'wx'));
			break;
		} catch (err) {
			if ((err as NodeJS.ErrnoException).code !== 'EEXIST') throw err;
			try {
				if (Date.now() - statSync(EMAIL_LOCK).mtimeMs > STALE_LOCK_MS) unlinkSync(EMAIL_LOCK);
			} catch {
				/* released between the two calls -- just retry */
			}
			if (Date.now() > deadline) throw new Error(`Timed out waiting for ${EMAIL_LOCK}`);
			await new Promise((r) => setTimeout(r, 50));
		}
	}
	try {
		return await fn();
	} finally {
		try {
			unlinkSync(EMAIL_LOCK);
		} catch {
			/* taken over as stale -- nothing to release */
		}
	}
}

/**
 * Signs up/in a brand-new user via magic link entirely through the real
 * API (no UI form-filling here -- login-form.spec-level tests cover that
 * surface; this is the fast path other tests build a signed-in session
 * on top of). Leaves the page navigated to `/profile`.
 */
export async function signUpViaMagicLink(page: Page, email: string): Promise<void> {
	const link = await withEmailLock(async () => {
		const before = listEmailFiles();
		const res = await page.request.post('/api/auth/sign-in/magic-link', {
			data: { email, callbackURL: '/profile' },
		});
		if (!res.ok()) throw new Error(`sign-in/magic-link failed: ${res.status()} ${await res.text()}`);
		return waitForNewEmailLink(before);
	});
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

/**
 * Runs SQL against the same local D1 (`anemoi_auth`, Miniflare state) the
 * dev server under test reads -- the same tool global-setup.ts uses.
 */
export function localD1(sql: string): void {
	execFileSync('npx', ['wrangler', 'd1', 'execute', 'anemoi_auth', '--local', '--command', sql], {
		cwd: join(import.meta.dirname, '../..'),
		stdio: 'pipe',
	});
}

export function setRegistrationOpen(open: boolean): void {
	localD1(`UPDATE registration_policy SET value = '${open}' WHERE key = 'open_registration';`);
}
