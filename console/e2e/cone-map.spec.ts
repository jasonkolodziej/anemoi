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

test('legend is real and clickable -- toggling the uncertainty cone changes aria-pressed', async ({
	page,
}) => {
	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
	await page.getByRole('button', { name: 'Run cycle' }).click();
	await expect(page.locator('canvas').first()).toBeVisible({ timeout: 10_000 });

	const coneToggle = page.getByRole('button', { name: /uncertainty cone/ });
	await expect(coneToggle).toHaveAttribute('aria-pressed', 'true');
	await coneToggle.click();
	await expect(coneToggle).toHaveAttribute('aria-pressed', 'false');
	await coneToggle.click();
	await expect(coneToggle).toHaveAttribute('aria-pressed', 'true');
});

// Real per-model tracks (per_model_tracks) only exist for real-mode
// cycles with actually-contributing Group 1 models -- DemoState's
// synthetic cycles never populate them (see cycle.py's DeterministicForecast
// docstring). The "individual model tracks" legend entry is conditional
// on that (`{#if modelSlugs.length > 0}`) specifically so demo mode
// doesn't show a toggle for lines that don't exist -- this is the
// negative-space proof of that condition against the real demo webServer;
// the positive case (real tracks actually rendering + hover isolating one)
// is covered by tests/test_real_inference_cycle.py on the Python side and
// was verified by hand against a real cycle (see PR description).
test('individual model tracks toggle does not appear without real per-model data', async ({
	page,
}) => {
	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	await page.waitForSelector('#cycle-input');
	await page.getByRole('button', { name: 'Run cycle' }).click();
	await expect(page.locator('canvas').first()).toBeVisible({ timeout: 10_000 });

	await expect(page.getByRole('button', { name: /individual model tracks/ })).toHaveCount(0);
});

// Real regression: the storm detail page's periodic-refresh fix (60s poll,
// e2e/periodic-refresh.spec.ts) combined with the fitBounds effect's old
// bounds-*value* guard meant a live storm's real history genuinely
// shifting between polls re-triggered fitBounds -- silently resetting
// whatever pan/zoom the user had set, mid-interaction, every ~60s. Found
// live against EP172026 (an active storm). Fixed by keying the guard on
// the *cycle label* instead of the bounds value, so a background refresh
// of the same cycle never re-fits, only a genuinely new cycle does.
test('a background data refresh does not reset the user\'s own pan/zoom', async ({ page }) => {
	await page.goto('/');
	await page.locator('a[href^="/storms/"]').first().click();
	const stormUrl = page.url();
	await page.waitForSelector('#cycle-input');
	await page.getByRole('button', { name: 'Run cycle' }).click();

	const canvas = page.locator('canvas').first();
	await expect(canvas).toBeVisible({ timeout: 10_000 });
	const marker = page.locator('.maplibregl-marker').first();
	await expect(marker).toBeVisible();

	// Install the virtual clock only now -- after the real cycle run and
	// initial fitBounds have already happened, so the 60s interval set up
	// in onMount starts counting from a known point.
	await page.clock.install({ time: new Date() });

	const box = await canvas.boundingBox();
	if (!box) throw new Error('map canvas has no bounding box');
	await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
	await page.mouse.down();
	await page.mouse.move(box.x + box.width / 2 - 120, box.y + box.height / 2 - 60, { steps: 8 });
	await page.mouse.up();
	await page.waitForTimeout(200);
	const pannedPosition = await marker.boundingBox();

	// The next real GET for this storm comes back with the *oldest* history
	// point shifted a long way -- enough to genuinely change `bounds` (its
	// envelope covers all of `history`) -- while leaving `latest_fix` and
	// history's *last* entry (what the current-fix marker itself renders
	// at) completely untouched. That isolates the signal precisely: if the
	// camera resets, the marker moves on screen even though its own real
	// lat/lon never changed; if the fix holds, it can't move at all.
	const stormId = new URL(stormUrl).pathname.split('/').pop();
	await page.route(`**/v1/storms/${stormId}`, async (route) => {
		const response = await route.fetch();
		const body = await response.json();
		body.history = body.history.map((f: { lat: number; lon: number }, i: number) =>
			i === 0 ? { ...f, lat: f.lat + 8, lon: f.lon - 8 } : f,
		);
		await route.fulfill({ response, json: body });
	});

	await page.clock.fastForward('01:05'); // past the 60s poll interval
	await page.waitForTimeout(300);

	const afterPollPosition = await marker.boundingBox();
	if (!pannedPosition || !afterPollPosition) throw new Error('marker has no bounding box');
	expect(Math.round(afterPollPosition.x)).toBe(Math.round(pannedPosition.x));
	expect(Math.round(afterPollPosition.y)).toBe(Math.round(pannedPosition.y));
});
