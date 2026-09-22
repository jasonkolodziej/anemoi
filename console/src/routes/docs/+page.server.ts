import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// The wiki's own Home.md is already a curated landing page (Start here,
// invariants, system diagram, the same page index the Sections sidebar
// now covers) -- no separate hand-maintained index page to keep in sync
// with it.
export const load: PageServerLoad = () => {
	redirect(307, '/docs/home');
};
