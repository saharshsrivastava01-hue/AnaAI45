import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { Script } from "node:vm";

const worker = await readFile(new URL("../src/index.js", import.meta.url), "utf8");
const platform = await readFile(new URL("../../platform.html", import.meta.url), "utf8");
const platformScript = await readFile(new URL("../../platform.js", import.meta.url), "utf8");
const schema = await readFile(new URL("../schema.sql", import.meta.url), "utf8");
const migration = await readFile(new URL("../migrations/0002_creator_key_ownership.sql", import.meta.url), "utf8");
const auditMigration = await readFile(new URL("../migrations/0003_moderation_audit_log.sql", import.meta.url), "utf8");
const auditImmutabilityMigration = await readFile(new URL("../migrations/0004_moderation_audit_immutability.sql", import.meta.url), "utf8");
const auditNoReplaceMigration = await readFile(new URL("../migrations/0006_moderation_audit_no_replace.sql", import.meta.url), "utf8");
const http = await readFile(new URL("../src/http.js", import.meta.url), "utf8");
const ai = await readFile(new URL("../src/ai.js", import.meta.url), "utf8");

test("moderation routes use strong shared-token verification and bounded attempts", () => {
  const matches = worker.match(/path === "\/api\/v1\/moderation\/queue"/g) || [];
  assert.equal(matches.length, 1);
  assert.match(worker, /async function authorizeAdmin\(request, env\)/);
  assert.match(worker, /crypto\.subtle\.digest\("SHA-256"/);
  assert.match(worker, /rateLimit\(request, env, "admin-auth", 60\)/);
  assert.doesNotMatch(worker, /token !== env\.ADMIN_TOKEN/);
});

test("report resolution is operator protected and only permits pending reports", () => {
  assert.match(worker, /moderation\/reports/);
  assert.match(worker, /!\["reviewed", "dismissed"\]\.includes\(b\.status\)/);
  assert.match(worker, /UPDATE abuse_reports SET status=\? WHERE id=\? AND status='pending'/);
  assert.match(platformScript, /reportButton\("Mark reviewed"/);
  assert.match(platformScript, /reportButton\("Dismiss"/);
});

test("creator enrollment stores a public P-256 key only after signature verification", () => {
  assert.match(worker, /verifyDetachedSignature\(publicKey, signature, fingerprint, claim\)/);
  assert.match(worker, /owner_public_key,owner_fingerprint,ownership_verified_at/);
  assert.match(schema, /idx_creators_owner_fingerprint/);
  assert.match(schema, /owner_public_key TEXT/);
  assert.match(schema, /owner_fingerprint TEXT/);
  assert.match(migration, /ALTER TABLE creators ADD COLUMN owner_public_key TEXT/);
  assert.match(platformScript, /generateKey\(\{ name:"ECDSA", namedCurve:"P-256" \}, false/);
  assert.match(platformScript, /indexedDB\.open\(KEY_DB, 1\)/);
});

test("post submissions are signed by the enrolled creator key, not a supplied handle", () => {
  assert.match(worker, /SELECT id,handle,status,owner_public_key,owner_fingerprint,ownership_verified_at FROM creators WHERE id/);
  assert.match(worker, /fingerprint !== creator\.owner_fingerprint/);
  assert.match(worker, /verifyDetachedSignature\(creator\.owner_public_key, signature, creator\.owner_fingerprint, signedPost\)/);
  assert.match(worker, /author_fingerprint,author_signature/);
  assert.doesNotMatch(worker, /INSERT INTO posts\(id,creator_id,title,body,category,created_at,status\)/);
  assert.match(platform, /Sign & submit for review/);
});

test("creator approval fails closed for legacy profiles without ownership proof", () => {
  assert.match(worker, /owner_public_key IS NOT NULL AND owner_fingerprint IS NOT NULL AND ownership_verified_at IS NOT NULL/);
});

test("moderation UI contains report actions and keeps the token in the current form only", () => {
  assert.match(platform, /id="adminToken"/);
  assert.match(platformScript, /authorization:"Bearer " \+ token/);
  assert.doesNotMatch(platformScript, /localStorage\.setItem\([^\n]*adminToken/i);
});

test("static creator frontend JavaScript parses without syntax errors", () => {
  assert.match(platform, /<script src="platform\.js" defer><\/script>/);
  assert.doesNotThrow(() => new Script(platformScript));
});


test("all Worker JSON endpoints use bounded streaming body parsing", () => {
  assert.doesNotMatch(worker, /request\.json\(\)/);
  assert.match(worker, /readJson\(request\)/);
  assert.match(http, /request\.body\.getReader\(\)/);
  assert.match(http, /total > maxBytes/);
  assert.match(ai, /readJson\(request, 20 \* 1024\)/);
});

test("per-IP rate limits use a single atomic D1 upsert", () => {
  assert.match(http, /ON CONFLICT\(bucket\) DO UPDATE SET/);
  assert.match(http, /RETURNING hits/);
  assert.match(worker, /consumeRateLimit\(env\.DB/);
  assert.match(ai, /consumeRateLimit\(env\.DB/);
});


test("moderation status changes have an append-only audit trail", () => {
  assert.match(schema, /CREATE TABLE IF NOT EXISTS moderation_events/);
  assert.match(auditMigration, /CREATE TABLE IF NOT EXISTS moderation_events/);
  assert.match(worker, /INSERT INTO moderation_events/);
  assert.match(worker, /env\.DB\.batch\(\[audit, update\]\)/);
  assert.match(worker, /FROM moderation_events ORDER BY created_at DESC LIMIT 50/);
  assert.match(platformScript, /Recent moderation activity/);
  assert.match(platformScript, /event\.actor_type/);
});

test("moderation audit rows reject ordinary updates and deletes", () => {
  for (const sql of [schema, auditImmutabilityMigration]) {
    assert.match(sql, /CREATE TRIGGER IF NOT EXISTS moderation_events_no_update/);
    assert.match(sql, /BEFORE UPDATE ON moderation_events/);
    assert.match(sql, /CREATE TRIGGER IF NOT EXISTS moderation_events_no_delete/);
    assert.match(sql, /BEFORE DELETE ON moderation_events/);
    assert.match(sql, /RAISE\(ABORT, 'moderation_events is append-only'\)/);
  }
});

test("moderation audit schema blocks INSERT OR REPLACE and UPSERT replacement", () => {
  for (const sql of [schema, auditNoReplaceMigration]) {
    assert.match(sql, /CREATE TRIGGER IF NOT EXISTS moderation_events_no_replace/);
    assert.match(sql, /BEFORE INSERT ON moderation_events/);
    assert.match(sql, /WHEN EXISTS \(SELECT 1 FROM moderation_events WHERE id = NEW\.id\)/);
    assert.match(sql, /RAISE\(ABORT, 'moderation_events is append-only'\)/);
  }
});

test("identity destinations and creator websites use strict HTTPS URL validation", () => {
  assert.match(http, /export function isSafeHttpsUrl\(value\)/);
  assert.match(worker, /isSafeHttpsUrl\(record\.destination\)/);
  assert.match(worker, /isSafeHttpsUrl\(website\)/);
});
