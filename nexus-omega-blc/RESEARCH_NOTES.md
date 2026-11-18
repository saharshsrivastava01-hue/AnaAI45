# Research notes: NEXUS OMEGA BLC

## Hypotheses to test
1. Data movement dominates selected workloads; near-memory execution may reduce transferred bytes.
2. Optical matrix engines may help dense linear algebra if optical-electrical conversion, precision and memory feed costs are controlled.
3. Event-driven hardware may benefit sparse, temporally localized workloads.
4. Approximate/stochastic execution may reduce cost only when an explicit error budget is acceptable.
5. Heterogeneous scheduling may improve utilization when routing overhead is lower than the benefit.
6. Reversible logic is a long-term energy research direction, not a drop-in low-power CPU.
7. Quantum devices should be treated as specialized external co-processors, not universal replacements for GPUs.

## Required evidence per subsystem
- Published device parameters and date.
- Supported operation and numerical precision.
- Throughput under a clearly specified workload.
- Energy boundary (core-only vs full system).
- Memory and interconnect costs.
- Conversion, calibration, error correction and cooling overhead.
- Reproducible baseline and independent replication.

## Falsification rules
Reject a claimed advantage if it disappears after including data movement, precision conversion, setup, queueing, error correction, cooling or system-level power. Never compare peak theoretical operations from different precision formats as if equivalent.

## Immediate engineering priorities
- Replace illustrative constants with sourced ranges and provenance metadata.
- Add confidence intervals and sensitivity analysis.
- Implement Amdahl's law and roofline ceilings separately.
- Add a discrete-event queueing model for shared engines.
- Import real benchmark traces and compare with local hardware.
