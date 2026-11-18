# NEXUS Interstellar Cinema Chip — Logical Block Design v1.1

> This is a software/FPGA-oriented logical architecture proposal, not a fabricated semiconductor, verified RTL, or benchmarked accelerator.

## Top-level data path

```text
ChatGPT / MCP Client
        |
Authenticated API Gateway
        |
Film Project Controller ---- SQLite Project + Asset Manifest
        |
Story & Continuity Engine
        |
Scene Graph Compiler
        |
Asset / Geometry Adapter
        |
Motion + VFX Graph ---- Audio / Dialogue Timeline
        |
Render Scheduler ---- Local Blender Worker(s)
        |
Frame / Audio Artifact Store
        |
FFmpeg Assembly + QC
        |
Final Movie Export
```

## Functional blocks

| Block | Responsibility | First implementation |
|---|---|---|
| INT-01 Intelligence Gateway | Accept structured film instructions from ChatGPT | FastMCP tools; no embedded LLM |
| CTRL-02 Command Controller | Validate project, scene and task state | Python service |
| MEM-03 Story Memory | Store continuity, assets and production metadata | SQLite |
| SCN-04 Scene Compiler | Convert scene descriptions into renderer inputs | JSON schema + Python |
| GEO-05 Geometry Adapter | Create or import scene assets | Blender Python scripts |
| MOT-06 Motion/VFX | Camera, animation and compositing instructions | Blender scene scripts |
| AUD-07 Audio Timeline | Dialogue, score and effects timing | Timeline metadata; licensed audio assets |
| SCH-08 Scheduler | Queue bounded local rendering jobs | SQLite queue; one worker by default |
| ASM-09 Movie Assembler | Join clips, audio and subtitles | FFmpeg adapter, optional |
| QC-10 Quality Gate | Check missing clips, durations and export metadata | Python validation |
| SEC-11 Security Monitor | Validate inputs, protect secrets and restrict execution | Allowlisted paths and environment secrets |
| COL-12 Collaboration Bridge | Send status to Teams when configured | Optional webhook adapter |

## Suggested logical interfaces
- Control plane: authenticated HTTP/MCP requests.
- Project data: versioned JSON documents with stable IDs.
- Local render adapter: subprocess invocation with explicit executable path, timeout and per-job working directory.
- Artifact interface: manifest entries containing relative path, media type, duration, dimensions, provenance and checksum.
- Collaboration: outbound-only notification adapter; webhook secret stored in an environment variable.

## Resource policy
- `virtual_gpu_slots` and `virtual_tpu_slots` are scheduler labels only.
- The local scheduler must cap concurrent Blender processes and reject jobs that exceed configured memory/time budgets.
- Never represent planned capacity as installed hardware or measured throughput.
- Default to draft previews (720p or lower) and short clips. Escalate resolution only after a successful test render.
- Paid APIs and remote rendering remain disabled unless the operator explicitly opts in.

## Failure states
Use explicit states: `planned`, `queued`, `running`, `completed`, `failed`, `blocked_missing_renderer`, `blocked_resource_limit`, and `cancelled`. Only `completed` may be used when the expected output file exists and passes validation.

## Silicon implementation path (separate future project)
A real ASIC would require an ISA, RTL, verification testbench, synthesis, timing closure, physical design, DRC/LVS, tape-out and silicon validation. This repository does not contain those deliverables. An FPGA prototype could be explored first for a small fixed-function scheduling or image-processing accelerator, but the existing Python/MCP software is not itself chip RTL.
