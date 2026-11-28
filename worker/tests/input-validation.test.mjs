import test from "node:test";
import assert from "node:assert/strict";
import { isSafeHttpsUrl } from "../src/http.js";

test("absolute HTTPS links with a hostname are accepted", () => {
  assert.equal(isSafeHttpsUrl("https://example.com"), true);
  assert.equal(isSafeHttpsUrl("https://sub.example.com/path?q=1#section"), true);
});

test("unsafe schemes, malformed URLs and embedded credentials are rejected", () => {
  for (const value of [
    "http://example.com",
    "javascript:alert(1)",
    "//example.com/path",
    "https://",
    "https://user:password@example.com/",
    " https://example.com",
    "https://example.com\n.evil"
  ]) assert.equal(isSafeHttpsUrl(value), false, JSON.stringify(value));
});

test("HTTPS URLs longer than 2048 characters are rejected", () => {
  assert.equal(isSafeHttpsUrl("https://example.com/" + "a".repeat(2048)), false);
});

test("non-string and empty values are rejected", () => {
  assert.equal(isSafeHttpsUrl(""), false);
  assert.equal(isSafeHttpsUrl(null), false);
  assert.equal(isSafeHttpsUrl({ toString:() => "https://example.com" }), false);
});
