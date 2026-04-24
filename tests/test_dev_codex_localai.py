import argparse
import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "dev_codex_localai.py"
SPEC = importlib.util.spec_from_file_location("dev_codex_localai", SCRIPT_PATH)
assert SPEC and SPEC.loader
dev_runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev_runtime)


def test_runtime_health_failures_reports_missing_services() -> None:
    snapshot = {
        "firered_web": {"ready": True, "status": "running"},
        "local_mcp": {"ready": False, "status": "missing", "detail": "not reachable"},
        "localai_gateway": {"ready": True, "status": "running"},
        "localai_tts_ready": {"ready": False, "status": "auth_error", "detail": "unauthorized"},
        "localai_music_ready": {"ready": True, "status": "ready"},
        "comfyui_bridge": {"ready": True, "status": "running"},
        "codex_auth_state": {"signed_in": False, "status": "signed_out", "detail": "login required"},
        "warnings": [],
    }

    failures = dev_runtime._runtime_health_failures(snapshot)

    assert "Local MCP: not reachable" in failures
    assert "LocalAI TTS: unauthorized" in failures
    assert "Codex auth: login required" in failures


def test_runtime_health_brief_only_exposes_brief_status() -> None:
    snapshot = {
        "firered_web": {"ready": True, "status": "running", "detail": "ignore"},
        "local_mcp": {"ready": True, "status": "running", "detail": "ignore"},
        "localai_gateway": {"ready": True, "status": "running", "detail": "ignore"},
        "localai_tts_ready": {"ready": True, "status": "ready", "detail": "ignore"},
        "localai_music_ready": {"ready": True, "status": "ready", "detail": "ignore"},
        "comfyui_bridge": {"ready": True, "status": "running", "detail": "ignore"},
        "codex_auth_state": {"signed_in": True, "status": "signed_in", "detail": "ignore"},
        "warnings": ["warn-a"],
    }

    brief = dev_runtime._runtime_health_brief(snapshot)

    assert brief["warnings"] == ["warn-a"]
    assert brief["codex_auth_state"] == {"signed_in": True, "status": "signed_in"}
    assert brief["localai_tts_ready"] == {"ready": True, "status": "ready"}
    assert "detail" not in brief["localai_tts_ready"]


def test_cmd_up_returns_failure_when_health_not_ready(monkeypatch, capsys) -> None:
    monkeypatch.setattr(dev_runtime, "_start_mcp", lambda port: {"name": "local_mcp", "port": port})
    monkeypatch.setattr(dev_runtime, "_start_web", lambda port: {"name": "firered_web", "port": port})
    monkeypatch.setattr(dev_runtime, "_start_bridge", lambda port, host, target: {"name": "comfyui_bridge", "port": port})
    monkeypatch.setattr(
        dev_runtime,
        "_wait_for_runtime_health",
        lambda **kwargs: {
            "firered_web": {"ready": True, "status": "running"},
            "local_mcp": {"ready": False, "status": "missing", "detail": "not reachable"},
            "localai_gateway": {"ready": True, "status": "running"},
            "localai_tts_ready": {"ready": True, "status": "ready"},
            "localai_music_ready": {"ready": True, "status": "ready"},
            "comfyui_bridge": {"ready": True, "status": "running"},
            "codex_auth_state": {"signed_in": True, "status": "signed_in"},
            "warnings": [],
        },
    )
    monkeypatch.setattr(dev_runtime.asyncio, "run", lambda coro: coro)

    args = argparse.Namespace(
        web_port=7861,
        mcp_port=8001,
        bridge_port=8188,
        bridge_target_host="172.17.0.1",
        bridge_target_port=8188,
        timeout=60.0,
        smoke=False,
        model="gpt-5.4",
        reasoning="medium",
    )

    rc = dev_runtime.cmd_up(args)
    output = capsys.readouterr().out

    assert rc == 1
    assert "\"ok\": false" in output
    assert "Local MCP: not reachable" in output


def test_cmd_verify_returns_success_with_smoke(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        dev_runtime,
        "_fetch_runtime_health",
        lambda web_port, mcp_port: {
            "firered_web": {"ready": True, "status": "running"},
            "local_mcp": {"ready": True, "status": "running"},
            "localai_gateway": {"ready": True, "status": "running"},
            "localai_tts_ready": {"ready": True, "status": "ready"},
            "localai_music_ready": {"ready": True, "status": "ready"},
            "comfyui_bridge": {"ready": True, "status": "running"},
            "codex_auth_state": {"signed_in": True, "status": "signed_in"},
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        dev_runtime,
        "_smoke_flow",
        lambda args: {"session_id": "sess-123", "steps": {"render_video": {"preview": "/tmp/demo.mp4"}}},
    )
    monkeypatch.setattr(dev_runtime.asyncio, "run", lambda coro: coro)

    args = argparse.Namespace(
        web_port=7861,
        mcp_port=8001,
        model="gpt-5.4",
        reasoning="medium",
    )

    rc = dev_runtime.cmd_verify(args)
    output = capsys.readouterr().out

    assert rc == 0
    assert "\"ok\": true" in output
    assert "\"session_id\": \"sess-123\"" in output
