from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "schema.sql").read_text(encoding="utf-8")
MIGRATIONS = ROOT / "migrations"


def columns(db, table):
    return {row[1] for row in db.execute(f"PRAGMA table_info({table})")}


def expect_integrity_error(action, message):
    try:
        action()
    except sqlite3.IntegrityError:
        return
    raise AssertionError(message)


def test_fresh_schema():
    db = sqlite3.connect(":memory:")
    db.executescript(SCHEMA)
    assert {"owner_public_key", "owner_fingerprint", "ownership_verified_at", "rejected_handle"} <= columns(db, "creators")
    indexes = {row[1] for row in db.execute("PRAGMA index_list(rate_limits)")}
    assert "idx_rate_limits_window_started" in indexes
    assert {"author_fingerprint", "author_signature"} <= columns(db, "posts")
    assert {"id", "target_type", "target_id", "action", "from_status", "to_status", "actor_type", "created_at"} <= columns(db, "moderation_events")
    db.execute(
        "INSERT INTO moderation_events(id,target_type,target_id,action,from_status,to_status,created_at) VALUES(?,?,?,?,?,?,?)",
        ("fresh-event", "report", "report-1", "reviewed", "pending", "reviewed", "2026-01-01T00:00:00Z"),
    )
    expect_integrity_error(
        lambda: db.execute("UPDATE moderation_events SET action='changed' WHERE id='fresh-event'"),
        "Fresh schema must reject audit updates",
    )
    expect_integrity_error(
        lambda: db.execute("DELETE FROM moderation_events WHERE id='fresh-event'"),
        "Fresh schema must reject audit deletes",
    )
    replacement_values = ("fresh-event", "report", "report-1", "tampered", "pending", "dismissed", "2026-01-02T00:00:00Z")
    expect_integrity_error(
        lambda: db.execute(
            "INSERT OR REPLACE INTO moderation_events(id,target_type,target_id,action,from_status,to_status,created_at) VALUES(?,?,?,?,?,?,?)",
            replacement_values,
        ),
        "Fresh schema must reject INSERT OR REPLACE of an existing audit ID",
    )
    expect_integrity_error(
        lambda: db.execute(
            "INSERT INTO moderation_events(id,target_type,target_id,action,from_status,to_status,created_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET action=excluded.action",
            replacement_values,
        ),
        "Fresh schema must reject UPSERT replacement of an existing audit ID",
    )
    assert db.execute("SELECT action FROM moderation_events WHERE id='fresh-event'").fetchone()[0] == "reviewed"
    db.close()


