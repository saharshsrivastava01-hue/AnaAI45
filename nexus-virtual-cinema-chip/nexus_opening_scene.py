# NEXUS 2090 — Blender proof-of-pipeline scene
# Run with Blender 4.x:
# blender -b --python nexus_opening_scene.py
#
# Creates a procedural 5-second orbital establishing shot and renders an MP4.
# This is a small proof-of-pipeline, not the complete feature film.
import bpy, math, random
from mathutils import Vector

# Reset scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.meshes):
    pass

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 120
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.filepath = "//NEXUS_2090_OPENING_PREVIEW.mp4"
scene.world.color = (0.001, 0.002, 0.008)
scene.render.film_transparent = False

def principled(name, color, metallic=0.0, roughness=0.5, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*color, 1)
    bs.inputs["Metallic"].default_value = metallic
    bs.inputs["Roughness"].default_value = roughness
    if emission:
        bs.inputs["Emission Color"].default_value = (*emission, 1)
        bs.inputs["Emission Strength"].default_value = emission_strength
    return mat

earth_mat = principled("Earth | deep ocean", (0.012, 0.07, 0.19), 0.15, 0.32)
cloud_mat = principled("Clouds | soft white", (0.65, 0.78, 0.9), 0.0, 0.9)
black_mat = principled("The Witness | light absorbing black", (0.0005, 0.0007, 0.001), 0.65, 0.22)
amber_mat = principled("Witness seam | amber", (0.8, 0.22, 0.025), 0.2, 0.25, (1.0, 0.12, 0.01), 2.5)
sat_mat = principled("Satellite | ceramic alloy", (0.23, 0.28, 0.34), 0.8, 0.28)
panel_mat = principled("Solar panels | blue", (0.008, 0.035, 0.11), 0.65, 0.3)

# Earth
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=5, location=(0, 0, 0))
earth = bpy.context.object
earth.name = "EARTH_2090"
earth.data.materials.append(earth_mat)
bpy.ops.object.shade_smooth()
earth.rotation_euler[2] = math.radians(-18)
earth.keyframe_insert(data_path="rotation_euler", frame=1)
earth.rotation_euler[2] = math.radians(2)
earth.keyframe_insert(data_path="rotation_euler", frame=120)

# Atmospheric halo
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=5.12, location=(0, 0, 0))
atmo = bpy.context.object
atmo.name = "EARTH_ATMOSPHERE"
atmo_mat = bpy.data.materials.new("Atmosphere | blue rim")
atmo_mat.diffuse_color = (0.025, 0.18, 0.55, 0.16)
atmo_mat.use_nodes = True
nodes = atmo_mat.node_tree.nodes
bs = nodes.get("Principled BSDF")
bs.inputs["Base Color"].default_value = (0.015, 0.12, 0.5, 1)
bs.inputs["Alpha"].default_value = 0.12
bs.inputs["Metallic"].default_value = 0.0
bs.inputs["Roughness"].default_value = 0.25
try:
    atmo_mat.surface_render_method = "DITHERED"
except Exception:
    pass
atmo.data.materials.append(atmo_mat)
bpy.ops.object.shade_smooth()

# The Witness: low-poly geometric object, slowly reorienting
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1.25, location=(7.6, 0.0, 2.0))
witness = bpy.context.object
witness.name = "THE_WITNESS"
witness.scale = (1.0, 1.0, 1.0)
witness.data.materials.append(black_mat)
witness.rotation_euler = (math.radians(12), math.radians(18), math.radians(-8))
witness.keyframe_insert(data_path="rotation_euler", frame=1)
witness.rotation_euler = (math.radians(18), math.radians(30), math.radians(16))
witness.keyframe_insert(data_path="rotation_euler", frame=120)
witness.location.x = 8.5
witness.keyframe_insert(data_path="location", frame=1)
witness.location.x = 7.6
witness.keyframe_insert(data_path="location", frame=120)

