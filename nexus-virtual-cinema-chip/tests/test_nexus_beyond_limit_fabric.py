import unittest
from nexus_beyond_limit_fabric import ENGINES, research_catalog, route_research_workload
from nexus_horizon_runtime import DeviceInfo

class BeyondLimitFabricTests(unittest.TestCase):
 def test_catalog_has_research_engines(self):
  self.assertGreaterEqual(len(ENGINES),8)
  self.assertFalse(research_catalog()["physical_future_engines_present"])
 def test_optical_route_is_not_claimed_executable(self):
  r=route_research_workload("dense_matmul",devices=[])
  self.assertIn("NOVA-OPT",r["research_candidates"])
  self.assertNotIn("NOVA-OPT",r["executable_research_candidates"])
 def test_detected_hardware_separate_from_virtual_engines(self):
  cpu=DeviceInfo("cpu","CPU","test cpu",True,"python",("general",),1024)
  r=route_research_workload("sampling",devices=[cpu])
  self.assertEqual(r["detected_hardware"][0]["id"],"cpu")
  self.assertEqual(r["status"],"recommendation_only")
if __name__=="__main__": unittest.main()
