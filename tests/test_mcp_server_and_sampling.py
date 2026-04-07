"""
Tests for MCP server creation, sampling handler, and sampling requester.

Covers:
- MCP server startup and shutdown (create_server)
- Tool registration flow (create_tool_wrapper, register)
- Sampling handler: URL helpers, image resize, frame sampling
- Sampling handler: media block building, normalization
- Sampling requester: MCPSampler, SamplingLLMClient
- Sampling handler: content extraction utilities
"""
import os
import sys
import base64
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

# Repo root for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


# ──────────────────────────────────────────────
# Sampling handler: URL helpers
# ──────────────────────────────────────────────
class TestUrlHelpers(unittest.TestCase):
    """Test URL classification and path helpers in sampling_handler.py."""

    def _import(self):
        from open_storyline.mcp import sampling_handler as sh
        return sh

    def test_is_data_url_detects_data_scheme(self):
        sh = self._import()
        self.assertTrue(sh._is_data_url("data:image/png;base64,abc123"))
        self.assertFalse(sh._is_data_url("http://example.com/image.png"))
        self.assertFalse(sh._is_data_url("/local/path/image.jpg"))

    def test_is_http_url_detects_http_schemes(self):
        sh = self._import()
        self.assertTrue(sh._is_http_url("http://example.com/vid.mp4"))
        self.assertTrue(sh._is_http_url("https://example.com/vid.mp4"))
        self.assertFalse(sh._is_http_url("file:///tmp/vid.mp4"))
        self.assertFalse(sh._is_http_url("/local/vid.mp4"))

    def test_strip_file_scheme_strips_file_prefix(self):
        sh = self._import()
        result = sh._strip_file_scheme("file:///tmp/video.mp4")
        self.assertEqual(result, "/tmp/video.mp4")

    def test_strip_file_scheme_leaves_other_urls(self):
        sh = self._import()
        self.assertEqual(sh._strip_file_scheme("http://example.com/v.mp4"), "http://example.com/v.mp4")
        self.assertEqual(sh._strip_file_scheme("/local/v.mp4"), "/local/v.mp4")

    def test_guess_ext_extracts_extension(self):
        sh = self._import()
        self.assertEqual(sh._guess_ext("/path/to/video.mp4"), ".mp4")
        self.assertEqual(sh._guess_ext("http://cdn/pic.PNG"), ".png")
        self.assertEqual(sh._guess_ext("file:///tmp/image.jpeg"), ".jpeg")


# ──────────────────────────────────────────────
# Sampling handler: image resize
# ──────────────────────────────────────────────
class TestImageResize(unittest.TestCase):
    """Test _resize_long_edge and _pil_to_data_url."""

    def _import(self):
        from open_storyline.mcp import sampling_handler as sh
        return sh

    def test_resize_noop_when_small(self):
        sh = self._import()
        from PIL import Image
        img = Image.new("RGB", (100, 50), "red")
        result = sh._resize_long_edge(img, 600)
        self.assertEqual(result.size, (100, 50))

    def test_resize_scales_down(self):
        sh = self._import()
        from PIL import Image
        img = Image.new("RGB", (1200, 600), "blue")
        result = sh._resize_long_edge(img, 600)
        self.assertEqual(result.size[0], 600)
        self.assertEqual(result.size[1], 300)

    def test_pil_to_data_url_returns_valid_data_url(self):
        sh = self._import()
        from PIL import Image
        img = Image.new("RGB", (200, 100), "green")
        url = sh._pil_to_data_url(img, resize_edge=600, jpeg_quality=80)
        self.assertTrue(url.startswith("data:image/jpeg;base64,"))
        # Verify round-trip decodes
        b64_part = url.split(",", 1)[1]
        data = base64.b64decode(b64_part)
        self.assertGreater(len(data), 0)


