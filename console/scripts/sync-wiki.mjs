#!/usr/bin/env node
// Pulls the wiki (github.com/jasonkolodziej/anemoi.wiki) into the console at
// build time, the same "fetch a static reference source over HTTP/git at
// build time, bake it into the deploy" pattern docker/api/Dockerfile already
// uses for HURDAT2 -- zero runtime network dependency, the docs page works
// offline exactly like everything else in this SPA.
//
// Idempotent: skips the clone if content already exists, so `pnpm dev`
// doesn't re-clone on every restart. `--force` re-fetches.
//
// Renders each page to real HTML at build time (unified/remark/rehype, not
// a Svelte-component-per-page compiler like mdsvex) -- these are plain
// wiki pages with no frontmatter and nothing Svelte-specific in them, so
// there's nothing a Svelte-aware markdown compiler buys here that a plain
// text -> HTML pipeline doesn't. Output is genuinely static content, not
// source, so it goes where SvelteKit's own convention puts static content:
// static/wiki/*.html (served/fetched as real files) -- only the small
// slug -> title routing manifest lives under src/lib, because SvelteKit's
// prerenderer needs it as a build-time import (entries()), not a fetch.
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readdirSync, readFileSync, writeFileSync, rmSync, existsSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkRehype from 'remark-rehype';
import rehypeSlug from 'rehype-slug';
import rehypeStringify from 'rehype-stringify';
import { rewriteWikiLinks } from '../src/lib/wiki/rewrite-wiki-links.mjs';
import { rehypeMermaid } from '../src/lib/wiki/rehype-mermaid.mjs';

const WIKI_REPO = 'https://github.com/jasonkolodziej/anemoi.wiki.git';
const CONSOLE_ROOT = fileURLToPath(new URL('..', import.meta.url));
const MANIFEST_DIR = join(CONSOLE_ROOT, 'src/lib/wiki-content');
const STATIC_DIR = join(CONSOLE_ROOT, 'static/wiki');
const force = process.argv.includes('--force');

if (existsSync(STATIC_DIR) && readdirSync(STATIC_DIR).some((f) => f.endsWith('.html')) && !force) {
	console.log('[sync-wiki] content already present, skipping (pass --force to refetch)');
	process.exit(0);
}

const processor = unified()
	.use(remarkParse)
	.use(remarkGfm)
	.use(rewriteWikiLinks)
	.use(remarkRehype)
	.use(rehypeSlug)
	.use(rehypeMermaid)
	.use(rehypeStringify);

function stripToText(markdown) {
	// Search-index body text -- crude but sufficient for substring/fuzzy
	// matching, and avoids a second full HTML round-trip just to strip tags.
	return markdown
		.replace(/```[\s\S]*?```/g, ' ')
		.replace(/`[^`]*`/g, ' ')
		.replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
		.replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
		.replace(/[#>*_~|]/g, ' ')
		.replace(/\s+/g, ' ')
		.trim();
}

const tmp = mkdtempSync(join(tmpdir(), 'anemoi-wiki-'));
try {
	console.log(`[sync-wiki] cloning ${WIKI_REPO}...`);
	execFileSync('git', ['clone', '--depth', '1', '-q', WIKI_REPO, tmp], { stdio: 'inherit' });

	rmSync(MANIFEST_DIR, { recursive: true, force: true });
	mkdirSync(MANIFEST_DIR, { recursive: true });
	rmSync(STATIC_DIR, { recursive: true, force: true });
	mkdirSync(STATIC_DIR, { recursive: true });

	// _Footer/_Sidebar are GitHub wiki UI chrome, not content. README.md is
	// explicitly "not a wiki page" per its own first line -- GitHub itself
	// ignores it when rendering the wiki.
	const pages = readdirSync(tmp).filter(
		(f) => f.endsWith('.md') && !/^(_Footer|_Sidebar|README)\.md$/i.test(f)
	);

	const manifest = [];
	const searchIndex = [];
	for (const file of pages) {
		const raw = readFileSync(join(tmp, file), 'utf8');
		const slug = file.replace(/\.md$/, '').toLowerCase();
		const h1 = raw.match(/^#\s+(.+)$/m);
		const title = h1 ? h1[1].trim() : file.replace(/\.md$/, '').replace(/-/g, ' ');

		const html = String(processor.processSync(raw));
		writeFileSync(join(STATIC_DIR, `${slug}.html`), html);

		manifest.push({ slug, title });
		searchIndex.push({ id: slug, title, body: stripToText(raw) });
	}
	manifest.sort((a, b) => a.title.localeCompare(b.title));
	writeFileSync(join(MANIFEST_DIR, 'manifest.json'), JSON.stringify(manifest, null, '\t') + '\n');
	writeFileSync(join(STATIC_DIR, 'search-index.json'), JSON.stringify(searchIndex));

	console.log(`[sync-wiki] wrote ${pages.length} pages to ${STATIC_DIR}`);
} finally {
	rmSync(tmp, { recursive: true, force: true });
}
