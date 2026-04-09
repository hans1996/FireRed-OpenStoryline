import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT_ROOT, "src")
for path in (SRC, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from open_storyline.utils.media_handler import scan_media_dir


class ScanMediaDirTests(unittest.TestCase):
    def test_counts_supported_images_and_videos_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            media_dir = Path(tmpdir)
            for name in ["cover.PNG", "shot.jpg", "loop.webp"]:
                (media_dir / name).write_bytes(b"data")
            for name in ["clip.MP4", "broll.mov"]:
                (media_dir / name).write_bytes(b"data")
            (media_dir / "notes.txt").write_text("ignore me", encoding="utf-8")

            result = scan_media_dir(media_dir)

        self.assertEqual(result["image number in user's media library"], 3)
        self.assertEqual(result["video number in user's media library"], 2)

    def test_ignores_hidden_entries_and_subdirectories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            media_dir = Path(tmpdir)
            (media_dir / ".hidden.png").write_bytes(b"data")
            (media_dir / ".hidden-dir").mkdir()
            nested = media_dir / "nested"
            nested.mkdir()
            (nested / "nested.mp4").write_bytes(b"data")
            (media_dir / "visible.gif").write_bytes(b"data")

            result = scan_media_dir(media_dir)

        self.assertEqual(result["image number in user's media library"], 1)
        self.assertEqual(result["video number in user's media library"], 0)

    def test_creates_missing_media_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            media_dir = Path(tmpdir) / "missing-library"

            result = scan_media_dir(media_dir)

            self.assertTrue(media_dir.exists())
            self.assertTrue(media_dir.is_dir())
            self.assertEqual(
                result,
                {
                    "image number in user's media library": 0,
                    "video number in user's media library": 0,
                },
            )


if __name__ == "__main__":
    unittest.main()
