/**
 * Request routing rules shared by the Worker's fetch handler and the cycle
 * Workflow. No imports and no Workers globals, so the tests in `test/` run
 * them under plain Node (`pnpm test`).
 */

/** Matches `POST /v1/storms/{storm_id}/cycles` -- the route that wakes
 * the billed container and runs real inference, gated tighter than
 * everything else. Matched against `decodedPath`, never the raw path. */
export const CYCLE_POST_RE = /^\/v1\/storms\/([^/]+)\/cycles\/?$/;

/** Set by the cycle Workflow on its own container calls to mark the
 * official, scheduled run (`api.cycle_policy`). The Workflow calls the
 * container directly; anything arriving here is a caller forging it. */
export const RUN_SOURCE_HEADER = 'X-Anemoi-Run-Source';

/** The path the container's router will see: uvicorn percent-decodes it, so
 * a gate matched on the raw path is bypassed by encoding one character --
 * `POST /v1/storms/AL012026%2Fcycles` skipped the 401, the rate limiter and
 * the KV update, then ran a cycle anyway (#212). Null for a path that
 * doesn't decode, which is refused outright rather than guessed at. */
export function decodedPath(pathname: string): string | null {
	try {
		return decodeURIComponent(pathname);
	} catch {
		return null;
	}
}

/** The storm id of a cycle-run request, or null for any other request. */
export function cycleRunStormId(method: string, pathname: string): string | null {
	if (method !== 'POST') return null;
	const path = decodedPath(pathname);
	return path?.match(CYCLE_POST_RE)?.[1] ?? null;
}

/** Reads only a signed-in caller gets -- what the console's Develop pages
 * (each behind sign-in itself) read and no public page does:
 *
 *   /v1/registry/{model}/architecture  each model's internals; also builds
 *                                      the model on the container
 *   /v1/retraining/...                 what's due to retrain
 *   /v1/monitoring/drift[/{model}]     input drift
 *   /v1/monitoring/calibration         spread/skill per lead
 *   /v1/sources                        the data source registry
 *
 * Not the registry listing, the active pin or /v1/monitoring/skew: the
 * public storm page reads those. An API key counts as signed in.
 * Matched on the decoded path, like the cycle gate. */
const SIGNED_IN_READ_RE =
	/^\/v1\/(registry\/[^/]+\/architecture|retraining(\/.*)?|monitoring\/drift(\/[^/]+)?|monitoring\/calibration|sources)\/?$/i;

/** Does this request need a resolved user? Any method -- a read gated here
 * is gated whatever it's sent as. An undecodable path is already refused by
 * `isInternalPath`. */
export function requiresSignedInUser(pathname: string): boolean {
	const path = decodedPath(pathname);
	return path !== null && SIGNED_IN_READ_RE.test(path);
}

/** Maintenance routes only this Worker's own cron calls, through the
 * container binding directly -- never reachable from the public route. */
const INTERNAL_RE = /^\/v1\/internal(\/|$)/i;

/** Checked on the decoded path: the container's router decodes it too, so
 * `/v1/%69nternal/...` would otherwise slip past a raw-path match. An
 * undecodable path is refused outright rather than guessed at. */
export function isInternalPath(pathname: string): boolean {
	const path = decodedPath(pathname);
	return path === null || INTERNAL_RE.test(path);
}

/** What the cycle Workflow does with the container's answer to a scheduled
 * cycle POST (`api.cycle_policy` decides the 409s):
 *
 *   ran      2xx -- store the result in the read cache
 *   done     409 `exists` -- the scheduled run already happened (a retry
 *            after a lost response, or a duplicate instance)
 *   retry    409 `in_progress` or a 5xx -- throw, so the step retries
 *   refused  any other 4xx -- retrying can't change it */
export type CycleOutcome = 'ran' | 'done' | 'retry' | 'refused';

export function classifyCycleResponse(status: number, body: string): CycleOutcome {
	if (status >= 200 && status < 300) return 'ran';
	if (status === 409) {
		let code: unknown;
		try {
			code = (JSON.parse(body) as { code?: unknown }).code;
		} catch {
			/* not JSON */
		}
		if (code === 'exists') return 'done';
		if (code === 'in_progress') return 'retry';
		return 'refused';
	}
	if (status >= 400 && status < 500) return 'refused';
	return 'retry';
}
