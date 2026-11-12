import type { ArchitectureOut, LayerOut } from '$lib/api/types';

/** A shape as read, without the batch dimension of a batched model. */
export function displayShape(shape: number[] | null, batched: boolean): number[] | null {
	if (!shape) return null;
	return batched && shape.length > 1 && shape[0] === 1 ? shape.slice(1) : shape;
}

export function formatShape(shape: number[] | null): string {
	return shape && shape.length ? shape.join(' × ') : '—';
}

export function formatParams(n: number): string {
	if (n >= 1e6) return `${(n / 1e6).toFixed(n >= 1e7 ? 0 : 1)}M`;
	if (n >= 1e3) return `${(n / 1e3).toFixed(n >= 1e4 ? 0 : 1)}k`;
	return String(n);
}

/** One block of the layer view: a module, or a run of identical ones. */
export interface Stage {
	key: string;
	label: string;
	type: string;
	shape: number[] | null;
	params: number;
	repeat: number;
	/** Every module inside it, for the details table. */
	children: LayerOut[];
}

/** Containers whose members are the interesting part, not the container. */
const CONTAINERS = new Set(['Sequential', 'ModuleList', 'TransformerEncoder']);

function inside(arch: ArchitectureOut, layer: LayerOut): LayerOut[] {
	return arch.layers.filter((l) => l.depth > layer.depth && l.path.startsWith(layer.path + '.'));
}

function direct(arch: ArchitectureOut, layer: LayerOut): LayerOut[] {
	return arch.layers.filter((l) => l.depth === layer.depth + 1 && l.path.startsWith(layer.path + '.'));
}

/** The members a container shows as blocks: those that hold parameters or
 * change the shape (activations and dropout don't earn a block), looking
 * through one wrapper (TransformerEncoder -> its `layers` ModuleList). */
function members(arch: ArchitectureOut, layer: LayerOut): LayerOut[] {
	let kids = direct(arch, layer);
	if (kids.length === 1 && kids[0].type === 'ModuleList') kids = direct(arch, kids[0]);
	let previous = layer.output_shape;
	return kids.filter((k) => {
		const changes = k.output_shape && JSON.stringify(k.output_shape) !== JSON.stringify(previous);
		if (k.output_shape) previous = k.output_shape;
		return k.total_params > 0 || changes;
	});
}

function single(arch: ArchitectureOut, layer: LayerOut): Stage {
	const children = inside(arch, layer);
	let shape = layer.output_shape;
	if (!shape) {
		// A container that never ran itself: its last member that did.
		shape = [...children].reverse().find((c) => c.output_shape)?.output_shape ?? null;
	}
	return {
		key: layer.path,
		label: layer.path,
		type: layer.type,
		shape: displayShape(shape, arch.batched),
		params: layer.total_params,
		repeat: 1,
		children
	};
}

export function stagesOf(arch: ArchitectureOut): Stage[] {
	const stages: Stage[] = [];
	for (const layer of arch.layers.filter((l) => l.depth === 1)) {
		const shown = CONTAINERS.has(layer.type) ? members(arch, layer) : [];
		if (shown.length < 2 || shown.length > 16) {
			stages.push(single(arch, layer));
			continue;
		}
		// Consecutive identical members (same type and output shape) as one
		// block marked ×N -- six encoder layers read as one repeated block.
		for (const m of shown) {
			const s = single(arch, m);
			const last = stages[stages.length - 1];
			if (
				last &&
				last.key.startsWith(layer.path + '.') &&
				last.type === s.type &&
				JSON.stringify(last.shape) === JSON.stringify(s.shape)
			) {
				last.repeat += 1;
				last.params += s.params;
				last.children = [...last.children, m, ...s.children];
				// encoder.layers.0 + encoder.layers.5 -> "encoder.layers.0–5"
				const a = last.key.split('.');
				const b = m.path.split('.');
				let i = 0;
				while (i < a.length - 1 && a[i] === b[i]) i++;
				last.label = `${a.join('.')}–${b.slice(i).join('.')}`;
			} else {
				stages.push({ ...s, children: [m, ...s.children] });
			}
		}
	}
	return stages;
}
