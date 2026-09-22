import { test, expect } from '@playwright/test';

// Model Pantheon (ModelStatusPanel.svelte): real branding data
// (direction/persona from $lib/branding, weights from the real cycle
// response), not fabricated -- hovering a row reveals its persona and
// highlights it in the model's own brand color.

test('model pantheon reveals persona on hover', async ({ page }) => {
	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
	await page.getByRole('button', { name: 'Run cycle' }).click();
	await page.waitForSelector('text=Model Pantheon');

	const firstRow = page.locator('[role="group"]').first();
	const personaPattern = /sprinter|strategist|maverick|observer|disciplinarian|oracle/;
	await expect(page.getByText(personaPattern)).toHaveCount(0);
	await firstRow.hover();
	await expect(page.getByText(personaPattern)).toBeVisible();
});
