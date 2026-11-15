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
