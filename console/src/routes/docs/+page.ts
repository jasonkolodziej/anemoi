import manifest from '$lib/wiki-content/manifest.json';
import type { PageLoad } from './$types';

// The root layout sets ssr=false app-wide -- opt back in here so this
// listing page prerenders with real content, not just the client shell
// (see docs/[slug]/+page.server.ts's comment for the full reasoning).
export const ssr = true;
export const prerender = true;

export const load: PageLoad = () => ({ pages: manifest });
