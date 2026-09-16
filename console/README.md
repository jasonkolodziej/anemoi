# Anemoi Console

A SvelteKit 5 + TypeScript + shadcn-svelte console for [Anemoi](https://github.com/jasonkolodziej/anemoi) — active storms, cone/track visualization, model contribution weights, intensity forecasts, the model registry, drift/skew monitoring, and retraining triggers. Talks to `anemoi.api` (see the wiki's [API](https://github.com/jasonkolodziej/anemoi/wiki/API) page, `docs/api.md` in the anemoi repo, or `anemoi-api-patch.zip` alongside this project).

Client-rendered SPA end to end (`routes/+layout.ts` sets `ssr = false`) — there's no server runtime to deploy, `npm run build` emits static files for any host.

## Design system

Every saturated colour in this app identifies one Anemoi model — the six wind-god colours plus Fusion's neutral — copied from `anemoi.branding` into `src/lib/branding.ts`. Everything else (chrome, interactive states) draws from a single neutral scale plus one dedicated action-blue that appears nowhere in the god palette. Tokens live in `src/app.css`'s `@theme` block (Tailwind v4, CSS-first config).

Type: Space Grotesk (display) / Inter (UI) / IBM Plex Mono (data — coordinates, cycle labels, durations only, never UI labels).

## Getting started

```sh
npm install
cp .env.example .env   # PUBLIC_ANEMOI_API_URL, defaults to http://127.0.0.1:8000
npm run dev            # http://localhost:5173
```

Needs `anemoi.api` running (`uv run python -m anemoi.api --reload` from the anemoi repo) — the dashboard shows a connection error with instructions if it can't reach it.

```sh
npm run build     # static output in build/
npm run preview   # serve the production build locally
npm run check     # svelte-check, 0 errors as of this scaffold
```

## Adding more shadcn-svelte components

`components.json` is configured (`new-york` style, `$lib/components/ui` alias). The hand-written primitives here (Button, Badge, Card, Separator, Table, Tabs) cover what the current routes need; add more with the usual CLI once you have network access to the shadcn-svelte registry:

```sh
npx shadcn-svelte@latest add dialog popover tooltip sonner
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
