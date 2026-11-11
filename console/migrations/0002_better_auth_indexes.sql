-- Both marked `index: true` in better-auth 1.7.7's own schema but missing
-- from the baseline (0001): every magic-link/email-OTP verify looks up
-- `verification` by identifier, and API-key lookups filter on configId.
CREATE INDEX IF NOT EXISTS idx_verification_identifier ON "verification"("identifier");
CREATE INDEX IF NOT EXISTS idx_apikey_configId ON "apikey"("configId");
