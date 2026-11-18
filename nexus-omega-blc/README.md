# NEXUS OMEGA BLC
**Beyond-Limit Compute — research simulator**

A from-scratch Python research prototype for comparing heterogeneous compute ideas: digital CPU/GPU baselines, hypothetical photonic matrix engines, near-memory compute, event-driven neuromorphic engines, stochastic compute and an external quantum-device bridge.

## Important scientific boundary
This repository contains an **analytical software model**, not a physical chip, quantum computer, photonic processor or AGI system. All hypothetical engine rates and power values are illustrative parameters in `nexus_blc.py`, not vendor specifications or measurements. The model does not establish a million-fold speedup. It uses a simplified roofline/Amdahl-style estimate and omits many real-world costs (precision loss, conversion, thermal coupling, queueing, network topology, compiler overhead, error correction and manufacturing constraints).

## Requirements
Python 3.10+; standard library only.

## Run
```bash
python nexus_blc_cli.py --demo --output nexus_blc_report.json
python -m unittest discover -s tests -v
```

## Architecture
- Workload description: operation count, bytes moved, sparsity, parallel fraction and precision.
- Engine catalogue: supported workload classes, peak modeled rate, modeled bandwidth, power and setup overhead.
- Analytical estimator: compute time, memory time, serial floor, total estimated latency and energy.
- Router: ranks compatible engines by modeled latency then modeled energy.
- Report: JSON with assumptions and explicit simulation-only status.

## Model equations
For workload operations (O), sparsity (s), peak rate (P), bytes (B), bandwidth (W), parallel fraction (f), setup time (t_0), and modeled power (p):

- useful operations = (O(1-s))
- compute time = (O(1-s)/P)
- memory time = (B/W)
- serial floor = (O(1-f)/P)
- estimated time = (t_0 + max(compute time, memory time, serial floor))
- estimated energy = estimated time × modeled power

This is a teaching/research approximation, not a cycle-accurate simulator. In particular, the serial-floor formula is simplified and should be replaced by a calibrated Amdahl/roofline model before making hardware decisions.

## Roadmap
1. Calibrate CPU/GPU baselines using reproducible local benchmarks.
2. Add precision/error models and conversion overhead.
3. Add multi-engine scheduling, contention, queueing and interconnect topology.
4. Add thermal/power caps and memory hierarchy.
5. Add trace replay from real workloads.
6. Validate each hypothetical subsystem against published device data.
7. Explore RTL/FPGA prototypes only after software models are falsifiable.

## Research honesty
A model can rank its own assumptions; it cannot prove that the assumptions are physically achievable. Report measured and simulated results separately.
