import os
import httpx
from mock.mock_data import get_mock_reply, get_mock_summary

LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:8001")
USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"


async def call_generate(payload: dict) -> dict:
    """
    调用 xiao-asr_llm 模块的 POST /generate 接口。
    替换为真实实现时，只需修改此函数，将 USE_MOCK 设为 false 即可。

    期望响应: { "text": str, "emotion": "愤怒"|"悲伤"|"喜悦"|"平静" }
    """
    if USE_MOCK:
        return get_mock_reply(payload.get("character_id", ""))

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{LLM_SERVICE_URL}/generate", json=payload)
        resp.raise_for_status()
        return resp.json()


async def call_summarize(payload: dict) -> dict:
    """
    调用 xiao-asr_llm 模块的 POST /summarize 接口。
    替换为真实实现时，只需修改此函数，将 USE_MOCK 设为 false 即可。

    期望响应: { "attitude": str, "comment": str }
    """
    if USE_MOCK:
        return get_mock_summary(payload.get("character_id", ""))

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{LLM_SERVICE_URL}/summarize", json=payload)
        resp.raise_for_status()
        return resp.json()
