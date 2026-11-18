"""NEXUS Horizon: truthful hardware discovery and capability registry.

Discovery reports hardware visible to this process. It never converts virtual
lane counts into compute capacity. Optional accelerator backends are reported
only when their runtime is installed and the device is visible.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
import os
import platform
from typing import Any


@dataclass(frozen=True)
class DeviceInfo:
    device_id: str
    kind: str
    name: str
    available: bool
    execution_backend: str
    capabilities: tuple[str, ...]
    memory_bytes: int | None = None
    notes: str = ""


def _host_memory_bytes() -> int | None:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        value = int(pages) * int(page_size)
        return value if value > 0 else None
    except (AttributeError, OSError, ValueError):
        return None


def discover_devices() -> list[DeviceInfo]:
    """Return detected host devices; optional frameworks are probed safely."""
    devices = [DeviceInfo(
        device_id="host-cpu-0",
        kind="CPU",
        name=platform.processor() or platform.machine() or "Host CPU",
        available=True,
        execution_backend="python",
        capabilities=("general", "control", "preprocess"),
        memory_bytes=_host_memory_bytes(),
        notes=f"logical_processors={os.cpu_count() or 1}; host CPU execution",
    )]

    if importlib.util.find_spec("torch") is None:
        devices.append(DeviceInfo(
            device_id="torch-accelerator-runtime",
            kind="GPU",
            name="PyTorch accelerator runtime not installed",
            available=False,
            execution_backend="none",
            capabilities=(),
            notes="Install a compatible framework and vendor driver to probe accelerators.",
        ))
        return devices

    try:
        import torch  # type: ignore
        if torch.cuda.is_available():
            count = torch.cuda.device_count()
            for index in range(count):
                props = torch.cuda.get_device_properties(index)
                devices.append(DeviceInfo(
                    device_id=f"torch-cuda-{index}",
                    kind="GPU",
                    name=str(props.name),
                    available=True,
                    execution_backend="pytorch-cuda",
                    capabilities=("tensor", "general", "raster_candidate"),
                    memory_bytes=int(props.total_memory),
                    notes="CUDA-visible device; workload support depends on installed kernels.",
                ))
        else:
            devices.append(DeviceInfo(
                device_id="torch-cuda-runtime",
                kind="GPU",
                name="PyTorch installed; no CUDA GPU visible",
                available=False,
                execution_backend="none",
                capabilities=(),
                notes="No CUDA device detected by this process.",
            ))
    except Exception as exc:
        devices.append(DeviceInfo(
            device_id="torch-probe-error",
            kind="GPU",
            name="Accelerator probe failed",
            available=False,
            execution_backend="none",
            capabilities=(),
            notes=f"{type(exc).__name__}: {exc}",
        ))
    return devices


def inventory() -> dict[str, Any]:
    devices = discover_devices()
    return {
        "system": {"platform": platform.platform(), "python": platform.python_version()},
        "device_count": len(devices),
        "available_device_count": sum(d.available for d in devices),
        "devices": [asdict(d) for d in devices],
        "claims": {
            "virtual_lanes_are_physical_cores": False,
            "virtual_memory_is_allocated_ram": False,
            "performance_measured": False,
            "note": "Discovery is not a benchmark. Run workload benchmarks before comparing compute power.",
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(inventory(), indent=2))
