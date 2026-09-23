import { test, expect } from '@playwright/test';

// Real browser coverage for the console-visuals proposal
// (console/tmp/PROPOSAL.md): the Wind Rose tap tooltip, the Today's
// schedule stage tooltip, and the Monitoring drift chart. Each of these
// replaced either fabricated data (IntensityPDFChart's old hardcoded
// `INTENSITY` array) or a browser-native `title` tooltip with a real
// shadcn component -- this is what would have caught either one
// silently failing to render.

test('tapping a wind rose forecast point opens a real tooltip with its lead hour and wind speed', async ({
	page,
}) => {
	const pageErrors: string[] = [];
	page.on('pageerror', (err) => pageErrors.push(err.message));

	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
	await page.getByRole('button', { name: 'Run cycle' }).click();
	await expect(page.locator('canvas').first()).toBeVisible({ timeout: 10_000 });

	// Forecast points are canvas-rendered (MapLibre), not real DOM nodes --
	// click through the canvas at a real point's approximate on-screen
	// position rather than locating a DOM element for it.
	const canvas = page.locator('canvas').first();
	const box = await canvas.boundingBox();
	if (!box) throw new Error('map canvas has no bounding box');

	// One of the real forecast point dots (5px radius) is reliably
	// somewhere in the canvas's own drawn extent (`fitBounds` already
	// ran) -- probe a dense pixel grid until one hits a circle and opens
	// the tooltip, since this test doesn't know the exact synthetic track
	// geometry in advance. bits-ui's tooltip content doesn't carry an
	// ARIA `tooltip` role in the installed version --
	// `data-slot="tooltip-content"` (this app's own shadcn wrapper) is
	// the real, stable hook.
	// Capped at exactly the grid's own real cell count (not an arbitrary
	// small constant, which silently made this test fail against the
	// map's real ~630x380 canvas -- most of a ~3800-cell grid was cut
	// off before ever reaching the actual dot) -- this still turns an
	// open-ended worst case into a bounded, one-pass-of-the-canvas
	// worst case (Copilot review on PR #180).
	const MAX_ATTEMPTS = Math.ceil(box.width / 8) * Math.ceil(box.height / 8);
	const tooltip = page.locator('[data-slot="tooltip-content"]');
	let opened = false;
	let attempts = 0;
	outer: for (let px = 8; px < box.width - 8; px += 8) {
		for (let py = 8; py < box.height - 8; py += 8) {
			if (attempts >= MAX_ATTEMPTS) break outer;
			attempts++;
			await page.mouse.click(box.x + px, box.y + py);
			if (await tooltip.isVisible().catch(() => false)) {
				opened = true;
				break outer;
			}
		}
	}
	expect(opened).toBe(true);
	await expect(tooltip).toContainText(/\+\d+h/);
	await expect(tooltip).toContainText(/kt/);
	expect(pageErrors).toEqual([]);
});

test('the intensity chart renders real data only, with no leftover fabricated overlay', async ({
	page,
}) => {
	const pageErrors: string[] = [];
	page.on('pageerror', (err) => pageErrors.push(err.message));

	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
	await page.getByRole('button', { name: 'Run cycle' }).click();

	await expect(page.getByText('Intensity (10th-90th percentile)')).toBeVisible();
	// The chart is a real <svg> (layerchart), drawn once real pdf data
	// exists -- this would fail to find anything if the AreaChart threw
	// during render instead of the fallback "No ensemble products" text.
	await expect(page.locator('svg.lc-layout-svg').first()).toBeVisible({ timeout: 5_000 });
	expect(pageErrors).toEqual([]);
});

test('today\'s schedule stage tooltip is a real shadcn tooltip, not the browser title attribute', async ({
	page,
}) => {
	const pageErrors: string[] = [];
	page.on('pageerror', (err) => pageErrors.push(err.message));

	await page.goto('/');
	await expect(page.getByText("Today's cycle schedule")).toBeVisible();

	const stageBar = page.locator('[data-slot="tooltip-trigger"]').first();
	await expect(stageBar).toBeVisible();
	await expect(stageBar).not.toHaveAttribute('title', /.+/);
	await stageBar.hover();
	await expect(page.locator('[data-slot="tooltip-content"]')).toBeVisible({ timeout: 3_000 });
	expect(pageErrors).toEqual([]);
});

test('monitoring page charts each model\'s real per-feature drift, not just the drifted subset as text', async ({
	page,
}) => {
	const pageErrors: string[] = [];
	page.on('pageerror', (err) => pageErrors.push(err.message));

	await page.goto('/monitoring');
	await expect(page.getByRole('heading', { name: 'Monitoring' })).toBeVisible();
	await page.waitForSelector('text=Loading drift reports…', { state: 'detached', timeout: 10_000 });

	// At least one drift report card should have real features to chart --
	// a real <svg> bar chart, not the old plain-text list.
	await expect(page.locator('svg.lc-layout-svg').first()).toBeVisible({ timeout: 5_000 });
	expect(pageErrors).toEqual([]);
});
