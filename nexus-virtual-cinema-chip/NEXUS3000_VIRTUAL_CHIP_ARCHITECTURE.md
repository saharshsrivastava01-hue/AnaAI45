# NEXUS-3000 Virtual Chip — Architecture v0.2

## Purpose
NEXUS-3000 is a software-defined film-production control plane. It describes
virtual accelerator domains, memory tiers, a virtual network-on-chip, and a
capability-aware production pipeline. It is not a physical GPU/TPU, does not
create compute capacity, and does not claim benchmark performance.

## Architecture layers

1. **Director plane** — story brief, screenplay, shot list, creative constraints.
2. **Orchestration plane** — dependency graph, task state, bounded concurrency,
   retry policy, cancellation and run manifests.
3. **Virtual compute plane** — capability domains:
   - VTPU: planning and AI inference adapters
   - VGEU: procedural geometry and transforms
   - VGPU: raster/material workloads
   - VRPU: ray tracing, shadows and reflections
   - VFXU: compositing, denoise and color pipeline
   - VAU: audio synthesis and mixing
   - VMEDIA: encode, mux and subtitles
   - VIO: ingest, caching and asset manifests
4. **Data plane** — VMEM logical tiers: hot cache, scene memory, frame buffer,
   and archive manifests.
5. **Interconnect plane** — VNoC logical hierarchical mesh. The current
   reference model represents routes and capabilities, not physical links.
6. **Delivery plane** — quality checks, render manifests, encode metadata and
   final deliverable packaging.

## Reliability and infrastructure contracts

- Every task should have a stable task ID, input manifest, output manifest,
  engine capability, and explicit state.
- A task may run only after all dependencies have succeeded.
- Retry only transient failures; cap retries and preserve error logs.
- Bound concurrency; never launch unbounded worker pools.
- Cache keys should include source asset hashes, scene settings, renderer
  version and output format.
- Keep source assets immutable; write outputs to per-run directories.
- Validate dimensions, frame count, frame rate, audio duration and file
  readability before marking a film deliverable complete.
- External commands and cloud providers remain opt-in; never assume credentials.
- Record provenance for generated assets and third-party inputs.

## Current implementation status

| Module | Role | Status |
|---|---|---|
| `nexus3000_virtual_chip.py` | Virtual topology and capability plan | Added; not execution-tested |
| `nexus_scene_graph.py` | JSON scene schema validator | Added; not execution-tested |
| `scenes/nexus_2090_opening.scene.json` | Example opening scene | Added |
| `nexus_photon_core.py` | Educational CPU ray-tracing prototype | Added; not execution-tested |
| `nexus3000_film_fabric.py` | Task orchestration prototype | Added earlier; integration incomplete |
| `rtl/nexus3000_top.sv` | RTL control-plane experiment | Added earlier; not linted or synthesized |

## Next engineering gates

1. Make Photon Core consume the validated scene manifest (currently not wired).
2. Add a renderer adapter with a strict input/output contract.
3. Connect adapter jobs to the film fabric with bounded workers and run IDs.
4. Add automated unit tests and CI; test one tiny frame before sequences.
5. Add VFX/audio/encode adapters only after the first end-to-end preview works.
6. For actual hardware, define FPGA/ASIC interfaces, memory arbitration,
   clock/reset domains, verification, timing closure and physical design.
   A Python simulation is not a substitute for those steps.

## Local commands

From this directory:

```bash
python nexus3000_virtual_chip.py --topology
python nexus3000_virtual_chip.py --plan
python nexus_scene_graph.py --write-sample scenes/sample.scene.json
python nexus_scene_graph.py --validate scenes/nexus_2090_opening.scene.json
```

These commands generate or inspect plans/manifests. They do not render a film.
