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

	const day = page
		.locator('[data-calendar-day]:not([data-outside-month]):not([data-disabled])')
		.first();
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

// A day the storm can't run a cycle on (before its first fix, or after the
// cycles the API would still accept) was clickable, and "Run cycle" could
// then only fail. The calendar and the hour select now offer only the
// storm's runnable range.
test('the picker disables days and hours outside the storm', async ({ page }) => {
	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
	const stormId = new URL(page.url()).pathname.split('/').pop()!;
	const storm = await (await page.request.get(`/api/v1/storms/${stormId}`)).json();

	const H = 3_600_000;
	const firstFix = new Date(storm.history[0].valid_time);
	const lastFix = new Date(storm.latest_fix.valid_time);
	const day = (d: Date) => d.toISOString().slice(0, 10);
	const label = (d: Date) => `${day(d).replaceAll('-', '')}_${String(d.getUTCHours()).padStart(2, '0')}Z`;
	const cell = (d: Date) => page.locator(`[data-calendar-day][data-value="${day(d)}"]`);
	// The demo storms ended months ago, so the last runnable cycle is the
	// API's 12 h grace past the latest fix, not the clock.
	expect(lastFix.getTime() + 12 * H).toBeLessThan(Date.now());

	// Open on the first fix's month: the day before it is disabled, its own day isn't.
	await page.fill('#cycle-input', label(firstFix));
	await page.getByTestId('cycle-date-trigger').click();
	await expect(cell(firstFix)).not.toHaveAttribute('data-disabled');
	const before = new Date(firstFix.getTime() - 24 * H);
	if (day(before).slice(0, 7) === day(firstFix).slice(0, 7)) {
		await expect(cell(before)).toHaveAttribute('data-disabled', '');
	}
	await page.keyboard.press('Escape');

	// On the first fix's day, the hours before it can't be picked.
	for (const h of [0, 6, 12, 18]) {
		const option = page.locator(`#cycle-hour-select option[value="${h}"]`);
		if (h < firstFix.getUTCHours()) await expect(option).toBeDisabled();
		else await expect(option).toBeEnabled();
	}

	// The day after the last runnable cycle is disabled too.
	const lastRunnable = new Date(lastFix.getTime() + 12 * H);
	await page.fill('#cycle-input', label(lastFix));
	await page.getByTestId('cycle-date-trigger').click();
	const after = new Date(Date.UTC(
		lastRunnable.getUTCFullYear(), lastRunnable.getUTCMonth(), lastRunnable.getUTCDate() + 1,
	));
	if (day(after).slice(0, 7) === day(lastFix).slice(0, 7)) {
		await expect(cell(after)).toHaveAttribute('data-disabled', '');
	}
	await expect(cell(lastFix)).not.toHaveAttribute('data-disabled');
});
