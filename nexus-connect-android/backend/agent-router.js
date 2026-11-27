import express from "express";

const router = express.Router();

function requireAppToken(req, res, next) {
  const expected = process.env.APP_ACCESS_TOKEN;
  if (!expected) return res.status(503).json({ error: "APP_ACCESS_TOKEN is not configured." });
  const supplied = (req.headers.authorization || "").replace(/^Bearer\\s+/i, "");
  if (!supplied || supplied !== expected) return res.status(401).json({ error: "Unauthorized." });
  next();
}

router.use(requireAppToken);

const tasks = new Set([
  "qualify_lead", "draft_proposal", "plan_website", "review_scope",
  "draft_job_application", "create_sample_content",
  "mock_interview_question", "evaluate_interview_answer", "interview_prep_plan"
]);
const systemPrompt = `You are NEXUS Connect AI, an assistant for a beginner freelance WordPress web designer in India.
Be truthful about the operator's experience: B.Tech ECE (AI and Cybernetics), WordPress web-design trainee experience. Do not invent portfolio projects, clients, certifications, skills, prices, delivery dates, or completed work.
Help qualify leads, draft proposals, break website work into verifiable tasks, identify missing information, draft truthful job applications using supplied role details, and create portfolio/sample content clearly labeled as samples.
For interview tasks: act as a supportive professional mock interviewer and coach. Ask exactly one question at a time. Tailor questions to the role and the user's actual experience. Do not invent experience or encourage false claims. When evaluating an answer, give a score from 1-10 with a brief reason, identify one strength, give two specific improvements, and provide a truthful improved sample answer. Distinguish mock interview feedback from a real employer's decision.
Never claim a call was made, a job was won, money was earned, or a website was deployed unless the user supplies evidence.
Do not agree to contracts, prices, deadlines, refunds, or legal terms on the user's behalf. Mark these as requiring human approval.
Return concise JSON with keys: summary, questions, suggested_reply, task_checklist, human_approval_required.`;

router.post("/assist", async (req, res) => {
  const { task, context } = req.body || {};
  if (!tasks.has(task)) return res.status(400).json({ error: "Unsupported task." });
  if (typeof context !== "string" || context.trim().length < 5 || context.length > 8000) {
    return res.status(400).json({ error: "context must contain 5–8000 characters." });
  }
  if (!process.env.OPENAI_API_KEY) return res.status(503).json({ error: "OPENAI_API_KEY is not configured on the server." });

  try {
    const response = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: process.env.OPENAI_MODEL || "gpt-4.1-mini",
        instructions: systemPrompt,
        input: `Task: ${task}\\nInterview / client context:\\n${context}\\nReturn valid JSON only.`,
        max_output_tokens: 1100
      })
    });
    if (!response.ok) {
      return res.status(502).json({ error: "AI provider request failed.", providerStatus: response.status });
    }
    const data = await response.json();
    const output = (data.output || [])
      .flatMap(item => item.content || [])
      .filter(item => item.type === "output_text")
      .map(item => item.text)
      .join("\\n");
    if (!output) return res.status(502).json({ error: "AI provider returned no text output." });
    res.json({ result: output, model: process.env.OPENAI_MODEL || "gpt-4.1-mini" });
  } catch {
    res.status(502).json({ error: "Unable to reach the AI provider." });
  }
});

export default router;
