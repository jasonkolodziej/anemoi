import { test, expect, type Page } from '@playwright/test';

// The cookie banner: nothing optional is stored or loaded until the visitor
// chooses. "Preferences" is lastKnown's localStorage copy of the last pages
// drawn; "analytics" is Cloudflare Web Analytics' beacon, loaded from
// static.cloudflareinsights.com (answered here with an empty script --
// nothing reaches Cloudflare). playwright.config.ts gives the console a
// stand-in token, so the beacon would load if allowed.
//
// Every other spec starts with the banner already answered
// (e2e/fixtures/consent-decided.json); this one starts from nothing.
test.use({ storageState: { cookies: [], origins: [] } });

const BEACON = 'https://static.cloudflareinsights.com/beacon.min.js';

/** Answers the beacon's request, and counts how often the page made one. */
async function watchBeacon(page: Page): Promise<{ requests: () => number }> {
	let count = 0;
	await page.route(BEACON, (route) => {
		count++;
		return route.fulfill({ contentType: 'text/javascript', body: '' });
	});
	return { requests: () => count };
}

const banner = (page: Page) => page.getByTestId('cookie-banner');

const storedKeys = (page: Page) => page.evaluate(() => Object.keys(localStorage));

/** Opens a storm page and waits for it to draw: the page that writes lastKnown. */
async function openFirstStorm(page: Page) {
	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
}

test('a first visit shows the banner, and stores and loads nothing optional', async ({ page }) => {
	const beacon = await watchBeacon(page);
	await openFirstStorm(page);

	await expect(banner(page)).toBeVisible();
	await expect(banner(page).getByRole('button', { name: 'Accept all' })).toBeVisible();
	await expect(banner(page).getByRole('button', { name: 'Necessary only' })).toBeVisible();
	await expect(banner(page).getByRole('button', { name: 'Choose…' })).toBeVisible();

	expect(await storedKeys(page)).toEqual([]);
	expect(await page.context().cookies()).toEqual([]);
	expect(beacon.requests()).toBe(0);
	await expect(page.locator(`script[src="${BEACON}"]`)).toHaveCount(0);
});

test('"Necessary only" keeps the choice and nothing else, and the banner stays away', async ({
	page,
}) => {
	const beacon = await watchBeacon(page);
	await openFirstStorm(page);
	await banner(page).getByRole('button', { name: 'Necessary only' }).click();
	await expect(banner(page)).toBeHidden();

	await page.reload();
	await page.waitForSelector('#cycle-input');
	await expect(banner(page)).toBeHidden();
	expect(await storedKeys(page)).toEqual(['anemoi:consent:v1']);
	const choice = JSON.parse((await page.evaluate(() => localStorage.getItem('anemoi:consent:v1')))!);
	expect(choice).toMatchObject({ preferences: false, analytics: false });
	expect(beacon.requests()).toBe(0);
});

test('"Accept all" loads Cloudflare Web Analytics and remembers pages', async ({ page }) => {
	const beacon = await watchBeacon(page);
	await page.goto('/');
	await banner(page).getByRole('button', { name: 'Accept all' }).click();
	await expect(banner(page)).toBeHidden();

	await expect.poll(beacon.requests).toBe(1);
	const script = page.locator(`script[src="${BEACON}"]`);
	await expect(script).toHaveCount(1);
	expect(JSON.parse((await script.getAttribute('data-cf-beacon'))!)).toEqual({
		token: 'e2e-test-token',
	});

	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
	await expect
		.poll(async () => (await storedKeys(page)).some((k) => k.startsWith('anemoi:last:')))
		.toBe(true);
	// One script, however many pages: client-side navigation doesn't add another.
	await expect(script).toHaveCount(1);
});

test('choosing analytics alone loads the beacon but remembers no pages', async ({ page }) => {
	const beacon = await watchBeacon(page);
	await page.goto('/');
	await banner(page).getByRole('button', { name: 'Choose…' }).click();

	const preferences = page.getByLabel(/^Preferences/);
	const analytics = page.getByLabel(/^Analytics/);
	await expect(page.getByLabel(/^Necessary/)).toBeChecked();
	await expect(page.getByLabel(/^Necessary/)).toBeDisabled();
	await expect(preferences).not.toBeChecked();
	await expect(analytics).not.toBeChecked();

	await analytics.check();
	await banner(page).getByRole('button', { name: 'Save choices' }).click();
	await expect(banner(page)).toBeHidden();
	await expect.poll(beacon.requests).toBe(1);

	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
	expect((await storedKeys(page)).filter((k) => k.startsWith('anemoi:last:'))).toEqual([]);
});

