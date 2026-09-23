/**
 * Worker front door for real-mode Anemoi-API (issue #91). Routes every
 * request into the AnemoiRealApi container, which runs the same FastAPI
 * app (`anemoi.api.main:app`, `ANEMOI_API_REAL_STATE=1`) as the reference
 * deployment -- Cloudflare's own Container class handles instance
 * lifecycle (start/sleep/restart), this Worker just forwards.
 *
 * Deliberately minimal for the #91 spike: no demo/real split, no caching,
 * no auth beyond whatever `ANEMOI_API_KEY` the container itself enforces
 * (see anemoi.api.deps.require_api_key). The demo-vs-real routing and edge
 * caching described in #91's "Proposed scope of work" step 3 are a
 * follow-up once this container is confirmed deployable for real.
 */
import { Container, getContainer } from '@cloudflare/containers';
import type { DurableObject } from 'cloudflare:workers';

/**
 * `wrangler secret put` sets Worker-level bindings, not container
 * environment variables -- `@cloudflare/containers`' own `Container.envVars`
 * defaults to `{}` and is never auto-populated from `env` (checked directly
 * against the installed package's source, `dist/lib/container.js`). Without
 * forwarding these explicitly, S3_ARTIFACT_* never reaches the container's
 * Python process at all: `CheckpointStore`/`ModelRegistry`'s
 * `S3Config.from_env()` would find them unset, but `RealState.run_cycle`'s
 * deterministic path swallows that into a silent synthetic fallback (see
 * `real_state.py`), so this gap produced no visible error before being
 * found by reading the SDK source directly.
 *
 * `wrangler types` has no way to know these secret names exist (they're
 * not declared in `wrangler.jsonc`'s bindings, just set via the API/CLI),
 * so this small extension is hand-maintained, not part of the generated
 * `Env` in `worker-configuration.d.ts`.
 */
interface RealApiEnv extends Env {
	S3_ARTIFACT_API_ENDPOINT: string;
	S3_ARTIFACT_BUCKET: string;
	S3_ARTIFACT_ACCESS_KEYID: string;
	S3_ARTIFACT_SECRET_ACCESS_KEY: string;
}

const SLEEP_DEADLINE_KEY = 'sleepAfterMs';

// Tracked outside the instance so it can't be reset by class-field
// initialization, whenever the base constructor happens to first call
// renewActivityTimeout().
const sleepDeadlineRestored = new WeakSet<object>();

export class AnemoiRealApi extends Container<RealApiEnv> {
	defaultPort = 8080;
	// Real cycles run four times a day (per synoptic time), not
	// continuously -- sleep fairly quickly between bursts rather than
	// paying for an idle container, matching Containers' pay-per-active-
	// second billing model.
	sleepAfter = '5m';

	constructor(ctx: DurableObject['ctx'], env: RealApiEnv) {
		super(ctx, env, {
			envVars: {
				S3_ARTIFACT_API_ENDPOINT: env.S3_ARTIFACT_API_ENDPOINT,
				S3_ARTIFACT_BUCKET: env.S3_ARTIFACT_BUCKET,
				S3_ARTIFACT_ACCESS_KEYID: env.S3_ARTIFACT_ACCESS_KEYID,
				S3_ARTIFACT_SECRET_ACCESS_KEY: env.S3_ARTIFACT_SECRET_ACCESS_KEY,
			},
		});
	}

	/**
	 * `@cloudflare/containers` (0.3.7) keeps the idle deadline only in
	 * memory and resets it to now + `sleepAfter` in its constructor, so every
	 * time the runtime re-creates this Durable Object (eviction between
	 * alarms, redeploys) the container got a fresh window no matter how long
	 * it had really been idle -- measured keeping it awake for hours with no
	 * traffic (#172). Persisting the deadline makes that first,
	 * constructor-driven call restore it instead; every later call is real
	 * activity and renews as normal.
	 */
	override renewActivityTimeout(): void {
		const self = this as unknown as { sleepAfterMs: number };
		if (!sleepDeadlineRestored.has(this)) {
			sleepDeadlineRestored.add(this);
			const persisted = this.ctx.storage.kv.get<number>(SLEEP_DEADLINE_KEY);
			if (persisted !== undefined) {
				self.sleepAfterMs = persisted;
				return;
			}
		}
		super.renewActivityTimeout();
		this.ctx.storage.kv.put(SLEEP_DEADLINE_KEY, self.sleepAfterMs);
	}

	override onStart() {
		console.log('anemoi-api-real container started');
	}

	override onStop() {
		console.log('anemoi-api-real container stopped');
	}

