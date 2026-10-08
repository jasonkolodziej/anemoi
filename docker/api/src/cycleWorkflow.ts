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
 *   find due storms -> run cycle {storm} (one step each) -> refresh read cache -> calibration audit
 *
 * The cron starts one instance per cycle label (`index.ts`'s `scheduled`),
 * with the label as the instance id, so an at-least-once duplicate cron
 * firing can't start a second run of the same cycle.
 */
import { getContainer } from '@cloudflare/containers';
import { WorkflowEntrypoint, type WorkflowEvent, type WorkflowStep } from 'cloudflare:workers';
import { type ContainerFetch, putCycleResult, refreshStormSnapshot } from './readCache';

export interface CycleParams {
	/** Synoptic cycle label, e.g. `20261008_06Z`. */
	cycleLabel: string;
}

interface StormSummaryOut {
	storm_id: string;
	active: boolean;
	last_cycle: string | null;
}

interface StormDetailOut {
	cycles: string[];
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
			const active = storms.filter((s) => s.active);
			// Idempotent against `last_cycle`, as before: the cron could also
			// overlap a cycle someone ran by hand.
			const due = active.filter((s) => s.last_cycle !== cycleLabel).map((s) => s.storm_id);
			log(`${due.length}/${active.length} active storm(s) due`);
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

		return { cycleLabel, outcomes, snapshot, audit };
	}
}

/**
 * One storm's cycle. Safe to retry: a previous attempt that ran the cycle
 * but lost its response is detected from the storm's own cycle list rather
 * than run twice. A 4xx is the container refusing the request (unknown
 * storm, a cycle that hasn't started) -- retrying can't change that, so it
 * is a completed step with a "refused" outcome rather than a thrown error.
 * (`NonRetryableError` would fail the whole instance, not just this storm.)
 */
async function runStormCycle(
	fetchContainer: ContainerFetch,
	kv: KVNamespace,
	stormId: string,
	cycleLabel: string,
): Promise<string> {
	const detail = await fetchContainer(new Request(`https://internal/v1/storms/${stormId}`));
	if (detail.ok && ((await detail.json()) as StormDetailOut).cycles.includes(cycleLabel)) {
		return 'already run';
	}

	const res = await fetchContainer(
		new Request(`https://internal/v1/storms/${stormId}/cycles`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ cycle: cycleLabel, members: 20 }),
		}),
	);
	const body = await res.text();
	if (res.status >= 400 && res.status < 500) return `refused: ${res.status} ${body.slice(0, 200)}`;
	if (!res.ok) throw new Error(`${res.status} ${body}`);
	await putCycleResult(kv, stormId, body);
	return `ran (${res.status})`;
}
