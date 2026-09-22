import { error } from '@sveltejs/kit';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import manifest from '$lib/wiki-content/manifest.json';
import type { EntryGenerator, PageServerLoad } from './$types';

// Every wiki page is known at build time (scripts/sync-wiki.mjs already ran
// by the time Vite starts, see package.json's build/dev scripts) -- prerender
// all of them to real static HTML rather than leaning on the SPA fallback
// the way storms/[stormId] has to (that one genuinely can't know its params
// ahead of time; this one can). A server load is fine under adapter-static
// here specifically because the route is prerendered -- it runs once at
// build time, not as a live server. ssr/prerender themselves are set at
// docs/+layout.ts, covering this whole subtree.
export const entries: EntryGenerator = () => manifest.map((page) => ({ slug: page.slug }));

export const load: PageServerLoad = ({ params }) => {
	const page = manifest.find((p) => p.slug === params.slug);
	if (!page) error(404, 'Wiki page not found');

	const html = readFileSync(join(process.cwd(), 'static', 'wiki', `${page.slug}.html`), 'utf8');
	return { title: page.title, slug: page.slug, html, related: page.related ?? [] };
};
