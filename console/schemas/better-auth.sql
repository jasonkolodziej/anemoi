-- better-auth schema for anemoi (ported from a prior project,
-- reveille-registry -- database/project names below updated to match).
-- Apply with: wrangler d1 execute anemoi_auth --file=./schemas/better-auth.sql --remote
-- Apply with: wrangler d1 execute anemoi_auth --file=./schemas/better-auth.sql --local
--
-- This migration:
-- 1. Drops the old custom auth tables (users, credentials, sessions, challenges)
-- 2. Creates the better-auth core tables (user, session, account, verification)
-- 3. Creates the passkey plugin table (passkey)
-- 4. Creates the API key plugin table (apikey)
-- 5. Adds admin plugin columns to user and session tables
-- 6. Creates the registration_policy table for runtime config

-- ═══════════════════════════════════════════════════════════════════════════════
-- Drop old tables
-- ═══════════════════════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS challenges;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS credentials;
DROP TABLE IF EXISTS users;

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
  "banExpires" INTEGER
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
-- Both marked `index: true` in better-auth 1.7.7's own schema but missing
-- from the ported file: every magic-link/email-OTP verify looks up
-- `verification` by identifier, and API-key lookups filter on configId.
-- Safe to re-run this whole file against an existing database to pick
-- these up (every statement above is IF NOT EXISTS / OR IGNORE).
CREATE INDEX IF NOT EXISTS idx_verification_identifier ON "verification"("identifier");
CREATE INDEX IF NOT EXISTS idx_apikey_configId ON "apikey"("configId");

-- ═══════════════════════════════════════════════════════════════════════════════
-- Seed admin (run manually after the first user signs up)
-- ═══════════════════════════════════════════════════════════════════════════════
-- Option A: Set ADMIN_USER_IDS env var in wrangler.jsonc or via `wrangler secret put`
-- Option B: Run this SQL after the first user is created:
--   UPDATE "user" SET "role" = 'admin' WHERE "email" = 'your@email.com';
