/**
 * Renders `<div class="mermaid">` elements (see rehype-mermaid.mjs) into
 * real SVG diagrams. Browser-only -- Mermaid needs a DOM, so this is
 * dynamically imported from docs/[slug]/+page.svelte's onMount, and only
 * on pages that actually contain a diagram, not loaded (~600KB) for every
 * doc page.
 */
let initialized = false;

export async function renderMermaidDiagrams(container: HTMLElement): Promise<void> {
	const nodes = container.querySelectorAll<HTMLElement>('.mermaid');
	if (nodes.length === 0) return;

	const { default: mermaid } = await import('mermaid');

	if (!initialized) {
		// Themed onto Anemoi's actual palette (see src/app.css's neutral
		// scale + --color-action) rather than Mermaid's stock 'dark' theme --
		// same "alias third-party tokens onto our brand" approach as the
		// shadcn-svelte compatibility layer and the glass tokens.
		mermaid.initialize({
			startOnLoad: false,
			theme: 'base',
			themeVariables: {
				background: '#0a0e17',
				primaryColor: '#111827',
				primaryTextColor: '#e7ecf3',
				primaryBorderColor: '#334155',
				lineColor: '#64748b',
				secondaryColor: '#161d29',
				tertiaryColor: '#111827',
				textColor: '#e7ecf3',
				mainBkg: '#111827',
				nodeTextColor: '#e7ecf3',
				edgeLabelBackground: '#0a0e17',
				fontFamily: "'Geist Variable', ui-sans-serif, system-ui, sans-serif"
			}
		});
		initialized = true;
	}

	await mermaid.run({ nodes: Array.from(nodes) });
}
