# NEXUS Virtual Cinema Chip — ChatGPT connection and feature queue

The project contains an MCP server and a separate local Blender preview task core. One trillion virtual slots are a sparse logical namespace, not GPUs, throughput or concurrent render workers.

## ChatGPT custom MCP connection
Custom MCP support and write actions depend on ChatGPT plan/workspace and current interface availability. On ChatGPT web, check Settings and Apps/Connectors or developer MCP options. If custom MCP is supported in your account, configure the server URL and its authentication there. The server must be securely reachable; a localhost URL is not reachable by ChatGPT cloud. Do not expose an unauthenticated server publicly. Use HTTPS, authentication, restrictive tool scopes, and never put tokens in GitHub.

If your account interface doesn't support custom MCP write connections, use the local core and Blender workflow separately; this isn't a direct ChatGPT integration.

## Local preview-task workflow
Install Blender and ensure its executable is on PATH. From the project folder:
```powershell
python nexus_chip_core.py status
python nexus_chip_core.py demo
python nexus_chip_core.py render-once
```
Render jobs can be blocked, failed or completed. Only a completed task indicates actual execution success. No paid APIs or cloud GPUs are connected.
