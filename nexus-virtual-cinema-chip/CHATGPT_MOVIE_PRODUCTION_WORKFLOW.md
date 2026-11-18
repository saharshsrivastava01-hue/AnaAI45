# NEXUS ChatGPT Movie Production Workflow

## Purpose
This file defines the practical path from a ChatGPT film brief to a structured NEXUS production package and, when a local renderer is installed, rendered scene files.

## What exists today
- `server.py` exposes project, scene, asset, 4D cue, render-queue and JSON-export tools through FastMCP.
- The SQLite render queue is metadata only. A queued job is not a rendered frame.
- The virtual GPU/TPU slot counts are scheduling concepts, not physical compute.
- No ChatGPT connection, cloud renderer, paid provider, or finished film is activated by this document.

## ChatGPT workflow
1. Write the film brief in ChatGPT: title, premise, genre, target runtime, rating, language, visual references described in words, aspect ratio and delivery format.
2. Ask ChatGPT to create a screenplay, character bible, world bible, scene breakdown and shot list.
3. If the NEXUS MCP server has been securely connected as a ChatGPT app/connector in an account that supports custom MCP connections, ask ChatGPT to call `create_film_project`.
4. Add every scene with `add_scene`. Register reusable characters, locations, props and sound assets with `add_asset`.
5. Add timed sensory metadata with `add_4d_cue` only as a production cue sheet; no physical 4D equipment is activated.
6. Export the package with `export_project_json` and save the JSON in the production folder.
7. Generate or create assets with tools the user has explicitly selected. Record each asset's source, license and local path.
8. Render locally with Blender only after Blender is installed and a real render adapter is configured. Assemble rendered clips with FFmpeg. Review continuity, audio, captions and export settings before delivery.

## Secure connection requirements
- The included server binds to 127.0.0.1 by default. A cloud-hosted ChatGPT service cannot reach a private localhost address.
- For a remote custom MCP connection, deploy the server to a reachable HTTPS endpoint and add authentication, authorization, request limits and secret management first.
- Never expose an unauthenticated MCP endpoint to the public internet.
- Do not paste API keys, webhook URLs, passwords or tokens into prompts, source code, issues or public repository files.
- ChatGPT account eligibility and connector setup UI can vary. A repository commit does not connect the server to ChatGPT. Verify by successfully listing and calling `chip_status` from the ChatGPT connection.

## Local Windows quick start
1. Install Python 3.11 or newer.
2. Open PowerShell in this folder.
3. Create and activate a virtual environment:
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Start the local MCP server:
   ```powershell
   python server.py
   ```
5. Keep it local until a secure remote deployment and authentication layer have been configured.

## Movie completion gates
A film is complete only when all required scene media actually exists, all media has been assembled, audio has been mixed, the final file has been exported, and the export has been played back and checked. A screenplay, storyboard, prompt pack, project record or render-queue item is not a movie.

## Free-first production profile
- Prefer local Blender and FFmpeg.
- Use preview resolution and short test shots before attempting long sequences.
- The Dell Inspiron 3501 configuration documented for this project has 8 GB RAM and an MX330 2 GB GPU; treat 4K/long-form rendering as a target, not a guaranteed local capability.
- Keep optional cloud and paid model integrations disabled unless the user explicitly approves their cost.
