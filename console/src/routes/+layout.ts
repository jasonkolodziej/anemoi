// Most of the dashboard (storm cards, charts, maps) fetches client-side
// and has no real benefit from server rendering, so this stays off as the
// app-wide default. #171 gave the console a real server (login, D1-backed
// sessions, the /api proxy -- see hooks.server.ts, vite.config.ts's
// adapter-cloudflare) but `ssr`/`prerender` here only control whether a
// route's *initial HTML* is rendered server-side, not whether server code
// runs at all: `+page.server.ts` load functions and `+server.ts` routes
// (routes/auth/*, routes/profile, routes/api/[...path]) still execute
// server-side regardless of this flag.
export const ssr = false;
export const prerender = false;
