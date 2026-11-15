import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const worker = await readFile(new URL("../src/index.js", import.meta.url), "utf8");
const ai = await readFile(new URL("../src/ai.js", import.meta.url), "utf8");
const page = await readFile(new URL("../../ai.html", import.meta.url), "utf8");

test("AI endpoint is routed through the Worker", () => {
  assert.match(worker, /path === "\/api\/v1\/ai\/chat"/);
  assert.match(worker, /handleAI\(request, env, headers\)/);
});

test("AI provider key is server-side and never embedded in the page", () => {
  assert.match(ai, /env\.OPENAI_API_KEY/);
  assert.doesNotMatch(page, /sk-[A-Za-z0-9]{20,}/);
  assert.match(page, /API key is never placed in this page/);
});

test("AI requests are bounded and rate limited", () => {
  assert.match(ai, /message\.length > 4000/);
  assert.match(ai, /row\.hits >= 8/);
  assert.match(ai, /max_tokens: 900/);
});

test("AI model is explicitly configured by the operator", () => {
  assert.match(ai, /env\.OPENAI_MODEL/);
  assert.match(ai, /AI is not configured/);
});