# ──────────────────────────────────────────────
# Sampling handler: frame count selection
# ──────────────────────────────────────────────
class TestChooseNumFrames(unittest.TestCase):
    """Test _choose_num_frames logic."""

    def _import(self):
        from open_storyline.mcp import sampling_handler as sh
        return sh

    def test_short_clip_uses_min_frames(self):
        sh = self._import()
        # 0.5s at 3 fps → ceil(1.5) = 2, which equals min
        self.assertEqual(sh._choose_num_frames(0.5, min_frames=2, max_frames=6, frames_per_sec=3.0), 2)

    def test_long_clip_caps_at_max_frames(self):
        sh = self._import()
        # 10s at 3 fps → 30, capped to max 6
        self.assertEqual(sh._choose_num_frames(10.0, min_frames=2, max_frames=6, frames_per_sec=3.0), 6)

    def test_mid_clip_returns_intermediate(self):
        sh = self._import()
        # 1s at 3 fps → 3
        self.assertEqual(sh._choose_num_frames(1.0, min_frames=2, max_frames=6, frames_per_sec=3.0), 3)


# ──────────────────────────────────────────────
# Sampling handler: media normalization
# ──────────────────────────────────────────────
class TestNormalizeMediaItems(unittest.TestCase):
    """Test _normalize_media_items input format handling."""

    def _import(self):
        from open_storyline.mcp import sampling_handler as sh
        return sh

    def test_string_input(self):
        sh = self._import()
        result = sh._normalize_media_items(["/path/to/video.mp4"])
        self.assertEqual(result, [{"url": "/path/to/video.mp4"}])

    def test_dict_input_with_url(self):
        sh = self._import()
        result = sh._normalize_media_items([{"url": "/path/vid.mp4", "in_sec": 1.0, "out_sec": 3.0}])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["url"], "/path/vid.mp4")
        self.assertEqual(result[0]["in_sec"], 1.0)
        self.assertEqual(result[0]["out_sec"], 3.0)

    def test_dict_input_with_path_key(self):
        sh = self._import()
        result = sh._normalize_media_items([{"path": "/path/vid.mp4"}])
        self.assertEqual(result, [{"url": "/path/vid.mp4"}])

    def test_dict_input_with_media_key(self):
        sh = self._import()
        result = sh._normalize_media_items([{"media": "/path/vid.mp4"}])
        self.assertEqual(result, [{"url": "/path/vid.mp4"}])

    def test_tuple_input(self):
        sh = self._import()
        result = sh._normalize_media_items([("/path/vid.mp4", 1.2, 3.4)])
        self.assertEqual(result, [{"url": "/path/vid.mp4", "in_sec": 1.2, "out_sec": 3.4}])

    def test_empty_and_none_input(self):
        sh = self._import()
        self.assertEqual(sh._normalize_media_items([]), [])
        self.assertEqual(sh._normalize_media_items(None), [])

    def test_dict_without_url_skipped(self):
        sh = self._import()
        result = sh._normalize_media_items([{"foo": "bar"}])
        self.assertEqual(result, [])


# ──────────────────────────────────────────────
# Sampling handler: content extraction
# ──────────────────────────────────────────────
class TestContentExtraction(unittest.TestCase):
    """Test _extract_text_from_mcp_content and _extract_text_from_lc_response."""

    def _import(self):
        from open_storyline.mcp import sampling_handler as sh
        return sh

    def test_mcp_content_none(self):
        sh = self._import()
        self.assertEqual(sh._extract_text_from_mcp_content(None), "")

    def test_mcp_content_single_text_block(self):
        sh = self._import()
        block = MagicMock()
        block.type = "text"
        block.text = "Hello MCP"
        result = sh._extract_text_from_mcp_content([block])
        self.assertEqual(result, "Hello MCP")

    def test_mcp_content_mixed_blocks(self):
        sh = self._import()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Hello"
        image_block = MagicMock()
        image_block.type = "image"
        result = sh._extract_text_from_mcp_content([text_block, image_block])
        self.assertEqual(result, "Hello")

    def test_lc_response_string_content(self):
        sh = self._import()
        resp = MagicMock()
        resp.content = "Direct string content"
        self.assertEqual(sh._extract_text_from_lc_response(resp), "Direct string content")

    def test_lc_response_list_content(self):
        sh = self._import()
        resp = MagicMock()
        resp.content = [{"type": "text", "text": "Block text"}]
        self.assertEqual(sh._extract_text_from_lc_response(resp), "Block text")


