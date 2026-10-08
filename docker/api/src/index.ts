/**
 * Worker front door for real-mode Anemoi-API (issue #91). Routes every
 * request into the AnemoiRealApi container, which runs the same FastAPI
 * app (`anemoi.api.main:app`, `ANEMOI_API_REAL_STATE=1`) as the reference
 * deployment -- Cloudflare's own Container class handles instance
 * lifecycle (start/sleep/restart), this Worker just forwards.
 *
 * #171: every request through the exported `fetch` handler now needs a
 * valid per-customer API key (console-issued, verified against the same
 * D1 database console binds as AUTH_DB) before it reaches the container --
 * a rejected request never wakes the billed container. `scheduled()`'s
 * cycle Workflow is unaffected: it calls `container.fetch()` directly on
 * the Durable Object binding, bypassing this gate entirely.
 * Reads of the storm list, a storm, and a stored cycle are served from KV
 * (src/readCache.ts) without waking the container; every cycle run --
 * cron or manual POST -- refreshes what they serve. Demo-vs-real routing
 * from #91's "Proposed scope of work" step 3 remains a follow-up.
 */
import { Container, getContainer } from '@cloudflare/containers';
import type { DurableObject } from 'cloudflare:workers';
import { verifyApiKey } from './auth';
import { recordCycleRun } from './metering';
import { cycleInstanceId } from './cycleWorkflow';
import { type ContainerFetch, putCycleResult, readThrough, refreshStormSnapshot } from './readCache';

export { CycleWorkflow } from './cycleWorkflow';

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
 *
 * `INTERNAL_PROXY_SECRET` is a second secret in the same category (#171):
 * shared with console's own Worker (set via `wrangler secret put` on
 * both), proving a request arrived through console's `/api/*` proxy
 * (console/src/routes/api/[...path]/+server.ts) rather than the public
 * internet. Needed because better-auth never returns a key's raw value
 * after creation -- only its hash is stored (`apikey.key`) -- so console
 * cannot "look up" a user's key to attach server-side the way a first
 * draft of this design assumed. Console already resolves the session
 * itself (hooks.server.ts); this secret is what lets it hand that
 * resolved identity to this Worker without re-deriving auth from a key
 * that doesn't exist in retrievable form.
 */
