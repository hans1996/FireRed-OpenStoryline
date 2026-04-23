#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import websockets

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
STATE_DIR = ROOT / ".storyline" / "dev_runtime"
LOG_DIR = STATE_DIR / "logs"
PID_DIR = STATE_DIR / "pids"
DEFAULT_WEB_PORT = 7861
DEFAULT_MCP_PORT = 8001
DEFAULT_BRIDGE_PORT = 8188
DEFAULT_BRIDGE_TARGET_HOST = "172.17.0.1"
DEFAULT_BRIDGE_TARGET_PORT = 8188

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from open_storyline.config import default_config_path, load_settings
from open_storyline.runtime_health import build_runtime_health_snapshot, probe_tcp_listener
from open_storyline.utils.localai_auth import inject_localai_runtime_env


def _ensure_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)


def _pid_path(name: str) -> Path:
    return PID_DIR / f"{name}.pid"


def _log_path(name: str) -> Path:
    return LOG_DIR / f"{name}.log"


def _read_pid(name: str) -> int | None:
    path = _pid_path(name)
    if not path.exists():
        return None
    try:
        return int(path.read_text().strip())
    except Exception:
        return None


def _is_pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    return True


def _write_pid(name: str, pid: int) -> None:
    _pid_path(name).write_text(f"{int(pid)}\n")


def _remove_pid(name: str) -> None:
    try:
        _pid_path(name).unlink()
    except FileNotFoundError:
        pass


def _runtime_env() -> dict[str, str]:
    env = inject_localai_runtime_env(dict(os.environ))
    current = env.get("PYTHONPATH", "").strip()
    parts = [str(SRC), str(ROOT)]
    if current:
        parts.append(current)
    env["PYTHONPATH"] = ":".join(parts)
    return env


def _spawn_service(name: str, cmd: list[str], *, cwd: Path = ROOT) -> subprocess.Popen[Any]:
    _ensure_dirs()
    log_file = _log_path(name).open("ab")
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=_runtime_env(),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    _write_pid(name, proc.pid)
    return proc


def _wait_for_port(host: str, port: int, *, timeout: float = 20.0) -> bool:
    deadline = time.time() + float(timeout)
    while time.time() < deadline:
        if probe_tcp_listener(host, port, 0.25):
            return True
        time.sleep(0.3)
    return False


def _service_status(name: str, *, host: str, port: int) -> dict[str, Any]:
    pid = _read_pid(name)
    return {
        "name": name,
        "pid": pid,
        "pid_alive": _is_pid_alive(pid),
        "host": host,
        "port": int(port),
        "listening": probe_tcp_listener(host, port, 0.25),
        "log_path": str(_log_path(name)),
    }


def _start_web(port: int) -> dict[str, Any]:
    if probe_tcp_listener("127.0.0.1", port, 0.25):
        return _service_status("firered_web", host="127.0.0.1", port=port)
    _spawn_service(
        "firered_web",
        [
            sys.executable,
            "-m",
            "uvicorn",
            "agent_fastapi:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
    )
    _wait_for_port("127.0.0.1", port)
    return _service_status("firered_web", host="127.0.0.1", port=port)


def _start_mcp(port: int) -> dict[str, Any]:
    if probe_tcp_listener("127.0.0.1", port, 0.25):
        return _service_status("local_mcp", host="127.0.0.1", port=port)
    _spawn_service(
        "local_mcp",
        [sys.executable, "-m", "open_storyline.mcp.server"],
    )
    _wait_for_port("127.0.0.1", port)
    return _service_status("local_mcp", host="127.0.0.1", port=port)


def _start_bridge(listen_port: int, target_host: str, target_port: int) -> dict[str, Any]:
    if probe_tcp_listener("127.0.0.1", listen_port, 0.25):
        return _service_status("comfyui_bridge", host="127.0.0.1", port=listen_port)
    _spawn_service(
        "comfyui_bridge",
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "bridge",
            "--listen-host",
            "127.0.0.1",
            "--listen-port",
            str(listen_port),
            "--target-host",
            str(target_host),
            "--target-port",
            str(target_port),
        ],
    )
    _wait_for_port("127.0.0.1", listen_port)
    return _service_status("comfyui_bridge", host="127.0.0.1", port=listen_port)