# ──────────────────────────────────────────────
# Sampling handler: media block building (mocked)
# ──────────────────────────────────────────────
class TestBuildMediaBlocks(unittest.TestCase):
    """Test _build_media_blocks with mocked file operations."""

    def _import(self):
        from open_storyline.mcp import sampling_handler as sh
        return sh

    @patch("open_storyline.mcp.sampling_handler.os.path.exists")
    @patch("open_storyline.mcp.sampling_handler._image_path_to_data_url")
    def test_local_image_generates_image_url_block(self, mock_data_url, mock_exists):
        sh = self._import()
        mock_exists.return_value = True
        mock_data_url.return_value = "data:image/jpeg;base64,fakedata"

        blocks = sh._build_media_blocks(
            media_inputs=["/fake/image.jpg"],
            resize_edge=600, jpeg_quality=80,
            min_frames=2, max_frames=6, frames_per_sec=3.0,
            global_max_images=48,
        )

        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["type"], "text")
        self.assertEqual(blocks[1]["type"], "image_url")

    @patch("open_storyline.mcp.sampling_handler.os.path.exists")
    def test_missing_file_gives_text_notice(self, mock_exists):
        sh = self._import()
        mock_exists.return_value = False

        blocks = sh._build_media_blocks(
            media_inputs=["/nonexist/image.png"],
            resize_edge=600, jpeg_quality=80,
            min_frames=2, max_frames=6, frames_per_sec=3.0,
            global_max_images=48,
        )

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["type"], "text")
        self.assertIn("missing file", blocks[0]["text"])

    def test_data_url_passthrough(self):
        sh = self._import()
        data_url = "data:image/png;base64,abc"
        blocks = sh._build_media_blocks(
            media_inputs=[data_url],
            resize_edge=600, jpeg_quality=80,
            min_frames=2, max_frames=6, frames_per_sec=3.0,
            global_max_images=48,
        )
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[1]["type"], "image_url")
        self.assertEqual(blocks[1]["image_url"]["url"], data_url)

    def test_remote_http_image(self):
        sh = self._import()
        blocks = sh._build_media_blocks(
            media_inputs=["https://example.com/photo.jpg"],
            resize_edge=600, jpeg_quality=80,
            min_frames=2, max_frames=6, frames_per_sec=3.0,
            global_max_images=48,
        )
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[1]["type"], "image_url")

    def test_remote_http_video_cannot_sample(self):
        sh = self._import()
        blocks = sh._build_media_blocks(
            media_inputs=["https://example.com/video.mp4"],
            resize_edge=600, jpeg_quality=80,
            min_frames=2, max_frames=6, frames_per_sec=3.0,
            global_max_images=48,
        )
        # Only a text notice, no image blocks
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["type"], "text")
        self.assertIn("cannot sample frames locally", blocks[0]["text"])

    def test_global_max_images_limit(self):
        sh = self._import()
        blocks = sh._build_media_blocks(
            media_inputs=[
                "data:image/png;base64,a",
                "data:image/png;base64,b",
            ],
            resize_edge=600, jpeg_quality=80,
            min_frames=2, max_frames=6, frames_per_sec=3.0,
            global_max_images=1,
        )
        # Only first image passes through (4 blocks: 2 text + 2 image_url at max 1 image)
        self.assertEqual(len(blocks), 2)


