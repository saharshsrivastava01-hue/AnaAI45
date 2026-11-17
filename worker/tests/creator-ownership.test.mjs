import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";
import { webcrypto } from "node:crypto";

if (!globalThis.crypto) globalThis.crypto = webcrypto;

class FakeD1 {
  constructor() {
    this.rates = new Map();
    this.creators = new Map();
    this.posts = new Map();
    this.reports = new Map();
  }
  prepare(sql) { return new FakeStatement(this, sql); }
}
class FakeStatement {
  constructor(db, sql) { this.db = db; this.sql = sql; this.values = []; }
  bind(...values) { this.values = values; return this; }
  async first() {
    const v = this.values;
    if (this.sql.startsWith("INSERT INTO rate_limits")) {
      const [bucket, now] = v;
      let row = this.db.rates.get(bucket);
      if (!row || now - row.window_started >= 60) row = { hits:1, window_started:now };
      else row.hits += 1;
      this.db.rates.set(bucket, row);
      return { hits:row.hits };
    }
    if (this.sql.startsWith("SELECT hits, window_started FROM rate_limits")) return this.db.rates.get(v[0]) || null;
    if (this.sql.startsWith("SELECT id,handle,status FROM creators WHERE owner_fingerprint")) {
      const row = [...this.db.creators.values()].find(x => x.owner_fingerprint === v[0]);
      return row ? { id:row.id, handle:row.handle, status:row.status } : null;
    }
    if (this.sql.startsWith("SELECT id,handle,status,owner_public_key,owner_fingerprint,ownership_verified_at FROM creators WHERE id")) {
      const row = this.db.creators.get(v[0]);
      return row ? { ...row } : null;
    }
    return null;
  }
  async all() {
    if (this.sql.includes("FROM creators WHERE status='pending'")) {
      return { results:[...this.db.creators.values()].filter(x => x.status === "pending").map(x => ({...x})) };
    }
    if (this.sql.includes("FROM posts p JOIN creators c") && this.sql.includes("p.status='pending'")) {
      return { results:[...this.db.posts.values()].filter(x => x.status === "pending").map(x => ({...x})) };
    }
    if (this.sql.includes("FROM abuse_reports WHERE status='pending'")) {
      return { results:[...this.db.reports.values()].filter(x => x.status === "pending").map(x => ({...x})) };
    }
    return { results:[] };
  }
  async run() {
    const v = this.values;
    if (this.sql.startsWith("INSERT INTO rate_limits")) {
      this.db.rates.set(v[0], { hits:1, window_started:v[1] });
      return { meta:{ changes:1 } };
    }
    if (this.sql.startsWith("UPDATE rate_limits SET hits=hits+1")) {
      const row = this.db.rates.get(v[0]);
      if (row) row.hits += 1;
      return { meta:{ changes:row ? 1 : 0 } };
    }
    if (this.sql.startsWith("INSERT INTO creators")) {
      const [id,handle,display_name,bio,website,created_at,owner_public_key,owner_fingerprint,ownership_verified_at] = v;
      if ([...this.db.creators.values()].some(x => x.handle.toLowerCase() === handle.toLowerCase() || x.owner_fingerprint === owner_fingerprint)) {
        throw Error("UNIQUE constraint failed");
      }
      this.db.creators.set(id, { id,handle,display_name,bio,website,created_at,status:"pending",owner_public_key,owner_fingerprint,ownership_verified_at });
      return { meta:{ changes:1 } };
    }
    if (this.sql.startsWith("UPDATE creators SET status=?")) {
      const [status,id] = v;
      const row = this.db.creators.get(id);
      const requiresOwner = this.sql.includes("owner_public_key IS NOT NULL");
      if (!row || row.status !== "pending" || (requiresOwner && (!row.owner_public_key || !row.owner_fingerprint || !row.ownership_verified_at))) return { meta:{ changes:0 } };
      row.status = status;
      return { meta:{ changes:1 } };
    }
    if (this.sql.startsWith("INSERT INTO posts")) {
      const [id,creator_id,title,body,category,created_at,author_fingerprint,author_signature] = v;
      if (this.db.posts.has(id)) throw Error("UNIQUE constraint failed");
      this.db.posts.set(id, { id,creator_id,title,body,category,created_at,status:"pending",author_fingerprint,author_signature });
      return { meta:{ changes:1 } };
    }
    if (this.sql.startsWith("INSERT INTO abuse_reports")) {
      const [id,label,reason,details,created_at] = v;
      this.db.reports.set(id, { id,label,reason,details,created_at,status:"pending" });
      return { meta:{ changes:1 } };
    }
    if (this.sql.startsWith("UPDATE abuse_reports SET status=?")) {
      const [status,id] = v;
      const row = this.db.reports.get(id);
      if (!row || row.status !== "pending") return { meta:{ changes:0 } };
      row.status = status;
      return { meta:{ changes:1 } };
    }
    throw Error("FakeD1 does not implement SQL: " + this.sql);
  }
}

