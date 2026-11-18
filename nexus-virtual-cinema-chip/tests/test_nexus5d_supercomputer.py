import unittest
from nexus5d_supercomputer import (
    ComputeJob, ComputeNode, NEXUS5DSupercomputer,
)


class FiveDSupercomputerTests(unittest.TestCase):
    def setUp(self):
        def cpu(command):
            return command["payload"]["x"] * 3
        def gpu(command):
            return command["payload"]["x"] * 5
        self.cluster = NEXUS5DSupercomputer(max_workers=3)
        self.cluster.register_node(ComputeNode(
            "cpu-local", "CPU", frozenset({"general"}),
            compute_units=2, memory_bytes=4096, network_gbps=1,
            region="local", rack="r1", executor=cpu,
        ))
        self.cluster.register_node(ComputeNode(
            "gpu-local", "GPU_SIMULATOR", frozenset({"general", "tensor"}),
            compute_units=20, memory_bytes=8192, network_gbps=10,
            region="local", rack="r1", executor=gpu,
        ))

    def test_capability_and_resource_placement(self):
        plan = self.cluster.plan([ComputeJob(
            "tensor", "multiply", {"x": 4}, capability="tensor",
            memory_bytes=1024, region="local", rack="r1",
        )])
        self.assertEqual(plan[0]["node"], "gpu-local")
        self.assertEqual(len(plan[0]["placement_dimensions"]), 5)

    def test_parallel_job_results(self):
        jobs = [ComputeJob(f"j{i}", "scale", {"x": i}) for i in range(8)]
        result = self.cluster.run(jobs)
        self.assertEqual(len(result["results"]), 8)
        self.assertEqual(result["metrics"]["jobs_completed"], 8)
        self.assertFalse(result["errors"])

    def test_cache_reuse(self):
        first = self.cluster.run([ComputeJob("a", "scale", {"x": 7}, cacheable=True)])
        second = self.cluster.run([ComputeJob("b", "scale", {"x": 7}, cacheable=True)])
        self.assertEqual(first["results"]["a"], second["results"]["b"])
        self.assertEqual(second["metrics"]["cache_hits"], 1)

    def test_memory_rejection(self):
        result = self.cluster.run([ComputeJob("too-big", "op", {}, memory_bytes=999999)])
        self.assertIn("too-big", result["errors"])

    def test_duplicate_ids_rejected(self):
        job = ComputeJob("same", "op", {})
        with self.assertRaises(ValueError):
            self.cluster.run([job, job])


if __name__ == "__main__":
    unittest.main()
