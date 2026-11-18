# NEXUS Virtual Cinema Chip — software prototype

A free-first local film orchestration prototype. The trillion logical scheduler slots are a sparse namespace target, **not** physical GPUs or concurrent execution.

## Core components
- SQLite-backed sparse task queue
- Bounded local worker execution (defaults to one worker)
- Blender CLI adapter with timeout and captured logs
- Procedural opening scene (Earth, geometric object, satellite, starfield, camera animation)
- Task states that distinguish blocked, failed and completed jobs

## Windows setup
1. Install Blender 4.x and make sure `blender` works in PowerShell.
2. Install Python 3.11+ (the core uses only standard-library Python).
3. Download the project folder.
4. From this directory:
   ```powershell
   python nexus_chip_core.py status
   python nexus_chip_core.py demo
   python nexus_chip_core.py render-once
   ```
5. Render output is written beneath `renders/<task-id>/`. It consists of PNG frames and a Blender scene file. Convert frames to video using FFmpeg if installed:
   ```powershell
   ffmpeg -framerate 24 -i renders/<task-id>/frame_%04d.png -c:v libx264 -pix_fmt yuv420p NEXUS_preview.mp4
   ```
   Check frame numbering against Blender's output naming before running FFmpeg.

## Safety / honesty
- Does not download models or call paid APIs.
- Local rendering only; no remote service or hardware modifications.
- The task queue is not a GPU benchmark.
- Render success is recorded only when Blender exits with code 0.
- For public network use, add authentication and transport security first.