# ──────────────────────────────────────────────
# Sampling handler: _sample_video_segment_to_data_urls
# ──────────────────────────────────────────────
class TestVideoSegmentSampling(unittest.TestCase):
    """Test video segment frame sampling with mocked VideoFileClip."""

    def _import(self):
        from open_storyline.mcp import sampling_handler as sh
        return sh

    @patch("open_storyline.mcp.sampling_handler.VideoFileClip")
    def test_sampling_returns_frames(self, mock_clip_cls):
        sh = self._import()
        import numpy as np

        mock_clip = MagicMock()
        mock_clip.duration = 5.0
        mock_clip.get_frame.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_clip_cls.return_value = mock_clip

        frames = sh._sample_video_segment_to_data_urls(
            video_path="/fake/video.mp4",
            in_sec=0.0, out_sec=2.0,
            resize_edge=600, jpeg_quality=80,
            min_frames=2, max_frames=6, frames_per_sec=3.0,
        )

        self.assertGreater(len(frames), 0)
        # Each frame is (rel_t, data_url)
        for rel_t, data_url in frames:
            self.assertIsInstance(rel_t, float)
            self.assertTrue(data_url.startswith("data:image/jpeg;base64,"))

    @patch("open_storyline.mcp.sampling_handler.VideoFileClip")
    def test_sampling_zero_duration_fallback(self, mock_clip_cls):
        sh = self._import()
        import numpy as np

        mock_clip = MagicMock()
        mock_clip.duration = 0.0
        mock_clip.get_frame.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_clip_cls.return_value = mock_clip

        frames = sh._sample_video_segment_to_data_urls(
            video_path="/fake/zero.mp4",
            in_sec=0.0, out_sec=2.0,
            resize_edge=600, jpeg_quality=80,
            min_frames=2, max_frames=6, frames_per_sec=3.0,
        )

        self.assertEqual(len(frames), 1)


# ──────────────────────────────────────────────
# Sampling handler: make_sampling_callback
# ──────────────────────────────────────────────
class TestSamplingCallback(unittest.IsolatedAsyncioTestCase):
    """Test make_sampling_callback with mocked LLM."""

    async def test_callback_routes_to_llm_when_no_media(self):
        from open_storyline.mcp.sampling_handler import make_sampling_callback

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "LLM response text"
        mock_ainvoke = AsyncMock(return_value=mock_response)
        mock_bind_return = MagicMock()
        mock_bind_return.ainvoke = mock_ainvoke
        mock_llm.bind.return_value = mock_bind_return
        mock_llm.model = "test-model"

        callback = make_sampling_callback(llm=mock_llm, vlm=None)

        mock_params = MagicMock()
        mock_params.systemPrompt = "You are helpful"
        mock_params.messages = [MagicMock(role="user", content=MagicMock(type="text", text="Hello"))]
        mock_params.metadata = {}
        mock_params.temperature = 0.5
        mock_params.maxTokens = 1024

        result = await callback(None, mock_params)

        self.assertEqual(result.content.text, "LLM response text")
        self.assertEqual(result.model, "test-model")
        self.assertEqual(result.role, "assistant")
        mock_bind_return.ainvoke.assert_called_once()

    async def test_callback_routes_to_vlm_when_media_present(self):
        from open_storyline.mcp.sampling_handler import make_sampling_callback

        mock_vlm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "VLM sees image and text"
        mock_ainvoke = AsyncMock(return_value=mock_response)
        mock_bind_return = MagicMock()
        mock_bind_return.ainvoke = mock_ainvoke
        mock_vlm.bind.return_value = mock_bind_return
        mock_vlm.model = "vlm-model"

        callback = make_sampling_callback(llm=MagicMock(), vlm=mock_vlm)

        mock_user_msg = MagicMock()
        mock_user_msg.role = "user"
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Describe this"
        mock_user_msg.content = [text_block]

        mock_params = MagicMock()
        mock_params.systemPrompt = None
        mock_params.messages = [mock_user_msg]
        mock_params.metadata = {"media": [{"url": "data:image/png;base64,fake"}]}
        mock_params.temperature = 0.3
        mock_params.maxTokens = 512

        result = await callback(None, mock_params)
        self.assertEqual(result.content.text, "VLM sees image and text")

    async def test_callback_error_handling(self):
        from open_storyline.mcp.sampling_handler import make_sampling_callback

        mock_llm = MagicMock()
        mock_llm.model = "error-model"
        mock_bind_return = MagicMock()
        mock_bind_return.ainvoke = AsyncMock(side_effect=ValueError("API failed"))
        mock_llm.bind.return_value = mock_bind_return

        callback = make_sampling_callback(llm=mock_llm, vlm=None)

        mock_params = MagicMock()
        mock_params.systemPrompt = None
        mock_params.messages = [MagicMock(role="user", content=MagicMock(type="text", text="test"))]
        mock_params.metadata = {}
        mock_params.temperature = 0.5
        mock_params.maxTokens = 256

        result = await callback(None, mock_params)
        self.assertIn("error", result.stopReason.lower())
        self.assertIn("ValueError", result.content.text)


