import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";

const EXPECTED = {
  "x-content-type-options": "nosniff",
  "x-frame-options": "DENY",
  "referrer-policy": "no-referrer",
  "permissions-policy": "camera=(), microphone=(), geolocation=()",
  "content-security-policy": "default-src 'none'; base-uri 'none'; frame-ancestors 'none'",
  "cache-control": "no-store"
};

async function call(path, { method = "GET", origin = "https://ultra.example", body } = {}) {
  return worker.fetch(new Request("https://worker.test" + path, {
    method,
    headers: {
      ...(origin ? { Origin: origin } : {}),
      ...(body ? { "content-type": "application/json" } : {})
    },
    ...(body ? { body: JSON.stringify(body) } : {})
  }), {
    DB: {},
    ALLOWED_ORIGIN: "https://ultra.example"
  });
}

function assertSecurityHeaders(response) {
  for (const [name, value] of Object.entries(EXPECTED)) {
    assert.equal(response.headers.get(name), value, name + " must be present");
  }
}

test("health and not-found API responses include baseline security headers", async () => {
  const health = await call("/health");
  assert.equal(health.status, 200);
  assertSecurityHeaders(health);

  const missing = await call("/missing");
  assert.equal(missing.status, 404);
  assertSecurityHeaders(missing);
});

test("preflight responses include security headers without granting an untrusted origin", async () => {
  const response = await call("/api/v1/posts", {
    method: "OPTIONS",
    origin: "https://attacker.example"
  });
  assert.equal(response.status, 204);
  assertSecurityHeaders(response);
  assert.equal(response.headers.get("access-control-allow-origin"), null);
});

test("AI configuration errors include the same baseline security headers", async () => {
  const response = await call("/api/v1/ai/chat", {
    method: "POST",
    body: { message: "hello" }
  });
  assert.equal(response.status, 503);
  assertSecurityHeaders(response);
});
