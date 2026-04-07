import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from agent_fastapi import (
    ChatSession,
    SessionStore,
    _list_builtin_model_labels,
    _list_builtin_model_names,
    _resolve_builtin_model_override,
)
from open_storyline.agent import _make_langchain_chat_model, _should_use_google_gemini_client
from open_storyline.config import LLMConfig, ModelOptionConfig, load_settings
from open_storyline.mcp.sampling_handler import _make_model_bind_kwargs
from open_storyline.nodes.node_schema import RenderVideoInput
from open_storyline.nodes.core_nodes.generate_voiceover import GenerateVoiceoverNode


REPO_CONFIG = Path(__file__).resolve().parent.parent / "config.toml"


class BuiltinModelSelectionTests(unittest.TestCase):
    def test_resolves_selected_builtin_alternative(self):
        cfg = LLMConfig(
            model="gemma4:31b-it-q4_K_M",
            base_url="http://127.0.0.1:11435/v1",
            api_key="ollama",
            timeout=30.0,
            alternatives=[
                ModelOptionConfig(
                    model="gemma4:26b-a4b-it-q4_K_M",
                    base_url="http://127.0.0.1:11435/v1",
                    api_key="ollama",
                    timeout=45.0,
                )
            ],
        )

        resolved, err = _resolve_builtin_model_override(
            "llm",
            cfg,
            selected_model="gemma4:26b-a4b-it-q4_K_M",
        )

        self.assertIsNone(err)
        self.assertEqual(resolved["model"], "gemma4:26b-a4b-it-q4_K_M")
        self.assertEqual(resolved["base_url"], "http://127.0.0.1:11435/v1")
        self.assertEqual(resolved["timeout"], 45.0)

    def test_lists_builtin_models_including_alternatives(self):
        cfg = LLMConfig(
            model="gemma4:31b-it-q4_K_M",
            base_url="http://127.0.0.1:11435/v1",
            api_key="ollama",
            alternatives=[
                ModelOptionConfig(
                    model="gemma4:26b-a4b-it-q4_K_M",
                    base_url="http://127.0.0.1:11435/v1",
                    api_key="ollama",
                )
            ],
        )

        self.assertEqual(
            _list_builtin_model_names("llm", cfg),
            ["gemma4:31b-it-q4_K_M", "gemma4:26b-a4b-it-q4_K_M"],
        )

    @patch.dict("os.environ", {"GEMINI_API_KEY": "gemini-secret"}, clear=False)
    def test_resolves_selected_builtin_alternative_with_entry_level_env_api_key(self):
        cfg = LLMConfig(
            model="gemma4:31b-it-q4_K_M",
            base_url="http://127.0.0.1:11435/v1",
            api_key="ollama",
            alternatives=[
                ModelOptionConfig(
                    model="gemini-3-flash-preview",
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                    api_key="",
                    api_key_env="GEMINI_API_KEY",
                    timeout=40.0,
                )
            ],
        )

        resolved, err = _resolve_builtin_model_override(
            "llm",
            cfg,
            selected_model="gemini-3-flash-preview",
        )

        self.assertIsNone(err)
        self.assertEqual(resolved["model"], "gemini-3-flash-preview")
        self.assertEqual(
            resolved["base_url"],
            "https://generativelanguage.googleapis.com/v1beta/openai",
        )
        self.assertEqual(resolved["api_key"], "gemini-secret")
        self.assertEqual(resolved["timeout"], 40.0)

    @patch.dict("os.environ", {}, clear=True)
    def test_selected_builtin_alternative_reports_entry_level_env_when_missing(self):
        cfg = LLMConfig(
            model="gemma4:31b-it-q4_K_M",
            base_url="http://127.0.0.1:11435/v1",
            api_key="ollama",
            alternatives=[
                ModelOptionConfig(
                    model="gemini-3.1-flash-lite-preview",
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                    api_key="",
                    api_key_env="GEMINI_API_KEY",
                )
            ],
        )

        resolved, err = _resolve_builtin_model_override(
            "llm",
            cfg,
            selected_model="gemini-3.1-flash-lite-preview",
        )

        self.assertIsNone(resolved)
        self.assertIn("GEMINI_API_KEY", err)
        self.assertNotIn("OPENSTORYLINE_LLM_API_KEY", err)


