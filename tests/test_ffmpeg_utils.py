import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT_ROOT, "src")
for path in (SRC, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from open_storyline.utils import ffmpeg_utils


class ResolveFfmpegExecutableTests(unittest.TestCase):
    def test_prefers_existing_env_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ffmpeg_path = Path(tmpdir) / "ffmpeg"
            ffmpeg_path.write_text("#!/bin/sh\n", encoding="utf-8")

            with patch.dict(os.environ, {"IMAGEIO_FFMPEG_EXE": str(ffmpeg_path)}, clear=True):
                resolved = ffmpeg_utils.resolve_ffmpeg_executable()

        self.assertEqual(resolved, str(ffmpeg_path))

    def test_falls_back_to_system_path_lookup(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "open_storyline.utils.ffmpeg_utils.shutil.which", return_value="/usr/bin/ffmpeg"
        ):
            resolved = ffmpeg_utils.resolve_ffmpeg_executable()

        self.assertEqual(resolved, "/usr/bin/ffmpeg")


class ReadVideoFramesAsRgb24Tests(unittest.TestCase):
    def test_returns_empty_array_when_ffmpeg_outputs_no_frames(self):
        process = MagicMock()
        process.communicate.return_value = (b"", b"")
        process.returncode = 0

        with patch("open_storyline.utils.ffmpeg_utils.subprocess.Popen", return_value=process):
            frames = ffmpeg_utils.read_video_frames_as_rgb24(
                Path("input.mp4"),
                "ffmpeg",
                frames_per_second=1,
                target_width=2,
                target_height=2,
            )

        self.assertEqual(frames.shape, (0, 2, 2, 3))
        self.assertEqual(frames.dtype, np.uint8)

    def test_reshapes_ffmpeg_bytes_into_rgb_frames(self):
        process = MagicMock()
        process.communicate.return_value = (bytes([0, 1, 2, 3, 4, 5]), b"")
        process.returncode = 0

        with patch("open_storyline.utils.ffmpeg_utils.subprocess.Popen", return_value=process):
            frames = ffmpeg_utils.read_video_frames_as_rgb24(
                Path("input.mp4"),
                "ffmpeg",
                frames_per_second=1,
                target_width=1,
                target_height=1,
            )

        self.assertEqual(frames.shape, (2, 1, 1, 3))
        self.assertEqual(frames[0, 0, 0].tolist(), [0, 1, 2])
        self.assertEqual(frames[1, 0, 0].tolist(), [3, 4, 5])


class SegmentVideoStreamCopyTests(unittest.TestCase):
    def test_without_split_points_returns_single_segment(self):
        completed = MagicMock(returncode=0, stderr=b"")

        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "open_storyline.utils.ffmpeg_utils.subprocess.run", return_value=completed
        ) as run_mock:
            segments = ffmpeg_utils.segment_video_stream_copy_with_ffmpeg(
                Path("input.mp4"),
                "ffmpeg",
                split_points_seconds=[],
                output_directory=Path(tmpdir),
                filename_prefix="clip",
                start_index=7,
            )

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].path, Path(tmpdir) / "clip_0007.mp4")
        self.assertEqual(segments[0].start_seconds, 0.0)
        self.assertEqual(segments[0].end_seconds, -1.0)
        command = run_mock.call_args.args[0]
        self.assertIn("-c", command)
        self.assertIn("copy", command)

    def test_parses_segment_manifest_into_video_segments(self):
        def fake_run(command, stdout=None, stderr=None):
            segment_list_path = Path(command[command.index("-segment_list") + 1])
            segment_list_path.write_text(
                "clip_0003.mp4,0.000,1.500\nclip_0004.mp4,1.500,3.000\n",
                encoding="utf-8",
            )
            return MagicMock(returncode=0, stderr=b"")

        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "open_storyline.utils.ffmpeg_utils.subprocess.run", side_effect=fake_run
        ):
            segments = ffmpeg_utils.segment_video_stream_copy_with_ffmpeg(
                Path("input.mp4"),
                "ffmpeg",
                split_points_seconds=[1.5],
                output_directory=Path(tmpdir),
                filename_prefix="clip",
                start_index=3,
            )

        self.assertEqual(
            segments,
            [
                ffmpeg_utils.VideoSegment(path=Path(tmpdir) / "clip_0003.mp4", start_seconds=0.0, end_seconds=1.5),
                ffmpeg_utils.VideoSegment(path=Path(tmpdir) / "clip_0004.mp4", start_seconds=1.5, end_seconds=3.0),
            ],
        )


class CutVideoSegmentTests(unittest.TestCase):
    def test_returns_requested_segment_metadata(self):
        completed = MagicMock(returncode=0, stderr=b"")

        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "open_storyline.utils.ffmpeg_utils.subprocess.run", return_value=completed
        ) as run_mock:
            output_path = Path(tmpdir) / "clips" / "out.mp4"
            segment = ffmpeg_utils.cut_video_segment_with_ffmpeg(
                Path("input.mp4"),
                start=1.25,
                end=2.5,
                output_path=output_path,
                ffmpeg_executable="ffmpeg",
                extra_args=["-preset", "veryfast"],
            )
            self.assertTrue(output_path.parent.exists())

        self.assertEqual(segment, ffmpeg_utils.VideoSegment(path=output_path, start_seconds=1.25, end_seconds=2.5))
        command = run_mock.call_args.args[0]
        self.assertIn("-preset", command)
        self.assertIn("veryfast", command)


if __name__ == "__main__":
    unittest.main()
