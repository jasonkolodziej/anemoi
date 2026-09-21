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

export default {
	async fetch(request, env) {
		const container = getContainer(env.ANEMOI_REAL_API);
		return container.fetch(request);
	},
} satisfies ExportedHandler<Env>;
