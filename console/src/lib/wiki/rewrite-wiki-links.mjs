// GitHub wiki pages link to each other by bare page name -- `[Decision
// Log](Decision-Log)`, sometimes with a `#heading` fragment -- which GitHub's
// own wiki renderer resolves relative to the wiki. Rendered inside the
// console those hrefs are just broken text. A remark plugin (run by mdsvex
// at build time, so this is a one-time rewrite baked into the prerendered
// output, not a runtime patch) turns them into real /docs/<slug> routes.
import { visit } from 'unist-util-visit';

const BARE_WIKI_LINK = /^([A-Za-z0-9_-]+)(#.*)?$/;

export function rewriteWikiLinks() {
	/** @param {any} tree */
	return (tree) => {
		visit(tree, 'link', (node) => {
			const match = BARE_WIKI_LINK.exec(node.url);
			if (!match) return;
			const [, page, fragment = ''] = match;
			node.url = `/docs/${page.toLowerCase()}${fragment}`;
		});
	};
}