class BuiltinModelLabelTests(unittest.TestCase):
    def test_lists_builtin_model_labels_with_explicit_provider_labels(self):
        cfg = LLMConfig(
            model="gemma4:31b-it-q4_K_M",
            base_url="http://127.0.0.1:11435/v1",
            api_key="ollama",
            label="Gemma 4 31B (Ollama)",
            alternatives=[
                ModelOptionConfig(
                    model="gemma-4-31b-it",
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                    api_key="",
                    api_key_env="GEMINI_API_KEY",
                    label="Gemma 4 31B (Google API)",
                )
            ],
        )

        self.assertEqual(
            _list_builtin_model_labels("llm", cfg),
            {
                "gemma4:31b-it-q4_K_M": "Gemma 4 31B (Ollama)",
                "gemma-4-31b-it": "Gemma 4 31B (Google API)",
            },
        )

    def test_infers_provider_suffix_when_label_missing(self):
        cfg = LLMConfig(
            model="gemma4:26b-a4b-it-q4_K_M",
            base_url="http://127.0.0.1:11435/v1",
            api_key="ollama",
            alternatives=[
                ModelOptionConfig(
                    model="gemini-3.1-flash-lite-preview",
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                    api_key="",
                    api_key_env="GEMINI_API_KEY",
                )
            ],
        )

        labels = _list_builtin_model_labels("llm", cfg)

        self.assertEqual(labels["gemma4:26b-a4b-it-q4_K_M"], "gemma4:26b-a4b-it-q4_K_M (Ollama)")
        self.assertEqual(
            labels["gemini-3.1-flash-lite-preview"],
            "gemini-3.1-flash-lite-preview (Google API)",
        )


class SessionStoreConfigRefreshTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_refreshes_latest_config_for_new_session(self):
        initial_cfg = load_settings(REPO_CONFIG)
        refreshed_cfg = initial_cfg.model_copy(
            update={
                "llm": initial_cfg.llm.model_copy(
                    update={
                        "alternatives": list(initial_cfg.llm.alternatives)
                        + [
                            ModelOptionConfig(
                                model="gemini-3.1-flash-lite-preview",
                                base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                                api_key="",
                                api_key_env="GEMINI_API_KEY",
                            )
                        ],
                    }
                )
            }
        )

        store = SessionStore(
            initial_cfg,
            config_path=str(REPO_CONFIG),
            config_loader=lambda _path: refreshed_cfg,
        )

        sess = await store.create()

        self.assertIn("gemini-3.1-flash-lite-preview", sess.chat_models)


class SessionSnapshotModelLabelTests(unittest.TestCase):
    def test_snapshot_exposes_builtin_model_labels(self):
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("session-test", cfg)

        snapshot = sess.snapshot()

        self.assertIn("llm_model_labels", snapshot)
        self.assertIn("vlm_model_labels", snapshot)
        self.assertEqual(
            snapshot["llm_model_labels"].get("gemma4:31b-it-q4_K_M"),
            "Gemma 4 31B (Ollama)",
        )



class DotenvConfigLoadingTests(unittest.TestCase):
    def test_load_settings_reads_adjacent_dotenv_for_model_env_key(self):
        config_text = REPO_CONFIG.read_text(encoding="utf-8")

        with TemporaryDirectory() as tmpdir, patch.dict("os.environ", {}, clear=True):
            tmp_path = Path(tmpdir)
            (tmp_path / "config.toml").write_text(config_text, encoding="utf-8")
            (tmp_path / ".env").write_text('GEMINI_API_KEY="dotenv-secret"\n', encoding="utf-8")

            cfg = load_settings(tmp_path / "config.toml")
            resolved, err = _resolve_builtin_model_override(
                "llm",
                cfg.llm,
                selected_model="gemini-3.1-flash-lite-preview",
            )

        self.assertIsNone(err)
        self.assertEqual(resolved["api_key"], "dotenv-secret")


class GeminiModelFactoryTests(unittest.TestCase):
    def test_detects_google_gemini_openai_compat_endpoint(self):
        self.assertTrue(
            _should_use_google_gemini_client(
                model="gemini-3.1-flash-lite-preview",
                base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            )
        )
        self.assertTrue(
            _should_use_google_gemini_client(
                model="gemma-4-31b-it",
                base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            )
        )
        self.assertFalse(
            _should_use_google_gemini_client(
                model="gemma4:26b-a4b-it-q4_K_M",
                base_url="http://127.0.0.1:11435/v1",
            )
        )

    def test_uses_google_client_for_gemini_models(self):
        captured = {}

        class FakeGoogleChat:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        with patch("open_storyline.agent._load_google_chat_model_class", return_value=FakeGoogleChat):
            model = _make_langchain_chat_model(
                model="gemini-3.1-flash-lite-preview",
                base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                api_key="gemini-secret",
                timeout=30.0,
                temperature=0.2,
                streaming=True,
                max_retries=2,
            )

        self.assertIsInstance(model, FakeGoogleChat)
        self.assertEqual(captured["model"], "gemini-3.1-flash-lite-preview")
        self.assertEqual(captured["google_api_key"], "gemini-secret")
        self.assertEqual(captured["temperature"], 0.2)
        self.assertEqual(captured["timeout"], 30.0)
        self.assertEqual(captured["max_retries"], 2)

    def test_uses_chatopenai_for_non_gemini_models(self):
        captured = {}

        class FakeChatOpenAI:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        with patch("open_storyline.agent.ChatOpenAI", FakeChatOpenAI):
            model = _make_langchain_chat_model(
                model="gemma4:26b-a4b-it-q4_K_M",
                base_url="http://127.0.0.1:11435/v1",
                api_key="ollama",
                timeout=45.0,
                temperature=0.1,
                streaming=False,
                max_retries=1,
            )

        self.assertIsInstance(model, FakeChatOpenAI)
        self.assertEqual(captured["model"], "gemma4:26b-a4b-it-q4_K_M")
        self.assertEqual(captured["base_url"], "http://127.0.0.1:11435/v1")
        self.assertEqual(captured["api_key"], "ollama")
        self.assertEqual(captured["timeout"], 45.0)


