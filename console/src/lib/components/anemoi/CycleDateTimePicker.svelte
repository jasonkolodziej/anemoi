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
	 *
	 * `range` (`runnableCycleRange`) bounds both fields to the cycles the
	 * API would run for this storm: days outside it are disabled in the
	 * calendar (bits-ui's `minValue`/`maxValue`, which also stop the month
	 * buttons at the bounds), and hours outside it in the select. Picking
	 * an earlier day for a storm that didn't exist yet could otherwise only
	 * be refused.
	 */
	import { CalendarDate, type DateValue } from '@internationalized/date';
	import { Calendar } from '$lib/components/ui/calendar';
	import * as Popover from '$lib/components/ui/popover';
	import { cn, cycleLabel, parseCycleLabel, SYNOPTIC_HOURS } from '$lib/utils';

	interface Props {
		value: string;
		range?: { first: Date; last: Date } | null;
	}
	let { value = $bindable(), range = null }: Props = $props();

	const toCalendarDate = (d: Date) =>
		new CalendarDate(d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate());
	const minValue = $derived(range ? toCalendarDate(range.first) : undefined);
	const maxValue = $derived(range ? toCalendarDate(range.last) : undefined);

	const at = (year: number, month: number, day: number, hour: number) =>
		new Date(Date.UTC(year, month - 1, day, hour));
	const inRange = (d: Date) => !range || (d >= range.first && d <= range.last);

	let open = $state(false);

	const parsed = $derived(parseCycleLabel(value));
	// A label at an hour no cycle starts at (e.g. `_07Z`, typed into the
	// text field) has no option here: without the blank one, the select
	// fell back to showing 00Z while the field said 07Z.
	const hour = $derived(
		parsed && (SYNOPTIC_HOURS as readonly number[]).includes(parsed.getUTCHours())
			? parsed.getUTCHours()
			: null,
	);
	const calendarValue = $derived<CalendarDate | undefined>(
		parsed ? toCalendarDate(parsed) : undefined,
	);
	// Hours the API would run on the date shown; every hour when no date is.
	const hourAllowed = $derived((h: number) =>
		parsed
			? inRange(at(parsed.getUTCFullYear(), parsed.getUTCMonth() + 1, parsed.getUTCDate(), h))
			: true,
	);

	function onDateChange(d: DateValue | undefined) {
		if (!d) return;
		// Keep the hour when the new day has it, else the nearest one it does:
		// moving 12Z onto a storm's first day, which starts at 18Z, gives 18Z.
		const keep = parsed?.getUTCHours() ?? 0;
		const nearest = SYNOPTIC_HOURS.filter((h) => inRange(at(d.year, d.month, d.day, h))).sort(
			(a, b) => Math.abs(a - keep) - Math.abs(b - keep),
		)[0];
		value = cycleLabel(at(d.year, d.month, d.day, nearest ?? keep));
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
				data-testid="cycle-date-trigger"
				class={cn(
					'font-data flex h-7.5 w-32 items-center justify-center rounded-md border',
					'border-border-strong bg-bg px-2.5 text-xs text-text hover:bg-surface-raised',
				)}
			>
				{parsed ? cycleLabel(parsed).slice(0, 8) : 'select date'}
			</Popover.Trigger>
			<Popover.Content class="w-auto border border-border bg-surface p-0 shadow-lg">
				<Calendar
					type="single"
					value={calendarValue}
					onValueChange={onDateChange}
					{minValue}
					{maxValue}
				/>
			</Popover.Content>
		</Popover.Root>
	</div>

	<div>
		<label for="cycle-hour-select" class="mb-1 block text-[11px] text-text-faint">time (UTC)</label>
		<select
			id="cycle-hour-select"
			value={hour ?? ''}
			onchange={(e) => onHourChange(Number(e.currentTarget.value))}
			class="font-data h-7.5 w-20 rounded-md border border-border-strong bg-bg px-2 text-xs text-text"
		>
			{#if hour === null}
				<option value="" disabled selected>—</option>
			{/if}
			{#each SYNOPTIC_HOURS as h (h)}
				<option value={h} disabled={!hourAllowed(h)}>{String(h).padStart(2, '0')}Z</option>
			{/each}
		</select>
	</div>
</div>
