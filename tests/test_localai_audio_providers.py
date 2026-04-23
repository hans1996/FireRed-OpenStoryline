from pathlib import Path

from agent_fastapi import _parse_service_config
from open_storyline.nodes.core_nodes.generate_voiceover import GenerateVoiceoverNode
from open_storyline.nodes.core_nodes.select_bgm import SelectBGMNode


class _FakeResponse:
    def __init__(
        self,
        content: bytes,
        *,
        headers: dict | None = None,
        status_code: int = 200,
        text: str = "",
        json_data=None,
    ):
        self.content = content
        self.headers = headers or {}
        self.status_code = status_code
        self.text = text
        self._json_data = json_data

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def raise_for_status(self) -> None:
        if not self.ok:
            raise RuntimeError(f"http {self.status_code}: {self.text}")

    def json(self):
        if self._json_data is None:
            raise RuntimeError("no json payload")
        return self._json_data


def test_parse_service_config_extracts_bgm_provider_block() -> None:
    service_cfg = {
        "tts": {
            "provider": "localai",
            "localai": {"base_url": "http://127.0.0.1:8080", "model": "piper-zh"},
        },
        "bgm": {
            "provider": "localai",
            "localai": {"base_url": "http://127.0.0.1:8080", "model_id": "ace-step-turbo"},
        },
    }

    llm, vlm, tts, ai_transition, bgm, pexels, err = _parse_service_config(service_cfg)

    assert err is None
    assert llm is None
    assert vlm is None
    assert tts == {
        "provider": "localai",
        "localai": {"base_url": "http://127.0.0.1:8080", "model": "piper-zh"},
    }
    assert ai_transition == {}
    assert bgm == {
        "provider": "localai",
        "localai": {"base_url": "http://127.0.0.1:8080", "model_id": "ace-step-turbo"},
    }
    assert pexels == {}


def test_parse_service_config_accepts_flat_provider_fields() -> None:
    service_cfg = {
        "tts": {
            "provider": "localai",
            "mode": "gateway",
            "base_url": "http://127.0.0.1:18080",
            "voice_provider": "voxcpm",
            "voice_id": "default",
        },
        "bgm": {
            "provider": "localai",
            "mode": "gateway",
            "base_url": "http://127.0.0.1:18080",
            "duration_seconds": 12,
            "instrumental": True,
        },
    }

    llm, vlm, tts, ai_transition, bgm, pexels, err = _parse_service_config(service_cfg)

    assert err is None
    assert llm is None
    assert vlm is None
    assert ai_transition == {}
    assert pexels == {}
    assert tts == {
        "provider": "localai",
        "localai": {
            "mode": "gateway",
            "base_url": "http://127.0.0.1:18080",
            "voice_provider": "voxcpm",
            "voice_id": "default",
        },
    }
    assert bgm == {
        "provider": "localai",
        "localai": {
            "mode": "gateway",
            "base_url": "http://127.0.0.1:18080",
            "duration_seconds": 12,
            "instrumental": True,
        },
    }


def test_select_bgm_normalizes_list_filters_for_localai_prompt() -> None:
    normalized = SelectBGMNode._normalize_filter_map(["Happy", "Travel", "Happy"])

    assert normalized == {
        "mood": ["Happy"],
        "scene": ["Travel"],
    }
    prompt = SelectBGMNode._build_localai_prompt("", normalized)
    assert "instrumental background music" in prompt
    assert "mood: Happy" in prompt
    assert "scene: Travel" in prompt


def test_generate_voiceover_preserves_gateway_mode_when_node_mode_is_auto() -> None:
    node = object.__new__(GenerateVoiceoverNode)

    secrets = node._resolve_provider_secrets(
        "localai",
        {
            "mode": "gateway",
            "base_url": "http://127.0.0.1:18080",
            "api_key": "",
            "voice_provider": "voxcpm",
            "voice_id": "default",
        },
        {"mode": "auto"},
        type("_NodeState", (), {"node_summary": type("_Summary", (), {"info_for_llm": staticmethod(lambda *_args, **_kwargs: None)})()})(),
    )

    assert secrets["mode"] == "gateway"
    assert secrets["base_url"] == "http://127.0.0.1:18080"


