import type { RequestHandler } from './$types';
import type { RequestEvent } from '@sveltejs/kit';

/**
 * Proxies `/api/*` to anemoi-api-real over a Workers service binding
 * (`wrangler.jsonc`'s `ANEMOI_API`) -- same-process, no CORS, no public
 * hop. #171: vouches for a resolved session to anemoi-api-real via a
 * shared secret (`X-Anemoi-Internal-Secret`) rather than a raw API key --
 * better-auth never returns a key's raw value after creation, only its
 * hash, so there is no key here to attach even if this route wanted to.
 * anemoi-api-real's own gate (docker/api/src/auth.ts's `resolveUserId`,
 * docker/api/src/index.ts) trusts `X-Anemoi-User-Id` only when that
 * secret matches.
 *
 * Reads stay open even when `locals.user` is absent -- matches the
 * product's existing behavior (anyone can already view forecasts with no
 * login) and anemoi-api-real's own gate, which only requires a resolved
 * identity for `POST .../cycles`. That route 401s downstream if this
 * proxy had no session to vouch for; this route doesn't need to guess
 * which paths are billable to enforce that itself.
 */
async function proxy(event: RequestEvent): Promise<Response> {
	const { request, locals, platform, url } = event;

	// `/api/v1/storms` -> `/v1/storms`.
	const targetPath = url.pathname.slice('/api'.length) || '/';

	const anemoiApi = platform?.env?.ANEMOI_API;
	const secret = platform?.env?.INTERNAL_PROXY_SECRET;

	const headers = new Headers(request.headers);
	// The session cookie is between the browser and this Worker only --
	// anemoi-api-real has no notion of it and doesn't need it. The other
	// two are stripped unconditionally, not just overwritten when a
	// session resolves: without this, an anonymous caller's own guessed
	// `X-Anemoi-Internal-Secret`/`X-Anemoi-User-Id` would pass straight
	// through untouched whenever `locals.user` is absent (Copilot review,
	// PR #197) -- brute-forcing the real secret is infeasible, but
	// stripping untrusted input doesn't get to depend on that.
	headers.delete('cookie');
	headers.delete('x-anemoi-internal-secret');
	headers.delete('x-anemoi-user-id');

	const hasBody = request.method !== 'GET' && request.method !== 'HEAD';
	const body = hasBody ? request.body : undefined;
	const duplex = hasBody ? ({ duplex: 'half' } as Record<string, string>) : {};

	if (anemoiApi && secret) {
		if (locals.user) {
			headers.set('X-Anemoi-Internal-Secret', secret);
			headers.set('X-Anemoi-User-Id', locals.user.id);
		}
		const target = new URL(targetPath + url.search, 'https://internal');
		const proxied = new Request(target, { method: request.method, headers, body, ...duplex });
		return anemoiApi.fetch(proxied);
	}

	// Plain `vite dev` has no service bindings at all (`platform` is only
	// populated under `wrangler dev`) -- fall back to a direct fetch so the
	// storm dashboard keeps working against a local `anemoi.api --reload`
	// with zero Cloudflare tooling, matching this project's dev workflow
	// before #171. Never used in a real deploy: `anemoiApi`/`secret` are
	// always present there.
	const localBase = (process.env.ANEMOI_API_LOCAL_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
	const target = new URL(targetPath + url.search, localBase);
	return fetch(target, { method: request.method, headers, body, ...duplex });
}

export const GET: RequestHandler = proxy;
export const POST: RequestHandler = proxy;
export const PUT: RequestHandler = proxy;
export const PATCH: RequestHandler = proxy;
export const DELETE: RequestHandler = proxy;
