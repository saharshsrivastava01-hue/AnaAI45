import http from "node:http";

const PORT = Number(process.env.PORT || 10000);
const APP_ORIGIN = (process.env.APP_ORIGIN || "https://sparkloop-ai.onrender.com").replace(/\/$/, "");
const MODEL = process.env.OPENAI_MODEL || "gpt-6.2-sol";
const MODEL_CATALOG = [
  { id: "gpt-6.2-astra", name: "GPT-6.2 Astra", inputUsdPerMillion: 8, outputUsdPerMillion: 40, description: "Flagship model for demanding creative strategy" },
  { id: "gpt-6.2-sol", name: "GPT-6.2 Sol", inputUsdPerMillion: 2, outputUsdPerMillion: 10, description: "Balanced model for regular content work" },
  { id: "gpt-6-astra", name: "GPT-6 Astra", inputUsdPerMillion: 10, outputUsdPerMillion: 50, description: "Previous flagship model" },
  { id: "gpt-6.1-sol", name: "GPT-6.1 Sol", inputUsdPerMillion: 2, outputUsdPerMillion: 10, description: "Professional general-work model" },
  { id: "gpt-6.1-terra", name: "GPT-6.1 Terra", inputUsdPerMillion: 1, outputUsdPerMillion: 5, description: "Efficient writing and reasoning" },
  { id: "gpt-6-luna", name: "GPT-6 Luna", inputUsdPerMillion: 0.1, outputUsdPerMillion: 0.5, description: "Lowest-cost high-volume option" }
];
const MODEL_IDS = new Set(MODEL_CATALOG.map((item) => item.id));
const API_KEY = process.env.OPENAI_API_KEY || "";
const WINDOW_MS = 15 * 60 * 1000;
const MAX_REQUESTS = Number(process.env.RATE_LIMIT_PER_WINDOW || 8);
const MAX_DAILY_REQUESTS = Number(process.env.MAX_DAILY_REQUESTS || 6);
const MAX_DAILY_ESTIMATED_COST_USD = Number(process.env.MAX_DAILY_ESTIMATED_COST_USD || 0.50);
let dailyDate = new Date().toISOString().slice(0, 10);
let dailyCount = 0;
let dailyEstimatedCostUsd = 0;
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
        platform VARCHAR(80) NOT NULL,
        model VARCHAR(100) NOT NULL,
        input_tokens BIGINT NOT NULL DEFAULT 0,
        output_tokens BIGINT NOT NULL DEFAULT 0,
        estimated_cost_usd NUMERIC(14,8) NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      )
    `);
    await dbPool.query("ALTER TABLE sparkloop_generation_events ADD COLUMN IF NOT EXISTS input_tokens BIGINT NOT NULL DEFAULT 0");
    await dbPool.query("ALTER TABLE sparkloop_generation_events ADD COLUMN IF NOT EXISTS output_tokens BIGINT NOT NULL DEFAULT 0");
    await dbPool.query("ALTER TABLE sparkloop_generation_events ADD COLUMN IF NOT EXISTS estimated_cost_usd NUMERIC(14,8) NOT NULL DEFAULT 0");
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
      model,
    });
  }

  const limit = rateLimit(clientIp(req));
  res.setHeader("X-RateLimit-Limit", String(MAX_REQUESTS));
  res.setHeader("X-RateLimit-Remaining", String(limit.remaining));
  res.setHeader("X-RateLimit-Reset", String(Math.ceil(limit.resetAt / 1000)));
  if (!limit.allowed) {
    return send(res, 429, { error: "RATE_LIMITED", message: "Too many requests. Please try again after the rate-limit window." });
  }
  const today = new Date().toISOString().slice(0, 10);
  if (today !== dailyDate) { dailyDate = today; dailyCount = 0; dailyEstimatedCostUsd = 0; }
  if (dailyCount >= MAX_DAILY_REQUESTS) {
    return send(res, 429, { error: "DAILY_LIMIT_REACHED", message: "This prototype has reached its daily AI request cap. Try again tomorrow or adjust the server-side limit after reviewing API costs." });
  }
  if (dailyEstimatedCostUsd >= MAX_DAILY_ESTIMATED_COST_USD) {
    return send(res, 429, { error: "DAILY_COST_CAP_REACHED", message: "The estimated daily model-cost cap has been reached. Review your API budget before increasing it." });
  }
  dailyCount += 1;

  const body = await readJson(req);
  const supportedModes = new Set(["content", "campaign", "repurpose", "carousel", "story", "storyboard", "adcopy", "seo", "hooklab"]);
  const mode = supportedModes.has(body.mode) ? body.mode : "content";
  const topic = clean(body.topic, 300);
  const audience = clean(body.audience, 160) || "people interested in this subject";
  const platform = clean(body.platform, 80) || "Instagram Reels";
  const tone = clean(body.tone, 80) || "Clear and useful";
  const proof = clean(body.proof, 300);
  const goal = clean(body.goal, 120) || "Build awareness";
  const brandVoice = clean(body.brandVoice, 1000);
  const constraints = clean(body.constraints, 500);
  const duration = ["15", "30", "60"].includes(String(body.duration)) ? String(body.duration) : "30";
  const selectedModel = clean(body.model, 80);
  const model = MODEL_IDS.has(selectedModel) ? selectedModel : MODEL;

  if (!topic) return send(res, 400, { error: "TOPIC_REQUIRED", message: "Please provide a topic or offer." });

  const common = [
    "Business/topic: " + topic,
    "Audience: " + audience,
    "Primary platform: " + platform,
    "Tone: " + tone,
    "Goal: " + goal,
    brandVoice ? "Brand voice guidance: " + brandVoice : "Use a clear, natural brand voice.",
    proof ? "User-provided proof point (do not embellish): " + proof : "No proof point supplied; do not invent proof.",
    constraints ? "Additional constraints: " + constraints : "",
    "Do not invent facts, customer results, testimonials, endorsements, scarcity, prices, or product capabilities.",
    "Do not promise virality, guaranteed reach, revenue, rankings, or performance.",
    "Create genuinely useful, specific, original work. Keep platform policies, copyright and accessibility in mind."
  ].filter(Boolean);

  const modeInstructions = {
    content: [
      "Create a high-quality social media content draft.",
      "Video duration: " + duration + " seconds.",
      "Return 3 distinct hooks, a timed script, caption, honest CTA, 4-7 relevant hashtags, shot suggestions and accessible alt-text."
    ],
    campaign: [
      "Create a practical 7-day organic content campaign.",
      "Return a seven-day plan with a post concept, draft copy direction, format and measurable KPI per day.",
      "Add a weekly review checklist and simple A/B test suggestions."
    ],
    repurpose: [
      "Repurpose this idea into platform-specific content for Instagram Reels, YouTube Shorts, TikTok, LinkedIn and WhatsApp.",
      "Adapt length, opening hook, CTA and formatting for each platform rather than repeating identical text.",
      "Return separate labelled blocks for each platform and a shared core message."
    ],
    carousel: [
      "Create an 8-slide educational social carousel.",
      "For every slide return: slide number, short headline (max 8 words), concise body copy, visual composition idea and accessible alt-text.",
      "Include a cover hook, a useful sequence, a practical takeaway and a non-deceptive final CTA."
    ],
    story: [
      "Create a 6-frame vertical story sequence.",
      "For each frame return: frame purpose, on-screen text (short), visual direction, interactive sticker suggestion and transition to next frame.",
      "Use a coherent narrative arc and one clear CTA."
    ],
    storyboard: [
      "Create a 30-60 second vertical video storyboard.",
      "Return 8 shots with timecode, camera framing, visual action, voiceover/dialogue, on-screen text, sound suggestion and editing transition.",
      "Keep it feasible for a small creator using a phone camera."
    ],
    adcopy: [
      "Create an advertising creative pack for a legitimate offer.",
      "Return 5 headline alternatives, 3 primary-text versions, 2 CTA alternatives, 3 creative concepts and a claims/compliance checklist.",
      "Clearly mark any claim that needs substantiation; do not invent evidence."
    ],
    seo: [
      "Create an SEO content brief, not fabricated search-volume data.",
      "Return 5 title options, a meta description, search intent, a structured H1/H2 outline, FAQ ideas and internal-link suggestions.",
      "Do not claim exact Google ranking, traffic or keyword-volume estimates."
    ],
    hooklab: [
      "Create 12 distinct opening hooks using different creative angles: problem, curiosity, contrast, checklist, myth correction, story, demonstration and question.",
      "For each hook explain intended audience reaction and one visual opening idea.",
      "Do not assign fake predicted views or engagement scores. Finish with a simple A/B testing protocol."
    ]
  };
  const prompt = [...common, ...modeInstructions[mode]].join("\n");

  const upstream = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      "Authorization": "Bearer " + API_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      instructions: "You are SparkLoop AI, a careful social-content strategist. Produce practical, original, truthful marketing drafts. Never invent evidence or claim guaranteed virality. Refuse requests for spam, deceptive impersonation, fake engagement, or fabricated testimonials. Output clean headings and usable copy.",
      input: prompt,
      max_output_tokens: ["campaign", "repurpose", "carousel", "storyboard"].includes(mode) ? 2800 : 2200,
      store: false,
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

  const usage = responseData.usage || {};
  const inputTokens = Number(usage.input_tokens || 0);
  const outputTokens = Number(usage.output_tokens || 0);
  const modelInfo = MODEL_CATALOG.find((item) => item.id === model);
  const estimatedCostUsd = modelInfo
    ? (inputTokens * modelInfo.inputUsdPerMillion + outputTokens * modelInfo.outputUsdPerMillion) / 1_000_000
    : 0;
  dailyEstimatedCostUsd += estimatedCostUsd;

  if (dbPool) {
    try {
      await dbPool.query(
        "INSERT INTO sparkloop_generation_events(platform, model, input_tokens, output_tokens, estimated_cost_usd) VALUES ($1, $2, $3, $4, $5)",
        [platform, model, inputTokens, outputTokens, estimatedCostUsd]
      );
    } catch (error) {
      console.error("Could not record usage metric:", error.message);
    }
  }
  return send(res, 200, {
    text, model, mode, database: dbStatus,
    usage: { inputTokens, outputTokens, estimatedCostUsd: Number(estimatedCostUsd.toFixed(8)), currency: "USD" }
  });
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
      models: MODEL_CATALOG,
      supportedModes: ["content", "campaign", "repurpose", "carousel", "story", "storyboard", "adcopy", "seo", "hooklab"],
      limits: { maxRequestsPer15Minutes: MAX_REQUESTS, maxRequestsPerDay: MAX_DAILY_REQUESTS, estimatedDailyCostCapUsd: MAX_DAILY_ESTIMATED_COST_USD },
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