interface RealApiEnv extends Env {
	S3_ARTIFACT_API_ENDPOINT: string;
	S3_ARTIFACT_BUCKET: string;
	S3_ARTIFACT_ACCESS_KEYID: string;
	S3_ARTIFACT_SECRET_ACCESS_KEY: string;
	INTERNAL_PROXY_SECRET: string;
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

/**
 * Start the operational cycle for every active storm (#178) as a durable
 * Workflow instance (src/cycleWorkflow.ts). Scheduled `t+1:30` after each
 * synoptic time (`wrangler.jsonc`'s cron), 10 minutes past
 * `scheduler.derive_vitals_timeout()`'s own real `t+1:20` -- by firing time,
 * TC-Vitals has either landed or `RealState.run_cycle`'s `vitals_estimated`
 * fallback is the honest answer, not a race against it.
 *
 * The instance id is the cycle label, so a duplicate cron firing (Cron
 * Triggers are at-least-once) finds the instance already exists instead of
 * starting a second run.
 */
async function startCycleWorkflow(env: Env, cycleLabel: string): Promise<void> {
	const id = cycleInstanceId(cycleLabel);
	try {
		await env.CYCLE_WORKFLOW.create({ id, params: { cycleLabel } });
		console.log(`scheduled cycle ${cycleLabel}: started workflow instance ${id}`);
	} catch (err) {
		try {
			const existing = await env.CYCLE_WORKFLOW.get(id);
			console.log(`scheduled cycle ${cycleLabel}: ${id} already exists (${(await existing.status()).status}), not restarting`);
		} catch {
			console.error(`scheduled cycle ${cycleLabel}: could not start ${id}`, err);
		}
	}
}

/** Matches `POST /v1/storms/{storm_id}/cycles` -- the route that wakes
 * the billed container and runs real inference, gated tighter than
 * everything else. */
const CYCLE_POST_RE = /^\/v1\/storms\/([^/]+)\/cycles\/?$/;

/** Maintenance routes only this Worker's own cron calls, through the
 * container binding directly -- never reachable from the public route. */
const INTERNAL_RE = /^\/v1\/internal(\/|$)/i;

/** Checked on the decoded path: the container's router decodes it too, so
 * `/v1/%69nternal/...` would otherwise slip past a raw-path match. An
 * undecodable path is refused outright rather than guessed at. */
function isInternalPath(pathname: string): boolean {
	try {
		return INTERNAL_RE.test(decodeURIComponent(pathname));
	} catch {
		return true;
	}
}

/**
 * Resolve the calling user id, trying two paths:
 *
 * 1. Console's own proxy (`console/src/routes/api/[...path]/+server.ts`),
 *    identified by a shared secret only the two Workers know. Console has
 *    already resolved its own session and is vouching for the
 *    `X-Anemoi-User-Id` it sends -- this Worker can't re-derive that
 *    itself, since better-auth never returns a key's raw value after
 *    creation (only `apikey.key`, the hash).
 * 2. A real customer API key (`X-Anemoi-Api-Key`), verified against
 *    `AUTH_DB` -- the actual per-customer path #171 is about.
 *
 * Constant-time comparison isn't used for the secret check: it's a
 * fixed, operator-controlled value compared once per request, not a
 * per-user credential where timing leaks matter across many attempts.
 */
async function resolveUserId(
	request: Request,
	env: RealApiEnv,
	ctx: ExecutionContext,
): Promise<string | null> {
	const internalSecret = request.headers.get('X-Anemoi-Internal-Secret');
	if (internalSecret && env.INTERNAL_PROXY_SECRET && internalSecret === env.INTERNAL_PROXY_SECRET) {
		return request.headers.get('X-Anemoi-User-Id');
	}
	const apiKey = request.headers.get('X-Anemoi-Api-Key');
	return verifyApiKey(env.AUTH_DB, ctx, apiKey);
}

export default {
	async fetch(request, env, ctx) {
		const url = new URL(request.url);
		if (isInternalPath(url.pathname)) {
			return new Response('not found', { status: 404 });
		}
		const cycleMatch = request.method === 'POST' ? url.pathname.match(CYCLE_POST_RE) : null;

		// #171's Phase 0 acceptance criterion is specifically "POST .../cycles
		// no longer runnable anonymously" -- the route that wakes the billed
		// container. Reads stay open, matching the product's existing
		// behavior (anyone can already view forecasts via the console with
		// no login) and the issue's own open "whether reads stay free"
		// question, which this pass doesn't resolve either way. Identity is
		// still resolved for everyone so a caller that *does* send a key
		// gets it forwarded downstream, but only a cycle POST requires one.
		const userId = await resolveUserId(request, env, ctx);
		if (cycleMatch) {
			if (!userId) {
				return new Response('invalid or missing X-Anemoi-Api-Key', { status: 401 });
			}
			const { success } = await env.CYCLE_RATE_LIMITER.limit({ key: userId });
			if (!success) {
				return new Response('rate limit exceeded for cycle runs', { status: 429 });
			}
		}

		// Cloned before `forwarded` is built below -- constructing a new
		// Request from `request` consumes its body, so reading it again
		// afterward would throw "body already used".
		const bodyForMetering = cycleMatch ? request.clone() : null;

		const forwarded = new Request(request, {
			headers: new Headers(request.headers),
		});
		// Deleted unconditionally, not just overwritten when `userId`
		// resolves: reads have no identity requirement, so an anonymous
		// caller hitting this Worker's public route directly (bypassing
		// console's proxy) could otherwise pass its own `X-Anemoi-User-Id`
		// straight through to the container untouched (Copilot review,
		// PR #197).
		forwarded.headers.delete('X-Anemoi-User-Id');
		if (userId) forwarded.headers.set('X-Anemoi-User-Id', userId);
		forwarded.headers.delete('X-Anemoi-Internal-Secret');
		forwarded.headers.delete('X-Anemoi-Api-Key');

		const container = getContainer(env.ANEMOI_REAL_API);
		const fetchContainer: ContainerFetch = (req) => container.fetch(req);

		const cached = await readThrough(forwarded, env.READ_CACHE, ctx, fetchContainer);
		if (cached) return cached;

		const response = await container.fetch(forwarded);

		if (cycleMatch && userId && bodyForMetering && response.ok) {
			// cycleLabel comes from the request body, not the URL -- storms.py's
			// run_cycle route takes it as JSON, same shape the cycle Workflow
			// already sends. Best-effort: never let a malformed/unreadable body
			// block a response that's already succeeded.
			try {
				const body = (await bodyForMetering.json()) as { cycle?: string };
				if (body?.cycle) {
					await recordCycleRun(env.AUTH_DB, userId, cycleMatch[1], body.cycle);
				}
			} catch (err) {
				console.error('recordCycleRun: could not read request body', err);
			}
		}

		if (cycleMatch && response.ok) {
			// The container is awake and just changed this storm: refresh what
			// the read cache serves for it, in the background. KV reads can lag
			// this write by up to a minute, so the page that ran the cycle
			// re-reads the storm with `Cache-Control: no-cache` instead of
			// relying on it (console's getStorm `fresh` option).
			const stormId = cycleMatch[1];
			const forCache = response.clone();
			ctx.waitUntil(
				(async () => {
					await putCycleResult(env.READ_CACHE, stormId, await forCache.text());
					await refreshStormSnapshot(env.READ_CACHE, fetchContainer, [stormId]);
				})().catch((err) => console.error('read-cache update after cycle POST threw', err)),
			);
		}

		return response;
	},

	async scheduled(controller, env, ctx) {
		const cycleLabel = currentCycleLabel(new Date(controller.scheduledTime));
		ctx.waitUntil(startCycleWorkflow(env, cycleLabel));
	},
} satisfies ExportedHandler<RealApiEnv>;
