#!/usr/bin/env python3
"""NEXUS OMEGA Virtual Chip Emulator.

A software-defined processor: virtual cores execute an explicit instruction set,
use virtual registers and bounded virtual memory, and render deterministic frames.
The emulator is portable Python. The host OS/CPU still performs the underlying
instructions; virtual cores are not physical silicon or independent hardware.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import platform
import struct
import time
from typing import Any


@dataclass
class VirtualCore:
    core_id: int
    registers: dict[str, float] = field(default_factory=lambda: {f"R{i}": 0.0 for i in range(16)})
    retired: int = 0
    cycles: int = 0
    state: str = "IDLE"


class VirtualMemory:
    def __init__(self, capacity_bytes: int) -> None:
        if capacity_bytes < 4096:
            raise ValueError("Virtual memory must be at least 4096 bytes")
        self.capacity = capacity_bytes
        self._store: dict[str, Any] = {}

    def write(self, address: str, value: Any) -> None:
        encoded = repr(value).encode("utf-8")
        used = sum(len(repr(v).encode("utf-8")) for v in self._store.values())
        old = len(repr(self._store[address]).encode("utf-8")) if address in self._store else 0
        if used - old + len(encoded) > self.capacity:
            raise MemoryError("NEXUS virtual memory capacity exceeded")
        self._store[address] = value

    def read(self, address: str) -> Any:
        return self._store[address]

    def stats(self) -> dict:
        used = sum(len(repr(v).encode("utf-8")) for v in self._store.values())
        return {"capacity_bytes": self.capacity, "used_bytes": used,
                "free_bytes": self.capacity - used, "cells": len(self._store)}


class NEXUSVirtualChip:
    """Small deterministic ISA emulator with a parallel virtual-core fabric."""

    ISA = {"LOAD", "ADD", "MUL", "SIN", "STORE", "RENDER_TILE", "HALT"}

    def __init__(self, cores: int = 4, memory_mb: int = 64) -> None:
        if not 1 <= cores <= 64:
            raise ValueError("Virtual core count must be between 1 and 64")
        self.cores = [VirtualCore(i) for i in range(cores)]
        self.memory = VirtualMemory(memory_mb * 1024 * 1024)
        self.booted = False
        self.trace: list[dict] = []
        self._trace_limit = 2000
        self._retired = 0
        self._faults = 0
        self._start = 0.0

    def _event(self, event: str, **data: Any) -> None:
        if len(self.trace) < self._trace_limit:
            self.trace.append({"t": round(time.perf_counter() - self._start, 6),
                               "event": event, **data})

    def boot(self) -> dict:
        if self.booted:
            raise RuntimeError("NEXUS virtual chip is already booted")
        self._start = time.perf_counter()
        self._event("POWER_ON", firmware="NEXUS-OMEGA-ISA/1.0")
        self._event("MEMORY_INIT", **self.memory.stats())
        for core in self.cores:
            core.state = "READY"
            self._event("CORE_READY", core=core.core_id)
        self.booted = True
        return self.status()

    def execute(self, core: VirtualCore, program: list[tuple]) -> dict:
        if not self.booted:
            raise RuntimeError("Boot the virtual chip before dispatch")
        core.state = "RUNNING"
        for pc, ins in enumerate(program):
            op, *a = ins
            if op not in self.ISA:
                self._faults += 1
                core.state = "FAULT"
                raise ValueError(f"Illegal opcode at PC={pc}: {op}")
            if op == "LOAD":
                reg, value = a
                core.registers[reg] = float(value)
            elif op == "ADD":
                dst, left, right = a
                core.registers[dst] = core.registers[left] + core.registers[right]
            elif op == "MUL":
                dst, left, right = a
                core.registers[dst] = core.registers[left] * core.registers[right]
            elif op == "SIN":
                dst, src = a
                core.registers[dst] = math.sin(core.registers[src])
            elif op == "STORE":
                address, reg = a
                self.memory.write(address, core.registers[reg])
            elif op == "RENDER_TILE":
                frame, tile, width, height = a
                pixels = self._render_tile(frame, tile, width, height)
                self.memory.write(f"frame:{frame}:tile:{tile}", pixels)
            elif op == "HALT":
                core.state = "HALTED"
                core.retired += 1
                self._retired += 1
                break
            core.retired += 1
            core.cycles += 1
            self._retired += 1
        if core.state == "RUNNING":
            core.state = "READY"
        self._event("PROGRAM_RETIRED", core=core.core_id,
                    instructions=core.retired, state=core.state)
        return {"core": core.core_id, "retired": core.retired, "state": core.state}

    @staticmethod
    def _render_tile(frame: int, tile: int, width: int, height: int) -> list:
        """Procedural sci-fi image tile: eclipse sphere over golden mountain horizon."""
        tile_h = max(1, math.ceil(height / 4))
        y0, y1 = tile * tile_h, min(height, (tile + 1) * tile_h)
        pixels = []
        phase = frame * 0.11
        cx, cy = width * (0.5 + 0.025 * math.sin(phase)), height * 0.40
        radius = min(width, height) * 0.22
        for y in range(y0, y1):
            for x in range(width):
                sky = max(0.0, 1.0 - y / max(1, height))
                horizon = height * (0.69 + 0.025 * math.sin(x * 0.035 + phase))
                d = math.hypot(x - cx, y - cy)
                glow = max(0.0, 1.0 - abs(d - radius) / max(1.0, radius * 0.22))
                sphere = d < radius
                fissure = (y > horizon and
                           abs(math.sin(x * 0.09 + y * 0.055 + phase)) > 0.994)
                r = int(min(255, 4 + 16 * sky + 170 * glow + (220 if fissure else 0)))
                g = int(min(255, 8 + 24 * sky + 105 * glow + (145 if fissure else 0)))
                b = int(min(255, 20 + 48 * sky + 18 * glow))
                if sphere:
                    r, g, b = 3, 4, 9
                if y > horizon:
                    ridge = 0.5 + 0.5 * math.sin(x * 0.025 + phase)
                    r, g, b = int(9 + 17 * ridge), int(8 + 10 * ridge), 18
                pixels.append((r, g, b))
        return {"y0": y0, "y1": y1, "pixels": pixels}

    def render_frames(self, out: Path, width: int, height: int, frames: int, fps: int) -> list[str]:
        if not self.booted:
            raise RuntimeError("Virtual chip is not booted")
        out.mkdir(parents=True, exist_ok=True)
        outputs = []
        for frame in range(frames):
            jobs = []
            with ThreadPoolExecutor(max_workers=len(self.cores)) as pool:
                for tile in range(4):
                    core = self.cores[tile % len(self.cores)]
                    program = [("LOAD", "R0", frame), ("LOAD", "R1", tile),
                               ("RENDER_TILE", frame, tile, width, height), ("HALT",)]
                    jobs.append(pool.submit(self.execute, core, program))
                for job in as_completed(jobs):
                    job.result()
            rows = [None] * height
            for tile in range(4):
                data = self.memory.read(f"frame:{frame}:tile:{tile}")
                for local_y, y in enumerate(range(data["y0"], data["y1"])):
                    start = local_y * width
                    rows[y] = data["pixels"][start:start + width]
            path = out / f"frame_{frame:04d}.ppm"
            with path.open("wb") as f:
                f.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
                for row in rows:
                    f.write(bytes(channel for pixel in row for channel in pixel))
            outputs.append(str(path))
        return outputs

    def status(self) -> dict:
        return {
            "processor": "NEXUS OMEGA VIRTUAL CHIP",
            "state": "ONLINE" if self.booted else "OFFLINE",
            "isa": sorted(self.ISA),
            "virtual_cores": len(self.cores),
            "cores": [{"id": c.core_id, "state": c.state, "retired": c.retired,
                       "cycles": c.cycles} for c in self.cores],
            "instructions_retired": self._retired,
            "faults": self._faults,
            "virtual_memory": self.memory.stats(),
            "host_execution_layer": {
                "platform": platform.platform(),
                "logical_cpu_count": os.cpu_count(),
                "note": "The host executes this emulator; virtual cores are software contexts, not physical cores."
            },
            "trace": self.trace,
        }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cores", type=int, default=4)
    p.add_argument("--memory-mb", type=int, default=64)
    p.add_argument("--width", type=int, default=180)
    p.add_argument("--height", type=int, default=320)
    p.add_argument("--frames", type=int, default=12)
    p.add_argument("--fps", type=int, default=12)
    p.add_argument("--out", type=Path, default=Path("NEXUS_VIRTUAL_CHIP_OUTPUT"))
    args = p.parse_args()
    if not (16 <= args.width <= 640 and 16 <= args.height <= 640 and
            1 <= args.frames <= 120 and 1 <= args.fps <= 60):
        p.error("Render settings outside safe prototype limits.")
    chip = NEXUSVirtualChip(args.cores, args.memory_mb)
    boot = chip.boot()
    started = time.perf_counter()
    files = chip.render_frames(args.out, args.width, args.height, args.frames, args.fps)
    elapsed = time.perf_counter() - started
    report = chip.status()
    report.update({"render_seconds": round(elapsed, 3), "fps_target": args.fps,
                   "frames_written": len(files), "frame_files": files,
                   "output_note": "PPM image sequence. MP4 encoding is a separate optional host tool step."})
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "nexus_chip_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"boot": boot["state"], "final_state": report["state"],
                      "frames_written": len(files), "instructions_retired": report["instructions_retired"],
                      "render_seconds": report["render_seconds"], "output": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
