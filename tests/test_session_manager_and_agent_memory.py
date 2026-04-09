import os
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch


def _install_stub(name):
    if name in sys.modules:
        return sys.modules[name]
    module = MagicMock()
    sys.modules[name] = module
    return module


_install_stub("colorlog")
_install_stub("colorlog.handlers")
_install_stub("proglog")
_install_stub("proglog.ProgressBarLogger")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT_ROOT, "src")
for path in (SRC, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from open_storyline.storage.agent_memory import ArtifactStore
from open_storyline.storage.session_manager import SessionLifecycleManager
from src.open_storyline.storage.agent_memory import ArtifactStore as SessionManagerArtifactStore


class ArtifactStoreTests(unittest.TestCase):
    def test_initializes_meta_file_with_empty_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArtifactStore(tmpdir, "session-1")

            self.assertTrue(store.meta_path.exists())
            self.assertEqual(store._load_meta_list(), [])

    def test_save_load_and_get_latest_meta(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "open_storyline.storage.agent_memory.logger"
        ):
            store = ArtifactStore(tmpdir, "session-1")

            with patch("open_storyline.storage.agent_memory.time.time", side_effect=[100.0, 200.0]):
                first_meta = store.save_result(
                    "session-1",
                    "node-a",
                    {
                        "artifact_id": "artifact-1",
                        "summary": "first summary",
                        "tool_excute_result": {"value": 1},
                    },
                )
                second_meta = store.save_result(
                    "session-1",
                    "node-a",
                    {
                        "artifact_id": "artifact-2",
                        "summary": "second summary",
                        "tool_excute_result": {"value": 2},
                    },
                )

            loaded_meta, loaded_data = store.load_result("artifact-1")
            latest_meta = store.get_latest_meta(node_id="node-a", session_id="session-1")

            self.assertEqual(first_meta.artifact_id, "artifact-1")
            self.assertEqual(second_meta.artifact_id, "artifact-2")
            self.assertEqual(loaded_meta.artifact_id, "artifact-1")
            self.assertEqual(loaded_data["payload"], {"value": 1})
            self.assertEqual(latest_meta.artifact_id, "artifact-2")
            self.assertEqual(latest_meta.summary, "second summary")

    def test_load_result_returns_message_for_missing_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArtifactStore(tmpdir, "session-1")

            meta, message = store.load_result("missing")

            self.assertIsNone(meta)
            self.assertIn("artifact `missing` not found", message)


class SessionLifecycleManagerTests(unittest.TestCase):
    def test_is_valid_session_id_accepts_uuid4_hex_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionLifecycleManager(tmpdir, tmpdir)
            valid_uuid = uuid.uuid4().hex
            invalid_uuid = uuid.uuid1().hex

            self.assertTrue(manager._is_valid_session_id(valid_uuid))
            self.assertFalse(manager._is_valid_session_id(invalid_uuid))
            self.assertFalse(manager._is_valid_session_id("not-a-uuid"))

    def test_cleanup_removes_expired_session_dirs_but_keeps_current_and_invalid_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "open_storyline.storage.session_manager.logger"
        ):
            artifacts_root = Path(tmpdir) / "artifacts"
            cache_root = Path(tmpdir) / "cache"
            manager = SessionLifecycleManager(
                artifacts_root,
                cache_root,
                retention_days=1,
                enable_cleanup=True,
            )

            expired_session = uuid.uuid4().hex
            current_session = uuid.uuid4().hex
            invalid_entry = "not-a-session"
            old_mtime = time.time() - (3 * 86400)

            for root in (artifacts_root, cache_root):
                expired_dir = root / expired_session
                expired_dir.mkdir(parents=True)
                os.utime(expired_dir, (old_mtime, old_mtime))

                current_dir = root / current_session
                current_dir.mkdir(parents=True)

                invalid_dir = root / invalid_entry
                invalid_dir.mkdir(parents=True)
                os.utime(invalid_dir, (old_mtime, old_mtime))

            manager.cleanup_expired_sessions(current_session)

            for root in (artifacts_root, cache_root):
                self.assertFalse((root / expired_session).exists())
                self.assertTrue((root / current_session).exists())
                self.assertTrue((root / invalid_entry).exists())

    def test_get_artifact_store_starts_background_cleanup_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "open_storyline.storage.session_manager.threading.Thread"
        ) as thread_cls:
            thread_mock = MagicMock()
            thread_cls.return_value = thread_mock
            manager = SessionLifecycleManager(
                Path(tmpdir) / "artifacts",
                Path(tmpdir) / "cache",
                enable_cleanup=True,
            )

            store = manager.get_artifact_store("session-xyz")

            self.assertIsInstance(store, SessionManagerArtifactStore)
            thread_cls.assert_called_once()
            self.assertEqual(thread_cls.call_args.kwargs["args"], ("session-xyz",))
            self.assertTrue(thread_cls.call_args.kwargs["daemon"])
            thread_mock.start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
