import { test, expect } from '@playwright/test';

// #188: `ri_probability` is a fraction of a finite ensemble and the alert
// threshold is a hard cut at 30%, so a two-state banner had to call a coin
// flip either "flagged" or "no signal". The third state says "cannot tell"
// instead. These drive each state through the real page by rewriting the
// cycle response, since a demo ensemble won't land on all three on its own.

const cases = [
	{
		name: 'undetermined when the interval spans the threshold',
		payload: {
			ri_uncertain: true,
			rapid_intensification: false,
			ri_probability: 0.3,
			ri_probability_lo: 0.15,
			ri_probability_hi: 0.52,
		},
		expect: /Rapid intensification undetermined/,
		alsoExpect: /spans the 30% alert threshold/,
	},
	{
		name: 'flagged when the interval clears the threshold',
		payload: {
			ri_uncertain: false,
			rapid_intensification: true,
			ri_probability: 0.62,
			ri_probability_lo: 0.48,
			ri_probability_hi: 0.74,
		},
		expect: /Rapid intensification flagged/,
		alsoExpect: /95% range 48%–74%/,
	},
	{
		name: 'clear when the interval sits below the threshold',
		payload: {
			ri_uncertain: false,
			rapid_intensification: false,
			ri_probability: 0.04,
			ri_probability_lo: 0.01,
			ri_probability_hi: 0.13,
		},
		expect: /No rapid intensification signal/,
		alsoExpect: /95% range 1%–13%/,
	},
];

for (const c of cases) {
	test(`RI banner is ${c.name}`, async ({ page }) => {
		// Only the POST: a trailing-glob pattern also caught the 60s poll's
		// GET-by-label, whose handler then outlived the test.
		await page.route('**/v1/storms/*/cycles', async (route) => {
			if (route.request().method() !== 'POST') return route.continue();
			const res = await route.fetch();
			const body = await res.json();
			if (body?.payload) Object.assign(body.payload, c.payload);
			await route.fulfill({ response: res, body: JSON.stringify(body) });
		});
		await page.goto('/');
		await page.locator('a[href^="/storms/"]').first().click();
		await page.waitForSelector('#cycle-input');
		const ran = page.waitForResponse(
			(r) => r.request().method() === 'POST' && r.url().includes('/cycles'),
		);
		await page.getByRole('button', { name: /Run cycle/i }).click();
		await ran;

		await expect(page.getByText(c.expect)).toBeVisible();
		await expect(page.getByText(c.alsoExpect)).toBeVisible();
	});
}

test('a cycle stored before the interval existed still renders two-state', async ({ page }) => {
	// Cycles persisted before #188 carry nulls for these fields (#175 keeps
	// them in R2 indefinitely). The banner must fall back, not render
	// "undetermined" or an empty range.
	await page.route('**/v1/storms/*/cycles', async (route) => {
		if (route.request().method() !== 'POST') return route.continue();
		const res = await route.fetch();
		const body = await res.json();
		if (body?.payload) {
			Object.assign(body.payload, {
				ri_uncertain: null,
				ri_probability_lo: null,
				ri_probability_hi: null,
				rapid_intensification: false,
				ri_probability: 0.1,
			});
		}
		await route.fulfill({ response: res, body: JSON.stringify(body) });
	});
	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
	const ran = page.waitForResponse(
		(r) => r.request().method() === 'POST' && r.url().includes('/cycles'),
	);
	await page.getByRole('button', { name: /Run cycle/i }).click();
	await ran;

	await expect(page.getByText(/No rapid intensification signal/)).toBeVisible();
	await expect(page.getByText(/Rapid intensification undetermined/)).toHaveCount(0);
	await expect(page.getByText(/95% range/)).toHaveCount(0);
});
