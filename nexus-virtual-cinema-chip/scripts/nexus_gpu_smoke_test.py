# Run with: blender -b -P scripts/nexus_gpu_smoke_test.py
import bpy, json, os
from mathutils import Vector
def log(obj): print("NEXUS_GPU_REPORT=" + json.dumps(obj, default=str))
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 8
scene.render.resolution_x, scene.render.resolution_y = 320, 180
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
out_dir = os.path.abspath("nexus_gpu_test_output")
os.makedirs(out_dir, exist_ok=True)
scene.render.filepath = os.path.join(out_dir, "nexus_gpu_smoke.png")
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_monkey_add(location=(0, 0, 0))
obj = bpy.context.object
mat = bpy.data.materials.new("NEXUS_Test_Material")
mat.diffuse_color = (0.08, 0.35, 0.8, 1.0)
obj.data.materials.append(mat)
bpy.ops.object.camera_add(location=(4, -6, 3))
cam = bpy.context.object
cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam
bpy.ops.object.light_add(type="AREA", location=(2, -3, 4))
bpy.context.object.data.energy = 500
prefs = bpy.context.preferences.addons["cycles"].preferences
try:
    prefs.get_devices()
    devices = [{"name": d.name, "type": d.type, "use": d.use} for d in prefs.devices]
except Exception as exc:
    log({"stage": "device-enumeration", "error": str(exc)})
    raise
cuda_devices = [d for d in prefs.devices if d.type == "CUDA"]
if not cuda_devices:
    log({"stage": "blocked", "reason": "Blender did not expose a CUDA device", "devices": devices})
    raise SystemExit(20)
for d in prefs.devices: d.use = (d.type == "CUDA")
prefs.compute_device_type = "CUDA"
scene.cycles.device = "GPU"
log({"stage": "render-start", "engine": scene.render.engine, "backend": prefs.compute_device_type, "selected_devices": devices, "output": scene.render.filepath})
bpy.ops.render.render(write_still=True)
if not os.path.isfile(scene.render.filepath) or os.path.getsize(scene.render.filepath) == 0:
    log({"stage": "failed", "reason": "Output image missing or empty"})
    raise SystemExit(21)
log({"stage": "completed", "output": scene.render.filepath, "bytes": os.path.getsize(scene.render.filepath), "note": "Cycles GPU selected; verify CUDA device in Blender log."})