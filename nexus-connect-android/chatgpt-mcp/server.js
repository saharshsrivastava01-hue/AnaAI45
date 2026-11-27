import express from "express";
import { randomUUID } from "node:crypto";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";

const backend = (process.env.NEXUS_BACKEND_URL || "http://127.0.0.1:8080").replace(/\\/$/, "");
const token = process.env.NEXUS_APP_TOKEN || "";
const port = Number(process.env.PORT || 8090);
const app = express();
app.use(express.json({ limit: "1mb" }));
function backendFetch(path, options={}) {
  if (!token) throw new Error("NEXUS_APP_TOKEN is not configured.");
  return fetch(backend + path, { ...options, headers: { "Content-Type": "application/json", Authorization: "Bearer " + token, ...(options.headers||{}) } });
}
function toolResult(value) { return ({ content: [{ type: "text", text: typeof value === "string" ? value : JSON.stringify(value, null, 2) }] }); }
function makeServer() {
  const mcp = new McpServer({ name: "NEXUS Connect AI", version: "0.1.0" });
  mcp.tool("nexus_health", "Check NEXUS backend health and telephony configuration status (does not place calls).", {}, async () => {
    const r=await fetch(backend+"/health"); return toolResult(await r.json());
  });
  mcp.tool("nexus_ai_draft", "Generate a reviewable AI draft for lead qualification, proposals, website plans, scope review, job applications, or portfolio samples. Does not send or submit.", {
    task: z.enum(["qualify_lead","draft_proposal","plan_website","review_scope","draft_job_application","create_sample_content"]),
    context: z.string().min(1).max(12000)
  }, async ({task,context}) => { const r=await backendFetch("/agent/assist",{method:"POST",body:JSON.stringify({task,context})}); return toolResult({status:r.status,body:await r.json()}); });
  mcp.tool("nexus_list_leads", "List leads saved in the NEXUS backend.", {}, async () => {const r=await backendFetch("/leads");return toolResult(await r.json())});
  mcp.tool("nexus_save_lead", "Save a prospect to the lead tracker. This does not contact them.", {
    businessName:z.string().min(1).max(200), country:z.string().min(1).max(100), city:z.string().optional(), website:z.string().optional(), publicContact:z.string().optional(), source:z.string().optional(), notes:z.string().optional()
  }, async (args)=>{const r=await backendFetch("/leads",{method:"POST",body:JSON.stringify(args)});return toolResult({status:r.status,body:await r.json()})});
  mcp.tool("nexus_list_applications", "List saved job opportunities and their application status.", {}, async()=>{const r=await backendFetch("/applications");return toolResult(await r.json())});
  mcp.tool("nexus_save_application", "Save a job opportunity for tracking; does not submit a job application.", {
    company:z.string().min(1).max(200), role:z.string().min(1).max(200), url:z.string().optional(), notes:z.string().optional(), status:z.enum(["saved","researching","draft_ready","approved_to_apply","applied","interview","offer","rejected","withdrawn"]).optional()
  },async(args)=>{const r=await backendFetch("/applications",{method:"POST",body:JSON.stringify(args)});return toolResult({status:r.status,body:await r.json()})});
  mcp.tool("nexus_update_application", "Update the status or notes of a tracked application. Does not apply or email employers.", {
    id:z.string().min(1), status:z.enum(["saved","researching","draft_ready","approved_to_apply","applied","interview","offer","rejected","withdrawn"]).optional(), notes:z.string().optional(), url:z.string().optional()
  },async({id,...patch})=>{const r=await backendFetch("/applications/"+encodeURIComponent(id),{method:"PATCH",body:JSON.stringify(patch)});return toolResult({status:r.status,body:await r.json()})});
  mcp.tool("nexus_validate_workflow", "Validate and order a proposed workflow. It is planning-only and never executes actions.", {
    tasks:z.array(z.object({id:z.string(),title:z.string(),dependsOn:z.array(z.string()).optional(),risk:z.enum(["low","medium","high"]).optional(),requiresApproval:z.boolean().optional()})).min(1).max(40)
  },async(args)=>{const r=await backendFetch("/workflows/validate",{method:"POST",body:JSON.stringify(args)});return toolResult({status:r.status,body:await r.json()})});
  return mcp;
}
app.get("/health",(_req,res)=>res.json({ok:true,service:"nexus-chatgpt-mcp",backend}));
app.all("/mcp",async(req,res,next)=>{\n  const access=process.env.MCP_ACCESS_TOKEN;\n  const bearer=(req.headers.authorization||"").replace(/^Bearer\\s+/i,"");\n  if(!access) return res.status(503).json({error:"MCP_ACCESS_TOKEN is not configured."});\n  if(bearer!==access) return res.status(401).json({error:"Unauthorized"});
  const server=makeServer();
  const transport=new StreamableHTTPServerTransport({sessionIdGenerator:undefined});
  res.on("close",()=>{transport.close();server.close()});
  try { await server.connect(transport); await transport.handleRequest(req,res,req.body); }
  catch(e){ console.error("MCP transport error",e); if(!res.headersSent)res.status(500).json({error:"MCP transport failed"}); }
});
app.listen(port,()=>console.log("NEXUS MCP server on port "+port));
