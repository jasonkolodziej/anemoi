<script lang="ts">
	/**
	 * The Anemoi mark: an eight-point wind rose, cardinals in god colours,
	 * diagonals in the two structural-only colours (Branding wiki, "Colour
	 * rules"). Below ~48px the diagonals drop per the same rule -- Lips lime
	 * sits close enough to Zephyrus emerald to flatten at icon sizes.
	 */
	import { GODS, STRUCTURAL_COLORS } from '$lib/branding';

	interface Props {
		size?: number;
		spinning?: boolean;
	}
	let { size = 28, spinning = false }: Props = $props();

	const cardinals = [
		{ god: GODS.find((g) => g.direction === 'N')!, angle: -90 },
		{ god: GODS.find((g) => g.direction === 'E')!, angle: 0 },
		{ god: GODS.find((g) => g.direction === 'S')!, angle: 90 },
		{ god: GODS.find((g) => g.direction === 'W')!, angle: 180 }
	];
	const diagonals = [
		{ color: GODS.find((g) => g.direction === 'NE')!.color, angle: -45 },
		{ color: STRUCTURAL_COLORS.SE, angle: 45 },
		{ color: STRUCTURAL_COLORS.SW, angle: 135 },
		{ color: GODS.find((g) => g.direction === 'NW')!.color, angle: -135 }
	];

	const showDiagonals = $derived(size >= 48);
	const r = 46;
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 100 100"
	class={spinning ? 'motion-safe:animate-[spin_40s_linear_infinite]' : ''}
	role="img"
	aria-label="Anemoi"
>
	{#if showDiagonals}
		{#each diagonals as p (p.angle)}
			<line
				x1="50"
				y1="50"
				x2={50 + r * Math.cos((p.angle * Math.PI) / 180)}
				y2={50 + r * Math.sin((p.angle * Math.PI) / 180)}
				stroke={p.color}
				stroke-width="3"
				stroke-linecap="round"
				opacity="0.55"
			/>
		{/each}
	{/if}
	{#each cardinals as p (p.god.slug)}
		<line
			x1="50"
			y1="50"
			x2={50 + r * Math.cos((p.angle * Math.PI) / 180)}
			y2={50 + r * Math.sin((p.angle * Math.PI) / 180)}
			stroke={p.god.color}
			stroke-width="4"
			stroke-linecap="round"
		/>
	{/each}
	<circle cx="50" cy="50" r="7" fill="var(--color-fusion)" />
</svg>
