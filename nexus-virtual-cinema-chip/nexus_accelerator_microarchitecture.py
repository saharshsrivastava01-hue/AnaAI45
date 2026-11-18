"""NEXUS OMEGA accelerator microarchitecture model.

Executable functional model of SIMT warps, block scheduling, register files,
shared memory, cache-line accounting and a cycle-stepped systolic MAC array.
This is an architectural simulator: cycles/bandwidth are modelled, not measured
silicon performance. Host Python executes the simulator.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import OrderedDict
from typing import Callable, Sequence
import math
import time


@dataclass
class Warp:
    warp_id: int
    lane_count: int
    pc: int = 0
    active_mask: int = 0
    state: str = "READY"
    registers: list[dict[str, float]] = field(default_factory=list)

    def __post_init__(self):
        self.active_mask = (1 << self.lane_count) - 1
        self.registers = [dict() for _ in range(self.lane_count)]


class SIMTCore:
    """SIMT core model with warp issue, predication and per-lane registers."""
    def __init__(self, warp_width=32, resident_warps=8):
        if warp_width not in (8, 16, 32, 64) or resident_warps < 1:
            raise ValueError("unsupported warp geometry")
        self.warp_width = warp_width
        self.resident_warps = resident_warps
        self.warps: list[Warp] = []
        self.issued = 0
        self.retired = 0
        self.cycles = 0

    def load_warps(self, lane_values: Sequence[float]):
        self.warps.clear()
        for start in range(0, len(lane_values), self.warp_width):
            values = lane_values[start:start + self.warp_width]
            w = Warp(len(self.warps), len(values))
            for lane, value in enumerate(values):
                w.registers[lane]["R0"] = float(value)
            self.warps.append(w)
        return len(self.warps)

    def issue(self, opcode: str, dst: str, src: str, scalar: float,
              predicate: Callable[[int, float], bool] | None = None):
        """Issue one instruction to each resident warp in round-robin order."""
        issued_now = 0
        for warp in self.warps:
            if warp.state != "READY":
                continue
            warp.state = "ISSUED"
            for lane in range(warp.lane_count):
                if not (warp.active_mask >> lane) & 1:
                    continue
                regs = warp.registers[lane]
                x = regs.get(src, 0.0)
                if predicate and not predicate(lane, x):
                    continue
                if opcode == "FADD":
                    regs[dst] = x + scalar
                elif opcode == "FMUL":
                    regs[dst] = x * scalar
                elif opcode == "FMA":
                    regs[dst] = x * scalar + regs.get("R1", 0.0)
                elif opcode == "SIN":
                    regs[dst] = math.sin(x)
                else:
                    warp.state = "FAULT"
                    raise ValueError(f"unsupported SIMT opcode {opcode}")
            warp.pc += 1
            warp.state = "READY"
            issued_now += 1
        self.issued += issued_now
        self.retired += issued_now
        self.cycles += max(1, math.ceil(issued_now / self.resident_warps))
        return issued_now

    def collect(self, register: str):
        return [w.registers[i].get(register, 0.0)
                for w in self.warps for i in range(w.lane_count)]


class CacheModel:
    """Set-associative LRU cache model; no real host cache control."""
    def __init__(self, capacity_bytes=64 * 1024, line_bytes=128, ways=4):
        if min(capacity_bytes, line_bytes, ways) <= 0:
            raise ValueError("cache parameters must be positive")
        self.capacity = capacity_bytes
        self.line_bytes = line_bytes
        self.ways = ways
        self.set_count = max(1, capacity_bytes // (line_bytes * ways))
        self.sets = [OrderedDict() for _ in range(self.set_count)]
        self.hits = self.misses = 0

    def access(self, address: int):
        if address < 0:
            raise ValueError("address must be non-negative")
        line = address // self.line_bytes
        set_id = line % self.set_count
        cache_set = self.sets[set_id]
        if line in cache_set:
            self.hits += 1
            cache_set.move_to_end(line)
            return True
        self.misses += 1
        cache_set[line] = None
        if len(cache_set) > self.ways:
            cache_set.popitem(last=False)
        return False

    def report(self):
        total = self.hits + self.misses
        return {"capacity_bytes": self.capacity, "line_bytes": self.line_bytes,
                "ways": self.ways, "hits": self.hits, "misses": self.misses,
                "hit_rate": self.hits / total if total else None}


class SharedMemory:
    """Block-local scratchpad model with bounds checking and bank conflicts."""
    def __init__(self, size_bytes=48 * 1024, banks=32, word_bytes=4):
        self.data = bytearray(size_bytes)
        self.banks = banks
        self.word_bytes = word_bytes
        self.accesses = 0
        self.bank_conflicts = 0

    def store_u32(self, address, value):
        if address < 0 or address + 4 > len(self.data):
            raise MemoryError("shared-memory address out of range")
        self.data[address:address+4] = int(value & 0xffffffff).to_bytes(4, "little")

    def load_u32(self, address):
        if address < 0 or address + 4 > len(self.data):
            raise MemoryError("shared-memory address out of range")
        return int.from_bytes(self.data[address:address+4], "little")

    def account_warp_access(self, word_addresses):
        banks = [((a * self.word_bytes) // self.word_bytes) % self.banks
                 for a in word_addresses]
        self.accesses += len(banks)
        self.bank_conflicts += len(banks) - len(set(banks))
        return len(banks) - len(set(banks))


class SystolicArray:
    """Cycle-stepped output-stationary integer/float MAC array model."""
    def __init__(self, rows=16, cols=16):
        if rows < 1 or cols < 1:
            raise ValueError("array dimensions must be positive")
        self.rows, self.cols = rows, cols
        self.mac_count = 0
        self.cycles = 0

    def matmul(self, a, b):
        m, k = len(a), len(a[0]) if a else 0
        kb, n = len(b), len(b[0]) if b else 0
        if not m or not k or not kb or not n or k != kb:
            raise ValueError("matrix dimensions are incompatible")
        out = [[0.0 for _ in range(n)] for _ in range(m)]
        # Tile traversal models feeding a physical systolic mesh.
        for mi in range(0, m, self.rows):
            for nj in range(0, n, self.cols):
                for kk in range(k):
                    for i in range(mi, min(mi + self.rows, m)):
                        for j in range(nj, min(nj + self.cols, n)):
                            out[i][j] += float(a[i][kk]) * float(b[kk][j])
                            self.mac_count += 1
                    self.cycles += 1
        return out

    def report(self):
        return {"array_shape": [self.rows, self.cols], "macs": self.mac_count,
                "modelled_feed_cycles": self.cycles,
                "note": "Cycle model only; not a measured hardware clock or throughput."}


class NEXUSAcceleratorModel:
    def __init__(self, warp_width=32, resident_warps=8,
                 cache_kb=64, shared_kb=48, systolic_rows=16, systolic_cols=16):
        self.simt = SIMTCore(warp_width, resident_warps)
        self.l1 = CacheModel(cache_kb * 1024)
        self.shared = SharedMemory(shared_kb * 1024)
        self.tensor = SystolicArray(systolic_rows, systolic_cols)
        self.started = None

    def run_simt_demo(self, values):
        self.simt.load_warps(values)
        self.simt.issue("FMUL", "R2", "R0", 2.0)
        self.simt.issue("FADD", "R3", "R2", 1.0)
        return self.simt.collect("R3")

    def run_tensor_demo(self, n=16):
        a = [[float(i + j) for j in range(n)] for i in range(n)]
        b = [[float(i == j) for j in range(n)] for i in range(n)]
        return self.tensor.matmul(a, b)

    def report(self):
        return {
            "architecture": "NEXUS OMEGA SIMT + Systolic Accelerator Model",
            "simt": {"warp_width": self.simt.warp_width,
                     "resident_warps": self.simt.resident_warps,
                     "warps_created": len(self.simt.warps),
                     "instructions_issued": self.simt.issued,
                     "instructions_retired": self.simt.retired,
                     "modelled_cycles": self.simt.cycles},
            "l1_cache_model": self.l1.report(),
            "shared_memory_model": {"capacity_bytes": len(self.shared.data),
                                    "banks": self.shared.banks,
                                    "accesses": self.shared.accesses,
                                    "bank_conflicts": self.shared.bank_conflicts},
            "systolic_array": self.tensor.report(),
            "truth": "Functional architectural simulation. Host software executes it; it does not reproduce physical GPU/TPU speed, clocking, power, bandwidth, drivers or silicon."
        }


def main():
    import argparse, json
    p = argparse.ArgumentParser()
    p.add_argument("--lanes", type=int, default=1024)
    p.add_argument("--warp-width", type=int, default=32)
    p.add_argument("--matrix-size", type=int, default=16)
    p.add_argument("--output", default="nexus_accelerator_microarchitecture.json")
    a = p.parse_args()
    if a.lanes < 1 or a.lanes > 1_000_000 or a.matrix_size < 1 or a.matrix_size > 128:
        p.error("lanes must be 1..1000000 and matrix-size 1..128")
    model = NEXUSAcceleratorModel(warp_width=a.warp_width)
    values = [float(i) for i in range(a.lanes)]
    start = time.perf_counter()
    simt_result = model.run_simt_demo(values)
    model.run_tensor_demo(a.matrix_size)
    elapsed = time.perf_counter() - start
    model.report()["simt"]["sample_outputs"] = simt_result[:8]
    report = model.report()
    report["host_execution_seconds"] = elapsed
    with open(a.output, "w", encoding="utf-8") as f:
        import json
        json.dump(report, f, indent=2)
        f.write("\n")
    print(json.dumps({"output": a.output, "lanes_tested": a.lanes,
                      "matrix_size": a.matrix_size, "elapsed_seconds": elapsed,
                      "status": "simulation_complete"}, indent=2))


if __name__ == "__main__":
    main()
