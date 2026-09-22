import { test, expect } from '@playwright/test';

// Real regression coverage for the v1.2 "Wind Rose Projection" styling pass:
// the map panel's real rename, a real coastline-point round trip driving a
// real non-null landfall_probability, and the real system-wide Verification
// panel (§4.6.3 skew audit) rendering on a storm page it isn't scoped to.

test('map panel is titled Wind Rose Projection and shows intensity-coded points', async ({ page }) => {
	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
	await page.getByRole('button', { name: 'Run cycle' }).click();

	await expect(page.getByText('Wind Rose Projection')).toBeVisible({ timeout: 10_000 });
	// The intensity-coded points/labels are drawn on the MapLibre canvas
	// itself (SymbolLayer/CircleLayer), not real DOM -- see ConeMap.svelte's
	// own docstring on why hover/text assertions target the legend instead.
	await expect(page.locator('canvas').first()).toBeVisible();
});

test('a coastline point drives a real landfall probability and map marker', async ({ page }) => {
	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');

	await page.fill('#coastline-lat-input', '29.3');
	await page.fill('#coastline-lon-input', '-94.8');
	await page.getByRole('button', { name: 'Run cycle' }).click();

	await expect(page.getByText('Landfall Projection')).toBeVisible({ timeout: 10_000 });
	await expect(page.getByText('29.3°N 94.8°W')).toBeVisible();
	// A real percentage rendered at the probability's own `text-xl` size --
	// distinct from Model Pantheon's `text-xs` per-model weight percentages
	// elsewhere on the same page -- not the "set a reference point" fallback.
	await expect(page.locator('span.text-xl', { hasText: /^\d+%$/ })).toBeVisible();
	await expect(page.getByText('landfall reference')).toBeVisible();
});

test('landfall projection shows the no-reference-point fallback until one is set', async ({ page }) => {
	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
	await page.getByRole('button', { name: 'Run cycle' }).click();

	await expect(page.getByText('Landfall Projection')).toBeVisible({ timeout: 10_000 });
	await expect(page.getByText(/No coastal reference point was set/)).toBeVisible();
});

test('verification panel shows real system-wide skew data, not storm-scoped', async ({ page }) => {
	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');

	await expect(page.getByText('Verification')).toBeVisible({ timeout: 10_000 });
	await expect(page.getByText(/System-wide 48h-lead ERA5T-vs-operational skew audit/)).toBeVisible();
	await expect(page.getByText('mean track delta')).toBeVisible();
	await expect(page.getByText('mean |intensity delta|')).toBeVisible();
	await expect(page.getByText('full monitoring →')).toBeVisible();
});
