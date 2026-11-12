// Run with `pnpm test` (Node's own runner, types stripped -- no build step).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { classifyCycleResponse, cycleRunStormId, decodedPath, isInternalPath, requiresSignedInUser } from '../src/routing.ts';

test('a cycle run is recognised on the path the container will route', () => {
	assert.equal(cycleRunStormId('POST', '/v1/storms/AL012026/cycles'), 'AL012026');
	assert.equal(cycleRunStormId('POST', '/v1/storms/AL012026/cycles/'), 'AL012026');
	// #212: an encoded slash used to skip the 401, rate limiter and KV update
	// while uvicorn decoded it and ran the cycle anyway.
	assert.equal(cycleRunStormId('POST', '/v1/storms/AL012026%2Fcycles'), 'AL012026');
	assert.equal(cycleRunStormId('POST', '/v1/storms/AL012026%2fcycles'), 'AL012026');
	assert.equal(cycleRunStormId('POST', '/v1/storms/AL012026/%63ycles'), 'AL012026');
});

test('other requests are not cycle runs', () => {
	assert.equal(cycleRunStormId('GET', '/v1/storms/AL012026/cycles'), null);
	assert.equal(cycleRunStormId('POST', '/v1/storms/AL012026'), null);
	assert.equal(cycleRunStormId('POST', '/v1/storms/AL012026/cycles/20261015_06Z'), null);
	assert.equal(cycleRunStormId('POST', '/v1/storms/%E0%A4%A/cycles'), null); // undecodable
});

test('internal routes are refused however they are spelled', () => {
	assert.equal(isInternalPath('/v1/internal/calibration-audit'), true);
	assert.equal(isInternalPath('/v1/%69nternal/calibration-audit'), true);
	assert.equal(isInternalPath('/v1/INTERNAL'), true);
	assert.equal(isInternalPath('/v1/%E0%A4%A'), true); // undecodable: refused, not guessed
	assert.equal(isInternalPath('/v1/storms'), false);
	assert.equal(decodedPath('/v1/%E0%A4%A'), null);
});

test('the Workflow branches on the API cycle-policy answer', () => {
	assert.equal(classifyCycleResponse(201, '{}'), 'ran');
	assert.equal(classifyCycleResponse(409, '{"detail":"x","code":"exists"}'), 'done');
	assert.equal(classifyCycleResponse(409, '{"detail":"x","code":"in_progress"}'), 'retry');
	assert.equal(classifyCycleResponse(409, '{"detail":"x","code":"not_scheduled_yet"}'), 'refused');
	assert.equal(classifyCycleResponse(409, 'not json'), 'refused');
	assert.equal(classifyCycleResponse(400, '{"detail":"outside the track"}'), 'refused');
	assert.equal(classifyCycleResponse(404, ''), 'refused');
	assert.equal(classifyCycleResponse(500, ''), 'retry');
	assert.equal(classifyCycleResponse(503, ''), 'retry');
});

test('the Develop pages\' reads need a signed-in user; the public storm page\'s don\'t', () => {
	for (const path of [
		'/v1/retraining/triggers',
		'/v1/retraining',
		'/v1/monitoring/drift',
		'/v1/monitoring/drift/cnn',
		'/v1/monitoring/calibration',
		'/v1/monitoring/%63alibration',
		'/v1/sources',
		'/v1/%73ources/',
	]) {
		assert.equal(requiresSignedInUser(path), true, path);
	}
	// Read by the public storm page.
	for (const path of ['/v1/monitoring/skew', '/v1/registry', '/v1/registry/pins/active', '/v1/storms/AL012026']) {
		assert.equal(requiresSignedInUser(path), false, path);
	}
});

test('model architecture needs a signed-in user, on the path the container will route', () => {
	assert.equal(requiresSignedInUser('/v1/registry/cnn/architecture'), true);
	assert.equal(requiresSignedInUser('/v1/registry/cnn/architecture/'), true);
	// The same bypass #212 closed for cycles: an encoded character must not skip it.
	assert.equal(requiresSignedInUser('/v1/registry/cnn/%61rchitecture'), true);
	assert.equal(requiresSignedInUser('/v1/registry/cnn%2Farchitecture'), true);
	assert.equal(requiresSignedInUser('/V1/REGISTRY/CNN/ARCHITECTURE'), true);
	// The rest of the registry stays as open as it was.
	assert.equal(requiresSignedInUser('/v1/registry'), false);
	assert.equal(requiresSignedInUser('/v1/registry/cnn'), false);
	assert.equal(requiresSignedInUser('/v1/registry/pins/active'), false);
	assert.equal(requiresSignedInUser('/v1/storms'), false);
});
