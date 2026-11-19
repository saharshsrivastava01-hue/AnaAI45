"""Secure bridge that lets a ChatGPT Action dispatch and inspect NEXUS renders.

Deploy this API on a public HTTPS host. Keep GITHUB_TOKEN and NEXUS_CHATGPT_API_KEY
in the host's secret manager; never put either secret in a GPT prompt or OpenAPI file.
"""
import os
import secrets
from typing import Optional

import requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="NEXUS Render Bridge", version="1.0.0")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
CHATGPT_API_KEY = os.getenv("NEXUS_CHATGPT_API_KEY", "")
REPO = os.getenv("NEXUS_GITHUB_REPO", "saharshsrivastava01-hue/AnaAI45")
BRANCH = os.getenv("NEXUS_GITHUB_BRANCH", "nexus-virtual-cinema-chip")
WORKFLOW = os.getenv("NEXUS_WORKFLOW_FILE", "nexus-renderer-ci.yml")
API = "https://api.github.com"
SESSION = requests.Session()
SESSION.headers.update({
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
})
if GITHUB_TOKEN:
    SESSION.headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"


class RenderRequest(BaseModel):
    project: str = Field(default="NEXUS_2090_DUMMY_FILM", max_length=80)
    confirm_cost: bool = Field(default=True, description="Must be true; workflow uses GitHub-hosted runner minutes.")
    frames: int = Field(default=120, ge=2, le=600)
    fps: int = Field(default=12, ge=1, le=30)


def authorize(authorization: Optional[str]):
    if not CHATGPT_API_KEY:
        raise HTTPException(503, "Bridge is not configured: set NEXUS_CHATGPT_API_KEY.")
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not secrets.compare_digest(supplied, CHATGPT_API_KEY):
        raise HTTPException(401, "Invalid bridge API key.")
    if not GITHUB_TOKEN:
        raise HTTPException(503, "Bridge is not configured: set GITHUB_TOKEN with Actions write permission.")


def gh(method: str, path: str, **kwargs):
    response = SESSION.request(method, f"{API}{path}", timeout=30, **kwargs)
    if response.status_code >= 400:
        raise HTTPException(response.status_code, f"GitHub API error: {response.text[:1200]}")
    return response.json() if response.content else {}


@app.get("/health")
def health():
    return {"service": "NEXUS Render Bridge", "configured": bool(GITHUB_TOKEN and CHATGPT_API_KEY)}


@app.post("/render")
def start_render(body: RenderRequest, authorization: Optional[str] = Header(default=None)):
    authorize(authorization)
    if not body.confirm_cost:
        raise HTTPException(400, "Set confirm_cost=true to authorize use of GitHub Actions runner minutes.")
    # Current checked-in workflow accepts workflow_dispatch but has no input parameters.
    # Fixed branch and workflow prevent arbitrary repository/workflow dispatch.
    gh("POST", f"/repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches",
       json={"ref": BRANCH})
    runs = gh("GET", f"/repos/{REPO}/actions/workflows/{WORKFLOW}/runs",
              params={"branch": BRANCH, "event": "workflow_dispatch", "per_page": 5})
    candidates = runs.get("workflow_runs", [])
    run = candidates[0] if candidates else None
    return {
        "accepted": True,
        "message": "Workflow dispatch accepted. GitHub may take a short time to create the run.",
        "run": ({"id": run["id"], "status": run["status"], "html_url": run["html_url"]}
                if run else None),
        "note": "The currently committed workflow renders its configured 120-frame demo; requested frames/fps are descriptive only until workflow inputs are added."
    }


@app.get("/runs/{run_id}")
def get_run(run_id: int, authorization: Optional[str] = Header(default=None)):
    authorize(authorization)
    run = gh("GET", f"/repos/{REPO}/actions/runs/{run_id}")
    return {k: run.get(k) for k in ("id", "name", "status", "conclusion", "html_url", "created_at", "updated_at")}


@app.get("/runs/{run_id}/artifacts")
def get_artifacts(run_id: int, authorization: Optional[str] = Header(default=None)):
    authorize(authorization)
    data = gh("GET", f"/repos/{REPO}/actions/runs/{run_id}/artifacts")
    return {"artifacts": [
        {"name": a["name"], "expired": a["expired"], "size_in_bytes": a["size_in_bytes"],
         "archive_download_url": a["archive_download_url"]}
        for a in data.get("artifacts", [])
    ]}


@app.get("/openapi.json", include_in_schema=True)
def openapi_document():
    return app.openapi()
