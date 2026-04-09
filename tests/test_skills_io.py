import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


if "aiofiles" not in sys.modules:
    _install_module("aiofiles", open=None)

if "skillkit" not in sys.modules:
    skillkit = _install_module("skillkit", SkillManager=object)
    skillkit_integrations = _install_module("skillkit.integrations")
    skillkit_langchain = _install_module(
        "skillkit.integrations.langchain",
        create_langchain_tools=lambda manager: [],
    )
    skillkit.integrations = skillkit_integrations
    skillkit_integrations.langchain = skillkit_langchain

if "langchain" not in sys.modules:
    langchain = _install_module("langchain")
    langchain_agents = _install_module("langchain.agents", create_agent=lambda *args, **kwargs: None)
    langchain_messages = _install_module("langchain.messages", HumanMessage=object)
    langchain.agents = langchain_agents
    langchain.messages = langchain_messages

if "langchain_openai" not in sys.modules:
    _install_module("langchain_openai", ChatOpenAI=object)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT_ROOT, "src")
for path in (SRC, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from open_storyline.skills.skills_io import dump_skills, load_skills


class _AsyncTextWriter:
    def __init__(self, path, mode="w", encoding="utf-8"):
        self._path = path
        self._mode = mode
        self._encoding = encoding
        self._handle = None

    async def __aenter__(self):
        self._handle = open(self._path, self._mode, encoding=self._encoding)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._handle.close()
        return False

    async def write(self, content):
        self._handle.write(content)


class LoadSkillsTests(unittest.IsolatedAsyncioTestCase):
    async def test_load_skills_discovers_manager_and_wraps_tools(self):
        manager = MagicMock()
        manager.adiscover = AsyncMock()

        with patch("open_storyline.skills.skills_io.SkillManager", return_value=manager) as manager_cls, patch(
            "open_storyline.skills.skills_io.create_langchain_tools",
            return_value=["tool-a", "tool-b"],
        ) as create_tools:
            tools = await load_skills("custom-skills")

        manager_cls.assert_called_once_with(skill_dir="custom-skills")
        manager.adiscover.assert_awaited_once()
        create_tools.assert_called_once_with(manager)
        self.assertEqual(tools, ["tool-a", "tool-b"])


class DumpSkillsTests(unittest.IsolatedAsyncioTestCase):
    async def test_dump_skills_writes_skill_file_inside_project(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch("open_storyline.skills.skills_io.aiofiles.open", side_effect=_AsyncTextWriter):
            cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = await dump_skills(
                    skill_name="storybeat",
                    skill_dir=".storyline/skills",
                    skill_content="# Skill\ncontent\n",
                )
            finally:
                os.chdir(cwd)

            target = Path(tmpdir) / ".storyline/skills/cutskill_storybeat/SKILL.md"
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["file_path"], str(target))
            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "# Skill\ncontent\n")

    async def test_dump_skills_rejects_empty_names(self):
        result = await dump_skills(skill_name="   ", skill_dir=".storyline/skills", skill_content="ignored")

        self.assertEqual(result["status"], "error")
        self.assertIn("skill_name cannot be empty", result["message"])

    async def test_dump_skills_blocks_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch("open_storyline.skills.skills_io.aiofiles.open", side_effect=_AsyncTextWriter):
            cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = await dump_skills(
                    skill_name="escape",
                    skill_dir="../../outside",
                    skill_content="secret",
                )
            finally:
                os.chdir(cwd)

        self.assertEqual(result["status"], "error")
        self.assertIn("Security Alert", result["message"])


if __name__ == "__main__":
    unittest.main()