class GeminiToolSchemaCompatibilityTests(unittest.TestCase):
    def test_render_video_color_arrays_use_items_schema(self):
        schema = RenderVideoInput.model_json_schema()

        for field_name in ("bg_color", "font_color", "stroke_color"):
            field_schema = schema["properties"][field_name]
            schema_json = str(field_schema)
            self.assertIn("items", schema_json, field_name)
            self.assertNotIn("prefixItems", schema_json, field_name)


class GeminiSamplingBindingTests(unittest.TestCase):
    def test_google_genai_models_use_max_output_tokens(self):
        class FakeGoogleModel:
            __module__ = "langchain_google_genai.chat_models"

        kwargs = _make_model_bind_kwargs(FakeGoogleModel(), temperature=0.1, max_tokens=123, top_p=0.8)

        self.assertEqual(kwargs["temperature"], 0.1)
        self.assertEqual(kwargs["top_p"], 0.8)
        self.assertEqual(kwargs["max_output_tokens"], 123)
        self.assertNotIn("max_tokens", kwargs)

    def test_openai_compatible_models_keep_max_tokens(self):
        class FakeOpenAIModel:
            __module__ = "langchain_openai.chat_models.base"

        kwargs = _make_model_bind_kwargs(FakeOpenAIModel(), temperature=0.2, max_tokens=456, top_p=0.7)

        self.assertEqual(kwargs["temperature"], 0.2)
        self.assertEqual(kwargs["top_p"], 0.7)
        self.assertEqual(kwargs["max_tokens"], 456)
        self.assertNotIn("max_output_tokens", kwargs)


class FishServerSessionTests(unittest.TestCase):
    def test_lazy_start_wraps_and_stops_spawned_server(self):
        node = GenerateVoiceoverNode(load_settings(REPO_CONFIG))
        events = []

        node._is_fish_service_reachable = lambda base_url: False
        node._start_fish_server = lambda runtime: events.append("start") or object()
        node._wait_for_fish_server = (
            lambda base_url, startup_timeout, proc: events.append("wait")
        )
        node._stop_fish_server = lambda proc: events.append("stop")

        secrets = {
            "base_url": "http://127.0.0.1:8080",
            "_auto_start": "true",
            "_stop_after_request": "true",
            "_launch_command": "python tools/api_server.py --listen 127.0.0.1:8080",
        }

        with node._fish_server_session("fish", secrets, {}):
            events.append("inside")

        self.assertEqual(events, ["start", "wait", "inside", "stop"])

    def test_ollama_models_are_unloaded_then_reloaded_around_fish(self):
        node = GenerateVoiceoverNode(load_settings(REPO_CONFIG))
        events = []

        node._load_session_model_runtime = lambda session_id: [
            {
                "model": "gemma4:26b-a4b-it-q4_K_M",
                "base_url": "http://127.0.0.1:11435/v1",
            }
        ]
        node._is_ollama_host = lambda api_root: True
        node._list_loaded_ollama_models = lambda api_root: [
            "gemma4:31b-it-q4_K_M",
            "gemma4:26b-a4b-it-q4_K_M",
        ]
        node._unload_ollama_model = lambda api_root, model: events.append(("unload", api_root, model))
        node._wait_for_ollama_models_unloaded = lambda api_root, models, timeout=30.0: events.append(("wait", api_root, tuple(models)))
        node._preload_ollama_model = lambda api_root, model, keep_alive: events.append(("reload", api_root, model, keep_alive))

        with node._ollama_gpu_memory_session("session-123", {"_ollama_keep_alive": "20m"}):
            events.append(("inside",))

        self.assertEqual(
            events,
            [
                ("unload", "http://127.0.0.1:11435", "gemma4:31b-it-q4_K_M"),
                ("unload", "http://127.0.0.1:11435", "gemma4:26b-a4b-it-q4_K_M"),
                ("wait", "http://127.0.0.1:11435", ("gemma4:31b-it-q4_K_M", "gemma4:26b-a4b-it-q4_K_M")),
                ("inside",),
                ("reload", "http://127.0.0.1:11435", "gemma4:26b-a4b-it-q4_K_M", "20m"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
