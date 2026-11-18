import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "nexus3000_virtual_chip.py"
spec = importlib.util.spec_from_file_location("nexus_virtual_chip", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class VirtualFabricTests(unittest.TestCase):
    def test_topology_has_all_domains(self):
        topo = module.topology()
        names = {e["name"] for e in topo["engines"]}
        self.assertTrue({"VTPU","VGPU","VRPU","VFXU","VGEU","VAU","VMEDIA","VIO","VDMA","VNoC","VSEC"} <= names)

    def test_billion_scale_is_logical_not_physical(self):
        topo = module.topology()
        tp = next(e for e in topo["engines"] if e["name"] == "VTPU")
        self.assertGreaterEqual(tp["logical_lanes"], 1_000_000_000)
        self.assertEqual(tp["physical_devices"], 0)
        self.assertFalse(topo["physical_hardware"])

    def test_plan_dependencies_validate(self):
        plan = module.build_plan()
        self.assertTrue(module.validate_plan(plan))
        self.assertEqual(plan["physical_accelerators"], 0)

    def test_invalid_dependency_rejected(self):
        plan = module.build_plan()
        plan["stages"][0]["depends_on"] = ["missing"]
        with self.assertRaises(ValueError):
            module.validate_plan(plan)

if __name__ == "__main__":
    unittest.main()
