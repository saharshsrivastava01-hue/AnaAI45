import unittest

from nexus3000_fabric_runtime import (
    Device, FabricError, Task, VirtualSuperfabric,
)


class FabricRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.fabric = VirtualSuperfabric(max_workers=3)

        def run(command):
            return (command["device"], command["payload"]["n"])

        self.fabric.register(Device(
            "cpu-0", "CPU", capacity=2,
            capabilities=frozenset({"general", "preprocess"}),
            executor=run,
        ))
        self.fabric.register(Device(
            "gpu-sim-0", "GPU_SIMULATOR", capacity=8,
            capabilities=frozenset({"general", "raster"}),
            executor=run,
        ))

    def test_capability_routing(self):
        result = self.fabric.run([
            Task("raster-1", "draw", {"n": 1}, frozenset({"raster"}))
        ])
        self.assertEqual(result["results"]["raster-1"], ("gpu-sim-0", 1))
        self.assertFalse(result["errors"])

    def test_many_tasks_are_queued_with_bounded_workers(self):
        tasks = [Task(f"t{i}", "work", {"n": i}) for i in range(12)]
        result = self.fabric.run(tasks)
        self.assertEqual(len(result["results"]), 12)
        self.assertEqual(result["metrics"]["runtime_worker_limit"], 3)
        self.assertEqual(result["metrics"]["completed"], 12)

    def test_missing_capability_fails_clearly(self):
        with self.assertRaises(FabricError):
            self.fabric.run([
                Task("x", "train", {}, frozenset({"quantum_magic"}))
            ])

    def test_duplicate_ids_rejected(self):
        task = Task("same", "work")
        with self.assertRaises(ValueError):
            self.fabric.run([task, task])

    def test_device_requires_executor(self):
        with self.assertRaises(ValueError):
            self.fabric.register(Device("empty", "GPU"))


if __name__ == "__main__":
    unittest.main()
