import { handleAI } from "./ai.js";
import { readJson, consumeRateLimit, pruneExpiredRateLimits } from "./http.js";
const JSON_HEADERS = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" };
const RESERVED = new Set(["admin","api","www","root","support","security","ultra","nexora","help","billing","login","signup","settings","mail","ftp","ns1","ns2"]);
const enc = new TextEncoder();

function response(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), { status, headers: { ...JSON_HEADERS, ...headers } });
}
function cors(request, env) {
  const origin = request.headers.get("Origin") || "";
  const configured = [
    env.ALLOWED_ORIGIN || "",
    ...(env.ALLOWED_DEV_ORIGINS || "").split(",")
  ].map(value => value.trim()).filter(Boolean);
  const headers = {
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "content-type,authorization",
    "vary": "Origin"
  };
  // Never echo an untrusted origin or silently fall back to the production origin.
  // Local development origins must be explicitly configured and are not enabled by default.
  if (origin && configured.includes(origin)) {
    headers["access-control-allow-origin"] = origin;
  }
  return headers;
}
function b64ToBytes(value) {
  const raw = atob(value);
  return Uint8Array.from(raw, c => c.charCodeAt(0));
}
function canonical(record) {
  return JSON.stringify({
    namespace: record.namespace,
    label: record.label,
    destination: record.destination,
    description: record.description,
    createdAt: record.createdAt,
    version: record.version,
    publicKey: record.publicKey,
    fingerprint: record.fingerprint
  });
}
async function verifyRecord(record) {
  try {
    if (!record || record.namespace !== "ultra" || !/^[a-z0-9_-]{3,24}$/.test(record.label) || RESERVED.has(record.label)) return false;
    if (record.destination && (typeof record.destination !== "string" || !record.destination.startsWith("https://"))) return false;
    if (typeof record.description !== "string" || record.description.length > 160) return false;
    if (record.version !== 1 || typeof record.publicKey !== "string" || typeof record.signature !== "string") return false;
    const keyBytes = b64ToBytes(record.publicKey);
    const key = await crypto.subtle.importKey("spki", keyBytes, { name: "ECDSA", namedCurve: "P-256" }, true, ["verify"]);
    const digest = await crypto.subtle.digest("SHA-256", keyBytes);
    const fingerprint = [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2, "0")).join("");
    if (fingerprint !== record.fingerprint) return false;
    return await crypto.subtle.verify(
      { name: "ECDSA", hash: "SHA-256" },
      key,
      b64ToBytes(record.signature),
      enc.encode(canonical(record))
    );
  } catch { return false; }
}
async function rateLimit(request, env, bucketName, max = 20) {
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  return consumeRateLimit(env.DB, bucketName + ":" + ip, max);
}