def test_select_bgm_preserves_gateway_mode_when_node_mode_is_auto() -> None:
    node = object.__new__(SelectBGMNode)
    node.server_cfg = type(
        "_Cfg",
        (),
        {
            "select_bgm": type(
                "_SelectBgmCfg",
                (),
                {
                    "providers": {
                        "localai": {
                            "mode": "gateway",
                            "base_url": "http://127.0.0.1:18080",
                            "api_key": "",
                            "duration_seconds": 12,
                            "instrumental": True,
                        }
                    }
                },
            )()
        },
    )()

    provider_cfg = node._resolve_provider_cfg("localai", {"mode": "auto"})

    assert provider_cfg["mode"] == "gateway"
    assert provider_cfg["base_url"] == "http://127.0.0.1:18080"


def test_generate_voiceover_localai_sync_writes_audio_file(tmp_path: Path, monkeypatch) -> None:
    seen = {}

    def _fake_post(url, *, headers=None, json=None, timeout=None):
        seen["url"] = url
        seen["headers"] = headers
        seen["json"] = json
        seen["timeout"] = timeout
        return _FakeResponse(b"RIFFtest-wave", headers={"Content-Type": "audio/wav"})

    monkeypatch.setattr("open_storyline.nodes.core_nodes.generate_voiceover.requests.post", _fake_post)

    node = object.__new__(GenerateVoiceoverNode)
    wav_path = tmp_path / "voice.wav"

    node._tts_localai_sync(
        text="你好，世界",
        wav_path=wav_path,
        secrets={"base_url": "http://127.0.0.1:8080", "api_key": "local-key"},
        tts_params={"model": "piper-zh", "backend": "piper"},
        provider_cfg={},
    )

    assert wav_path.read_bytes() == b"RIFFtest-wave"
    assert seen["url"] == "http://127.0.0.1:8080/tts"
    assert seen["headers"]["Authorization"] == "Bearer local-key"
    assert seen["json"]["model"] == "piper-zh"
    assert seen["json"]["backend"] == "piper"
    assert seen["json"]["input"] == "你好，世界"


def test_select_bgm_localai_sync_generates_local_audio_file(tmp_path: Path, monkeypatch) -> None:
    seen = {}

    def _fake_post(url, *, headers=None, json=None, timeout=None):
        seen["url"] = url
        seen["headers"] = headers
        seen["json"] = json
        seen["timeout"] = timeout
        return _FakeResponse(b"ID3fake-mp3", headers={"Content-Type": "audio/mpeg"})

    monkeypatch.setattr("open_storyline.nodes.core_nodes.select_bgm.requests.post", _fake_post)

    node = object.__new__(SelectBGMNode)
    out_dir = tmp_path / "bgm"
    out_dir.mkdir()

    result = node._generate_localai_bgm_sync(
        prompt="欢快的旅行 vlog 背景音乐",
        output_dir=out_dir,
        provider_cfg={
            "base_url": "http://127.0.0.1:8080",
            "api_key": "local-key",
            "model_id": "ace-step-turbo",
            "duration_seconds": 12,
        },
    )

    result_path = Path(result["path"])
    assert result["bgm_id"].startswith("bgm_localai_")
    assert result_path.exists()
    assert result_path.suffix == ".mp3"
    assert result_path.read_bytes() == b"ID3fake-mp3"
    assert seen["url"] == "http://127.0.0.1:8080/v1/sound-generation"
    assert seen["headers"]["Authorization"] == "Bearer local-key"
    assert seen["json"]["model_id"] == "ace-step-turbo"
    assert seen["json"]["text"] == "欢快的旅行 vlog 背景音乐"
    assert seen["json"]["duration_seconds"] == 12
    assert seen["json"]["instrumental"] is True


