import unittest
from nexus_blc import BLCFabric, Workload, WorkloadKind, default_engines, demo_workloads

class BLCtests(unittest.TestCase):
    def setUp(self): self.fabric = BLCFabric()
    def test_demo_has_recommendations(self):
        r = self.fabric.report(demo_workloads())
        self.assertEqual(r["status"], "SIMULATION_ONLY")
        self.assertFalse(r["physical_hardware_created"])
        self.assertEqual(len(r["results"]), 8)
        self.assertTrue(all(x["recommended"] for x in r["results"]))
    def test_dense_can_compare_optical_and_gpu(self):
        w = Workload("dense", WorkloadKind.DENSE, 1e9, 1e8)
        names = {x.engine for x in self.fabric.rank(w)}
        self.assertIn("NOVA_OPTICAL_HYPOTHETICAL", names)
        self.assertIn("GPU_STYLE_REFERENCE", names)
    def test_unsupported_engine_rejected(self):
        e = next(x for x in default_engines() if x.name == "NEURO_EVENT_HYPOTHETICAL")
        with self.assertRaises(ValueError):
            self.fabric.estimate(Workload("x", WorkloadKind.DENSE, 1), e)
    def test_invalid_sparsity_rejected(self):
        with self.assertRaises(ValueError):
            Workload("bad", WorkloadKind.SPARSE, 10, sparsity=1.0)
    def test_estimates_disclose_assumptions(self):
        x = self.fabric.rank(demo_workloads()[0])[0]
        self.assertGreaterEqual(x.total_seconds, 0)
        self.assertGreaterEqual(x.energy_joules, 0)
        self.assertTrue(any("not a measured" in a for a in x.assumptions))

if __name__ == "__main__": unittest.main()
