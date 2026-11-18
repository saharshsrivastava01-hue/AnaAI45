# NEXUS-3000 on Android (Termux)

This guide runs the existing NEXUS Virtual Cinema MCP prototype locally on an Android phone. It does not turn the phone into a physical GPU/TPU and it does not render a film by itself.

## Requirements
- Android 11 or newer; Samsung Galaxy M35 5G is suitable for lightweight orchestration.
- Termux installed from the official F-Droid or Termux GitHub source. Avoid old Play Store builds.
- Internet only for the initial package and repository download. Runtime can be local.

## Install and launch

Open Termux and run these commands one at a time:

```bash
pkg update -y && pkg upgrade -y
pkg install -y python git
git clone --branch nexus-virtual-cinema-chip https://github.com/saharshsrivastava01-hue/AnaAI45.git
cd AnaAI45/nexus-virtual-cinema-chip
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If the dependency installation fails, stop and copy the final error output. Do not install random packages or paste API keys into Termux.

Start the server:

```bash
python server.py
```

The current server binds to `127.0.0.1:8000` by default. Keep it local. Do not change the host to `0.0.0.0` or expose port 8000 publicly.

## Verify it is running

Open a second Termux session (swipe from the left edge and choose NEW SESSION), then run:

```bash
curl -i http://127.0.0.1:8000/mcp
```

An HTTP response, including an MCP protocol response or method-related response, confirms that a process is listening. A browser opening the MCP endpoint is not the same as a graphical dashboard.

## Data and limitations
- SQLite data is stored in the project working directory as `nexus_chip.sqlite3`.
- The existing tools manage film projects, scenes, assets, 4D cue metadata and simulated render-queue records.
- A queued render job is not a rendered frame or video.
- The repository's SystemVerilog RTL files are source code; Termux does not synthesize them into a chip.
- Android thermal limits and memory mean this phone should be used for control, planning and small tests—not large-scale rendering or trillion-core simulation.
- ChatGPT custom MCP integration is separate from running this local server. A local-only Android endpoint is not automatically accessible to ChatGPT.

## Stop the server
Return to the Termux session running the server and press `CTRL+C`.

## Troubleshooting
- If `git clone` says the folder exists, use `cd ~/AnaAI45/nexus-virtual-cinema-chip`.
- If `python -m pip install -r requirements.txt` fails, capture the complete error; package compatibility can change with Termux's Python version.
- If Android kills the process, keep Termux open and disable battery optimization for Termux while testing.
