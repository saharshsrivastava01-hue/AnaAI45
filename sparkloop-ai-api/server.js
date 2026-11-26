import http from "node:http";
import { timingSafeEqual } from "node:crypto";

const PORT = Number(process.env.PORT || 10000);
const APP_ORIGIN = (process.env.APP_ORIGIN || "https://sparkloop-ai.onrender.com").replace(/\/$/, "");
const MODEL = process.env.OPENAI_MODEL || "gpt-6.2-sol";
const API_KEY = process.env.OPENAI_API_KEY || "";
const WINDOW_MS = 15 * 60 * 1000;
const MAX_REQUESTS = Number(process.env.RATE_LIMIT_PER_WINDOW || 8);
const MAX_BODY = 12_000;
const rates = new Map();
let dbPool = null;
let dbStatus = "not_configured";

function send(res, status, body) {
  const data = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
  });
  res.end(data);
}

function cors(req, res) {
  const origin = req.headers.origin;
  if (origin && origin !== APP_ORIGIN) return false;
  res.setHeader("Access-Control-Allow-Origin", APP_ORIGIN);
  res.setHeader("Vary", "Origin");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Access-Control-Max-Age", "600");
  return true;
}

function clientIp(req) {
  return String(req.headers["x-forwarded-for"] || req.socket.remoteAddress || "unknown").split(",")[0].trim();
}

function rateLimit(ip) {
  const now = Date.now();
  let entry = rates.get(ip);
  if (!entry || now >= entry.resetAt) entry = { count: 0, resetAt: now + WINDOW_MS };
  entry.count += 1;
  rates.set(ip, entry);
  if (rates.size > 5000) {
    for (const [key, value] of rates) if (now >= value.resetAt) rates.delete(key);
  }
  return { allowed: entry.count <= MAX_REQUESTS, remaining: Math.max(0, MAX_REQUESTS - entry.count), resetAt: entry.resetAt };
}

async function readJson(req) {
  let raw = "";
  for await (const chunk of req) {
    raw += chunk.toString("utf8");
    if (raw.length > MAX_BODY) throw Object.assign(new Error("Request too large"), { status: 413 });
  }
  try { return JSON.parse(raw || "{}"); }
  catch { throw Object.assign(new Error("Invalid JSON body"), { status: 400 }); }
}

function clean(value, max = 300) {
  return typeof value === "string" ? value.trim().slice(0, max) : "";
}

function extractText(data) {
  if (typeof data.output_text === "string" && data.output_text.trim()) return data.output_text.trim();
  const texts = [];
  for (const item of data.output || []) {
    for (const part of item.content || []) {
      if (part.type === "output_text" && part.text) texts.push(part.text);
    }
  }
  return texts.join("\n").trim();
}

async function initDatabase() {
  if (!process.env.DATABASE_URL) return;
  try {
    const { Pool } = await import("pg");
    dbPool = new Pool({
      connectionString: process.env.DATABASE_URL,
      ssl: process.env.PGSSL === "disable" ? false : { rejectUnauthorized: false },
      max: 3,
      idleTimeoutMillis: 10000,
      connectionTimeoutMillis: 5000,
    });
    await dbPool.query(`
      CREATE TABLE IF NOT EXISTS sparkloop_generation_events (
        id BIGSERIAL PRIMARY KEY,
        platform VARCHAR(40) NOT NULL,
        model VARCHAR(100) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      )
    `);
    dbStatus = "connected";
  } catch (error) {
    dbStatus = "error";
    console.error("Database connection failed:", error.message);
  }
}

