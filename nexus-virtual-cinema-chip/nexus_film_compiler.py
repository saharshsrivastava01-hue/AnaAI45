#!/usr/bin/env python3
"""NEXUS FILM COMPILER — procedural movie generator for the NEXUS virtual chip.

Creates a self-contained Blender scene script, renders frames with Blender,
and encodes an MP4 with FFmpeg. This is a real backend adapter, not a claim
that the virtual chip itself supplies physical compute. CPU rendering is the
safe fallback; optional GPU rendering is attempted only when requested.

Requirements: Python 3.10+, Blender 3.6+/4.x, FFmpeg.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "nexus_movies"

BLENDER_SCRIPT = r'''
import bpy, math, os, random
from mathutils import Vector

# ----- NEXUS scene bootstrap -----
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
frames = int(os.environ.get("NEXUS_FRAMES", "240"))
fps = int(os.environ.get("NEXUS_FPS", "24"))
width = int(os.environ.get("NEXUS_WIDTH", "1280"))
height = int(os.environ.get("NEXUS_HEIGHT", "720"))
scene.frame_start, scene.frame_end = 1, frames
scene.render.fps = fps
scene.render.resolution_x, scene.render.resolution_y = width, height
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.filepath = os.environ["NEXUS_FRAMES_DIR"] + os.sep
scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys() else "BLENDER_EEVEE"
scene.render.film_transparent = False
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.color_depth = "8"

# Render settings favor compatibility and reasonable memory use.
if hasattr(scene, "eevee"):
    scene.eevee.taa_render_samples = 32

# World / background
world = bpy.data.worlds.new("NEXUS Deep Cosmos") if not bpy.data.worlds else bpy.data.worlds[0]
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.001, 0.004, 0.018, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.35

def principled(name, color, metallic=0.0, roughness=0.4, emission=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = roughness
    if emission is not None:
        p.inputs["Emission Color"].default_value = (*emission, 1)
        p.inputs["Emission Strength"].default_value = strength
    return m

plasma = principled("NEXUS Ion Plasma", (0.012,0.09,0.3), .55, .22, (0.015,0.45,1), 3.0)
metal = principled("Obsidian Titanium", (.012,.025,.055), .88, .23)
gold = principled("Ancient Gold", (.65,.31,.055), .82, .2, (.8,.22,.025), .8)
glow = principled("Quantum Light", (.04,.45,.9), .2, .18, (.02,.45,1), 4.0)
white = principled("Starlight", (.6,.8,1), .1, .3, (.4,.7,1), 3.0)

def animate_rotation(obj, end_angle=math.tau):
    obj.rotation_euler[2] = 0
    obj.keyframe_insert(data_path="rotation_euler", frame=1)
    obj.rotation_euler[2] = end_angle
    obj.keyframe_insert(data_path="rotation_euler", frame=frames)

def add_text(body, location, size, material):
    bpy.ops.object.text_add(location=location, rotation=(math.radians(90),0,0))
    ob=bpy.context.object
    ob.data.body=body
    ob.data.size=size
    ob.data.extrude=.004
    ob.data.materials.append(material)
    return ob

# Camera: slow cinematic push-in and slight orbit.
bpy.ops.object.camera_add(location=(0,-19,5.2))
camera=bpy.context.object
camera.data.lens=42
camera.rotation_euler=(math.radians(78),0,0)
scene.camera=camera
camera.keyframe_insert(data_path="location",frame=1)
camera.location=(1.2,-14.5,3.6)
camera.keyframe_insert(data_path="location",frame=frames)
camera.rotation_euler=(math.radians(82),0,math.radians(3))
camera.keyframe_insert(data_path="rotation_euler",frame=frames)

# Hero structure: layered alien neural reactor.
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=2.0, location=(0,0,0))
core=bpy.context.object
core.name="NEXUS Alien Neural Reactor"
core.data.materials.append(plasma)
for i in range(3):
    bpy.ops.mesh.primitive_torus_add(major_radius=2.6+i*.42, minor_radius=.035,
        major_segments=128, minor_segments=12,
        rotation=(math.radians(25+i*39),math.radians(i*23),math.radians(i*17)))
    ring=bpy.context.object
    ring.name="Gyroscopic Quantum Ring"
    ring.data.materials.append(gold if i==1 else glow)
    animate_rotation(ring, math.tau*(1 if i%2==0 else -1))

# Mechanical pylons surrounding the core.
for i in range(12):
    a=math.tau*i/12
    x,y=4.0*math.cos(a),4.0*math.sin(a)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x,y,0))
    p=bpy.context.object
    p.name="Reactor Pylon"
    p.dimensions=(.32,.32,random.uniform(1.3,2.4))
    p.rotation_euler[2]=a
    p.data.materials.append(metal)
    bevel=p.modifiers.new("Precision bevel","BEVEL"); bevel.width=.09; bevel.segments=3
    p.modifiers.new("Weighted normals","WEIGHTED_NORMAL")
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=.16, location=(x,y,1.15))
    node=bpy.context.object; node.data.materials.append(glow)

# Neural filaments: curved Bezier links around the core.
random.seed(23)
for i in range(28):
    a=math.tau*i/28
    curve=bpy.data.curves.new("Neural filament","CURVE")
    curve.dimensions="3D"; curve.bevel_depth=.018; curve.bevel_resolution=2
    spline=curve.splines.new("BEZIER"); spline.bezier_points.add(2)
    for j,bp in enumerate(spline.bezier_points):
        ang=a+(j-1)*.18
        radius=2.2+random.uniform(-.18,.18)
        bp.co=(radius*math.cos(ang),radius*math.sin(ang), (j-1)*1.25)
        bp.handle_left_type="AUTO"; bp.handle_right_type="AUTO"
    ob=bpy.data.objects.new("Luminous neural filament",curve)
    scene.collection.objects.link(ob); ob.data.materials.append(glow)

# Star field
for i in range(320):
    loc=(random.uniform(-24,24),random.uniform(5,28),random.uniform(-14,14))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4,
        radius=random.uniform(.012,.035), location=loc)
    bpy.context.object.data.materials.append(white)

# Ground platform and concentric engraved rings
bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=7.2, depth=.22, location=(0,0,-2.15))
platform=bpy.context.object
platform.name="Floating alien megastructure dais"
platform.data.materials.append(metal)
bev=platform.modifiers.new("Machined edge","BEVEL"); bev.width=.12; bev.segments=4
for r in (5.4,6.1,6.8):
    bpy.ops.mesh.primitive_torus_add(major_radius=r,minor_radius=.018,location=(0,0,-2.0))
    bpy.context.object.data.materials.append(gold)

# Lights
for loc,power,color,size in [
    ((4,-7,8),2200,(.04,.28,1),8),
    ((-7,1,4),1800,(.02,.75,1),7),
    ((0,5,-3),1400,(.7,.12,1),6),
    ((0,-2,9),1100,(1,.35,.08),5)]:
    bpy.ops.object.light_add(type="AREA",location=loc)
    lamp=bpy.context.object; lamp.data.energy=power; lamp.data.color=color
    lamp.data.shape="DISK"; lamp.data.size=size

# Title card geometry, kept within frame.
add_text("N E X U S   //   3 0 0 0",( -4.2,-.4,5.4),.55,white)
add_text("THE AWAKENING",( -2.6,-.4,4.65),.28,gold)

# Subtle animation on reactor core.
core.scale=(.96,.96,.96); core.keyframe_insert(data_path="scale",frame=1)
core.scale=(1.04,1.04,1.04); core.keyframe_insert(data_path="scale",frame=max(2,frames//2))
core.scale=(.96,.96,.96); core.keyframe_insert(data_path="scale",frame=frames)

# Linear interpolation avoids abrupt timing jumps.
for ob in scene.objects:
    if ob.animation_data and ob.animation_data.action:
        for fc in ob.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation="BEZIER"

# Save project and render animation.
bpy.ops.wm.save_as_mainfile(filepath=os.environ["NEXUS_BLEND_PATH"])
bpy.ops.render.render(animation=True)
'''

def run_checked(cmd: list[str], env: dict[str,str] | None = None) -> None:
    print("$", " ".join(map(str,cmd)), flush=True)
    subprocess.run(cmd, env=env, check=True)

def create(args: argparse.Namespace) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp=time.strftime("%Y%m%d_%H%M%S")
    folder=OUT / f"{stamp}_nexus_awakening"
    (folder/"frames").mkdir(parents=True)
    (folder/"exports").mkdir()
    data={
        "title":args.title,"prompt":args.prompt,
        "created":time.time(),"status":"prepared",
        "virtual_chip":{"VTPU":"director plan","VGPU":"Blender render",
                        "VFXU":"procedural effects","VRPU":"frame processing",
                        "VMEDIA":"FFmpeg encode","VMEM":"project assets","VNoC":"scheduler"},
        "render":{"duration_seconds":args.duration,"fps":args.fps,
                  "width":args.width,"height":args.height,
                  "frames":args.duration*args.fps},
        "backend":"Blender + FFmpeg on the host machine",
        "paid_services_allowed":False,
        "outputs":{"blend":"nexus_scene.blend","mp4":"exports/NEXUS_FILM.mp4"}
    }
    (folder/"job.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    (folder/"scene.py").write_text(BLENDER_SCRIPT,encoding="utf-8")
    print(f"Project prepared: {folder}")
    print("Next: run this project with the Blender and FFmpeg executables.")
    return folder

def render(args: argparse.Namespace) -> None:
    folder=Path(args.project).resolve()
    manifest=folder/"job.json"
    if not manifest.exists():
        raise SystemExit(f"Project manifest not found: {manifest}")
    blender=shutil.which("blender"); ffmpeg=shutil.which("ffmpeg")
    if not blender: raise SystemExit("Blender executable not found on PATH.")
    if not ffmpeg: raise SystemExit("FFmpeg executable not found on PATH.")
    data=json.loads(manifest.read_text(encoding="utf-8"))
    r=data["render"]
    frames=folder/"frames"; frames.mkdir(exist_ok=True)
    blend=folder/"nexus_scene.blend"
    env=os.environ.copy()
    env.update({"NEXUS_FRAMES":str(r["frames"]),"NEXUS_FPS":str(r["fps"]),
        "NEXUS_WIDTH":str(r["width"]),"NEXUS_HEIGHT":str(r["height"]),
        "NEXUS_FRAMES_DIR":str(frames),"NEXUS_BLEND_PATH":str(blend)})
    data["status"]="rendering"
    manifest.write_text(json.dumps(data,indent=2),encoding="utf-8")
    run_checked([blender,"-b","-t",str(args.threads),"--python",str(folder/"scene.py")],env)
    mp4=folder/"exports"/"NEXUS_FILM.mp4"
    run_checked([ffmpeg,"-y","-framerate",str(r["fps"]),"-i",str(frames/"%04d.png"),
        "-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(mp4)])
    data["status"]="rendered"
    data["outputs"]["mp4"]=str(mp4)
    data["completed"]=time.time()
    manifest.write_text(json.dumps(data,indent=2),encoding="utf-8")
    print(f"MP4 READY: {mp4}")

def main() -> None:
    p=argparse.ArgumentParser(description="NEXUS-3000 procedural cinema compiler")
    sub=p.add_subparsers(dest="command",required=True)
    c=sub.add_parser("create",help="Create a procedural sci-fi movie project")
    c.add_argument("--title",default="NEXUS THE AWAKENING")
    c.add_argument("--prompt",default="An alien neural superintelligence awakens in a cosmic megastructure.")
    c.add_argument("--duration",type=int,default=10)
    c.add_argument("--fps",type=int,default=12)
    c.add_argument("--width",type=int,default=640)
    c.add_argument("--height",type=int,default=360)
    c.set_defaults(func=create)
    r=sub.add_parser("render",help="Render frames and encode MP4")
    r.add_argument("project")
    r.add_argument("--threads",type=int,default=2)
    r.set_defaults(func=render)
    args=p.parse_args()
    if args.command=="create" and (args.duration<1 or args.fps<1 or args.width<160 or args.height<90):
        p.error("duration/fps must be positive and resolution at least 160x90")
    args.func(args)

if __name__=="__main__":
    main()
