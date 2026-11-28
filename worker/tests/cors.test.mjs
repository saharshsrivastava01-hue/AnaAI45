import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";

async function request(origin, envOverrides = {}, method = "GET") {
  const headers = origin ? { Origin: origin } : {};
  return worker.fetch(new Request("https://worker.test/health", { method, headers }), {
    DB: {},
    ALLOWED_ORIGIN: "https://saharshsrivastava01-hue.github.io",
    ...envOverrides
  });
}

test("CORS permits only the exact configured production origin", async () => {
  const allowed = "https://saharshsrivastava01-hue.github.io";
  const response = await request(allowed);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("access-control-allow-origin"), allowed);
  assert.equal(response.headers.get("vary"), "Origin");
});

test("CORS does not reflect or fall back to the production origin for an untrusted site", async () => {
  const response = await request("https://attacker.example");
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("access-control-allow-origin"), null);
  assert.equal(response.headers.get("vary"), "Origin");
});

test("localhost is not implicitly trusted in production", async () => {
  for (const origin of ["http://localhost:8788", "http://127.0.0.1:8788"]) {
    const response = await request(origin);
    assert.equal(response.headers.get("access-control-allow-origin"), null);
  }
});

test("local development origins can be explicitly allowlisted", async () => {
  const origin = "http://localhost:8788";
  const response = await request(origin, {
    ALLOWED_DEV_ORIGINS: "http://localhost:8788, http://127.0.0.1:8788"
  });
  assert.equal(response.headers.get("access-control-allow-origin"), origin);
});

test("untrusted preflight requests receive no allow-origin permission", async () => {
  const response = await request("https://attacker.example", {}, "OPTIONS");
  assert.equal(response.status, 204);
  assert.equal(response.headers.get("access-control-allow-origin"), null);
  assert.equal(response.headers.get("access-control-allow-methods"), "GET,POST,OPTIONS");
});
