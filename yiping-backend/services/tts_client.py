import os
import base64
import uuid
import shutil
import httpx

TTS_SERVICE_URL = os.getenv("TTS_SERVICE_URL", "http://localhost:8002")
GPT_SOVITS_SERVICE_URL = os.getenv("GPT_SOVITS_SERVICE_URL", TTS_SERVICE_URL)
COSYVOICE_SERVICE_URL = os.getenv("COSYVOICE_SERVICE_URL", os.getenv("COSYVOICE_TTS_SERVICE_URL", TTS_SERVICE_URL))
USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"
# 允许独立控制 TTS mock，优先级: USE_MOCK_TTS > USE_MOCK
_use_mock_tts = os.getenv("USE_MOCK_TTS", "").lower()
USE_MOCK_TTS = _use_mock_tts == "true" if _use_mock_tts else USE_MOCK
STATIC_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "audio")
STATIC_BASE_URL = os.getenv("STATIC_BASE_URL", "http://localhost:8000")


def _tts_service_url(payload: dict) -> str:
    engine = (payload.get("engine") or "gpt_sovits").replace("-", "_")
    if engine == "cosyvoice":
        return COSYVOICE_SERVICE_URL
    if engine == "gpt_sovits":
        return GPT_SOVITS_SERVICE_URL
    return TTS_SERVICE_URL


async def call_synthesize(payload: dict) -> str:
    """
    调用 TTS 模块的 POST /synthesize 接口，返回可访问的 audio_url。
    替换为真实实现时，只需修改此函数，将 USE_MOCK 设为 false 即可。

    TTS 模块支持两种响应格式：
      方案A: { "audio_path": "/absolute/path/to/audio.wav" }
      方案B: { "audio_base64": "...", "format": "wav" }
    """
    if USE_MOCK_TTS:
        return f"{STATIC_BASE_URL}/static/audio/mock_silence.wav"

    service_url = _tts_service_url(payload).rstrip("/")
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{service_url}/synthesize", json=payload)
        resp.raise_for_status()
        data = resp.json()

    os.makedirs(STATIC_AUDIO_DIR, exist_ok=True)
    filename = f"reply_{uuid.uuid4().hex}.wav"
    dest = os.path.join(STATIC_AUDIO_DIR, filename)

    if "audio_path" in data:
        # 方案A：直接复制文件到 static/audio/
        shutil.copy2(data["audio_path"], dest)
    elif "audio_base64" in data:
        # 方案B：解码 base64 写入文件
        ext = data.get("format", "wav")
        filename = f"reply_{uuid.uuid4().hex}.{ext}"
        dest = os.path.join(STATIC_AUDIO_DIR, filename)
        with open(dest, "wb") as f:
            f.write(base64.b64decode(data["audio_base64"]))
    else:
        raise ValueError("TTS 响应格式不支持，需含 audio_path 或 audio_base64 字段")

    return f"{STATIC_BASE_URL}/static/audio/{filename}"
