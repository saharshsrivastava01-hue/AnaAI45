#!/usr/bin/env python3
"""NEXUS OMEGA Cinema: native local execution orchestrator.

The virtual chip describes and routes work. Actual rendering is performed by
the local NEXUS renderer on the host CPU unless a future compatible backend is
implemented and detected. No external AI/video service is called.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

from nexus_omega_futuristic_chip import Job, plan_jobs, topology
from nexus_horizon_runtime import inventory
from nexus_omega_processor import NexusOmegaProcessor

ROOT = Path(__file__).resolve().parent
PIPELINE = ROOT / "nexus_film_pipeline.py"


def run_local_render(args: argparse.Namespace) -> dict:
    if not PIPELINE.is_file():
        raise FileNotFoundError(f"Local NEXUS film pipeline not found: {PIPELINE}")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg and ffprobe are required for MP4 assembly; install them locally first.")

    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    hardware = inventory()
    plan = plan_jobs([
        Job("cinema_scene_and_raytrace", "PRSE", complexity=args.frames * args.width * args.height * args.spp),
        Job("procedural_scene_graph", "PGA", complexity=args.frames),
        Job("encode_video", "VEM", complexity=args.frames),
        Job("master_control", "CSCC", complexity=1),
    ])
    # The plan is descriptive; the real execution backend is the detected host.
    cpu = next((d for d in hardware["devices"] if d["kind"] == "CPU" and d["available"]), None)
    if cpu is None:
        raise RuntimeError("No host CPU execution device was detected.")

    command = [
        sys.executable, str(PIPELINE),
        "--out", str(out),
        "--width", str(args.width), "--height", str(args.height),
        "--frames", str(args.frames), "--fps", str(args.fps),
        "--spp", str(args.spp), "--depth", str(args.depth),
        "--preset", args.preset,
    ]
    manifest = {
        "project": "NEXUS OMEGA Cinema",
        "execution_mode": "native_local_host_execution",
        "external_video_models_used": False,
        "virtual_chip": topology(),
        "hardware_discovery": hardware,
        "workload_plan": plan,
        "execution_backend": {
            "device_id": cpu["device_id"],
            "device_name": cpu["name"],
            "backend": "local Python + NEXUS CPU renderer + FFmpeg",
            "virtual_lanes_are_physical_cores": False,
        },
        "command": command,
        "status": "starting_local_render",
    }
    manifest_path = out / "nexus_omega_execution.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\\n", encoding="utf-8")
    processor = NexusOmegaProcessor()
    boot_report = processor.boot()
    manifest["processor_boot_report"] = boot_report
    started = time.perf_counter()
    try:
        instruction = processor.dispatch("EXEC", command)
        instruction_result = processor.wait(instruction)
    finally:
        processor.shutdown()
    elapsed = time.perf_counter() - started
    manifest["processor_execution"] = processor.snapshot()
    manifest["retired_instruction"] = instruction_result
    manifest["status"] = "completed"
    manifest["elapsed_seconds"] = round(elapsed, 3)
    manifest["output_video"] = str(out / "NEXUS_FILM.mp4")
    manifest["performance_claims"] = {
        "measured_wall_time_seconds": round(elapsed, 3),
        "speedup_claim": None,
        "note": "One run is not a comparative benchmark; virtual chip lane counts are not physical compute."
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=Path("NEXUS_OMEGA_MOVIE"))
    p.add_argument("--width", type=int, default=160)
    p.add_argument("--height", type=int, default=90)
    p.add_argument("--frames", type=int, default=24)
    p.add_argument("--fps", type=int, default=12)
    p.add_argument("--spp", type=int, default=1)
    p.add_argument("--depth", type=int, default=1)
    p.add_argument("--preset", choices=("cinema", "sci-fi", "neutral"), default="sci-fi")
    args = p.parse_args()
    if not (16 <= args.width <= 640 and 16 <= args.height <= 360
            and 1 <= args.frames <= 120 and 1 <= args.fps <= 60
            and 1 <= args.spp <= 16 and 0 <= args.depth <= 5):
        p.error("Render settings exceed the existing prototype's safe limits.")
    try:
        result = run_local_render(args)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        p.exit(2, f"NEXUS local execution could not complete: {exc}\n")
    print(json.dumps({
        "status": result["status"],
        "output_video": result.get("output_video"),
        "elapsed_seconds": result.get("elapsed_seconds"),
        "manifest": str((args.out.resolve() / "nexus_omega_execution.json")),
        "backend": result["execution_backend"],
        "processor": result["processor_execution"],
    }, indent=2))


if __name__ == "__main__":
    main()
