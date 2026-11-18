"""NEXUS-3000 physical worker capability probe.

This safe first-stage worker reports local capabilities only. It does not accept
remote commands, execute arbitrary shell strings, or claim a GPU render.
Run: python nexus_gpu_worker_probe.py
Optional: pip install psutil
"""
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

def command_version(executable, args):
    path = shutil.which(executable)
    if not path:
        return {"available": False, "path": None, "version": None}
    try:
        p = subprocess.run([path, *args], capture_output=True, text=True, timeout=8)
        output = (p.stdout or p.stderr).strip().splitlines()
        return {"available": p.returncode == 0, "path": path,
                "version": output[0][:300] if output else f"exit={p.returncode}"}
    except Exception as exc:
        return {"available": True, "path": path, "error": str(exc)}

def main():
    report = {
        "worker": "NEXUS-3000",
        "probe_only": True,
        "os": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "blender": command_version("blender", ["--version"]),
        "ffmpeg": command_version("ffmpeg", ["-version"]),
        "nvidia_smi": command_version("nvidia-smi", ["--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"]),
        "workspace": str(Path.cwd().resolve()),
    }
    try:
        import psutil
        report["ram"] = {
            "total_bytes": psutil.virtual_memory().total,
            "available_bytes": psutil.virtual_memory().available,
        }
    except ImportError:
        report["ram"] = {"available": False, "note": "Install psutil for RAM telemetry"}
    try:
        import torch
        report["pytorch"] = {
            "version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count(),
            "devices": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
        }
    except Exception as exc:
        report["pytorch"] = {"available": False, "note": str(exc)}
    print(json.dumps(report, indent=2))
    print("\nProbe only: no rendering was submitted and no hardware was modified.")

if __name__ == "__main__":
    main()
