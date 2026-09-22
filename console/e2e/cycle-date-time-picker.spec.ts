import { test, expect } from '@playwright/test';

// The storm detail page's cycle-label input got two companion fields (a
// date popover + a synoptic-hour select, from shadcn-svelte's real
// Calendar/Popover components) that write into the same #cycle-input the
// raw text field already edits -- this proves the whole round trip
// against a real running demo API and real Chromium, not a screenshot
// read by eye.

test('date and time picker updates the cycle label input', async ({ page }) => {
	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');

	const dateTrigger = page.getByRole('button', { name: /select date|^\d{8}$/ });
	await dateTrigger.click();

	const day = page.locator('[data-calendar-day]:not([data-outside-month])').first();
	const label = await day.getAttribute('aria-label');
	await day.click();

	// Popover closes on pick (onValueChange sets open = false).
	await expect(page.locator('[data-calendar-root]')).toBeHidden();

	// aria-label is e.g. "Tuesday, September 1, 2026" -- extract day/month/year
	// to build the expected YYYYMMDD prefix without hardcoding "today".
	const parsedDate = new Date(label!.replace(/^\w+, /, ''));
	const expectedPrefix =
		String(parsedDate.getFullYear()) +
		String(parsedDate.getMonth() + 1).padStart(2, '0') +
		String(parsedDate.getDate()).padStart(2, '0');
	await expect(page.locator('#cycle-input')).toHaveValue(new RegExp(`^${expectedPrefix}_\\d{2}Z$`));

	await page.selectOption('#cycle-hour-select', '18');
	await expect(page.locator('#cycle-input')).toHaveValue(`${expectedPrefix}_18Z`);

	// The raw text field itself must still be independently editable --
	// this is an added convenience, not a replacement.
	await page.fill('#cycle-input', '20260101_06Z');
	await expect(page.locator('#cycle-input')).toHaveValue('20260101_06Z');
});
