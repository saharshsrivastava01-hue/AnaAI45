"""NEXUS-3000 heterogeneous virtual fabric runtime.

This is a software scheduler/orchestrator, not a source of physical compute.
It schedules tasks onto registered executors. Real GPU/TPU acceleration exists
only when a user supplies an executor backed by actual hardware and drivers.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class Device:
    name: str
    kind: str
    capacity: int = 1
    capabilities: frozenset[str] = frozenset()
    memory_bytes: int = 0
    executor: Callable[[dict[str, Any]], Any] | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("device name cannot be empty")
        if self.capacity < 1:
            raise ValueError("device capacity must be >= 1")
        if self.memory_bytes < 0:
            raise ValueError("memory_bytes cannot be negative")


@dataclass(frozen=True)
class Task:
    task_id: str
    operation: str
    payload: dict[str, Any] = field(default_factory=dict)
    required_capabilities: frozenset[str] = frozenset()
    estimated_memory_bytes: int = 0
    estimated_cost: float = 1.0
    affinity: str | None = None

    def __post_init__(self) -> None:
        if not self.task_id or not self.operation:
            raise ValueError("task_id and operation are required")
        if self.estimated_memory_bytes < 0 or self.estimated_cost < 0:
            raise ValueError("task estimates cannot be negative")


class FabricError(RuntimeError):
    pass


class VirtualSuperfabric:
    """Capability-aware scheduler with bounded real worker threads.

    'Virtual lanes' are scheduling identifiers; they are not CPU/GPU cores.
    Each Device.executor must perform work on the real resource it represents.
    """

    def __init__(self, max_workers: int = 8) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        self.max_workers = max_workers
        self._devices: dict[str, Device] = {}
        self._lock = Lock()
        self._loads: dict[str, int] = {}
        self._completed = 0
        self._failed = 0
        self._submitted = 0
        self._latencies: list[float] = []

    def register(self, device: Device) -> None:
        if device.executor is None:
            raise ValueError(f"{device.name} needs an executor")
        with self._lock:
            if device.name in self._devices:
                raise ValueError(f"device already registered: {device.name}")
            self._devices[device.name] = device
            self._loads[device.name] = 0

    def devices(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {"name": d.name, "kind": d.kind, "capacity": d.capacity,
                 "capabilities": sorted(d.capabilities),
                 "memory_bytes": d.memory_bytes, "active_slots": self._loads[d.name]}
                for d in self._devices.values()
            ]

    def _choose(self, task: Task) -> Device:
        candidates = []
        with self._lock:
            for device in self._devices.values():
                if not task.required_capabilities.issubset(device.capabilities):
                    continue
                if device.memory_bytes and task.estimated_memory_bytes > device.memory_bytes:
                    continue
                active = self._loads[device.name]
                # Capacity is a scheduling weight, not a hard physical-core count.
                # ThreadPoolExecutor enforces the actual local concurrency limit.
                # Prefer affinity, then lower normalized load, then lower estimated
                # cost for this operation. This is a heuristic, not measured FLOPS.
                affinity_penalty = 0 if task.affinity == device.name else 1
                normalized_load = active / min(device.capacity, self.max_workers)
                score = (affinity_penalty, normalized_load, task.estimated_cost, device.name)
                candidates.append((score, device))
            if not candidates:
                raise FabricError(f"no eligible device for task {task.task_id}")
            _, selected = min(candidates, key=lambda item: item[0])
            self._loads[selected.name] += 1
            self._submitted += 1
            return selected

    def _release(self, device: Device, started: float, succeeded: bool) -> None:
        with self._lock:
            self._loads[device.name] -= 1
            self._latencies.append(monotonic() - started)
            if succeeded:
                self._completed += 1
            else:
                self._failed += 1

    def run(self, tasks: Iterable[Task]) -> dict[str, Any]:
        task_list = list(tasks)
        ids = [task.task_id for task in task_list]
        if len(ids) != len(set(ids)):
            raise ValueError("task_id values must be unique within a run")
        results: dict[str, Any] = {}
        errors: dict[str, str] = {}
        if not task_list:
            return {"results": results, "errors": errors, "metrics": self.metrics()}

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures: dict[Future[Any], tuple[Task, Device, float]] = {}
            for task in task_list:
                device = self._choose(task)
                started = monotonic()
                future = pool.submit(device.executor, {
                    "task_id": task.task_id, "operation": task.operation,
                    "payload": task.payload, "device": device.name,
                    "device_kind": device.kind,
                })
                futures[future] = (task, device, started)
            for future in as_completed(futures):
                task, device, started = futures[future]
                try:
                    results[task.task_id] = future.result()
                    self._release(device, started, True)
                except Exception as exc:  # surfaced per task; other tasks continue
                    errors[task.task_id] = f"{type(exc).__name__}: {exc}"
                    self._release(device, started, False)

        return {"results": results, "errors": errors, "metrics": self.metrics()}

    def metrics(self) -> dict[str, Any]:
        with self._lock:
            avg_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
            return {
                "registered_devices": len(self._devices),
                "logical_capacity_slots": sum(min(d.capacity, self.max_workers) for d in self._devices.values()),
                "runtime_worker_limit": self.max_workers,
                "submitted": self._submitted,
                "completed": self._completed,
                "failed": self._failed,
                "average_task_latency_seconds": round(avg_latency, 6),
                "active_slots": dict(self._loads),
                "compute_power_claim": "not inferred; benchmark real hardware executors",
            }


def demo() -> dict[str, Any]:
    """Run a tiny CPU-backed demonstration; no GPU/TPU is implied."""
    def cpu_echo(command: dict[str, Any]) -> dict[str, Any]:
        return {"device": command["device"], "operation": command["operation"],
                "value": command["payload"].get("value")}

    fabric = VirtualSuperfabric(max_workers=4)
    fabric.register(Device("cpu-demo", "CPU", capacity=4,
                           capabilities=frozenset({"general", "preprocess"}),
                           executor=cpu_echo))
    tasks = [Task(f"demo-{i}", "echo", {"value": i}, frozenset({"general"}))
             for i in range(4)]
    return fabric.run(tasks)


if __name__ == "__main__":
    import json
    print(json.dumps(demo(), indent=2))