test('"Cookie settings" reopens the choice, and withdrawing analytics unloads it', async ({
	page,
}) => {
	const beacon = await watchBeacon(page);
	await page.goto('/');
	await banner(page).getByRole('button', { name: 'Accept all' }).click();
	await expect.poll(beacon.requests).toBe(1);
	// Pages are remembered from the next one drawn after accepting.
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
	await expect
		.poll(async () => (await storedKeys(page)).some((k) => k.startsWith('anemoi:last:')))
		.toBe(true);

	await page.getByRole('contentinfo').getByRole('button', { name: 'Cookie settings' }).click();
	await expect(banner(page)).toBeVisible();
	await expect(page.getByLabel(/^Preferences/)).toBeChecked();
	await expect(page.getByLabel(/^Analytics/)).toBeChecked();

	// Withdrawing both: the stored pages go at once, and the page starts
	// again without the beacon (a loaded script can't be taken out).
	await page.getByLabel(/^Preferences/).uncheck();
	await page.getByLabel(/^Analytics/).uncheck();
	const reloaded = page.waitForEvent('load');
	await banner(page).getByRole('button', { name: 'Save choices' }).click();
	await reloaded;
	await page.waitForSelector('#cycle-input');

	await expect(banner(page)).toBeHidden();
	await expect(page.locator(`script[src="${BEACON}"]`)).toHaveCount(0);
	expect(beacon.requests()).toBe(1);
	expect(await storedKeys(page)).toEqual(['anemoi:consent:v1']);
});

test('the mobile menu has "Cookie settings" as well as the footer', async ({ page }) => {
	await page.setViewportSize({ width: 390, height: 844 });
	await page.goto('/');
	await banner(page).getByRole('button', { name: 'Necessary only' }).click();
	await expect(banner(page)).toBeHidden();

	await page.getByRole('button', { name: 'Open navigation' }).click();
	await page
		.getByRole('dialog', { name: 'Navigation' })
		.getByRole('button', { name: 'Cookie settings' })
		.click();
	await expect(banner(page)).toBeVisible();
	await expect(page.getByLabel(/^Analytics/)).not.toBeChecked();
});

// Phones (portrait and held sideways), a tablet, laptops and a large
// desktop: the whole banner sits inside the viewport with every button in
// view, and with the categories open the buttons stay in view while the
// text scrolls inside the banner instead of running off a short screen.
const FORM_FACTORS = [
	{ name: 'small phone', width: 320, height: 568 },
	{ name: 'phone', width: 390, height: 844 },
	{ name: 'phone, landscape', width: 844, height: 390 },
	{ name: 'tablet', width: 820, height: 1180 },
	{ name: 'laptop', width: 1280, height: 720 },
	{ name: 'desktop', width: 1920, height: 1080 },
];

for (const { name, width, height } of FORM_FACTORS) {
	test(`the banner fits a ${name} (${width}x${height})`, async ({ page }) => {
		await page.setViewportSize({ width, height });
		await page.goto('/');
		const box = await banner(page).locator('> div').boundingBox();
		expect(box).not.toBeNull();
		expect(box!.x).toBeGreaterThanOrEqual(0);
		expect(box!.y).toBeGreaterThanOrEqual(0);
		expect(box!.x + box!.width).toBeLessThanOrEqual(width);
		expect(box!.y + box!.height).toBeLessThanOrEqual(height);
		for (const label of ['Choose…', 'Necessary only', 'Accept all']) {
			await expect(banner(page).getByRole('button', { name: label })).toBeInViewport({ ratio: 1 });
		}

		await banner(page).getByRole('button', { name: 'Choose…' }).click();
		const opened = await banner(page).locator('> div').boundingBox();
		expect(opened!.y).toBeGreaterThanOrEqual(0);
		expect(opened!.y + opened!.height).toBeLessThanOrEqual(height);
		for (const label of ['Save choices', 'Necessary only', 'Accept all']) {
			await expect(banner(page).getByRole('button', { name: label })).toBeInViewport({ ratio: 1 });
		}
		// The last category, however short the screen, can be scrolled to and set.
		const analytics = page.getByLabel(/^Analytics/);
		await analytics.scrollIntoViewIfNeeded();
		await expect(analytics).toBeInViewport({ ratio: 1 });
		await analytics.check();
		await banner(page).getByRole('button', { name: 'Save choices' }).click();
		await expect(banner(page)).toBeHidden();
	});
}
