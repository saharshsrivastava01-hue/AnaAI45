PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS identities (
  label TEXT PRIMARY KEY COLLATE NOCASE,
  namespace TEXT NOT NULL CHECK(namespace = 'ultra'),
  record_json TEXT NOT NULL,
  fingerprint TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_identities_created_at ON identities(created_at DESC);

CREATE TABLE IF NOT EXISTS rate_limits (
  bucket TEXT PRIMARY KEY,
  hits INTEGER NOT NULL,
  window_started INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS abuse_reports (
  id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  reason TEXT NOT NULL,
  details TEXT,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
);

-- Names are globally unique in this D1 database. No private keys are stored here.


-- Community publishing: submissions are hidden until an operator approves them.
CREATE TABLE IF NOT EXISTS creators (
  id TEXT PRIMARY KEY,
  handle TEXT NOT NULL UNIQUE COLLATE NOCASE,
  display_name TEXT NOT NULL,
  bio TEXT NOT NULL DEFAULT '',
  website TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  owner_public_key TEXT,
  owner_fingerprint TEXT,
  ownership_verified_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_creators_owner_fingerprint
  ON creators(owner_fingerprint) WHERE owner_fingerprint IS NOT NULL;

CREATE TABLE IF NOT EXISTS posts (
  id TEXT PRIMARY KEY,
  creator_id TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  category TEXT NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  author_fingerprint TEXT,
  author_signature TEXT,
  FOREIGN KEY (creator_id) REFERENCES creators(id)
);
CREATE INDEX IF NOT EXISTS idx_posts_public ON posts(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_creators_public ON creators(status, created_at DESC);


-- Append-only operator moderation history. The actor label deliberately reflects
-- the current shared-token model; it does not claim individual operator identity.
CREATE TABLE IF NOT EXISTS moderation_events (
  id TEXT PRIMARY KEY,
  target_type TEXT NOT NULL CHECK(target_type IN ('report','creator','post')),
  target_id TEXT NOT NULL,
  action TEXT NOT NULL,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  actor_type TEXT NOT NULL DEFAULT 'shared-admin-token',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_moderation_events_created
  ON moderation_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_moderation_events_target
  ON moderation_events(target_type, target_id, created_at DESC);
