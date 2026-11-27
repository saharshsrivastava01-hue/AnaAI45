import test from "node:test";
import assert from "node:assert/strict";
import { validatePlan } from "../workflow-engine.js";

test("orders tasks by dependency and marks plan-only policy", () => {
  const result = validatePlan({ tasks: [
    { id: "deliver", title: "Deliver after approval", dependsOn: ["approve"], risk: "high" },
    { id: "research", title: "Research", dependsOn: [], risk: "low" },
    { id: "approve", title: "User approval", dependsOn: ["research"], risk: "high" }
  ] });
  assert.deepEqual(result.tasks.map(t => t.id), ["research", "approve", "deliver"]);
  assert.equal(result.executionPolicy, "plan_only");
  assert.equal(result.summary.approvalCount, 3);
  assert.equal(result.summary.highRiskCount, 2);
});

test("rejects duplicate task ids", () => {
  assert.throws(() => validatePlan({ tasks: [
    { id: "x", title: "One", dependsOn: [] },
    { id: "x", title: "Two", dependsOn: [] }
  ] }), /unique/);
});

test("rejects unknown dependency", () => {
  assert.throws(() => validatePlan({ tasks: [
    { id: "a", title: "Task", dependsOn: ["missing"] }
  ] }), /Unknown dependency/);
});

test("rejects self-dependency and cycles", () => {
  assert.throws(() => validatePlan({ tasks: [
    { id: "a", title: "Self", dependsOn: ["a"] }
  ] }), /cannot depend/);
  assert.throws(() => validatePlan({ tasks: [
    { id: "a", title: "A", dependsOn: ["b"] },
    { id: "b", title: "B", dependsOn: ["a"] }
  ] }), /cycle/);
});

test("rejects empty and oversized plans", () => {
  assert.throws(() => validatePlan({ tasks: [] }), /between 1 and 40/);
  assert.throws(() => validatePlan({ tasks: Array.from({ length: 41 }, (_, i) => ({
    id: "t" + i, title: "Task " + i, dependsOn: []
  })) }), /between 1 and 40/);
});
