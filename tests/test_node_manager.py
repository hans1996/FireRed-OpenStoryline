import os
import sys
import unittest
from unittest.mock import MagicMock, patch

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

# langchain_core
_lc = _install_stub("langchain_core")
_lc.tools = _install_stub("langchain_core.tools")
_lc.tools.structured = _install_stub("langchain_core.tools.structured")
_lc.tools.structured.StructuredTool = _lc.tools.structured  # alias for isinstance checks


# ─────────────────────────────────────────────────────────────────
# Imports  – must come AFTER the stubs
# ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT_ROOT, "src")
for p in (SRC, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from open_storyline.nodes.node_manager import NodeManager  # noqa: E402


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────
def _make_tool(metadata_dict=None):
    """Create a mock StructuredTool-like object with .metadata."""
    tool = MagicMock()
    tool.metadata = metadata_dict
    return tool


# ─────────────────────────────────────────────────────────────────
# 1. INIT / _BUILD
# ─────────────────────────────────────────────────────────────────
class TestInitAndBuild(unittest.TestCase):
    def test_init_empty(self):
        nm = NodeManager()
        self.assertEqual(dict(nm.kind_to_node_ids), {})
        self.assertEqual(nm.id_to_tool, {})
        self.assertEqual(nm.id_to_next, {})
        self.assertEqual(nm.id_to_priority, {})
        self.assertEqual(nm.id_to_kind, {})

    def test_init_with_tools(self):
        tool = _make_tool({
            "_meta": {
                "node_id": "n1",
                "node_kind": "k1",
                "priority": 7,
            }
        })
        nm = NodeManager(tools=[tool])
        self.assertIn("n1", nm.id_to_tool)
        self.assertEqual(nm.id_to_kind["n1"], "k1")
        self.assertEqual(nm.id_to_priority["n1"], 7)

    def test_build_empty_list(self):
        nm = NodeManager()
        nm._build([])
        self.assertEqual(nm.id_to_tool, {})

    def test_build_valid_tools(self):
        nm = NodeManager()
        nm._build([
            _make_tool({"_meta": {"node_id": "t1", "node_kind": "k"}}),
            _make_tool({"_meta": {"node_id": "t2", "node_kind": "k2", "priority": 3}}),
        ])
        self.assertIn("t1", nm.id_to_tool)
        self.assertIn("t2", nm.id_to_tool)

    def test_build_skips_missing_metadata(self):
        nm = NodeManager()
        nm._build([_make_tool(None), _make_tool({"_meta": {"node_id": "good"}})])
        self.assertEqual(len(nm.id_to_tool), 1)

    def test_build_skips_missing_node_id(self):
        nm = NodeManager()
        nm._build([_make_tool({"_meta": {"node_kind": "no_id"}})])
        self.assertEqual(nm.id_to_tool, {})

    def test_build_tool_without_metadata_attr(self):
        nm = NodeManager()
        bare = MagicMock()  # spec=None allows arbitrary attribute access
        nm._build([bare])  # should not crash


# ─────────────────────────────────────────────────────────────────
# 2. ADD_NODE
# ─────────────────────────────────────────────────────────────────
class TestAddNode(unittest.TestCase):
    def test_add_success(self):
        nm = NodeManager()
        tool = _make_tool({
            "_meta": {
                "node_id": "x",
                "node_kind": "k",
                "priority": 10,
                "next_available_node": ["y"],
                "require_prior_kind": ["p1"],
                "default_require_prior_kind": ["p2"],
            }
        })
        self.assertTrue(nm.add_node(tool))
        self.assertIn("x", nm.id_to_tool)
        self.assertEqual(nm.id_to_kind["x"], "k")
        self.assertEqual(nm.id_to_priority["x"], 10)
        self.assertEqual(nm.id_to_next["x"], ["y"])
        self.assertEqual(nm.id_to_require_prior_kind["x"], ["p1"])
        self.assertEqual(nm.id_to_default_require_prior_kind["x"], ["p2"])

    def test_add_defaults(self):
        nm = NodeManager()
        self.assertTrue(nm.add_node(_make_tool({"_meta": {"node_id": "min"}})))
        self.assertEqual(nm.id_to_kind["min"], "min")   # defaults to node_id
        self.assertEqual(nm.id_to_priority["min"], 0)
        self.assertEqual(nm.id_to_next["min"], [])

    def test_add_duplicate_replaces(self):
        nm = NodeManager()
        t1 = _make_tool({"_meta": {"node_id": "d", "priority": 1}})
        t2 = _make_tool({"_meta": {"node_id": "d", "priority": 99, "node_kind": "nk"}})
        nm.add_node(t1)
        nm.add_node(t2)
        self.assertIs(nm.id_to_tool["d"], t2)
        self.assertEqual(nm.id_to_priority["d"], 99)
        self.assertEqual(nm.kind_to_node_ids["nk"].count("d"), 1)

    def test_add_multiple_same_kind(self):
        nm = NodeManager()
        nm.add_node(_make_tool({"_meta": {"node_id": "a", "node_kind": "s"}}))
        nm.add_node(_make_tool({"_meta": {"node_id": "b", "node_kind": "s"}}))
        self.assertEqual(set(nm.kind_to_node_ids["s"]), {"a", "b"})

    def test_add_reverse_index(self):
        nm = NodeManager()
        nm.add_node(_make_tool({
            "_meta": {
                "node_id": "r1",
                "require_prior_kind": ["fx", "fy"],
                "default_require_prior_kind": ["fz"],
            }
        }))
        self.assertIn("r1", nm.kind_to_dependent_nodes["fx"])
        self.assertIn("r1", nm.kind_to_dependent_nodes["fy"])
        self.assertIn("r1", nm.kind_to_default_dependent_nodes["fz"])

    def test_add_none_metadata_returns_false(self):
        nm = NodeManager()
        self.assertFalse(nm.add_node(_make_tool(None)))

    def test_add_empty_metadata_returns_false(self):
        nm = NodeManager()
        self.assertFalse(nm.add_node(_make_tool({})))

    def test_add_empty_meta_dict_returns_false(self):
        nm = NodeManager()
        self.assertFalse(nm.add_node(_make_tool({"_meta": {}})))

    def test_add_empty_node_id_returns_false(self):
        nm = NodeManager()
        self.assertFalse(nm.add_node(_make_tool({"_meta": {"node_id": ""}})))

    def test_add_node_none_raises(self):
        nm = NodeManager()
        with self.assertRaises(AttributeError):
            nm.add_node(None)


# ─────────────────────────────────────────────────────────────────
# 3. REMOVE_NODE
# ─────────────────────────────────────────────────────────────────
class TestRemoveNode(unittest.TestCase):
    def test_remove_success(self):
        nm = NodeManager()
        nm.add_node(_make_tool({
            "_meta": {
                "node_id": "rm",
                "node_kind": "k",
                "require_prior_kind": ["pr"],
                "default_require_prior_kind": ["dp"],
            }
        }))
        self.assertTrue(nm.remove_node("rm"))
        self.assertNotIn("rm", nm.id_to_tool)
        self.assertNotIn("rm", nm.id_to_kind)
        self.assertNotIn("rm", nm.id_to_priority)
        self.assertNotIn("rm", nm.id_to_next)
        self.assertNotIn("rm", nm.kind_to_node_ids.get("k", []))
        self.assertNotIn("rm", nm.kind_to_dependent_nodes.get("pr", set()))
        self.assertNotIn("rm", nm.kind_to_default_dependent_nodes.get("dp", set()))

    def test_remove_nonexistent(self):
        nm = NodeManager()
        self.assertFalse(nm.remove_node("ghost"))

    def test_remove_cleans_references(self):
        nm = NodeManager()
        nm.add_node(_make_tool({"_meta": {"node_id": "a", "next_available_node": ["b"]}}))
        nm.add_node(_make_tool({"_meta": {"node_id": "b"}}))
        nm.remove_node("b", clean_references=True)
        self.assertEqual(nm.id_to_next.get("a"), [])

    def test_remove_keeps_references(self):
        nm = NodeManager()
        nm.add_node(_make_tool({"_meta": {"node_id": "a", "next_available_node": ["b"]}}))
        nm.add_node(_make_tool({"_meta": {"node_id": "b"}}))
        nm.remove_node("b", clean_references=False)
        self.assertIn("b", nm.id_to_next["a"])

    def test_remove_clears_empty_kind(self):
        nm = NodeManager()
        nm.add_node(_make_tool({"_meta": {"node_id": "only", "node_kind": "lonely"}}))
        nm.remove_node("only")
        self.assertNotIn("lonely", nm.kind_to_node_ids)

    def test_remove_twice_returns_false(self):
        nm = NodeManager()
        nm.add_node(_make_tool({"_meta": {"node_id": "once"}}))
        self.assertTrue(nm.remove_node("once"))
        self.assertFalse(nm.remove_node("once"))

    def test_reverse_index_partial_cleanup(self):
        nm = NodeManager()
        nm.add_node(_make_tool({
            "_meta": {"node_id": "d1", "require_prior_kind": ["sf"], "default_require_prior_kind": ["sd"]}
        }))
        nm.add_node(_make_tool({
            "_meta": {"node_id": "d2", "require_prior_kind": ["sf"], "default_require_prior_kind": ["sd"]}
        }))
        nm.remove_node("d1")
        self.assertNotIn("d1", nm.kind_to_dependent_nodes["sf"])
        self.assertIn("d2", nm.kind_to_dependent_nodes["sf"])
        self.assertNotIn("d1", nm.kind_to_default_dependent_nodes["sd"])
        self.assertIn("d2", nm.kind_to_default_dependent_nodes["sd"])


# ─────────────────────────────────────────────────────────────────
# 4. _SORT_KIND
# ─────────────────────────────────────────────────────────────────
class TestSortKind(unittest.TestCase):
    def test_sort_descending(self):
        nm = NodeManager()
        for nid, pri in [("lo", 1), ("hi", 10), ("mid", 5)]:
            nm.add_node(_make_tool({"_meta": {"node_id": nid, "node_kind": "s", "priority": pri}}))
        nm._sort_kind("s")
        self.assertEqual(nm.kind_to_node_ids["s"], ["hi", "mid", "lo"])

    def test_sort_nonexistent_kind(self):
        nm = NodeManager()
        nm._sort_kind("no_such_kind")  # should not raise

    def test_sort_single(self):
        nm = NodeManager()
        nm.add_node(_make_tool({"_meta": {"node_id": "solo", "node_kind": "k", "priority": 0}}))
        nm._sort_kind("k")
        self.assertEqual(nm.kind_to_node_ids["k"], ["solo"])

    def test_priority_sorted_on_add(self):
        nm = NodeManager()
        nm.add_node(_make_tool({"_meta": {"node_id": "low", "node_kind": "auto", "priority": 5}}))
        nm.add_node(_make_tool({"_meta": {"node_id": "high", "node_kind": "auto", "priority": 10}}))
        self.assertEqual(nm.kind_to_node_ids["auto"], ["high", "low"])


# ─────────────────────────────────────────────────────────────────
# 5. GET_TOOL / VALIDATION
# ─────────────────────────────────────────────────────────────────
class TestGetToolAndValidation(unittest.TestCase):
    def test_get_existing(self):
        nm = NodeManager()
        t = _make_tool({"_meta": {"node_id": "find_me"}})
        nm.add_node(t)
        self.assertIs(nm.get_tool("find_me"), t)

    def test_get_nonexistent(self):
        nm = NodeManager()
        self.assertIsNone(nm.get_tool("ghost"))

    def test_id_to_kind_mapping(self):
        nm = NodeManager()
        nm.add_node(_make_tool({"_meta": {"node_id": "x", "node_kind": "special"}}))
        self.assertEqual(nm.id_to_kind["x"], "special")

    def test_kind_to_node_ids_is_list(self):
        nm = NodeManager()
        nm.add_node(_make_tool({"_meta": {"node_id": "x", "node_kind": "k"}}))
        self.assertIsInstance(nm.kind_to_node_ids["k"], list)

    def test_defaultdict_creates_empty_list(self):
        nm = NodeManager()
        _ = nm.kind_to_node_ids["nothing"]
        self.assertEqual(nm.kind_to_node_ids["nothing"], [])


# ─────────────────────────────────────────────────────────────────
# 6. CHECK_EXCUTABLE (dependency resolution)
# ─────────────────────────────────────────────────────────────────
class TestCheckExcutable(unittest.TestCase):
    def _meta(self, node_id, session_id, created_at):
        m = MagicMock()
        m.node_id = node_id
        m.session_id = session_id
        m.created_at = created_at
        return m

    def test_all_satisfied(self):
        nm = NodeManager()
        for nid, kid in [("n1", "k1"), ("n2", "k2")]:
            nm.add_node(_make_tool({"_meta": {"node_id": nid, "node_kind": kid}}))

        store = MagicMock()
        store.get_latest_meta.return_value = self._meta("n1", "s1", 1000.0)

        r = nm.check_excutable("s1", store, ["k1", "k2"])
        self.assertTrue(r["excutable"])
        self.assertEqual(r["missing_kind"], [])
        self.assertIn("k1", r["collected_node"])
        self.assertIn("k2", r["collected_node"])

    def test_missing_kind(self):
        nm = NodeManager()
        nm.add_node(_make_tool({"_meta": {"node_id": "n1", "node_kind": "k1"}}))
        nm.add_node(_make_tool({"_meta": {"node_id": "n2", "node_kind": "mk"}}))

        def _get(node_id, session_id):
            return self._meta("n1", "s1", 1000.0) if node_id == "n1" else None

        store = MagicMock()
        store.get_latest_meta.side_effect = _get

        r = nm.check_excutable("s1", store, ["k1", "mk"])
        self.assertFalse(r["excutable"])
        self.assertEqual(r["missing_kind"], ["mk"])

    def test_selects_latest_output(self):
        nm = NodeManager()
        nm.add_node(_make_tool({"_meta": {"node_id": "old", "node_kind": "k", "priority": 1}}))
        nm.add_node(_make_tool({"_meta": {"node_id": "new", "node_kind": "k", "priority": 2}}))

        def _get(node_id, session_id):
            return self._meta(node_id, "s1", 100.0 if node_id == "old" else 200.0)

        store = MagicMock()
        store.get_latest_meta.side_effect = _get

        r = nm.check_excutable("s1", store, ["k"])
        self.assertTrue(r["excutable"])
        self.assertEqual(r["collected_node"]["k"].node_id, "new")
        self.assertEqual(r["collected_node"]["k"].created_at, 200.0)

    def test_empty_require_kind(self):
        nm = NodeManager()
        r = nm.check_excutable("s1", MagicMock(), [])
        self.assertTrue(r["excutable"])
        self.assertEqual(r["missing_kind"], [])
        self.assertEqual(r["collected_node"], {})

    def test_unknown_kind(self):
        nm = NodeManager()
        nm.add_node(_make_tool({"_meta": {"node_id": "n1", "node_kind": "known"}}))
        r = nm.check_excutable("s1", MagicMock(), ["unknown_kind"])
        self.assertFalse(r["excutable"])
        self.assertEqual(r["missing_kind"], ["unknown_kind"])

    def test_partial_prerequisites(self):
        nm = NodeManager()
        for nid, kid in [("sg", "script"), ("vg", "voice"), ("sb", "visual")]:
            nm.add_node(_make_tool({"_meta": {"node_id": nid, "node_kind": kid}}))

        def _get(node_id, session_id):
            outs = {"sg": self._meta("sg", "s1", 100.0), "sb": self._meta("sb", "s1", 200.0)}
            return outs.get(node_id)

        store = MagicMock()
        store.get_latest_meta.side_effect = _get

        r = nm.check_excutable("s1", store, ["script", "voice", "visual"])
        self.assertFalse(r["excutable"])
        self.assertEqual(r["missing_kind"], ["voice"])
        self.assertIn("script", r["collected_node"])
        self.assertIn("visual", r["collected_node"])
        self.assertNotIn("voice", r["collected_node"])


# ─────────────────────────────────────────────────────────────────
# 7. EDGE-CASE / INTEGRATION
# ─────────────────────────────────────────────────────────────────
class TestIntegration(unittest.TestCase):
    def test_complex_pipeline(self):
        tools = [
            _make_tool({"_meta": {
                "node_id": "script_gen", "node_kind": "script", "priority": 10,
                "next_available_node": ["voice_gen", "storyboard"],
            }}),
            _make_tool({"_meta": {
                "node_id": "voice_gen", "node_kind": "voice", "priority": 5,
                "require_prior_kind": ["script"],
                "next_available_node": ["render"],
            }}),
            _make_tool({"_meta": {
                "node_id": "storyboard", "node_kind": "visual", "priority": 3,
                "require_prior_kind": ["script"],
                "next_available_node": ["render"],
            }}),
            _make_tool({"_meta": {
                "node_id": "render", "node_kind": "render", "priority": 1,
                "require_prior_kind": ["voice", "visual"],
            }}),
        ]
        nm = NodeManager(tools=tools)

        self.assertEqual(len(nm.id_to_tool), 4)
        self.assertEqual(nm.id_to_priority["script_gen"], 10)
        self.assertEqual(nm.id_to_next["script_gen"], ["voice_gen", "storyboard"])
        self.assertIn("voice_gen", nm.kind_to_dependent_nodes["script"])
        self.assertIn("storyboard", nm.kind_to_dependent_nodes["script"])
        self.assertIn("render", nm.kind_to_dependent_nodes["voice"])
        self.assertIn("render", nm.kind_to_dependent_nodes["visual"])

    def test_remove_and_rebuild(self):
        nm = NodeManager()
        t1 = _make_tool({"_meta": {"node_id": "a", "node_kind": "k"}})
        t2 = _make_tool({"_meta": {"node_id": "b", "node_kind": "k"}})
        nm.add_node(t1)
        nm.add_node(t2)
        self.assertEqual(len(nm.kind_to_node_ids["k"]), 2)
        nm.remove_node("a")
        self.assertEqual(nm.kind_to_node_ids["k"], ["b"])
        nm.add_node(t1)
        self.assertEqual(set(nm.kind_to_node_ids["k"]), {"a", "b"})


if __name__ == "__main__":
    unittest.main()
