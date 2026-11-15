const JSON_HEADERS = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" };

function json(data, status, headers) {
  return new Response(JSON.stringify(data), { status, headers: { ...JSON_HEADERS, ...headers } });
}

async function limit(request, env) {
  if (!env.DB) return false;
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const bucket = "ai:" + ip;
  const now = Math.floor(Date.now() / 1000);
  const row = await env.DB.prepare("SELECT hits, window_started FROM rate_limits WHERE bucket = ?").bind(bucket).first();
  if (!row || now - row.window_started >= 60) {
    await env.DB.prepare("INSERT INTO rate_limits(bucket,hits,window_started) VALUES(?,1,?) ON CONFLICT(bucket) DO UPDATE SET hits=1, window_started=excluded.window_started").bind(bucket, now).run();
    return true;
  }
  if (row.hits >= 8) return false;
  await env.DB.prepare("UPDATE rate_limits SET hits=hits+1 WHERE bucket=?").bind(bucket).run();
  return true;
}

export async function handleAI(request, env, headers) {
  if (request.method !== "POST") return json({ error: "Method not allowed." }, 405, { ...headers, allow: "POST, OPTIONS" });
  if (!env.OPENAI_API_KEY || !env.OPENAI_MODEL) {
    return json({ error: "AI is not configured. Set OPENAI_API_KEY and OPENAI_MODEL as Worker secrets/variables." }, 503, headers);
  }
  if (!env.DB) return json({ error: "Database binding DB is not configured." }, 503, headers);
  if (!await limit(request, env)) return json({ error: "AI request limit reached. Try again in one minute." }, 429, headers);

  let body;
  try { body = await request.json(); } catch { return json({ error: "Request body must be JSON." }, 400, headers); }
  const message = typeof body.message === "string" ? body.message.trim() : "";
  if (!message || message.length > 4000) return json({ error: "Enter a message of 1–4000 characters." }, 400, headers);

  let upstream;
  try {
    upstream = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "authorization": "Bearer " + env.OPENAI_API_KEY,
        "content-type": "application/json"
      },
      body: JSON.stringify({
        model: env.OPENAI_MODEL,
        messages: [
          { role: "system", content: "You are ULTRA AI, a helpful assistant. Be accurate, transparent about uncertainty, and never claim actions or capabilities you do not have." },
          { role: "user", content: message }
        ],
        max_tokens: 900,
        temperature: 0.7
      })
    });
  } catch {
    return json({ error: "The AI provider could not be reached. Try again later." }, 502, headers);
  }

  const data = await upstream.json().catch(() => ({}));
  if (!upstream.ok) {
    const status = upstream.status === 429 ? 429 : 502;
    return json({ error: status === 429 ? "AI provider rate limit reached. Try again later." : "AI provider request failed. Check the server-side model configuration." }, status, headers);
  }
  const answer = data.choices?.[0]?.message?.content;
  if (typeof answer !== "string" || !answer.trim()) return json({ error: "The AI provider returned no answer." }, 502, headers);
  return json({ answer: answer.trim(), model: env.OPENAI_MODEL }, 200, headers);
}
