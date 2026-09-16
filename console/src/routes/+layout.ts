// Anemoi-API has no server-rendering counterpart in this console -- every
// route fetches from a runtime API base URL, so the whole app is a static,
// client-rendered SPA (matches vite.config.ts's adapter-static + fallback).
export const ssr = false;
export const prerender = false;
