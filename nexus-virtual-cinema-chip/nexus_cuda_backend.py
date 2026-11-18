"""NEXUS CUDA backend prototype using PyTorch CUDA tensors.

This is an adapter to NVIDIA CUDA through an installed PyTorch build. It does
not implement CUDA itself. No GPU is emulated: CUDA mode requires a real,
visible NVIDIA GPU and compatible driver/runtime.
"""
from __future__ import annotations

import argparse
import json
import time
from typing import Any


def cuda_status() -> dict[str, Any]:
    try:
        import torch
    except ImportError:
        return {"available": False, "reason": "PyTorch is not installed"}
    if not torch.cuda.is_available():
        return {
            "available": False,
            "reason": "PyTorch cannot see a CUDA GPU; check NVIDIA driver and CUDA-enabled PyTorch",
            "torch_version": torch.__version__,
            "torch_cuda_build": torch.version.cuda,
        }
    props = torch.cuda.get_device_properties(0)
    return {
        "available": True,
        "device_count": torch.cuda.device_count(),
        "device_name": props.name,
        "total_memory_bytes": props.total_memory,
        "compute_capability": list(torch.cuda.get_device_capability(0)),
        "torch_version": torch.__version__,
        "torch_cuda_build": torch.version.cuda,
    }


def run_matmul_benchmark(size: int = 1024, repeats: int = 5, dtype_name: str = "float32") -> dict[str, Any]:
    if size < 16 or size > 8192:
        raise ValueError("size must be between 16 and 8192")
    if repeats < 1 or repeats > 100:
        raise ValueError("repeats must be between 1 and 100")
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA benchmark requires a real CUDA-visible NVIDIA GPU")
    dtypes = {"float32": torch.float32, "float16": torch.float16, "bfloat16": torch.bfloat16}
    if dtype_name not in dtypes:
        raise ValueError(f"Unsupported dtype: {dtype_name}")
    dtype = dtypes[dtype_name]
    device = torch.device("cuda:0")
    # Allocate on the real device and warm up before timing.
    a = torch.randn((size, size), device=device, dtype=dtype)
    b = torch.randn((size, size), device=device, dtype=dtype)
    for _ in range(2):
        c = a @ b
    torch.cuda.synchronize()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        c = a @ b
        torch.cuda.synchronize()
        samples.append(time.perf_counter() - start)
    seconds = min(samples)
    # 2*N^3 operations for one dense matrix multiplication; theoretical operation count.
    operations = 2 * (size ** 3)
    return {
        "backend": "pytorch-cuda",
        "device": torch.cuda.get_device_name(0),
        "matrix_size": size,
        "dtype": dtype_name,
        "repeats": repeats,
        "best_seconds": seconds,
        "estimated_tflops": operations / seconds / 1e12,
        "correctness_finite": bool(torch.isfinite(c).all().item()),
        "result_shape": list(c.shape),
        "note": "Single workload measurement, not a universal GPU ranking. Includes device execution and synchronization, excludes initial allocation.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--size", type=int, default=1024)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--dtype", choices=("float32", "float16", "bfloat16"), default="float32")
    args = parser.parse_args()
    status = cuda_status()
    result: dict[str, Any] = {"cuda_status": status}
    if args.benchmark:
        result["benchmark"] = run_matmul_benchmark(args.size, args.repeats, args.dtype)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
