"""NEXUS-3000 5D Virtual Supercomputer reference simulator.

Five scheduling dimensions:
  1. compute capability / estimated compute units
  2. memory capacity and task working set
  3. network locality / transfer estimate
  4. time: deadline, priority, queue delay
  5. spatial topology: node, rack, region placement

These are scheduling abstractions. A worker only performs real GPU/TPU
computations when its executor is connected to actual hardware and drivers.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from hashlib import sha256
import json
from threading import Lock
from time import monotonic
from typing import Any, Callable


@dataclass(frozen=True)
class ComputeNode:
    node_id: str
    device: str
    capabilities: frozenset[str]
    compute_units: float
    memory_bytes: int
    network_gbps: float
    region: str
    rack: str
    executor: Callable[[dict[str, Any]], Any] = field(compare=False, repr=False)

    def __post_init__(self):
        if not self.node_id or not self.region or not self.rack:
            raise ValueError("node_id, region and rack are required")
        if self.compute_units <= 0 or self.memory_bytes < 0 or self.network_gbps < 0:
            raise ValueError("invalid node resource metadata")


@dataclass(frozen=True)
class ComputeJob:
    job_id: str
    operation: str
    payload: dict[str, Any]
    capability: str = "general"
    estimated_compute: float = 1.0
    memory_bytes: int = 0
    input_bytes: int = 0
    region: str | None = None
    rack: str | None = None
    priority: int = 0
    deadline_seconds: float | None = None
    cacheable: bool = False

    def __post_init__(self):
        if not self.job_id or not self.operation:
            raise ValueError("job_id and operation are required")
        if min(self.estimated_compute, self.memory_bytes, self.input_bytes) < 0:
            raise ValueError("job resource estimates cannot be negative")
        if self.deadline_seconds is not None and self.deadline_seconds <= 0:
            raise ValueError("deadline_seconds must be positive")


class NEXUS5DSupercomputer:
    """Bounded concurrent scheduler with transparent placement scoring."""

    def __init__(self, max_workers: int = 8):
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        self.max_workers = max_workers
        self._nodes: dict[str, ComputeNode] = {}
        self._cache: dict[str, Any] = {}
        self._lock = Lock()
        self._metrics = {
            "jobs_submitted": 0, "jobs_completed": 0, "jobs_failed": 0,
            "cache_hits": 0, "deadline_misses": 0,
        }

    def register_node(self, node: ComputeNode):
        with self._lock:
            if node.node_id in self._nodes:
                raise ValueError(f"duplicate node {node.node_id}")
            self._nodes[node.node_id] = node

    @staticmethod
    def _key(job: ComputeJob) -> str:
        raw = json.dumps(
            {"operation": job.operation, "payload": job.payload,
             "capability": job.capability},
            sort_keys=True, separators=(",", ":"), default=str,
        )
        return sha256(raw.encode()).hexdigest()

    def _rank(self, job: ComputeJob) -> list[tuple[tuple[Any, ...], ComputeNode]]:
        ranked = []
        for node in self._nodes.values():
            if job.capability not in node.capabilities or job.memory_bytes > node.memory_bytes:
                continue
            # Estimate input-transfer time in seconds. This is a planning estimate,
            # not measured network throughput.
            transfer = (job.input_bytes * 8 / (node.network_gbps * 1e9)
                        if node.network_gbps > 0 else (0 if job.input_bytes == 0 else float("inf")))
            compute_time = job.estimated_compute / node.compute_units
            region_penalty = 0 if job.region and job.region == node.region else 1
            rack_penalty = 0 if job.rack and job.rack == node.rack else 1
            # Score combines locality, estimated compute and transfer time.
            score = (region_penalty, rack_penalty, compute_time + transfer, node.node_id)
            ranked.append((score, node))
        return sorted(ranked, key=lambda pair: pair[0])

    def plan(self, jobs: list[ComputeJob]) -> list[dict[str, Any]]:
        plan = []
        for job in sorted(jobs, key=lambda j: (-j.priority, j.job_id)):
            if job.cacheable and self._key(job) in self._cache:
                plan.append({"job_id": job.job_id, "node": "CACHE", "reason": "cached deterministic result"})
                continue
            ranked = self._rank(job)
            if not ranked:
                plan.append({"job_id": job.job_id, "node": None, "error": "no compatible node"})
                continue
            score, node = ranked[0]
            plan.append({
                "job_id": job.job_id, "node": node.node_id, "device": node.device,
                "estimated_score_seconds": round(score[2], 9),
                "placement_dimensions": ["compute", "memory", "network", "time", "spatial"],
            })
        return plan

    def run(self, jobs: list[ComputeJob]) -> dict[str, Any]:
        ids = [job.job_id for job in jobs]
        if len(ids) != len(set(ids)):
            raise ValueError("job IDs must be unique")
        ordered = sorted(jobs, key=lambda j: (-j.priority, j.job_id))
        plan_by_id = {entry["job_id"]: entry for entry in self.plan(ordered)}
        results, errors = {}, {}
        start_all = monotonic()
        self._metrics["jobs_submitted"] += len(ordered)

        def execute(job: ComputeJob, node: ComputeNode):
            started = monotonic()
            output = node.executor({
                "job_id": job.job_id, "operation": job.operation,
                "payload": job.payload, "device": node.device,
                "node_id": node.node_id,
            })
            elapsed = monotonic() - started
            return output, elapsed

        futures = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            for job in ordered:
                entry = plan_by_id[job.job_id]
                if entry.get("node") == "CACHE":
                    results[job.job_id] = self._cache[self._key(job)]
                    self._metrics["cache_hits"] += 1
                    continue
                if entry.get("node") is None:
                    errors[job.job_id] = entry["error"]
                    self._metrics["jobs_failed"] += 1
                    continue
                node = self._nodes[entry["node"]]
                futures[pool.submit(execute, job, node)] = (job, node)

            for future in as_completed(futures):
                job, node = futures[future]
                try:
                    output, elapsed = future.result()
                    results[job.job_id] = output
                    if job.cacheable:
                        self._cache[self._key(job)] = output
                    if job.deadline_seconds is not None and elapsed > job.deadline_seconds:
                        self._metrics["deadline_misses"] += 1
                    self._metrics["jobs_completed"] += 1
                except Exception as exc:
                    errors[job.job_id] = f"{type(exc).__name__}: {exc}"
                    self._metrics["jobs_failed"] += 1

        return {
            "results": results, "errors": errors,
            "plan": list(plan_by_id.values()),
            "metrics": {**self._metrics, "registered_nodes": len(self._nodes),
                        "max_concurrent_workers": self.max_workers,
                        "wall_time_seconds": round(monotonic() - start_all, 6),
                        "compute_power": "not inferred; benchmark attached hardware"},
        }


def demo():
    def cpu_executor(command):
        return {"node": command["node_id"],
                "value": command["payload"].get("value", 0) ** 2}

    cluster = NEXUS5DSupercomputer(max_workers=4)
    cluster.register_node(ComputeNode(
        node_id="cpu-lab-a", device="CPU",
        capabilities=frozenset({"general", "preprocess"}),
        compute_units=4, memory_bytes=8 * 1024**3,
        network_gbps=1.0, region="local", rack="desk",
        executor=cpu_executor,
    ))
    jobs = [
        ComputeJob(f"job-{i}", "square", {"value": i},
                   estimated_compute=2, memory_bytes=1024,
                   input_bytes=64, region="local", rack="desk",
                   priority=10-i, cacheable=True)
        for i in range(4)
    ]
    return cluster.run(jobs)


if __name__ == "__main__":
    print(json.dumps(demo(), indent=2))
