import { readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';
import { signUpViaMagicLink } from './helpers/auth';

// The Develop pages (architecture, registry, monitoring, retraining) are
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

const DEVELOP = ['/architecture', '/registry', '/monitoring', '/retraining'];

for (const path of DEVELOP) {
	test(`${path} sends a signed-out visitor to sign in, then back`, async ({ page }) => {
		await page.goto(path);
		await expect(page).toHaveURL(new RegExp(`/auth/login\\?next=${encodeURIComponent(path)}`));
	});
}

test.describe('signed in', () => {
	test.beforeEach(async ({ page }) => {
		await serveDemoApi(page);
		await signUpViaMagicLink(page, `develop-${test.info().testId}-${Date.now()}@example.com`);
	});

	test('the Develop menu lists all four pages', async ({ page }) => {
		await page.goto('/');
		await page.getByRole('button', { name: 'Develop' }).click();
		for (const title of ['Architecture', 'Registry', 'Monitoring', 'Retraining']) {
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

	test('retraining loads its triggers', async ({ page }) => {
		const pageErrors: string[] = [];
		page.on('pageerror', (err) => pageErrors.push(err.message));
		await page.goto('/retraining');
		await expect(page.getByRole('heading', { name: /Retrain/ })).toBeVisible();
		expect(pageErrors).toEqual([]);
	});
});
