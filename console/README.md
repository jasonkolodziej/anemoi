# Anemoi Console

A SvelteKit 5 + TypeScript + shadcn-svelte console for [Anemoi](https://github.com/jasonkolodziej/anemoi) — active storms, cone/track visualization, model contribution weights, intensity forecasts, the model registry, drift/skew monitoring, and retraining triggers. Talks to `anemoi.api` (see the wiki's [API](https://github.com/jasonkolodziej/anemoi/wiki/API) page, `docs/api.md` in the anemoi repo, or `anemoi-api-patch.zip` alongside this project).

Most of the dashboard is still client-rendered (`routes/+layout.ts` sets
`ssr = false`), but this is no longer a pure static-assets deployment:
#171 gave it a real Worker (`@sveltejs/adapter-cloudflare`, not
`adapter-static`) for login (`better-auth`, D1-backed sessions, passkeys,
magic link, GitHub/Google OAuth), API-key issuance, and a same-origin
`/api/*` proxy to `anemoi-api-real` that attaches the caller's identity
server-side so a raw API key never reaches the browser. See "Deploying"
below for the D1 setup and secrets this now needs.

## Design system

Every saturated colour in this app identifies one Anemoi model — the six wind-god colours plus Fusion's neutral — copied from `anemoi.branding` into `src/lib/branding.ts`. Everything else (chrome, interactive states) draws from a single neutral scale plus one dedicated action-blue that appears nowhere in the god palette. Tokens live in `src/app.css`'s `@theme` block (Tailwind v4, CSS-first config).

Type: Inter Variable (display/headings) / Geist Variable (UI, self-hosted via `@fontsource-variable`) / Geist Mono (data — coordinates, cycle labels, durations only, never UI labels; still a Google Fonts `<link>`, no `@fontsource-variable/geist-mono` package exists). `Card` and app chrome use a flat `bg-surface` fill — see `src/app.css`'s own comments for where each token comes from and why.

## Getting started

```sh
pnpm install
cp .env.example .env   # only needed if anemoi.api runs somewhere other
                        # than http://127.0.0.1:8000, see the comment inside
pnpm dev                # http://localhost:5173
```

Needs `anemoi.api` running (`uv run python -m anemoi.api --reload` from
the anemoi repo, demo mode by default) -- `pnpm dev` (plain `vite dev`,
no Cloudflare bindings) proxies `/api/*` straight to it
(`routes/api/[...path]/+server.ts`'s fallback path). `hooks.server.ts`
treats every request as anonymous when `AUTH_DB` isn't bound, so this
works with zero Cloudflare setup -- only the "Run cycle" action needs a
login, which won't work in this mode. To exercise login/API keys
locally, copy `.dev.vars.example` to `.dev.vars` and use `wrangler dev`
instead (see "Deploying" below for what each var is).

```sh
pnpm build     # emits .svelte-kit/cloudflare (adapter-cloudflare)
pnpm preview   # serve the production build locally
pnpm check     # svelte-check, 0 errors as of this scaffold
```

## Deploying

Issue #96, promoted off pure static assets by #171. Cloudflare Workers
(`@sveltejs/adapter-cloudflare`), same tooling as `docker/api`'s
deployment (#91).

`PUBLIC_ANEMOI_API_URL` is unused now that reads go through this Worker's
own `/api/*` proxy (`routes/api/[...path]/+server.ts`) to `anemoi-api-real`
via a service binding, not a direct cross-origin fetch -- no CORS
allow-listing needed either, since traffic never leaves Cloudflare's
network between the two Workers.

### D1 database

One database, shared with `docker/api` (its own `AUTH_DB` binding reads
from it; only this Worker writes):

```sh
pnpm exec wrangler d1 create anemoi_auth
# put the printed database_id into wrangler.jsonc's d1_databases AND
# ../docker/api/wrangler.jsonc's d1_databases -- both must match exactly
pnpm exec wrangler d1 migrations apply anemoi_auth --remote
```

Schema changes go in a new numbered file under `migrations/`
(`pnpm exec wrangler d1 migrations create anemoi_auth <name>`). D1 records
each applied file in its `d1_migrations` table, so each one runs exactly
once per database: `.github/workflows/deploy.yml` applies new ones
to production on merge, and `e2e/global-setup.ts` applies them locally.
Two rules, because migrations are applied *before* the new Worker
version goes live and there's no automatic down-migration:

- **Additive only.** Add tables, nullable/defaulted columns and indexes.
  The still-running previous Worker must keep working against the new
  schema. Renames/drops take two deploys: stop using it, then drop it.
- **Never edit an applied migration** -- add a new one. A changed file
  isn't re-run anywhere it's already recorded.

If a migration does go wrong, the deploy log prints a D1 Time Travel
bookmark from just before it ran:
`pnpm exec wrangler d1 time-travel restore anemoi_auth --bookmark=<id>`.

### Secrets

```sh
pnpm exec wrangler secret put BETTER_AUTH_SECRET     # openssl rand -base64 32
pnpm exec wrangler secret put GITHUB_CLIENT_ID
pnpm exec wrangler secret put GITHUB_CLIENT_SECRET
pnpm exec wrangler secret put GOOGLE_CLIENT_ID
pnpm exec wrangler secret put GOOGLE_CLIENT_SECRET
pnpm exec wrangler secret put ADMIN_USER_IDS         # comma-separated user ids; set after your first sign-up
pnpm exec wrangler secret put INTERNAL_PROXY_SECRET  # same value as docker/api's -- see docker/api/README.md
```

GitHub/Google OAuth apps need registering against this console's own
domain (`anemoi.systems`) -- credentials from any other app (including a
prior project's) won't validate the callback URL. `Email Routing` must
also be enabled on `anemoi.systems` in the dashboard before magic
link/OTP email (`src/lib/server/email.ts`, the `SEND_EMAIL` binding) sends
anything real; without it, both fall back to a `console.warn` with the
link/code, which still works for local testing.

Then deploy:

```sh
pnpm run cf:deploy
```

Live at `https://anemoi.systems` (custom domain, `console/wrangler.jsonc`'s
`routes`) and `https://anemoi-console.jasonkolodziej.workers.dev`.

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
