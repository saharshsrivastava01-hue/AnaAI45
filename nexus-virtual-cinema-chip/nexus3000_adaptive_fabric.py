"""NEXUS-3000 Adaptive Fabric v2: locality-aware, cache-aware task planner.

This module adds a deterministic planning layer above real worker adapters.
It does not emulate physical FLOPS or manufacture hardware capacity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from threading import Lock
from time import monotonic
from typing import Any, Callable


@dataclass(frozen=True)
class Worker:
    worker_id: str
    device_type: str
    capabilities: frozenset[str]
    memory_bytes: int
    max_inflight: int = 1
    data_regions: frozenset[str] = frozenset()
    executor: Callable[[dict[str, Any]], Any] | None = field(default=None, compare=False, repr=False)

    def __post_init__(self):
        if not self.worker_id or self.memory_bytes < 0 or self.max_inflight < 1:
            raise ValueError("invalid worker metadata")


@dataclass(frozen=True)
class WorkItem:
    work_id: str
    operation: str
    inputs: dict[str, Any]
    needs: frozenset[str] = frozenset()
    memory_bytes: int = 0
    data_region: str | None = None
    deterministic: bool = True
    priority: int = 0

    def __post_init__(self):
        if not self.work_id or not self.operation or self.memory_bytes < 0:
            raise ValueError("invalid work item")


class AdaptiveFabric:
    """Small orchestration core with locality scoring and deterministic cache."""

    def __init__(self, max_workers: int = 8):
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        self.max_workers = max_workers
        self._workers: dict[str, Worker] = {}
        self._inflight: dict[str, int] = {}
        self._cache: dict[str, Any] = {}
        self._lock = Lock()
        self._metrics = {"planned": 0, "cache_hits": 0, "completed": 0, "failed": 0}

    def register_worker(self, worker: Worker):
        if worker.executor is None:
            raise ValueError("worker must provide a real executor adapter")
        with self._lock:
            if worker.worker_id in self._workers:
                raise ValueError(f"duplicate worker: {worker.worker_id}")
            self._workers[worker.worker_id] = worker
            self._inflight[worker.worker_id] = 0

    @staticmethod
    def _cache_key(item: WorkItem) -> str:
        canonical = json.dumps(
            {"operation": item.operation, "inputs": item.inputs,
             "needs": sorted(item.needs), "memory_bytes": item.memory_bytes},
            sort_keys=True, separators=(",", ":"), default=str,
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def _select(self, item: WorkItem) -> Worker:
        options = []
        with self._lock:
            for worker in self._workers.values():
                if not item.needs.issubset(worker.capabilities):
                    continue
                if item.memory_bytes > worker.memory_bytes:
                    continue
                if self._inflight[worker.worker_id] >= min(worker.max_inflight, self.max_workers):
                    continue
                locality_penalty = 0 if item.data_region and item.data_region in worker.data_regions else 1
                load_ratio = self._inflight[worker.worker_id] / min(worker.max_inflight, self.max_workers)
                # Locality first, then load; deterministic tie break.
                options.append(((locality_penalty, load_ratio, worker.worker_id), worker))
            if not options:
                raise RuntimeError(f"no eligible worker for {item.work_id}")
            worker = min(options, key=lambda pair: pair[0])[1]
            self._inflight[worker.worker_id] += 1
            return worker

    def run(self, items: list[WorkItem]) -> dict[str, Any]:
        if len({x.work_id for x in items}) != len(items):
            raise ValueError("work IDs must be unique")
        ordered = sorted(items, key=lambda x: (-x.priority, x.work_id))
        results, errors, plan = {}, {}, []
        for item in ordered:
            key = self._cache_key(item)
            if item.deterministic and key in self._cache:
                results[item.work_id] = self._cache[key]
                self._metrics["cache_hits"] += 1
                plan.append({"work_id": item.work_id, "placement": "cache", "reason": "deterministic result reused"})
                continue
            worker = self._select(item)
            plan.append({"work_id": item.work_id, "placement": worker.worker_id,
                         "device_type": worker.device_type,
                         "reason": "capability + memory + locality + load"})
            self._metrics["planned"] += 1
            started = monotonic()
            try:
                result = worker.executor({
                    "work_id": item.work_id, "operation": item.operation,
                    "inputs": item.inputs, "device_type": worker.device_type,
                })
                results[item.work_id] = result
                if item.deterministic:
                    self._cache[key] = result
                self._metrics["completed"] += 1
            except Exception as exc:
                errors[item.work_id] = f"{type(exc).__name__}: {exc}"
                self._metrics["failed"] += 1
            finally:
                with self._lock:
                    self._inflight[worker.worker_id] -= 1
            plan[-1]["elapsed_seconds"] = round(monotonic() - started, 6)
        return {"results": results, "errors": errors, "plan": plan, "metrics": self.metrics()}

    def metrics(self):
        return {**self._metrics, "registered_workers": len(self._workers),
                "cache_entries": len(self._cache), "runtime_worker_limit": self.max_workers,
                "physical_compute_claim": "measured only by attached hardware adapters"}


def demo():
    def cpu_worker(job):
        return {"backend": "CPU demo", "value": job["inputs"].get("value", 0) * 2}

    fabric = AdaptiveFabric(max_workers=4)
    fabric.register_worker(Worker(
        worker_id="cpu-node-01", device_type="CPU",
        capabilities=frozenset({"general", "preprocess"}),
        memory_bytes=2 * 1024**3, max_inflight=4,
        data_regions=frozenset({"local"}), executor=cpu_worker,
    ))
    job = WorkItem("first", "double", {"value": 21}, frozenset({"general"}),
                   memory_bytes=1024, data_region="local", deterministic=True)
    return {"first_run": fabric.run([job]), "second_run": fabric.run([
        WorkItem("second", "double", {"value": 21}, frozenset({"general"}),
                 memory_bytes=1024, data_region="local", deterministic=True)
    ])}


if __name__ == "__main__":
    print(json.dumps(demo(), indent=2))
