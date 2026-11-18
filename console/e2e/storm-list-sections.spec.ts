import { test, expect } from '@playwright/test';

// The home page splits the storm list: active storms first, ended ones under
// "Recent storms". With nothing active it says so rather than heading
// last season's archive "Active storms".
type Storm = { storm_id: string; active: boolean; track_source?: string | null; latest_fix: { quality: string } };

async function serve(page: import('@playwright/test').Page, edit: (storms: Storm[]) => Storm[]) {
	await page.route('**/v1/storms', async (route) => {
		const res = await route.fetch();
		const storms = (await res.json()) as Storm[];
		await route.fulfill({ response: res, json: edit(storms) });
	});
}

test('ended storms are listed under Recent storms, archived ones labelled', async ({ page }) => {
	await serve(page, (storms) =>
		storms.map((s, i) =>
			i === 0
				? { ...s, active: true, track_source: 'live', latest_fix: { ...s.latest_fix, quality: 'working' } }
				: i === 1
					? { ...s, active: false, track_source: 'season_archive', latest_fix: { ...s.latest_fix, quality: 'working' } }
					: { ...s, active: false, track_source: 'hurdat2' },
		),
	);
	await page.goto('/');
	const recent = page.locator('section[aria-labelledby="recent-storms"]');
	await expect(page.getByRole('heading', { name: 'Recent storms' })).toBeVisible();
	await expect(recent.getByText('working (archived)')).toHaveCount(1);
	await expect(page.getByTestId('no-active-storms')).toHaveCount(0);
	const cards = page.locator('a[href^="/storms/"]');
	const inRecent = recent.locator('a[href^="/storms/"]');
	expect((await cards.count()) - (await inRecent.count())).toBe(1);
	await page.unrouteAll({ behavior: 'ignoreErrors' });
});

test('with no active storm the page says so', async ({ page }) => {
	await serve(page, (storms) => storms.map((s) => ({ ...s, active: false, track_source: 'hurdat2' })));
	await page.goto('/');
	await expect(page.getByTestId('no-active-storms')).toHaveText('No active storms right now.');
	await expect(page.getByRole('heading', { name: 'Recent storms' })).toBeVisible();
	await page.unrouteAll({ behavior: 'ignoreErrors' });
});
