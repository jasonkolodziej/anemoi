import type { Page } from '@playwright/test';
import { signUpViaMagicLink } from './auth';

/**
 * Running a cycle needs an account (#171): an anonymous "Run cycle" goes to
 * the sign-in page. Specs that run one sign a fresh user in first, the way
 * a forecaster would.
 */
export async function signIn(page: Page): Promise<void> {
	const tag = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
	await signUpViaMagicLink(page, `e2e-${tag}@example.com`);
}

function label(t: number): string {
	const d = new Date(t);
	const pad = (n: number) => String(n).padStart(2, '0');
	return `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}_${pad(d.getUTCHours())}Z`;
}

/**
 * A synoptic cycle label the open storm has no cycle for. The run form
 * refuses one it already has ("has already run -- View it"), and the demo
 * API keeps every cycle any earlier test ran for as long as it's up, so a
 * fixed label only works once. Random over 2020-2024 so tests running in
 * parallel on the same storm don't pick the same one.
 */
export async function freeCycleLabel(page: Page, exclude: string[] = []): Promise<string> {
	const stormId = new URL(page.url()).pathname.split('/').pop()!;
	const storm = await (await page.request.get(`/api/v1/storms/${stormId}`)).json();
	const have = new Set<string>([...storm.cycles, ...exclude]);
	const start = Date.UTC(2020, 0, 1);
	for (;;) {
		const candidate = label(start + Math.floor(Math.random() * 5 * 365 * 4) * 6 * 3_600_000);
		if (!have.has(candidate)) return candidate;
	}
}

/** Runs a cycle from the open storm page's form -- `cycle`, else one the
 * storm doesn't have yet -- and waits for the API's answer. */
export async function runFreshCycle(page: Page, cycle?: string): Promise<string> {
	const target = cycle ?? (await freeCycleLabel(page));
	await page.locator('#cycle-input').fill(target);
	const answered = page.waitForResponse(
		(r) => r.request().method() === 'POST' && new URL(r.url()).pathname.endsWith('/cycles'),
	);
	await page.getByRole('button', { name: 'Run cycle' }).click();
	await answered;
	return target;
}
