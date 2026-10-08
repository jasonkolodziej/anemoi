import { test, expect } from '@playwright/test';

// A return visit used to show an empty page under the full-page waiter
// until the API answered -- with a sleeping API container, a long wait.
// The last answer this browser saw is now drawn at once and refreshed
// behind it. Each test holds the API request open to prove the page
// rendered without it.

test('a return visit to the homepage shows the last storms while the API is slow', async ({ page }) => {
	await page.goto('/');
	const firstCard = page.locator('a[href^="/storms/"]').first();
	await expect(firstCard).toBeVisible();
	const href = await firstCard.getAttribute('href');

	let release!: () => void;
	const held = new Promise<void>((r) => (release = r));
	await page.route('**/v1/storms', async (route) => {
		await held;
		await route.continue();
	});

	await page.reload();
	await expect(page.locator(`a[href="${href}"]`)).toBeVisible();
	await expect(page.getByTestId('refreshing')).toBeVisible();
	await expect(page.getByText('Please wait...')).toBeHidden();

	release();
	await expect(page.getByTestId('refreshing')).toBeHidden();
});

test('a return visit to a storm shows it while the API is slow', async ({ page }) => {
	await page.goto('/');
	const href = await page.locator('a[href^="/storms/"]').first().getAttribute('href');
	await page.goto(href!);
	await page.waitForSelector('#cycle-input');
	const heading = await page.locator('h1').first().textContent();

	let release!: () => void;
	const held = new Promise<void>((r) => (release = r));
	await page.route(`**/v1${href}`, async (route) => {
		await held;
		await route.continue();
	});

	await page.reload();
	await expect(page.locator('h1').first()).toHaveText(heading!);
	await expect(page.getByText('Please wait...')).toBeHidden();
	release();
});

test('a first visit with nothing remembered still loads normally', async ({ page }) => {
	await page.goto('/');
	await page.evaluate(() => localStorage.clear());
	await page.reload();
	await expect(page.locator('a[href^="/storms/"]').first()).toBeVisible();
	await expect(page.getByTestId('refreshing')).toBeHidden();
});
