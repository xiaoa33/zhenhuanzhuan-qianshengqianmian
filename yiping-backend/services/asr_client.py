import os

import httpx


LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:8001")
USE_MOCK_ASR = os.getenv("USE_MOCK_ASR", "false").lower() == "true"


async def call_asr(filename: str, content: bytes, content_type: str | None = None) -> dict:
    """Proxy uploaded browser audio to xiao-asr_llm POST /asr."""
    if USE_MOCK_ASR:
        return {"text": "娘娘今日心情如何？", "language": "zh", "confidence": None}

    files = {
        "audio": (
            filename or "recording.webm",
            content,
            content_type or "application/octet-stream",
        )
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(f"{LLM_SERVICE_URL}/asr", files=files)
        resp.raise_for_status()
        return resp.json()
