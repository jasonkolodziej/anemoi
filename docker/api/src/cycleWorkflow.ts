/**
 * The operational cycle for every active storm, as a Cloudflare Workflow.
 *
 * This ran as one `scheduled()` invocation (`runDueCycles`, #178): every
 * storm's cycle one after another inside a single cron execution, with no
 * retries -- a storm whose cycle failed or timed out waited six hours for
 * the next synoptic time, and a busy day with several active storms risked
 * outrunning the cron's own time limit, leaving the last storms without a
 * cycle. Each piece is now its own durable step: a failed step retries on
 * its own, a finished step is never re-run, and one storm's failure never
 * stops the others.
 *
 *   find active storms -> run cycle {storm} (one step each) -> refresh read cache
 *     -> calibration audit -> archive atcf -> skew audit
 *
 * The cron starts one instance per cycle label (`index.ts`'s `scheduled`),
 * with the label as the instance id, so an at-least-once duplicate cron
 * firing can't start a second run of the same cycle.
 */
import { getContainer } from '@cloudflare/containers';
import { WorkflowEntrypoint, type WorkflowEvent, type WorkflowStep } from 'cloudflare:workers';
import { type ContainerFetch, putCycleResult, refreshStormSnapshot } from './readCache';
import { RUN_SOURCE_HEADER, classifyCycleResponse } from './routing';

export interface CycleParams {
	/** Synoptic cycle label, e.g. `20261008_06Z`. */
	cycleLabel: string;
}

interface StormSummaryOut {
	storm_id: string;
	active: boolean;
}

/** Workflow instance ids are one per cycle label. */
export const cycleInstanceId = (cycleLabel: string) => `cycle-${cycleLabel}`;

/** A real cycle runs torch inference for the full ensemble in the
 * container; the retry delay gives a container that failed mid-start time
 * to come back before the next attempt. */
const CYCLE_STEP = {
	retries: { limit: 2, delay: '2 minutes', backoff: 'exponential' },
	timeout: '20 minutes',
} as const;

/** Replays a handful of cycles through every model on ERA5T fields: heavier
 * than the light steps, far lighter than a full ensemble cycle. */
const SKEW_STEP = {
	retries: { limit: 1, delay: '2 minutes', backoff: 'exponential' },
	timeout: '15 minutes',
} as const;

const LIGHT_STEP = {
	retries: { limit: 3, delay: '30 seconds', backoff: 'exponential' },
	timeout: '5 minutes',
} as const;

