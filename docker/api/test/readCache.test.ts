// Run with `pnpm test` (Node's own runner, types stripped -- no build step).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { cacheTargetFor, readThrough } from '../src/readCache.ts';

const target = (url: string) => cacheTargetFor(new URL(url, 'https://x'));

test('the polled console reads are cached, keyed by exactly what they depend on (#212)', () => {
	assert.deepEqual(target('/v1/health'), { key: 'health', immutable: false, source: '/v1/health' });
	assert.equal(target('/v1/schedule?date=2026-10-15&worst_case=false')?.key, 'schedule:2026-10-15:false');
	assert.equal(target('/v1/schedule?worst_case=false&date=2026-10-15')?.key, 'schedule:2026-10-15:false');
	assert.equal(target('/v1/schedule?date=2026-10-15')?.key, 'schedule:2026-10-15:false');
	assert.equal(
		target('/v1/schedule?date=2026-10-15&worst_case=true')?.source,
		'/v1/schedule?date=2026-10-15&worst_case=true',
	);
	assert.equal(target('/v1/monitoring/skew?lead_hours=48')?.key, 'skew:48');
	assert.equal(target('/v1/monitoring/skew')?.key, 'skew:48');
});

test('a query the key does not cover passes through', () => {
	assert.equal(target('/v1/schedule'), null);
	assert.equal(target('/v1/schedule?date=tomorrow'), null);
	assert.equal(target('/v1/schedule?date=2026-10-15&extra=1'), null);
	assert.equal(target('/v1/schedule?date=2026-10-15&date=2026-10-16'), null);
	assert.equal(target('/v1/monitoring/skew?lead_hours=abc'), null);
	assert.equal(target('/v1/storms?x=1'), null);
	assert.equal(target('/v1/health?x=1'), null);
});

test('storm and cycle keys are unchanged', () => {
	assert.equal(target('/v1/storms')?.key, 'storms:index');
	assert.equal(target('/v1/storms/AL012026')?.key, 'storm:AL012026');
	assert.deepEqual(target('/v1/storms/AL012026/cycles/20261015_06Z'), {
		key: 'cycle:AL012026:20261015_06Z',
		immutable: true,
		source: '/v1/storms/AL012026/cycles/20261015_06Z',
	});
});

function fakeKv(entries: Record<string, string>) {
	return {
		puts: [] as string[],
		async getWithMetadata(key: string) {
			return key in entries ? { value: entries[key], metadata: { storedAt: Date.now() } } : { value: null, metadata: null };
		},
		async put(key: string) {
			this.puts.push(key);
		},
	};
}

const ctx = { waitUntil() {} } as unknown as ExecutionContext;

async function read(headers: Record<string, string>, allowBypass: boolean) {
	const kv = fakeKv({ health: '{"cached":true}' });
	let containerCalls = 0;
	const res = await readThrough(
		new Request('https://x/v1/health', { headers }),
		kv as unknown as KVNamespace,
		ctx,
		async () => {
			containerCalls += 1;
			return new Response('{"cached":false}');
		},
		{ allowBypass },
	);
	return { res: res!, containerCalls };
}

test('only a signed-in caller can skip the cache (#212)', async () => {
	const anonymous = await read({ 'Cache-Control': 'no-cache' }, false);
	assert.equal(anonymous.res.headers.get('X-Anemoi-Cache'), 'hit');
	assert.equal(anonymous.containerCalls, 0);

	const signedIn = await read({ 'Cache-Control': 'no-cache' }, true);
	assert.equal(signedIn.res.headers.get('X-Anemoi-Cache'), 'bypass');
	assert.equal(signedIn.containerCalls, 1);
});
