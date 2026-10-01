-- Issue #171: per-customer plan and a billable-event audit trail, on top
-- of the better-auth schema in better-auth.sql (apply that one first).
-- Apply with: wrangler d1 execute anemoi_auth --file=./schemas/anemoi.sql --remote
-- Apply with: wrangler d1 execute anemoi_auth --file=./schemas/anemoi.sql --local
--
-- Neither table is enforced against anything yet (no quotas, no billing --
-- #171's Phase 2/3). They exist now so that work is additive later instead
-- of needing a migration plus a backfill once there are real customers.

-- ═══════════════════════════════════════════════════════════════════════════════
-- Plan column on the better-auth `user` table
-- ═══════════════════════════════════════════════════════════════════════════════

-- Matches `auth.ts`'s `user.additionalFields.plan` config. `'internal'` is
-- for you (seed it by hand after your first sign-up, alongside the
-- `role = 'admin'` seed in better-auth.sql); `'free'` is the default for
-- everyone else until a paid tier exists.
ALTER TABLE "user" ADD COLUMN "plan" TEXT NOT NULL DEFAULT 'free';

-- ═══════════════════════════════════════════════════════════════════════════════
-- cycle_runs: one row per accepted `POST /v1/storms/{id}/cycles`
-- ═══════════════════════════════════════════════════════════════════════════════

-- Written by anemoi-api-real (docker/api/src/index.ts) on every request its
-- edge gate accepts -- the billable event #171 is ultimately about
-- metering. Phase 2 reads this to enforce a plan's cycle allowance; for
-- now it's just an audit trail.
CREATE TABLE IF NOT EXISTS "cycle_runs" (
  "id" TEXT PRIMARY KEY NOT NULL,
  "user_id" TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
  "storm_id" TEXT NOT NULL,
  "cycle_label" TEXT NOT NULL,
  "started_at" TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cycle_runs_userId ON "cycle_runs"("user_id");
CREATE INDEX IF NOT EXISTS idx_cycle_runs_startedAt ON "cycle_runs"("started_at");