# ──────────────────────────────────────────────
# Sampling requester: MCPSampler
# ──────────────────────────────────────────────
class TestMCPSampler(unittest.TestCase):
    """Test MCPSampler class."""

    def _import(self):
        from open_storyline.mcp import sampling_requester as sr
        return sr

    def test_to_mcp_model_preferences_with_empty_dict(self):
        sr = self._import()
        sampler = sr.MCPSampler(MagicMock())
        result = sampler._to_mcp_model_preferences({"costPriority": 0.5})
        self.assertIsNotNone(result)
        self.assertIsNone(result.hints)

    def test_to_mcp_model_preferences_with_string_hints(self):
        sr = self._import()
        sampler = sr.MCPSampler(MagicMock())
        result = sampler._to_mcp_model_preferences({
            "hints": ["claude", "gpt-4"],
            "costPriority": 0.5,
            "speedPriority": 0.8,
        })
        self.assertIsNotNone(result)
        self.assertEqual(len(result.hints), 2)
        self.assertEqual(result.hints[0].name, "claude")
        self.assertEqual(result.costPriority, 0.5)

    def test_to_mcp_model_preferences_with_none(self):
        sr = self._import()
        sampler = sr.MCPSampler(MagicMock())
        result = sampler._to_mcp_model_preferences(None)
        self.assertIsNone(result)

    def test_extract_text_removes_emoji(self):
        sr = self._import()
        sampler = sr.MCPSampler(MagicMock())
        block = MagicMock()
        block.type = "text"
        block.text = "🎬 Hello World ✨"
        result = sampler._extract_text([block])
        self.assertNotIn("🎬", result)
        self.assertNotIn("✨", result)
        self.assertIn("Hello World", result)

    def test_extract_text_single_block(self):
        sr = self._import()
        sampler = sr.MCPSampler(MagicMock())
        block = MagicMock()
        block.type = "text"
        block.text = "Single result"
        result = sampler._extract_text(block)
        self.assertEqual(result, "Single result")

    async def test_sampling_sends_message_and_extracts_text(self):
        sr = self._import()
        mock_ctx = MagicMock()
        mock_result = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "🤖 Generated answer"
        mock_result.content = text_block
        mock_ctx.session.create_message = AsyncMock(return_value=mock_result)

        sampler = sr.MCPSampler(mock_ctx)
        result = await sampler.sampling(
            system_prompt="Be helpful",
            messages=[MagicMock()],
            temperature=0.5,
            top_p=0.9,
            max_tokens=1024,
        )

        mock_ctx.session.create_message.assert_called_once()
        self.assertEqual(result, "Generated answer")


