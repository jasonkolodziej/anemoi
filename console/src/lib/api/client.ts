/**
 * Thin typed fetch wrapper over Anemoi-API. Base URL is read once from
 * `PUBLIC_ANEMOI_API_URL` (see .env.example); every endpoint function in
 * `endpoints.ts` goes through `apiFetch` so auth headers, error handling and
 * the base URL stay in one place.
 */

import { env } from '$env/dynamic/public';

export class ApiError extends Error {
	status: number;
	constructor(status: number, detail: string) {
		super(detail);
		this.name = 'ApiError';
		this.status = status;
	}
}

// $env/dynamic/public still means "set at build time" for this SPA, not
// truly per-request runtime config -- checked directly against a real
// build: adapter-static emits `build/_app/env.js` (a real `export const
// env = {...}` literal, fetched via a lazy `import()` at page load, but
// with whatever `PUBLIC_ANEMOI_API_URL` was in the *build's* environment
// already baked into it). There is no server here to inject a fresh value
// per request the way a real SvelteKit server adapter would -- deploying
// to a different API target means rebuilding with a different
// PUBLIC_ANEMOI_API_URL set (see console/wrangler.jsonc's cf:deploy note),
// not changing anything after the fact. Falls back to the reference
// server's default so `pnpm dev`/`pnpm build` work with zero setup.
const BASE_URL = (env.PUBLIC_ANEMOI_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

let apiKey: string | null = null;

/** Set the X-Anemoi-Api-Key header for all subsequent requests. No-op
 * against a reference deployment, where ANEMOI_API_KEY is unset. */
export function setApiKey(key: string | null): void {
	apiKey = key;
}

export async function apiFetch<T>(
	path: string,
	init: RequestInit & { query?: Record<string, string | number | boolean | undefined> } = {}
): Promise<T> {
	const { query, ...rest } = init;
	const url = new URL(BASE_URL + path);
	if (query) {
		for (const [k, v] of Object.entries(query)) {
			if (v !== undefined) url.searchParams.set(k, String(v));
		}
	}

	const headers = new Headers(rest.headers);
	if (rest.body && !headers.has('Content-Type')) {
		headers.set('Content-Type', 'application/json');
	}
	if (apiKey) headers.set('X-Anemoi-Api-Key', apiKey);

	const res = await fetch(url, { ...rest, headers });
	if (!res.ok) {
		let detail = res.statusText;
		try {
			detail = (await res.json()).detail ?? detail;
		} catch {
			/* body wasn't JSON; keep statusText */
		}
		throw new ApiError(res.status, detail);
	}
	if (res.status === 204) return undefined as T;
	return (await res.json()) as T;
}

export function apiWebSocketUrl(path: string): string {
	const httpUrl = new URL(BASE_URL + path);
	httpUrl.protocol = httpUrl.protocol === 'https:' ? 'wss:' : 'ws:';
	return httpUrl.toString();
}
