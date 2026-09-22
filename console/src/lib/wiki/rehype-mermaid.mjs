// Turns ```mermaid fences into <div class="mermaid">raw source</div> --
// Mermaid's client-side runtime (dynamically imported in
// docs/[slug]/+page.svelte, only on pages that actually have one) finds
// elements with that class and replaces their text content with a
// rendered SVG diagram at hydration time. Rendering the diagram itself
// still happens in the browser -- Mermaid needs a DOM, so there's no good
// build-time option here without pulling in a headless browser just for
// this -- but the fence detection and unwrapping is a one-time build-time
// rewrite, same as the wiki-link rewrite.
import { visit } from 'unist-util-visit';

export function rehypeMermaid() {
	/** @param {any} tree */
	return (tree) => {
		visit(tree, 'element', (node, index, parent) => {
			if (node.tagName !== 'pre' || !parent || index === undefined) return;
			const code = node.children.find((c) => c.tagName === 'code');
			if (!code) return;
			const classes = (code.properties?.className ?? []);
			if (!classes.includes('language-mermaid')) return;

			const source = code.children.map((c) => (c.type === 'text' ? c.value : '')).join('');
			parent.children[index] = {
				type: 'element',
				tagName: 'div',
				properties: { className: ['mermaid'] },
				children: [{ type: 'text', value: source }]
			};
		});
	};
}
