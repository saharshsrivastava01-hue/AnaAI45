"""NEXUS Horizon bounded capability scheduler.

Routes tasks only to discovered, available devices with registered executors.
This is a host-side scheduler, not a hardware accelerator or performance claim.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
import threading
import time
from typing import Any, Callable, Iterable

from nexus_horizon_runtime import DeviceInfo


@dataclass(frozen=True)
class WorkItem:
    task_id: str
    capability: str
    estimated_memory_bytes: int = 0
    preferred_kind: str | None = None


class HorizonScheduler:
    def __init__(self, devices: Iterable[DeviceInfo], max_workers: int = 4):
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        self.devices = [d for d in devices if d.available]
        if not self.devices:
            raise ValueError("No available devices were discovered")
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="nexus-horizon")
        self._executors: dict[str, Callable[[WorkItem], Any]] = {}
        self._active = {d.device_id: 0 for d in self.devices}
        self._completed = {d.device_id: 0 for d in self.devices}
        self._failed = {d.device_id: 0 for d in self.devices}
        self._runtime = {d.device_id: 0.0 for d in self.devices}
        self._lock = threading.Lock()
        self._closed = False

    def register_executor(self, device_id: str, executor: Callable[[WorkItem], Any]) -> None:
        if device_id not in self._active:
            raise KeyError(f"Device is not available: {device_id}")
        self._executors[device_id] = executor

    def choose_device(self, item: WorkItem) -> DeviceInfo:
        candidates = []
        with self._lock:
            for device in self.devices:
                if item.capability not in device.capabilities:
                    continue
                if item.preferred_kind and item.preferred_kind.lower() != device.kind.lower():
                    continue
                if device.memory_bytes is not None and item.estimated_memory_bytes > device.memory_bytes:
                    continue
                # Do not treat unknown memory as infinite; it is simply unverified.
                pressure = self._active[device.device_id]
                candidates.append(((pressure, device.kind != "GPU", device.device_id), device))
        if not candidates:
            raise RuntimeError(f"No discovered device satisfies capability {item.capability!r} and memory requirement")
        return min(candidates, key=lambda pair: pair[0])[1]

    def submit(self, item: WorkItem) -> Future:
        if self._closed:
            raise RuntimeError("Scheduler is shut down")
        device = self.choose_device(item)
        executor = self._executors.get(device.device_id)
        if executor is None:
            if device.execution_backend != "python" or device.kind != "CPU":
                raise RuntimeError(f"No executable backend registered for {device.device_id}")
            executor = lambda work: {"task_id": work.task_id, "backend": "python-cpu-reference"}
        with self._lock:
            self._active[device.device_id] += 1

        def run():
            start = time.perf_counter()
            try:
                result = executor(item)
                elapsed = time.perf_counter() - start
                with self._lock:
                    self._completed[device.device_id] += 1
                    self._runtime[device.device_id] += elapsed
                return {"task_id": item.task_id, "device_id": device.device_id,
                        "result": result, "runtime_seconds": elapsed}
            except Exception:
                with self._lock:
                    self._failed[device.device_id] += 1
                raise
            finally:
                with self._lock:
                    self._active[device.device_id] -= 1
        return self._pool.submit(run)

    def metrics(self) -> dict:
        with self._lock:
            return {
                "devices": [{"device_id": d.device_id, "kind": d.kind, "name": d.name,
                             "memory_bytes": d.memory_bytes, "capabilities": list(d.capabilities)}
                            for d in self.devices],
                "stats": {key: {"active": self._active[key], "completed": self._completed[key],
                                "failed": self._failed[key], "runtime_seconds": round(self._runtime[key], 6)}
                          for key in self._active},
                "virtual_lanes_used_as_compute": False,
            }

    def shutdown(self, wait: bool = True) -> None:
        self._closed = True
        self._pool.shutdown(wait=wait)
