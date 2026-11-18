# NEXUS-3000 Hollywood-Scale Virtual Cinema Architecture
Version: 0.5 design specification
Status: architecture proposal; not a claim of completed hardware or production-scale performance.

## 1. Product goal

NEXUS-3000 is a modular film-production computer architecture. Its job is to turn an original creative brief into a reproducible, reviewable film pipeline:

**Brief -> screenplay -> shot plan -> scene graph -> assets -> geometry -> lighting -> render -> compositing -> sound -> encode -> quality-control -> delivery.**

The system should be easy to operate from one project manifest. Advanced users can replace individual engines without rewriting the entire pipeline.

## 2. Rendering: what exists and what does not

The repository already contains a CPU renderer prototype, cinematic post-processing code, and a GitHub Actions workflow configured for a small dummy-film render and MP4 encoding. The workflow configuration is not proof that a run has passed. The CPU renderer is an educational prototype, not a production renderer.

Current boundaries:
- A local render requires Python and the required dependencies; MP4 encoding also requires FFmpeg.
- GitHub Actions can provide a remote CI render runner when the workflow is enabled and completes successfully. It is not an unlimited render farm.
- Logical GPU/TPU lane counts in the virtual-chip model are scheduling labels, not physical cores, memory, or measured throughput.
- No Blender/Unreal replacement, Dolby certification, physical 4D effects, or ASIC silicon is claimed.

## 3. High-level architecture

```text
                  NEXUS STUDIO / PROJECT MANIFEST
                               |
                     Creative Orchestrator
                               |
            +------------------+------------------+
            |                  |                  |
       Story Engine       Shot/Scene Compiler   Asset Registry
            |                  |                  |
            +------------------+------------------+
                               |
                       Scene Description IR
                               |
                   Dependency / Task Graph
                               |
        +----------------------+----------------------+
        |                      |                      |
   Geometry Engine        Simulation Engine      Neural Assist
   mesh / curves          particles / cloth      denoise / upscale*
   BVH / triangles        fluids / rigid body    segmentation*
        |                      |                      |
        +----------------------+----------------------+
                               |
                       Render Scheduler
                               |
      +------------------------+------------------------+
      |                        |                        |
  Raster Preview          Ray/Path Tracing          Volume Renderer
  fast blocking           reflections / GI          fog / smoke
      |                        |                        |
      +------------------------+------------------------+
                               |
                       Frame / Tile Store
                               |
                    Compositing & Color Pipeline
               AOVs -> keying -> glow -> grade -> grain
                               |
                 Spatial Audio / Dialogue / Music
                               |
                    Video + Audio Mux / Encoder
                               |
                   QC -> Master -> Delivery Package
```

*Neural assist modules are optional future integrations. They require actual model weights, a compatible runtime, and sufficient compute; a module name alone does not provide AI capability.

## 4. Core subsystems

### A. Studio interface and creative orchestration
- One project manifest defines frame rate, resolution, shot list, asset references, render quality, output format, and compute budget.
- A shot is a first-class unit: it can be previewed, rendered, retried, versioned, and approved independently.
- Every task records inputs, outputs, status, duration, and error details.
- Human approval gates protect screenplay, shot continuity, character identity, and final master.

### B. Scene compiler
- Convert a validated scene description into a deterministic intermediate representation (IR).
- Resolve asset paths, coordinate systems, units, camera transforms, material references, and dependency edges.
- Reject missing assets, invalid transforms, cyclic dependencies, and unsupported features before expensive rendering.
- Keep source scene files separate from compiled render data.

### C. Geometry and visibility
- Mesh, curve, instancing, skinning, and procedural geometry interfaces.
- BVH builder and traversal controller.
- AABB broad-phase intersection followed by triangle narrow-phase intersection.
- Acceleration structures are versioned against the geometry they describe.
- The current RTL BVH controller and ray/AABB block are early components; triangle intersection and complete memory integration remain future work.

### D. Materials, lighting, and rendering
- Material interface: base color, roughness, metallic, opacity, emission, normal, and texture bindings.
- Lighting interface: directional, point, area, environment, and emissive surfaces.
- Raster preview for fast composition; ray/path tracing for higher-quality lighting; volume rendering for smoke, haze, and atmosphere.
- Progressive rendering should checkpoint completed tiles and allow interrupted jobs to resume.
- Denoising must be an optional post-process, not silently substituted for ground-truth samples.

