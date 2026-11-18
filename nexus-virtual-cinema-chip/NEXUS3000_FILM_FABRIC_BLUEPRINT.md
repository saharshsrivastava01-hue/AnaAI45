# NEXUS-3000 Virtual Cinema Chip — Infrastructure Blueprint
Revision: 0.3.0
Status: software architecture + local orchestration starter

## 1. What this system is
NEXUS-3000 is a software-defined film-production fabric. Its trillion-lane number is a virtual namespace used for task IDs and scheduling experiments. It does not represent one trillion physical GPU/TPU cores, memory bandwidth, or measured compute throughput.

The repository contains prototypes at different maturity levels. Treat them as source code until they have been run and tested on the target machine.

## 2. Logical compute domains
| Domain | Responsibility | Practical implementation |
|---|---|---|
| VTPU | creative reasoning, script and shot planning | ChatGPT-assisted authoring; local deterministic tools |
| VGPU | geometry, animation, frame rendering | Blender; CPU/GPU selected by Blender |
| VFXU | compositing, particles, grading | Blender compositor and FFmpeg filters |
| VRPU | shot continuity and quality review | manifests, frame sampling, human review |
| VMEDIA | audio, timeline and delivery | FFmpeg; optional local audio tools |
| VMEM | project, assets, metadata and cache | filesystem + SQLite registry |
| VNoC | task routing and dependency scheduling | bounded Python task graph |

These are logical service boundaries, not separate silicon devices.

## 3. Infrastructure layers
1. Project layer: one root directory, project.json, stable project ID, asset folders.
2. Asset layer: models, textures, audio, fonts and generated frames; each final asset should have a source, license note, checksum and version.
3. Planning layer: screenplay, scene breakdown, shot list, camera/lens notes, dialogue and audio cue sheets.
4. Graph layer: explicit dependencies; downstream stages cannot start until inputs are complete.
5. Scheduling layer: bounded local workers, retries, failure states and SQLite event history.
6. Execution layer: subprocess adapters for Blender and FFmpeg; no hidden cloud fallback.
7. Quality layer: missing-frame checks, render-log inspection, duration/resolution/audio checks and human approval.
8. Delivery layer: MP4 master, proxy, subtitles, credits, manifest and checksums.

## 4. Current implementation in this branch
- nexus3000_trillion_fabric.py: virtual lane namespace and simulated film-stage scheduler.
- nexus3000_film_fabric.py: local project initializer, SQLite event/task persistence, dependency validation, bounded workers, retry handling and JSON report.
- nexus_film_compiler.py: procedural Blender scene compiler prototype.
- nexus_ai_director.py: offline deterministic screenplay/shot package prototype.
- nexus_virtual_backend.py: FastAPI backend prototype; not yet verified end-to-end.
- rtl/nexus3000_top.sv: SystemVerilog control-plane prototype; not yet linted, simulated or synthesized.

Do not assume all modules are already connected. The film fabric currently records unconfigured planning checkpoints; it does not generate a feature film by itself.

## 5. Quick start (Windows)
Install Python 3.10+ and open PowerShell in the repository folder:

```powershell
python nexus3000_film_fabric.py --self-test
python nexus3000_film_fabric.py --project NEXUS_2090_FILM --init-only
python nexus3000_film_fabric.py --project NEXUS_2090_FILM
```

The first command validates the task graph. The second creates a project layout. The third runs the orchestration skeleton and writes fabric_report.json. Stages without configured commands are recorded as planning checkpoints, not footage.

For an actual local render, install Blender and FFmpeg separately, then configure and test the render adapters. Start with a 5–10 second 640x360 proxy at 12 fps. Do not attempt a long 4K feature render until a short scene completes successfully.

## 6. Render adapter contract
Every real stage should implement this contract:
- Inputs: project root, stage ID, input asset manifest, output directory.
- Outputs: deterministic output paths, machine-readable result JSON, log path.
- Exit code: zero only when outputs are complete and validated.
- Safety: argument arrays (never shell string concatenation), bounded timeouts, no paid API calls by default.
- Reproducibility: record tool version, command, settings, input checksums and output checksums.

## 7. Resilience and scaling rules
- Keep worker count small on 8 GB RAM systems; begin at 1–2 workers.
- Use proxies and incremental rendering; never load every frame into RAM.
- Resume from completed task records, but invalidate downstream tasks when an input checksum changes.
- Retry transient failures only; missing executables and invalid inputs should fail clearly.
- Add remote workers only as opt-in, separately configured infrastructure. No automatic paid compute.
- Use a queue broker only when local SQLite scheduling becomes a measured bottleneck.

## 8. Quality gates before a master export
- Every planned shot has an output or an explicitly approved omission.
- Frame sequence has no unexplained gaps or duplicate numbering.
- Video opens and decodes from beginning to end.
- Frame rate, resolution and duration match the project manifest.
- Audio is present when expected, synchronized, and not clipping.
- Credits, asset licenses and attribution are included where required.
- Final MP4 and manifest have SHA-256 checksums.

## 9. Roadmap to a working movie
P0 Validate: run Python self-tests; install Blender/FFmpeg; verify one 5-second proxy render.
P1 Connect: wire director output to a scene manifest and Blender adapter.
P2 Produce: render one shot at a time, cache frames, and resume failed shots.
P3 Post: create audio tracks, assemble timeline and encode MP4 with FFmpeg.
P4 Review: inspect frames and sound, fix continuity, then export a short master.
P5 Expand: add more scenes and only then increase resolution/runtime.

A complete film requires actual scene assets, generated or recorded audio, editing decisions and review. A scheduler or architecture diagram alone cannot supply those media assets.
