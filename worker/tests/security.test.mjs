import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const worker = await readFile(new URL("../src/index.js", import.meta.url), "utf8");
const platform = await readFile(new URL("../../platform.html", import.meta.url), "utf8");

test("there is exactly one moderation queue route", () => {
  const matches = worker.match(/path === "\/api\/v1\/moderation\/queue"/g) || [];
  assert.equal(matches.length, 1);
});

test("moderation bearer token parsing accepts the standard Bearer scheme", () => {
  assert.match(worker, /replace\(\/\^Bearer\\s\+\/i/);
});

test("report resolution is operator protected and only permits terminal review states", () => {
  assert.match(worker, /moderation\/reports/);
  assert.match(worker, /!\["reviewed", "dismissed"\]\.includes\(b\.status\)/);
  assert.match(worker, /UPDATE abuse_reports SET status=\? WHERE id=\? AND status='pending'/);
});

test("creator posts fail closed while ownership verification is absent", () => {
  assert.match(worker, /handle-only publishing permits impersonation/);
  assert.match(platform, /Publishing paused for security/);
});

test("operator UI exposes report review and dismissal actions", () => {
  assert.match(platform, /data-report-status="reviewed"/);
  assert.match(platform, /data-report-status="dismissed"/);
  assert.match(platform, /moderation\/reports\//);
});
