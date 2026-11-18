# NEXUS-3000 Heterogeneous Virtual Fabric Runtime

## What this adds

`nexus3000_fabric_runtime.py` is a capability-aware task scheduler. It can
coordinate registered executors representing CPUs, GPUs, TPUs, render nodes,
or other workers through one interface. The runtime uses a bounded local
thread pool and reports task counts and observed latency.

## Critical distinction

The virtual fabric does **not** create physical compute. A device entry is
only an adapter to a resource that already exists. A billion virtual lanes
are identifiers/scheduling capacity, not a billion GPU cores, memory channels,
or FLOPS. The demo executor runs ordinary Python on the host CPU.

## Run the demo

From the repository root:

```bash
cd nexus-virtual-cinema-chip
python nexus3000_fabric_runtime.py
```

## Run tests

```bash
python -m unittest discover -s tests -p "test_fabric_runtime.py" -v
```

## Attach real hardware

Create an executor function that accepts a command dictionary, transfers the
payload to a real backend, waits for its result, and returns a serializable
result. Register it with truthful metadata:

- NVIDIA GPU: use an installed CUDA-compatible framework/runtime.
- AMD GPU: use a supported ROCm or vendor runtime.
- TPU: use the supported TPU runtime and an available TPU device.
- Remote worker: use an authenticated transport/worker service and explicit
  timeouts, retries, serialization, and trust boundaries.

Do not label a simulator as a physical GPU/TPU. Report hardware model, driver,
memory, measured throughput, and benchmark conditions separately.

## Scaling roadmap

1. Add authenticated remote-worker protocol and heartbeats.
2. Add backpressure, cancellation, retries, and durable task queues.
3. Add data locality and transfer-cost-aware placement.
4. Add adapters for actual GPU/TPU frameworks when hardware is available.
5. Benchmark real workloads (matrix multiplication, inference, rendering) and
   compare against a single-device baseline.

The scheduler can improve utilization and reduce coordination overhead. It
cannot bypass the physical limits of silicon, memory bandwidth, networking,
power, cooling, or hardware availability.
