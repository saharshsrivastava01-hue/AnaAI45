import express from "express";
import twilio from "twilio";

const app = express();
app.use(express.json({ limit: "16kb" }));

const required = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER", "PUBLIC_BASE_URL"];
const configured = required.every((key) => Boolean(process.env[key]));
const allowed = new Set((process.env.OUTBOUND_ALLOWLIST || "").split(",").map(x => x.trim()).filter(Boolean));

app.get("/health", (_req, res) => {
  res.json({ ok: true, service: "nexus-connect-ai", telephonyConfigured: configured });
});

app.post("/calls/create", async (req, res) => {
  if (!configured) return res.status(503).json({ error: "Telephony is not configured. Add provider credentials to backend environment secrets." });
  const { to, userConfirmed } = req.body ?? {};
  if (userConfirmed !== true) return res.status(400).json({ error: "Explicit user confirmation is required." });
  if (typeof to !== "string" || !/^\+[1-9]\d{7,14}$/.test(to)) return res.status(400).json({ error: "Use an E.164 phone number, e.g. +14155550123." });
  if (!allowed.has(to)) return res.status(403).json({ error: "Number is not in the configured outbound allowlist." });

  try {
    const client = twilio(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN);
    const call = await client.calls.create({
      to,
      from: process.env.TWILIO_PHONE_NUMBER,
      url: new URL("/voice/intro", process.env.PUBLIC_BASE_URL).toString(),
      method: "POST"
    });
    res.status(202).json({ accepted: true, callSid: call.sid, status: call.status });
  } catch (error) {
    res.status(502).json({ error: "Telephony provider rejected the call request." });
  }
});

app.post("/voice/intro", (_req, res) => {
  const twiml = new twilio.twiml.VoiceResponse();
  twiml.say({ voice: "alice" }, "Hello. This is an AI assistant calling on behalf of Saharsh. I am an automated assistant. Is now a convenient time for a brief conversation about website services?");
  twiml.pause({ length: 1 });
  twiml.say("This starter is not yet connected to a live conversational AI. Please contact Saharsh directly if you would like to continue.");
  twiml.hangup();
  res.type("text/xml").send(twiml.toString());
});

const port = Number(process.env.PORT || 8080);
app.listen(port, () => console.log(`NEXUS backend listening on ${port}`));
