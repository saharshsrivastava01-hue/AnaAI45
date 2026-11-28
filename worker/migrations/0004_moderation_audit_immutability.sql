-- Apply after 0003_moderation_audit_log.sql.
-- Prevent ordinary application SQL from updating or deleting moderation history.
-- A D1/database administrator can still drop these triggers; this is not tamper-proof storage.
CREATE TRIGGER IF NOT EXISTS moderation_events_no_update
BEFORE UPDATE ON moderation_events
BEGIN
  SELECT RAISE(ABORT, 'moderation_events is append-only');
END;

CREATE TRIGGER IF NOT EXISTS moderation_events_no_delete
BEFORE DELETE ON moderation_events
BEGIN
  SELECT RAISE(ABORT, 'moderation_events is append-only');
END;
