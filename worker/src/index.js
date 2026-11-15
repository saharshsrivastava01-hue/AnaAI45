const JSON_HEADERS = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" };
const RESERVED = new Set(["admin","api","www","root","support","security","ultra","nexora","help","billing","login","signup","settings","mail","ftp","ns1","ns2"]);
const enc = new TextEncoder();

function response(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), { status, headers: { ...JSON_HEADERS, ...headers } });
}
function cors(request, env) {
  const origin = request.headers.get("Origin") || "";
  const allowed = env.ALLOWED_ORIGIN || "";
  const permitted = origin === allowed || origin === "http://localhost:8788" || origin === "http://127.0.0.1:8788";
  return {
    "access-control-allow-origin": permitted ? origin : allowed,
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "content-type",
    "vary": "Origin"
  };
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
  const bucket = bucketName + ":" + ip;
  const now = Math.floor(Date.now() / 1000);
  const row = await env.DB.prepare("SELECT hits, window_started FROM rate_limits WHERE bucket = ?").bind(bucket).first();
  if (!row || now - row.window_started >= 60) {
    await env.DB.prepare("INSERT INTO rate_limits(bucket,hits,window_started) VALUES(?,1,?) ON CONFLICT(bucket) DO UPDATE SET hits=1, window_started=excluded.window_started").bind(bucket, now).run();
    return true;
  }
  if (row.hits >= max) return false;
  await env.DB.prepare("UPDATE rate_limits SET hits=hits+1 WHERE bucket=?").bind(bucket).run();
  return true;
}
async function handle(request, env) {
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(request, env) });
  const headers = cors(request, env);
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
    let body;
    try { body = await request.json(); } catch { return response({ error: "Request body must be JSON." }, 400, headers); }
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
  return response({ error: "Not found", routes: ["GET /health", "GET /api/v1/registry", "GET /api/v1/resolve/{label}", "POST /api/v1/identities"] }, 404, headers);
}
export default {
  async fetch(request, env) {
    try { return await handle(request, env); }
    catch (error) { return response({ error: "Internal server error" }, 500, cors(request, env)); }
  }
};
