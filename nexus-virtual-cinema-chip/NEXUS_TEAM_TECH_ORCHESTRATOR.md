# NEXUS Team Technology Orchestrator

## Goal
Coordinate a film-production team of specialized workers through the NEXUS scheduler and optionally Microsoft Teams. This document defines an implementable, provider-neutral design. It does not imply physical GPUs or a live Teams connection.

## Teams (Microsoft) integration
- Use Microsoft Graph with OAuth delegated permissions and a tenant/user consent flow for messages, meetings or channels as supported by the tenant.
- Prefer a Teams channel as the production dashboard: task-created, worker-started, render-failed, asset-review and shot-completed notifications.
- For a low-risk prototype, use a manually configured Power Automate workflow or Teams Workflows webhook if available in the tenant. Treat webhook URL as a secret; never commit it.
- Do not expose the local MCP server publicly. Use a secured tunnel only if needed, with authentication and restricted scope, or deploy behind HTTPS/authentication.
- Teams notifications are not a substitute for ChatGPT MCP connectivity. The ChatGPT interface/account must independently support MCP connections.

## Agent roles
1. Executive Producer / Coordinator — project goals, priority, approvals, budget guardrails.
2. Screenwriter — story, screenplay, dialogue, character beats.
3. Continuity Editor — story bible, timeline, props, geography, character consistency.
4. Production Designer — sets, color palette, props and environment plans.
5. Cinematographer — shot sizes, lenses, camera movement, composition.
6. Lighting Artist — lighting rigs, exposure and atmosphere.
7. VFX Supervisor — effects breakdown and compositing plan.
8. Asset Engineer — procedural assets and model/texture manifests.
9. Animation Director — blocking, motion and timing.
10. Sound Designer — sound effects, dialogue cues and score brief (no copyrighted tracks generated without authorization).
11. Render Scheduler — queues jobs, throttles local workers and records real results.
12. Editor — shot assembly, timing, transitions and export checklist.
13. QA Reviewer — inspect rendered frames, continuity, audio and export.
14. 4D Experience Planner — motion, haptic, wind, lighting cue metadata; physical effects require compatible hardware.

## Workflow
Story input -> story bible -> scene/shot breakdown -> assets -> shot plans -> local render queue -> frame review -> edit/assembly -> QA -> delivery.
Each stage produces structured artifacts (JSON/Markdown) and is versioned. Tasks have dependencies, retries, timeouts and resource caps. Failed tasks must stay failed; simulated tasks are marked simulated.

## Future-compatible modules
- Blender Python scene generation and render adapter
- FFmpeg assembly/transcoding adapter
- OpenTimelineIO timeline interchange
- glTF/ USD asset interchange where practical
- SQLite task ledger, manifests, hashes, audit log
- GPU telemetry via optional NVIDIA tools; CPU fallback; measured throughput only
- Local model adapters (optional) with model license and hardware checks
- Optional remote providers: disabled until configured and user-approved
- Accessibility captions, subtitles, language versions and metadata
- Shot-level quality-control checklist and review thumbnails

## Cost and safety gates
- Free/local execution by default; remote inference and cloud rendering disabled.
- Before a paid or metered service, display provider, estimated cost and require explicit approval.
- Queue concurrency defaults to one local worker. Increase only after measurements.
- Secrets go in environment variables or a secret store, not source code.
- This system does not claim a virtual capacity count represents actual compute.
