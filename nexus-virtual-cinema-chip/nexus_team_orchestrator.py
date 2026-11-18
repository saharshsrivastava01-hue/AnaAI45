"""NEXUS film-team task planner. Local/offline by default; optional Teams webhook notifications.

This planner does not call AI providers or renderers. It creates a transparent task plan
and may send a notification to a webhook explicitly supplied via environment variable.
"""
from __future__ import annotations
import json, os, sys, urllib.request
from datetime import datetime, timezone

ROLES = [
 ("producer","Executive Producer","Approve scope, runtime, milestones and budget guardrails."),
 ("writer","Screenwriter","Draft screenplay beats, dialogue and scene descriptions."),
 ("continuity","Continuity Editor","Maintain character, timeline, props and location continuity."),
 ("design","Production Designer","Define environment, palette, props and asset briefs."),
 ("camera","Cinematographer","Specify framing, lens, movement and shot composition."),
 ("lighting","Lighting Artist","Specify practical lighting and atmosphere."),
 ("vfx","VFX Supervisor","Plan compositing, particles, simulations and effects."),
 ("assets","Asset Engineer","Create asset manifests and procedural asset tasks."),
 ("animation","Animation Director","Plan motion, blocking, timing and character animation."),
 ("sound","Sound Designer","Plan dialogue, ambience, effects and music briefs."),
 ("scheduler","Render Scheduler","Queue real local renders with measured resource limits."),
 ("editor","Editor","Plan assembly, timing, transitions and export."),
 ("qa","Quality Reviewer","Review frames, continuity, audio and delivery requirements."),
 ("4d","4D Experience Planner","Plan optional cue metadata for compatible physical systems.")
]
def plan(title, premise, runtime):
 tasks=[]
 for i,(key,role,desc) in enumerate(ROLES):
  tasks.append({"id":f"T{i+1:02}","role":role,"description":desc,"status":"planned","depends_on":[] if i<2 else ["T01","T02"]})
 return {"project":{"title":title,"premise":premise,"runtime_minutes":runtime},"created_at":datetime.now(timezone.utc).isoformat(),"execution_mode":"planning_only","tasks":tasks,"resource_note":"No GPU units are allocated or consumed by this plan."}
def notify_teams(message):
 url=os.getenv("NEXUS_TEAMS_WEBHOOK_URL")
 if not url: return "Teams webhook not configured; notification skipped."
 payload=json.dumps({"text":message}).encode()
 req=urllib.request.Request(url,data=payload,headers={"Content-Type":"application/json"},method="POST")
 with urllib.request.urlopen(req,timeout=10) as res:
  return f"Webhook response HTTP {res.status}"
if __name__=="__main__":
 title=sys.argv[1] if len(sys.argv)>1 else "NEXUS 2090: THE LAST INTELLIGENCE"
 premise=sys.argv[2] if len(sys.argv)>2 else "A geometric intelligence appears in Earth's orbit."
 runtime=int(sys.argv[3]) if len(sys.argv)>3 else 100
 result=plan(title,premise,runtime)
 out="nexus_team_plan.json"
 with open(out,"w",encoding="utf-8") as f: json.dump(result,f,indent=2,ensure_ascii=False)
 print(f"Saved {out} with {len(result['tasks'])} role tasks.")
 print(notify_teams(f"NEXUS production plan created: {title} ({runtime} min). Tasks: {len(result['tasks'])}."))
