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
			prerender: { handleHttpError: 'warn' }
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
	}
});
