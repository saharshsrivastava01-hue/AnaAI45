-- Apply after 0005_rate_limit_retention_index.sql.
-- SQLite REPLACE can delete conflicting rows without firing DELETE triggers when
-- recursive_triggers is disabled. Reject duplicate audit IDs before conflict handling.
CREATE TRIGGER IF NOT EXISTS moderation_events_no_replace
BEFORE INSERT ON moderation_events
WHEN EXISTS (SELECT 1 FROM moderation_events WHERE id = NEW.id)
BEGIN
  SELECT RAISE(ABORT, 'moderation_events is append-only');
END;
