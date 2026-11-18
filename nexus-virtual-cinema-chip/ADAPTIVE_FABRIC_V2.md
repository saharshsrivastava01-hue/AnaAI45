# NEXUS-3000 Adaptive Fabric v2

This layer adds a workload planner above the heterogeneous executor runtime.

## New mechanisms

- **Capability routing:** only workers advertising the requested operation class are eligible.
- **Memory admission control:** a task is not placed on a worker whose declared memory is too small.
- **Data locality:** workers holding the requested data region are preferred to reduce transfers.
- **Load-aware placement:** the planner prefers workers with lower normalized in-flight load.
- **Deterministic result cache:** identical deterministic operations can reuse a prior result instead of recomputing it.
- **Priority ordering:** higher-priority jobs are planned first.
- **Bounded concurrency metadata:** worker capacity and the runtime worker limit constrain admission.

## Run

```bash
cd nexus-virtual-cinema-chip
python nexus3000_adaptive_fabric.py
python -m unittest discover -s tests -p "test_adaptive_fabric.py" -v
```

## Important limitations

The included demo is CPU-backed. A worker becomes a real GPU/TPU worker only when its executor is connected to a real device runtime. Device memory and capability metadata must be populated from actual hardware discovery, not guessed.

The current planner executes its item list synchronously in one process. It is a foundation for a future remote-worker protocol, distributed queue, cancellation, heartbeats, fault recovery and measured multi-node scheduling. Cache correctness depends on deterministic operations and complete input keys; do not enable deterministic caching for stochastic training, time-dependent operations, or side effects.

No virtual-lane count can replace physical arithmetic units, HBM bandwidth, network links, power or cooling. Performance claims require reproducible benchmarks on attached hardware.
