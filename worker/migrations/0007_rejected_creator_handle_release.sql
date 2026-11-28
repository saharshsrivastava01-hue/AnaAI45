-- Apply once after migrations 0002–0006 on an existing database.
-- Preserve rejected creator claims for audit while releasing the public handle.
-- The tombstone is outside the API's 3–24 character handle syntax.
ALTER TABLE creators ADD COLUMN rejected_handle TEXT;

UPDATE creators
SET rejected_handle = handle,
    handle = 'rejected-' || id
WHERE status = 'rejected';
