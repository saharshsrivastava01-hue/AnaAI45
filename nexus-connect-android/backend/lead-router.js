import express from "express";

const router = express.Router();
const leads = new Map();
const stages = new Set(["new", "researching", "qualified", "contacted", "replied", "meeting", "won", "lost", "do_not_contact"]);

function requireAppToken(req, res, next) {
  const expected = process.env.APP_ACCESS_TOKEN;
  const supplied = (req.headers.authorization || "").replace(/^Bearer\\s+/i, "");
  if (!expected) return res.status(503).json({ error: "APP_ACCESS_TOKEN is not configured." });
  if (!supplied || supplied !== expected) return res.status(401).json({ error: "Unauthorized." });
  next();
}
router.use(requireAppToken);

router.get("/", (_req, res) => {
  res.json({ leads: [...leads.values()], persistence: "in-memory prototype; records reset when server restarts" });
});

router.post("/", (req, res) => {
  const { businessName, country, city, website, publicContact, source, notes } = req.body || {};
  if (typeof businessName !== "string" || !businessName.trim() || typeof country !== "string" || !country.trim()) {
    return res.status(400).json({ error: "businessName and country are required." });
  }
  const id = crypto.randomUUID();
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
  res.status(201).json({ lead });
});

router.patch("/:id", (req, res) => {
  const lead = leads.get(req.params.id);
  if (!lead) return res.status(404).json({ error: "Lead not found." });
  const { stage, notes, website, publicContact } = req.body || {};
  if (stage !== undefined && !stages.has(stage)) return res.status(400).json({ error: "Invalid stage." });
  if (stage !== undefined) lead.stage = stage;
  for (const key of ["notes", "website", "publicContact"]) {
    if (typeof req.body[key] === "string") lead[key] = req.body[key].trim();
  }
  lead.updatedAt = new Date().toISOString();
  if (lead.stage === "do_not_contact") lead.publicContact = "";
  res.json({ lead });
});

router.delete("/:id", (req, res) => {
  const lead = leads.get(req.params.id);
  if (!lead) return res.status(404).json({ error: "Lead not found." });
  leads.delete(req.params.id);
  res.json({ deleted: true });
});

export default router;