def cmd_start(args: argparse.Namespace) -> int:
    services = {
        "local_mcp": _start_mcp(int(args.mcp_port)),
        "firered_web": _start_web(int(args.web_port)),
        "comfyui_bridge": _start_bridge(int(args.bridge_port), str(args.bridge_target_host), int(args.bridge_target_port)),
    }
    print(json.dumps(services, ensure_ascii=False, indent=2))
    return 0


async def _fallback_runtime_health(web_port: int, mcp_port: int) -> dict[str, Any]:
    cfg = load_settings(default_config_path())
    fake_manager = SimpleNamespace(
        snapshot=lambda: {
            "status": "running" if probe_tcp_listener("127.0.0.1", mcp_port, 0.25) else "missing",
            "host": "127.0.0.1",
            "port": int(mcp_port),
            "transport": "streamable-http",
            "should_manage": True,
            "last_error": "",
            "recent_logs": [],
        }
    )
    return await build_runtime_health_snapshot(
        cfg=cfg,
        firered_port=int(web_port),
        local_mcp_manager=fake_manager,
    )


def cmd_status(args: argparse.Namespace) -> int:
    base_url = f"http://127.0.0.1:{int(args.web_port)}"
    if probe_tcp_listener("127.0.0.1", int(args.web_port), 0.25):
        try:
            response = httpx.get(f"{base_url}/api/meta/runtime_health", timeout=5.0)
            response.raise_for_status()
            print(json.dumps(response.json(), ensure_ascii=False, indent=2))
            return 0
        except Exception:
            pass
    snapshot = asyncio.run(_fallback_runtime_health(int(args.web_port), int(args.mcp_port)))
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    return 0


def _stop_service(name: str) -> dict[str, Any]:
    pid = _read_pid(name)
    stopped = False
    if _is_pid_alive(pid):
        try:
            os.killpg(os.getpgid(int(pid)), signal.SIGTERM)
        except Exception:
            try:
                os.kill(int(pid), signal.SIGTERM)
            except Exception:
                pass
        stopped = True
        time.sleep(0.4)
    _remove_pid(name)
    return {"name": name, "pid": pid, "stopped": stopped}


def cmd_stop(_: argparse.Namespace) -> int:
    results = [
        _stop_service("firered_web"),
        _stop_service("local_mcp"),
        _stop_service("comfyui_bridge"),
    ]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while not reader.at_eof():
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def _bridge_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    *,
    target_host: str,
    target_port: int,
) -> None:
    upstream_reader, upstream_writer = await asyncio.open_connection(target_host, target_port)
    tasks = [
        asyncio.create_task(_pipe(client_reader, upstream_writer)),
        asyncio.create_task(_pipe(upstream_reader, client_writer)),
    ]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    for task in done:
        with contextlib.suppress(Exception):
            await task


def cmd_bridge(args: argparse.Namespace) -> int:
    async def _main() -> None:
        server = await asyncio.start_server(
            lambda r, w: _bridge_client(
                r,
                w,
                target_host=str(args.target_host),
                target_port=int(args.target_port),
            ),
            str(args.listen_host),
            int(args.listen_port),
        )
        async with server:
            await server.serve_forever()

    asyncio.run(_main())
    return 0


class SmokeFailure(RuntimeError):
    def __init__(self, step: str, message: str):
        super().__init__(f"[{step}] {message}")
        self.step = step
        self.message = message


def _tool_record(snapshot: dict[str, Any], tool_name: str) -> dict[str, Any] | None:
    history = snapshot.get("history") or []
    for record in reversed(history):
        if record.get("role") == "tool" and record.get("name") == tool_name:
            return record
    return None


def _latest_assistant_text(snapshot: dict[str, Any]) -> str:
    history = snapshot.get("history") or []
    for record in reversed(history):
        if record.get("role") == "assistant":
            return str(record.get("content") or "").strip()
    return ""


