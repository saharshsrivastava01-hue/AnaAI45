# NEXUS-3000 Virtual Execution Fabric

## Purpose
NEXUS-3000 is the single software-defined execution interface for film production. Film requests enter the virtual chip; its scheduler decomposes them into AI inference, scene generation, rendering, compositing, audio, and encoding jobs.

## Critical engineering boundary
Virtual GPU/TPU/RPU units are scheduler abstractions, not newly created physical silicon. Every operation must execute on a registered backend: local CPU, supported physical GPU, local inference runtime, Blender, FFmpeg, or an explicitly approved remote model provider. The virtual chip owns scheduling, memory budgeting, dependencies, retries, provenance, and output assembly.

## Virtual compute domains
- VGPU: image/geometry kernels, shader and render workloads; maps to a supported GPU backend or CPU fallback.
- VTPU: tensor/matrix inference workloads; maps to a supported local inference runtime and physical CPU/GPU accelerator.
- VRPU: programmable image/video transforms, denoise/upscale/flow and compositing; maps to available libraries and media accelerators.
- VMEDIA: audio/video encode/decode and mux; maps to FFmpeg and available codecs.
- VMEM: bounded job working sets, cache metadata, model manifests and artifact references. It is not extra physical RAM or VRAM.
- VNOС: dependency graph, queue, worker registry, admission control, telemetry and resource arbitration.

## Film request execution graph
1. ChatGPT authors a film brief, script, shot list and structured scene specifications.
2. NEXUS Director validates the brief and creates a dependency graph.
3. VTPU schedules available local model inference; missing models are reported rather than silently fabricated.
4. VGPU schedules scene generation and Blender renders.
5. VRPU schedules post-processing and compositing.
6. VMEDIA assembles frames, audio, subtitles and final video.
7. NEXUS validates output files and returns artifact paths, logs, timings and backend provenance.

## Current Dell-first target
- Host: Dell Inspiron 3501, Intel i5-1135G7, 8 GB RAM, NVIDIA MX330 2 GB.
- First renderer: Blender Cycles CUDA if the installed driver and Blender build expose the MX330; otherwise CPU fallback.
- First inference runtime: CPU-only small model/runtime until GPU compatibility and available VRAM are measured.
- Concurrency: one heavy render or inference job by default; no simultaneous large models on 2 GB VRAM.
- Android phone: controller only, not assumed to be a remote accelerator.

## ChatGPT connection
ChatGPT can create structured film jobs and inspect results through an available secure integration. A local Dell process is not automatically reachable from ChatGPT. Until an eligible secure remote connector is configured, use the local NEXUS CLI/web interface and exchange job manifests/artifacts. Never expose an unauthenticated worker to the public internet.

## Cost and safety policy
- Local CPU/GPU jobs are free of provider API charges but consume electricity and hardware resources.
- Remote inference/video providers are disabled unless the user explicitly approves the provider and cost.
- No automatic model downloads, cloud provisioning, purchases, or paid job submission.
- Enforce maximum resolution, frame count, memory budget, execution timeout, allowed paths, and worker authentication.

## Acceptance gates
- Gate A: host probe reports CPU, RAM, GPU and driver state.
- Gate B: Blender renders one test frame and logs the actual device used.
- Gate C: local inference runs one prompt and records model/runtime/device.
- Gate D: NEXUS DAG runs an end-to-end short preview and verifies the resulting MP4.
- Gate E: ChatGPT integration submits a job only through an authenticated supported connector.

Do not mark a gate passed until the corresponding command has been executed and its output inspected.