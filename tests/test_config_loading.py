import os
import sys
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT_ROOT, "src")
for path in (SRC, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)


from open_storyline.config import default_config_path, load_settings  # noqa: E402


MINIMAL_CONFIG = textwrap.dedent(
    """
    [developer]
    developer_mode = false
    print_context = false

    [project]
    media_dir = "./outputs/media"
    bgm_dir = "./resource/bgms"
    outputs_dir = "./outputs"

    [llm]
    model = "test-llm"
    base_url = "https://example.com/llm"
    api_key = "placeholder"

    [vlm]
    model = "test-vlm"
    base_url = "https://example.com/vlm"
    api_key = "placeholder"

    [local_mcp_server]
    port = 8001

    [skills]
    skill_dir = "./.storyline/skills"

    [search_media]
    pexels_api_key = "placeholder"

    [split_shots]
    transnet_weights = ".storyline/models/transnetv2-pytorch-weights.pth"

    [understand_clips]
    sample_fps = 2.0
    max_frames = 64

    [group_clips]
    base_max_tokens = 4096
    tokens_per_clip = 48
    max_tokens_cap = 16384
    retry_token_step = 2048
    max_parse_retries = 2

    [script_template]
    script_template_dir = "./resource/script_templates"
    script_template_info_path = "./resource/script_templates/meta.json"

    [generate_voiceover]
    tts_provider_params_path = "./resource/tts/providers.json"

    [generate_voiceover.providers.minimax]
    base_url = "https://voice.example.com"
    api_key = "placeholder"

    [generate_voiceover.providers.bytedance]
    uid = "placeholder"
    appid = "placeholder"
    access_token = "placeholder"

    [generate_ai_transition]

    [generate_ai_transition.providers.minimax]
    model_name = "transition-model"
    api_key = "placeholder"

    [generate_ai_transition.providers.dashscope]
    model_name = "wanx2.1"
    api_key = "placeholder"

    [select_bgm]
    sample_rate = 22050
    hop_length = 2048
    frame_length = 2048

    [recommend_text]
    font_info_path = "./resource/fonts/font_info.json"

    [plan_timeline]
    beat_type_max = 1
    title_duration = 0
    bgm_loop = true
    min_clip_duration = 1000
    estimate_text_min = 1500
    estimate_text_char_per_sec = 6.0
    image_default_duration = 3000
    group_margin_over_voiceover = 1000

    [plan_timeline_pro]
    min_single_text_duration = 200
    max_text_duration = 5000
    img_default_duration = 1500
    min_group_margin = 1500
    max_group_margin = 2000
    min_clip_duration = 1000
    tts_margin_mode = "random"
    min_tts_margin = 300
    max_tts_margin = 400
    text_tts_offset_mode = "random"
    min_text_tts_offset = 0
    max_text_tts_offset = 0
    long_short_text_duration = 3000
    long_text_margin_rate = 0.0
    short_text_margin_rate = 0.0
    text_duration_mode = "with_tts"
    is_text_beats = false
    """
)


class ConfigLoadingTests(unittest.TestCase):
    def test_load_settings_resolves_paths_relative_to_config_location(self):
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "configs"
            config_dir.mkdir()
            config_path = config_dir / "config.toml"
            config_path.write_text(MINIMAL_CONFIG, encoding="utf-8")

            settings = load_settings(config_path)

            self.assertEqual(settings.project.media_dir, (config_dir / "outputs/media").resolve())
            self.assertEqual(settings.project.bgm_dir, (config_dir / "resource/bgms").resolve())
            self.assertEqual(settings.project.outputs_dir, (config_dir / "outputs").resolve())
            self.assertEqual(settings.skills.skill_dir, (config_dir / ".storyline/skills").resolve())
            self.assertEqual(
                settings.generate_voiceover.tts_provider_params_path,
                (config_dir / "resource/tts/providers.json").resolve(),
            )
            self.assertEqual(
                settings.recommend_text.font_info_path,
                (config_dir / "resource/fonts/font_info.json").resolve(),
            )

    def test_load_settings_preserves_nested_provider_configuration(self):
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_path.write_text(MINIMAL_CONFIG, encoding="utf-8")

            settings = load_settings(config_path)

            self.assertEqual(
                settings.generate_voiceover.providers["minimax"],
                {
                    "base_url": "https://voice.example.com",
                    "api_key": "placeholder",
                },
            )
            self.assertEqual(
                settings.generate_voiceover.providers["bytedance"],
                {
                    "uid": "placeholder",
                    "appid": "placeholder",
                    "access_token": "placeholder",
                },
            )
            self.assertEqual(
                settings.generate_ai_transition.providers["minimax"],
                {
                    "model_name": "transition-model",
                    "api_key": "placeholder",
                },
            )
            self.assertEqual(
                settings.generate_ai_transition.providers["dashscope"],
                {
                    "model_name": "wanx2.1",
                    "api_key": "placeholder",
                },
            )

    def test_default_config_path_prefers_openstoryline_env_override(self):
        with patch.dict(os.environ, {"OPENSTORYLINE_CONFIG": "/tmp/custom-config.toml"}, clear=False):
            self.assertEqual(default_config_path(), "/tmp/custom-config.toml")

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(default_config_path(), "config.toml")


if __name__ == "__main__":
    unittest.main()
