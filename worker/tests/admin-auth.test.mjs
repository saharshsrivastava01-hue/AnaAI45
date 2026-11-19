import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";
import { webcrypto } from "node:crypto";

if (!globalThis.crypto) globalThis.crypto = webcrypto;

class RateLimitDB {
  constructor() { this.buckets = new Map(); }
  prepare(sql) { return new RateLimitStatement(this, sql); }
}
class RateLimitStatement {
  constructor(db, sql) { this.db = db; this.sql = sql; this.values = []; }
  bind(...values) { this.values = values; return this; }
  async first() {
    assert.match(this.sql, /INSERT INTO rate_limits/);
    const [bucket, now] = this.values;
    const row = this.db.buckets.get(bucket);
    const next = !row || now - row.window_started >= 60
      ? { hits:1, window_started:now }
      : { hits:row.hits + 1, window_started:row.window_started };
    this.db.buckets.set(bucket, next);
    return { hits:next.hits };
  }
  async all() { return { results:[] }; }
}

const configuredToken = "a".repeat(64);
async function call({ configured = configuredToken, authorization, ip = "203.0.113.77" } = {}) {
  const headers = { "CF-Connecting-IP":ip };
  if (authorization !== undefined) headers.Authorization = authorization;
  return worker.fetch(new Request("https://worker.test/api/v1/moderation/queue", { headers }), {
    DB:new RateLimitDB(),
    ADMIN_TOKEN:configured
  });
}

test("a strong configured bearer token can access the private moderation queue", async () => {
  const response = await call({ authorization:"Bearer " + configuredToken });
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { creators:[], posts:[], reports:[], events:[] });
});

test("missing, malformed and short operator secrets fail closed", async () => {
  assert.equal((await call({ configured:undefined, authorization:"Bearer " + configuredToken })).status, 503);
  assert.equal((await call({ configured:"short-secret", authorization:"Bearer short-secret" })).status, 503);
  assert.equal((await call({ authorization:configuredToken })).status, 401);
  assert.equal((await call({ authorization:"Basic " + configuredToken })).status, 401);
  assert.equal((await call({ authorization:"Bearer " + "b".repeat(64) })).status, 401);
});

test("moderation authentication attempts are rate limited per source IP", async () => {
  const db = new RateLimitDB();
  const env = { DB:db, ADMIN_TOKEN:configuredToken };
  const make = () => worker.fetch(new Request("https://worker.test/api/v1/moderation/queue", {
    headers:{ "CF-Connecting-IP":"198.51.100.77", Authorization:"Bearer " + "b".repeat(64) }
  }), env);
  const first = await Promise.all(Array.from({ length:60 }, () => make()));
  assert.ok(first.every(response => response.status === 401));
  const blocked = await make();
  assert.equal(blocked.status, 429);
});
