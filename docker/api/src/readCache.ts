/**
 * KV read cache in front of the AnemoiRealApi container.
 *
 * Every console page view and 60s poll used to reach the container, which
 * sleeps after 5 minutes idle -- so most visits paid a cold start, a NHC
 * feed fetch and R2 reads before the storm list rendered. What those reads
 * return only really changes when a cycle runs (four synoptic times a day,
 * plus manual runs) and both of those pass through this Worker, so it keeps
 * the answers in KV itself:
 *
 *   storms:index         GET /v1/storms                       soft TTL, then refreshed
 *   storm:{id}           GET /v1/storms/{id}                  soft TTL, then refreshed
 *   cycle:{id}:{label}   GET /v1/storms/{id}/cycles/{label}   immutable once run
 *   health               GET /v1/health                       soft TTL, then refreshed
 *   schedule:{date}:{wc} GET /v1/schedule?date=&worst_case=   soft TTL, then refreshed
 *   skew:{lead}          GET /v1/monitoring/skew?lead_hours=  soft TTL, then refreshed
 *
 * The last three are what the console polls every minute next to the storm
 * reads (#212): left uncached, a visible tab kept the container awake on
 * them alone, cache or no cache.
 *
 * Past the soft TTL an entry is still served at once and refreshed in the
 * background (stale-while-revalidate); the hard expiry is KV's own, so a
 * dead cron makes data disappear rather than look current. Every response
 * carries `X-Anemoi-Cache: hit|stale|miss|bypass`, visible in `wrangler tail`.
 *
 * A signed-in request sent with `Cache-Control: no-cache` skips the lookup
 * and refills the entry from the container. KV reads can lag a write by up
 * to a minute, so the console sends it for the one read that must see a
 * write it just caused: the storm, right after running a cycle on it. An
 * anonymous one is served from the cache like any other read (#212) --
 * otherwise anyone could wake the container at will, and browsers send it
 * on their own (a hard reload, DevTools' "Disable cache").
 *
 * Functions here take the KV binding and a container fetcher rather than
 * reaching for globals, so the fetch handler, the cron and a future
 * Cloudflare Workflow step can all call them unchanged.
 */

export type ContainerFetch = (request: Request) => Promise<Response>;

/** Matches the container's own live-feed TTL (`real_state._LIVE_STORMS_TTL`):
 * refreshing more often would only re-read the same NHC bulletin. */
const SOFT_TTL_MS = 30 * 60 * 1000;
/** A little past one synoptic interval: an entry the cron failed to refresh
 * for a whole cycle expires instead of being served indefinitely. */
const HARD_TTL_S = 7 * 60 * 60;
/** Cycle results never change once run (a re-run of the same label passes
 * through `putCycleResult` again); the expiry only keeps KV from growing
 * forever with storms nobody looks at any more. */
const CYCLE_TTL_S = 90 * 24 * 60 * 60;

const STORMS_INDEX_KEY = 'storms:index';
const stormKey = (stormId: string) => `storm:${stormId}`;
const cycleKey = (stormId: string, label: string) => `cycle:${stormId}:${label}`;

interface EntryMeta {
	storedAt: number;
}