export class CycleWorkflow extends WorkflowEntrypoint<Env, CycleParams> {
	async run(event: Readonly<WorkflowEvent<CycleParams>>, step: WorkflowStep) {
		const { cycleLabel } = event.payload;
		const fetchContainer: ContainerFetch = (req) => getContainer(this.env.ANEMOI_REAL_API).fetch(req);
		// Logged only from inside step bodies: the Workflows runtime re-runs
		// `run` from the top on every resume, replaying finished steps from
		// their stored results, so a log line outside a step would repeat
		// once per later step. Final outcomes are the instance's output.
		const log = (msg: string) => console.log(`cycle workflow ${cycleLabel}: ${msg}`);

		const due = await step.do('find due storms', LIGHT_STEP, async () => {
			const res = await fetchContainer(new Request('https://internal/v1/storms'));
			if (!res.ok) throw new Error(`GET /v1/storms -> ${res.status}`);
			const storms = (await res.json()) as StormSummaryOut[];
			// Every active storm, including one whose last cycle already has
			// this label: that may be a manual run, which the scheduled run
			// replaces. The API answers 409 `exists` when the scheduled run
			// already happened (#212).
			const due = storms.filter((s) => s.active).map((s) => s.storm_id);
			log(`${due.length} active storm(s)`);
			return due;
		});

		const outcomes: Record<string, string> = {};
		for (const stormId of due) {
			try {
				outcomes[stormId] = await step.do(`run cycle ${stormId}`, CYCLE_STEP, async () => {
					try {
						const outcome = await runStormCycle(fetchContainer, this.env.READ_CACHE, stormId, cycleLabel);
						log(`${stormId} -> ${outcome}`);
						return outcome;
					} catch (err) {
						log(`${stormId} attempt failed: ${err instanceof Error ? err.message : String(err)}`);
						throw err;
					}
				});
			} catch (err) {
				// Retries exhausted: record it and carry on with the other storms.
				outcomes[stormId] = `failed: ${err instanceof Error ? err.message : String(err)}`;
			}
		}

		// Both post-cycle steps run even if a storm failed: the snapshot
		// should reflect whatever did run, and the audit covers older cycles.
		let snapshot = 'failed';
		try {
			snapshot = await step.do('refresh read cache', LIGHT_STEP, async () => {
				await refreshStormSnapshot(this.env.READ_CACHE, fetchContainer);
				log('read cache refreshed');
				return 'ok';
			});
		} catch {
			/* retries exhausted; recorded in the output below */
		}
		let audit = 'failed';
		try {
			audit = await step.do('calibration audit', LIGHT_STEP, async () => {
				const res = await fetchContainer(
					new Request('https://internal/v1/internal/calibration-audit', { method: 'POST' }),
				);
				const body = await res.text();
				log(`calibration audit -> ${res.status} ${body}`);
				if (!res.ok) throw new Error(`calibration audit -> ${res.status}`);
				return body;
			});
		} catch {
			/* retries exhausted; recorded in the output below */
		}

		// Last, so it never delays a cycle: NHC's as-issued files (TC-Vitals,
		// b-deck, a-deck, CurrentStorms.json) copied to R2 before NHC
		// overwrites or drops them -- the working half of the (working, final)
		// pairs retraining needs (#213, `data.atcf_archive`).
		let archive = 'failed';
		try {
			archive = await step.do('archive atcf', LIGHT_STEP, async () => {
				const res = await fetchContainer(new Request('https://internal/v1/internal/archive-atcf', { method: 'POST' }));
				const body = await res.text();
				log(`archive atcf -> ${res.status} ${body.slice(0, 300)}`);
				if (!res.ok) throw new Error(`archive atcf -> ${res.status}`);
				return body;
			});
		} catch {
			/* retries exhausted; recorded in the output below */
		}

		// The §4.6.3 ERA5T skew audit (#216), in the same container and code
		// that served the cycles it replays. Bounded per pass so the step
		// stays short; whatever's left is taken by the next cycle's pass.
		// Nothing ran `anemoi skew-audit` on a schedule before.
		let skew = 'failed';
		try {
			skew = await step.do('skew audit', SKEW_STEP, async () => {
				const res = await fetchContainer(
					new Request('https://internal/v1/internal/skew-audit?max_records=6', { method: 'POST' }),
				);
				const body = await res.text();
				log(`skew audit -> ${res.status} ${body.slice(0, 300)}`);
				if (!res.ok) throw new Error(`skew audit -> ${res.status}`);
				return body;
			});
		} catch {
			/* retries exhausted; recorded in the output below */
		}

		return { cycleLabel, outcomes, snapshot, audit, archive, skew };
	}
}

/**
 * One storm's cycle. Safe to retry: the API refuses a second scheduled run
 * of a label (409 `exists`, reported as done) and a run of a label already
 * running (409 `in_progress`, thrown so the step retries once the first
 * finishes). Any other 4xx is the container refusing the request (unknown
 * storm, a cycle outside the storm's track) -- retrying can't change that,
 * so it is a completed step with a "refused" outcome rather than a thrown
 * error. (`NonRetryableError` would fail the whole instance, not just this
 * storm.)
 *
 * No `members`: the API's default is the full operational ensemble
 * (`configs/inference.yaml`). This sent 20 until #212, so every scheduled
 * cycle since #188 raised the default to 50 was a reduced ensemble.
 */
async function runStormCycle(
	fetchContainer: ContainerFetch,
	kv: KVNamespace,
	stormId: string,
	cycleLabel: string,
): Promise<string> {
	const res = await fetchContainer(
		new Request(`https://internal/v1/storms/${stormId}/cycles`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', [RUN_SOURCE_HEADER]: 'scheduled' },
			body: JSON.stringify({ cycle: cycleLabel }),
		}),
	);
	const body = await res.text();
	switch (classifyCycleResponse(res.status, body)) {
		case 'ran':
			await putCycleResult(kv, stormId, body);
			return `ran (${res.status})`;
		case 'done':
			return 'already run';
		case 'refused':
			return `refused: ${res.status} ${body.slice(0, 200)}`;
		case 'retry':
			throw new Error(`${res.status} ${body.slice(0, 200)}`);
	}
}
