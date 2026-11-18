# NEXUS-3000 ULTRA: Virtual Compute Backend and ChatGPT Director Integration

**Revision:** 1.0  
**Status:** engineering design; not physically fabricated or connected to ChatGPT private compute.

## Product definition

NEXUS-3000 ULTRA is a software-defined cinema accelerator. It presents one virtual chip interface while scheduling work across explicitly registered compute backends. ChatGPT is the natural-language director and planning interface. The NEXUS runtime is the compiler, scheduler, memory manager, VFX graph coordinator and export manager.

A virtual chip can unify the control plane; it cannot make ChatGPT's private GPUs accessible or create physical compute from software. Every task records its real backend and execution status.

## Ultra-futuristic logical chip floorplan

| Block | Virtual role | Runtime responsibility | Real execution target |
|---|---|---|---|
| NPU-DIRECTOR | Neuro-director array | Story, screenplay, shot planning, continuity | ChatGPT conversation/API or approved LLM |
| VTPU-MATRIX | Tensor inference array | Model inference and embeddings | Registered inference API, local ONNX/llama.cpp, or GPU worker |
| VGPU-CINEMA | Parallel visual array | 3D geometry, shading, frame rendering | Blender/Eevee/Cycles on supported CPU/GPU |
| VRPU-PIXEL | Pixel transformation array | Denoise, optical flow, tracking, resize | OpenCV/FFmpeg CPU or supported GPU kernels |
| VFX-FABRIC | Node compositing array | Keying, masks, layers, particles, color pipeline | Blender compositor/FFmpeg/OpenColorIO |
| AUDIO-NEURAL | Audio DSP array | Dialogue, ambience, score, mix | Local audio tools or approved audio model |
| VMEM-HOLO | Project memory | Asset registry, continuity bible, proxies, cache | Local disk or configured object storage |
| VNoC-QUANTUM | Task interconnect | DAG routing, queues, retries, priorities | Python async scheduler / Redis-compatible queue |
| SAFETY-CORE | Policy and budget guard | Consent, provider allow-list, spend cap, file checks | Local policy engine |
| MEDIA-ENCODER | Delivery pipeline | MP4/H.264, AAC, subtitles, poster, metadata | FFmpeg |

"Quantum" and "neuro" here are design metaphors for routing and coordination, not claims of quantum computing or biological neural hardware.

## Unified API / virtual instruction set

All tools use the same project/job contract:

- BRIEF(prompt, target_duration, aspect_ratio, style, budget_policy)
- DIRECT(project_id) -> treatment, screenplay, continuity_bible
- BREAKDOWN(project_id) -> shot_list, asset_manifest
- COMPILE(project_id) -> task_DAG
- INFER(task_id, model_policy) -> generated_asset
- RENDER(task_id, renderer_policy) -> frames_or_video
- VFX(task_id, graph) -> composited_asset
- AUDIO(project_id) -> soundtrack_and_mix
- EDIT(project_id) -> timeline
- QA(project_id) -> report
- EXPORT(project_id, mp4_profile) -> verified_download_artifact

## Job DAG

A full production is a dependency graph, not a single monolithic generation call:

1. Brief and director treatment.
2. Script, shot list, continuity bible.
3. Character/environment/prop assets.
4. Per-shot inference or procedural scene creation.
5. Shot rendering and VFX compositing.
6. Audio generation/mix.
7. Timeline assembly and color finishing.
8. Automated QA and failed-shot retry.
9. MP4 encode and artifact verification.

Tasks can run in parallel only when their dependencies and shared assets permit it. Character references and approved scene assets are pinned in project memory.

## ChatGPT integration architecture

### Supported interaction
- User chats with ChatGPT to define a film.
- ChatGPT produces a structured project brief and director decisions.
- The user submits that brief to a NEXUS app/API, or to a supported connected tool when available.
- NEXUS schedules jobs and returns progress/artifact metadata.
- ChatGPT can explain status, revise the brief and request another pass.

### Not supported by this design
- Direct access to ChatGPT's private GPU/TPU cluster.
- A hidden local process running inside the ChatGPT mobile app.
- Guaranteed free unlimited video inference.
- Guaranteed feature-film rendering in seconds.

A real ChatGPT app connection requires a supported public HTTPS service/MCP integration and an eligible ChatGPT plan/client. Until then, the NEXUS local web app/CLI is the control surface; this is not the same as being embedded inside ChatGPT.

## Compute backend interface

Each backend adapter must declare:
- backend_id, capabilities, supported_formats, max_resolution, max_duration
- available, health, resource_limits
- cost_policy (free_only, user_approved, or local_only)
- submit(task), status(job_id), cancel(job_id), fetch_artifact(job_id)

Scheduler chooses only healthy, capability-compatible backends permitted by the project's cost policy. Unknown price is not treated as zero. Paid endpoints are disabled unless explicitly authorized for that project.

## Resource policy for the user's Dell Inspiron 3501

Target profile: i5-1135G7, 8 GB RAM, NVIDIA MX330 2 GB, Intel Iris Xe.
- First milestone: 10-second 640x360 or 720p preview, 12–24 fps.
- Default one render worker; limit memory and concurrent tasks.
- CPU fallback always available but may be slow.
- Use NVIDIA acceleration only after driver and Blender device detection confirms it.
- Avoid loading large local generative video models into 2 GB VRAM.
- Prefer external inference only when explicitly enabled and cost is disclosed.
- Android phone acts as controller/monitor, not presumed render accelerator.

## Security and reliability

- Bind local service to loopback by default.
- Never expose arbitrary shell execution through a public endpoint.
- Use authenticated job submission, strict task schemas and an allow-list of executables.
- Store provider credentials only in environment/secret storage; never commit keys.
- Use per-project spend ceilings, job cancellation and audit logs.
- Verify file existence, duration, codec and media readability before declaring an export ready.
- Retry transient failures with bounded attempts; never duplicate paid jobs after uncertain submission.

## Milestones / acceptance gates

### M0 — Virtual chip contract
A single project manifest, task DAG, backend registry and status API. Unit tests for task dependencies, budget gates and retry policy.

### M1 — Procedural cinema backend
Blender scene creation, local rendering and FFmpeg assembly. Acceptance: a playable short MP4 with verified duration and metadata.

### M2 — Director compiler
Brief-to-treatment-to-shotlist-to-DAG. Acceptance: every shot has duration, prompt/scene recipe, continuity references and backend assignment.

### M3 — VFX and audio
Reusable compositor graphs, sound mix and titles. Acceptance: no missing media, synchronized audio, consistent frame rate.

### M4 — AI inference adapters
Provider-neutral adapter interface, with one model endpoint enabled only after user approval and cost disclosure. Local open model adapter is optional and hardware-limited.

### M5 — ChatGPT app connection
Supported authenticated HTTPS/MCP app integration where account plan and client support it. Acceptance: ChatGPT can submit a project brief, read job status and retrieve the final verified artifact.

## Definition of done

NEXUS is only allowed to say "film generated" after a real artifact exists and passes media verification. A design document, queued task, storyboard, or simulated render is not a finished film.
