"""
Tests for ChatSession lifecycle in agent_fastapi.py.

Covers:
- Session creation and config loading
- Session refresh when config.toml changes (model availability)
- Session snapshot serialization/deserialization
- Session cleanup (session deletion and resource cleanup)
- Media operations lifecycle (add, take, delete)
"""
import asyncio
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch, MagicMock
from importlib import reload

# Import from the module under test
from agent_fastapi import ChatSession, SessionStore, MediaMeta
from open_storyline.config import load_settings, ModelOptionConfig

REPO_CONFIG = Path(__file__).resolve().parent.parent / "config.toml"


class ChatSessionCreationTests(unittest.TestCase):
    """Tests for ChatSession creation and config loading."""

    def test_session_creation_with_valid_config(self):
        """A session can be created with valid Settings."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("test-session-001", cfg)

        self.assertEqual(sess.session_id, "test-session-001")
        self.assertEqual(sess.lang, "zh")
        self.assertIsNotNone(sess.cfg)
        self.assertIn("test-session-001", sess.media_dir)
        self.assertIsNone(sess.agent)
        self.assertIsNone(sess.node_manager)
        self.assertIsNone(sess.client_context)
        self.assertEqual(sess.history, [])
        self.assertEqual(sess.load_media, {})
        self.assertEqual(sess.pending_media_ids, [])
        self.assertFalse(sess._media_seq_inited)
        self.assertEqual(sess._media_seq_next, 1)

    def test_session_has_async_locks(self):
        """Session provides separate chat_lock and media_lock."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("test-locks", cfg)

        self.assertIsInstance(sess.chat_lock, asyncio.Lock)
        self.assertIsInstance(sess.media_lock, asyncio.Lock)

    def test_session_initial_lc_messages_contains_system_prompt(self):
        """Chat message history starts with system prompts."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("test-system-prompt", cfg)

        self.assertGreaterEqual(len(sess.lc_messages), 1)
        # At least one SystemMessage should be present
        system_count = sum(
            1
            for msg in sess.lc_messages
            if hasattr(msg, "content") and "System" in type(msg).__name__
        )
        self.assertGreaterEqual(system_count, 1)

    def test_custom_model_key_is_available(self):
        """Session exposes the __custom__ model option."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("test-custom", cfg)

        self.assertIn("__custom__", sess.chat_models)
        self.assertIn("__custom__", sess.vlm_models)
        # Default model key should NOT be __custom__
        self.assertNotEqual(sess.chat_model_key, "__custom__")
        self.assertNotEqual(sess.vlm_model_key, "__custom__")

    def test_multiple_sessions_are_independent(self):
        """Two sessions with different IDs do not share mutable state."""
        cfg = load_settings(REPO_CONFIG)
        sess1 = ChatSession("session-alpha", cfg)
        sess2 = ChatSession("session-beta", cfg)

        self.assertEqual(sess1.session_id, "session-alpha")
        self.assertEqual(sess2.session_id, "session-beta")
        self.assertNotEqual(sess1.media_dir, sess2.media_dir)


