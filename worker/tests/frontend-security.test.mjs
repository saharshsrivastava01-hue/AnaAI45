import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

const html = await readFile(new URL("../../platform.html", import.meta.url), "utf8");
const script = await readFile(new URL("../../platform.js", import.meta.url), "utf8");

test("creator page loads one external script under a restrictive script policy", () => {
  assert.match(html, /Content-Security-Policy[^>]*script-src 'self'/);
  assert.match(html, /object-src 'none'/);
  assert.match(html, /base-uri 'none'/);
  assert.match(html, /<script src="platform\.js" defer><\/script>/);
  assert.doesNotMatch(html, /<script>([\s\S]*?)<\/script>/);
});

test("creator frontend JavaScript parses without executing browser APIs", () => {
  assert.doesNotThrow(() => new vm.Script(script, { filename: "platform.js" }));
});

test("server-provided content is rendered without HTML parsing sinks", () => {
  assert.doesNotMatch(script, /\b(?:innerHTML|outerHTML|insertAdjacentHTML|document\.write)\b/);
  assert.match(script, /document\.createElement/);
  assert.match(script, /textContent/);
  assert.match(script, /store\.delete\(value\)/);
  assert.match(script, /Permanently delete the local signing key/);
});

test("moderation queue status is separate from its rendered action container", () => {
  assert.match(html, /id="queueStatus"/);
  assert.match(html, /id="queue"/);
  assert.match(script, /const container = \$\("queue"\)/);
  assert.match(script, /const status = "queueStatus"/);
  assert.doesNotMatch(script, /msg\("queue",/);
  assert.match(script, /button\[data-report-id\]/);
});

test("Worker endpoint validation and fetch settings protect operator requests", () => {
  assert.match(script, /parsed\.protocol !== "https:"/);
  assert.match(script, /credentials: "omit"/);
  assert.match(script, /redirect: "error"/);
  assert.match(script, /referrerPolicy: "no-referrer"/);
  assert.doesNotMatch(script, /localStorage\.setItem\([^\n]*adminToken/i);
});

test("moderation token requires an explicit exact-endpoint page-session trust pin", () => {
  assert.match(html, /id="trustAdminEndpoint"/);
  assert.match(html, /id="adminTrustStatus"/);
  assert.match(html, /independently verified that the exact HTTPS Worker API URL/);
  assert.match(script, /let trustedAdminEndpoint = ""/);
  assert.match(script, /window\.confirm\(/);
  assert.match(script, /trustedAdminEndpoint !== endpoint/);
  const moderate = script.slice(script.indexOf("async function moderate"), script.indexOf("function moderationButton"));
  const queue = script.slice(script.indexOf("async function loadQueue"), script.indexOf('\$("connect")'));
  assert.match(moderate, /requireTrustedAdminEndpoint\(\)/);
  assert.match(queue, /requireTrustedAdminEndpoint\(\)/);
  assert.ok(moderate.indexOf("requireTrustedAdminEndpoint()") < moderate.indexOf('$("adminToken").value'));
  assert.ok(queue.indexOf("requireTrustedAdminEndpoint()") < queue.indexOf('$("adminToken").value'));
  assert.match(script, /trustedAdminEndpoint = ""/);
  assert.match(script, /\$\("adminToken"\)\.value = ""/);
  assert.doesNotMatch(script, /localStorage\.(?:setItem|getItem)\([^\n]*trustedAdminEndpoint/);
  assert.doesNotMatch(script, /sessionStorage\./);
});
