<script lang="ts">
	/**
	 * A date + synoptic-hour picker that writes into the same cycle-label
	 * string the raw text input next to it edits directly (see
	 * routes/storms/[stormId]/+page.svelte) -- two convenience fields
	 * alongside the existing one, not a replacement for it.
	 *
	 * Built from shadcn-svelte's real Calendar/Popover components
	 * (`pnpm run shad:add calendar popover`, per
	 * https://www.shadcn-svelte.com/docs/components/calendar
	 * #date-and-time-picker's composition), not hand-rolled.
	 *
	 * The "time" field is a 00/06/12/18Z select, not the reference's
	 * freeform `<input type="time">` -- a real domain constraint, not a
	 * stylistic choice: `SYNOPTIC_HOURS` mirrors
	 * `anemoi.time_utils.SYNOPTIC_HOURS`, and the API rejects any other
	 * hour outright (`require_synoptic`). A free-text time field would
	 * make it easy to pick an hour the API immediately 400s on.
	 *
	 * `@internationalized/date`'s `CalendarDate` is a pure date value with
	 * no time-of-day/timezone component -- exactly right here, since every
	 * cycle label is UTC by definition (no local-timezone conversion to
	 * get wrong).
	 */
	import { CalendarDate, type DateValue } from '@internationalized/date';
	import { Calendar } from '$lib/components/ui/calendar';
	import * as Popover from '$lib/components/ui/popover';
	import { cn, cycleLabel, parseCycleLabel, SYNOPTIC_HOURS } from '$lib/utils';

	interface Props {
		value: string;
	}
	let { value = $bindable() }: Props = $props();

	let open = $state(false);

	const parsed = $derived(parseCycleLabel(value));
	const calendarValue = $derived<CalendarDate | undefined>(
		parsed
			? new CalendarDate(parsed.getUTCFullYear(), parsed.getUTCMonth() + 1, parsed.getUTCDate())
			: undefined,
	);

	function onDateChange(d: DateValue | undefined) {
		if (!d) return;
		const hour = parsed?.getUTCHours() ?? 0;
		value = cycleLabel(new Date(Date.UTC(d.year, d.month - 1, d.day, hour)));
		open = false;
	}

	function onHourChange(hour: number) {
		const base = parsed ?? new Date();
		value = cycleLabel(
			new Date(Date.UTC(base.getUTCFullYear(), base.getUTCMonth(), base.getUTCDate(), hour)),
		);
	}
</script>

<div class="flex items-end gap-2">
	<div>
		<span class="mb-1 block text-[11px] text-text-faint">date</span>
		<Popover.Root bind:open>
			<Popover.Trigger
				class={cn(
					'font-data flex h-7.5 w-32 items-center justify-center rounded-md border',
					'border-border-strong bg-bg px-2.5 text-xs text-text hover:bg-surface-raised',
				)}
			>
				{parsed ? cycleLabel(parsed).slice(0, 8) : 'select date'}
			</Popover.Trigger>
			<Popover.Content class="w-auto border border-border bg-surface p-0 shadow-lg">
				<Calendar type="single" value={calendarValue} onValueChange={onDateChange} />
			</Popover.Content>
		</Popover.Root>
	</div>

	<div>
		<label for="cycle-hour-select" class="mb-1 block text-[11px] text-text-faint">time (UTC)</label>
		<select
			id="cycle-hour-select"
			value={parsed?.getUTCHours() ?? ''}
			onchange={(e) => onHourChange(Number(e.currentTarget.value))}
			class="font-data h-7.5 w-20 rounded-md border border-border-strong bg-bg px-2 text-xs text-text"
		>
			{#if parsed === null}
				<option value="" disabled selected>—</option>
			{/if}
			{#each SYNOPTIC_HOURS as h (h)}
				<option value={h}>{String(h).padStart(2, '0')}Z</option>
			{/each}
		</select>
	</div>
</div>
