# NEXUS-3000 5D Virtual Supercomputer Architecture

## Vision

A single software control plane that can schedule work across heterogeneous
CPU, GPU, TPU and remote compute workers. The "5D" name describes five
planning dimensions; it does not imply a fifth physical dimension or extra
physical compute.

## Five scheduling dimensions

1. **Compute:** capability matching and estimated work cost.
2. **Memory:** working-set admission against declared device memory.
3. **Network:** estimate input transfer time using declared link bandwidth.
4. **Time:** priority ordering, elapsed-time measurements and deadline-miss
   reporting.
5. **Spatial topology:** prefer matching region and rack to reduce data movement.

## Runtime layers

- **Control plane:** job validation, placement plan, priorities and metrics.
- **Fabric plane:** worker registry and capability/resource metadata.
- **Execution plane:** bounded concurrent executor adapters.
- **Data plane:** payload transfer, data locality and deterministic cache.
- **Observability plane:** job outcomes, wall time, errors and deadline misses.

## Implemented prototype

`nexus5d_supercomputer.py` provides a bounded thread-pool scheduler, five-axis
placement metadata, capability and memory filtering, locality-aware placement,
simple compute/transfer estimates, priority ordering, optional deterministic
result caching, and execution metrics.

Run from the repository root:

```bash
cd nexus-virtual-cinema-chip
python nexus5d_supercomputer.py
python -m unittest discover -s tests -p "test_nexus5d_supercomputer.py" -v
```

## Real hardware adapters

A node's executor must call a real backend. Examples include a CUDA runtime,
ROCm, a supported TPU runtime, or an authenticated remote worker service.
Populate device model, memory and bandwidth from hardware discovery and
measurements. The demo uses a CPU function and a simulated GPU label only in
tests; it does not execute GPU instructions.

## Production roadmap

1. Add device discovery and explicit backend adapters.
2. Add authenticated RPC, TLS, worker heartbeats and health checks.
3. Add durable queues, backpressure, cancellation, retry budgets and idempotency.
4. Add distributed object storage, chunking, zero-copy paths where supported,
   and topology-aware data placement.
5. Add gang scheduling for multi-device jobs and distributed collectives.
6. Add workload-specific benchmarks and power/energy accounting.
7. Add quotas, tenant isolation, signed artifacts and audit logs.

## Physical limits and honest performance

The scheduler cannot turn virtual lanes into arithmetic units or create HBM,
interconnect bandwidth, power, cooling or silicon. It can reduce wasted work
and improve utilization of existing resources. Any speedup claim must be
measured against a named baseline on specified hardware with reproducible
inputs, warm-up, repeated trials and reported variance.
