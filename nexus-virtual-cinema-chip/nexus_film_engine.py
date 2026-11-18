#!/usr/bin/env python3
"""NEXUS-3000 Film Engine: procedural cinematic renderer.

Creates a real Blender scene and renders it through the Blender executable,
then assembles an MP4 with FFmpeg. The virtual-chip modules are schedulers;
they do not create GPU compute or access ChatGPT's private infrastructure.

Quick start:
  python nexus_film_engine.py doctor
  python nexus_film_engine.py create --prompt "An alien intelligence awakens"
  python nexus_film_engine.py render nexus_projects/<id>

Requires Blender and FFmpeg installed and available on PATH.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path.cwd()
PROJECTS = ROOT / "nexus_projects"

BLENDER_SCRIPT = r"""
import bpy, math, os, random
from mathutils import Vector

# NEXUS procedural sci-fi scene generator
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
W = int(os.environ.get('NX_WIDTH', '1280'))
H = int(os.environ.get('NX_HEIGHT', '720'))
FPS = int(os.environ.get('NX_FPS', '24'))
FRAMES = int(os.environ.get('NX_FRAMES', str(FPS * 10)))
OUT = os.environ['NX_FRAME_DIR']
BLEND = os.environ['NX_BLEND_FILE']

scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys() else 'BLENDER_EEVEE'
scene.render.resolution_x = W
scene.render.resolution_y = H
scene.render.resolution_percentage = 100
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = FRAMES
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = os.path.join(OUT, 'frame_')
scene.render.film_transparent = False
scene.render.image_settings.color_depth = '8'
scene.view_settings.view_transform = 'Standard'
scene.render.engine = scene.render.engine

def emission(name, color, strength, metallic=0.0, roughness=0.35):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Emission Color'].default_value = (*color, 1)
    p.inputs['Emission Strength'].default_value = strength
    return m

plasma = emission('NEXUS cyan plasma', (0.015, 0.28, 0.8), 2.8, 0.65)
gold = emission('Ancient alien gold', (0.9, 0.42, 0.045), 1.2, 0.8)
ice = emission('Neural light', (0.08, 0.72, 1.0), 3.2)
dark = emission('Obsidian alloy', (0.008, 0.018, 0.045), 0.15, 0.9)
white = emission('Stars', (0.65, 0.82, 1.0), 2.0)

# Hero object: a dark metallic sphere with a luminous neural shell.
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=2.0, location=(0,0,0))
core = bpy.context.object
core.name = 'NEXUS Alien Intelligence Core'
core.data.materials.append(dark)
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1.83, location=(0,0,0))
shell = bpy.context.object
shell.name = 'Energy membrane'
shell.scale = (1, 1, 1)
shell.data.materials.append(plasma)
# Wireframe shell creates a technical lattice.
wire = shell.modifiers.new('Neural lattice', 'WIREFRAME')
wire.thickness = 0.018
wire.use_replace = True

# Intersecting orbital rings.
for i in range(7):
    bpy.ops.mesh.primitive_torus_add(major_radius=2.6 + i*0.19, minor_radius=0.018,
        major_segments=128, minor_segments=8,
        location=(0,0,0),
        rotation=(math.radians(28+i*21), math.radians(i*29), math.radians(i*13)))
    ring = bpy.context.object
    ring.name = 'Orbital data ring'
    ring.data.materials.append(gold if i % 3 == 0 else ice)
    ring.rotation_euler[2] += math.tau * (1 if i % 2 == 0 else -1)
    ring.keyframe_insert(data_path='rotation_euler', frame=FRAMES)

# Neural nodes distributed on a spherical shell.
random.seed(3000)
for i in range(160):
    z = random.uniform(-1.0, 1.0)
    a = random.uniform(0, math.tau)
    r = 2.12 * math.sqrt(1-z*z)
    loc = (r*math.cos(a), r*math.sin(a), z*2.12)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
        radius=random.uniform(0.025, 0.065), location=loc)
    node = bpy.context.object
    node.data.materials.append(ice if i % 4 else gold)

# Starfield.
for i in range(500):
    loc = (random.uniform(-24,24), random.uniform(-5,25), random.uniform(-15,15))
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,
        radius=random.uniform(0.012,0.035), location=loc)
    bpy.context.object.data.materials.append(white)

# Cinematic floor grid.
for x in range(-12,13):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x*1.2, 4, -5))
    obj=bpy.context.object; obj.name='Distant grid line'
    obj.scale=(0.008, 24, 0.008); obj.data.materials.append(ice)
for y in range(-12,13):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, y*1.2+4, -5))
    obj=bpy.context.object; obj.name='Distant grid crossline'
    obj.scale=(15, 0.008, 0.008); obj.data.materials.append(plasma)

# Camera and animated dolly.
bpy.ops.object.camera_add(location=(0,-17,4.2))
cam=bpy.context.object
cam.data.lens=42
cam.rotation_euler=(math.radians(78),0,0)
scene.camera=cam
cam.location=(0,-18,4.5); cam.keyframe_insert(data_path='location', frame=1)
cam.location=(1.0,-14.5,2.6); cam.keyframe_insert(data_path='location', frame=FRAMES)
cam.rotation_euler=(math.radians(78),0,0); cam.keyframe_insert(data_path='rotation_euler', frame=1)
cam.rotation_euler=(math.radians(84),0,math.radians(3)); cam.keyframe_insert(data_path='rotation_euler', frame=FRAMES)

