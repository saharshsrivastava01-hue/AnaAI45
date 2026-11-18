# NEXUS CUDA backend prototype

This module calls a real NVIDIA GPU through PyTorch's CUDA backend when a
compatible NVIDIA driver and CUDA-enabled PyTorch installation are present.
It does not emulate CUDA, create GPU cores, or make virtual lane counts real.

## Check hardware visibility

```bash
python nexus_cuda_backend.py --status
```

## Run a real matrix multiplication benchmark

```bash
python nexus_cuda_backend.py --benchmark --size 1024 --repeats 5 --dtype float32
```

Try larger sizes only when device memory permits. The script caps matrix size
at 8192 and reports the actual detected GPU name, PyTorch build, precision,
elapsed time, and estimated throughput for this one workload.

## Requirements

- NVIDIA GPU with a compatible driver.
- PyTorch installed from an official build compatible with the driver/runtime.
- Use the official PyTorch install selector for the correct command:
  https://pytorch.org/get-started/locally/

## Important

- A CUDA build of PyTorch alone does not provide a GPU if no compatible device
  is visible.
- CUDA status and benchmark results are runtime facts, not CI assumptions.
- A single GEMM result does not establish general superiority to another GPU.
- The NEXUS scheduler must register a concrete executor before dispatching to
  a GPU device. Discovery is not execution.
