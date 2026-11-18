import unittest

from nexus_fabric_scale_model import build_topology, validate_topology


class FabricScaleModelTests(unittest.TestCase):
    def test_total_logical_lanes(self):
        topology = build_topology()
        self.assertEqual(topology["total_logical_lanes"], 1_960_000_000_000)

    def test_never_claims_physical_cores(self):
        topology = build_topology()
        self.assertEqual(topology["physical_devices_allocated"], 0)
        self.assertFalse(topology["logical_lanes_are_physical_cores"])
        validate_topology(topology)

    def test_rejects_physical_core_claim(self):
        topology = build_topology()
        topology["logical_lanes_are_physical_cores"] = True
        with self.assertRaises(ValueError):
            validate_topology(topology)

    def test_rejects_duplicate_pool_names(self):
        topology = build_topology()
        topology["pools"].append(dict(topology["pools"][0]))
        with self.assertRaises(ValueError):
            validate_topology(topology)


if __name__ == "__main__":
    unittest.main()