# Thin amber edge motif, represented by a glowing line on the near-facing facet
curve = bpy.data.curves.new("Amber signal seam", type="CURVE")
curve.dimensions = "3D"
curve.bevel_depth = 0.018
curve.bevel_resolution = 3
spline = curve.splines.new("POLY")
spline.points.add(2)
for p, co in zip(spline.points, [(0.0, -1.22, 0.0, 1), (0.7, -0.82, 0.15, 1), (1.15, -0.12, 0.0, 1)]):
    p.co = co
seam = bpy.data.objects.new("WITNESS_AMBER_SEAM", curve)
scene.collection.objects.link(seam)
seam.parent = witness
seam.location = (0, 0, 0)
curve.materials.append(amber_mat)

# Distant satellite with simple solar wings
bpy.ops.mesh.primitive_cube_add(size=1, location=(2.2, -4.8, 2.4))
sat = bpy.context.object
sat.name = "ORBITAL_MAINTENANCE_SATELLITE"
sat.scale = (0.42, 0.28, 0.28)
sat.data.materials.append(sat_mat)
for side in (-1, 1):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(2.2 + side * 0.95, -4.8, 2.4))
    wing = bpy.context.object
    wing.name = "SOLAR_WING"
    wing.scale = (0.9, 0.045, 0.42)
    wing.data.materials.append(panel_mat)
    wing.parent = sat
    wing.location = (side * 1.4, 0, 0)

# Starfield
random.seed(2090)
verts = []
for _ in range(500):
    # points on a distant spherical shell
    v = Vector((random.uniform(-1,1), random.uniform(-1,1), random.uniform(-1,1)))
    if v.length < 0.1:
        continue
    v.normalize()
    verts.append(tuple(v * random.uniform(28, 42)))
mesh = bpy.data.meshes.new("STARFIELD_MESH")
mesh.from_pydata(verts, [], [])
stars = bpy.data.objects.new("STARFIELD", mesh)
scene.collection.objects.link(stars)
star_mat = principled("Starlight", (0.7, 0.8, 1.0), emission=(0.55,0.65,1.0), emission_strength=1.4)
stars.data.materials.append(star_mat)

# Lighting
bpy.ops.object.light_add(type="AREA", location=(-7, -8, 8))
key = bpy.context.object
key.name = "SUN_KEY"
key.data.energy = 4200
key.data.shape = "DISK"
key.data.size = 7
key.rotation_euler = (math.radians(25), 0, math.radians(-35))

bpy.ops.object.light_add(type="AREA", location=(4, 5, 3))
rim = bpy.context.object
rim.name = "EARTH_RIM"
rim.data.energy = 900
rim.data.color = (0.08, 0.25, 1.0)
rim.data.size = 5
rim.rotation_euler = (math.radians(45), 0, math.radians(145))

# Camera
bpy.ops.object.camera_add(location=(0.4, -16.5, 5.0))
cam = bpy.context.object
cam.name = "CAMERA_ORBITAL_ESTABLISHING"
target = Vector((1.0, 0.0, 0.6))
direction = target - cam.location
cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 42
scene.camera = cam
cam.keyframe_insert(data_path="location", frame=1)
cam.location.x = 1.2
cam.location.z = 4.7
cam.keyframe_insert(data_path="location", frame=120)

# Gentle contrast, avoid expensive effects on modest hardware
scene.view_settings.view_transform = "AgX"
scene.render.image_settings.color_mode = "RGB"
scene.render.resolution_percentage = 75  # preview-safe; increase for final output
scene.render.filepath = "//NEXUS_2090_OPENING_PREVIEW.mp4"

# Linear interpolation for slow cinematic movement
for obj in (earth, witness, cam):
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            for keyframe in fc.keyframe_points:
                keyframe.interpolation = "LINEAR"

scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath="//NEXUS_2090_OPENING.blend")
bpy.ops.render.render(animation=True)
print("NEXUS opening preview render complete: //NEXUS_2090_OPENING_PREVIEW.mp4")
