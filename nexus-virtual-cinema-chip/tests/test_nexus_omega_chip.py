import unittest
from nexus_omega_futuristic_chip import COMPONENTS, topology, Job, plan_jobs

class OmegaTests(unittest.TestCase):
    def test_components_unique(self):
        self.assertEqual(len({c.abbreviation for c in COMPONENTS}), len(COMPONENTS))
    def test_inventory(self):
        data=topology()
        self.assertEqual(data["physical_units"],0)
        self.assertIsNone(data["measured_speedup"])
        self.assertEqual(len(data["components"]),12)
    def test_planning_not_execution(self):
        plans=plan_jobs([Job("movie frame","ray",10,2.0)])
        self.assertEqual(plans[0]["status"],"planned_not_executed")
        self.assertFalse(plans[0]["logical_capacity_used_for_placement"])
    def test_unknown(self):
        self.assertEqual(plan_jobs([Job("x","unknown")])[0]["status"],"unknown_component")
if __name__=="__main__": unittest.main()