export interface CacheTarget {
	key: string;
	immutable: boolean;
	/** Path and query a background refresh fetches. */
	source: string;
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/** The cache key for a cacheable GET, or null to pass it through. A query
 * is only accepted on the routes that take one, and only with exactly the
 * parameters the key is built from, so two requests sharing a key always
 * get the same answer. */
export function cacheTargetFor(url: URL): CacheTarget | null {
	const path = url.pathname.replace(/\/$/, '');
	const params = [...url.searchParams.keys()];
	const only = (...allowed: string[]) => params.every((k) => allowed.includes(k)) && new Set(params).size === params.length;
	if (path === '/v1/schedule') {
		const date = url.searchParams.get('date');
		const worstCase = url.searchParams.get('worst_case') ?? 'false';
		if (!only('date', 'worst_case') || !date || !DATE_RE.test(date) || !['true', 'false'].includes(worstCase)) {
			return null;
		}
		return {
			key: `schedule:${date}:${worstCase}`,
			immutable: false,
			source: `${path}?date=${date}&worst_case=${worstCase}`,
		};
	}
	if (path === '/v1/monitoring/skew') {
		const lead = url.searchParams.get('lead_hours') ?? '48';
		if (!only('lead_hours') || !/^\d{1,3}$/.test(lead)) return null;
		return { key: `skew:${lead}`, immutable: false, source: `${path}?lead_hours=${lead}` };
	}
	if (url.search) return null; // no other cached route takes a query
	if (path === '/v1/health') return { key: 'health', immutable: false, source: path };
	if (path === '/v1/storms') return { key: STORMS_INDEX_KEY, immutable: false, source: path };
	const cycle = path.match(/^\/v1\/storms\/([^/]+)\/cycles\/([^/]+)$/);
	if (cycle) return { key: cycleKey(cycle[1], cycle[2]), immutable: true, source: path };
	const storm = path.match(/^\/v1\/storms\/([^/]+)$/);
	if (storm) return { key: stormKey(storm[1]), immutable: false, source: path };
	return null;
}

function jsonResponse(body: string, cache: 'hit' | 'stale' | 'miss' | 'bypass'): Response {
	return new Response(body, {
		headers: { 'Content-Type': 'application/json', 'X-Anemoi-Cache': cache },
	});
}

async function put(kv: KVNamespace, key: string, body: string, immutable: boolean): Promise<void> {
	try {
		await kv.put(key, body, {
			expirationTtl: immutable ? CYCLE_TTL_S : HARD_TTL_S,
			metadata: { storedAt: Date.now() } satisfies EntryMeta,
		});
	} catch (err) {
		// The cache is an accelerator, never a gate: a failed write just
		// means the next read falls through to the container.
		console.error(`readCache: put ${key} failed`, err);
	}
}

/** Background refreshes already in flight in this isolate, so a burst of
 * stale reads triggers one container request per key, not one each. */
const refreshing = new Set<string>();

async function refresh(kv: KVNamespace, key: string, path: string, fetchContainer: ContainerFetch): Promise<void> {
	if (refreshing.has(key)) return;
	refreshing.add(key);
	try {
		const res = await fetchContainer(new Request(`https://internal${path}`));
		if (res.ok) await put(kv, key, await res.text(), false);
	} catch (err) {
		console.error(`readCache: refresh ${key} failed`, err);
	} finally {
		refreshing.delete(key);
	}
}

/**
 * Serve a GET from KV when possible, falling through to the container on a
 * miss (and caching a successful answer). Returns null for requests this
 * cache doesn't handle, so the caller forwards them as before.
 */
export async function readThrough(
	request: Request,
	kv: KVNamespace,
	ctx: ExecutionContext,
	fetchContainer: ContainerFetch,
	{ allowBypass = false }: { allowBypass?: boolean } = {},
): Promise<Response | null> {
	if (request.method !== 'GET') return null;
	const url = new URL(request.url);
	const target = cacheTargetFor(url);
	if (!target) return null;

	const bypass = allowBypass && (request.headers.get('Cache-Control')?.includes('no-cache') ?? false);
	let cached: KVNamespaceGetWithMetadataResult<string, EntryMeta> | null = null;
	if (!bypass) {
		try {
			cached = await kv.getWithMetadata<EntryMeta>(target.key, 'text');
		} catch (err) {
			console.error(`readCache: get ${target.key} failed`, err);
		}
	}
	if (cached?.value != null) {
		const age = Date.now() - (cached.metadata?.storedAt ?? 0);
		if (target.immutable || age < SOFT_TTL_MS) return jsonResponse(cached.value, 'hit');
		ctx.waitUntil(refresh(kv, target.key, target.source, fetchContainer));
		return jsonResponse(cached.value, 'stale');
	}

	const res = await fetchContainer(request);
	if (!res.ok) return res; // a 404 for a cycle not run yet must not stick
	const body = await res.text();
	ctx.waitUntil(put(kv, target.key, body, target.immutable));
	return jsonResponse(body, bypass ? 'bypass' : 'miss');
}

/** Store a cycle result the container just returned from a run. */
export async function putCycleResult(kv: KVNamespace, stormId: string, body: string): Promise<void> {
	let label: string | undefined;
	try {
		label = (JSON.parse(body) as { payload?: { cycle?: string } }).payload?.cycle;
	} catch {
		/* not JSON -- nothing to cache */
	}
	if (label) await put(kv, cycleKey(stormId, label), body, true);
}

interface StormSummary {
	storm_id: string;
}

/**
 * Re-read the storm list and the given storms' details from the container
 * and store them. Called after cycle runs, when the container is already
 * awake; `stormIds` defaults to every storm in the list.
 */
export async function refreshStormSnapshot(
	kv: KVNamespace,
	fetchContainer: ContainerFetch,
	stormIds?: string[],
): Promise<void> {
	const res = await fetchContainer(new Request('https://internal/v1/storms'));
	if (!res.ok) {
		console.error(`readCache: snapshot GET /v1/storms -> ${res.status}`);
		return;
	}
	const body = await res.text();
	await put(kv, STORMS_INDEX_KEY, body, false);

	const ids = stormIds ?? (JSON.parse(body) as StormSummary[]).map((s) => s.storm_id);
	for (const id of ids) {
		await refresh(kv, stormKey(id), `/v1/storms/${id}`, fetchContainer);
	}
}
