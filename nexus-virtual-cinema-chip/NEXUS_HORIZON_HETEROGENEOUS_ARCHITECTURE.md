# NEXUS-3000 Horizon Architecture — Research Design v0.1

**Status:** Proposed research architecture. Not implemented silicon, not a forecast of 2050 hardware, and not a performance claim.

## 1. Mission and honest boundary

Design a modular heterogeneous compute system that could be developed and benchmarked against future accelerator systems. The target is *competitive capability*, not an unsupported promise to exceed unknown 2050 technology. No architecture can guarantee superiority over hardware that has not yet been designed or measured.

The existing NEXUS virtual lane counts are namespace labels. They are not cores, memory, bandwidth, FLOPS, TOPS, qubits, or delivered compute. This proposal replaces lane-count marketing with measurable resource contracts.

## 2. System concept: Horizon Heterogeneous Compute Fabric

The system is a scale-out fabric of independently useful compute domains connected by a high-bandwidth, fault-tolerant, coherent-or-message-passing interconnect.

### Compute domains

1. **Scalar/vector CPU domain** — control plane, irregular workloads, OS/runtime, graph traversal, serial sections.
2. **SIMD/SIMT graphics domain** — rasterization, geometry, shader workloads, image kernels.
3. **Tensor domain** — dense/sparse matrix multiplication, convolution, attention, quantized inference and training.
4. **Ray/geometry domain** — BVH traversal, ray/triangle intersection, sampling, denoising and physically based rendering.
5. **Reconfigurable domain** — FPGA-like dataflow pipelines for low-latency custom operators; only when an actual FPGA is present.
6. **Memory-compute domain** — near-memory processing and data-reduction engines to reduce data movement; requires compatible memory hardware.
7. **Quantum interface domain (optional, remote)** — job submission to an actual external quantum processor for narrow algorithms where hardware and error rates justify it. A simulator or quantum-inspired optimizer is not a quantum computer.
8. **Agent orchestration domain** — sandboxed tools, model serving, retrieval, planning, evaluation, policy enforcement and human approval. This is an AI software platform, not a guarantee of AGI.

## 3. Fabric topology

Use a hierarchical 3-tier topology:

- **Package/local:** chiplet links, local cache and memory controllers.
- **Rack/pod:** high-radix switched fabric with redundant paths and congestion control.
- **Campus/region:** routed optical or electrical fabric with explicit latency and failure domains.

Every link publishes measured bandwidth, latency, error rate, congestion, and power. The scheduler must not assume a link is faster because it has a larger virtual capacity label.

Support two communication models:
- shared-memory coherence only inside bounded domains where the protocol and hardware support it;
- explicit message passing / RDMA-style transfers across nodes, with ownership, completion, retry and integrity checks.

## 4. Memory hierarchy and data movement

- Registers and local scratchpad for deterministic low-latency kernels.
- On-chip caches where supported by the selected processor.
- HBM or GDDR on accelerator boards where physically installed.
- Host DDR memory.
- NVMe/object storage for datasets and checkpoints.
- Distributed cache with explicit replication and eviction policy.

The runtime tracks *real allocated bytes*, bandwidth, locality, transfer time, page faults and spill events. Virtual address-space reservations must never be reported as installed RAM.

## 5. Runtime and scheduler

Implement a capability-aware task graph:
- typed tasks with input/output schemas and resource requirements;
- measured device inventory discovered at runtime;
- queue backpressure and admission control;
- topology-aware placement using estimated compute + transfer + queueing cost;
- per-device concurrency limits and memory budgets;
- preemption only for tasks that declare safe checkpoints;
- retries for idempotent tasks, with deduplication keys;
- deterministic caching only when inputs, model versions and execution semantics permit it;
- isolation, quotas, audit logs and signed artifacts.

A task is dispatched only to a device whose real capabilities satisfy the task contract. If no such device exists, the runtime reports unsupported or falls back to a slower valid backend.

## 6. AI and agent cluster layer