### E. Simulation and effects
- Separate deterministic simulation jobs for particles, rigid bodies, cloth, fluids, hair, and procedural environments.
- Cache simulation outputs by scene version, timestep, and solver settings.
- Keep simulation resolution and iteration limits explicit to prevent unbounded jobs.

### F. Compositing and color
- Render passes/AOVs: beauty, diffuse, specular, emission, depth, normal, motion vectors, and object masks.
- Node-based compositing graph with explicit color-space conversions.
- HDR output only when the source data, processing chain, encoder, and display target support it.
- VFX presets are creative looks, not a guarantee of professional mastering or display certification.

### G. Audio and delivery
- Dialogue, Foley, ambience, score, and spatial audio remain separate stems until the final mix.
- Support stereo and multichannel layouts based on the actual encoder and playback target.
- Object-based spatial audio can be designed as a general capability; Dolby Atmos branding/certification requires the appropriate licensed workflow.
- Encode MP4 review copies first; preserve high-quality image sequences and audio stems for mastering.

## 5. Simple operator workflow

1. Create a project and choose a preset: Preview, Standard, or Final.
2. Add a story and shot list.
3. Attach or generate assets; approve character and environment references.
4. Compile the scene and fix validation errors.
5. Render low-resolution previews for every shot.
6. Approve camera, blocking, continuity, and timing.
7. Render final frames in resumable tiles.
8. Composite AOVs, mix audio, encode, and run QC.
9. Export the MP4 review copy plus a reproducibility manifest.

Recommended defaults for a constrained computer: 720p preview, one shot at a time, low samples, small tile sizes, and a short test clip before a full sequence. High-resolution, long-duration renders need more RAM, storage, and compute.

## 6. Compute tiers

| Tier | Execution | Intended use | Reality |
|---|---|---|---|
| Local CPU | User computer | Learning, previews, small scenes | Limited by available CPU/RAM |
| Local GPU | Supported GPU and drivers | Faster previews/rendering | Only supported devices execute work |
| CI runner | GitHub Actions runner | Tests and short automated renders | Quotas/time limits apply |
| Connected render nodes | Explicitly registered machines | Distributed frame/tile rendering | Requires real nodes, network, storage, and scheduling |
| FPGA prototype | Synthesized RTL on supported FPGA | Validate hardware datapaths | Requires board, toolchain, timing closure |
| ASIC | Fabricated silicon | Dedicated accelerator | Requires tapeout, foundry, packaging, validation |

A virtual lane or pod count is not a compute tier. Capacity is measured only from real registered devices and completed benchmark jobs.

## 7. Reliability and quality gates

- Unit tests for math kernels and parsers.
- Golden-image tests for deterministic scenes.
- Scene validation before scheduling.
- Per-frame checks for missing/black frames, invalid dimensions, corrupted files, and audio/video duration mismatch.
- Resource admission limits for RAM, disk, worker count, and render duration.
- Retry only failed tasks; preserve successful tiles.
- Record software version, scene hash, assets, settings, and hardware for reproducibility.

## 8. Upgrade roadmap

1. **v0.5 — Pipeline contract:** project manifest, scene IR, task graph, and QC report format.
2. **v0.6 — Geometry correctness:** triangle intersection RTL/software reference, edge-case tests, BVH + AABB + triangle integration.
3. **v0.7 — Real frame renderer:** tile scheduler, framebuffer, camera, materials, direct lighting, image-sequence output.
4. **v0.8 — Film workflow:** shot manager, resumable rendering, AOV compositing, audio stems, FFmpeg delivery.
5. **v0.9 — Scale-out:** real worker registration, bounded queues, storage/cache, telemetry, fault recovery.
6. **v1.0 — Hardware prototype:** synthesis, FPGA validation, timing/resource reports, hardware/software parity tests.

## 9. Definition of done

A feature is complete only when its source is committed, tests run, outputs are inspected, and limitations are documented. A workflow file being committed does not mean it has run. A successful compile does not mean the design is synthesized or fabricated. A generated MP4 is not automatically a Hollywood master.