const db = new FakeD1();
const env = { DB:db, ALLOWED_ORIGIN:"https://ultra.test", ADMIN_TOKEN:"test-admin-token" };
async function request(method, path, body, token, ip = "203.0.113.10") {
  const headers = { Origin:"https://ultra.test", "CF-Connecting-IP":ip };
  if (body !== undefined) headers["content-type"] = "application/json";
  if (token) headers.authorization = "Bearer " + token;
  return worker.fetch(new Request("https://worker.test" + path, {
    method, headers, body:body === undefined ? undefined : JSON.stringify(body)
  }), env);
}
async function rawRequest(method, path, rawBody, token, ip = "203.0.113.10") {
  const headers = { Origin:"https://ultra.test", "CF-Connecting-IP":ip, "content-type":"application/json" };
  if (token) headers.authorization = "Bearer " + token;
  return worker.fetch(new Request("https://worker.test" + path, { method, headers, body:rawBody }), env);
}
async function makeKeyPair() {
  const pair = await crypto.subtle.generateKey({ name:"ECDSA", namedCurve:"P-256" }, false, ["sign","verify"]);
  const publicBytes = new Uint8Array(await crypto.subtle.exportKey("spki", pair.publicKey));
  const publicKey = Buffer.from(publicBytes).toString("base64");
  const fingerprint = Buffer.from(await crypto.subtle.digest("SHA-256", publicBytes)).toString("hex");
  return { pair, publicKey, fingerprint };
}
async function sign(privateKey, payload) {
  const bytes = await crypto.subtle.sign({ name:"ECDSA", hash:"SHA-256" }, privateKey, new TextEncoder().encode(JSON.stringify(payload)));
  return Buffer.from(bytes).toString("base64");
}
async function enroll(handle = "securecreator") {
  const key = await makeKeyPair();
  const claim = {
    handle, displayName:"Secure Creator", bio:"Test profile", website:"",
    createdAt:new Date().toISOString(), version:1,
    publicKey:key.publicKey, fingerprint:key.fingerprint
  };
  const signature = await sign(key.pair.privateKey, claim);
  const response = await request("POST", "/api/v1/creators", { ...claim, signature });
  const data = await response.json();
  return { ...key, claim, signature, response, data };
}

test("creator enrollment requires a fresh signature matching its public key", async () => {
  const wrongKey = await makeKeyPair();
  const claim = {
    handle:"forgedcreator", displayName:"Forged", bio:"", website:"",
    createdAt:new Date().toISOString(), version:1,
    publicKey:wrongKey.publicKey, fingerprint:wrongKey.fingerprint
  };
  const attacker = await makeKeyPair();
  const response = await request("POST", "/api/v1/creators", { ...claim, signature:await sign(attacker.pair.privateKey, claim) });
  assert.equal(response.status, 400);
  assert.equal(db.creators.size, 0);
});

