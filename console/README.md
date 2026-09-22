# Anemoi Console

A SvelteKit 5 + TypeScript + shadcn-svelte console for [Anemoi](https://github.com/jasonkolodziej/anemoi) — active storms, cone/track visualization, model contribution weights, intensity forecasts, the model registry, drift/skew monitoring, and retraining triggers. Talks to `anemoi.api` (see the wiki's [API](https://github.com/jasonkolodziej/anemoi/wiki/API) page, `docs/api.md` in the anemoi repo, or `anemoi-api-patch.zip` alongside this project).

Client-rendered SPA end to end (`routes/+layout.ts` sets `ssr = false`) — there's no server runtime to deploy, `npm run build` emits static files for any host.

## Design system

Every saturated colour in this app identifies one Anemoi model — the six wind-god colours plus Fusion's neutral — copied from `anemoi.branding` into `src/lib/branding.ts`. Everything else (chrome, interactive states) draws from a single neutral scale plus one dedicated action-blue that appears nowhere in the god palette. Tokens live in `src/app.css`'s `@theme` block (Tailwind v4, CSS-first config).

Type: Inter Variable (display/headings) / Geist Variable (UI, self-hosted via `@fontsource-variable`) / Geist Mono (data — coordinates, cycle labels, durations only, never UI labels; still a Google Fonts `<link>`, no `@fontsource-variable/geist-mono` package exists). `Card` and app chrome use a flat `bg-surface` fill — see `src/app.css`'s own comments for where each token comes from and why.

## Getting started

```sh
pnpm install
cp .env.example .env   # PUBLIC_ANEMOI_API_URL, defaults to http://127.0.0.1:8000
pnpm dev                # http://localhost:5173
```

Needs `anemoi.api` running (`uv run python -m anemoi.api --reload` from the anemoi repo, demo mode by default) — the dashboard shows a connection error with instructions if it can't reach it.

```sh
pnpm build     # static output in build/
pnpm preview   # serve the production build locally
pnpm check     # svelte-check, 0 errors as of this scaffold
```

## Deploying

Issue #96. Pure static assets on Cloudflare Workers (no separate Worker
script -- `wrangler.jsonc`'s `assets` block is the whole config), same
tooling as `docker/api`'s deployment (#91).

`PUBLIC_ANEMOI_API_URL` is read via `$env/dynamic/public`, but for this
static-assets-only deployment that's effectively **build-time**
configuration, not true per-request runtime config -- confirmed directly
against a real build: `adapter-static` emits `build/_app/env.js` as a real
`export const env = {...}` literal with whatever was in the environment
when `vite build` ran already baked in, fetched via a lazy `import()` at
page load but fixed at build time regardless. Deploying against a
different API target means rebuilding with a different
`PUBLIC_ANEMOI_API_URL`, not just redeploying:

```sh
PUBLIC_ANEMOI_API_URL=https://anemoi-api-real.jasonkolodziej.workers.dev pnpm run cf:deploy
```

A `.env` here with the same `PUBLIC_ANEMOI_API_URL` line (see
`.env.example`) makes this the default for every `pnpm run cf:deploy`
too, so a plain `pnpm run cf:deploy` doesn't silently fall back to the
`127.0.0.1:8000` dev default and ship a console that can't reach
anything -- found the hard way, three real deploys in, once against
`.env`'s absence.

Live at `https://anemoi.systems` (custom domain, `console/wrangler.jsonc`'s
`routes`) and `https://anemoi-console.jasonkolodziej.workers.dev`, both
pointed at the real-mode API. The real API's `ANEMOI_API_CORS_ORIGINS`
(`docker/api/Dockerfile`) has to explicitly allow-list *both* of this
console's origins -- main.py's own default only covers local dev
(`localhost:5173`/`127.0.0.1:5173`), which a browser hitting the deployed
API from either deployed console origin doesn't match; found the hard
way via a real `Disallowed CORS origin` response, not assumed.

## Docs (`/docs`)

The [Anemoi wiki](https://github.com/jasonkolodziej/anemoi.wiki) rendered inside the console, in its own theme rather than GitHub's. `scripts/sync-wiki.mjs` runs before every `dev`/`build`/`check` (idempotent -- skips if content already exists, `--force` refetches): shallow-clones the wiki repo, renders each page to real HTML via `unified`/`remark`/`rehype` (GFM tables, wiki-style `[Text](Page-Name)` links rewritten to `/docs/<slug>`, heading ids via `rehype-slug`), and writes `static/wiki/*.html` (genuinely static content, fetched/read as files, not Svelte-component source) plus a small `src/lib/wiki-content/manifest.json` (slug -> title, the one piece `docs/[slug]/+page.server.ts`'s `entries()` needs as a build-time import for prerendering). No mdsvex, no Velite -- these are plain wiki pages with no frontmatter, so a Svelte-aware markdown compiler or a schema-validated content-collection tool buys nothing a plain `unified` pipeline doesn't already give directly.

`/docs/[slug]` opts back into SSR (`export const ssr = true`) to override the app-wide `ssr = false` in the root layout -- without it, prerendering only captures the empty client shell for each slug, not the actual content (found the hard way, first build).

Search (`$lib/wiki/search.ts`, `WikiSearch.svelte`) is client-side full-text via `minisearch`, indexing `static/wiki/search-index.json` (also written by the sync script -- plain title + stripped-markdown body per page). Fetched once, lazily, the first time someone actually searches -- no search service, no runtime dependency beyond this same deploy.

`` ```mermaid `` fences render as real diagrams: `rehype-mermaid.mjs` (build time) unwraps the code fence into `<div class="mermaid">raw source</div>`; `$lib/wiki/mermaid.ts` (browser only, dynamically imported from `docs/[slug]/+page.svelte`'s `$effect` -- not `onMount` alone, since navigating between two `/docs/[slug]` pages reuses the component instance rather than remounting it) finds those divs and renders them via Mermaid's own client-side runtime, themed onto Anemoi's palette rather than Mermaid's stock dark theme. No build-time diagram rendering -- Mermaid needs a real DOM, and pulling in a headless browser at build time just for this isn't worth it for a handful of diagrams.

## Adding more shadcn-svelte components

`components.json` is configured (`nova` style, `$lib/components/ui` alias, adopted via `pnpm dlx shadcn-svelte@latest apply --preset bJysdLKoE` -- see `src/app.css`'s "shadcn-svelte compatibility layer" comment for how pulled components inherit Anemoi's actual theme instead of shadcn's generic one). Add more with:

```sh
pnpm run shad:add dialog popover tooltip sonner
```

## Structure

```
[...]/console/
        ├── README.md                  # console / ui README
        ├── components.json            # shadcn-svelte
        ├── package.json
        ├── src/lib/
        │   ├── branding.ts             # wind-god catalog + colour rules (mirrors anemoi.branding)
        │   │   ├── api/                # types.ts (mirrors anemoi.api.schemas), client.ts, endpoints.ts
        │   │   ├── components/
        │   │   │   ├── ui/             # shadcn-svelte primitives
        │   │   │   └── anemoi/         # WindRose, ConeMap, IntensityPDFChart, ModelStatusPanel,
        │   │                           #   RIFlagBanner, FlagsList, CycleTimeline, StormCard
        │   └── routes/                 # storms list+detail, models, sources, registry, monitoring, retraining
```