# Lighting.
for loc, power, color, size in [
    ((5,-7,7),2200,(0.08,0.32,1),8),
    ((-6,1,4),1700,(0.02,0.75,1),7),
    ((0,6,-3),1300,(1.0,0.32,0.06),6)]:
    bpy.ops.object.light_add(type='AREA', location=loc)
    light=bpy.context.object
    light.data.energy=power; light.data.color=color
    light.data.shape='DISK'; light.data.size=size

world = bpy.data.worlds.new('NEXUS deep cosmos') if not bpy.data.worlds else bpy.data.worlds[0]
scene.world=world; world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(0.001,0.003,0.015,1)
world.node_tree.nodes['Background'].inputs[1].default_value=0.35

# Subtle bloom through compositor glare.
scene.use_nodes=True
nt=scene.node_tree; nt.nodes.clear()
rl=nt.nodes.new('CompositorNodeRLayers')
gl=nt.nodes.new('CompositorNodeGlare')
gl.glare_type='FOG_GLOW'
gl.quality='MEDIUM'
gl.threshold=1.2
comp=nt.nodes.new('CompositorNodeComposite')
nt.links.new(rl.outputs['Image'], gl.inputs['Image'])
nt.links.new(gl.outputs['Image'], comp.inputs['Image'])

# Smooth interpolation.
for obj in scene.objects:
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            for key in fc.keyframe_points:
                key.interpolation='BEZIER'

bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.render.render(animation=True)
"""

def call(cmd: list[str], env: dict[str, str] | None = None) -> None:
    print("$ " + " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, env=env, check=True)

def doctor(_: argparse.Namespace) -> None:
    print("NEXUS-3000 Film Engine preflight")
    for name in ("blender", "ffmpeg"):
        p = shutil.which(name)
        print(f"{name}: {p or 'NOT INSTALLED / NOT ON PATH'}")
    print("ChatGPT private GPU access: unavailable as a programmable backend")
    print("Paid model calls: none; this engine does not submit paid jobs")
    print("A real render requires Blender and FFmpeg on an accessible machine.")

def create(args: argparse.Namespace) -> None:
    if args.duration < 1 or args.fps < 1:
        raise SystemExit("duration and fps must be positive")
    pid = uuid.uuid4().hex[:10]
    folder = PROJECTS / pid
    for name in ("frames", "exports", "assets"):
        (folder / name).mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": pid, "title": args.title, "prompt": args.prompt,
        "duration_seconds": args.duration, "fps": args.fps,
        "width": args.width, "height": args.height,
        "frame_count": args.duration * args.fps,
        "logical_chip": ["VTPU","VGPU","VFXU","VRPU","VMEDIA","VMEM","VNoC"],
        "backend": "Blender procedural renderer + FFmpeg encoder",
        "status": "created", "created_at": time.time(),
        "output": "exports/NEXUS_FILM.mp4",
        "limitation": "Procedural 3D film preview; not generative AI video."
    }
    (folder / "project.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (folder / "scene_generator.py").write_text(BLENDER_SCRIPT, encoding="utf-8")
    print(f"Created project {pid}: {folder}")
    print(f"Frames planned: {manifest['frame_count']} at {args.fps} fps")
    print("Ready for render. No rendering has run yet.")

def render(args: argparse.Namespace) -> None:
    folder = Path(args.project).resolve()
    manifest_path = folder / "project.json"
    if not manifest_path.exists():
        raise SystemExit(f"Project manifest not found: {manifest_path}")
    blender, ffmpeg = shutil.which("blender"), shutil.which("ffmpeg")
    if not blender or not ffmpeg:
        raise SystemExit("Install Blender and FFmpeg and ensure both commands are on PATH. Run doctor.")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    env = os.environ.copy()
    env.update({
        "NX_WIDTH": str(data["width"]), "NX_HEIGHT": str(data["height"]),
        "NX_FPS": str(data["fps"]), "NX_FRAMES": str(data["frame_count"]),
        "NX_FRAME_DIR": str((folder / "frames").resolve()),
        "NX_BLEND_FILE": str((folder / "NEXUS_scene.blend").resolve()),
    })
    call([blender, "-b", "-t", str(args.threads), "--python",
          str(folder / "scene_generator.py")], env=env)
    # Blender writes frame_0001.png, frame_0002.png, ...
    output = folder / "exports" / "NEXUS_FILM.mp4"
    call([ffmpeg, "-y", "-framerate", str(data["fps"]),
          "-i", str(folder / "frames" / "frame_%04d.png"),
          "-c:v", "libx264", "-preset", "medium", "-crf", "19",
          "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)])
    data["status"] = "rendered"
    data["output"] = str(output)
    data["completed_at"] = time.time()
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"RENDER COMPLETE: {output}")

def main() -> None:
    p=argparse.ArgumentParser(description="NEXUS-3000 procedural cinema engine")
    sub=p.add_subparsers(dest="cmd", required=True)
    d=sub.add_parser("doctor"); d.set_defaults(fn=doctor)
    c=sub.add_parser("create")
    c.add_argument("--title", default="NEXUS: Alien Intelligence")
    c.add_argument("--prompt", required=True)
    c.add_argument("--duration", type=int, default=10)
    c.add_argument("--fps", type=int, default=24)
    c.add_argument("--width", type=int, default=1280)
    c.add_argument("--height", type=int, default=720)
    c.set_defaults(fn=create)
    r=sub.add_parser("render")
    r.add_argument("project")
    r.add_argument("--threads", type=int, default=2)
    r.set_defaults(fn=render)
    args=p.parse_args()
    args.fn(args)

if __name__ == "__main__":
    main()