	override onError(error: unknown) {
		console.error('anemoi-api-real container error:', error);
	}
}

//: Synoptic hours per Scope v2.1 §6.2 (`time_utils.SYNOPTIC_HOURS`) -- kept
// in sync by hand, not imported, since this is TypeScript reaching for a
// Python constant across the container boundary.
const SYNOPTIC_HOURS = [0, 6, 12, 18];

/** The synoptic cycle label containing `now`, e.g. `20260923_18Z` -- the
 * TS equivalent of `time_utils.cycle_label(time_utils.floor_synoptic(now))`.
 * Always `<= now` by construction, so it always clears `RealState.run_cycle`'s
 * own "hasn't started yet" guard. */
function currentCycleLabel(now: Date): string {
	const hour = SYNOPTIC_HOURS.filter((h) => h <= now.getUTCHours()).pop()!;
	const y = now.getUTCFullYear();
	const m = String(now.getUTCMonth() + 1).padStart(2, '0');
	const d = String(now.getUTCDate()).padStart(2, '0');
	return `${y}${m}${d}_${String(hour).padStart(2, '0')}Z`;
}

interface StormSummaryOut {
	storm_id: string;
	active: boolean;
	last_cycle: string | null;
}

/**
 * Runs the real operational cycle for every currently-active storm (#178:
 * nothing triggered a real cycle automatically -- every one in
 * production so far was a manual `POST .../cycles`, which is also why
 * drift/skew monitoring had almost no real samples to report on). Scheduled
 * `t+1:30` after each synoptic time (`wrangler.jsonc`'s cron), 10 minutes
 * past `scheduler.derive_vitals_timeout()`'s own real `t+1:20` -- by firing
 * time, TC-Vitals has either landed or the real `vitals_estimated` fallback
 * `RealState.run_cycle` already has is the honest answer, not a race against
 * it. Idempotent against `last_cycle` so a retried/duplicate invocation
 * (Cron Triggers are at-least-once) doesn't double-run a cycle; one storm's
 * failure is logged and does not stop the rest (`wrangler tail` is where
 * this becomes visible -- there is no dashboard for it otherwise).
 */
async function runDueCycles(env: Env, cycleLabel: string): Promise<void> {
	const container = getContainer(env.ANEMOI_REAL_API);
	let storms: StormSummaryOut[];
	try {
		const stormsRes = await container.fetch(new Request('https://internal/v1/storms'));
		if (!stormsRes.ok) {
			console.error(`scheduled cycle: GET /v1/storms -> ${stormsRes.status}, aborting`);
			return;
		}
		const body: unknown = await stormsRes.json();
		if (!Array.isArray(body)) {
			console.error('scheduled cycle: GET /v1/storms did not return an array, aborting', body);
			return;
		}
		storms = body as StormSummaryOut[];
	} catch (err) {
		// Network error, or the container never woke up -- a per-storm try/
		// catch further down can't help here, since there's no list to loop
		// over yet. Real gap Copilot review caught on this PR (#179): an
		// unhandled throw here previously took the whole scheduled
		// invocation down noisily instead of a clear logged abort.
		console.error('scheduled cycle: GET /v1/storms threw, aborting', err);
		return;
	}
	const active = storms.filter((s) => s.active);
	console.log(`scheduled cycle ${cycleLabel}: ${active.length}/${storms.length} storm(s) active`);

	for (const storm of active) {
		if (storm.last_cycle === cycleLabel) {
			console.log(`scheduled cycle ${cycleLabel}: ${storm.storm_id} already has it, skipping`);
			continue;
		}
		try {
			const res = await container.fetch(
				new Request(`https://internal/v1/storms/${storm.storm_id}/cycles`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ cycle: cycleLabel, members: 20 }),
				}),
			);
			if (!res.ok) {
				console.error(
					`scheduled cycle ${cycleLabel}: ${storm.storm_id} -> ${res.status} ${await res.text()}`,
				);
			} else {
				console.log(`scheduled cycle ${cycleLabel}: ${storm.storm_id} -> ${res.status}`);
			}
		} catch (err) {
			console.error(`scheduled cycle ${cycleLabel}: ${storm.storm_id} threw`, err);
		}
	}
}

export default {
	async fetch(request, env) {
		const container = getContainer(env.ANEMOI_REAL_API);
		return container.fetch(request);
	},

	async scheduled(controller, env, ctx) {
		const cycleLabel = currentCycleLabel(new Date(controller.scheduledTime));
		ctx.waitUntil(runDueCycles(env, cycleLabel));
	},
} satisfies ExportedHandler<Env>;
