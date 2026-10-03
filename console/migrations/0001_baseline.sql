-- Baseline: the auth schema as it stood when D1 migrations were adopted
-- (formerly console/schemas/better-auth.sql + anemoi.sql, applied by hand).
--
-- Every statement is IF NOT EXISTS / OR IGNORE on purpose: production
-- already had all of this when `wrangler d1 migrations apply` first ran,
-- so there this file is a no-op that just gets recorded in d1_migrations.
-- A fresh database (local dev, e2e, CI) gets the full schema. Migrations
-- after this one run exactly once per database, so they need not be
-- idempotent -- but keep them additive (see console/README.md).
--
-- One exception to "no-op on production": `plan` is a column in CREATE
-- TABLE "user" below, where production got it from anemoi.sql's ALTER
-- TABLE. If a database somehow has "user" without "plan", this won't add
-- it -- the deploy workflow's schema verification
-- (scripts/verify-d1-schema.mjs) catches exactly that kind of gap.

-- ═══════════════════════════════════════════════════════════════════════════════
-- better-auth core tables
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS "user" (
  "id" TEXT PRIMARY KEY NOT NULL,
  "name" TEXT NOT NULL,
  "email" TEXT NOT NULL UNIQUE,
  "emailVerified" INTEGER NOT NULL DEFAULT 0,
  "image" TEXT,
  "createdAt" TEXT NOT NULL DEFAULT (datetime('now')),
  "updatedAt" TEXT NOT NULL DEFAULT (datetime('now')),
  -- admin plugin columns
  "role" TEXT DEFAULT 'user',
  "banned" INTEGER DEFAULT 0,
  "banReason" TEXT,
  "banExpires" INTEGER,
  -- #171: matches auth.ts's `user.additionalFields.plan`. 'internal' is for
  -- the operator (seed by hand); 'free' for everyone until a paid tier.
  "plan" TEXT NOT NULL DEFAULT 'free'
);

CREATE TABLE IF NOT EXISTS "session" (
  "id" TEXT PRIMARY KEY NOT NULL,
  "expiresAt" TEXT NOT NULL,
  "token" TEXT NOT NULL UNIQUE,
  "createdAt" TEXT NOT NULL DEFAULT (datetime('now')),
  "updatedAt" TEXT NOT NULL DEFAULT (datetime('now')),
  "ipAddress" TEXT,
  "userAgent" TEXT,
  "userId" TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
  -- admin plugin column
  "impersonatedBy" TEXT
);

CREATE TABLE IF NOT EXISTS "account" (
  "id" TEXT PRIMARY KEY NOT NULL,
  "accountId" TEXT NOT NULL,
  "providerId" TEXT NOT NULL,
  "userId" TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
  "accessToken" TEXT,
  "refreshToken" TEXT,
  "idToken" TEXT,
  "accessTokenExpiresAt" TEXT,
  "refreshTokenExpiresAt" TEXT,
  "scope" TEXT,
  "password" TEXT,
  "createdAt" TEXT NOT NULL DEFAULT (datetime('now')),
  "updatedAt" TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS "verification" (
  "id" TEXT PRIMARY KEY NOT NULL,
  "identifier" TEXT NOT NULL,
  "value" TEXT NOT NULL,
  "expiresAt" TEXT NOT NULL,
  "createdAt" TEXT DEFAULT (datetime('now')),
  "updatedAt" TEXT DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Passkey plugin table
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS "passkey" (
  "id" TEXT PRIMARY KEY NOT NULL,
  "name" TEXT,
  "publicKey" TEXT NOT NULL,
  "userId" TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
  "credentialID" TEXT NOT NULL,
  "counter" INTEGER NOT NULL DEFAULT 0,
  "deviceType" TEXT NOT NULL,
  "backedUp" INTEGER NOT NULL DEFAULT 0,
  "transports" TEXT,
  "aaguid" TEXT,
  "createdAt" TEXT DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- API key plugin table
-- ═══════════════════════════════════════════════════════════════════════════════

-- Field list verified directly against the installed
-- @better-auth/api-key@1.7.7 package's own schema (its `apiKeySchema`,
-- node_modules/@better-auth/api-key/dist/index.mjs) rather than trusted
-- as ported: the reveille-registry version of this file used `userId`
-- and had no `configId` column, both stale against 1.7.7 -- `userId` was
-- renamed to `referenceId` (still the owning user's id by default; only
-- changes meaning if the plugin is configured with
-- `references: "organization"`, which it isn't here), and `configId` is
-- now a required column (`defaultValue: "default"`) for multi-config
-- support this project doesn't use.
CREATE TABLE IF NOT EXISTS "apikey" (
  "id" TEXT PRIMARY KEY NOT NULL,
  "configId" TEXT NOT NULL DEFAULT 'default',
  "name" TEXT,
  "start" TEXT,
  "prefix" TEXT,
  "key" TEXT NOT NULL,
  "referenceId" TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
  -- INTEGER (milliseconds) -- the plugin's own type is `number`. Was TEXT
  -- as ported; a database created from the old file keeps TEXT affinity
  -- (CREATE TABLE IF NOT EXISTS won't change it), which is harmless: the
  -- only read is a `>` comparison that coerces, and nothing here sets
  -- refills (server-only option, unused).
  "refillInterval" INTEGER,
  "refillAmount" INTEGER,
  "lastRefillAt" TEXT,
  "enabled" INTEGER DEFAULT 1,
  "rateLimitEnabled" INTEGER DEFAULT 1,
  "rateLimitTimeWindow" INTEGER,
  "rateLimitMax" INTEGER,
  "requestCount" INTEGER DEFAULT 0,
  "remaining" INTEGER,
  "lastRequest" TEXT,
  "expiresAt" TEXT,
  "createdAt" TEXT NOT NULL DEFAULT (datetime('now')),
  "updatedAt" TEXT NOT NULL DEFAULT (datetime('now')),
  "permissions" TEXT,
  "metadata" TEXT
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Registration policy table (runtime config)
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS "registration_policy" (
  "key" TEXT PRIMARY KEY,
  "value" TEXT NOT NULL,
  "updated_at" TEXT DEFAULT (datetime('now'))
);

-- Seed with default: registration closed
INSERT OR IGNORE INTO "registration_policy" ("key", "value")
  VALUES ('open_registration', 'false');

-- ═══════════════════════════════════════════════════════════════════════════════
-- Indexes
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_session_userId ON "session"("userId");
CREATE INDEX IF NOT EXISTS idx_session_token ON "session"("token");
CREATE INDEX IF NOT EXISTS idx_account_userId ON "account"("userId");
CREATE INDEX IF NOT EXISTS idx_passkey_userId ON "passkey"("userId");
CREATE INDEX IF NOT EXISTS idx_passkey_credentialID ON "passkey"("credentialID");
CREATE INDEX IF NOT EXISTS idx_apikey_referenceId ON "apikey"("referenceId");
CREATE INDEX IF NOT EXISTS idx_apikey_key ON "apikey"("key");

-- ═══════════════════════════════════════════════════════════════════════════════
-- Seed admin (run manually after the first user signs up)
-- ═══════════════════════════════════════════════════════════════════════════════
-- Option A: Set ADMIN_USER_IDS env var in wrangler.jsonc or via `wrangler secret put`
-- Option B: Run this SQL after the first user is created:
--   UPDATE "user" SET "role" = 'admin' WHERE "email" = 'your@email.com';

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
