import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";
import { pruneExpiredRateLimits } from "../src/http.js";

class CleanupDB {
  constructor(rows = []) { this.rows = new Map(rows.map(row => [row.bucket, row])); }
  prepare(sql) { return new CleanupStatement(this, sql); }
}
class CleanupStatement {
  constructor(db, sql) { this.db = db; this.sql = sql; this.values = []; }
  bind(...values) { this.values = values; return this; }
  async run() {
    assert.match(this.sql, /DELETE FROM rate_limits/);
    assert.match(this.sql, /ORDER BY window_started ASC/);
    assert.match(this.sql, /LIMIT \?/);
    const [cutoff, batchSize] = this.values;
    const stale = [...this.db.rows.values()]
      .filter(row => row.window_started < cutoff)
      .sort((a, b) => a.window_started - b.window_started)
      .slice(0, batchSize);
    for (const row of stale) this.db.rows.delete(row.bucket);
    return { meta: { changes: stale.length } };
  }
}

test("rate-limit cleanup removes only expired buckets and respects its batch cap", async () => {
  const db = new CleanupDB([
    { bucket:"old-a", window_started:1 },
    { bucket:"old-b", window_started:2 },
    { bucket:"old-c", window_started:3 },
    { bucket:"recent", window_started:199000 }
  ]);
  const removed = await pruneExpiredRateLimits(db, 200000, 86400, 2);
  assert.equal(removed, 2);
  assert.equal(db.rows.has("old-a"), false);
  assert.equal(db.rows.has("old-b"), false);
  assert.equal(db.rows.has("old-c"), true);
  assert.equal(db.rows.has("recent"), true);
});

test("cleanup enforces a hard 500-row maximum even if a larger batch is requested", async () => {
  const rows = Array.from({ length:501 }, (_, index) => ({
    bucket:"expired-" + index,
    window_started:index
  }));
  const db = new CleanupDB(rows);
  const removed = await pruneExpiredRateLimits(db, 5000000, 86400, 5000);
  assert.equal(removed, 500);
  assert.equal(db.rows.size, 1);
});

test("scheduled handler submits one cleanup task through waitUntil", async () => {
  const now = Math.floor(Date.now() / 1000);
  const db = new CleanupDB([
    { bucket:"expired", window_started:now - 3 * 86400 },
    { bucket:"still-retained", window_started:now - 2 * 3600 }
  ]);
  let pending;
  await worker.scheduled({}, { DB:db }, { waitUntil(promise) { pending = promise; } });
  assert.ok(pending instanceof Promise);
  await pending;
  assert.equal(db.rows.has("expired"), false);
  assert.equal(db.rows.has("still-retained"), true);
});

test("scheduled handler safely does nothing when D1 is not configured", async () => {
  await worker.scheduled({}, {}, { waitUntil() { throw new Error("must not schedule without D1"); } });
});
