import adapter from '@sveltejs/adapter-static';
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
			// Static adapter: the console is a client-rendered SPA talking to
			// Anemoi-API over fetch/WebSocket, so there is no server runtime to
			// deploy -- `npm run build` emits plain files for any static host.
			adapter: adapter({
				pages: 'build',
				assets: 'build',
				fallback: 'index.html',
				precompress: false,
				strict: true
			}),
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
	}
});
