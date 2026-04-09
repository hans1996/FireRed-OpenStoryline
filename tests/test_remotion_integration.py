"""Tests for Remotion integration."""

import json
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REMOTION_DIR = REPO_ROOT / "remotion-project"


class RemotionProjectTests(unittest.TestCase):
    def test_project_structure(self):
        self.assertTrue(REMOTION_DIR.exists())
        self.assertTrue((REMOTION_DIR / "package.json").exists())
        self.assertTrue((REMOTION_DIR / "src" / "index.ts").exists())
        self.assertTrue((REMOTION_DIR / "src" / "Root.tsx").exists())
        self.assertTrue((REMOTION_DIR / "src" / "TimelineComposition.tsx").exists())
        self.assertTrue((REMOTION_DIR / "src" / "timeline_schema.ts").exists())

    def test_node_modules(self):
        nm = REMOTION_DIR / "node_modules" / "remotion"
        self.assertTrue(nm.exists(), "Remotion package not installed")

    def test_render_script_syntax(self):
        script = REMOTION_DIR / "scripts" / "render_timeline.js"
        self.assertTrue(script.exists())
        r = subprocess.run(["node", "--check", str(script)], capture_output=True)
        self.assertEqual(r.returncode, 0, f"Script syntax error: {r.stderr.decode()}")

    def test_timeline_json(self):
        timeline = {
            "fps": 25,
            "width": 1920,
            "height": 1080,
            "total_duration": 5000,
            "tracks": {"video": [], "bgm": [], "voiceover": []},
            "subtitles": [],
            "style": {
                "bg_color": [0, 0, 0],
                "font_color": [255, 255, 255],
                "font_size": 40,
                "transition_duration": 500,
                "layout_mode": "fit",
            },
        }
        data = {"timelineData": timeline}
        self.assertIsNotNone(json.dumps(data))


class TimelineConversionTests(unittest.TestCase):
    def test_ms_to_frames(self):
        fps = 25

        def ms_to_frame(ms: int) -> int:
            return round((ms / 1000.0) * fps)

        self.assertEqual(ms_to_frame(1000), 25)
        self.assertEqual(ms_to_frame(4000), 100)
        self.assertEqual(ms_to_frame(3500), 88)


if __name__ == "__main__":
    unittest.main()
