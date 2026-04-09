import importlib
import os
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT_ROOT, "src")
for path in (SRC, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)


class _BaseMessage:
    def __init__(self, content):
        self.content = content


class _AIMessage(_BaseMessage):
    pass


class _HumanMessage(_BaseMessage):
    pass


class _SystemMessage(_BaseMessage):
    pass


class _ClientContext(SimpleNamespace):
    pass


class _ToolInterceptor:
    inject_media_content_before = object()
    save_media_content_after = object()
    inject_tts_config = object()


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _install_cli_dependencies():
    langchain_core = sys.modules.get("langchain_core") or _install_module("langchain_core")
    langchain_messages = _install_module(
        "langchain_core.messages",
        AIMessage=_AIMessage,
        BaseMessage=_BaseMessage,
        HumanMessage=_HumanMessage,
        SystemMessage=_SystemMessage,
    )
    langchain_core.messages = langchain_messages

    open_storyline = sys.modules.get("open_storyline") or _install_module("open_storyline")
    agent_mod = _install_module("open_storyline.agent", ClientContext=_ClientContext, build_agent=None)
    prompts_mod = _install_module("open_storyline.utils.prompts", get_prompt=lambda *args, **kwargs: "system prompt")
    media_handler_mod = _install_module("open_storyline.utils.media_handler", scan_media_dir=lambda path: {})
    config_mod = _install_module(
        "open_storyline.config",
        load_settings=lambda path: None,
        default_config_path=lambda: Path("config.toml"),
    )
    storage_pkg = _install_module("open_storyline.storage")
    storage_mod = _install_module("open_storyline.storage.agent_memory", ArtifactStore=object)
    mcp_pkg = _install_module("open_storyline.mcp")
    hooks_pkg = _install_module("open_storyline.mcp.hooks")
    interceptors_mod = _install_module("open_storyline.mcp.hooks.node_interceptors", ToolInterceptor=_ToolInterceptor)
    middleware_mod = _install_module("open_storyline.mcp.hooks.chat_middleware", PrintStreamingTokens=lambda: object())

    open_storyline.agent = agent_mod
    open_storyline.config = config_mod
    open_storyline.storage = storage_pkg
    open_storyline.mcp = mcp_pkg
    storage_pkg.agent_memory = storage_mod
    mcp_pkg.hooks = hooks_pkg
    hooks_pkg.node_interceptors = interceptors_mod
    hooks_pkg.chat_middleware = middleware_mod

    utils_pkg = sys.modules.get("open_storyline.utils") or _install_module("open_storyline.utils")
    utils_pkg.prompts = prompts_mod
    utils_pkg.media_handler = media_handler_mod
    open_storyline.utils = utils_pkg


def _load_cli_module():
    _install_cli_dependencies()
    sys.modules.pop("cli", None)
    return importlib.import_module("cli")


class CliMainTests(unittest.IsolatedAsyncioTestCase):
    async def test_exit_command_stops_without_invoking_agent(self):
        cli = _load_cli_module()
        cfg = SimpleNamespace(
            project=SimpleNamespace(
                outputs_dir=Path("/tmp/outputs"),
                media_dir=Path("/tmp/media"),
                bgm_dir=Path("/tmp/bgm"),
            ),
            llm=SimpleNamespace(model="demo-llm"),
        )
        agent = SimpleNamespace(ainvoke=AsyncMock())

        with patch.object(cli, "load_settings", return_value=cfg), patch.object(
            cli, "default_config_path", return_value=Path("config.toml")
        ), patch.object(cli, "ArtifactStore", return_value=object()), patch.object(
            cli, "build_agent", AsyncMock(return_value=(agent, object()))
        ) as build_agent_mock, patch.object(cli, "get_prompt", return_value="system prompt"), patch.object(
            cli, "scan_media_dir", return_value={"image number in user's media library": 0, "video number in user's media library": 0}
        ) as scan_media_dir_mock, patch("builtins.input", side_effect=["/exit"]), patch("builtins.print") as print_mock:
            await cli.main()

        build_agent_mock.assert_awaited_once()
        agent.ainvoke.assert_not_awaited()
        scan_media_dir_mock.assert_not_called()
        printed = "\n".join(" ".join(str(arg) for arg in call.args) for call in print_mock.call_args_list)
        self.assertIn("GoodBye~", printed)

    async def test_prompt_invokes_agent_and_prints_final_response(self):
        cli = _load_cli_module()
        cfg = SimpleNamespace(
            project=SimpleNamespace(
                outputs_dir=Path("/tmp/outputs"),
                media_dir=Path("/tmp/media"),
                bgm_dir=Path("/tmp/bgm"),
            ),
            llm=SimpleNamespace(model="demo-llm"),
        )
        agent = SimpleNamespace(
            ainvoke=AsyncMock(return_value={"messages": [_HumanMessage("make a trailer"), _AIMessage("Finished cut")]}),
        )

        with patch.object(cli, "load_settings", return_value=cfg), patch.object(
            cli, "default_config_path", return_value=Path("config.toml")
        ), patch.object(cli, "ArtifactStore", return_value=object()), patch.object(
            cli, "build_agent", AsyncMock(return_value=(agent, object()))
        ), patch.object(cli, "get_prompt", return_value="system prompt"), patch.object(
            cli,
            "scan_media_dir",
            return_value={"image number in user's media library": 2, "video number in user's media library": 1},
        ) as scan_media_dir_mock, patch("builtins.input", side_effect=["make a trailer", "/exit"]), patch(
            "builtins.print"
        ) as print_mock:
            await cli.main()

        scan_media_dir_mock.assert_called_once_with(cfg.project.media_dir)
        agent.ainvoke.assert_awaited_once()
        payload = agent.ainvoke.await_args.args[0]
        self.assertEqual(payload["messages"][-1].content, "make a trailer")
        self.assertIn('"image number in user\'s media library": 2', payload["messages"][1].content)
        self.assertIn('"video number in user\'s media library": 1', payload["messages"][1].content)
        self.assertEqual(agent.ainvoke.await_args.kwargs["context"].media_dir, cfg.project.media_dir)
        printed = "\n".join(" ".join(str(arg) for arg in call.args) for call in print_mock.call_args_list)
        self.assertIn("Finished cut", printed)


if __name__ == "__main__":
    unittest.main()
