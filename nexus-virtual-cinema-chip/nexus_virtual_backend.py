#!/usr/bin/env python3
"""NEXUS 3000 Virtual Cinema Backend.

A single local control plane for the virtual chip: project registry, task graph,
SQLite job ledger, bounded worker pool, capability registry and render handoff.
All engines are logical software adapters mapped to explicitly installed local
tools. No hidden/cloud compute or paid provider is assumed.

Run:
  python nexus_virtual_backend.py --host 127.0.0.1 --port 8787
Optional API dependency:
  pip install fastapi uvicorn
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import subprocess
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

ROOT = Path(os.getenv("NEXUS_HOME", "./nexus_runtime")).resolve()
DB = ROOT / "nexus_chip.db"
MAX_WORKERS = max(1, min(int(os.getenv("NEXUS_WORKERS", "2")), 4))
QUEUE: asyncio.Queue[str] = asyncio.Queue()
WORKERS: list[asyncio.Task] = []
ENGINES = {
    "VTPU": {"role": "planning_and_prompt_compilation", "backend": "local_rules", "ready": True},
    "VGPU": {"role": "procedural_3d_rendering", "backend": "blender_cli", "ready": False},
    "VFXU": {"role": "compositing_and_effects", "backend": "blender_compositor", "ready": False},
    "VRPU": {"role": "image_processing_and_upscale", "backend": "local_cli_adapter", "ready": False},
    "VMEDIA": {"role": "timeline_audio_and_mp4", "backend": "ffmpeg_cli", "ready": False},
    "VMEM": {"role": "assets_and_project_state", "backend": "sqlite_filesystem", "ready": True},
    "VNoC": {"role": "routing_scheduling_and_retries", "backend": "asyncio_task_graph", "ready": True},
}

def db() -> sqlite3.Connection:
    ROOT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS projects(
        id TEXT PRIMARY KEY, title TEXT NOT NULL, prompt TEXT NOT NULL,
        created REAL NOT NULL, state TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS tasks(
        id TEXT PRIMARY KEY, project_id TEXT NOT NULL, engine TEXT NOT NULL,
        kind TEXT NOT NULL, payload TEXT NOT NULL, dependencies TEXT NOT NULL,
        state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
        result TEXT, error TEXT, created REAL NOT NULL, updated REAL NOT NULL)""")
    con.commit()
    return con

def capabilities() -> dict[str, Any]:
    import shutil
    return {
        "engines": ENGINES,
        "host_tools": {name: shutil.which(name) for name in ("blender", "ffmpeg", "python")},
        "worker_limit": MAX_WORKERS,
        "compute_mode": "local_only",
        "paid_services_enabled": False,
    }

def create_project(title: str, prompt: str) -> dict[str, Any]:
    pid = "nxp_" + uuid.uuid4().hex[:12]
    now = time.time()
    con = db()
    con.execute("INSERT INTO projects VALUES(?,?,?,?,?)", (pid, title, prompt, now, "PLANNED"))
    con.commit()
    con.close()
    return {"project_id": pid, "title": title, "state": "PLANNED"}

def add_task(project_id: str, engine: str, kind: str, payload: dict,
             dependencies: list[str] | None = None) -> dict[str, Any]:
    if engine not in ENGINES:
        raise ValueError("Unknown virtual engine")
    tid, now = "nxt_" + uuid.uuid4().hex[:12], time.time()
    con = db()
    if not con.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
        con.close()
        raise ValueError("Project not found")
    con.execute("""INSERT INTO tasks
        (id,project_id,engine,kind,payload,dependencies,state,created,updated)
        VALUES(?,?,?,?,?,?,?,?,?)""",
        (tid, project_id, engine, kind, json.dumps(payload), json.dumps(dependencies or []),
         "QUEUED", now, now))
    con.commit()
    con.close()
    return {"task_id": tid, "state": "QUEUED", "engine": engine}

def task_row(task_id: str):
    con = db()
    row = con.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    con.close()
    return dict(row) if row else None

