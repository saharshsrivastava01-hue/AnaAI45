import express from "express";
import { validatePlan } from "./workflow-engine.js";

const router = express.Router();
function auth(req,res,next) {
  const expected = process.env.APP_ACCESS_TOKEN;
  const supplied = (req.headers.authorization || "").replace(/^Bearer\\s+/i, "");
  if (!expected) return res.status(503).json({ error: "APP_ACCESS_TOKEN is not configured." });
  if (!supplied || supplied !== expected) return res.status(401).json({ error: "Unauthorized." });
  next();
}
router.use(auth);

// Deterministic planning endpoint: accepts a proposed task graph and validates it.
router.post("/validate", (req,res) => {
  try { return res.json(validatePlan(req.body)); }
  catch (error) { return res.status(400).json({ error: error.message || "Invalid workflow." }); }
});
export default router;
