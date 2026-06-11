import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.tts_client import call_synthesize, call_synthesize_stream

router = APIRouter()


class SynthesizeRequest(BaseModel):
    character_id: str
    text: str
    emotion: str
    engine: str | None = None
    speed: float = 1.0


@router.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    """非流式 TTS，返回 audio_url（兼容 GPT-SOVITS 和 CosyVoice）"""
    try:
        audio_url = await call_synthesize(req.model_dump())
        return {"audio_url": audio_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthesize/stream")
async def synthesize_stream(req: SynthesizeRequest):
    """
    流式 TTS — SSE 推送音频块，边生成边播放。
    仅 CosyVoice 支持，GPT-SOVITS 请求会返回错误。
    """
    try:
        async def event_stream():
            async for chunk in call_synthesize_stream(req.model_dump()):
                if "done" in chunk:
                    yield f"event: done\ndata: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