def execute_local_task(row: dict) -> dict:
    """Safe adapter dispatch. Never executes arbitrary prompt-provided commands."""
    engine, kind = row["engine"], row["kind"]
    payload = json.loads(row["payload"])
    if kind == "compile_film_package" and engine == "VTPU":
        return {"accepted": True, "output": "Use nexus_ai_director.py to compile the screenplay and shot package.",
                "payload_keys": sorted(payload.keys())}
    if kind == "probe_host" and engine == "VMEM":
        return capabilities()
    if kind == "render_blender" and engine in ("VGPU", "VFXU"):
        import shutil
        blender = shutil.which("blender")
        if not blender:
            raise RuntimeError("Blender CLI not installed; render task remains blocked.")
        script = payload.get("script_path")
        if not script or not Path(script).is_file():
            raise RuntimeError("A valid local script_path is required.")
        proc = subprocess.run([blender, "-b", "--python", str(Path(script).resolve())],
                              capture_output=True, text=True, timeout=3600, check=False)
        if proc.returncode:
            raise RuntimeError(proc.stderr[-3000:] or f"Blender exited {proc.returncode}")
        return {"returncode": proc.returncode, "stdout_tail": proc.stdout[-1500:]}
    if kind == "encode_mp4" and engine == "VMEDIA":
        import shutil
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("FFmpeg CLI not installed; encoding task is blocked.")
        # Explicit argv only; no shell interpolation.
        frames, output = payload.get("frames_pattern"), payload.get("output_path")
        if not frames or not output:
            raise RuntimeError("frames_pattern and output_path are required.")
        proc = subprocess.run([ffmpeg, "-y", "-framerate", str(int(payload.get("fps", 24))),
            "-i", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output)],
            capture_output=True, text=True, timeout=3600, check=False)
        if proc.returncode:
            raise RuntimeError(proc.stderr[-3000:] or f"FFmpeg exited {proc.returncode}")
        return {"output_path": str(output)}
    return {"accepted": True, "state": "ADAPTER_REQUIRED",
            "message": f"{engine}/{kind} is registered but has no executable adapter yet."}

async def worker_loop():
    while True:
        task_id = await QUEUE.get()
        try:
            row = task_row(task_id)
            if not row:
                continue
            con = db()
            con.execute("UPDATE tasks SET state='RUNNING', attempts=attempts+1, updated=? WHERE id=?",
                        (time.time(), task_id))
            con.commit()
            con.close()
            try:
                result = await asyncio.to_thread(execute_local_task, row)
                state, error = ("COMPLETED" if result.get("accepted") is not False else "BLOCKED"), None
            except Exception as exc:
                result, state, error = {}, "FAILED", str(exc)
            con = db()
            con.execute("UPDATE tasks SET state=?, result=?, error=?, updated=? WHERE id=?",
                        (state, json.dumps(result), error, time.time(), task_id))
            con.commit()
            con.close()
        finally:
            QUEUE.task_done()

@asynccontextmanager
async def lifespan(app):
    db()
    for _ in range(MAX_WORKERS):
        WORKERS.append(asyncio.create_task(worker_loop()))
    yield
    for task in WORKERS:
        task.cancel()
    await asyncio.gather(*WORKERS, return_exceptions=True)

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
    app = FastAPI(title="NEXUS 3000 Virtual Cinema Chip", version="0.1.0", lifespan=lifespan)

    class ProjectIn(BaseModel):
        title: str = Field(min_length=1, max_length=160)
        prompt: str = Field(min_length=1, max_length=12000)

    class TaskIn(BaseModel):
        project_id: str
        engine: str
        kind: str
        payload: dict = {}
        dependencies: list[str] = []

    @app.get("/health")
    def health():
        return {"status": "online", "control_plane": "local", "capabilities": capabilities()}

    @app.post("/v1/projects")
    def project_create(body: ProjectIn):
        return create_project(body.title, body.prompt)

    @app.post("/v1/tasks")
    async def task_create(body: TaskIn):
        try:
            task = add_task(body.project_id, body.engine, body.kind, body.payload, body.dependencies)
            await QUEUE.put(task["task_id"])
            return task
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/v1/tasks/{task_id}")
    def task_status(task_id: str):
        row = task_row(task_id)
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        for key in ("payload", "dependencies", "result"):
            if row.get(key):
                row[key] = json.loads(row[key])
        return row

    @app.get("/v1/projects/{project_id}")
    def project_status(project_id: str):
        con = db()
        project = con.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        tasks = con.execute("SELECT id,engine,kind,state,error,created,updated FROM tasks WHERE project_id=? ORDER BY created",
                            (project_id,)).fetchall()
        con.close()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"project": dict(project), "tasks": [dict(t) for t in tasks]}

except ImportError:
    app = None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    if app is None:
        raise SystemExit("Install backend dependencies: pip install fastapi uvicorn")
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
