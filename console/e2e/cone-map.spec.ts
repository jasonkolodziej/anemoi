import { test, expect } from '@playwright/test';

// The storm cycle map (ConeMap.svelte) is a real interactive MapLibre map,
// not a static SVG -- this drives a real cycle run and checks the map
// actually renders (a canvas element, real MapLibre DOM classes) and,
// critically, that panning/zooming doesn't throw. That last part is not
// paranoia: a real bug shipped here once already -- fitBounds's own
// move/moveend events fed back into this app's fitBounds effect closely
// enough to trip Svelte's effect_update_depth_exceeded guard the moment a
// user interacted with the map. This test would have caught it.

test('cycle map renders and survives pan/zoom without throwing', async ({ page }) => {
	const pageErrors: string[] = [];
	page.on('pageerror', (err) => pageErrors.push(err.message));

	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
	await page.getByRole('button', { name: 'Run cycle' }).click();

	const canvas = page.locator('canvas').first();
	await expect(canvas).toBeVisible({ timeout: 10_000 });
	await expect(page.locator('.maplibregl-map')).toBeVisible();

	const box = await canvas.boundingBox();
	if (!box) throw new Error('map canvas has no bounding box');

	// Zoom, then pan -- exactly the interaction that triggered the
	// fitBounds feedback loop for real.
	await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
	await page.mouse.wheel(0, -300);
	await page.waitForTimeout(400);
	await page.mouse.down();
	await page.mouse.move(box.x + box.width / 2 - 80, box.y + box.height / 2 - 40, { steps: 8 });
	await page.mouse.up();
	await page.waitForTimeout(400);

	expect(pageErrors).toEqual([]);

	// The in-map legend is real DOM (unlike the track/labels, which are
	// drawn on the canvas and not queryable this way).
	await expect(page.getByText('forecast (fusion)')).toBeVisible();
});
