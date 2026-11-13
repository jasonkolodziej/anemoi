import { readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';
import { signUpViaMagicLink } from './helpers/auth';

// The Develop pages (architecture, registry, monitoring, retraining, sources) are
// signed-in only: each has a -guard.ts, and anemoi-api-real refuses the
// reads only they make (docker/api/src/routing.ts). This runs in the
// workerd suite because sign-in needs the local D1 `vite dev` doesn't have.
//
// No API runs here, so every /api/v1/* call is answered in the browser from
// fixtures/develop-api.json: the demo API's own responses, captured from
// `anemoi.api` in demo mode (the seeded registry, synthetic drift and
// calibration, and each model described from its builder's defaults).

const API: Record<string, unknown> = JSON.parse(
	readFileSync(new URL('./fixtures/develop-api.json', import.meta.url), 'utf8')
);

async function serveDemoApi(page: Page) {
	await page.route('**/api/v1/**', (route) => {
		const path = new URL(route.request().url()).pathname.replace(/^\/api/, '');
		return path in API
			? route.fulfill({ json: API[path] })
			: route.fulfill({ status: 404, json: { detail: `not in develop-api.json: ${path}` } });
	});
}

/** Answers one path differently from the fixture for the rest of the test
 * (a route registered later is tried first). */
async function serveInstead(page: Page, path: string, response: { status?: number; json: unknown }) {
	await page.route(`**/api${path}`, (route) => route.fulfill(response));
}

type SourceRow = { key: string; used_by?: string[] };
const SOURCES = API['/v1/sources'] as SourceRow[];
/** /v1/sources as an API from before `used_by` sends it. The console and
 * the API deploy separately, so the console can meet one. */
const SOURCES_BEFORE_USED_BY = SOURCES.map(({ used_by: _, ...row }) => row);

const PHONE = { width: 390, height: 844 };

/** How far the page itself can be scrolled sideways: 0 when it fits. */
const sidewaysOverflow = (page: Page) =>
	page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

const DEVELOP = ['/architecture', '/registry', '/monitoring', '/retraining', '/sources'];

for (const path of DEVELOP) {
	test(`${path} sends a signed-out visitor to sign in, then back`, async ({ page }) => {
		await page.goto(path);
		await expect(page).toHaveURL(new RegExp(`/auth/login\\?next=${encodeURIComponent(path)}`));
	});
}

// The bug a direct visit doesn't show: navigating in the browser from another
// page makes no server request unless the page has a server load, so the
// guard never ran and the page rendered signed out.
test('the Develop menu sends a signed-out visitor to sign in, client-side navigation included', async ({ page }) => {
	await page.goto('/');
	for (const [title, path] of [
		['Architecture', '/architecture'],
		['Registry', '/registry'],
		['Monitoring', '/monitoring'],
		['Retraining', '/retraining'],
		['Sources', '/sources'],
	]) {
		await page.getByRole('button', { name: 'Develop' }).click();
		await page.getByRole('link', { name: new RegExp(`^${title}`) }).click();
		await expect(page).toHaveURL(new RegExp(`/auth/login\\?next=${encodeURIComponent(path)}`));
		await page.goto('/');
	}
});

test.describe('signed in', () => {
	test.beforeEach(async ({ page }) => {
		await serveDemoApi(page);
		await signUpViaMagicLink(page, `develop-${test.info().testId}-${Date.now()}@example.com`);
	});

	test('the Develop menu lists all five pages', async ({ page }) => {
		await page.goto('/');
		await page.getByRole('button', { name: 'Develop' }).click();
		for (const title of ['Architecture', 'Registry', 'Monitoring', 'Retraining', 'Sources']) {
			await expect(page.getByRole('link', { name: new RegExp(`^${title}`) })).toBeVisible();
		}
	});

	test('architecture draws the system and opens a model into its layers', async ({ page }) => {
		const pageErrors: string[] = [];
		page.on('pageerror', (err) => pageErrors.push(err.message));

		await page.goto('/architecture');
		await expect(page.getByRole('heading', { name: 'Architecture' })).toBeVisible();
		const muted = page.locator('svg[aria-label="Anemoi system"] .beam-muted');
		// Nothing selected: only the two sources no model reads yet are muted.
		await expect(muted).toHaveCount(2);

		// Desktop width: the layers open in a popover laid over the graph,
		// inside the screen -- the page doesn't scroll for it.
		await page.getByRole('button', { name: /\(lstm\)/ }).click();
		const popover = page.locator('[data-slot="popover-content"]');
		await expect(popover).toBeVisible();
		await expect(popover.locator('svg[aria-label="lstm layers"]')).toContainText('4 × 14');
		const graph = await page.locator('svg[aria-label="Anemoi system"]').boundingBox();
		const box = await popover.boundingBox();
		const viewport = page.viewportSize()!;
		expect(box!.y).toBeLessThan(graph!.y + graph!.height); // over the graph
		expect(box!.y + box!.height).toBeLessThanOrEqual(viewport.height);
		expect(await page.evaluate(() => window.scrollY)).toBe(0);

		// Close it, then open another model.
		await page.keyboard.press('Escape');
		await expect(popover).toBeHidden();
		await page.getByRole('button', { name: /\(cnn\)/ }).click();
		const cnn = popover.locator('svg[aria-label="cnn layers"]');
		await expect(cnn).toContainText('5 × 41 × 41'); // the gridded crop
		// The residual stages are opened up, not one opaque "blocks" box.
		await expect(cnn).toContainText('blocks.0');
		await expect(cnn).toContainText('blocks.3');
		// The demo versions predate arch_params, and the page says so.
		await expect(popover.getByText(/builder's defaults/)).toBeVisible();
		// The CNN's path: the GFS source in, through PINN, fusion and
		// diffusion out. The other three models' edges and the best-track
		// source are muted on top of the two unused sources.
		await expect(muted).toHaveCount(2 + 1 + 3 + 3);

		// Hovering a block lists what's inside it.
		await cnn.getByRole('button', { name: /^blocks\.0,/ }).hover();
		await expect(popover.getByRole('heading', { name: /blocks\.0 · ResBlock/ })).toBeVisible();

		// Escape closes it, and the whole system flows again.
		await page.keyboard.press('Escape');
		await expect(popover).toBeHidden();
		await expect(muted).toHaveCount(2);
		expect(pageErrors).toEqual([]);
	});

	// Moved from registry.spec.ts (#92 gap 1): the provenance column renders
	// what the demo API returns.
	test('registry renders provenance for a seeded demo version', async ({ page }) => {
		await page.goto('/registry');
		const lstmRow = page.getByRole('row', { name: /^lstm/ });
		await expect(lstmRow).toBeVisible();
		await expect(lstmRow.getByText('no checkpoint_uri')).toBeVisible();
		await expect(lstmRow.getByText('arch_params')).toHaveCount(0);
	});

	test('registry renders the latent_signature-derived pin', async ({ page }) => {
		await page.goto('/registry');
		await expect(page.getByText(/Active pin/)).toBeVisible();
		await expect(page.getByText(/latent signature:/)).toBeVisible();
	});

	// Moved from console-visuals.spec.ts.
	test("monitoring charts each model's per-feature drift", async ({ page }) => {
		const pageErrors: string[] = [];
		page.on('pageerror', (err) => pageErrors.push(err.message));
		await page.goto('/monitoring');
		await expect(page.getByRole('heading', { name: 'Monitoring' })).toBeVisible();
		await page.waitForSelector('text=Loading drift reports…', { state: 'detached', timeout: 10_000 });
		await expect(page.locator('svg.lc-layout-svg').first()).toBeVisible({ timeout: 5_000 });
		expect(pageErrors).toEqual([]);
	});

	test('monitoring shows served-product calibration by lead (#166)', async ({ page }) => {
		const pageErrors: string[] = [];
		page.on('pageerror', (err) => pageErrors.push(err.message));
		await page.goto('/monitoring');
		await expect(page.getByText('Calibration — served product containment by lead')).toBeVisible();
		await expect(page.locator('svg.lc-layout-svg').first()).toBeVisible({ timeout: 5_000 });
		await expect(page.getByText('No real cycles have been audited yet')).toHaveCount(0);
		await expect(page.getByText(/cone nominal \d+%/)).toBeVisible();
		await expect(page.getByText(/intensity nominal \d+%/)).toBeVisible();
		expect(pageErrors).toEqual([]);
	});

	test('sources lists the data source registry', async ({ page }) => {
		const pageErrors: string[] = [];
		page.on('pageerror', (err) => pageErrors.push(err.message));
		await page.goto('/sources');
		await expect(page.getByRole('heading', { name: /source/i }).first()).toBeVisible();
		await expect(page.getByRole('row').nth(1)).toBeVisible();
		expect(pageErrors).toEqual([]);
	});

	/** The cell under `heading` in the row for source `key`. */
	async function sourceCell(page: Page, key: string, heading: string) {
		await expect(page.getByRole('row').nth(1)).toBeVisible();
		const headings = (await page.getByRole('columnheader').allTextContents()).map((h) => h.trim());
		expect(headings).toContain(heading);
		const row = page.getByRole('row').filter({ has: page.getByRole('cell', { name: key, exact: true }) });
		return row.getByRole('cell').nth(headings.indexOf(heading));
	}

	test('sources says what uses each source, next to its role', async ({ page }) => {
		await page.goto('/sources');
		// A model input, labels, verification only, and nothing yet.
		await expect(await sourceCell(page, 'besttrack_working', 'Used by')).toHaveText('LSTM · PINN');
		await expect(await sourceCell(page, 'gdas_gfs', 'Used by')).toHaveText('CNN · Transformer · GNN · PINN');
		await expect(await sourceCell(page, 'besttrack_final', 'Used by')).toHaveText('labels · verification');
		await expect(await sourceCell(page, 'dropsonde', 'Used by')).toHaveText('verification only');
		await expect(await sourceCell(page, 'ndbc', 'Used by')).toHaveText('verification only');
		await expect(await sourceCell(page, 'goes', 'Used by')).toHaveText('not used yet');
		// Role is still there and says something else: GOES may be read in
		// a cycle, and nothing reads it.
		await expect(await sourceCell(page, 'goes', 'Role')).toHaveText('operational');
		// No column is pushed off the right edge of the table.
		const hidden = await page
			.getByRole('table')
			.evaluate((el) => el.parentElement!.scrollWidth - el.parentElement!.clientWidth);
		expect(hidden).toBe(0);
	});

	test('sources shows a dash, not "not used yet", when the API predates used_by', async ({ page }) => {
		await serveInstead(page, '/v1/sources', { json: SOURCES_BEFORE_USED_BY });
		await page.goto('/sources');
		for (const key of ['besttrack_working', 'dropsonde', 'goes']) {
			const cell = await sourceCell(page, key, 'Used by');
			await expect(cell).toContainText('—');
			await expect(cell).not.toContainText('not used yet');
		}
		await expect(page.getByText('not used yet')).toHaveCount(0);
	});

	test('sources on a phone: each source with its role and use, nothing to scroll sideways for', async ({
		page,
	}) => {
		await page.setViewportSize(PHONE);
		await page.goto('/sources');
		const item = (key: string) =>
			page.getByRole('listitem').filter({ has: page.getByRole('heading', { name: key, exact: true }) });
		await expect(item('besttrack_working')).toContainText('LSTM · PINN');
		await expect(item('besttrack_working')).toContainText('operational');
		await expect(item('dropsonde')).toContainText('verification only');
		await expect(item('goes')).toContainText('not used yet');
		await expect(page.getByRole('table')).toHaveCount(0);
		expect(await sidewaysOverflow(page)).toBe(0);
	});

	test('retraining loads its triggers', async ({ page }) => {
		const pageErrors: string[] = [];
		page.on('pageerror', (err) => pageErrors.push(err.message));
		await page.goto('/retraining');
		await expect(page.getByRole('heading', { name: /Retrain/ })).toBeVisible();
		expect(pageErrors).toEqual([]);
	});
});
