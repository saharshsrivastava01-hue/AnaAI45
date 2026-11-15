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
    "access-control-allow-headers": "content-type,authorization",
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

  // Public creator directory (approved profiles only).
  if (request.method === "GET" && path === "/api/v1/creators") {
    const rows = await env.DB.prepare("SELECT id,handle,display_name,bio,website,created_at FROM creators WHERE status='approved' ORDER BY created_at DESC LIMIT 100").all();
    return response({ items: rows.results || [] }, 200, headers);
  }
  // New creator profiles enter a moderation queue.
  if (request.method === "POST" && path === "/api/v1/creators") {
    if (!await rateLimit(request, env, "creator", 5)) return response({ error: "Rate limit exceeded." }, 429, headers);
    let b; try { b = await request.json(); } catch { return response({ error: "Invalid JSON." }, 400, headers); }
    const handle = String(b.handle || "").trim().toLowerCase();
    const display = String(b.displayName || "").trim();
    const bio = String(b.bio || "").trim();
    const website = String(b.website || "").trim();
    if (!/^[a-z0-9_]{3,24}$/.test(handle) || RESERVED.has(handle)) return response({ error: "Handle must be 3–24 letters, numbers or underscores and cannot be reserved." }, 400, headers);
    if (!display || display.length > 60 || bio.length > 240) return response({ error: "Display name is required (max 60); bio max 240 characters." }, 400, headers);
    if (website && !/^https:\/\//i.test(website)) return response({ error: "Website must begin with https://." }, 400, headers);
    const id = crypto.randomUUID(), now = new Date().toISOString();
    try {
      await env.DB.prepare("INSERT INTO creators(id,handle,display_name,bio,website,created_at,status) VALUES(?,?,?,?,?,?,'pending')").bind(id,handle,display,bio,website,now).run();
      return response({ ok:true, id, handle, status:"pending", message:"Creator profile submitted for moderation." }, 201, headers);
    } catch (e) { return response({ error: String(e.message||"").includes("UNIQUE") ? "That creator handle is already taken." : "Could not submit creator profile." }, 409, headers); }
  }
  // Public feed returns approved posts and approved creator metadata only.
  if (request.method === "GET" && path === "/api/v1/posts") {
    const rows = await env.DB.prepare("SELECT p.id,p.title,p.body,p.category,p.created_at,c.handle,c.display_name FROM posts p JOIN creators c ON c.id=p.creator_id WHERE p.status='approved' AND c.status='approved' ORDER BY p.created_at DESC LIMIT 100").all();
    return response({ items: rows.results || [] }, 200, headers);
  }
  // Posts are queued, never published immediately.
  if (request.method === "POST" && path === "/api/v1/posts") {
    // Fail closed until creator ownership is cryptographically verified.
    return response({ error: "Publishing is paused until creator ownership verification is implemented; handle-only publishing permits impersonation." }, 503, headers);
    if (!await rateLimit(request, env, "post", 8)) return response({ error: "Rate limit exceeded." }, 429, headers);
    let b; try { b = await request.json(); } catch { return response({ error: "Invalid JSON." }, 400, headers); }
    const handle = String(b.handle || "").trim().toLowerCase();
    const title = String(b.title || "").trim();
    const body = String(b.body || "").trim();
    const category = String(b.category || "General").trim().slice(0,32);
    if (!handle || !title || !body || title.length > 100 || body.length > 4000) return response({ error: "Provide an approved creator handle, title (max 100) and content (max 4000)." }, 400, headers);
    const creator = await env.DB.prepare("SELECT id FROM creators WHERE handle=? COLLATE NOCASE AND status='approved'").bind(handle).first();
    if (!creator) return response({ error: "Approved creator profile not found. Submit a profile and wait for moderation first." }, 404, headers);
    const id=crypto.randomUUID(), now=new Date().toISOString();
    await env.DB.prepare("INSERT INTO posts(id,creator_id,title,body,category,created_at,status) VALUES(?,?,?,?,?,?,'pending')").bind(id,creator.id,title,body,category,now).run();
    return response({ ok:true,id,status:"pending",message:"Post submitted for review; it is not public yet." },201,headers);
  }
  if (request.method === "POST" && path === "/api/v1/reports") {
    if (!await rateLimit(request, env, "report", 5)) return response({ error: "Rate limit exceeded." }, 429, headers);
    let b; try { b=await request.json(); } catch { return response({ error:"Invalid JSON." },400,headers); }
    const label=String(b.label||"").trim().slice(0,80), reason=String(b.reason||"").trim().slice(0,60), details=String(b.details||"").trim().slice(0,1000);
    if (!label || !reason) return response({ error:"Label and reason are required." },400,headers);
    await env.DB.prepare("INSERT INTO abuse_reports(id,label,reason,details,created_at,status) VALUES(?,?,?,?,?,'pending')").bind(crypto.randomUUID(),label,reason,details,new Date().toISOString()).run();
    return response({ok:true,message:"Report received for operator review."},201,headers);
  }
  // Operator-only queue. Never expose ADMIN_TOKEN in a public client.
  if (request.method === "GET" && path === "/api/v1/moderation/queue") {
    const token=(request.headers.get("Authorization")||"").replace(/^Bearer\\s+/i,"");
    if (!env.ADMIN_TOKEN || token !== env.ADMIN_TOKEN) return response({error:"Unauthorized moderation request."},401,headers);
    const creators=await env.DB.prepare("SELECT id,handle,display_name,bio,website,created_at FROM creators WHERE status='pending' ORDER BY created_at ASC LIMIT 100").all();
    const posts=await env.DB.prepare("SELECT p.id,p.title,p.body,p.category,p.created_at,c.handle FROM posts p JOIN creators c ON c.id=p.creator_id WHERE p.status='pending' ORDER BY p.created_at ASC LIMIT 100").all();
    const reports=await env.DB.prepare("SELECT id,label,reason,details,created_at FROM abuse_reports WHERE status='pending' ORDER BY created_at ASC LIMIT 100").all();
    return response({creators:creators.results||[],posts:posts.results||[],reports:reports.results||[]},200,headers);
  }


  // Operator-only report resolution.
  const reportModeration = path.match(new RegExp('^/api/v1/moderation/reports/([a-f0-9-]{36})$', 'i'));
  if (request.method === "POST" && reportModeration) {
    const token = (request.headers.get("Authorization") || "").replace(/^Bearer\\s+/i, "");
    if (!env.ADMIN_TOKEN || token !== env.ADMIN_TOKEN) return response({ error: "Unauthorized moderation request." }, 401, headers);
    let b; try { b = await request.json(); } catch { return response({ error: "Invalid JSON." }, 400, headers); }
    if (!["reviewed", "dismissed"].includes(b.status)) return response({ error: "Status must be reviewed or dismissed." }, 400, headers);
    const result = await env.DB.prepare("UPDATE abuse_reports SET status=? WHERE id=? AND status='pending'").bind(b.status, reportModeration[1]).run();
    if (!result.meta || result.meta.changes === 0) return response({ error: "Pending report not found." }, 404, headers);
    return response({ ok: true, status: b.status }, 200, headers);
  }
  // Operator-only moderation. Configure ADMIN_TOKEN with: wrangler secret put ADMIN_TOKEN
  const moderation = path.match(/^\/api\/v1\/moderation\/(creators|posts)\/([a-f0-9-]{36})$/i);
  if (request.method === "POST" && moderation) {
    const token=(request.headers.get("Authorization")||"").replace(/^Bearer\s+/i,"");
    if (!env.ADMIN_TOKEN || token !== env.ADMIN_TOKEN) return response({error:"Unauthorized moderation request."},401,headers);
    let b; try { b=await request.json(); } catch { return response({error:"Invalid JSON."},400,headers); }
    const status=b.status;
    if (!["approved","rejected"].includes(status)) return response({error:"Status must be approved or rejected."},400,headers);
    const table=moderation[1]==="creators"?"creators":"posts";
    const result=await env.DB.prepare("UPDATE "+table+" SET status=? WHERE id=?").bind(status,moderation[2]).run();
    if (!result.meta || result.meta.changes===0) return response({error:"Submission not found."},404,headers);
    return response({ok:true,status},200,headers);
  }
  return response({ error: "Not found", routes: ["GET /health", "GET /api/v1/registry", "GET /api/v1/resolve/{label}", "POST /api/v1/identities"] }, 404, headers);
}
export default {
  async fetch(request, env) {
    try { return await handle(request, env); }
    catch (error) { return response({ error: "Internal server error" }, 500, cors(request, env)); }
  }
};
