/**
 * Client-side full-text search over the bundled wiki content -- no search
 * service, no runtime API call to anywhere but this same deploy.
 * scripts/sync-wiki.mjs pre-builds static/wiki/search-index.json (plain
 * title + stripped body text) at build time; this only fetches that one
 * file (once, lazily -- not until someone actually searches) and builds
 * the MiniSearch index client-side. Same "static, self-contained, zero
 * runtime network dependency" pattern as the rest of this console
 * (ConeMap's bundled coastlines, the HURDAT2 archive baked into the API
 * image).
 */
import MiniSearch from 'minisearch';

export interface WikiSearchResult {
	slug: string;
	title: string;
	excerpt: string;
}

interface IndexedDoc {
	id: string;
	title: string;
	body: string;
}

const bodyById = new Map<string, string>();
let miniPromise: Promise<MiniSearch<IndexedDoc>> | null = null;

async function buildIndex(): Promise<MiniSearch<IndexedDoc>> {
	const docs = (await fetch('/wiki/search-index.json').then((r) => r.json())) as IndexedDoc[];
	for (const doc of docs) bodyById.set(doc.id, doc.body);

	const mini = new MiniSearch<IndexedDoc>({
		fields: ['title', 'body'],
		storeFields: ['title'],
		searchOptions: { boost: { title: 3 }, prefix: true, fuzzy: 0.2 }
	});
	mini.addAll(docs);
	return mini;
}

function getIndex(): Promise<MiniSearch<IndexedDoc>> {
	if (!miniPromise) miniPromise = buildIndex();
	return miniPromise;
}

function excerptAround(body: string, term: string, radius = 70): string {
	const idx = body.toLowerCase().indexOf(term.toLowerCase());
	if (idx === -1) return body.slice(0, radius * 2);
	const start = Math.max(0, idx - radius);
	const end = Math.min(body.length, idx + term.length + radius);
	return `${start > 0 ? '…' : ''}${body.slice(start, end)}${end < body.length ? '…' : ''}`;
}

export async function searchWiki(query: string): Promise<WikiSearchResult[]> {
	const trimmed = query.trim();
	if (!trimmed) return [];
	const mini = await getIndex();
	const results = mini.search(trimmed).slice(0, 8);
	const firstTerm = trimmed.split(/\s+/)[0];
	return results.map((r) => ({
		slug: r.id,
		title: r.title as string,
		excerpt: excerptAround(bodyById.get(r.id) ?? '', firstTerm)
	}));
}