class SessionStoreLifecycleTests(unittest.IsolatedAsyncioTestCase):
    """Tests for SessionStore lifecycle operations."""

    async def test_store_create_registers_session(self):
        """Creating a session via SessionStore registers it internally."""
        cfg = load_settings(REPO_CONFIG)
        store = SessionStore(cfg)
        sess = await store.create()

        self.assertIsInstance(sess, ChatSession)
        retrieved = await store.get(sess.session_id)
        self.assertIs(retrieved, sess)

    async def test_store_get_nonexistent_returns_none(self):
        """Getting a non-existent session returns None."""
        cfg = load_settings(REPO_CONFIG)
        store = SessionStore(cfg)

        result = await store.get("nonexistent-session-id")
        self.assertIsNone(result)

    async def test_store_get_or_404_raises_on_missing(self):
        """get_or_404 raises HTTPException for missing sessions."""
        from fastapi import HTTPException

        cfg = load_settings(REPO_CONFIG)
        store = SessionStore(cfg)

        with self.assertRaises(HTTPException) as ctx:
            await store.get_or_404("does-not-exist")
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_store_get_or_404_returns_existing(self):
        """get_or_404 returns the session when it exists."""
        cfg = load_settings(REPO_CONFIG)
        store = SessionStore(cfg)
        sess = await store.create()

        result = await store.get_or_404(sess.session_id)
        self.assertIs(result, sess)

    async def test_store_creates_unique_sessions(self):
        """Each call to create() returns a session with a unique ID."""
        cfg = load_settings(REPO_CONFIG)
        store = SessionStore(cfg)

        s1 = await store.create()
        s2 = await store.create()
        s3 = await store.create()

        ids = {s.session_id for s in (s1, s2, s3)}
        self.assertEqual(len(ids), 3)

    async def test_store_reloads_config_on_create(self):
        """store.create() reloads config so new sessions see latest settings."""
        initial_cfg = load_settings(REPO_CONFIG)
        refreshed_cfg = initial_cfg.model_copy(
            update={
                "llm": initial_cfg.llm.model_copy(
                    update={
                        "alternatives": list(initial_cfg.llm.alternatives)
                        + [
                            ModelOptionConfig(
                                model="gemini-refreshed-model",
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
        # Session should see the refreshed config with the new model
        self.assertIn("gemini-refreshed-model", sess.chat_models)
        # The store's cfg should have been updated
        found = any(
            m.model == "gemini-refreshed-model"
            for m in store.cfg.llm.alternatives
        )
        self.assertTrue(found)


class SessionSnapshotTests(unittest.TestCase):
    """Tests for ChatSession.snapshot() serialization."""

    def test_snapshot_returns_dict_with_required_keys(self):
        """snapshot() returns a dict with all required lifecycle fields."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("snap-test", cfg)

        snap = sess.snapshot()

        self.assertIsInstance(snap, dict)
        required_keys = {
            "session_id",
            "developer_mode",
            "pending_media",
            "history",
            "turn_running",
            "limits",
            "stats",
            "chat_model_key",
            "chat_models",
            "llm_model_key",
            "llm_models",
            "vlm_model_key",
            "vlm_models",
            "lang",
        }
        self.assertTrue(required_keys.issubset(snap.keys()))

    def test_snapshot_matches_session_state(self):
        """snapshot() values match the session's actual state."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("snap-match", cfg)

        snap = sess.snapshot()

        self.assertEqual(snap["session_id"], "snap-match")
        self.assertEqual(snap["lang"], "zh")
        self.assertEqual(snap["history"], [])
        self.assertEqual(snap["pending_media"], [])
        self.assertEqual(snap["stats"]["media_count"], 0)
        self.assertEqual(snap["stats"]["pending_count"], 0)
        self.assertFalse(snap["turn_running"])

    def test_snapshot_is_json_serializable(self):
        """snapshot() output can be serialized to JSON."""
        import json

        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("snap-json", cfg)

        snap = sess.snapshot()
        # Should not raise
        json_str = json.dumps(snap, ensure_ascii=False)
        self.assertIsInstance(json_str, str)
        self.assertGreater(len(json_str), 0)

    def test_snapshot_exposes_model_labels(self):
        """snapshot() includes model label information."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("snap-labels", cfg)

        snap = sess.snapshot()

        self.assertIn("llm_model_labels", snap)
        self.assertIn("vlm_model_labels", snap)

    def test_snapshot_limits_struct(self):
        """snapshot() includes limit configuration."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("snap-limits", cfg)

        snap = sess.snapshot()
        limits = snap["limits"]

        self.assertIn("max_upload_files_per_request", limits)
        self.assertIn("max_media_per_session", limits)
        self.assertIn("max_pending_media_per_session", limits)
        self.assertIn("upload_chunk_bytes", limits)


class SessionConfigChangeRefreshTests(unittest.IsolatedAsyncioTestCase):
    """Tests for session behavior when config changes."""

    async def test_session_uses_latest_config_after_store_refresh(self):
        """When config is refreshed, newly created sessions use the updated config."""
        initial_cfg = load_settings(REPO_CONFIG)
        # Create a new LLM config with a different default model
        updated_llm = initial_cfg.llm.model_copy(
            update={
                "model": "gemini-refreshed-llm",
                "base_url": "https://new.api/v1",
            }
        )
        refreshed_cfg = initial_cfg.model_copy(update={"llm": updated_llm})

        store = SessionStore(
            initial_cfg,
            config_path=str(REPO_CONFIG),
            config_loader=lambda _path: refreshed_cfg,
        )

        sess = await store.create()
        # The session's cfg should now be the refreshed one
        self.assertEqual(sess.cfg.llm.model, "gemini-refreshed-llm")


class SessionMediaLifecycleTests(unittest.IsolatedAsyncioTestCase):
    """Tests for media operations within a session lifecycle."""

    async def test_take_pending_media_returns_and_clears_pending(self):
        """take_pending_media_for_message returns pending media and clears the list."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("media-lifecycle", cfg)

        # Manually inject some pending media
        meta = MediaMeta(id="media-001", name="test.jpg", kind="image", path="/tmp/test.jpg", thumb_path=None, ts=0.0)
        sess.load_media["media-001"] = meta
        sess.pending_media_ids.append("media-001")

        # Take all pending media
        taken = await sess.take_pending_media_for_message(None)

        self.assertEqual(len(taken), 1)
        self.assertEqual(taken[0].id, "media-001")
        self.assertEqual(sess.pending_media_ids, [])

    async def test_delete_pending_media_removes_from_lists(self):
        """Deleting pending media removes it from pending and load_media."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("media-del", cfg)
        # Manually inject some pending media
        meta = MediaMeta(id="media-del-001", name="del.jpg", kind="image", path="/tmp/del.jpg", thumb_path=None, ts=0.0)
        sess.load_media["media-del-001"] = meta
        sess.pending_media_ids.append("media-del-001")

        # Mock delete_files to avoid actual file operations
        sess.media_store.delete_files = AsyncMock()

        await sess.delete_pending_media("media-del-001")

        self.assertNotIn("media-del-001", sess.pending_media_ids)
        self.assertNotIn("media-del-001", sess.load_media)
        sess.media_store.delete_files.assert_called_once()

    async def test_delete_non_pending_media_raises(self):
        """Deleting media that is not pending raises HTTPException."""
        from fastapi import HTTPException

        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("media-del-bad", cfg)

        with self.assertRaises(HTTPException) as ctx:
            await sess.delete_pending_media("non-existent-id")
        self.assertEqual(ctx.exception.status_code, 400)


class SessionToolTraceLifecycleTests(unittest.TestCase):
    """Tests for tool event trace lifecycle in a session."""

    def test_apply_tool_event_tool_start_creates_record(self):
        """tool_start creates a new history record."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("tool-trace", cfg)

        event = {
            "type": "tool_start",
            "tool_call_id": "tc-001",
            "server": "test-server",
            "name": "test_tool",
            "args": {"param": "value"},
        }
        rec = sess.apply_tool_event(event)

        self.assertIsNotNone(rec)
        self.assertEqual(rec["state"], "running")
        self.assertEqual(rec["progress"], 0.0)
        self.assertEqual(rec["server"], "test-server")
        self.assertEqual(rec["name"], "test_tool")

    def test_apply_tool_event_progress_updates_record(self):
        """tool_progress updates the existing record with progress."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("tool-progress", cfg)

        # First: start
        sess.apply_tool_event({
            "type": "tool_start",
            "tool_call_id": "tc-002",
            "server": "s",
            "name": "n",
            "args": {},
        })

        # Then: progress
        rec = sess.apply_tool_event({
            "type": "tool_progress",
            "tool_call_id": "tc-002",
            "progress": 0.5,
            "message": "Halfway done",
        })

        self.assertEqual(rec["state"], "running")
        self.assertEqual(rec["progress"], 0.5)
        self.assertEqual(rec["message"], "Halfway done")

    def test_apply_tool_event_tool_end_completes_record(self):
        """tool_end marks the record as complete."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("tool-end", cfg)

        sess.apply_tool_event({
            "type": "tool_start",
            "tool_call_id": "tc-003",
            "server": "s",
            "name": "n",
            "args": {},
        })
        rec = sess.apply_tool_event({
            "type": "tool_end",
            "tool_call_id": "tc-003",
            "is_error": False,
            "message": "Done",
        })

        self.assertEqual(rec["state"], "complete")
        self.assertEqual(rec["progress"], 1.0)

    def test_apply_tool_event_error_marks_as_error(self):
        """tool_end with is_error marks state as error."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("tool-error", cfg)

        sess.apply_tool_event({
            "type": "tool_start",
            "tool_call_id": "tc-004",
            "server": "s",
            "name": "n",
            "args": {},
        })
        rec = sess.apply_tool_event({
            "type": "tool_end",
            "tool_call_id": "tc-004",
            "is_error": True,
            "message": "Something broke",
        })

        self.assertEqual(rec["state"], "error")

    def test_apply_tool_event_invalid_returns_none(self):
        """apply_tool_event returns None for unrecognized event types."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("tool-invalid-event", cfg)

        result = sess.apply_tool_event({"type": "unknown"})
        self.assertIsNone(result)

    def test_tool_events_appended_to_history(self):
        """Tool events accumulate in session history."""
        cfg = load_settings(REPO_CONFIG)
        sess = ChatSession("tool-history-accumulate", cfg)

        self.assertEqual(sess.history, [])

        sess.apply_tool_event({
            "type": "tool_start",
            "tool_call_id": "tc-005",
            "server": "s",
            "name": "tool_a",
            "args": {},
        })
        sess.apply_tool_event({
            "type": "tool_start",
            "tool_call_id": "tc-006",
            "server": "s",
            "name": "tool_b",
            "args": {},
        })

        self.assertEqual(len(sess.history), 2)


if __name__ == "__main__":
    unittest.main()
