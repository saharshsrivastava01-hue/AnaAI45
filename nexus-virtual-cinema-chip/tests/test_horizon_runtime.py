import unittest
from unittest.mock import patch

from nexus_horizon_runtime import DeviceInfo, discover_devices, inventory


class HorizonDiscoveryTests(unittest.TestCase):
    def test_host_cpu_is_always_reported(self):
        devices = discover_devices()
        self.assertGreaterEqual(len(devices), 1)
        cpu = devices[0]
        self.assertEqual(cpu.kind, "CPU")
        self.assertTrue(cpu.available)
        self.assertIn("general", cpu.capabilities)

    def test_inventory_never_claims_virtual_lanes_as_hardware(self):
        result = inventory()
        self.assertFalse(result["claims"]["virtual_lanes_are_physical_cores"])
        self.assertFalse(result["claims"]["performance_measured"])
        self.assertGreaterEqual(result["available_device_count"], 1)

    def test_no_torch_reports_no_accelerator_runtime(self):
        with patch("nexus_horizon_runtime.importlib.util.find_spec", return_value=None):
            devices = discover_devices()
        self.assertEqual(devices[0].kind, "CPU")
        self.assertFalse(devices[1].available)
        self.assertEqual(devices[1].execution_backend, "none")


if __name__ == "__main__":
    unittest.main()
