// Shared bounded HTTP parsing and atomic D1 rate limiting for the Worker.
export async function readJson(request, maxBytes = 8192) {
  const declared = request.headers.get("content-length");
  if (declared !== null) {
    const size = Number(declared);
    if (!Number.isSafeInteger(size) || size < 0) {
      return { ok: false, status: 400, error: "Invalid Content-Length." };
    }
    if (size > maxBytes) {
      return { ok: false, status: 413, error: "Request body is too large." };
    }
  }

  if (!request.body) return { ok: false, status: 400, error: "Request body must be JSON." };
  const reader = request.body.getReader();
  const chunks = [];
  let total = 0;
  try {
    while (true) {
      const part = await reader.read();
      if (part.done) break;
      total += part.value.byteLength;
      if (total > maxBytes) {
        await reader.cancel();
        return { ok: false, status: 413, error: "Request body is too large." };
      }
      chunks.push(part.value);
    }
  } catch {
    return { ok: false, status: 400, error: "Could not read request body." };
  }

  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  try {
    const value = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return { ok: false, status: 400, error: "JSON body must be an object." };
    }
    return { ok: true, value };
  } catch {
    return { ok: false, status: 400, error: "Request body must be valid UTF-8 JSON." };
  }
}

// A single SQLite UPSERT makes increment/reset atomic across concurrent requests.
// Returns true only for requests within the configured window limit.
export async function consumeRateLimit(db, bucket, max, now = Math.floor(Date.now() / 1000)) {
  const row = await db.prepare(`
    INSERT INTO rate_limits(bucket,hits,window_started) VALUES(?,1,?)
    ON CONFLICT(bucket) DO UPDATE SET
      hits = CASE
        WHEN excluded.window_started - rate_limits.window_started >= 60 THEN 1
        ELSE rate_limits.hits + 1
      END,
      window_started = CASE
        WHEN excluded.window_started - rate_limits.window_started >= 60 THEN excluded.window_started
        ELSE rate_limits.window_started
      END
    RETURNING hits
  `).bind(bucket, now).first();
  return !!row && row.hits <= max;
}