def _assistant_requests_confirmation(snapshot: dict[str, Any]) -> bool:
    text = _latest_assistant_text(snapshot)
    if not text:
        return False
    phrases = (
        "回复一句“继续”",
        "回复一句\"继续\"",
        "回复“继续”",
        "回复\"继续\"",
        "你回复一句",
        "等待用户确认",
        "确认后",
        "继续后",
    )
    return any(phrase in text for phrase in phrases)


async def _wait_for_tool_record(
    client: httpx.AsyncClient,
    *,
    session_id: str,
    tool_name: str,
    timeout: float = 90.0,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    deadline = time.time() + float(timeout)
    snapshot: dict[str, Any] = {}
    while time.time() < deadline:
        snapshot = (await client.get(f"/api/sessions/{session_id}")).json()
        record = _tool_record(snapshot, tool_name)
        if record and record.get("state") == "complete":
            return snapshot, record
        if _assistant_requests_confirmation(snapshot):
            return snapshot, None
        await asyncio.sleep(1.0)
    return snapshot, None


async def _ensure_tool_completed(
    client: httpx.AsyncClient,
    ws,
    *,
    session_id: str,
    tool_name: str,
    model: str,
    reasoning: str,
    confirmation_text: str = "继续，按刚才确认的流程直接执行，不要再等待确认。",
    timeout: float = 90.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot, record = await _wait_for_tool_record(
        client,
        session_id=session_id,
        tool_name=tool_name,
        timeout=timeout,
    )
    if record:
        return snapshot, record

    if _assistant_requests_confirmation(snapshot):
        await _send_turn(
            ws,
            text=confirmation_text,
            attachment_ids=[],
            model=model,
            reasoning=reasoning,
        )
        snapshot, record = await _wait_for_tool_record(
            client,
            session_id=session_id,
            tool_name=tool_name,
            timeout=timeout,
        )
        if record:
            return snapshot, record

    raise SmokeFailure(tool_name, "tool record missing or incomplete")


async def _wait_for_turn(ws, *, timeout: float = 240.0) -> list[dict[str, Any]]:
    deadline = time.time() + float(timeout)
    events: list[dict[str, Any]] = []
    while time.time() < deadline:
        raw = await asyncio.wait_for(ws.recv(), timeout=max(1.0, deadline - time.time()))
        event = json.loads(raw)
        events.append(event)
        kind = str(event.get("type") or "")
        if kind == "error":
            data = event.get("data") or {}
            raise SmokeFailure("turn", str(data.get("message") or "unknown websocket error"))
        if kind == "assistant.end":
            return events
    raise SmokeFailure("turn", "timed out waiting for assistant.end")


async def _send_turn(
    ws,
    *,
    text: str,
    attachment_ids: list[str],
    model: str,
    reasoning: str,
) -> list[dict[str, Any]]:
    payload = {
        "type": "chat.send",
        "data": {
            "text": text,
            "lang": "zh",
            "attachment_ids": list(attachment_ids),
            "llm_model": "__provider__:codex",
            "vlm_model": "__provider__:codex",
            "service_config": {
                "custom_models": {
                    "llm": {
                        "provider": "codex",
                        "model": model,
                        "reasoning_effort": reasoning,
                    },
                    "vlm": {
                        "provider": "codex",
                        "model": model,
                        "reasoning_effort": reasoning,
                    },
                },
                "tts": {"provider": "localai", "localai": {}},
                "bgm": {"provider": "localai", "localai": {}},
            },
        },
    }
    await ws.send(json.dumps(payload, ensure_ascii=False))
    return await _wait_for_turn(ws)


def _assert_file(path_text: str, *, step: str) -> str:
    path = Path(str(path_text or "")).expanduser()
    if not path.exists():
        raise SmokeFailure(step, f"expected artifact missing: {path}")
    return str(path)


async def _smoke_flow(args: argparse.Namespace) -> dict[str, Any]:
    base_url = f"http://127.0.0.1:{int(args.web_port)}"
    ws_url = f"ws://127.0.0.1:{int(args.web_port)}/ws/sessions/{{session_id}}/chat"
    async with httpx.AsyncClient(base_url=base_url, timeout=20.0) as client:
        health = (await client.get("/api/meta/runtime_health")).json()
        if not health.get("codex_auth_state", {}).get("signed_in"):
            raise SmokeFailure("health", "Codex auth is not signed in")
        if not health.get("local_mcp", {}).get("ready"):
            raise SmokeFailure("health", "Local MCP is not ready")
        if not health.get("localai_tts_ready", {}).get("ready"):
            raise SmokeFailure("health", "LocalAI TTS is not ready")
        if not health.get("localai_music_ready", {}).get("ready"):
            raise SmokeFailure("health", "LocalAI music is not ready")

        session_id = (await client.post("/api/sessions")).json()["session_id"]
        outputs_root = ROOT / "outputs" / session_id
        results: dict[str, Any] = {"session_id": session_id, "steps": {}}

        async with websockets.connect(ws_url.format(session_id=session_id), max_size=8 * 1024 * 1024) as ws:
            await _send_turn(
                ws,
                text="$imagegen 生成两张不同构图的夏日海滩旅行素材图片，用于后续制作欢快旅行 vlog。",
                attachment_ids=[],
                model=str(args.model),
                reasoning=str(args.reasoning),
            )
            snapshot = (await client.get(f"/api/sessions/{session_id}")).json()
            pending = snapshot.get("pending_media") or []
            if len(pending) < 2:
                raise SmokeFailure("imagegen", f"expected at least 2 pending images, got {len(pending)}")
            results["steps"]["imagegen"] = {
                "pending_media_ids": [item.get("id") for item in pending],
                "media_dir": str(outputs_root / "media"),
            }

            await _send_turn(
                ws,
                text="请直接调用 load_media、split_shots、understand_clips 工具，理解刚才两张素材图，不要解释内部流程。",
                attachment_ids=[str(item.get("id")) for item in pending],
                model=str(args.model),
                reasoning=str(args.reasoning),
            )
            snapshot, understand = await _ensure_tool_completed(
                client,
                ws,
                session_id=session_id,
                tool_name="understand_clips",
                model=str(args.model),
                reasoning=str(args.reasoning),
            )
            understand_path = max((outputs_root / "understand_clips").glob("*.json"), default=None, key=lambda p: p.stat().st_mtime)
            if understand_path is None:
                raise SmokeFailure("understand_clips", "artifact not found")
            results["steps"]["understand_clips"] = {"artifact": str(understand_path)}

            await _send_turn(
                ws,
                text="请直接调用 generate_script 工具，为当前素材生成一条欢快旅行 vlog 文案和标题，不要解释内部流程。",
                attachment_ids=[],
                model=str(args.model),
                reasoning=str(args.reasoning),
            )
            snapshot, script_record = await _ensure_tool_completed(
                client,
                ws,
                session_id=session_id,
                tool_name="generate_script",
                model=str(args.model),
                reasoning=str(args.reasoning),
            )
            script_path = max((outputs_root / "generate_script").glob("*.json"), default=None, key=lambda p: p.stat().st_mtime)
            if script_path is None:
                raise SmokeFailure("generate_script", "artifact not found")
            results["steps"]["generate_script"] = {"artifact": str(script_path)}

            await _send_turn(
                ws,
                text="请直接调用 generate_voiceover 工具，为当前文案生成一段欢快旅行 vlog 配音，使用默认 LocalAI TTS，不要解释内部流程。",
                attachment_ids=[],
                model=str(args.model),
                reasoning=str(args.reasoning),
            )
            snapshot, tts_record = await _ensure_tool_completed(
                client,
                ws,
                session_id=session_id,
                tool_name="generate_voiceover",
                model=str(args.model),
                reasoning=str(args.reasoning),
            )
            tts_preview = ((tts_record or {}).get("summary") or {}).get("preview_urls") or []
            if not tts_preview:
                raise SmokeFailure("generate_voiceover", "preview url missing")
            results["steps"]["generate_voiceover"] = {"preview": _assert_file(tts_preview[0], step="generate_voiceover")}

            await _send_turn(
                ws,
                text="请直接调用 select_bgm 工具，为当前成片生成一段欢快清爽的旅行背景音乐，使用默认 LocalAI BGM，不要解释内部流程。",
                attachment_ids=[],
                model=str(args.model),
                reasoning=str(args.reasoning),
            )
            snapshot, bgm_record = await _ensure_tool_completed(
                client,
                ws,
                session_id=session_id,
                tool_name="select_bgm",
                model=str(args.model),
                reasoning=str(args.reasoning),
            )
            bgm_preview = ((bgm_record or {}).get("summary") or {}).get("preview_urls") or []
            if not bgm_preview:
                raise SmokeFailure("select_bgm", "preview url missing")
            results["steps"]["select_bgm"] = {"preview": _assert_file(bgm_preview[0], step="select_bgm")}

            await _send_turn(
                ws,
                text="请直接调用 render_video 工具，把当前图片素材、配音和背景音乐渲染成一条短片，不要解释内部流程。",
                attachment_ids=[],
                model=str(args.model),
                reasoning=str(args.reasoning),
            )
            snapshot, render_record = await _ensure_tool_completed(
                client,
                ws,
                session_id=session_id,
                tool_name="render_video",
                model=str(args.model),
                reasoning=str(args.reasoning),
            )
            render_preview = ((render_record or {}).get("summary") or {}).get("preview_urls") or []
            if not render_preview:
                raise SmokeFailure("render_video", "preview url missing")
            results["steps"]["render_video"] = {"preview": _assert_file(render_preview[0], step="render_video")}

        return results


def cmd_smoke(args: argparse.Namespace) -> int:
    try:
        results = asyncio.run(_smoke_flow(args))
    except SmokeFailure as exc:
        print(json.dumps({"ok": False, "failed_step": exc.step, "error": exc.message}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, **results}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the FireRed Codex + LocalAI local development runtime.")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Start FireRed web, local MCP, and the ComfyUI bridge.")
    start.add_argument("--web-port", type=int, default=DEFAULT_WEB_PORT)
    start.add_argument("--mcp-port", type=int, default=DEFAULT_MCP_PORT)
    start.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    start.add_argument("--bridge-target-host", default=DEFAULT_BRIDGE_TARGET_HOST)
    start.add_argument("--bridge-target-port", type=int, default=DEFAULT_BRIDGE_TARGET_PORT)
    start.set_defaults(func=cmd_start)

    status = sub.add_parser("status", help="Print the runtime health snapshot.")
    status.add_argument("--web-port", type=int, default=DEFAULT_WEB_PORT)
    status.add_argument("--mcp-port", type=int, default=DEFAULT_MCP_PORT)
    status.set_defaults(func=cmd_status)

    stop = sub.add_parser("stop", help="Stop managed local development services.")
    stop.set_defaults(func=cmd_stop)

    bridge = sub.add_parser("bridge", help="Run the local ComfyUI TCP bridge.")
    bridge.add_argument("--listen-host", default="127.0.0.1")
    bridge.add_argument("--listen-port", type=int, default=DEFAULT_BRIDGE_PORT)
    bridge.add_argument("--target-host", default=DEFAULT_BRIDGE_TARGET_HOST)
    bridge.add_argument("--target-port", type=int, default=DEFAULT_BRIDGE_TARGET_PORT)
    bridge.set_defaults(func=cmd_bridge)

    smoke = sub.add_parser("smoke", help="Run a live Codex + LocalAI smoke workflow against the local FireRed app.")
    smoke.add_argument("--web-port", type=int, default=DEFAULT_WEB_PORT)
    smoke.add_argument("--model", default="gpt-5.4")
    smoke.add_argument("--reasoning", default="medium")
    smoke.set_defaults(func=cmd_smoke)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
