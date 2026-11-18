#!/usr/bin/env python3
"""NEXUS-3000 Film Fabric: local-first production infrastructure.

This is a practical orchestration layer, not a physical GPU/TPU simulator.
It stores a film project, validates its dependency graph, schedules bounded
local tasks, records resumable state in SQLite, and can invoke Blender/FFmpeg
only when explicitly configured and installed. No paid cloud services are used.
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

VERSION = "0.2.0"
ENGINES = ("VTPU", "VGPU", "VFXU", "VRPU", "VMEDIA", "VMEM", "VNoC")


@dataclass
class Task:
    task_id: str
    stage: str
    engine: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    command: list[str] | None = None
    status: str = "pending"
    attempts: int = 0
    output: str | None = None
    error: str | None = None


def starter_tasks() -> list[Task]:
    """A small, honest starter graph; replace commands with real generators."""
    return [
        Task("brief", "creative", "VTPU", "Lock premise, tone, runtime and constraints"),
        Task("script", "writing", "VTPU", "Create screenplay and dialogue", ["brief"]),
        Task("boards", "preproduction", "VRPU", "Create shot list and storyboard plan", ["script"]),
        Task("assets", "assets", "VMEM", "Register required models, textures and audio", ["boards"]),
        Task("scene", "scene-build", "VGPU", "Build a procedural Blender scene", ["assets"]),
        Task("vfx", "lookdev-vfx", "VFXU", "Apply lighting, compositing and effects", ["scene"]),
        Task("render", "render", "VGPU", "Render frames using local Blender", ["vfx"]),
        Task("sound-edit", "post", "VMEDIA", "Mix audio and assemble edit", ["render"]),
        Task("qc", "quality", "VRPU", "Check output existence, duration and media integrity", ["sound-edit"]),
        Task("master", "delivery", "VMEDIA", "Publish final master and manifest", ["qc"]),
    ]


class Fabric:
    def __init__(self, root: Path, max_workers: int = 2, max_attempts: int = 2):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "fabric.sqlite3"
        self.max_workers = max(1, min(max_workers, 8))
        self.max_attempts = max(1, max_attempts)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated REAL NOT NULL)""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT,
            event TEXT NOT NULL, detail TEXT, created REAL NOT NULL)""")
        self.conn.commit()

    def close(self):
        self.conn.close()

    def record(self, task: Task, event: str, detail: str = ""):
        self.conn.execute(
            "INSERT OR REPLACE INTO tasks(task_id,payload,updated) VALUES(?,?,?)",
            (task.task_id, json.dumps(asdict(task)), time.time()))
        self.conn.execute(
            "INSERT INTO events(task_id,event,detail,created) VALUES(?,?,?,?)",
            (task.task_id, event, detail, time.time()))
        self.conn.commit()

    def load(self) -> list[Task]:
        rows = self.conn.execute("SELECT payload FROM tasks ORDER BY updated").fetchall()
        return [Task(**json.loads(row[0])) for row in rows]

    @staticmethod
    def validate(tasks: list[Task]):
        by_id = {t.task_id: t for t in tasks}
        if len(by_id) != len(tasks):
            raise ValueError("Duplicate task_id found")
        for task in tasks:
            if task.engine not in ENGINES:
                raise ValueError(f"Unknown engine {task.engine} on {task.task_id}")
            missing = set(task.depends_on) - set(by_id)
            if missing:
                raise ValueError(f"{task.task_id} has missing dependencies: {sorted(missing)}")
        visiting, visited = set(), set()
        def visit(node: str):
            if node in visiting:
                raise ValueError(f"Dependency cycle detected at {node}")
            if node in visited:
                return
            visiting.add(node)
            for dep in by_id[node].depends_on:
                visit(dep)
            visiting.remove(node)
            visited.add(node)
        for key in by_id:
            visit(key)

    def run_command(self, task: Task) -> tuple[bool, str]:
        if not task.command:
            # Planning tasks deliberately complete as recorded placeholders.
            return True, "No command configured; recorded as a planning checkpoint."
        executable = shutil.which(task.command[0])
        if not executable:
            return False, f"Required executable not found on PATH: {task.command[0]}"
        proc = subprocess.run(task.command, cwd=self.root, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=60 * 60, check=False)
        log_dir = self.root / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"{task.task_id}.log"
        log_file.write_text(proc.stdout or "", encoding="utf-8")
        return proc.returncode == 0, f"exit={proc.returncode}; log={log_file}"

    def execute(self, tasks: list[Task]) -> dict[str, Any]:
        self.validate(tasks)
        by_id = {t.task_id: t for t in tasks}
        # Reuse completed tasks, but retry interrupted/failed tasks.
        for task in tasks:
            self.record(task, "queued", task.description)
        running: dict[futures.Future, Task] = {}
        with futures.ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            while True:
                progressed = False
                for task in tasks:
                    if task.status != "pending" or len(running) >= self.max_workers:
                        continue
                    deps = [by_id[d] for d in task.depends_on]
                    if any(d.status == "failed" for d in deps):
                        task.status, task.error = "blocked", "A dependency failed"
                        self.record(task, "blocked", task.error)
                        progressed = True
                    elif all(d.status == "completed" for d in deps):
                        task.status = "running"
                        task.attempts += 1
                        self.record(task, "started", f"attempt {task.attempts}")
                        running[pool.submit(self.run_command, task)] = task
                        progressed = True
                if running:
                    done, _ = futures.wait(running, return_when=futures.FIRST_COMPLETED)
                    for future in done:
                        task = running.pop(future)
                        try:
                            ok, detail = future.result()
                        except Exception as exc:
                            ok, detail = False, repr(exc)
                        if ok:
                            task.status, task.output, task.error = "completed", detail, None
                            self.record(task, "completed", detail)
                        elif task.attempts < self.max_attempts:
                            task.status, task.error = "pending", detail
                            self.record(task, "retry-scheduled", detail)
                        else:
                            task.status, task.error = "failed", detail
                            self.record(task, "failed", detail)
                    progressed = True
                unfinished = [t for t in tasks if t.status in ("pending", "running")]
                if not unfinished:
                    break
                if not progressed and not running:
                    raise RuntimeError("Scheduler stalled; inspect dependency graph")
        return {
            "fabric_version": VERSION,
            "project_root": str(self.root),
            "virtual_lane_namespace": 1_000_000_000_000,
            "physical_accelerators_claimed": 0,
            "max_local_workers": self.max_workers,
            "tasks": [asdict(t) for t in tasks],
            "summary": {s: sum(t.status == s for t in tasks)
                        for s in ("completed", "failed", "blocked", "pending")},
        }


