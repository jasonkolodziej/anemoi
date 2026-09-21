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

export class AnemoiRealApi extends Container {
	defaultPort = 8080;
	// Real cycles run four times a day (per synoptic time), not
	// continuously -- sleep fairly quickly between bursts rather than
	// paying for an idle container, matching Containers' pay-per-active-
	// second billing model.
	sleepAfter = '5m';

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
