import { test, expect } from '@playwright/test';

// Real, found gap: both the homepage and the storm detail page fetched
// their data exactly once, in onMount, with no refresh -- a tab left open
// (the storm detail page in particular is exactly what someone watching a
// live storm would leave open) silently went stale forever, and the
// homepage's "Today's cycle schedule" kept showing the wrong day's plan
// past UTC midnight since `today` was only ever computed once. Both pages
// now poll every 60s; these tests prove the poll actually fires a real
// second request, using Playwright's virtual clock so this doesn't need
// to wait 60 real seconds.

test('homepage re-fetches storms/schedule/health on a 60s poll', async ({ page }) => {
	let storms = 0;
	page.on('request', (req) => {
		if (req.url().includes('/v1/storms') && !req.url().includes('/cycles')) storms++;
	});

	await page.clock.install({ time: new Date() });
	await page.goto('/');
	await page.waitForSelector('text=Today\'s cycle schedule');
	await page.waitForTimeout(300); // let the initial Promise.all settle
	const initial = storms;
	expect(initial).toBeGreaterThan(0);

	await page.clock.fastForward('01:01'); // past the 60s interval
	await page.waitForTimeout(300);

	expect(storms).toBeGreaterThan(initial);
});

test('storm detail page re-fetches storm/cycle on a 60s poll', async ({ page }) => {
	await page.goto('/');
	await page.waitForSelector('a[href^="/storms/"]');
	const href = await page.locator('a[href^="/storms/"]').first().getAttribute('href');

	let storm = 0;
	page.on('request', (req) => {
		if (req.url().endsWith(href!)) storm++;
	});

	await page.clock.install({ time: new Date() });
	await page.goto(href!);
	await page.waitForSelector('#cycle-input');
	await page.waitForTimeout(300);
	const initial = storm;
	expect(initial).toBeGreaterThan(0);

	await page.clock.fastForward('01:01');
	await page.waitForTimeout(300);

	expect(storm).toBeGreaterThan(initial);
});

test('storm detail poll does not fire while a cycle run is in flight', async ({ page }) => {
	// A poll landing mid-run could clobber the cycle handleRunCycle just
	// produced with a slightly different snapshot -- `load()` must skip
	// itself entirely while `running` is true, not just risk a race.
	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');

	await page.clock.install({ time: new Date() });
	// Hold the run in flight by delaying the POST response.
	await page.route('**/v1/storms/*/cycles', async (route) => {
		await new Promise((r) => setTimeout(r, 2000));
		await route.continue();
	});

	const runButton = page.getByRole('button', { name: /Run cycle/i });
	await runButton.click();
	await expect(page.getByRole('button', { name: 'Running…' })).toBeVisible();

	let getCalls = 0;
	page.on('request', (req) => {
		if (req.method() === 'GET' && /\/v1\/storms\/[^/]+$/.test(new URL(req.url()).pathname)) {
			getCalls++;
		}
	});
	await page.clock.fastForward('01:01'); // the poll interval firing mid-run
	await page.waitForTimeout(200);

	expect(getCalls).toBe(0);
});

test('a hidden tab stops polling, and refreshes as soon as it is visible again', async ({ page }) => {
	// Every request wakes the billed API container and restarts its 5-minute
	// sleep timer, so a forgotten background tab polling every minute would
	// keep it awake indefinitely (#172).
	let storms = 0;
	page.on('request', (req) => {
		if (req.url().includes('/v1/storms') && !req.url().includes('/cycles')) storms++;
	});

	await page.clock.install({ time: new Date() });
	await page.goto('/');
	await page.waitForSelector("text=Today's cycle schedule");
	await page.waitForTimeout(300);

	const setHidden = (hidden: boolean) =>
		page.evaluate((h) => {
			Object.defineProperty(document, 'hidden', { configurable: true, get: () => h });
			document.dispatchEvent(new Event('visibilitychange'));
		}, hidden);

	await setHidden(true);
	const whileHidden = storms;
	await page.clock.fastForward('05:01'); // five poll intervals
	await page.waitForTimeout(300);
	expect(storms).toBe(whileHidden);

	await setHidden(false);
	await page.waitForTimeout(300);
	expect(storms).toBeGreaterThan(whileHidden);
});
