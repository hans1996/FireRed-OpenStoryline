import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from open_storyline.config import load_settings
from open_storyline.nodes.core_nodes.search_web import SearchWebNode, _resolve_search_web_api_key
from open_storyline.nodes.node_state import NodeState
from open_storyline.nodes.node_summary import NodeSummary


REPO_CONFIG = Path(__file__).resolve().parent.parent / "config.toml"


class SearchWebConfigTests(unittest.TestCase):
    def test_load_settings_reads_adjacent_dotenv_for_exa_key(self):
        config_text = REPO_CONFIG.read_text(encoding="utf-8")

        with TemporaryDirectory() as tmpdir, patch.dict("os.environ", {}, clear=True):
            tmp_path = Path(tmpdir)
            (tmp_path / "config.toml").write_text(config_text, encoding="utf-8")
            (tmp_path / ".env").write_text('EXA_API_KEY="exa-secret"\n', encoding="utf-8")

            cfg = load_settings(tmp_path / "config.toml")
            self.assertEqual(_resolve_search_web_api_key(cfg), "exa-secret")


class SearchWebNodeTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_returns_condensed_results(self):
        cfg = load_settings(REPO_CONFIG)
        node = SearchWebNode(cfg)
        state = NodeState(
            session_id="sess",
            artifact_id="artifact",
            lang="zh",
            node_summary=NodeSummary(auto_console=False),
            llm=Mock(),
            mcp_ctx=Mock(),
        )

        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "results": [
                {
                    "title": "Global economy slows",
                    "url": "https://example.com/economy",
                    "publishedDate": "2026-01-01T00:00:00.000Z",
                    "text": "The global economy slowed amid weak demand.",
                    "highlights": ["Global growth cooled in 2025."],
                    "summary": "Growth softened in 2025.",
                }
            ]
        }

        with patch.dict("os.environ", {"EXA_API_KEY": "exa-secret"}, clear=False):
            with patch("open_storyline.nodes.core_nodes.search_web.requests.post", return_value=fake_response) as mock_post:
                result = await node.process(
                    state,
                    {
                        "query": "global economy past year",
                        "num_results": 3,
                        "category": "news",
                    },
                )

        self.assertEqual(len(result["search_results"]), 1)
        first = result["search_results"][0]
        self.assertEqual(first["title"], "Global economy slows")
        self.assertEqual(first["url"], "https://example.com/economy")
        self.assertEqual(first["snippet"], "Growth softened in 2025.")
        self.assertEqual(first["published_date"], "2026-01-01T00:00:00.000Z")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["query"], "global economy past year")
        self.assertEqual(payload["category"], "news")
        self.assertEqual(payload["numResults"], 3)
        self.assertIn("contents", payload)

    async def test_process_requires_exa_api_key(self):
        cfg = load_settings(REPO_CONFIG)
        node = SearchWebNode(cfg)
        state = NodeState(
            session_id="sess",
            artifact_id="artifact",
            lang="zh",
            node_summary=NodeSummary(auto_console=False),
            llm=Mock(),
            mcp_ctx=Mock(),
        )

        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError) as cm:
                await node.process(
                    state,
                    {
                        "query": "global economy past year",
                        "num_results": 3,
                    },
                )

        self.assertIn("EXA_API_KEY", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