async function authorizeAdmin(request, env) {
  const expected = env.ADMIN_TOKEN;
  if (typeof expected !== "string" || !/^[A-Za-z0-9_-]{32,128}$/.test(expected)) {
    return { ok:false, status:503, error:"Operator authentication is not configured with a 32–128 character URL-safe token." };
  }
  if (!await rateLimit(request, env, "admin-auth", 60)) {
    return { ok:false, status:429, error:"Too many moderation authentication attempts. Try again in one minute." };
  }
  const match = /^Bearer ([A-Za-z0-9_-]{32,128})$/.exec(request.headers.get("Authorization") || "");
  if (!match) return { ok:false, status:401, error:"Unauthorized moderation request." };

  // Compare fixed-size SHA-256 digests instead of using a short-circuit string comparison.
  const [candidateDigest, expectedDigest] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(match[1])),
    crypto.subtle.digest("SHA-256", enc.encode(expected))
  ]);
  let difference = 0;
  const candidateBytes = new Uint8Array(candidateDigest);
  const expectedBytes = new Uint8Array(expectedDigest);
  for (let i = 0; i < candidateBytes.length; i++) difference |= candidateBytes[i] ^ expectedBytes[i];
  if (difference !== 0) return { ok:false, status:401, error:"Unauthorized moderation request." };
  return { ok:true };
}
async function verifyDetachedSignature(publicKeyBase64, signatureBase64, fingerprint, payload) {
  try {
    if (typeof publicKeyBase64 !== "string" || publicKeyBase64.length > 512 ||
        typeof signatureBase64 !== "string" || signatureBase64.length > 256 ||
        !/^[a-f0-9]{64}$/.test(fingerprint || "")) return false;
    const keyBytes = b64ToBytes(publicKeyBase64);
    const digest = await crypto.subtle.digest("SHA-256", keyBytes);
    const actualFingerprint = [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2, "0")).join("");
    if (actualFingerprint !== fingerprint) return false;
    const key = await crypto.subtle.importKey("spki", keyBytes, { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]);
    return await crypto.subtle.verify(
      { name: "ECDSA", hash: "SHA-256" },
      key,
      b64ToBytes(signatureBase64),
      enc.encode(JSON.stringify(payload))
    );
  } catch { return false; }
}
function freshSignedTimestamp(value) {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) && Math.abs(Date.now() - parsed) <= 5 * 60 * 1000;
}
function validUuid(value) {
  return typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

async function handle(request, env) {
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(request, env) });
  const headers = cors(request, env);
  if (path === "/api/v1/ai/chat") return handleAI(request, env, headers);
  if (!env.DB) return response({ error: "Database binding DB is not configured." }, 503, headers);
  if (request.method === "GET" && path === "/health") return response({ ok: true, service: "ULTRA Registry API", version: "1.0.0" }, 200, headers);
  if (request.method === "GET" && path === "/api/v1/registry") {
    const requested = Number(url.searchParams.get("limit") || 50);
    const limit = Math.max(1, Math.min(Number(env.MAX_PAGE_SIZE || 100), Number.isFinite(requested) ? requested : 50));
    const offset = Math.max(0, Number(url.searchParams.get("offset") || 0));
    const result = await env.DB.prepare("SELECT record_json FROM identities ORDER BY created_at DESC LIMIT ? OFFSET ?").bind(limit, offset).all();
    const count = await env.DB.prepare("SELECT COUNT(*) AS total FROM identities").first();
    return response({ items: (result.results || []).map(row => JSON.parse(row.record_json)), total: count.total, limit, offset }, 200, headers);
  }
  const resolveMatch = path.match(/^\/api\/v1\/resolve\/([a-z0-9_-]{3,24})$/i);
  if (request.method === "GET" && resolveMatch) {
    const label = resolveMatch[1].toLowerCase().replace(/\.ultra$/, "");
    const row = await env.DB.prepare("SELECT record_json FROM identities WHERE label = ? COLLATE NOCASE").bind(label).first();
    if (!row) return response({ error: "Identity not found", label }, 404, headers);
    const record = JSON.parse(row.record_json);
    return response({ record, verified: await verifyRecord(record) }, 200, headers);
  }
  if (request.method === "POST" && path === "/api/v1/identities") {
    if (!await rateLimit(request, env, "claim", 10)) return response({ error: "Rate limit exceeded. Try again in one minute." }, 429, headers);
    const parsed = await readJson(request);
    if (!parsed.ok) return response({ error: parsed.error }, parsed.status, headers);
    const body = parsed.value;
    const record = body.record;
    if (!await verifyRecord(record)) return response({ error: "Invalid identity record or signature." }, 400, headers);
    const now = new Date().toISOString();
    try {
      await env.DB.prepare("INSERT INTO identities(label,namespace,record_json,fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?)")
        .bind(record.label, record.namespace, JSON.stringify(record), record.fingerprint, record.createdAt || now, now).run();
      return response({ ok: true, label: record.label, identity: record.label + ".ultra", resolver: "/api/v1/resolve/" + record.label }, 201, headers);
    } catch (error) {
      const message = String(error && error.message || "");
      if (message.includes("UNIQUE") || message.includes("constraint")) return response({ error: "That identity label or key fingerprint has already been claimed." }, 409, headers);
      return response({ error: "Could not save identity." }, 500, headers);
    }
  }

  // Public creator directory (approved profiles only).
  if (request.method === "GET" && path === "/api/v1/creators") {
    const rows = await env.DB.prepare("SELECT id,handle,display_name,bio,website,created_at FROM creators WHERE status='approved' ORDER BY created_at DESC LIMIT 100").all();
    return response({ items: rows.results || [] }, 200, headers);
  }
  // Creator enrollment binds a unique handle to an ECDSA P-256 key.
  if (request.method === "POST" && path === "/api/v1/creators") {
    if (!await rateLimit(request, env, "creator", 5)) return response({ error: "Rate limit exceeded." }, 429, headers);
    const parsed = await readJson(request);
    if (!parsed.ok) return response({ error: parsed.error }, parsed.status, headers);
    const b = parsed.value;
    const handle = typeof b.handle === "string" ? b.handle.trim().toLowerCase() : "";
    const displayName = typeof b.displayName === "string" ? b.displayName.trim() : "";
    const bio = typeof b.bio === "string" ? b.bio.trim() : "";
    const website = typeof b.website === "string" ? b.website.trim() : "";
    const createdAt = typeof b.createdAt === "string" ? b.createdAt : "";
    const publicKey = typeof b.publicKey === "string" ? b.publicKey : "";
    const fingerprint = typeof b.fingerprint === "string" ? b.fingerprint : "";
    const signature = typeof b.signature === "string" ? b.signature : "";
    if (!/^[a-z0-9_]{3,24}$/.test(handle) || RESERVED.has(handle)) return response({ error: "Handle must be 3–24 letters, numbers or underscores and cannot be reserved." }, 400, headers);
    if (!displayName || displayName.length > 60 || bio.length > 240) return response({ error: "Display name is required (max 60); bio max 240 characters." }, 400, headers);
    if (website && !/^https:\/\//i.test(website)) return response({ error: "Website must begin with https://." }, 400, headers);
    if (!freshSignedTimestamp(createdAt)) return response({ error: "Creator proof timestamp is missing, invalid or expired. Try again." }, 400, headers);
    const claim = { handle, displayName, bio, website, createdAt, version: 1, publicKey, fingerprint };
    if (!await verifyDetachedSignature(publicKey, signature, fingerprint, claim)) return response({ error: "Creator key proof is invalid. Profile not created." }, 400, headers);
    const id = crypto.randomUUID(), now = new Date().toISOString();
    try {
      await env.DB.prepare("INSERT INTO creators(id,handle,display_name,bio,website,created_at,status,owner_public_key,owner_fingerprint,ownership_verified_at) VALUES(?,?,?,?,?,?,'pending',?,?,?)")
        .bind(id, handle, displayName, bio, website, now, publicKey, fingerprint, now).run();
      return response({ ok: true, id, handle, status: "pending", ownershipVerified: true, message: "Key-backed creator profile submitted for moderation. Keep this browser's creator key safe." }, 201, headers);
    } catch (e) {
      const message = String(e && e.message || "");
      if (message.includes("UNIQUE") || message.includes("constraint")) return response({ error: "That handle or creator key is already registered." }, 409, headers);
      return response({ error: "Could not submit creator profile." }, 500, headers);
    }
  }
  // Resolve a locally stored key after a lost enrollment response. This returns public metadata only.
  const ownerMatch = path.match(/^\/api\/v1\/creators\/by-key\/([a-f0-9]{64})$/i);
  if (request.method === "GET" && ownerMatch) {
    const row = await env.DB.prepare("SELECT id,handle,status FROM creators WHERE owner_fingerprint=?").bind(ownerMatch[1].toLowerCase()).first();
    if (!row) return response({ error: "No creator account is linked to this key." }, 404, headers);
    return response({ id: row.id, handle: row.handle, status: row.status }, 200, headers);
  }
  // Public feed returns approved posts and approved creator metadata only.
  if (request.method === "GET" && path === "/api/v1/posts") {
    const rows = await env.DB.prepare("SELECT p.id,p.title,p.body,p.category,p.created_at,c.handle,c.display_name FROM posts p JOIN creators c ON c.id=p.creator_id WHERE p.status='approved' AND c.status='approved' ORDER BY p.created_at DESC LIMIT 100").all();
    return response({ items: rows.results || [] }, 200, headers);
  }
  // A post is accepted only when signed by the key bound to its creator account.
  if (request.method === "POST" && path === "/api/v1/posts") {
    if (!await rateLimit(request, env, "post", 8)) return response({ error: "Rate limit exceeded." }, 429, headers);
    const parsed = await readJson(request, 20 * 1024);
    if (!parsed.ok) return response({ error: parsed.error }, parsed.status, headers);
    const b = parsed.value;
    const creatorId = b.creatorId;
    const id = b.id;
    const title = typeof b.title === "string" ? b.title.trim() : "";
    const bodyText = typeof b.body === "string" ? b.body.trim() : "";
    const category = typeof b.category === "string" ? b.category.trim() : "General";
    const createdAt = typeof b.createdAt === "string" ? b.createdAt : "";
    const fingerprint = typeof b.fingerprint === "string" ? b.fingerprint : "";
    const signature = typeof b.signature === "string" ? b.signature : "";
    if (!validUuid(creatorId) || !validUuid(id) || !title || title.length > 100 || !bodyText || bodyText.length > 4000 ||
        !category || category.length > 32 || !freshSignedTimestamp(createdAt)) {
      return response({ error: "Invalid post fields or expired signing timestamp. Check the form and try again." }, 400, headers);
    }
    const creator = await env.DB.prepare("SELECT id,handle,status,owner_public_key,owner_fingerprint,ownership_verified_at FROM creators WHERE id=?").bind(creatorId).first();
    if (!creator || creator.status !== "approved") return response({ error: "Approved creator account not found." }, 404, headers);
    if (!creator.owner_public_key || !creator.owner_fingerprint || !creator.ownership_verified_at) return response({ error: "This legacy creator profile has no verified owner key and cannot publish." }, 403, headers);
    if (fingerprint !== creator.owner_fingerprint) return response({ error: "Post signing key does not belong to this creator account." }, 403, headers);
    const signedPost = { creatorId, id, title, body: bodyText, category, createdAt, version: 1, fingerprint };
    if (!await verifyDetachedSignature(creator.owner_public_key, signature, creator.owner_fingerprint, signedPost)) {
      return response({ error: "Post signature is invalid. Publishing rejected." }, 403, headers);
    }
    try {
      await env.DB.prepare("INSERT INTO posts(id,creator_id,title,body,category,created_at,status,author_fingerprint,author_signature) VALUES(?,?,?,?,?,?,'pending',?,?)")
        .bind(id, creatorId, title, bodyText, category, createdAt, fingerprint, signature).run();
      return response({ ok: true, id, status: "pending", message: "Signed post submitted for review; it is not public until approved." }, 201, headers);
    } catch (e) {
      const message = String(e && e.message || "");
      if (message.includes("UNIQUE") || message.includes("constraint")) return response({ error: "This signed post was already submitted or its ID is invalid." }, 409, headers);
      return response({ error: "Could not save post." }, 500, headers);
    }
  }
  if (request.method === "POST" && path === "/api/v1/reports") {
    if (!await rateLimit(request, env, "report", 5)) return response({ error: "Rate limit exceeded." }, 429, headers);
    const parsed = await readJson(request);
    if (!parsed.ok) return response({ error: parsed.error }, parsed.status, headers);
    const b = parsed.value;
    const label=String(b.label||"").trim().slice(0,80), reason=String(b.reason||"").trim().slice(0,60), details=String(b.details||"").trim().slice(0,1000);
    if (!label || !reason) return response({ error:"Label and reason are required." },400,headers);
    await env.DB.prepare("INSERT INTO abuse_reports(id,label,reason,details,created_at,status) VALUES(?,?,?,?,?,'pending')").bind(crypto.randomUUID(),label,reason,details,new Date().toISOString()).run();
    return response({ok:true,message:"Report received for operator review."},201,headers);
  }
  // Operator-only queue. Never expose ADMIN_TOKEN in a public client.
  if (request.method === "GET" && path === "/api/v1/moderation/queue") {
    const auth = await authorizeAdmin(request, env);
    if (!auth.ok) return response({ error:auth.error }, auth.status, headers);
    const creators=await env.DB.prepare("SELECT id,handle,display_name,bio,website,created_at,ownership_verified_at,owner_fingerprint FROM creators WHERE status='pending' ORDER BY created_at ASC LIMIT 100").all();
    const posts=await env.DB.prepare("SELECT p.id,p.title,p.body,p.category,p.created_at,c.handle FROM posts p JOIN creators c ON c.id=p.creator_id WHERE p.status='pending' ORDER BY p.created_at ASC LIMIT 100").all();
    const reports=await env.DB.prepare("SELECT id,label,reason,details,created_at FROM abuse_reports WHERE status='pending' ORDER BY created_at ASC LIMIT 100").all();
    const events=await env.DB.prepare("SELECT id,target_type,target_id,action,from_status,to_status,actor_type,created_at FROM moderation_events ORDER BY created_at DESC LIMIT 50").all();
    return response({creators:creators.results||[],posts:posts.results||[],reports:reports.results||[],events:events.results||[]},200,headers);
  }


  // Operator-only report resolution.
  const reportModeration = path.match(new RegExp('^/api/v1/moderation/reports/([a-f0-9-]{36})$', 'i'));
  if (request.method === "POST" && reportModeration) {
    const auth = await authorizeAdmin(request, env);
    if (!auth.ok) return response({ error:auth.error }, auth.status, headers);
    const parsed = await readJson(request);
    if (!parsed.ok) return response({ error: parsed.error }, parsed.status, headers);
    const b = parsed.value;
    if (!["reviewed", "dismissed"].includes(b.status)) return response({ error: "Status must be reviewed or dismissed." }, 400, headers);
    const eventId = crypto.randomUUID();
    const now = new Date().toISOString();
    const audit = env.DB.prepare(`
      INSERT INTO moderation_events(id,target_type,target_id,action,from_status,to_status,actor_type,created_at)
      SELECT ?, 'report', id, ?, 'pending', ?, 'shared-admin-token', ?
      FROM abuse_reports WHERE id=? AND status='pending'
    `).bind(eventId, b.status, b.status, now, reportModeration[1]);
    const update = env.DB.prepare("UPDATE abuse_reports SET status=? WHERE id=? AND status='pending'").bind(b.status, reportModeration[1]);
    const results = await env.DB.batch([audit, update]);
    if (!results[1]?.meta || results[1].meta.changes === 0) return response({ error: "Pending report not found." }, 404, headers);
    return response({ ok: true, status: b.status, eventId }, 200, headers);
  }
  // Operator-only moderation. Creator approval requires a verified owner key.
  const moderation = path.match(/^\/api\/v1\/moderation\/(creators|posts)\/([a-f0-9-]{36})$/i);
  if (request.method === "POST" && moderation) {
    const auth = await authorizeAdmin(request, env);
    if (!auth.ok) return response({ error:auth.error }, auth.status, headers);
    const parsed = await readJson(request);
    if (!parsed.ok) return response({ error: parsed.error }, parsed.status, headers);
    const b = parsed.value;
    const status = b.status;
    if (!["approved", "rejected"].includes(status)) return response({ error: "Status must be approved or rejected." }, 400, headers);
    const table = moderation[1] === "creators" ? "creators" : "posts";
    const targetType = table === "creators" ? "creator" : "post";
    const targetId = moderation[2];
    const eventId = crypto.randomUUID();
    const now = new Date().toISOString();
    const ownerGuard = table === "creators" && status === "approved"
      ? " AND owner_public_key IS NOT NULL AND owner_fingerprint IS NOT NULL AND ownership_verified_at IS NOT NULL"
      : "";
    const audit = env.DB.prepare(`
      INSERT INTO moderation_events(id,target_type,target_id,action,from_status,to_status,actor_type,created_at)
      SELECT ?, ?, id, ?, 'pending', ?, 'shared-admin-token', ?
      FROM ${table} WHERE id=? AND status='pending'${ownerGuard}
    `).bind(eventId, targetType, status, status, now, targetId);
    const update = table === "creators" && status === "approved"
      ? env.DB.prepare("UPDATE creators SET status=? WHERE id=? AND status='pending' AND owner_public_key IS NOT NULL AND owner_fingerprint IS NOT NULL AND ownership_verified_at IS NOT NULL").bind(status, targetId)
      : env.DB.prepare("UPDATE " + table + " SET status=? WHERE id=? AND status='pending'").bind(status, targetId);
    const results = await env.DB.batch([audit, update]);
    if (!results[1]?.meta || results[1].meta.changes === 0) return response({ error: table === "creators" && status === "approved" ? "Pending creator not found or verified owner proof is missing." : "Pending submission not found." }, 409, headers);
    return response({ ok: true, status, eventId }, 200, headers);
  }
  return response({ error: "Not found", routes: ["GET /health", "GET /api/v1/registry", "GET /api/v1/resolve/{label}", "POST /api/v1/identities"] }, 404, headers);
}
export default {
  async fetch(request, env) {
    try { return await handle(request, env); }
    catch (error) { return response({ error: "Internal server error" }, 500, cors(request, env)); }
  },
  async scheduled(_controller, env, ctx) {
    if (!env.DB) return;
    const cleanup = pruneExpiredRateLimits(env.DB);
    if (ctx && typeof ctx.waitUntil === "function") ctx.waitUntil(cleanup);
    else await cleanup;
  }
};
