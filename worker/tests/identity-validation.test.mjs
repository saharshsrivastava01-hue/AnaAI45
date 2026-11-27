import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";
import { webcrypto } from "node:crypto";

if (!globalThis.crypto) globalThis.crypto = webcrypto;

class IdentityDB {
  constructor() { this.identities = new Map(); this.rates = new Map(); }
  prepare(sql) { return new IdentityStatement(this, sql); }
}
class IdentityStatement {
  constructor(db, sql) { this.db = db; this.sql = sql; this.values = []; }
  bind(...values) { this.values = values; return this; }
  async first() {
    if (!this.sql.trimStart().startsWith("INSERT INTO rate_limits")) throw Error("Unexpected first(): " + this.sql);
    const [bucket, now] = this.values;
    const current = this.db.rates.get(bucket);
    const next = !current || now - current.window_started >= 60
      ? { hits:1, window_started:now }
      : { hits:current.hits + 1, window_started:current.window_started };
    this.db.rates.set(bucket, next);
    return { hits:next.hits };
  }
  async run() {
    if (!this.sql.trimStart().startsWith("INSERT INTO identities")) throw Error("Unexpected run(): " + this.sql);
    const [label, namespace, recordJson, fingerprint, createdAt, updatedAt] = this.values;
    if (this.db.identities.has(label) || [...this.db.identities.values()].some(row => row.fingerprint === fingerprint)) {
      throw Error("UNIQUE constraint failed");
    }
    this.db.identities.set(label, { label, namespace, record_json:recordJson, fingerprint, created_at:createdAt, updated_at:updatedAt });
    return { meta:{ changes:1 } };
  }
}

const db = new IdentityDB();
async function signedRecord(label, destination) {
  const pair = await crypto.subtle.generateKey({ name:"ECDSA", namedCurve:"P-256" }, false, ["sign","verify"]);
  const publicBytes = new Uint8Array(await crypto.subtle.exportKey("spki", pair.publicKey));
  const publicKey = Buffer.from(publicBytes).toString("base64");
  const fingerprint = Buffer.from(await crypto.subtle.digest("SHA-256", publicBytes)).toString("hex");
  const record = {
    namespace:"ultra", label, destination, description:"test identity",
    createdAt:new Date().toISOString(), version:1, publicKey, fingerprint
  };
  const signature = Buffer.from(await crypto.subtle.sign(
    { name:"ECDSA", hash:"SHA-256" }, pair.privateKey,
    new TextEncoder().encode(JSON.stringify(record))
  )).toString("base64");
  return { record, signature };
}
async function submit(label, destination, ip) {
  const signed = await signedRecord(label, destination);
  return worker.fetch(new Request("https://worker.test/api/v1/identities", {
    method:"POST",
    headers:{ "content-type":"application/json", "CF-Connecting-IP":ip },
    body:JSON.stringify({ record:{ ...signed.record, signature:signed.signature } })
  }), { DB:db });
}

test("identity registration accepts empty or absolute safe HTTPS destinations", async () => {
  const empty = await submit("identityempty", "", "203.0.113.21");
  assert.equal(empty.status, 201);
  const https = await submit("identityhttps", "https://example.com/path", "203.0.113.22");
  assert.equal(https.status, 201);
  assert.equal(db.identities.size, 2);
});

test("identity registration rejects unsafe, malformed and non-string destinations", async () => {
  const invalid = [
    ["identityhttp", "http://example.com"],
    ["identityjs", "javascript:alert(1)"],
    ["identitycredentials", "https://user:password@example.com/"],
    ["identitycontrol", "https://example.com\n.evil"],
    ["identitylong", "https://example.com/" + "x".repeat(2050)],
    ["identitynull", null],
    ["identitynumber", 0]
  ];
  const before = db.identities.size;
  for (const [index, [label, destination]] of invalid.entries()) {
    const response = await submit(label, destination, "203.0.113." + (30 + index));
    assert.equal(response.status, 400, label);
  }
  assert.equal(db.identities.size, before);
});
