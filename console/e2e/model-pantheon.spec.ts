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

// DemoState hardcodes contributors for a fixed 4 models with no skip
// reasons at all (see demo_state.py's deterministic_fn) -- the "Not
// weighing in" section is conditional on missing_model_reasons actually
// having entries, so it must not appear for a synthetic demo cycle. The
// positive case (a real partial cycle showing real per-model skip
// reasons, e.g. "no real live feature (no cache, on-demand fetch
// failed)") was verified by hand against a real cycle, same as
// per_model_tracks -- DemoState has no equivalent for an e2e test to
// exercise.
test('model pantheon has no "not weighing in" section without real skip reasons', async ({
	page,
}) => {
	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
	await page.getByRole('button', { name: 'Run cycle' }).click();
	await page.waitForSelector('text=Model Pantheon');

	await expect(page.getByText('Not weighing in')).toHaveCount(0);
});