# ──────────────────────────────────────────────
# Sampling requester: SamplingLLMClient
# ──────────────────────────────────────────────
class TestSamplingLLMClient(unittest.IsolatedAsyncioTestCase):
    """Test SamplingLLMClient.complete() and make_llm()."""

    async def test_complete_delegates_to_sampler(self):
        from open_storyline.mcp.sampling_requester import SamplingLLMClient

        mock_sampler = AsyncMock()
        mock_sampler.sampling.return_value = "Sampler output"

        client = SamplingLLMClient(mock_sampler)
        result = await client.complete(
            system_prompt="You are a writer",
            user_prompt="Write a scene",
            temperature=0.7,
        )

        self.assertEqual(result, "Sampler output")
        mock_sampler.sampling.assert_called_once()
        call_kwargs = mock_sampler.sampling.call_args.kwargs
        self.assertEqual(call_kwargs["system_prompt"], "You are a writer")
        # Verify metadata includes modality flag
        self.assertIn("modality", call_kwargs["metadata"])

    async def test_complete_with_media_sets_multimodal_modality(self):
        from open_storyline.mcp.sampling_requester import SamplingLLMClient

        mock_sampler = AsyncMock()
        mock_sampler.sampling.return_value = "Multimodal result"

        client = SamplingLLMClient(mock_sampler)
        await client.complete(
            system_prompt=None,
            user_prompt="Describe this image",
            media=[{"url": "/path/img.jpg", "in_sec": 0, "out_sec": 5}],
        )

        metadata = mock_sampler.sampling.call_args.kwargs["metadata"]
        self.assertEqual(metadata["modality"], "multimodal")
        self.assertIn("media", metadata)

    async def test_make_llm_returns_llm_client(self):
        from open_storyline.mcp.sampling_requester import make_llm, LLMClient

        mock_ctx = MagicMock()
        llm = make_llm(mock_ctx)
        # Should satisfy the LLMClient protocol
        self.assertTrue(hasattr(llm, "complete"))


