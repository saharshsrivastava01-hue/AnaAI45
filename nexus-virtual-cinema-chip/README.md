# NEXUS Virtual Cinema Chip

A free-first MCP server for film pre-production and immersive 4D cue planning.

## What works in this starter
- ChatGPT-callable MCP tools (once connected through a supported custom MCP setup)
- SQLite project, scene, asset, 4D cue and render-queue records
- JSON production-package export
- No paid APIs, cloud renderers or external provider calls

## Honest capability boundaries
This is a software orchestration prototype, not a physical GPU/TPU. The virtual
GPU/TPU numbers shown by `chip_status` are design/simulation targets only.
Render jobs are queue records, not rendered footage. 4D cues are metadata;
they do not activate motion seats, wind, vibration or other physical devices.

## Run locally (Windows 11)
1. Install Python 3.11 or newer.
2. Open PowerShell in this folder.
3. Create a virtual environment:
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
5. Start the MCP server:
   ```powershell
   python server.py
   ```

The server listens on localhost port 8000 using the MCP HTTP transport.
Keep it local while testing. Do not expose it to the internet without TLS,
authentication, access controls and a secure deployment.

## ChatGPT connection
This repository contains the MCP server implementation, but does not itself
connect a ChatGPT account. A supported ChatGPT plan/workspace and the current
ChatGPT web custom-connector workflow are required. The server must be reachable
through a secure HTTPS endpoint. Never paste API keys or passwords into chat or
commit them to this repository.

## Tools
- `chip_status`
- `create_film_project`
- `add_scene`
- `add_asset`
- `add_4d_cue`
- `queue_render_job`
- `get_project`
- `export_project_json`

## Next milestones
1. Test local MCP transport and tools.
2. Add optional LLM screenplay generation with explicit user-configured secrets.
3. Connect Blender for real 3D scene generation.
4. Add a selectable real video-render provider (disabled by default).
5. Build a 4D playback adapter for compatible venue hardware.