def test_generate_voiceover_localai_gateway_mode_polls_job_and_downloads_asset(tmp_path: Path, monkeypatch) -> None:
    seen = {"post": [], "get": []}
    job_polls = {"count": 0}

    def _fake_post(url, *, headers=None, json=None, timeout=None):
        seen["post"].append((url, headers, json, timeout))
        return _FakeResponse(
            b"",
            headers={"Content-Type": "application/json"},
            json_data={"data": {"job_id": "job-tts-1"}},
        )

    def _fake_get(url, *, headers=None, timeout=None):
        seen["get"].append((url, headers, timeout))
        if url.endswith("/api/v1/jobs/job-tts-1"):
            job_polls["count"] += 1
            status = "running" if job_polls["count"] == 1 else "succeeded"
            payload = {"data": {"status": status, "result_asset_ids": ["asset-tts-1"] if status == "succeeded" else []}}
            return _FakeResponse(
                b"",
                headers={"Content-Type": "application/json"},
                json_data=payload,
            )
        if url.endswith("/api/v1/assets/asset-tts-1/content"):
            return _FakeResponse(b"RIFFgateway-wave", headers={"Content-Type": "audio/wav"})
        raise AssertionError(f"unexpected GET {url}")

    monkeypatch.setattr("open_storyline.nodes.core_nodes.generate_voiceover.requests.post", _fake_post)
    monkeypatch.setattr("open_storyline.nodes.core_nodes.generate_voiceover.requests.get", _fake_get)
    monkeypatch.setattr("open_storyline.nodes.core_nodes.generate_voiceover.time.sleep", lambda *_args, **_kwargs: None)

    node = object.__new__(GenerateVoiceoverNode)
    wav_path = tmp_path / "voice_gateway.wav"

    node._tts_localai_sync(
        text="你好，世界",
        wav_path=wav_path,
        secrets={
            "base_url": "http://127.0.0.1:18080",
            "api_key": "gateway-token",
            "mode": "gateway",
            "voice_provider": "voxcpm",
            "voice_id": "default",
        },
        tts_params={},
        provider_cfg={"format": "wav", "sample_rate_hz": 24000},
    )

    assert wav_path.read_bytes() == b"RIFFgateway-wave"
    create_url, create_headers, create_json, _ = seen["post"][0]
    assert create_url == "http://127.0.0.1:18080/api/v1/jobs/tts"
    assert create_headers["Authorization"] == "Bearer gateway-token"
    assert create_json["voice"]["provider"] == "voxcpm"
    assert create_json["voice"]["voice_id"] == "default"
    assert create_json["output"]["format"] == "wav"
    assert create_json["output"]["sample_rate_hz"] == 24000
    assert job_polls["count"] == 2


def test_select_bgm_localai_gateway_mode_polls_job_and_downloads_asset(tmp_path: Path, monkeypatch) -> None:
    seen = {"post": [], "get": []}

    def _fake_post(url, *, headers=None, json=None, timeout=None):
        seen["post"].append((url, headers, json, timeout))
        return _FakeResponse(
            b"",
            headers={"Content-Type": "application/json"},
            json_data={"data": {"job_id": "job-music-1"}},
        )

    def _fake_get(url, *, headers=None, timeout=None):
        seen["get"].append((url, headers, timeout))
        if url.endswith("/api/v1/jobs/job-music-1"):
            return _FakeResponse(
                b"",
                headers={"Content-Type": "application/json"},
                json_data={"data": {"status": "succeeded", "result_asset_ids": ["asset-music-1"]}},
            )
        if url.endswith("/api/v1/assets/asset-music-1/content"):
            return _FakeResponse(b"ID3gateway-mp3", headers={"Content-Type": "audio/mpeg"})
        raise AssertionError(f"unexpected GET {url}")

    monkeypatch.setattr("open_storyline.nodes.core_nodes.select_bgm.requests.post", _fake_post)
    monkeypatch.setattr("open_storyline.nodes.core_nodes.select_bgm.requests.get", _fake_get)
    monkeypatch.setattr("open_storyline.nodes.core_nodes.select_bgm.time.sleep", lambda *_args, **_kwargs: None)

    node = object.__new__(SelectBGMNode)
    out_dir = tmp_path / "bgm_gateway"
    out_dir.mkdir()

    result = node._generate_localai_bgm_sync(
        prompt="欢快的旅行 vlog 背景音乐",
        output_dir=out_dir,
        provider_cfg={
            "base_url": "http://127.0.0.1:18080",
            "api_key": "gateway-token",
            "mode": "gateway",
            "duration_seconds": 12,
            "instrumental": True,
        },
    )

    result_path = Path(result["path"])
    assert result_path.exists()
    assert result_path.suffix == ".mp3"
    assert result_path.read_bytes() == b"ID3gateway-mp3"
    create_url, create_headers, create_json, _ = seen["post"][0]
    assert create_url == "http://127.0.0.1:18080/api/v1/jobs/music"
    assert create_headers["Authorization"] == "Bearer gateway-token"
    assert create_json["prompt"] == "欢快的旅行 vlog 背景音乐"
    assert create_json["style"]["duration_seconds"] == 12
    assert create_json["style"]["instrumental"] is True
