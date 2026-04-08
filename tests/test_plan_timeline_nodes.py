import os
import sys
import types
import unittest
from types import SimpleNamespace


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT_ROOT, "src")
for path in (SRC, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)


def _install_module(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


node_state_module = _install_module("open_storyline.nodes.node_state")


class NodeState:  # pragma: no cover - import stub only
    pass


node_state_module.NodeState = NodeState

base_node_module = _install_module("open_storyline.nodes.core_nodes.base_node")


class BaseNode:  # pragma: no cover - import stub only
    pass


class NodeMeta:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


base_node_module.BaseNode = BaseNode
base_node_module.NodeMeta = NodeMeta

node_schema_module = _install_module("open_storyline.nodes.node_schema")


class PlanTimelineInput:  # pragma: no cover - import stub only
    pass


node_schema_module.PlanTimelineInput = PlanTimelineInput

register_module = _install_module("open_storyline.utils.register")


class _Registry:
    def register(self):
        def decorator(obj):
            return obj

        return decorator

    def register_module(self):
        def decorator(obj):
            return obj

        return decorator


register_module.NODE_REGISTRY = _Registry()

from open_storyline.config import PlanTimelineConfig, PlanTimelineProConfig  # noqa: E402
from open_storyline.nodes.core_nodes.plan_timeline import TimelinePlanner  # noqa: E402
from open_storyline.nodes.core_nodes.plan_timeline_pro import TimeLine  # noqa: E402


class SummaryRecorder:
    def __init__(self):
        self.warnings = []
        self.infos = []

    def add_warning(self, message):
        self.warnings.append(message)

    def info_for_llm(self, message):
        self.infos.append(message)


class TimelinePlannerTests(unittest.TestCase):
    def test_plan_builds_aligned_tracks_for_voiceover_groups(self):
        planner = TimelinePlanner(PlanTimelineConfig())

        result = planner.plan(
            media=[{"media_id": "m1", "path": "/orig/video.mp4"}],
            clips=[
                {
                    "clip_id": "c1",
                    "kind": "video",
                    "path": "/cache/c1.mp4",
                    "media_id": "m1",
                    "source_ref": {"media_id": "m1", "start": 0, "end": 1200, "duration": 1200},
                    "fps": 30,
                }
            ],
            groups=[{"group_id": "g1", "clip_ids": ["c1"]}],
            group_scripts=[
                {
                    "group_id": "g1",
                    "raw_text": "Hello world",
                    "subtitle_units": [{"unit_id": "u1", "index_in_group": 0, "text": "Hello world"}],
                }
            ],
            voiceovers=[{"group_id": "g1", "path": "/audio/g1.wav", "duration": 2000}],
            background_music=None,
            use_beats=False,
        )

        tracks = result["tracks"]
        self.assertEqual(len(tracks["video"]), 1)
        self.assertEqual(len(tracks["voiceover"]), 1)
        self.assertEqual(len(tracks["subtitles"]), 1)

        video_track = tracks["video"][0]
        self.assertEqual(video_track["source_path"], "/orig/video.mp4")
        self.assertEqual(video_track["timeline_window"], {"start": 0, "end": 3000, "duration": 3000})
        self.assertAlmostEqual(video_track["playback_rate"], 0.4)

        voiceover_track = tracks["voiceover"][0]
        self.assertEqual(voiceover_track["timeline_window"], {"start": 500.0, "end": 2500.0, "duration": 2000})

        subtitle_track = tracks["subtitles"][0]
        self.assertEqual(subtitle_track["text"], "Hello world")
        self.assertEqual(subtitle_track["timeline_window"], {"start": 250, "end": 2750})


class TimelineProTests(unittest.TestCase):
    def test_edit_meterial_timeline_uses_tts_margins_without_beats(self):
        cfg = PlanTimelineProConfig(
            tts_margin_mode="min",
            min_tts_margin=300,
            max_tts_margin=300,
            min_group_margin=1500,
            max_group_margin=1500,
            text_tts_offset_mode="min",
        )
        node_state = SimpleNamespace(node_summary=SummaryRecorder())

        music_offset, durations, speeds, time_margins = TimeLine().edit_meterial_timeline(
            cfg,
            node_state,
            music=None,
            meterial_durations=[1000, 1000],
            tts_res=[{"duration": 1000}],
            texts=[["a", "b"]],
            types=["video", "img"],
            tts_indices_map={0: 2},
            group_indices_map={0: 1},
        )

        self.assertEqual(music_offset, 0)
        self.assertEqual(durations, [1000, 1000])
        self.assertEqual(speeds, [1.0, 1.0])
        self.assertEqual(time_margins, [300])
        self.assertEqual(node_state.node_summary.warnings, [])

    def test_edit_meterial_timeline_aligns_to_beats_and_reports_rate(self):
        cfg = PlanTimelineProConfig(min_clip_duration=1000)
        node_state = SimpleNamespace(node_summary=SummaryRecorder())

        music_offset, durations, speeds, time_margins = TimeLine().edit_meterial_timeline(
            cfg,
            node_state,
            music={"beats": [1000, 2000, 3500], "duration": 5000},
            meterial_durations=[800, 800],
            tts_res=[{"duration": 600}],
            texts=[["hello"]],
            types=["video", "img"],
            tts_indices_map={0: 2},
            group_indices_map={0: 1},
            title_clip_duration=500,
            is_on_beats=True,
        )

        self.assertEqual(music_offset, 500)
        self.assertEqual(durations, [1000, 1500])
        self.assertEqual(speeds, [0.8, 1.0])
        self.assertEqual(time_margins, [0, 0])
        self.assertEqual(node_state.node_summary.warnings, [])
        self.assertEqual(node_state.node_summary.infos, ["[W/O. Beats Rate] 0.50"])


if __name__ == "__main__":
    unittest.main()
