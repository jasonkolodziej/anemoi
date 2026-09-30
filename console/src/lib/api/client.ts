/**
 * Thin typed fetch wrapper over Anemoi-API. Every endpoint function in
 * `endpoints.ts` goes through `apiFetch` so auth, error handling and the
 * base path stay in one place.
 *
 * #171: requests go to `/api/...` on this same Worker, not directly to
 * anemoi-api-real -- `routes/api/[...path]/+server.ts` proxies them
 * through a service binding after checking the caller's session, and
 * attaches the real API key server-side. No key is ever sent from the
 * browser (the old `setApiKey`/`X-Anemoi-Api-Key`-from-browser mechanism
 * this replaced never had one to attach in production anyway --
 * `ANEMOI_API_KEY` was unset).
 */

export class ApiError extends Error {
	status: number;
	constructor(status: number, detail: string) {
		super(detail);
		this.name = 'ApiError';
		this.status = status;
	}
}

export async function apiFetch<T>(
	path: string,
	init: RequestInit & { query?: Record<string, string | number | boolean | undefined> } = {}
): Promise<T> {
	const { query, ...rest } = init;
	const url = new URL('/api' + path, 'http://placeholder');
	if (query) {
		for (const [k, v] of Object.entries(query)) {
			if (v !== undefined) url.searchParams.set(k, String(v));
		}
	}

	const headers = new Headers(rest.headers);
	if (rest.body && !headers.has('Content-Type')) {
		headers.set('Content-Type', 'application/json');
	}

	const res = await fetch(url.pathname + url.search, { ...rest, headers, credentials: 'include' });
	if (!res.ok) {
		let detail = res.statusText;
		try {
			const body: unknown = await res.json();
			if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
				detail = body.detail;
			}
		} catch {
			/* body wasn't JSON; keep statusText */
		}
		throw new ApiError(res.status, detail);
	}
	if (res.status === 204) return undefined as T;
	return (await res.json()) as T;
}
