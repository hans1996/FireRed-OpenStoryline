import base64
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


pil_module = types.ModuleType("PIL")


class _Resampling:
    LANCZOS = "lanczos"


class FakeImage:
    Resampling = _Resampling

    def __init__(self, mode, size, color=None):
        self.mode = mode
        self.size = size
        self.color = color

    def resize(self, new_size, _resample):
        return FakeImage(self.mode, new_size, self.color)

    def convert(self, new_mode):
        return FakeImage(new_mode, self.size, self.color)

    def save(self, buffered, format=None, quality=None):
        payload = f"{format}|{self.mode}|{self.size[0]}x{self.size[1]}|{quality}".encode("utf-8")
        buffered.write(payload)


image_module = types.SimpleNamespace(Image=FakeImage, Resampling=_Resampling, new=FakeImage)
pil_module.Image = image_module
pil_module.ImageOps = types.SimpleNamespace()
sys.modules["PIL"] = pil_module

moviepy_module = types.ModuleType("moviepy")


class VideoFileClip:  # pragma: no cover - import stub only
    pass


moviepy_module.VideoFileClip = VideoFileClip
sys.modules["moviepy"] = moviepy_module

register_module = types.ModuleType("open_storyline.utils.register")


class _Registry:
    def register(self):
        def decorator(obj):
            return obj

        return decorator


register_module.NODE_REGISTRY = _Registry()
sys.modules["open_storyline.utils.register"] = register_module

prompts_module = types.ModuleType("open_storyline.utils.prompts")
prompts_module.get_prompt = lambda *args, **kwargs: "prompt"
sys.modules["open_storyline.utils.prompts"] = prompts_module

cancel_module = types.ModuleType("open_storyline.utils.ai_transition_cancel")
cancel_module.is_ai_transition_cancelled = lambda *args, **kwargs: False
sys.modules["open_storyline.utils.ai_transition_cancel"] = cancel_module

client_module = types.ModuleType("open_storyline.utils.ai_transition_client")
client_module.VisionClientFactory = object
sys.modules["open_storyline.utils.ai_transition_client"] = client_module

node_state_module = types.ModuleType("open_storyline.nodes.node_state")
node_state_module.NodeState = object
sys.modules["open_storyline.nodes.node_state"] = node_state_module

base_node_module = types.ModuleType("open_storyline.nodes.core_nodes.base_node")


class BaseNode:  # pragma: no cover - import stub only
    pass


class NodeMeta:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


base_node_module.BaseNode = BaseNode
base_node_module.NodeMeta = NodeMeta
sys.modules["open_storyline.nodes.core_nodes.base_node"] = base_node_module

node_schema_module = types.ModuleType("open_storyline.nodes.node_schema")
node_schema_module.GenerateAITransitionInput = object
sys.modules["open_storyline.nodes.node_schema"] = node_schema_module


from open_storyline.nodes.core_nodes.generate_ai_transition import (  # noqa: E402
    GenerateAITransitionNode,
    encode_image_to_data_url,
)


class EncodeImageToDataUrlTests(unittest.TestCase):
    def test_jpeg_encoding_converts_rgba_and_downsamples(self):
        image = FakeImage("RGBA", (200, 100), (255, 0, 0, 128))

        data_url = encode_image_to_data_url(
            image,
            format="JPEG",
            quality=80,
            max_long_edge=50,
        )

        self.assertTrue(data_url.startswith("data:image/jpeg;base64,"))
        encoded = data_url.split(",", 1)[1]
        decoded = base64.b64decode(encoded).decode("utf-8")
        self.assertEqual(decoded, "JPEG|RGB|50x25|80")


class GenerateAITransitionHelperTests(unittest.TestCase):
    def _make_node(self, providers):
        node = GenerateAITransitionNode()
        node.server_cfg = SimpleNamespace(
            generate_ai_transition=SimpleNamespace(providers=providers)
        )
        return node

    def test_runtime_cfg_prefers_complete_frontend_values(self):
        node = self._make_node(
            {
                "minimax": {
                    "model_name": "config-model",
                    "api_key": "placeholder",
                }
            }
        )

        result = node._resolve_ai_transition_runtime_cfg(
            {
                "provider": "  MiniMax ",
                "model_name": "frontend-model",
                "api_key": "frontend-placeholder",
            }
        )

        self.assertEqual(
            result,
            {
                "provider": "minimax",
                "model_name": "frontend-model",
                "api_key": "frontend-placeholder",
            },
        )

    def test_runtime_cfg_falls_back_to_config_when_frontend_is_incomplete(self):
        node = self._make_node(
            {
                "minimax": {
                    "model_name": "config-model",
                    "api_key": "placeholder",
                }
            }
        )

        result = node._resolve_ai_transition_runtime_cfg(
            {
                "provider": "minimax",
                "model_name": "frontend-model",
            }
        )

        self.assertEqual(
            result,
            {
                "provider": "minimax",
                "model_name": "config-model",
                "api_key": "placeholder",
            },
        )

    def test_runtime_cfg_raises_for_missing_config_fields(self):
        node = self._make_node(
            {
                "minimax": {
                    "model_name": "config-model",
                    "api_key": "",
                }
            }
        )

        with self.assertRaises(ValueError) as ctx:
            node._resolve_ai_transition_runtime_cfg({"provider": "minimax"})

        self.assertIn("provider=minimax", str(ctx.exception))
        self.assertIn("api_key", str(ctx.exception))

    def test_aspect_ratio_and_duration_helpers_cover_edge_cases(self):
        node = self._make_node(
            {
                "minimax": {
                    "model_name": "config-model",
                    "api_key": "placeholder",
                }
            }
        )

        self.assertTrue(node._is_aspect_ratio_compatible((1920, 1080), (1280, 720)))
        self.assertFalse(node._is_aspect_ratio_compatible((1920, 1080), (1000, 1000)))
        self.assertEqual(node._parse_duration_seconds(2), 2.0)
        self.assertEqual(node._parse_duration_seconds("3.5s"), 3.5)
        self.assertEqual(node._parse_duration_seconds("bad-value"), 0.0)
        self.assertEqual(
            node._transition_payload_duration_seconds({"source_ref": {"duration_ms": 2500}}),
            2.5,
        )
        self.assertEqual(
            node._transition_payload_duration_seconds({"source_ref": {"duration_ms": "oops"}}),
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