def test_existing_database_migrations():
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
        CREATE TABLE creators (
            id TEXT PRIMARY KEY,
            handle TEXT NOT NULL UNIQUE COLLATE NOCASE,
            display_name TEXT NOT NULL,
            bio TEXT NOT NULL DEFAULT '',
            website TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        );
        CREATE TABLE posts (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            category TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            FOREIGN KEY (creator_id) REFERENCES creators(id)
        );
        CREATE TABLE rate_limits (
            bucket TEXT PRIMARY KEY,
            hits INTEGER NOT NULL,
            window_started INTEGER NOT NULL
        );
        CREATE TABLE abuse_reports (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            reason TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        );
        INSERT INTO creators(id,handle,display_name,created_at) VALUES('legacy-creator','legacyname','Legacy','2026-01-01');
        INSERT INTO creators(id,handle,display_name,created_at,status) VALUES('rejected-creator','releasedhandle','Rejected','2026-01-02','rejected');
        INSERT INTO posts(id,creator_id,title,body,category,created_at) VALUES('legacy-post','legacy-creator','Old post','Body','General','2026-01-01');
        INSERT INTO abuse_reports(id,label,reason,created_at) VALUES('report-atomic','legacyname','Spam','2026-01-01');
    """)
    db.executescript((MIGRATIONS / "0002_creator_key_ownership.sql").read_text(encoding="utf-8"))
    db.executescript((MIGRATIONS / "0003_moderation_audit_log.sql").read_text(encoding="utf-8"))
    migration_4 = (MIGRATIONS / "0004_moderation_audit_immutability.sql").read_text(encoding="utf-8")
    migration_5 = (MIGRATIONS / "0005_rate_limit_retention_index.sql").read_text(encoding="utf-8")
    migration_6 = (MIGRATIONS / "0006_moderation_audit_no_replace.sql").read_text(encoding="utf-8")
    db.executescript(migration_4)
    db.executescript(migration_5)
    db.executescript(migration_6)
    migration_7 = (MIGRATIONS / "0007_rejected_creator_handle_release.sql").read_text(encoding="utf-8")
    db.executescript(migration_7)
    indexes = {row[1] for row in db.execute("PRAGMA index_list(rate_limits)")}
    assert "idx_rate_limits_window_started" in indexes
    plan = db.execute(
        "EXPLAIN QUERY PLAN SELECT bucket FROM rate_limits WHERE window_started < ? ORDER BY window_started ASC LIMIT ?",
        (0, 10),
    ).fetchall()
    assert any("idx_rate_limits_window_started" in str(row) for row in plan)

    assert {"owner_public_key", "owner_fingerprint", "ownership_verified_at"} <= columns(db, "creators")
    assert {"author_fingerprint", "author_signature"} <= columns(db, "posts")
    assert db.execute("SELECT status FROM creators WHERE id='legacy-creator'").fetchone()[0] == "pending"
    assert db.execute("SELECT status FROM posts WHERE id='legacy-post'").fetchone()[0] == "pending"
    assert db.execute("SELECT owner_fingerprint FROM creators WHERE id='legacy-creator'").fetchone()[0] is None
    rejected = db.execute("SELECT handle,rejected_handle,status FROM creators WHERE id='rejected-creator'").fetchone()
    assert rejected == ("rejected-rejected-creator", "releasedhandle", "rejected")
    db.execute("INSERT INTO creators(id,handle,display_name,created_at) VALUES('new-owner','releasedhandle','New owner','2026-01-03')")
    assert db.execute("SELECT COUNT(*) FROM creators WHERE handle='releasedhandle'").fetchone()[0] == 1

    # Migrations 0003/0004 are deliberately safe to retry after an interrupted setup.
    db.executescript((MIGRATIONS / "0003_moderation_audit_log.sql").read_text(encoding="utf-8"))
    db.executescript(migration_4)
    db.executescript(migration_5)
    db.executescript(migration_6)

    db.execute(
        "INSERT INTO moderation_events(id,target_type,target_id,action,from_status,to_status,created_at) VALUES(?,?,?,?,?,?,?)",
        ("migration-event", "report", "report-atomic", "reviewed", "pending", "reviewed", "2026-01-01T00:00:00Z"),
    )
    expect_integrity_error(
        lambda: db.execute("UPDATE moderation_events SET action='changed' WHERE id='migration-event'"),
        "Migrated database must reject audit updates",
    )
    expect_integrity_error(
        lambda: db.execute("DELETE FROM moderation_events WHERE id='migration-event'"),
        "Migrated database must reject audit deletes",
    )
    replacement_values = ("migration-event", "report", "report-atomic", "tampered", "pending", "dismissed", "2026-01-02T00:00:00Z")
    expect_integrity_error(
        lambda: db.execute(
            "INSERT OR REPLACE INTO moderation_events(id,target_type,target_id,action,from_status,to_status,created_at) VALUES(?,?,?,?,?,?,?)",
            replacement_values,
        ),
        "Migrated database must reject INSERT OR REPLACE of an existing audit ID",
    )
    expect_integrity_error(
        lambda: db.execute(
            "INSERT INTO moderation_events(id,target_type,target_id,action,from_status,to_status,created_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET action=excluded.action",
            replacement_values,
        ),
        "Migrated database must reject UPSERT replacement of an existing audit ID",
    )
    assert db.execute("SELECT action FROM moderation_events WHERE id='migration-event'").fetchone()[0] == "reviewed"

    # Exercise the same audit-then-status transaction pattern used by the Worker.
    db.commit()
    db.executescript("""
        CREATE TRIGGER fail_report_update
        BEFORE UPDATE ON abuse_reports
        BEGIN
            SELECT RAISE(ABORT, 'simulated status-write failure');
        END;
    """)
    db.commit()
    try:
        db.execute("BEGIN")
        db.execute(
            """
            INSERT INTO moderation_events(id,target_type,target_id,action,from_status,to_status,created_at)
            SELECT ?, 'report', id, 'reviewed', 'pending', 'reviewed', ?
            FROM abuse_reports WHERE id=? AND status='pending'
            """,
            ("event-atomic", "2026-01-01T00:00:01Z", "report-atomic"),
        )
        db.execute("UPDATE abuse_reports SET status='reviewed' WHERE id='report-atomic' AND status='pending'")
        db.commit()
        raise AssertionError("Simulated status-write failure should abort the transaction")
    except sqlite3.IntegrityError:
        db.rollback()

    assert db.execute("SELECT status FROM abuse_reports WHERE id='report-atomic'").fetchone()[0] == "pending"
    assert db.execute("SELECT COUNT(*) FROM moderation_events WHERE id='event-atomic'").fetchone()[0] == 0
    db.close()


if __name__ == "__main__":
    test_fresh_schema()
    test_existing_database_migrations()
    print("SQLite schema, migrations, audit triggers and moderation rollback checks passed.")
