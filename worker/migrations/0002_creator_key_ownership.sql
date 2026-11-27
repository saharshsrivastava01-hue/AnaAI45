-- One-time upgrade for databases created before key-backed creator ownership.
-- Apply only to an existing database that has already received worker/schema.sql.
ALTER TABLE creators ADD COLUMN owner_public_key TEXT;
ALTER TABLE creators ADD COLUMN owner_fingerprint TEXT;
ALTER TABLE creators ADD COLUMN ownership_verified_at TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_creators_owner_fingerprint
  ON creators(owner_fingerprint) WHERE owner_fingerprint IS NOT NULL;

ALTER TABLE posts ADD COLUMN author_fingerprint TEXT;
ALTER TABLE posts ADD COLUMN author_signature TEXT;
