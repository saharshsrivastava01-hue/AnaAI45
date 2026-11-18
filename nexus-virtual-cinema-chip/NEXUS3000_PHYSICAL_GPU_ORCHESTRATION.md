# NEXUS-3000 Physical GPU Orchestration Architecture

## Purpose
NEXUS-3000 is a control plane that schedules work onto real, independently installed GPU devices. The virtual chip is an orchestration and simulation model; it does not create GPU hardware or multiply physical compute resources.

## System topology

```text
ChatGPT (user-approved requests)
        |
        | MCP tools / authenticated HTTPS (when supported by account)
        v
NEXUS Gateway (project API + job scheduler)
        |
        +---- Android controller (Termux; project control, monitoring)
        |
        +---- GPU Worker A (NVIDIA CUDA / Blender Cycles / FFmpeg)
        |
        +---- GPU Worker B (optional additional physical GPU)
        |
        +---- Video-generation provider (separate external inference)
        |
        v
Job store -> artifacts -> edit/encode -> final film
```

## Compute engines and physical mapping

| Virtual block | Real execution target | Honest responsibility |
|---|---|---|
| GPU SIMD cluster | CPU/GPU kernels; CUDA/OpenCL/Vulkan where supported | Small parallel compute kernels |
| TPU MAC tile | RTL simulation or actual FPGA/ASIC implementation | INT8 arithmetic prototype; not a production AI accelerator |
| Ray-tracing block | Blender Cycles on a supported GPU | Actual scene ray tracing |
| Media block | FFmpeg with supported hardware encoders | Video assembly, transcode and mux |
| Scheduler / NoC | NEXUS job queue | Route tasks to available workers |
| Memory fabric | Host RAM, GPU VRAM, disk | Real capacity limits; no virtual capacity claim |

## Execution lifecycle
1. ChatGPT submits a film task through an authorized MCP/API connection.
2. NEXUS validates project ID, task parameters, allowed paths and resource budget.
3. Scheduler checks worker heartbeat, free RAM/VRAM, renderer availability and job limits.
4. Worker claims one job with a short-lived lease.
5. Worker runs Blender/FFmpeg or a supported local kernel.
6. Worker returns status, logs and artifact metadata.
7. NEXUS stores the artifact path and exposes a controlled download/preview.
8. Failed jobs are retried only when idempotent and within retry policy.

## Security requirements
- Bind local development services to 127.0.0.1 by default.
- For remote access, use HTTPS through a managed tunnel or reverse proxy; never expose an unauthenticated worker.
- Use a random bearer token stored in environment variables, not committed to Git.
- Restrict worker file access to a dedicated workspace directory.
- Validate every submitted path; reject traversal and arbitrary shell commands.
- Use allowlisted executables (Blender, FFmpeg) with argument arrays, never shell interpolation.
- Add per-job timeouts, concurrency caps, disk quotas and explicit cost approval for paid model calls.
- Treat prompts, downloaded assets and tool outputs as untrusted data.

## Current user hardware
The Samsung Galaxy M35 5G is suitable as a controller for lightweight tasks. It is not a CUDA GPU host. Its Mali graphics hardware does not provide a drop-in CUDA backend. Do not claim that the phone can run NVIDIA CUDA or Blender GPU rendering.
The Dell Inspiron 3501's NVIDIA MX330 may support limited CUDA workloads depending on driver and software versions, but its 2 GB VRAM is restrictive. Verify the installed NVIDIA driver, CUDA runtime compatibility and Blender device detection before scheduling GPU renders.

## ChatGPT integration
A local Android endpoint is not automatically reachable by ChatGPT. ChatGPT custom MCP integration requires an eligible plan/workspace, a remotely reachable secure endpoint and user/admin authorization. GitHub repository access is not the same as connecting a running worker. Until connected, operate the gateway from its local CLI or web UI.

## Milestones
- M0: Existing NEXUS project and simulated queue.
- M1: Worker discovery + heartbeat + capability report.
- M2: Real Blender background render of one low-resolution test frame.
- M3: FFmpeg assembles a short preview from verified frames.
- M4: Multi-shot queue, progress, retry and artifact registry.
- M5: Secure remote MCP/API gateway for eligible ChatGPT integration.
- M6: Full feature-length production only after measured render time, storage, budget and provider capacity are known.

## Acceptance tests
- Worker reports exact OS, CPU, RAM, GPU name, VRAM (when discoverable), Blender and FFmpeg versions.
- A test scene produces a real image file and a non-zero output size.
- FFmpeg assembles two test frames into a playable short clip.
- Every output has a checksum, job ID and source project ID.
- No test reports "completed" unless the output artifact exists and passes a basic validation.