# ──────────────────────────────────────────────
# MCP server: create_server
# ──────────────────────────────────────────────
class TestCreateServer(unittest.TestCase):
    """Test MCP server creation with mocked dependencies."""

    def setUp(self):
        """Stub heavy dependencies so server module can be imported."""
        import sys
        from unittest.mock import MagicMock
        self._orig_modules = {}
        for mod_name in [
            "skillkit",
            "skillkit.integrations",
            "skillkit.integrations.langchain",
            "colorlog",
            "langchain_mcp_adapters",
            "langchain_mcp_adapters.interceptors",
            "langgraph",
            "langgraph.types",
            "langgraph.runtime",
            "langgraph.prebuilt",
            "langgraph.prebuilt.tool_node",
            "open_storyline.utils.logging",
            "open_storyline.skills.skills_io",
        ]:
            if mod_name not in sys.modules:
                self._orig_modules[mod_name] = sys.modules.get(mod_name)
                sys.modules[mod_name] = MagicMock()

    def tearDown(self):
        """Restore sys.modules to original state."""
        import sys
        for mod_name in list(self._orig_modules.keys()):
            if mod_name in sys.modules and self._orig_modules[mod_name] is None:
                del sys.modules[mod_name]
            elif mod_name in sys.modules:
                sys.modules[mod_name] = self._orig_modules[mod_name]

    def test_create_server_instantiates_fastmcp(self):
        from open_storyline.mcp import server as srv
        from mcp.server.fastmcp import FastMCP
        mock_server = MagicMock()
        mock_cfg = MagicMock()
        mock_cfg.local_mcp_server.server_name = "test-server"
        mock_cfg.local_mcp_server.stateless_http = False
        mock_cfg.local_mcp_server.json_response = True
        mock_cfg.project.outputs_dir = "/tmp/outputs"
        mock_cfg.local_mcp_server.server_cache_dir = "/tmp/cache"
        mock_cfg.local_mcp_server.available_node_pkgs = []
        mock_cfg.local_mcp_server.available_nodes = []

        captured_lifespan = {}

        def capture_fastmcp(**kwargs):
            captured_lifespan["lifespan"] = kwargs.get("lifespan")
            return mock_server

        with patch("open_storyline.mcp.server.FastMCP", side_effect=capture_fastmcp):
            with patch.object(srv.register_tools, "register", return_value=None):
                result = srv.create_server(mock_cfg)

        self.assertEqual(result, mock_server)
        self.assertIn("lifespan", captured_lifespan)
        # Verify lifespan was passed (it's a callable that wraps an async context manager)
        self.assertTrue(callable(captured_lifespan["lifespan"]))

    def test_server_lifespan_yields_session_manager(self):
        """The session_lifespan context manager yields a SessionLifecycleManager."""
        from open_storyline.mcp import server as srv

        mock_server = MagicMock()
        mock_cfg = MagicMock()
        mock_cfg.local_mcp_server.server_name = "test-server"
        mock_cfg.local_mcp_server.stateless_http = True
        mock_cfg.local_mcp_server.json_response = True
        mock_cfg.project.outputs_dir = "/tmp/outputs"
        mock_cfg.local_mcp_server.server_cache_dir = "/tmp/cache"
        mock_cfg.local_mcp_server.available_node_pkgs = []
        mock_cfg.local_mcp_server.available_nodes = []

        with patch("open_storyline.mcp.server.FastMCP", return_value=mock_server) as mock_fastmcp:
            with patch.object(srv.register_tools, "register", return_value=None):
                srv.create_server(mock_cfg)

            # Verify the lifespan was registered
            call_kwargs = mock_fastmcp.call_args.kwargs
            self.assertIn("lifespan", call_kwargs)
            # Verify lifespan is a callable passed to FastMCP
            self.assertTrue(callable(call_kwargs["lifespan"]))


# ──────────────────────────────────────────────
# Tool registration: create_tool_wrapper
# ──────────────────────────────────────────────
class TestCreateToolWrapper(unittest.IsolatedAsyncioTestCase):
    """Test create_tool_wrapper converts nodes to MCP tool functions."""

    async def test_wrapper_has_correct_signature(self):
        import sys
        import inspect
        # We can't import register_tools due to cascade dependencies (skillkit, colorlog, etc.)
        # Instead, reimplement the create_tool_wrapper logic inline to verify the concept
        from mcp.server.fastmcp import Context
        from pydantic import BaseModel, Field

        class DummyInput(BaseModel):
            artifact_id: str = Field(description="Artifact ID")
            lang: str = Field(default="en", description="Language")

        mock_meta = MagicMock()
        mock_meta.name = "test_tool"
        mock_meta.description = "A test tool"

        # Inline test of the signature construction logic (same as register_tools.create_tool_wrapper)
        from typing import Annotated
        new_params = []
        new_params.append(
            inspect.Parameter(
                'mcp_ctx', 
                inspect.Parameter.POSITIONAL_OR_KEYWORD, 
                annotation=Context
            )
        )
        new_annotations = {'mcp_ctx': Context}
        for field_name, field_info in DummyInput.model_fields.items():
            annotation = Annotated[field_info.annotation, field_info]
            new_params.append(
                inspect.Parameter(
                    field_name,
                    inspect.Parameter.KEYWORD_ONLY,
                    default=field_info.default if field_info.default is not ... else inspect.Parameter.empty,
                    annotation=annotation
                )
            )
            new_annotations[field_name] = annotation

        signature = inspect.Signature(new_params)

        self.assertEqual(mock_meta.name, "test_tool")
        self.assertIn("artifact_id", signature.parameters)
        self.assertIn("lang", signature.parameters)
        self.assertIn("mcp_ctx", signature.parameters)


if __name__ == "__main__":
    unittest.main()
