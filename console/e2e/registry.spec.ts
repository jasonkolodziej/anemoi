import { test, expect } from '@playwright/test';

// #92 gap 1: the registry table silently dropped tags/checkpoint_uri/
// input_flavor/latent_signature before this -- these assert the new
// "Provenance" column actually renders what the real (not mocked) demo
// API returns, catching a schema/convert regression the API-side
// round-trip test (tests/test_api_smoke.py) can't: that one only proves
// the fields survive the HTTP boundary, not that the frontend does
// anything with them once they arrive.

test('registry page renders provenance for a seeded demo version', async ({ page }) => {
	await page.goto('/registry');

	const lstmRow = page.getByRole('row', { name: /^lstm/ });
	await expect(lstmRow).toBeVisible();

	// Demo-seeded lstm has no checkpoint_uri (#78's provenance only exists
	// for real training runs, not the synthetic demo seed) -- the fallback
	// text is exactly as much a real behavior as the populated case.
	await expect(lstmRow.getByText('no checkpoint_uri')).toBeVisible();

	// tags={"input_flavor": "gdas_finetune", "nwp_cycle_lag": "6"} from
	// api/demo_state.py's _seed_registry -- no arch_params/git_commit/
	// storm_split/gpu_type tag, so neither the arch_params badge nor the
	// tag-summary line should render for this row.
	await expect(lstmRow.getByText('arch_params')).toHaveCount(0);
});

test('registry page renders a latent_signature-derived pin for fusion', async ({ page }) => {
	await page.goto('/registry');

	// fusion is a DERIVED_MODELS entry -- api/demo_state.py registers it
	// with a real latent_signature (unlike lstm, a Group 1 model, which has
	// none). The active-pin card at the top of the page is built from that
	// same signature, so its presence is a real (not just schema-level)
	// signal the provenance fields are wired through end to end.
	await expect(page.getByText(/Active pin/)).toBeVisible();
	await expect(page.getByText(/latent signature:/)).toBeVisible();
});
