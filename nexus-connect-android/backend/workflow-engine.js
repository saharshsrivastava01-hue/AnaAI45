// NEXUS 10G deterministic workflow planner.
// AI proposes work; this engine validates dependencies and computes a safe execution order.
export function validatePlan(input) {
  if (!input || !Array.isArray(input.tasks) || input.tasks.length < 1 || input.tasks.length > 40) {
    throw new Error("Plan must contain between 1 and 40 tasks.");
  }
  const ids = new Set();
  for (const task of input.tasks) {
    if (!task || typeof task.id !== "string" || !/^[a-zA-Z0-9_-]{1,40}$/.test(task.id)) throw new Error("Every task needs a valid id.");
    if (ids.has(task.id)) throw new Error("Task ids must be unique.");
    ids.add(task.id);
    if (typeof task.title !== "string" || !task.title.trim() || task.title.length > 160) throw new Error("Every task needs a short title.");
    if (!Array.isArray(task.dependsOn)) task.dependsOn = [];
    if (task.dependsOn.length > 20) throw new Error("Too many dependencies.");
    if (!["low","medium","high"].includes(task.risk || "medium")) task.risk = "medium";
    task.requiresApproval = task.requiresApproval !== false;
    task.status = "proposed";
  }
  for (const task of input.tasks) for (const dep of task.dependsOn) {
    if (!ids.has(dep)) throw new Error(`Unknown dependency ${dep} in task ${task.id}.`);
    if (dep === task.id) throw new Error("A task cannot depend on itself.");
  }
  // Kahn topological sort; cycles are rejected rather than silently executed.
  const indegree = new Map(input.tasks.map(t => [t.id, t.dependsOn.length]));
  const next = new Map(input.tasks.map(t => [t.id, []]));
  for (const task of input.tasks) for (const dep of task.dependsOn) next.get(dep).push(task.id);
  const queue = input.tasks.filter(t => indegree.get(t.id) === 0).map(t => t.id);
  const order = [];
  while (queue.length) {
    const id = queue.shift();
    order.push(id);
    for (const child of next.get(id)) {
      indegree.set(child, indegree.get(child) - 1);
      if (indegree.get(child) === 0) queue.push(child);
    }
  }
  if (order.length !== input.tasks.length) throw new Error("Dependency cycle detected; revise the plan.");
  const byId = new Map(input.tasks.map(t => [t.id, t]));
  const ordered = order.map((id, index) => ({ ...byId.get(id), sequence: index + 1 }));
  return {
    tasks: ordered,
    summary: { taskCount: ordered.length, approvalCount: ordered.filter(t => t.requiresApproval).length,
      highRiskCount: ordered.filter(t => t.risk === "high").length },
    executionPolicy: "plan_only",
    notice: "No external action is executed. Human approval is required before communication, spending, publishing, or commitments."
  };
}
