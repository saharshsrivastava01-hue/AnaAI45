import unittest
from nexus3000_adaptive_fabric import AdaptiveFabric, Worker, WorkItem


class AdaptiveFabricTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        def execute(job):
            self.calls.append(job)
            return job["inputs"]["x"] + 10
        self.fabric = AdaptiveFabric(max_workers=4)
        self.fabric.register_worker(Worker(
            "gpu-sim", "GPU_SIMULATOR", frozenset({"vector", "general"}),
            1024 * 1024, max_inflight=2, data_regions=frozenset({"fast"}),
            executor=execute,
        ))
        self.fabric.register_worker(Worker(
            "cpu", "CPU", frozenset({"general"}), 1024 * 1024,
            max_inflight=4, data_regions=frozenset({"local"}), executor=execute,
        ))

    def test_capability_and_locality_routing(self):
        result = self.fabric.run([WorkItem(
            "a", "vector-op", {"x": 5}, frozenset({"vector"}),
            128, "fast"
        )])
        self.assertEqual(result["plan"][0]["placement"], "gpu-sim")

    def test_deterministic_cache_reuse(self):
        first = self.fabric.run([WorkItem("a", "op", {"x": 7})])
        second = self.fabric.run([WorkItem("b", "op", {"x": 7})])
        self.assertEqual(first["results"]["a"], second["results"]["b"])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(second["plan"][0]["placement"], "cache")

    def test_memory_requirement_rejected(self):
        with self.assertRaises(RuntimeError):
            self.fabric.run([WorkItem("huge", "op", {}, memory_bytes=2**40)])

    def test_duplicate_ids_rejected(self):
        item = WorkItem("same", "op", {})
        with self.assertRaises(ValueError):
            self.fabric.run([item, item])


if __name__ == "__main__":
    unittest.main()
