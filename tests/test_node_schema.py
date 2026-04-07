"""
Tests for node_schema.py and node_state.py.

Covers:
- Pydantic model validation for all schema classes in node_schema.py
- VideoMetadata audio sample rate validation
- Media union type resolution (video vs image metadata)
- Input model mode validation
- Timeline and track model construction
- Output model defaults and field validation
- NodeState dataclass creation
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

# ── install stub modules for missing dependencies ─────────────────────────────
def _install_stub(name):
    if name in sys.modules:
        return sys.modules[name]
    m = MagicMock()
    sys.modules[name] = m
    return m

_install_stub("colorlog")
_install_stub("colorlog.handlers")
_install_stub("proglog")
_install_stub("proglog.ProgressBarLogger")

_lc = _install_stub("langchain_core")
_lc.tools = _install_stub("langchain_core.tools")
_lc.tools.structured = _install_stub("langchain_core.tools.structured")
_lc.tools.structured.StructuredTool = _lc.tools.structured

# ─────────────────────────────────────────────────────────────────
# Imports – must come AFTER the stubs
# ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT_ROOT, "src")
for p in (SRC, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from pydantic import ValidationError  # noqa: E402

from open_storyline.nodes.node_schema import (  # noqa: E402
    VideoMetadata,
    ImageMetadata,
    Media,
    SourceRef,
    Clip,
    SubtitleUnit,
    GroupClips,
    GroupScript,
    Voiceover,
    BGM,
    TimeWindow,
    AudioMix,
    ClipTrack,
    BgmTrack,
    SubtitleTrack,
    VoiceoverTrack,
    TimelineTracks,
    BaseInput,
    LoadMediaInput,
    SearchMediaInput,
    SplitShotsInput,
    SplitShotsOutput,
    LocalASRInput,
    SpeechRoughCutInput,
    UnderstandClipsInput,
    UnderstandClipsOutput,
    FilterClipsInput,
    FilterClipsOutput,
    GroupClipsInput,
    GroupClipsOutput,
    GenerateScriptInput,
    GenerateScriptOutput,
    GenerateVoiceoverInput,
    GenerateVoiceoverOutput,
    RecommendScriptTemplateInput,
    SelectBGMInput,
    SelectBGMOutput,
    RecommendTransitionInput,
    RecommendTransitionOutput,
    GenerateAITransitionInput,
    RecommendTextInput,
    RecommendTextOutput,
    PlanTimelineInput,
    PlanTimelineAITransitionInput,
    PlanTimelineOutput,
    RenderVideoInput,
)
from open_storyline.nodes.node_state import NodeState  # noqa: E402


# ======================================================================
# 1. VideoMetadata
# ======================================================================
class TestVideoMetadata(unittest.TestCase):
    def test_valid_no_audio(self):
        vm = VideoMetadata(width=1920, height=1080, duration=3000.0, fps=30.0)
        self.assertFalse(vm.has_audio)
        self.assertIsNone(vm.audio_sample_rate_hz)

    def test_valid_with_audio(self):
        vm = VideoMetadata(
            width=1920, height=1080, duration=3000.0, fps=30.0,
            has_audio=True, audio_sample_rate_hz=48000,
        )
        self.assertTrue(vm.has_audio)
        self.assertEqual(vm.audio_sample_rate_hz, 48000)

    def test_audio_without_sample_rate_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            VideoMetadata(
                width=1920, height=1080, duration=3000.0, fps=30.0,
                has_audio=True,
            )
        self.assertIn("audio_sample_rate_hz", str(ctx.exception))

    def test_audio_sample_rate_must_be_positive(self):
        with self.assertRaises(ValidationError) as ctx:
            VideoMetadata(width=1920, height=1080, duration=3000.0, fps=30.0,
                          audio_sample_rate_hz=-1)
        self.assertIn("greater than 0", str(ctx.exception).lower())

    def test_defaults(self):
        vm = VideoMetadata(width=1280, height=720, duration=1500.0, fps=24.0)
        self.assertEqual(vm.has_audio, False)
        self.assertEqual(vm.audio_sample_rate_hz, None)


# ======================================================================
# 2. ImageMetadata
# ======================================================================
class TestImageMetadata(unittest.TestCase):
    def test_valid(self):
        im = ImageMetadata(width=800, height=600)
        self.assertEqual(im.width, 800)
        self.assertEqual(im.height, 600)

    def test_square(self):
        im = ImageMetadata(width=1080, height=1080)
        self.assertEqual(im.width, 1080)


# ======================================================================
# 3. Media
# ======================================================================
class TestMedia(unittest.TestCase):
    def _video_meta(self):
        return VideoMetadata(width=1920, height=1080, duration=5000.0, fps=30.0, has_audio=True, audio_sample_rate_hz=48000)

    def _image_meta(self):
        return ImageMetadata(width=800, height=600)

    def test_video_media(self):
        m = Media(media_id="v1", path="/videos/v1.mp4", media_type="video",
                  metadata=self._video_meta())
        self.assertEqual(m.media_id, "v1")
        self.assertIsInstance(m.metadata, VideoMetadata)

    def test_image_media(self):
        m = Media(media_id="i1", path="/images/i1.jpg", media_type="image",
                  metadata=self._image_meta())
        self.assertEqual(m.media_id, "i1")
        self.assertIsInstance(m.metadata, ImageMetadata)

    def test_extra_info_optional(self):
        m = Media(media_id="m1", path="/x", media_type="video",
                  metadata=self._video_meta())
        self.assertIsNone(m.extra_info)

    def test_extra_info_populated(self):
        m = Media(media_id="m1", path="/x", media_type="video",
                  metadata=self._video_meta(), extra_info={"key": "val"})
        self.assertEqual(m.extra_info, {"key": "val"})

    def test_unknown_media_type(self):
        m = Media(media_id="u1", path="/u", media_type="unknown",
                  metadata=self._image_meta())
        self.assertEqual(m.media_type, "unknown")


# ======================================================================
# 4. SourceRef
# ======================================================================
class TestSourceRef(unittest.TestCase):
    def test_valid(self):
        sr = SourceRef(media_id="src1", start=0.0, end=5.5, duration=5.5)
        self.assertEqual(sr.media_id, "src1")
        self.assertEqual(sr.duration, 5.5)
        self.assertIsNone(sr.height)
        self.assertIsNone(sr.width)

    def test_with_dimensions(self):
        sr = SourceRef(media_id="src1", start=0.0, end=10.0, duration=10.0,
                       height=1080, width=1920)
        self.assertEqual(sr.height, 1080)
        self.assertEqual(sr.width, 1920)


# ======================================================================
# 5. Clip
# ======================================================================
class TestClip(unittest.TestCase):
    def test_valid(self):
        c = Clip(clip_id="c1", caption="Test clip", media_type="video", path="/c1.mp4")
        self.assertEqual(c.clip_id, "c1")
        self.assertIsNone(c.language)
        self.assertIsNone(c.fps)
        self.assertIsNone(c.extra_info)

    def test_all_fields(self):
        c = Clip(clip_id="c1", language="en", caption="A cat", media_type="video",
                 path="/c1.mp4", fps=30.0, extra_info={"key": "val"})
        self.assertEqual(c.language, "en")
        self.assertEqual(c.fps, 30.0)
        self.assertEqual(c.extra_info, {"key": "val"})


# ======================================================================
# 6. SubtitleUnit
# ======================================================================
class TestSubtitleUnit(unittest.TestCase):
    def test_valid(self):
        su = SubtitleUnit(unit_id="su1", index_in_group=0, text="Hello world")
        self.assertEqual(su.unit_id, "su1")
        self.assertEqual(su.index_in_group, 0)
        self.assertEqual(su.text, "Hello world")

    def test_index_must_be_non_negative(self):
        with self.assertRaises(ValidationError):
            SubtitleUnit(unit_id="su2", index_in_group=-1, text="Bad")


# ======================================================================
# 7. GroupClips
# ======================================================================
class TestGroupClips(unittest.TestCase):
    def test_valid(self):
        gc = GroupClips(group_id="g1", summary="Good vibes",
                        clip_ids=["c1", "c2", "c3"])
        self.assertEqual(gc.group_id, "g1")
        self.assertEqual(len(gc.clip_ids), 3)

    def test_empty_clip_ids(self):
        gc = GroupClips(group_id="g1", summary="Empty", clip_ids=[])
        self.assertEqual(gc.clip_ids, [])


# ======================================================================
# 8. GroupScript
# ======================================================================
class TestGroupScript(unittest.TestCase):
    def test_valid(self):
        gs = GroupScript(group_id="g1", raw_text="Once upon a time...",
                         subtitle_units=[])
        self.assertEqual(gs.group_id, "g1")
        self.assertEqual(gs.raw_text, "Once upon a time...")

    def test_with_subtitle_units(self):
        su = SubtitleUnit(unit_id="su1", index_in_group=0, text="Hello")
        gs = GroupScript(group_id="g1", raw_text="Hello",
                         subtitle_units=[su])
        self.assertEqual(len(gs.subtitle_units), 1)


# ======================================================================
# 9. Voiceover
# ======================================================================
class TestVoiceover(unittest.TestCase):
    def test_valid(self):
        vo = Voiceover(group_id="g1", voiceover_id="vo1", path="/vo1.mp3",
                       duration=3000)
        self.assertEqual(vo.duration, 3000)

    def test_duration_must_be_positive(self):
        with self.assertRaises(ValidationError):
            Voiceover(group_id="g1", voiceover_id="vo1", path="/x", duration=0)


# ======================================================================
# 10. BGM
# ======================================================================
class TestBGM(unittest.TestCase):
    def test_valid(self):
        bgm = BGM(bgm_id="bgm1", path="/bgm.mp3", duration=120000, bpm=120.0)
        self.assertEqual(bgm.bgm_id, "bgm1")
        self.assertEqual(bgm.beats, [])

    def test_with_beats(self):
        bgm = BGM(bgm_id="bgm1", path="/bgm.mp3", duration=120000, bpm=120.0,
                  beats=[0, 500, 1000, 1500])
        self.assertEqual(len(bgm.beats), 4)

    def test_bpm_must_be_positive(self):
        with self.assertRaises(ValidationError):
            BGM(bgm_id="b1", path="/x", duration=1000, bpm=0)


# ======================================================================
# 11. TimeWindow
# ======================================================================
class TestTimeWindow(unittest.TestCase):
    def test_valid(self):
        tw = TimeWindow(start=0, end=5000)
        self.assertEqual(tw.start, 0)
        self.assertEqual(tw.end, 5000)


# ======================================================================
# 12. AudioMix
# ======================================================================
class TestAudioMix(unittest.TestCase):
    def test_defaults(self):
        am = AudioMix()
        self.assertEqual(am.gain_db, 0.0)
        self.assertIsNone(am.ducking)

    def test_custom_gain(self):
        am = AudioMix(gain_db=-3.0, ducking={"ratio": 4.0})
        self.assertEqual(am.gain_db, -3.0)
        self.assertIsNotNone(am.ducking)


# ======================================================================
# 13. Track Models
# ======================================================================
class TestTrackModels(unittest.TestCase):
    def test_clip_track(self):
        tw = TimeWindow(start=0, end=3000)
        ct = ClipTrack(clip_id="c1", source_window=tw, timeline_window=tw)
        self.assertEqual(ct.clip_id, "c1")

    def test_bgm_track(self):
        tw = TimeWindow(start=0, end=5000)
        am = AudioMix(gain_db=-2.0)
        bt = BgmTrack(bgm_id="bgm1", timeline_window=tw, mix=am)
        self.assertEqual(bt.bgm_id, "bgm1")
        self.assertEqual(bt.mix.gain_db, -2.0)

    def test_subtitle_track(self):
        tw = TimeWindow(start=1000, end=4000)
        st = SubtitleTrack(text="Hello world", timeline_window=tw)
        self.assertEqual(st.text, "Hello world")

    def test_voiceover_track(self):
        tw = TimeWindow(start=0, end=10000)
        vt = VoiceoverTrack(media_id="vo1", timeline_window=tw)
        self.assertEqual(vt.media_id, "vo1")

    def test_timeline_tracks_defaults(self):
        tt = TimelineTracks()
        self.assertEqual(tt.video, [])
        self.assertEqual(tt.subtitles, [])
        self.assertEqual(tt.voiceover, [])
        self.assertEqual(tt.bgm, [])

    def test_timeline_tracks_with_data(self):
        tw = TimeWindow(start=0, end=3000)
        ct = ClipTrack(clip_id="c1", source_window=tw, timeline_window=tw)
        st = SubtitleTrack(text="Hi", timeline_window=tw)
        tt = TimelineTracks(video=[ct], subtitles=[st])
        self.assertEqual(len(tt.video), 1)
        self.assertEqual(len(tt.subtitles), 1)


# ======================================================================
# 14. BaseInput
# ======================================================================
class TestBaseInput(unittest.TestCase):
    def test_default_mode(self):
        bi = BaseInput()
        self.assertEqual(bi.mode, "auto")

    def test_all_modes(self):
        for mode in ["auto", "skip", "default"]:
            bi = BaseInput(mode=mode)
            self.assertEqual(bi.mode, mode)

    def test_invalid_mode(self):
        with self.assertRaises(ValidationError):
            BaseInput(mode="invalid_mode")


# ======================================================================
# 15. SearchMediaInput
# ======================================================================
class TestSearchMediaInput(unittest.TestCase):
    def test_defaults(self):
        smi = SearchMediaInput()
        self.assertEqual(smi.mode, "auto")
        self.assertEqual(smi.photo_number, 0)
        self.assertEqual(smi.video_number, 5)
        self.assertEqual(smi.search_keyword, "scenery")
        self.assertEqual(smi.orientation, "landscape")
        self.assertEqual(smi.min_video_duration, 1)
        self.assertEqual(smi.max_video_duration, 30)

    def test_custom_values(self):
        smi = SearchMediaInput(
            photo_number=3, video_number=10, search_keyword="mountain",
            orientation="portrait", min_video_duration=5, max_video_duration=60,
        )
        self.assertEqual(smi.photo_number, 3)
        self.assertEqual(smi.orientation, "portrait")

    def test_invalid_orientation(self):
        with self.assertRaises(ValidationError):
            SearchMediaInput(orientation="square")


# ======================================================================
# 16. SplitShotsInput / Output
# ======================================================================
class TestSplitShots(unittest.TestCase):
    def test_input_defaults(self):
        ssi = SplitShotsInput()
        self.assertEqual(ssi.mode, "auto")
        self.assertEqual(ssi.min_shot_duration, 1000)
        self.assertEqual(ssi.max_shot_duration, 10000)

    def test_output_with_clips_only(self):
        sso = SplitShotsOutput(clip_captions=[], overall={"scenes": "1"})
        self.assertEqual(sso.clip_captions, [])
        self.assertEqual(sso.overall, {"scenes": "1"})

    def test_output_with_clips(self):
        clip = Clip(clip_id="c1", caption="Shot 1", media_type="video", path="/v.mp4")
        sso = SplitShotsOutput(clip_captions=[clip], overall={"scenes": "2"})
        self.assertEqual(len(sso.clip_captions), 1)
        self.assertEqual(sso.overall, {"scenes": "2"})


# ======================================================================
# 17. UnderstandClipsInput / Output
# ======================================================================
class TestUnderstandClips(unittest.TestCase):
    def test_input_defaults(self):
        uci = UnderstandClipsInput()
        self.assertEqual(uci.mode, "auto")

    def test_output_with_fields(self):
        uco = UnderstandClipsOutput(clip_captions=[], overall={"key": "val"})
        self.assertEqual(uco.clip_captions, [])
        self.assertEqual(uco.overall, {"key": "val"})


# ======================================================================
# 18. FilterClipsInput / Output
# ======================================================================
class TestFilterClips(unittest.TestCase):
    def test_input_defaults(self):
        fci = FilterClipsInput()
        self.assertEqual(fci.mode, "auto")
        self.assertEqual(fci.user_request, "")

    def test_input_with_request(self):
        fci = FilterClipsInput(user_request="Find outdoor scenes")
        self.assertEqual(fci.user_request, "Find outdoor scenes")

    def test_output_with_fields(self):
        fco = FilterClipsOutput(clip_captions=[], overall={"filtered": "true"})
        self.assertEqual(fco.clip_captions, [])
        self.assertEqual(fco.overall, {"filtered": "true"})


# ======================================================================
# 19. GroupClipsInput / Output
# ======================================================================
class TestGroupClipsInOut(unittest.TestCase):
    def test_input_defaults(self):
        gci = GroupClipsInput()
        self.assertEqual(gci.mode, "auto")

    def test_output_defaults(self):
        gco = GroupClipsOutput()
        self.assertEqual(gco.groups, [])


# ======================================================================
# 20. GenerateScript
# ======================================================================
class TestGenerateScript(unittest.TestCase):
    def test_input_defaults(self):
        gsi = GenerateScriptInput()
        self.assertEqual(gsi.mode, "auto")
        self.assertEqual(gsi.user_request, "")
        self.assertEqual(gsi.custom_script, {})

    def test_input_with_custom_script(self):
        gsi = GenerateScriptInput(
            mode="auto",
            custom_script={"group_id": "g1", "raw_text": "Custom text", "title": "My Video"},
        )
        self.assertEqual(gsi.custom_script["title"], "My Video")

    def test_output_with_group_scripts(self):
        gso = GenerateScriptOutput(group_scripts=[], title="My Amazing Video")
        self.assertEqual(gso.group_scripts, [])
        self.assertEqual(gso.title, "My Amazing Video")


# ======================================================================
# 21. GenerateVoiceover
# ======================================================================
class TestGenerateVoiceover(unittest.TestCase):
    def test_input_defaults(self):
        gvi = GenerateVoiceoverInput()
        self.assertEqual(gvi.mode, "auto")
        self.assertEqual(gvi.user_request, "")

    def test_output_defaults(self):
        gvo = GenerateVoiceoverOutput()
        self.assertEqual(gvo.voiceover, [])

    def test_output_with_voiceover(self):
        vo = Voiceover(group_id="g1", voiceover_id="vo1", path="/v.mp3", duration=2000)
        gvo = GenerateVoiceoverOutput(voiceover=[vo])
        self.assertEqual(len(gvo.voiceover), 1)


# ======================================================================
# 22. SelectBGM
# ======================================================================
class TestSelectBGM(unittest.TestCase):
    def test_input_defaults(self):
        sbi = SelectBGMInput()
        self.assertEqual(sbi.mode, "auto")
        self.assertEqual(sbi.filter_include, {})
        self.assertEqual(sbi.filter_exclude, {})

    def test_input_with_filters(self):
        sbi = SelectBGMInput(
            filter_include={"mood": ["Happy"], "genre": ["Pop"]},
            filter_exclude={"lang": ["bgm"]},
        )
        self.assertEqual(sbi.filter_include["mood"], ["Happy"])
        self.assertEqual(sbi.filter_exclude["lang"], ["bgm"])

    def test_output_defaults(self):
        sbo = SelectBGMOutput()
        self.assertEqual(sbo.bgm, [])


# ======================================================================
# 23. RecommendTransition
# ======================================================================
class TestRecommendTransition(unittest.TestCase):
    def test_defaults(self):
        rti = RecommendTransitionInput()
        self.assertEqual(rti.mode, "auto")
        self.assertEqual(rti.duration, 1000)

    def test_custom_duration(self):
        rti = RecommendTransitionInput(duration=2000)
        self.assertEqual(rti.duration, 2000)

    def test_skip_mode(self):
        rti = RecommendTransitionInput(mode="skip")
        self.assertEqual(rti.mode, "skip")

    def test_output_inherits_input_defaults(self):
        rto = RecommendTransitionOutput()
        self.assertEqual(rto.mode, "auto")


# ======================================================================
# 24. GenerateAITransition
# ======================================================================
class TestGenerateAITransition(unittest.TestCase):
    def test_defaults(self):
        gati = GenerateAITransitionInput()
        self.assertEqual(gati.mode, "auto")
        self.assertEqual(gati.user_request, "")
        self.assertIsNone(gati.duration)
        self.assertIsNone(gati.resolution)

    def test_with_prompt(self):
        gati = GenerateAITransitionInput(
            user_request="Smooth zoom transition",
            duration=6,
            resolution="720P",
        )
        self.assertEqual(gati.user_request, "Smooth zoom transition")
        self.assertEqual(gati.duration, 6)
        self.assertEqual(gati.resolution, "720P")


# ======================================================================
# 25. PlanTimeline
# ======================================================================
class TestPlanTimeline(unittest.TestCase):
    def test_input_defaults(self):
        pti = PlanTimelineInput()
        self.assertTrue(pti.use_beats)
        self.assertFalse(pti.is_speech_rough_cut)
        self.assertFalse(pti.is_ai_transition)
        self.assertEqual(pti.image_duration_ms, 3000)

    def test_input_custom(self):
        pti = PlanTimelineInput(
            use_beats=False, is_speech_rough_cut=True, image_duration_ms=5000,
        )
        self.assertFalse(pti.use_beats)
        self.assertTrue(pti.is_speech_rough_cut)
        self.assertEqual(pti.image_duration_ms, 5000)

    def test_ai_transition_input(self):
        ptai = PlanTimelineAITransitionInput()
        self.assertEqual(ptai.mode, "auto")
        self.assertEqual(ptai.image_duration_ms, 3000)

    def test_output_defaults(self):
        pto = PlanTimelineOutput()
        self.assertEqual(pto.tracks, [])


# ======================================================================
# 26. RenderVideoInput
# ======================================================================
class TestRenderVideoInput(unittest.TestCase):
    def test_defaults(self):
        rvi = RenderVideoInput()
        self.assertIsNone(rvi.aspect_ratio)
        self.assertIsNone(rvi.output_max_dimension_px)
        self.assertEqual(rvi.clip_compose_mode, "padding")
        self.assertEqual(rvi.bg_color, (0, 0, 0))
        self.assertEqual(rvi.crf, 23)
        self.assertEqual(rvi.font_color, (255, 255, 255, 255))
        self.assertEqual(rvi.font_size, 40)
        self.assertEqual(rvi.margin_bottom, 270)
        self.assertEqual(rvi.stroke_width, 2)
        self.assertEqual(rvi.stroke_color, (0, 0, 0, 255))
        self.assertEqual(rvi.bgm_volume_scale, 0.25)
        self.assertEqual(rvi.tts_volume_scale, 2.0)
        self.assertFalse(rvi.include_video_audio)
        self.assertEqual(rvi.video_volume_scale, 1.0)

    def test_custom_aspect_ratio(self):
        rvi = RenderVideoInput(aspect_ratio="9:16", output_max_dimension_px=720)
        self.assertEqual(rvi.aspect_ratio, "9:16")
        self.assertEqual(rvi.output_max_dimension_px, 720)

    def test_crop_mode(self):
        rvi = RenderVideoInput(clip_compose_mode="crop")
        self.assertEqual(rvi.clip_compose_mode, "crop")

    def test_with_audio(self):
        rvi = RenderVideoInput(include_video_audio=True, bgm_volume_scale=0.5)
        self.assertTrue(rvi.include_video_audio)
        self.assertEqual(rvi.bgm_volume_scale, 0.5)


# ======================================================================
# 27. RecommendScriptTemplate
# ======================================================================
class TestRecommendScriptTemplate(unittest.TestCase):
    def test_defaults(self):
        rsti = RecommendScriptTemplateInput()
        self.assertEqual(rsti.mode, "auto")
        self.assertEqual(rsti.filter_include, {})
        self.assertEqual(rsti.filter_exclude, {})

    def test_with_filters(self):
        rsti = RecommendScriptTemplateInput(
            filter_include={"tags": ["Life", "Food"]},
            filter_exclude={"tags": ["Tech"]},
        )
        self.assertEqual(rsti.filter_include["tags"], ["Life", "Food"])


# ======================================================================
# 28. LocalASR & SpeechRoughCut
# ======================================================================
class TestASRAndRoughCut(unittest.TestCase):
    def test_local_asr_defaults(self):
        lasr = LocalASRInput()
        self.assertEqual(lasr.mode, "auto")

    def test_speech_rough_cut_defaults(self):
        src = SpeechRoughCutInput()
        self.assertEqual(src.mode, "auto")
        self.assertEqual(src.gap_threshold, 400)
        self.assertEqual(src.user_request, "")

    def test_speech_rough_cut_custom(self):
        src = SpeechRoughCutInput(gap_threshold=600, user_request="Short clips only")
        self.assertEqual(src.gap_threshold, 600)
        self.assertEqual(src.user_request, "Short clips only")


# ======================================================================
# 29. RecommendText
# ======================================================================
class TestRecommendText(unittest.TestCase):
    def test_defaults(self):
        rti = RecommendTextInput()
        self.assertEqual(rti.mode, "auto")
        self.assertEqual(rti.user_request, "")
        self.assertEqual(rti.filter_include, {})

    def test_output_defaults(self):
        rto = RecommendTextOutput()
        self.assertEqual(rto.mode, "auto")


# ======================================================================
# 30. NodeState
# ======================================================================
class TestNodeState(unittest.TestCase):
    def test_create_node_state(self):
        mock_llm = MagicMock()
        mock_ctx = MagicMock()
        mock_summary = MagicMock()

        ns = NodeState(
            session_id="s1",
            artifact_id="a1",
            lang="en",
            node_summary=mock_summary,
            llm=mock_llm,
            mcp_ctx=mock_ctx,
        )
        self.assertEqual(ns.session_id, "s1")
        self.assertEqual(ns.artifact_id, "a1")
        self.assertEqual(ns.lang, "en")
        self.assertIs(ns.llm, mock_llm)
        self.assertIs(ns.mcp_ctx, mock_ctx)
        self.assertIs(ns.node_summary, mock_summary)

    def test_node_state_is_dataclass(self):
        mock_llm = MagicMock()
        mock_ctx = MagicMock()
        mock_summary = MagicMock()

        ns = NodeState(
            session_id="s1", artifact_id="a1", lang="zh",
            node_summary=mock_summary, llm=mock_llm, mcp_ctx=mock_ctx,
        )
        # Dataclasses support repr
        self.assertIn("s1", repr(ns))
        self.assertIn("a1", repr(ns))


# ======================================================================
# 31. ModelValidator edge cases
# ======================================================================
class TestModelValidatorEdgeCases(unittest.TestCase):
    def test_video_metadata_has_audio_false_no_sample_rate_ok(self):
        vm = VideoMetadata(width=640, height=480, duration=1000.0, fps=24.0,
                           has_audio=False)
        self.assertFalse(vm.has_audio)

    def test_media_union_resolves_to_video(self):
        meta = {"width": 1920, "height": 1080, "duration": 5000.0,
                "fps": 30.0, "has_audio": True, "audio_sample_rate_hz": 48000}
        m = Media.model_validate({
            "media_id": "v2", "path": "/v2.mp4", "media_type": "video",
            "metadata": meta,
        })
        self.assertIsInstance(m.metadata, VideoMetadata)
        self.assertTrue(m.metadata.has_audio)

    def test_media_union_resolves_to_image(self):
        meta = {"width": 800, "height": 600}
        m = Media.model_validate({
            "media_id": "i2", "path": "/i2.png", "media_type": "image",
            "metadata": meta,
        })
        self.assertIsInstance(m.metadata, ImageMetadata)

    def test_media_empty_metadata_fails_as_video(self):
        with self.assertRaises(ValidationError):
            Media.model_validate({
                "media_id": "bad", "path": "/x", "media_type": "video",
                "metadata": {},
            })

    def test_subtitle_unit_empty_text_still_valid(self):
        su = SubtitleUnit(unit_id="su1", index_in_group=5, text="")
        self.assertEqual(su.text, "")

    def test_bgm_invalid_id_type(self):
        # bgm_id should be a string
        bgm = BGM(bgm_id="bgm99", path="/bgm.mp3", duration=60000, bpm=90.0)
        self.assertEqual(bgm.bgm_id, "bgm99")


# ======================================================================
# 32. Input mode enumeration validation across all input models
# ======================================================================
class TestModeValidation(unittest.TestCase):
    def _all_auto(self, *models):
        for model_cls in models:
            instance = model_cls()
            self.assertEqual(instance.mode, "auto",
                             f"{model_cls.__name__} should default to 'auto'")

    def test_all_inputs_default_to_auto(self):
        self._all_auto(
            BaseInput, LoadMediaInput, SearchMediaInput,
            SplitShotsInput, LocalASRInput, SpeechRoughCutInput,
            UnderstandClipsInput, FilterClipsInput, GroupClipsInput,
            GenerateScriptInput, GenerateVoiceoverInput,
            RecommendScriptTemplateInput, SelectBGMInput,
            RecommendTransitionInput, GenerateAITransitionInput,
            RecommendTextInput, PlanTimelineAITransitionInput, RenderVideoInput,
        )


if __name__ == "__main__":
    unittest.main()
