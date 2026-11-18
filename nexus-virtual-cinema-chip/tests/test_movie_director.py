import tempfile
import unittest
from pathlib import Path

from nexus_movie_director import build_plan, write_srt


class MovieDirectorTests(unittest.TestCase):
    def test_plan_has_six_ordered_beats_and_vertical_format(self):
        plan = build_plan("NEXUS Signal", "sci-fi", 30, "youtube-shorts")
        self.assertEqual(plan["aspect_ratio"], "9:16")
        self.assertEqual(len(plan["shots"]), 6)
        self.assertEqual(plan["shots"][0]["beat"], "HOOK")
        self.assertEqual(plan["shots"][-1]["beat"], "LOOP")
        self.assertEqual(plan["shots"][-1]["end_seconds"], 30)

    def test_duration_validation(self):
        with self.assertRaises(ValueError):
            build_plan("Test", "sci-fi", 10, "youtube-shorts")

    def test_srt_export(self):
        plan = build_plan("Test", "adventure", 20, "instagram-reels")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "captions.srt"
            write_srt(plan, path)
            content = path.read_text(encoding="utf-8")
            self.assertIn("00:00:00,000 -->", content)
            self.assertIn("What if this world", content)


if __name__ == "__main__":
    unittest.main()