Treat an agent system as a controlled distributed application:
- model gateway with explicit model/version/context limits;
- retrieval and vector index services;
- tool registry with least-privilege credentials;
- planner/executor separation;
- sandboxed code and browser workers;
- policy checks before external side effects;
- evaluator and regression suite;
- trace IDs, token/cost accounting, latency and failure metrics;
- human approval for consequential actions.

Multiple agents do not automatically create AGI. Evaluate task success, reliability, calibration, tool safety, cost and reproducibility on published test sets.

## 7. Rendering and simulation stack

A practical first vertical slice:
1. scene graph and USD/glTF import;
2. geometry, materials and texture pipeline;
3. BVH build and traversal;
4. ray/triangle intersection;
5. physically based shading and sampling;
6. denoising as an optional model-backed stage;
7. tiled frame buffer and compositing;
8. audio/video encode and quality-control report.

Do not label a CPU prototype as GPU acceleration. Do not claim production path tracing until image correctness and performance are measured against reference scenes.

## 8. Quantum computing: realistic integration

Quantum processors are not general-purpose replacements for GPUs/TPUs. The architecture exposes a pluggable quantum job API for selected optimization, chemistry or sampling experiments only when a real provider/device is connected. Track qubit count, connectivity, gate/readout error, circuit depth, queue time, shots and result uncertainty. Classical simulation must be labelled simulation.

## 9. Benchmark contract

Every release publishes:
- exact hardware model, firmware, driver and software versions;
- precision and numerical tolerance;
- model/scene/dataset and input dimensions;
- warm-up policy, repetitions and variance;
- throughput, latency (p50/p95/p99), memory footprint and bandwidth;
- wall power and energy per task where instrumentation exists;
- scaling efficiency across one device, one node and multiple nodes;
- correctness score and output-quality metrics;
- baseline implementation and reproducible commands.

Report measured results separately from estimates. Compare against contemporary GPUs/TPUs using identical workloads and precision. A claim of superiority requires repeatable wins on a defined workload suite, not a larger logical lane count.

## 10. Staged implementation plan

**Stage A — software truth layer**
- Replace virtual resource claims in reports with explicit logical-vs-physical fields.
- Add device discovery, capability contracts and a CPU reference backend.
- Add task-graph scheduler with actual bounded concurrency, queue depth and memory admission.
- Add telemetry and reproducible benchmark harness.

**Stage B — real accelerator backends**
- Add CUDA/ROCm/oneAPI or other vendor backend adapters only where compatible hardware and drivers are detected.
- Implement tensor, raster and ray workloads with correctness tests.
- Measure host-device transfer costs and end-to-end performance.

**Stage C — multi-node scale-out**
- Add worker agents, authenticated RPC, object store/checkpointing, topology-aware scheduling and fault recovery.
- Test scale-out efficiency and failure injection.

**Stage D — research hardware**
- Define RTL interfaces, fixed-point formats, memory protocols and formal assertions.
- Simulate, lint and synthesize modules; then validate on an FPGA board.
- Only after FPGA evidence consider chiplet/ASIC feasibility, area, timing, thermal and power budgets.

**Stage E — advanced research**
- Explore near-memory compute, optical links, sparsity-aware tensor engines, approximate computing with error bounds, and optional quantum-service integration.
- Keep each feature behind measurable experiments and ablation tests.

## 11. Acceptance gates

A stage is complete only when:
- source and build are reproducible;
- automated tests pass on a named runner;
- hardware detection is truthful;
- benchmark data and raw logs are archived;
- correctness is checked against a reference;
- resource and power claims are supported by instrumentation.

## 12. Non-goals and prohibited claims

This document does not claim:
- physical billion-lane processors or petabytes of installed memory;
- a working quantum computer or quantum advantage;
- AGI or autonomous superintelligence;
- superiority to 2050 systems;
- Dolby certification, Hollywood-grade rendering, or any unmeasured performance.

**Core principle:** build a system that earns performance claims through silicon, software, reproducible benchmarks and independent comparison—not by assigning enormous numbers to virtual lanes.
