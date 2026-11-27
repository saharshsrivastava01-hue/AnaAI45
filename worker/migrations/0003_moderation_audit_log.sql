-- Add a durable, append-only record of moderation status transitions.
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
