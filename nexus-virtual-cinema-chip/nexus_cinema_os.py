#!/usr/bin/env python3
"""NEXUS CINEMA OS — virtual-chip film production orchestrator.

This is an executable software-defined scheduler, not a physical GPU and not a
replacement renderer. It coordinates real backends through one NEXUS interface.
No paid service is called unless the operator explicitly configures one.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

VERSION = "0.1.0"
ROOT = Path.cwd()
PROJECTS = ROOT / "nexus_projects"

# Logical chip engines. Each must be bound to an actual executable backend.
ENGINES = {
    "VTPU": "director/planning/model inference",
    "VGPU": "3D scene and frame rendering",
    "VFXU": "compositing, particles, lighting and effects",
    "VRPU": "image processing, tracking and transforms",
    "VMEDIA": "audio, timeline assembly and MP4 encoding",
    "VMEM": "assets, continuity and project state",
    "VNoC": "task routing, retries and resource scheduling",
}

@dataclass
class Task:
    task_id: str
    opcode: str
    engine: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    status: str = "planned"
    backend: str = "unassigned"
    outputs: list[str] = field(default_factory=list)

@dataclass
class FilmProject:
    project_id: str
    title: str
    prompt: str
    duration_seconds: int
    fps: int
    width: int
    height: int
    created_at: float
    status: str
    engines: dict[str, str]
    tasks: list[Task]
    output_file: str = "exports/final_movie.mp4"
    policy: dict[str, Any] = field(default_factory=lambda: {
        "paid_backends_allowed": False,
        "require_user_approval_for_paid_jobs": True,
        "chatgpt_private_compute_access": False,
    })

def build_tasks() -> list[Task]:
    specs = [
        ("BRIEF", "VTPU", "Parse brief, audience, genre and constraints", []),
        ("DIRECT", "VTPU", "Create director treatment and visual language", ["BRIEF"]),
        ("SCRIPT", "VTPU", "Write screenplay, narration and scene beats", ["DIRECT"]),
        ("STORYBOARD", "VTPU", "Create shot list, camera plans and timing", ["SCRIPT"]),
        ("ASSETS", "VMEM", "Build character, environment, prop and continuity bible", ["STORYBOARD"]),
        ("SCENES", "VGPU", "Build procedural 3D scenes and animation", ["ASSETS"]),
        ("INFERENCE", "VTPU", "Run only explicitly configured model inference", ["STORYBOARD", "ASSETS"]),
        ("VFX", "VFXU", "Composite scene layers, lighting, particles and effects", ["SCENES", "INFERENCE"]),
        ("POST", "VRPU", "Tracking, transforms, denoise and image processing", ["VFX"]),
        ("AUDIO", "VMEDIA", "Prepare dialogue, ambience, music and sound effects", ["SCRIPT"]),
        ("EDIT", "VMEDIA", "Assemble shots, transitions, titles and sound", ["POST", "AUDIO"]),
        ("QA", "VNoC", "Validate duration, frame sequence, audio and output", ["EDIT"]),
        ("EXPORT", "VMEDIA", "Encode final MP4 and write delivery manifest", ["QA"]),
    ]
    return [Task(task_id=f"T{i+1:02d}", opcode=op, engine=engine,
                 description=desc, depends_on=deps)
            for i, (op, engine, desc, deps) in enumerate(specs)]

def create_project(args: argparse.Namespace) -> Path:
    pid = uuid.uuid4().hex[:10]
    folder = PROJECTS / pid
    (folder / "assets").mkdir(parents=True)
    (folder / "shots").mkdir()
    (folder / "renders").mkdir()
    (folder / "exports").mkdir()
    project = FilmProject(
        project_id=pid, title=args.title, prompt=args.prompt,
        duration_seconds=args.duration, fps=args.fps,
        width=args.width, height=args.height, created_at=time.time(),
        status="planned", engines=ENGINES, tasks=build_tasks())
    (folder / "project.json").write_text(
        json.dumps(asdict(project), indent=2), encoding="utf-8")
    (folder / "DIRECTOR_BRIEF.md").write_text(
        f"# {args.title}\n\n## Creative brief\n{args.prompt}\n\n"
        f"## Delivery target\n{args.duration}s · {args.fps} fps · "
        f"{args.width}×{args.height}\n\n"
        "## Director workflow\n"
        "NEXUS will create a treatment, screenplay, shot list, asset bible, "
        "render plan, VFX plan, edit plan and QA report.\n",
        encoding="utf-8")
    print(f"Project created: {folder}")
    print(f"Project ID: {pid}")
    print("Status: PLANNED — no rendering has been performed.")
    return folder

def load_project(path: str) -> tuple[Path, dict[str, Any]]:
    folder = Path(path).resolve()
    manifest = folder / "project.json"
    if not manifest.is_file():
        raise SystemExit(f"Missing project manifest: {manifest}")
    return folder, json.loads(manifest.read_text(encoding="utf-8"))

def status(args: argparse.Namespace) -> None:
    folder, data = load_project(args.project)
    print(f"{data['title']} [{data['project_id']}] — {data['status']}")
    for task in data["tasks"]:
        print(f"{task['task_id']}  {task['opcode']:<12} "
              f"{task['engine']:<7} {task['status']}")

def preflight(args: argparse.Namespace) -> None:
    print("NEXUS CINEMA OS backend preflight")
    for executable in ("blender", "ffmpeg"):
        path = shutil.which(executable)
        print(f"{executable}: {path or 'NOT FOUND'}")
    print("ChatGPT private compute: not an exposed execution target")
    print("Paid inference: disabled by default")
    print("Preflight does not launch jobs or consume paid credits.")

def plan(args: argparse.Namespace) -> None:
    folder, data = load_project(args.project)
    rows = ["# NEXUS Render Plan", "", f"Project: {data['title']}", ""]
    for task in data["tasks"]:
        rows.append(f"- [ ] **{task['opcode']}** ({task['engine']}): "
                    f"{task['description']}")
        if task["depends_on"]:
            rows.append(f"  - Depends on: {', '.join(task['depends_on'])}")
    (folder / "RENDER_PLAN.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Render plan written: {folder / 'RENDER_PLAN.md'}")
    print("The plan is ready; execution adapters must be configured per engine.")

def main() -> None:
    parser = argparse.ArgumentParser(
        description="NEXUS CINEMA OS — one virtual-chip interface for film production")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("create", help="Create a film project and task graph")
    c.add_argument("--title", default="NEXUS: The Awakening")
    c.add_argument("--prompt", required=True)
    c.add_argument("--duration", type=int, default=60)
    c.add_argument("--fps", type=int, default=24)
    c.add_argument("--width", type=int, default=1920)
    c.add_argument("--height", type=int, default=1080)
    c.set_defaults(func=create_project)
    s = sub.add_parser("status", help="Show project and virtual-chip task status")
    s.add_argument("project")
    s.set_defaults(func=status)
    p = sub.add_parser("plan", help="Compile the film task graph")
    p.add_argument("project")
    p.set_defaults(func=plan)
    pf = sub.add_parser("preflight", help="Check local render executables")
    pf.set_defaults(func=preflight)
    args = parser.parse_args()
    if getattr(args, "duration", 1) < 1 or getattr(args, "fps", 1) < 1:
        parser.error("duration and fps must be positive")
    args.func(args)

if __name__ == "__main__":
    main()
