#!/usr/bin/env python3
"""NEXUS-3000 Neuro-Cinema Runtime — local, honest, extensible film pipeline.

The "alien neuro" chip is a software-defined virtual fabric. VGPU/VTPU/VRPU
are logical devices scheduled onto real local backends; they are not physical
silicon and do not create compute capacity that the host does not have.

First milestone: generate a procedural sci-fi film scene with Blender, render
frames locally, and assemble MP4 with FFmpeg. No paid APIs or cloud jobs.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "nexus_output"

BLENDER_SCENE = r'''
import bpy, math, random, sys
from mathutils import Vector
# Clear scene
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys() else 'BLENDER_EEVEE'
scene.render.resolution_percentage=100
# camera
bpy.ops.object.camera_add(location=(0,-18,5), rotation=(math.radians(78),0,0))
cam=bpy.context.object; scene.camera=cam; cam.data.lens=42
# central alien neuro-core
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=2, location=(0,0,0))
core=bpy.context.object; core.name='NEXUS Neuro Core'
mat=bpy.data.materials.new('Neuro plasma'); mat.diffuse_color=(0.02,0.55,0.95,1); mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(0.01,0.18,0.55,1); bs.inputs['Metallic'].default_value=.65; bs.inputs['Emission Color'].default_value=(0.01,0.4,1,1); bs.inputs['Emission Strength'].default_value=2.5
core.data.materials.append(mat)
# orbital neural rings
for i in range(5):
    bpy.ops.mesh.primitive_torus_add(major_radius=2.8+i*.22, minor_radius=.025, major_segments=96, minor_segments=8,
       location=(0,0,0), rotation=(math.radians(25+i*28), math.radians(i*17), math.radians(i*31)))
    ring=bpy.context.object; ring.name='Neural orbital ring'
    rm=bpy.data.materials.new('Ion silver'); rm.diffuse_color=(.15,.7,1,1); rm.use_nodes=True
    rbs=rm.node_tree.nodes.get('Principled BSDF'); rbs.inputs['Base Color'].default_value=(.08,.3,.6,1); rbs.inputs['Metallic'].default_value=.9; rbs.inputs['Emission Color'].default_value=(.02,.3,1,1); rbs.inputs['Emission Strength'].default_value=1.4
    ring.data.materials.append(rm)
    ring.rotation_euler[2]=0; ring.keyframe_insert(data_path='rotation_euler',frame=1)
    ring.rotation_euler[2]=math.tau*(1 if i%2==0 else -1); ring.keyframe_insert(data_path='rotation_euler',frame=120)
# neural nodes
random.seed(19)
for i in range(90):
    phi=random.random()*math.tau; z=random.uniform(-1.6,1.6); r=math.sqrt(max(0,1-z*z/4))*2.15
    loc=(r*math.cos(phi),r*math.sin(phi),z)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6, radius=random.uniform(.025,.07), location=loc)
    node=bpy.context.object
    nm=bpy.data.materials.new('Neural node'); nm.diffuse_color=(.1,.8,1,1); nm.use_nodes=True
    nbs=nm.node_tree.nodes.get('Principled BSDF'); nbs.inputs['Base Color'].default_value=(.02,.35,.8,1); nbs.inputs['Emission Color'].default_value=(.02,.5,1,1); nbs.inputs['Emission Strength'].default_value=3
    node.data.materials.append(nm)
# starfield
for i in range(450):
    loc=(random.uniform(-22,22),random.uniform(4,24),random.uniform(-12,12))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=4, ring_count=3, radius=random.uniform(.012,.035), location=loc)
    star=bpy.context.object
    sm=bpy.data.materials.new('Star'); sm.diffuse_color=(.55,.8,1,1); sm.use_nodes=True
    sbs=sm.node_tree.nodes.get('Principled BSDF'); sbs.inputs['Emission Color'].default_value=(.4,.7,1,1); sbs.inputs['Emission Strength'].default_value=2
    star.data.materials.append(sm)
# lighting
for loc,power,color,size in [((4,-6,7),1800,(.05,.35,1),7),((-6,1,3),1400,(.1,.8,1),6),((0,5,-5),1100,(.2,.1,1),5)]:
    bpy.ops.object.light_add(type='AREA', location=loc); l=bpy.context.object; l.data.energy=power; l.data.color=color; l.data.shape='DISK'; l.data.size=size
# camera animation
cam.location=(0,-18,5); cam.keyframe_insert(data_path='location',frame=1)
cam.location=(1.5,-15,3.5); cam.keyframe_insert(data_path='location',frame=120)
cam.rotation_euler=(math.radians(78),0,0); cam.keyframe_insert(data_path='rotation_euler',frame=1)
cam.rotation_euler=(math.radians(83),0,math.radians(4)); cam.keyframe_insert(data_path='rotation_euler',frame=120)
# world
world=bpy.data.worlds.new('Deep space') if not bpy.data.worlds else bpy.data.worlds[0]
scene.world=world; world.use_nodes=True; world.node_tree.nodes['Background'].inputs[0].default_value=(.001,.003,.018,1); world.node_tree.nodes['Background'].inputs[1].default_value=.25
scene.view_settings.view_transform='Standard'
scene.frame_start=1; scene.frame_end=int(os.environ.get('NEXUS_FRAMES','120'))
scene.render.image_settings.file_format='PNG'
scene.render.filepath=os.environ.get('NEXUS_FRAMES_DIR','//frames/')+'/'
scene.camera.data.dof.use_dof=False
# render still sequence
bpy.ops.wm.save_as_mainfile(filepath=os.environ['NEXUS_BLEND_PATH'])
bpy.ops.render.render(animation=True)
'''

def run(cmd, **kw):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(list(map(str, cmd)), check=True, **kw)

def create(args):
    OUT.mkdir(exist_ok=True)
    job = OUT / "job.json"
    frames = 120 if args.full else 60
    fps = 24 if args.full else 12
    width,height = (1280,720) if args.full else (640,360)
    data = {"name":"NEXUS Neuro-Cinema: Awakening","prompt":args.prompt,
            "logical_devices":["VGPU","VTPU","VRPU","VMEDIA","VMEM","VNoC"],
            "backend":"local Blender; CPU fallback, optional supported GPU",
            "render":{"frames":frames,"fps":fps,"resolution":[width,height]},
            "status":"prepared","created_unix":time.time(),
            "note":"Logical accelerator fabric; actual work runs on available host hardware."}
    job.write_text(json.dumps(data,indent=2),encoding="utf-8")
    (OUT/"scene.py").write_text(BLENDER_SCENE,encoding="utf-8")
    print(f"Prepared {job}")
    print("Virtual neuro-fabric job graph created. No rendering has run yet.")

def execute(args):
    if not (OUT/"job.json").exists(): raise SystemExit("Run 'create' first.")
    blender=shutil.which("blender")
    ffmpeg=shutil.which("ffmpeg")
    if not blender: raise SystemExit("Blender not found. Install Blender, then rerun.")
    if not ffmpeg: raise SystemExit("FFmpeg not found. Install FFmpeg, then rerun.")
    data=json.loads((OUT/"job.json").read_text(encoding="utf-8"))
    render=data["render"]; frames_dir=OUT/"frames"; frames_dir.mkdir(parents=True,exist_ok=True)
    blend=OUT/"nexus_neuro_cinema.blend"
    env=os.environ.copy(); env["NEXUS_FRAMES"]=str(render["frames"])
    env["NEXUS_FRAMES_DIR"]=str(frames_dir); env["NEXUS_BLEND_PATH"]=str(blend)
    # Blender's script uses output directory passed through environment.
    run([blender,"-b","-t","2","--python",OUT/"scene.py"],env=env)
    mp4=OUT/"NEXUS_NEURO_CINEMA.mp4"
    run([ffmpeg,"-y","-framerate",str(render["fps"]),"-i",frames_dir/"%04d.png",
         "-c:v","libx264","-pix_fmt","yuv420p","-crf","20","-movflags","+faststart",mp4])
    data["status"]="rendered"; data["output"]=str(mp4)
    (OUT/"job.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    print(f"Film preview created: {mp4}")

def main():
    p=argparse.ArgumentParser(description="NEXUS-3000 virtual neuro-cinema chip")
    sub=p.add_subparsers(dest="cmd",required=True)
    c=sub.add_parser("create"); c.add_argument("--prompt",default="An alien neural superintelligence awakens in deep space"); c.add_argument("--full",action="store_true"); c.set_defaults(fn=create)
    r=sub.add_parser("run"); r.set_defaults(fn=execute)
    sub.add_parser("status").set_defaults(fn=lambda a: print((OUT/"job.json").read_text() if (OUT/"job.json").exists() else "No job yet."))
    a=p.parse_args(); a.fn(a)
if __name__=="__main__": main()
