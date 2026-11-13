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
/** /v1/sources with some rows' `used_by` replaced. */
const sourcesWith = (usedBy: Record<string, string[]>) =>
	SOURCES.map((row) => (row.key in usedBy ? { ...row, used_by: usedBy[row.key] } : row));
/** /v1/sources wired unlike today: GOES feeds the GNN, nothing reads the
 * working best-track any more, and a source the console has no name for
 * feeds the LSTM. The specs on it fail if either page draws the mapping
 * from anything but `used_by`. */
const SOURCES_REWIRED = [
	...sourcesWith({ goes: ['gnn'], besttrack_working: [] }),
	{ ...SOURCES.find((row) => row.key === 'goes')!, key: 'new_feed', used_by: ['lstm'] },
];

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
		// Nothing selected: every beam runs. An edge nothing travels (from a
		// source no model reads yet) has no beam to mute.
		await expect(muted).toHaveCount(0);

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
		// The CNN's path: GDAS/GFS and ERA5 in, through PINN, fusion and
		// diffusion out. Muted: the working best-track (the CNN doesn't
		// read it), and the other three models' edges in and out.
		await expect(muted).toHaveCount(1 + 3 + 3);

		// Hovering a block lists what's inside it.
		await cnn.getByRole('button', { name: /^blocks\.0,/ }).hover();
		await expect(popover.getByRole('heading', { name: /blocks\.0 · ResBlock/ })).toBeVisible();

		// Escape closes it, and the whole system flows again.
		await page.keyboard.press('Escape');
		await expect(popover).toBeHidden();
		// The pointer was on the popover, which lay over the graph: move it
		// off, or the node now under it is hovered and mutes the rest.
		await page.mouse.move(0, 0);
		await expect(muted).toHaveCount(0);
		expect(pageErrors).toEqual([]);
	});

	// The graph's sources, and which models read them, come from
	// /v1/sources (`used_by`), not from a list kept in the console.
	test('architecture draws every registered source and how it is used', async ({ page }) => {
		const pageErrors: string[] = [];
		page.on('pageerror', (err) => pageErrors.push(err.message));
		await page.goto('/architecture');
		const graph = page.locator('svg[aria-label="Anemoi system"]');
		const source = (key: string) => graph.locator(`[data-source-node="${key}"]`);

		await expect(graph.locator('[data-source-node]')).toHaveCount(SOURCES.length);
		for (const { key } of SOURCES) await expect(source(key)).toBeVisible();

		// Three states, told apart in the node's own words.
		await expect(source('besttrack_working')).toHaveAttribute('data-use', 'input');
		await expect(source('besttrack_working')).toContainText('LSTM · PINN');
		await expect(source('gdas_gfs')).toContainText('CNN · Transformer · GNN · PINN');
		// ERA5 feeds the same models, in Stage A pretraining only.
		await expect(source('era5')).toHaveAttribute('data-use', 'input');
		await expect(source('era5')).toContainText('pretraining only');
		for (const key of ['dropsonde', 'ndbc']) {
			await expect(source(key)).toHaveAttribute('data-use', 'reference');
			await expect(source(key)).toContainText('verification only');
		}
		await expect(source('besttrack_final')).toHaveAttribute('data-use', 'reference');
		await expect(source('besttrack_final')).toContainText('labels · verification');
		for (const key of ['goes', 'microwave', 'sst_ohc', 'ensemble_perturbations']) {
			await expect(source(key)).toHaveAttribute('data-use', 'unused');
			await expect(source(key)).toContainText('not used yet');
		}
		// And by line, not colour: a source a model reads has a solid
		// outline and edge, one nothing reads yet a dashed outline and edge,
		// and labels or verification no edge into the pipeline at all.
		const edgeFrom = (key: string) => graph.locator(`[data-edge="src:${key}>prep"]`);
		const outline = (key: string) => source(key).locator(':scope > rect');
		await expect(edgeFrom('besttrack_working')).not.toHaveAttribute('stroke-dasharray');
		await expect(outline('besttrack_working')).not.toHaveAttribute('stroke-dasharray');
		await expect(edgeFrom('goes')).toHaveAttribute('stroke-dasharray');
		await expect(outline('goes')).toHaveAttribute('stroke-dasharray');
		await expect(edgeFrom('dropsonde')).toHaveCount(0);
		await expect(outline('dropsonde')).not.toHaveAttribute('stroke-dasharray');
		await expect(graph.locator('[data-edge$=">prep"]')).toHaveCount(3 + 4);

		// A screen reader gets the state in words, with no mark or line to
		// go on.
		for (const name of [
			'Working best-track: read by LSTM and PINN',
			'ERA5: read by CNN, Transformer, GNN and PINN, in pretraining only',
			'Final best-track: labels and verification only, never a model input',
			'Dropsondes: verification only, never a model input',
			'GOES imagery: not used yet',
		]) {
			await expect(graph.getByRole('img', { name, exact: true })).toHaveCount(1);
		}

		const legend = page.getByRole('list', { name: 'How a data source is drawn' });
		await expect(legend.getByRole('listitem')).toHaveText([
			'feeds a model',
			'labels or verification only, never a model input',
			'not used yet',
		]);

		// A beam per edge something travels in a forecast cycle: the two
		// sources a cycle's models read, then the eleven edges from
		// preprocessing on. ERA5's edge is solid, as the models do read
		// it, but carries no beam: nothing reads it in a cycle.
		const beams = graph.locator('.beam');
		const muted = graph.locator('.beam-muted');
		await expect(beams).toHaveCount(2 + 11);
		await expect(muted).toHaveCount(0);
		await expect(graph.locator('[data-beam="src:gdas_gfs>prep"]')).toHaveCount(1);
		await expect(graph.locator('[data-beam="src:era5>prep"]')).toHaveCount(0);
		await expect(edgeFrom('era5')).not.toHaveAttribute('stroke-dasharray');

		// Hovering a model keeps the sources it reads: the LSTM's is the
		// working best-track alone. Muted: the GDAS/GFS beam, and the other
		// three models' edges in and out.
		await page.getByRole('button', { name: /\(lstm\)/ }).hover();
		await expect(muted).toHaveCount(1 + 3 + 3);
		await expect(source('besttrack_working')).toHaveAttribute('opacity', '1');
		await expect(source('gdas_gfs')).toHaveAttribute('opacity', '0.45');

		// Hovering a source keeps the models that read it: GDAS/GFS feeds
		// the gridded three and PINN. Muted: the working best-track's beam,
		// and the LSTM's edge in and out.
		await source('gdas_gfs').hover();
		await expect(muted).toHaveCount(1 + 1 + 1);
		await expect(page.locator('[data-model-node="cnn"]')).toHaveAttribute('opacity', '1');
		await expect(page.locator('[data-model-node="lstm"]')).toHaveAttribute('opacity', '0.45');

		// A source nothing reads has no path to show, and mutes nothing.
		await source('dropsonde').hover();
		await expect(muted).toHaveCount(0);
		await source('goes').hover();
		await expect(muted).toHaveCount(0);
		expect(pageErrors).toEqual([]);
	});

	test('architecture draws the pipeline when the sources fail to load', async ({ page }) => {
		const pageErrors: string[] = [];
		page.on('pageerror', (err) => pageErrors.push(err.message));
		await serveInstead(page, '/v1/sources', { status: 503, json: { detail: 'registry offline' } });
		await page.goto('/architecture');
		const graph = page.locator('svg[aria-label="Anemoi system"]');

		// One stand-in where the sources go, a toast that offers a retry, and
		// the rest of the system as usual.
		await expect(graph.locator('[data-sources-pending]')).toContainText('not available right now');
		await expect(graph.locator('[data-source-node]')).toHaveCount(0);
		await expect(page.getByText('Could not load the data sources')).toBeVisible();
		await expect(page.getByRole('button', { name: /\(lstm\)/ })).toBeVisible();
		await expect(graph.locator('.beam')).toHaveCount(11);
		await expect(page.getByRole('list', { name: 'How a data source is drawn' })).toHaveCount(0);

		// Retry, with the API back.
		await page.unroute('**/api/v1/sources');
		await page.getByRole('button', { name: 'Retry' }).click();
		await expect(graph.locator('[data-source-node]')).toHaveCount(SOURCES.length);
		await expect(graph.locator('[data-sources-pending]')).toHaveCount(0);
		expect(pageErrors).toEqual([]);
	});

	test('architecture draws no source as feeding a model when the API predates used_by', async ({ page }) => {
		await serveInstead(page, '/v1/sources', { json: SOURCES_BEFORE_USED_BY });
		await page.goto('/architecture');
		const graph = page.locator('svg[aria-label="Anemoi system"]');

		await expect(graph.locator('[data-source-node]')).toHaveCount(SOURCES.length);
		await expect(graph.locator('[data-source-node][data-use="unknown"]')).toHaveCount(SOURCES.length);
		await expect(graph.getByText('not used yet')).toHaveCount(0);
		// No beam leaves a source: only the eleven edges from preprocessing on.
		await expect(graph.locator('.beam')).toHaveCount(11);
		// And every source's edge is dashed, the way an unused one's is: a
		// solid edge would say the labels-only final best-track feeds the
		// models.
		const sourceEdges = graph.locator('[data-edge$=">prep"]');
		await expect(sourceEdges).toHaveCount(SOURCES.length);
		for (const edge of await sourceEdges.all()) await expect(edge).toHaveAttribute('stroke-dasharray');
		await expect(page.getByText("This API doesn't say what uses each source")).toBeVisible();
		await expect(graph.getByRole('img', { name: 'GOES imagery: use not reported', exact: true })).toHaveCount(1);
	});

	test('architecture draws whatever used_by says, not a mapping of its own', async ({ page }) => {
		await serveInstead(page, '/v1/sources', { json: SOURCES_REWIRED });
		await page.goto('/architecture');
		const graph = page.locator('svg[aria-label="Anemoi system"]');
		const source = (key: string) => graph.locator(`[data-source-node="${key}"]`);
		const edgeFrom = (key: string) => graph.locator(`[data-edge="src:${key}>prep"]`);
		const beamFrom = (key: string) => graph.locator(`[data-beam="src:${key}>prep"]`);

		// One node per row, all inside the drawing: eleven sources make
		// the graph taller than the ten it is sized for.
		await expect(graph.locator('[data-source-node]')).toHaveCount(SOURCES_REWIRED.length);
		const svg = (await graph.boundingBox())!;
		for (const node of await graph.locator('[data-source-node]').all()) {
			const box = (await node.boundingBox())!;
			expect(box.y).toBeGreaterThanOrEqual(svg.y);
			expect(box.y + box.height).toBeLessThanOrEqual(svg.y + svg.height);
		}

		await expect(source('goes')).toHaveAttribute('data-use', 'input');
		await expect(source('goes')).toContainText('GNN');
		await expect(edgeFrom('goes')).not.toHaveAttribute('stroke-dasharray');
		await expect(beamFrom('goes')).toHaveCount(1);

		await expect(source('besttrack_working')).toHaveAttribute('data-use', 'unused');
		await expect(source('besttrack_working')).toContainText('not used yet');
		await expect(edgeFrom('besttrack_working')).toHaveAttribute('stroke-dasharray');
		await expect(beamFrom('besttrack_working')).toHaveCount(0);

		await expect(source('new_feed')).toHaveAttribute('data-use', 'input');
		await expect(source('new_feed')).toContainText('new_feed'); // no name for it: its key
		await expect(source('new_feed')).toContainText('LSTM');
		await expect(beamFrom('new_feed')).toHaveCount(1);

		// GOES, GDAS/GFS and the new feed, then the eleven edges from
		// preprocessing on.
		const muted = graph.locator('.beam-muted');
		await expect(graph.locator('.beam')).toHaveCount(3 + 11);

		// The LSTM now reads the new feed and nothing else. Muted: GDAS/GFS
		// and GOES, and the other three models' edges in and out.
		await page.getByRole('button', { name: /\(lstm\)/ }).hover();
		await expect(muted).toHaveCount(2 + 3 + 3);
		await expect(source('new_feed')).toHaveAttribute('opacity', '1');
		await expect(source('goes')).toHaveAttribute('opacity', '0.45');
		await expect(source('besttrack_working')).toHaveAttribute('opacity', '0.45');

		// GOES lights the GNN alone. Muted: the other two sources' beams,
		// and the other three models' edges in and out.
		await source('goes').hover();
		await expect(muted).toHaveCount(2 + 3 + 3);
		await expect(page.locator('[data-model-node="gnn"]')).toHaveAttribute('opacity', '1');
		await expect(page.locator('[data-model-node="cnn"]')).toHaveAttribute('opacity', '0.45');
		await expect(page.locator('[data-model-node="lstm"]')).toHaveAttribute('opacity', '0.45');
	});

	test('architecture keeps a source line longer than its box inside the box', async ({ page }) => {
		const all = ['lstm', 'cnn', 'transformer', 'gnn', 'pinn'];
		await serveInstead(page, '/v1/sources', { json: sourcesWith({ goes: all }) });
		await page.goto('/architecture');
		const goes = page.locator('[data-source-node="goes"]');
		await expect(goes).toContainText('LSTM · CNN · Transformer · GNN · PINN');

		// The line is wider than the box, and drawn clipped to it.
		const fit = await goes.evaluate((node) => {
			const box = node.querySelector(':scope > rect')!.getBBox();
			const line = node.querySelectorAll<SVGTextElement>('[data-source-text] text')[1];
			const clipId = node.querySelector('[data-source-text]')!.getAttribute('clip-path')!.slice(5, -1);
			const clip = document.getElementById(clipId)!.querySelector('rect')!.getBBox();
			return {
				overflows: line.getBBox().x + line.getComputedTextLength() > box.x + box.width,
				clipInside: clip.x >= box.x && clip.x + clip.width <= box.x + box.width,
			};
		});
		expect(fit).toEqual({ overflows: true, clipInside: true });
		// What the clip cuts off is still in its name.
		await expect(
			page.getByRole('img', { name: 'GOES imagery: read by LSTM, CNN, Transformer, GNN and PINN', exact: true }),
		).toHaveCount(1);
	});

	// A newer API may name a use this console doesn't know. It may not be a
	// model, so it must not be drawn as feeding one.
	test('architecture draws a use it does not know without claiming it feeds a model', async ({ page }) => {
		await serveInstead(page, '/v1/sources', { json: sourcesWith({ goes: ['calibration'] }) });
		await page.goto('/architecture');
		const graph = page.locator('svg[aria-label="Anemoi system"]');
		const goes = graph.locator('[data-source-node="goes"]');

		await expect(goes).toHaveAttribute('data-use', 'unknown');
		await expect(goes).toContainText('calibration');
		await expect(
			graph.getByRole('img', { name: "GOES imagery: calibration, a use this console doesn't know", exact: true }),
		).toHaveCount(1);
		await expect(graph.locator('[data-edge="src:goes>prep"]')).toHaveAttribute('stroke-dasharray');
		await expect(graph.locator('.beam')).toHaveCount(2 + 11); // the same beams as always
		await expect(page.getByText("A use this console doesn't know is named as the API sends it")).toBeVisible();
		await expect(page.getByText("This API doesn't say what uses each source")).toHaveCount(0);
	});

	test('architecture on a phone: the graph scrolls sideways, the page does not', async ({ page }) => {
		await page.setViewportSize(PHONE);
		await page.goto('/architecture');
		const graph = page.locator('svg[aria-label="Anemoi system"]');
		const scroller = graph.locator('xpath=..');
		await expect(graph.locator('[data-source-node]')).toHaveCount(SOURCES.length);

		// The graph is wider than the screen, and says it scrolls.
		expect(await scroller.evaluate((el) => el.scrollWidth - el.clientWidth)).toBeGreaterThan(0);
		await expect(page.getByText('Scroll the graph sideways')).toBeVisible();
		expect(await sidewaysOverflow(page)).toBe(0);

		// The far end of the pipeline starts off-screen and is reached by
		// scrolling the graph, with the page staying where it is.
		const last = page.getByRole('button', { name: /\(diffusion\)/ });
		await expect(last).not.toBeInViewport();
		await scroller.evaluate((el) => el.scrollTo({ left: el.scrollWidth }));
		await expect(last).toBeInViewport({ ratio: 1 });
		const box = (await last.boundingBox())!;
		expect(box.x).toBeGreaterThanOrEqual(0);
		expect(box.x + box.width).toBeLessThanOrEqual(PHONE.width);
		expect(await page.evaluate(() => window.scrollX)).toBe(0);
		expect(await sidewaysOverflow(page)).toBe(0);

		// And back: the first source is in view again.
		await scroller.evaluate((el) => el.scrollTo({ left: 0 }));
		await expect(graph.locator('[data-source-node="besttrack_working"]')).toBeInViewport({ ratio: 1 });
	});

	// Between a phone and a desktop the graph card is narrower than the
	// graph. It keeps its desktop size and scrolls, rather than shrinking
	// its text below what a desktop shows.
	test('architecture keeps the graph its desktop size on a small laptop', async ({ page }) => {
		const graph = page.locator('svg[aria-label="Anemoi system"]');
		const scroller = graph.locator('xpath=..');
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/architecture');
		await expect(graph.locator('[data-source-node]')).toHaveCount(SOURCES.length);
		const desktop = (await graph.boundingBox())!.width;
		expect(await scroller.evaluate((el) => el.scrollWidth - el.clientWidth)).toBe(0);
		await expect(page.getByText('Scroll the graph sideways')).toHaveCount(0);

		await page.setViewportSize({ width: 1024, height: 768 });
		await expect(page.getByText('Scroll the graph sideways')).toBeVisible();
		expect((await graph.boundingBox())!.width).toBeGreaterThanOrEqual(desktop - 8);
		expect(await scroller.evaluate((el) => el.scrollWidth - el.clientWidth)).toBeGreaterThan(0);
		expect(await sidewaysOverflow(page)).toBe(0);
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

	test('sources says whatever used_by says, not a mapping of its own', async ({ page }) => {
		await serveInstead(page, '/v1/sources', { json: SOURCES_REWIRED });
		await page.goto('/sources');
		await expect(await sourceCell(page, 'goes', 'Used by')).toHaveText('GNN');
		await expect(await sourceCell(page, 'besttrack_working', 'Used by')).toHaveText('not used yet');
		await expect(await sourceCell(page, 'new_feed', 'Used by')).toHaveText('LSTM');
		await expect(page.getByRole('row')).toHaveCount(1 + SOURCES_REWIRED.length);
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
