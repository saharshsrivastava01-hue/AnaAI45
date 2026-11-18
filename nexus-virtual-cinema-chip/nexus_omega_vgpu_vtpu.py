"""NEXUS OMEGA VGPU/VTPU logical accelerator fabric.

Executable software reference implementation:
- GPU-like vector kernels and TPU-like matrix/tensor kernels
- virtual device inventory, memory accounting, command queues and events
- CPU-backed execution via NumPy when installed, pure-Python fallback otherwise
- explicit distinction between logical accelerator units and physical hardware

This is a functional software runtime, not a physical GPU/TPU emulator at cycle,
ISA, driver, bandwidth, or performance fidelity. It does not create silicon.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, asdict
from enum import Enum
import math
import os
import platform
import threading
import time
from typing import Callable, Any


class EngineKind(str, Enum):
    VGPU = "vgpu"
    VTPU = "vtpu"


class DeviceState(str, Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    FAULT = "fault"


@dataclass
class VirtualAccelerator:
    device_id: str
    kind: str
    logical_units: int
    memory_capacity_bytes: int
    state: str = DeviceState.ONLINE.value
    operations_completed: int = 0
    bytes_allocated: int = 0


class VirtualBuffer:
    def __init__(self, size: int, owner: str):
        if size < 0:
            raise ValueError("buffer size cannot be negative")
        self.data = bytearray(size)
        self.owner = owner
        self.created_at = time.time()

    @property
    def nbytes(self):
        return len(self.data)


class NEXUSAcceleratorFabric:
    """GPU/TPU-style software API over host CPU execution.

    logical_gpu_units and logical_tpu_units are architectural configuration
    values only. The actual execution backend is the host CPU.
    """

    def __init__(self, logical_gpu_units: int = 1_000_000_000_000,
                 logical_tpu_units: int = 1_000_000_000_000,
                 virtual_memory_mb: int = 512, queues: int = 4):
        for label, value in (("logical_gpu_units", logical_gpu_units),
                             ("logical_tpu_units", logical_tpu_units)):
            if not isinstance(value, int) or value < 1:
                raise ValueError(f"{label} must be a positive integer")
        if not 1 <= virtual_memory_mb <= 4096:
            raise ValueError("virtual_memory_mb must be in 1..4096")
        if not 1 <= queues <= 64:
            raise ValueError("queues must be in 1..64")
        capacity = virtual_memory_mb * 1024 * 1024
        self.devices = {
            "NEXUS-VGPU-0": VirtualAccelerator(
                "NEXUS-VGPU-0", EngineKind.VGPU.value,
                logical_gpu_units, capacity),
            "NEXUS-VTPU-0": VirtualAccelerator(
                "NEXUS-VTPU-0", EngineKind.VTPU.value,
                logical_tpu_units, capacity),
        }
        self._pool = ThreadPoolExecutor(max_workers=queues,
                                        thread_name_prefix="nexus-accelerator-queue")
        self._lock = threading.RLock()
        self._futures: list[Future] = []
        self._buffers: list[VirtualBuffer] = []
        self._sequence = 0
        self._stats = {"vector_ops": 0, "tensor_ops": 0,
                       "bytes_processed": 0, "faults": 0}
        self._closed = False
        self._trace: list[dict] = []

    def _submit(self, device_id: str, op_name: str,
                fn: Callable[..., Any], *args) -> Future:
        with self._lock:
            if self._closed:
                raise RuntimeError("accelerator fabric is shut down")
            if device_id not in self.devices:
                raise KeyError(f"unknown virtual device: {device_id}")
            self._sequence += 1
            seq = self._sequence
            self.devices[device_id].state = DeviceState.BUSY.value
            self._trace.append({"seq": seq, "event": "DISPATCH",
                                "device": device_id, "op": op_name})
        def run():
            start = time.perf_counter()
            try:
                result, byte_count = fn(*args)
                elapsed = time.perf_counter() - start
                with self._lock:
                    d = self.devices[device_id]
                    d.operations_completed += 1
                    d.state = DeviceState.ONLINE.value
                    self._stats["bytes_processed"] += byte_count
                    if d.kind == EngineKind.VGPU.value:
                        self._stats["vector_ops"] += 1
                    else:
                        self._stats["tensor_ops"] += 1
                    self._trace.append({"seq": seq, "event": "COMPLETE",
                                        "seconds": round(elapsed, 6)})
                return {"sequence": seq, "device": device_id, "operation": op_name,
                        "elapsed_seconds": elapsed, "result": result}
            except Exception as exc:
                with self._lock:
                    self.devices[device_id].state = DeviceState.FAULT.value
                    self._stats["faults"] += 1
                    self._trace.append({"seq": seq, "event": "FAULT",
                                        "error": str(exc)})
                raise
        future = self._pool.submit(run)
        with self._lock:
            self._futures.append(future)
        return future

    @staticmethod
    def _vector_add(a, b):
        if len(a) != len(b):
            raise ValueError("vector lengths must match")
        try:
            import numpy as np
            out = (np.asarray(a) + np.asarray(b)).tolist()
        except ImportError:
            out = [x + y for x, y in zip(a, b)]
        return out, (len(a) + len(b) + len(out)) * 8

    @staticmethod
    def _vector_scale(a, scalar):
        try:
            import numpy as np
            out = (np.asarray(a) * scalar).tolist()
        except ImportError:
            out = [x * scalar for x in a]
        return out, (len(a) + len(out)) * 8

    @staticmethod
    def _matmul(a, b):
        if not a or not b or len(a[0]) != len(b):
            raise ValueError("invalid matrix dimensions")
        try:
            import numpy as np
            out = (np.asarray(a, dtype="float32") @
                   np.asarray(b, dtype="float32")).tolist()
        except ImportError:
            cols = list(zip(*b))
            out = [[sum(x * y for x, y in zip(row, col))
                    for col in cols] for row in a]
        count = len(a) * len(b[0])
        return out, (len(a) * len(a[0]) + len(b) * len(b[0]) + count) * 4

    def vector_add(self, a, b) -> Future:
        return self._submit("NEXUS-VGPU-0", "VECTOR_ADD",
                            self._vector_add, list(a), list(b))

    def vector_scale(self, a, scalar: float) -> Future:
        return self._submit("NEXUS-VGPU-0", "VECTOR_SCALE",
                            self._vector_scale, list(a), float(scalar))

    def matmul(self, a, b) -> Future:
        return self._submit("NEXUS-VTPU-0", "MATRIX_MULTIPLY",
                            self._matmul, a, b)

    def allocate(self, device_id: str, size_bytes: int) -> VirtualBuffer:
        with self._lock:
            if self._closed:
                raise RuntimeError("accelerator fabric is shut down")
            device = self.devices[device_id]
            if size_bytes < 0:
                raise ValueError("size_bytes cannot be negative")
            if device.bytes_allocated + size_bytes > device.memory_capacity_bytes:
                raise MemoryError("virtual device memory capacity exceeded")
            buf = VirtualBuffer(size_bytes, device_id)
            device.bytes_allocated += size_bytes
            self._buffers.append(buf)
            self._trace.append({"event": "ALLOC", "device": device_id,
                                "bytes": size_bytes})
            return buf

    def synchronize(self):
        with self._lock:
            pending = list(self._futures)
            self._futures.clear()
        return [future.result() for future in pending]

    def benchmark(self, size: int = 256):
        if not 1 <= size <= 2048:
            raise ValueError("benchmark size must be in 1..2048")
        a = [[float((i + j) % 7) for j in range(size)] for i in range(size)]
        b = [[float((i * 2 + j) % 5) for j in range(size)] for i in range(size)]
        start = time.perf_counter()
        result = self.matmul(a, b).result()
        elapsed = time.perf_counter() - start
        return {"size": size, "elapsed_seconds": elapsed,
                "backend": "host CPU (NumPy if installed, otherwise Python)",
                "theoretical_flops": 2 * size ** 3,
                "measured_flops_per_second": (2 * size ** 3 / elapsed) if elapsed else None,
                "checksum": sum(sum(row) for row in result["result"])}

    def report(self):
        with self._lock:
            return {
                "fabric": "NEXUS OMEGA VGPU/VTPU",
                "devices": {key: asdict(value) for key, value in self.devices.items()},
                "configured_logical_gpu_units": self.devices["NEXUS-VGPU-0"].logical_units,
                "configured_logical_tpu_units": self.devices["NEXUS-VTPU-0"].logical_units,
                "host": {"platform": platform.platform(),
                         "cpu_threads_reported": os.cpu_count() or 1},
                "backend": "host CPU software execution",
                "stats": dict(self._stats),
                "trace": self._trace[-100:],
                "truth": "Logical unit counts are virtual architecture labels, not physical GPU/TPU cores. This runtime does not emulate proprietary device ISA, cycle timing, bandwidth or performance exactly."
            }

    def close(self):
        if not self._closed:
            self.synchronize()
            self._pool.shutdown(wait=True)
            self._closed = True
            for device in self.devices.values():
                device.state = DeviceState.OFFLINE.value


def main():
    import argparse, json
    parser = argparse.ArgumentParser(description="NEXUS VGPU/VTPU runtime self-test")
    parser.add_argument("--units", type=int, default=1_000_000_000_000)
    parser.add_argument("--memory-mb", type=int, default=64)
    parser.add_argument("--benchmark-size", type=int, default=128)
    args = parser.parse_args()
    fabric = NEXUSAcceleratorFabric(args.units, args.units, args.memory_mb)
    try:
        v = fabric.vector_add([1, 2, 3], [4, 5, 6]).result()
        t = fabric.matmul([[1, 2], [3, 4]], [[5, 6], [7, 8]]).result()
        buf = fabric.allocate("NEXUS-VGPU-0", 4096)
        bench = fabric.benchmark(args.benchmark_size)
        fabric.synchronize()
        report = fabric.report()
        report["self_test"] = {"vector_add": v["result"],
                               "matrix_multiply": t["result"],
                               "allocated_buffer_bytes": buf.nbytes,
                               "benchmark": bench}
        print(json.dumps(report, indent=2))
    finally:
        fabric.close()


if __name__ == "__main__":
    main()
