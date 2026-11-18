import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

ultra = load_module("nexus_ultra_renderer", "nexus_ultra_renderer.py")
scene_graph = load_module("nexus_scene_graph", "nexus_scene_graph.py")
vfx = load_module("nexus_vfx_studio", "nexus_vfx_studio.py")
immersive = load_module("nexus_immersive_media", "nexus_immersive_media.py")

class RendererMathTests(unittest.TestCase):
    def test_unit_vector(self):
        v = ultra.unit((3.0, 0.0, 4.0))
        self.assertAlmostEqual(ultra.length(v), 1.0, places=7)

    def test_sphere_intersection(self):
        hit = ultra.Sphere((0, 0, 0), 1, (1, 1, 1)).hit((0, 0, 3), (0, 0, -1))
        self.assertIsNotNone(hit)
        self.assertAlmostEqual(hit[0], 2.0)

    def test_miss(self):
        self.assertIsNone(ultra.Sphere((0, 0, 0), 1, (1, 1, 1)).hit((0, 3, 0), (0, 0, -1)))

    def test_tone_mapper_is_bounded(self):
        for x in (0, 0.1, 1, 10, 1000):
            self.assertGreaterEqual(ultra.aces(x), 0)
            self.assertLessEqual(ultra.aces(x), 1)

    def test_render_tiny_frame_writes_valid_ppm(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            ultra.render(out, 16, 16, 1, 12, 1, 2090, 1, 0.01, 0.0)
            frame = out / "frame_00000.ppm"
            raw = frame.read_bytes()
            header = b"P6\n16 16\n255\n"
            self.assertTrue(raw.startswith(header))
            self.assertEqual(len(raw) - len(header), 16 * 16 * 3)
            manifest = json.loads((out / "render_manifest.json").read_text())
            self.assertEqual(manifest["resolution"], [16, 16])

class PipelineTests(unittest.TestCase):
    def test_sample_scene_validates(self):
        counts = scene_graph.validate_scene(scene_graph.sample_scene())
        self.assertEqual(counts["spheres"], 3)
        self.assertEqual(counts["planes"], 1)

    def test_vfx_graph_topological_order(self):
        order = vfx.validate(vfx.sample_graph())
        self.assertEqual(order[0], "plate")
        self.assertEqual(order[-1], "out")

    def test_vfx_cycle_rejected(self):
        graph = vfx.sample_graph()
        graph["edges"].append({"from": "out", "to": "grade"})
        with self.assertRaises(ValueError):
            vfx.validate(graph)

    def test_immersive_manifest(self):
        manifest = immersive.build_manifest("test", "preview_4k", "surround_7_1")
        result = immersive.validate(manifest)
        self.assertEqual(result["stages"], 10)
        self.assertEqual(result["video"], "3840x2160@24")

if __name__ == "__main__":
    unittest.main(verbosity=2)
