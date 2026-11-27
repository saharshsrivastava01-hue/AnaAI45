import express from "express";
import { randomUUID } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";

const router = express.Router();
const dataFile = resolve(process.env.NEXUS_LEADS_FILE || "./data/leads.json");
const leads = new Map();
const stages = new Set(["new", "researching", "qualified", "contacted", "replied", "meeting", "won", "lost", "do_not_contact"]);

function loadLeads() {
  try {
    const parsed = JSON.parse(readFileSync(dataFile, "utf8"));
    if (Array.isArray(parsed)) for (const lead of parsed) if (lead && typeof lead.id === "string") leads.set(lead.id, lead);
  } catch (error) {
    if (error.code !== "ENOENT") console.error("Lead store read error:", error.message);
  }
}
function saveLeads() {
  mkdirSync(dirname(dataFile), { recursive: true });
  writeFileSync(dataFile, JSON.stringify([...leads.values()], null, 2), { encoding: "utf8", mode: 0o600 });
}
loadLeads();

function requireAppToken(req, res, next) {
  const expected = process.env.APP_ACCESS_TOKEN;
  const supplied = (req.headers.authorization || "").replace(/^Bearer\\s+/i, "");
  if (!expected) return res.status(503).json({ error: "APP_ACCESS_TOKEN is not configured." });
  if (!supplied || supplied !== expected) return res.status(401).json({ error: "Unauthorized." });
  next();
}
router.use(requireAppToken);

router.get("/", (_req, res) => {
  res.json({ leads: [...leads.values()], persistence: "JSON file persistence enabled; configure NEXUS_LEADS_FILE to choose storage path." });
});

router.post("/", (req, res) => {
  const { businessName, country, city, website, publicContact, source, notes } = req.body || {};
  if (typeof businessName !== "string" || !businessName.trim() || typeof country !== "string" || !country.trim()) {
    return res.status(400).json({ error: "businessName and country are required." });
  }
  const id = randomUUID();
  const lead = {
    id, businessName: businessName.trim(), country: country.trim(),
    city: typeof city === "string" ? city.trim() : "",
    website: typeof website === "string" ? website.trim() : "",
    publicContact: typeof publicContact === "string" ? publicContact.trim() : "",
    source: typeof source === "string" ? source.trim() : "",
    notes: typeof notes === "string" ? notes.trim() : "",
    stage: "new", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString()
  };
  leads.set(id, lead);
  try { saveLeads(); } catch (error) { leads.delete(id); return res.status(500).json({ error: "Could not persist lead." }); }
  res.status(201).json({ lead });
});

router.patch("/:id", (req, res) => {
  const lead = leads.get(req.params.id);
  if (!lead) return res.status(404).json({ error: "Lead not found." });
  const { stage } = req.body || {};
  if (stage !== undefined && !stages.has(stage)) return res.status(400).json({ error: "Invalid stage." });
  const prior = { ...lead };
  if (stage !== undefined) lead.stage = stage;
  for (const key of ["notes", "website", "publicContact"]) if (typeof req.body[key] === "string") lead[key] = req.body[key].trim();
  lead.updatedAt = new Date().toISOString();
  if (lead.stage === "do_not_contact") lead.publicContact = "";
  try { saveLeads(); } catch (error) { Object.assign(lead, prior); return res.status(500).json({ error: "Could not persist lead changes." }); }
  res.json({ lead });
});

router.delete("/:id", (req, res) => {
  const lead = leads.get(req.params.id);
  if (!lead) return res.status(404).json({ error: "Lead not found." });
  leads.delete(req.params.id);
  try { saveLeads(); } catch (error) { leads.set(req.params.id, lead); return res.status(500).json({ error: "Could not persist lead deletion." }); }
  res.json({ deleted: true });
});

export default router;
