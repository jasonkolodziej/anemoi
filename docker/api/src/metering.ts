/**
 * #171 Phase 2 groundwork: one row per accepted cycle run. Nothing reads
 * this yet (no quota enforcement, no billing) -- it exists now so that
 * work is additive later instead of needing a migration plus a backfill
 * once there are real customers. Schema: console/schemas/anemoi.sql.
 */
export async function recordCycleRun(
	d1: D1Database,
	userId: string,
	stormId: string,
	cycleLabel: string,
): Promise<void> {
	try {
		await d1
			.prepare('INSERT INTO cycle_runs (id, user_id, storm_id, cycle_label) VALUES (?, ?, ?, ?)')
			.bind(crypto.randomUUID(), userId, stormId, cycleLabel)
			.run();
	} catch (err) {
		// Metering is an audit trail, not a gate -- a write failure here
		// must never block or fail an otherwise-accepted cycle run.
		console.error('recordCycleRun failed:', err);
	}
}