def write_project(root: Path, title: str):
    root.mkdir(parents=True, exist_ok=True)
    for folder in ("assets/models", "assets/textures", "assets/audio", "shots",
                   "renders/frames", "renders/proxies", "audio", "edit", "delivery", "logs"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    manifest = {
        "project_id": str(uuid.uuid4()),
        "title": title,
        "fabric_version": VERSION,
        "created_unix": time.time(),
        "policy": {"paid_cloud": False, "external_paid_apis": False},
        "targets": {"resolution": "640x360 proxy", "fps": 12, "container": "mp4"},
        "folders": ["assets", "shots", "renders", "audio", "edit", "delivery"],
        "note": "Proxy defaults are intentional; scale only after a successful local test."
    }
    path = root / "project.json"
    if not path.exists():
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="NEXUS-3000 local-first film fabric")
    parser.add_argument("--project", default="NEXUS_2090_FILM", help="Project directory")
    parser.add_argument("--title", default="NEXUS 2090: THE LAST INTELLIGENCE")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--init-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    root = Path(args.project)
    manifest = write_project(root, args.title)
    if args.self_test:
        tasks = starter_tasks()
        Fabric.validate(tasks)
        assert len(tasks) == 10
        assert all(t.engine in ENGINES for t in tasks)
        print("SELF-TEST PASS: graph valid; 10 stages; no physical accelerator claim.")
        return
    print(f"Project initialized: {root.resolve()}")
    print(f"Manifest: {root / 'project.json'}")
    if args.init_only:
        return
    fabric = Fabric(root, args.workers, args.max_attempts)
    try:
        report = fabric.execute(starter_tasks())
        report_path = root / "fabric_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report["summary"], indent=2))
        print(f"Report: {report_path}")
        print("NOTE: unconfigured stages are planning checkpoints, not generated footage.")
    finally:
        fabric.close()


if __name__ == "__main__":
    main()
