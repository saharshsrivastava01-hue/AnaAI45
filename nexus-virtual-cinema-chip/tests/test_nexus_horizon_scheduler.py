import unittest

from nexus_horizon_runtime import DeviceInfo
from nexus_horizon_scheduler import HorizonScheduler, WorkItem


class HorizonSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.cpu = DeviceInfo("cpu0", "CPU", "Test CPU", True, "python",
                              ("general", "reference"), memory_bytes=4096)
        self.gpu = DeviceInfo("gpu0", "GPU", "Test GPU", True, "pytorch-cuda",
                              ("tensor",), memory_bytes=2048)
        self.scheduler = HorizonScheduler([self.cpu, self.gpu], max_workers=2)

    def tearDown(self):
        self.scheduler.shutdown()

    def test_cpu_reference_dispatch(self):
        result = self.scheduler.submit(WorkItem("smoke", "reference")).result()
        self.assertEqual(result["device_id"], "cpu0")

    def test_gpu_requires_registered_executor(self):
        with self.assertRaises(RuntimeError):
            self.scheduler.submit(WorkItem("tensor", "tensor"))

    def test_registered_gpu_executor(self):
        self.scheduler.register_executor("gpu0", lambda item: "ok")
        result = self.scheduler.submit(WorkItem("tensor", "tensor", 1024)).result()
        self.assertEqual(result["result"], "ok")
        self.assertEqual(self.scheduler.metrics()["stats"]["gpu0"]["completed"], 1)

    def test_memory_admission(self):
        with self.assertRaises(RuntimeError):
            self.scheduler.submit(WorkItem("oversized", "tensor", 4096))

    def test_unavailable_device_is_not_scheduled(self):
        unavailable = DeviceInfo("missing", "GPU", "Not present", False, "none", ())
        scheduler = HorizonScheduler([self.cpu, unavailable])
        try:
            self.assertEqual(len(scheduler.devices), 1)
        finally:
            scheduler.shutdown()


if __name__ == "__main__":
    unittest.main()
