"""Procedural Blender scene generator for NEXUS proof-of-pipeline.
Run via chip core; this script creates a short preview shot. No external assets required.
"""
import bpy, math, json, sys, argparse
from mathutils import Vector
args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
ap=argparse.ArgumentParser();ap.add_argument("--spec",required=True);opts=ap.parse_args(args)
spec=json.load(open(opts.spec,encoding="utf-8"))
out=spec["output_dir"];frames=int(spec.get("duration_seconds",5)*spec.get("fps",24))
bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
sc=bpy.context.scene;sc.render.engine="BLENDER_EEVEE_NEXT";sc.render.resolution_x=spec.get("resolution",[1280,720])[0];sc.render.resolution_y=spec.get("resolution",[1280,720])[1];sc.render.fps=spec.get("fps",24);sc.frame_end=frames
sc.render.image_settings.file_format="PNG";sc.render.filepath=out+"/frame_";sc.world.color=(0.001,0.002,0.008)
def mat(name,color,metal=0,rough=.5,emission=None,strength=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;b=m.node_tree.nodes.get("Principled BSDF");b.inputs["Base Color"].default_value=(*color,1);b.inputs["Metallic"].default_value=metal;b.inputs["Roughness"].default_value=rough
 if emission:b.inputs["Emission Color"].default_value=(*emission,1);b.inputs["Emission Strength"].default_value=strength
 return m
earthmat=mat("Ocean blue",(0.015,.08,.22),.1,.3); black=mat("Obsidian",(.001,.001,.002),.6,.25); amber=mat("Amber",(1,.16,.025),.2,.25,(1,.08,.01),3);metal=mat("Alloy",(.25,.3,.36),.7,.3);panel=mat("Panel",(.015,.04,.12),.5,.3)
bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=5);earth=bpy.context.object;earth.name="EARTH";earth.data.materials.append(earthmat);bpy.ops.object.shade_smooth()
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=5.08);halo=bpy.context.object;halo.name="ATMOSPHERE_RIM";halo.scale=(1,1,1);halo.data.materials.append(mat("Rim blue",(.02,.1,.3),0,.6,(.01,.1,.5),.25))
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1.35,location=(7.5,0,2));w=bpy.context.object;w.name="THE_WITNESS";w.data.materials.append(black)
# Angular glowing seam using curve
c=bpy.data.curves.new("Signal seam","CURVE");c.dimensions="3D";c.bevel_depth=.025;c.bevel_resolution=2;s=c.splines.new("POLY");s.points.add(3)
for p,co in zip(s.points,[(-1,-.7,0,1),(-.4,-1,.5,1),(.5,-.9,.2,1),(1,-.3,0,1)]):p.co=co
o=bpy.data.objects.new("AMBER_SEAM",c);sc.collection.objects.link(o);o.parent=w;c.materials.append(amber)
# Satellite block and solar panels
bpy.ops.mesh.primitive_cube_add(size=.6,location=(2.2,-4.8,2.5));sat=bpy.context.object;sat.name="SATELLITE";sat.data.materials.append(metal)
for side in (-1,1):
 bpy.ops.mesh.primitive_cube_add(size=1,location=(2.2+side, -4.8,2.5));wing=bpy.context.object;wing.scale=(.85,.05,.35);wing.data.materials.append(panel);wing.parent=sat;wing.location=(side*1.4,0,0)
# point stars
import random;random.seed(2090);verts=[]
for _ in range(650):
 v=Vector((random.uniform(-1,1),random.uniform(-1,1),random.uniform(-1,1)))
 if v.length>0.01:verts.append(tuple(v.normalized()*random.uniform(25,40)))
me=bpy.data.meshes.new("Star mesh");me.from_pydata(verts,[],[]);stars=bpy.data.objects.new("STARFIELD",me);sc.collection.objects.link(stars);stars.data.materials.append(mat("Starlight",(.8,.8,1),0,.5,(.6,.7,1),1))
bpy.ops.object.light_add(type="SUN",location=(-8,-6,8));sun=bpy.context.object;sun.data.energy=3;sun.rotation_euler=(.5,.4,-.6)
bpy.ops.object.camera_add(location=(.2,-17,5));cam=bpy.context.object;cam.data.lens=42;cam.rotation_euler=(Vector((1,0,.6))-cam.location).to_track_quat("-Z","Y").to_euler();sc.camera=cam
cam.keyframe_insert("location",frame=1);cam.location.x=1.4;cam.location.z=4.7;cam.keyframe_insert("location",frame=frames)
w.keyframe_insert("rotation_euler",frame=1);w.rotation_euler=(.4,.5,.8);w.keyframe_insert("rotation_euler",frame=frames)
earth.keyframe_insert("rotation_euler",frame=1);earth.rotation_euler.z=math.radians(20);earth.keyframe_insert("rotation_euler",frame=frames)
for obj in (cam,w,earth):
 if obj.animation_data and obj.animation_data.action:
  for fc in obj.animation_data.action.fcurves:
   for k in fc.keyframe_points:k.interpolation="LINEAR"
sc.view_settings.view_transform="AgX";sc.render.filepath=out+"/frame_";sc.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=out+"/scene.blend")
bpy.ops.render.render(animation=True)
print("Frames rendered to",out)
