import sections from '$lib/wiki-content/sections.json';
import type { LayoutLoad } from './$types';

// The root layout sets ssr=false app-wide (the rest of this console is a
// pure client-rendered SPA against a runtime API, with nothing to
// server-render) -- opt back in for the whole /docs subtree, or
// prerendering only captures the empty client shell for each page instead
// of the actual wiki content (found the hard way, first build).
export const ssr = true;
export const prerender = true;

export const load: LayoutLoad = () => ({ sections });