test("a verified creator can be approved and resolve its local key after refresh", async () => {
  const result = await enroll();
  assert.equal(result.response.status, 201);
  assert.equal(result.data.ownershipVerified, true);
  const owner = await request("GET", "/api/v1/creators/by-key/" + result.fingerprint);
  const ownerData = await owner.json();
  assert.equal(owner.status, 200);
  assert.equal(ownerData.id, result.data.id);
  const approval = await request("POST", "/api/v1/moderation/creators/" + result.data.id, { status:"approved" }, "test-admin-token");
  assert.equal(approval.status, 200);
  assert.equal(db.creators.get(result.data.id).status, "approved");
});

test("post publishing requires a signature from the creator's enrolled key", async () => {
  const result = await enroll("postowner");
  const approval = await request("POST", "/api/v1/moderation/creators/" + result.data.id, { status:"approved" }, "test-admin-token");
  assert.equal(approval.status, 200);
  const post = {
    creatorId:result.data.id, id:crypto.randomUUID(), title:"Signed post", body:"Only the owner key can submit this.",
    category:"Technology", createdAt:new Date().toISOString(), version:1, fingerprint:result.fingerprint
  };
  const forged = await makeKeyPair();
  const bad = await request("POST", "/api/v1/posts", { ...post, signature:await sign(forged.pair.privateKey, post) });
  assert.equal(bad.status, 403);
  assert.equal(db.posts.size, 0);
  const signature = await sign(result.pair.privateKey, post);
  const good = await request("POST", "/api/v1/posts", { ...post, signature });
  const data = await good.json();
  assert.equal(good.status, 201);
  assert.equal(data.status, "pending");
  assert.equal(db.posts.get(post.id).author_fingerprint, result.fingerprint);
  const replay = await request("POST", "/api/v1/posts", { ...post, signature });
  assert.equal(replay.status, 409);
});

test("legacy creators without an enrolled owner key cannot publish or be approved", async () => {
  const id = crypto.randomUUID();
  db.creators.set(id, {
    id, handle:"legacycreator", display_name:"Legacy", status:"pending",
    owner_public_key:null, owner_fingerprint:null, ownership_verified_at:null
  });
  const approval = await request("POST", "/api/v1/moderation/creators/" + id, { status:"approved" }, "test-admin-token");
  assert.equal(approval.status, 409);
  assert.equal(db.creators.get(id).status, "pending");
});

test("abuse reports can only be resolved by an operator and only once", async () => {
  const created = await request("POST", "/api/v1/reports", { label:"spam-account", reason:"Spam", details:"Repeated spam" });
  assert.equal(created.status, 201);
  const report = [...db.reports.values()][0];
  const unauthorized = await request("POST", "/api/v1/moderation/reports/" + report.id, { status:"dismissed" });
  assert.equal(unauthorized.status, 401);
  assert.equal(db.reports.get(report.id).status, "pending");
  const reviewed = await request("POST", "/api/v1/moderation/reports/" + report.id, { status:"reviewed" }, "test-admin-token");
  assert.equal(reviewed.status, 200);
  assert.equal(db.reports.get(report.id).status, "reviewed");
  const repeated = await request("POST", "/api/v1/moderation/reports/" + report.id, { status:"dismissed" }, "test-admin-token");
  assert.equal(repeated.status, 404);
});


test("oversized and malformed JSON bodies are rejected before database writes", async () => {
  const before = db.reports.size;
  const oversized = await rawRequest(
    "POST",
    "/api/v1/reports",
    JSON.stringify({ label:"large-report", reason:"spam", details:"x".repeat(9000) }),
    undefined,
    "203.0.113.11"
  );
  assert.equal(oversized.status, 413);
  assert.equal(db.reports.size, before);
  const malformed = await rawRequest("POST", "/api/v1/reports", "{", undefined, "203.0.113.12");
  assert.equal(malformed.status, 400);
  assert.equal(db.reports.size, before);
});

test("concurrent requests cannot exceed the atomic per-IP report limit", async () => {
  const responses = await Promise.all(Array.from({ length:8 }, (_, i) =>
    request("POST", "/api/v1/reports", { label:"rate-" + i, reason:"spam" }, undefined, "198.51.100.44")
  ));
  const statuses = responses.map(x => x.status).sort((a,b) => a-b);
  assert.deepEqual(statuses, [201,201,201,201,201,429,429,429]);
});