async function handleGenerate(req, res) {
  if (!API_KEY) {
    return send(res, 503, {
      error: "AI_NOT_CONFIGURED",
      message: "The AI backend is deployed, but OPENAI_API_KEY has not been added as a private server environment variable yet.",
      model: MODEL,
    });
  }

  const limit = rateLimit(clientIp(req));
  res.setHeader("X-RateLimit-Limit", String(MAX_REQUESTS));
  res.setHeader("X-RateLimit-Remaining", String(limit.remaining));
  res.setHeader("X-RateLimit-Reset", String(Math.ceil(limit.resetAt / 1000)));
  if (!limit.allowed) {
    return send(res, 429, { error: "RATE_LIMITED", message: "Too many requests. Please try again after the rate-limit window." });
  }

  const body = await readJson(req);
  const mode = body.mode === "campaign" ? "campaign" : "content";
  const topic = clean(body.topic, 300);
  const audience = clean(body.audience, 160) || "people interested in this subject";
  const platform = clean(body.platform, 40) || "Instagram Reels";
  const tone = clean(body.tone, 60) || "Clear and useful";
  const proof = clean(body.proof, 300);
  const goal = clean(body.goal, 100) || "Build awareness";
  const duration = ["15", "30", "60"].includes(String(body.duration)) ? String(body.duration) : "30";

  if (!topic) return send(res, 400, { error: "TOPIC_REQUIRED", message: "Please provide a topic or offer." });

  const prompt = mode === "campaign"
    ? [
        "Create a practical 7-day organic content campaign.",
        "Objective: " + goal,
        "Offer: " + topic,
        "Audience: " + audience,
        "Platform: " + platform,
        "Tone: " + tone,
        "Return a seven-day plan with one post idea, short copy direction, and a measurable KPI per day.",
        "Never fabricate testimonials, customer results, scarcity, endorsements, or performance metrics.",
        "Do not promise virality, guaranteed reach, revenue, or rankings.",
      ].join("\n")
    : [
        "Create a high-quality social media content draft for a real creator or small business.",
        "Topic / offer: " + topic,
        "Target audience: " + audience,
        "Platform: " + platform,
        "Tone: " + tone,
        "Video duration: " + duration + " seconds",
        "Campaign goal: " + goal,
        proof ? "User-supplied real proof point (do not embellish): " + proof : "No proof point supplied; do not invent one.",
        "Return: 3 distinct hooks; a timed short-form script; caption; clear non-deceptive CTA; 4-7 relevant hashtags; visual shot suggestions; an accessibility-friendly alt-text idea.",
        "Keep language specific and natural. Do not invent facts, testimonials, outcomes, product features, or customer claims.",
        "Do not promise virality or guaranteed performance. Make it useful, original, and platform-appropriate.",
      ].join("\n");

  const upstream = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      "Authorization": "Bearer " + API_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: MODEL,
      instructions: "You are SparkLoop AI, a careful social-content strategist. Produce practical, original, truthful marketing drafts. Never invent evidence or claim guaranteed virality. Refuse requests for spam, deceptive impersonation, fake engagement, or fabricated testimonials. Output clean headings and usable copy.",
      input: prompt,
      max_output_tokens: 1800,
    }),
    signal: AbortSignal.timeout(60000),
  });

  const responseData = await upstream.json().catch(() => ({}));
  if (!upstream.ok) {
    const message = clean(responseData?.error?.message, 500) || "The model request failed.";
    console.error("OpenAI API error:", upstream.status, message);
    return send(res, upstream.status === 429 ? 429 : 502, {
      error: "MODEL_REQUEST_FAILED",
      message: upstream.status === 401 ? "The server API key was rejected. Replace it in the hosting environment settings." :
        upstream.status === 429 ? "The API quota or rate limit was reached. Check API billing and limits." : "The AI provider could not complete this request.",
    });
  }

  const text = extractText(responseData);
  if (!text) return send(res, 502, { error: "EMPTY_MODEL_RESPONSE", message: "The model returned no text. Please retry." });

  if (dbPool) {
    try {
      await dbPool.query("INSERT INTO sparkloop_generation_events(platform, model) VALUES ($1, $2)", [platform, MODEL]);
    } catch (error) {
      console.error("Could not record usage metric:", error.message);
    }
  }
  return send(res, 200, { text, model: MODEL, mode, database: dbStatus });
}

const server = http.createServer(async (req, res) => {
  if (!cors(req, res)) return send(res, 403, { error: "ORIGIN_NOT_ALLOWED" });
  if (req.method === "OPTIONS") { res.writeHead(204); return res.end(); }
  const url = new URL(req.url, "http://localhost");
  if (req.method === "GET" && url.pathname === "/health") {
    return send(res, 200, {
      status: "ok",
      service: "sparkloop-ai-api",
      model: MODEL,
      aiConfigured: Boolean(API_KEY),
      database: dbStatus,
      timestamp: new Date().toISOString(),
    });
  }
  if (req.method === "POST" && url.pathname === "/api/generate") {
    try { return await handleGenerate(req, res); }
    catch (error) {
      console.error("Request failed:", error.message);
      return send(res, error.status || 500, { error: "REQUEST_FAILED", message: error.status ? error.message : "The server could not process this request." });
    }
  }
  return send(res, 404, { error: "NOT_FOUND" });
});

await initDatabase();
server.listen(PORT, "0.0.0.0", () => {
  console.log(`SparkLoop API listening on ${PORT}; model=${MODEL}; aiConfigured=${Boolean(API_KEY)}; database=${dbStatus}`);
});
