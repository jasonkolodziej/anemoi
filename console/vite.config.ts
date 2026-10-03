import adapter from '@sveltejs/adapter-cloudflare';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			// Cloudflare adapter, not adapter-static: #171 gives the console a
			// real Worker (login, D1-backed sessions, API-key issuance,
			// proxying to anemoi-api-real) -- `+page.server.ts`/`+server.ts`
			// routes need a server runtime, which static prerendering can't
			// provide. Emits `.svelte-kit/cloudflare/_worker.js` +
			// `.svelte-kit/cloudflare` assets; see console/wrangler.jsonc.
			adapter: adapter(),
			// /docs/[slug] pages prerender from wiki content edited in a
			// separate repo, with no chance for this build to catch a mistake
			// before it happens -- a malformed link in some future wiki edit
			// (already happened once: a data-source link missing its URL
			// scheme) would otherwise fail the *entire* console build, not
			// just that one link.
			// Same reasoning for a link to a heading anchor a later wiki edit
			// renamed (hit for real: operations-runbook linking a roadmap
			// heading that no longer exists).
			prerender: { handleHttpError: 'warn', handleMissingId: 'warn' }
		})
	],
	server: {
		port: 5173
	},
	// maplibre-gl's worker is loaded via svelte-maplibre-gl/vite's
	// `?worker&url` import -- Vite 8's Rolldown-based dependency optimizer
	// fails to resolve that special query suffix during pre-bundling
	// ("UNLOADABLE_DEPENDENCY", found running this for real), even though
	// the target file genuinely exists on disk. Excluding both from
	// optimizeDeps skips that broken pre-bundling step; the browser then
	// loads them as native ESM instead, which resolves the worker fine.
	optimizeDeps: {
		exclude: ['maplibre-gl', 'svelte-maplibre-gl']
	},
	build: {
		// The only chunks over the default 500kB limit are mermaid and its
		// own dependencies (elkjs, cytoscape, its diagram-grammar parsers --
		// confirmed by inspecting the built chunks directly). mermaid is
		// already dynamically `import()`ed from a single call site
		// (src/lib/wiki/mermaid.ts's renderMermaidDiagrams, itself only
		// invoked from docs/[slug]'s onMount, and only when a page actually
		// has a `.mermaid` node) -- verified in the client build manifest
		// that no other route's chunk references it. Raising the limit
		// just far enough to cover it (current largest is ~1.46MB) avoids
		// papering over a *real* regression elsewhere; it only silences
		// this specific, already-isolated, already-lazy dependency.
		chunkSizeWarningLimit: 1600,
		rolldownOptions: {
			checks: {
				// Every build prints a "PLUGIN_TIMINGS" breakdown by default
				// (rolldown's `checks.bundlerTimings`, on unless disabled).
				// Its own slowest entries here are inherent to this project's
				// size (writing the compiled bundle to disk, compiling ~2500
				// Svelte files, maplibre-gl's worker handling) -- not
				// something a config change fixes, so the report itself is
				// just noise on every single build rather than an
				// actionable warning.
				bundlerTimings: false
			}
		}
	}
});
