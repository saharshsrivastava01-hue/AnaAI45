"""Create a starter NEXUS 2090 production project on the running local MCP server.

Run with:
  python android_bootstrap_nexus2090.py

Requires the NEXUS server already running at http://127.0.0.1:8000/mcp.
This creates planning/database records only. It does not render video.
"""
import asyncio
import json
from fastmcp import Client

SERVER = "http://127.0.0.1:8000/mcp"

async def main():
    async with Client(SERVER) as client:
        status = await client.call_tool("chip_status", {})
        print("NEXUS SERVER:", status.data if hasattr(status, "data") else status)

        created = await client.call_tool("create_film_project", {
            "title": "NEXUS 2090: THE LAST INTELLIGENCE",
            "premise": (
                "In 2090, a deep-space research crew discovers a silent geometric "
                "object beyond Earth's orbit. Its signals appear to reconstruct "
                "memories, forcing the crew to decide whether it is a warning, "
                "a machine, or the last surviving intelligence."
            ),
            "genre": "science-fiction mystery adventure",
            "runtime_minutes": 100,
            "visual_style": "cinematic photorealism, monumental scale, restrained futuristic design",
            "aspect_ratio": "16:9",
            "resolution_target": "4K production target; device preview should use low resolution"
        })
        data = created.data if hasattr(created, "data") else created
        if isinstance(data, str):
            try: data = json.loads(data)
            except Exception: pass
        if not isinstance(data, dict) or not data.get("ok"):
            raise RuntimeError(f"Project creation failed: {data}")
        project_id = data["project_id"]
        print("\nPROJECT CREATED:", project_id)

        scenes = [
            {
                "title": "The Blue Planet",
                "description": "A slow orbital establishing shot of Earth at night. City lights trace coastlines. The camera glides above the atmosphere; a tiny research vessel crosses the frame.",
                "duration_seconds": 45,
                "camera": "ultra-wide orbital shot, slow stabilized push-in, gradual reveal",
                "vfx": "physically inspired cloud layers, atmospheric limb, subtle aurora, restrained starfield"
            },
            {
                "title": "The Silent Geometry",
                "description": "Beyond the vessel, a vast matte-black geometric object hangs motionless. Its edges catch a thin line of cold starlight. No obvious propulsion or surface markings.",
                "duration_seconds": 55,
                "camera": "long-lens reveal, slow lateral drift, scale-reference vessel in foreground",
                "vfx": "subtle gravitational lensing, sparse particles, high-contrast rim lighting"
            },
            {
                "title": "Signal Without Sound",
                "description": "Inside the observation deck, instruments register a repeating pulse. Reflections move across the crew's visors as the object aligns with the ship.",
                "duration_seconds": 50,
                "camera": "measured dolly through observation glass, close-up inserts of instruments",
                "vfx": "minimal holographic overlays, physically plausible reflections, restrained volumetric beams"
            },
            {
                "title": "The First Response",
                "description": "A pattern appears across the ship's display: a star map matching no known catalogue. The crew exchange uncertain looks as the ship's lights dim.",
                "duration_seconds": 60,
                "camera": "slow close-ups, controlled rack focus, final wide composition",
                "vfx": "procedural star-map graphics, soft display bloom, practical light changes"
            }
        ]

        for scene in scenes:
            result = await client.call_tool("add_scene", {
                "project_id": project_id, **scene
            })
            print("SCENE:", scene["title"], "->", result)

        assets = [
            ("THE WITNESS", "environment", "Enormous silent black geometric object in deep space; sharp silhouette, almost light-absorbing surface, no visible markings.", "Keep geometry, scale and surface appearance consistent in every shot."),
            ("ORBITAL RESEARCH VESSEL", "vehicle", "Compact modular deep-space research ship with realistic radiators, antennae and observation windows.", "Maintain identical hull layout, proportions and light placement."),
            ("EARTH 2090", "environment", "Photorealistic Earth from low orbit, detailed cloud systems, blue atmospheric limb and night-side city lights.", "Preserve geography and lighting continuity between orbital shots."),
            ("OBSERVATION CREW", "character_group", "Small international science crew in practical near-future pressure suits; grounded, functional costume design.", "Do not change suit markings, colours or helmet design between shots.")
        ]
        for name, kind, desc, continuity in assets:
            result = await client.call_tool("add_asset", {
                "project_id": project_id,
                "name": name,
                "asset_type": kind,
                "description": desc,
                "continuity_notes": continuity
            })
            print("ASSET:", name, "->", result)

        cues = [
            (1, 8.0, "lighting", "low", "Subtle cabin light dip as the object enters view."),
            (2, 20.0, "vibration", "low", "Metadata cue for a restrained low-frequency discovery pulse."),
            (3, 12.0, "wind", "low", "Optional venue airflow cue; metadata only."),
            (4, 42.0, "motion_seat", "low", "Optional gentle seat movement at the first response; metadata only.")
        ]
        for number, seconds, kind, intensity, description in cues:
            result = await client.call_tool("add_4d_cue", {
                "project_id": project_id,
                "scene_number": number,
                "time_seconds": seconds,
                "cue_type": kind,
                "intensity": intensity,
                "description": description
            })
            print("4D CUE:", number, seconds, "->", result)

        queued = await client.call_tool("queue_render_job", {
            "project_id": project_id,
            "scene_number": 1,
            "task": "opening_scene_preview",
            "profile": "android_low_resource_draft"
        })
        print("\nSIMULATED RENDER QUEUE:", queued)
        project = await client.call_tool("get_project", {"project_id": project_id})
        print("\nPROJECT SUMMARY")
        print("Project ID:", project_id)
        print("Four scenes, four asset records, four 4D cue records.")
        print("Render queue entry is metadata only; no frame or video was rendered.")
        print("\nSAVE THIS PROJECT ID:", project_id)

if __name__ == "__main__":
    asyncio.run(main())
