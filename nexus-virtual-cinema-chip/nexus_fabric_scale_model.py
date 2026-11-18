"""NEXUS massively-parallel heterogeneous fabric scale model.

This is a topology/scheduling model, NOT trillions of physical CUDA/TPU cores.
It represents logical work lanes grouped into accelerator-inspired pools and
maps jobs only onto execution backends that are actually registered.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Dict, Iterable


@dataclass(frozen=True)
class Pool:
    name: str
    role: str
    logical_lanes: int
    physical_devices_required: bool
    backend: str


DEFAULT_POOLS = (
    Pool("NVIDIA_CUDA_STYLE", "general_parallel_gpu", 1_000_000_000_000, True, "cuda"),
    Pool("GOOGLE_TPU_STYLE", "tensor_matrix_ai", 500_000_000_000, True, "tpu"),
    Pool("META_AI_ACCELERATOR_STYLE", "training_inference", 250_000_000_000, True, "vendor"),
    Pool("NEXUS_RAY_STYLE", "ray_geometry", 100_000_000_000, True, "ray"),
    Pool("NEXUS_VECTOR_STYLE", "vector_signal_processing", 100_000_000_000, True, "vector"),
    Pool("NEXUS_CPU_STYLE", "control_serial_fallback", 10_000_000_000, True, "cpu"),
)


def build_topology(pools: Iterable[Pool] = DEFAULT_POOLS) -> dict:
    rows = [asdict(pool) for pool in pools]
    return {
        "architecture": "NEXUS_HETEROGENEOUS_FABRIC",
        "status": "logical_capacity_model_only",
        "physical_devices_allocated": 0,
        "measured_throughput": False,
        "logical_lanes_are_physical_cores": False,
        "pools": rows,
        "total_logical_lanes": sum(p["logical_lanes"] for p in rows),
        "execution_rule": (
            "A logical pool is not executable until a real device backend is "
            "detected, registered, and validated."
        ),
    }


def validate_topology(topology: dict) -> None:
    if topology["physical_devices_allocated"] != 0:
        raise ValueError("This model must not claim physical devices were allocated")
    if topology["logical_lanes_are_physical_cores"]:
        raise ValueError("Logical lane counts must never be labelled physical cores")
    names = [p["name"] for p in topology["pools"]]
    if len(names) != len(set(names)):
        raise ValueError("Pool names must be unique")
    if any(p["logical_lanes"] <= 0 for p in topology["pools"]):
        raise ValueError("Every pool must have a positive logical lane count")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology", action="store_true")
    args = parser.parse_args()
    topology = build_topology()
    validate_topology(topology)
    print(json.dumps(topology, indent=2))


if __name__ == "__main__":
    main()
