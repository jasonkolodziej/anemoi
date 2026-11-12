import { test, expect } from '@playwright/test';
import { unwrapLon } from '../src/lib/geo';

// docs/multi_basin.md phase 4: the storm list filters by basin, and the map
// draws Central Pacific tracks across the antimeridian continuously.

test('longitudes are unwrapped around the storm, across the antimeridian', () => {
	// A CP storm at 179W moving west: 179E is 2 degrees away, not 358.
	expect(unwrapLon(179, -179)).toBe(-181);
	expect(unwrapLon(-179, 179)).toBe(181);
	// Anything already within 180 degrees is untouched.
	expect(unwrapLon(-75, -72)).toBe(-75);
	expect(unwrapLon(-140, -170)).toBe(-140);
});

test('the storm list filters by basin, kept in the URL', async ({ page }) => {
	// The demo API's storms are Atlantic; relabel two as EP and CP so the
	// list has three basins to filter.
	await page.route('**/v1/storms', async (route) => {
		const res = await route.fetch();
		const storms = (await res.json()) as { storm_id: string; basin: string; trained_basin: boolean }[];
		const relabel = (s: (typeof storms)[number], basin: string) => ({
			...s,
			storm_id: basin + s.storm_id.slice(2),
			basin,
			trained_basin: false,
		});
		const out = storms.map((s, i) => (i === 0 ? relabel(s, 'EP') : i === 1 ? relabel(s, 'CP') : s));
		await route.fulfill({ response: res, json: out });
	});
	await page.goto('/');
	const cards = page.locator('a[href^="/storms/"]');
	await expect(cards.first()).toBeVisible();
	const total = await cards.count();

	const filters = page.getByRole('group', { name: 'Filter storms by basin' });
	await filters.getByRole('button', { name: /^EP/ }).click();
	await expect(page).toHaveURL(/\?basin=EP$/);
	await expect(cards).toHaveCount(1);
	await expect(cards.first()).toHaveAttribute('href', /\/storms\/EP/);
	// A basin not every served model is verified in says so.
	await expect(page.getByText('EP basin -- not verified')).toBeVisible();

	// The filter survives a reload, and "All" clears it.
	await page.reload();
	await expect(cards).toHaveCount(1);
	await filters.getByRole('button', { name: /^All/ }).click();
	await expect(page).not.toHaveURL(/basin=/);
	await expect(cards).toHaveCount(total);
});
