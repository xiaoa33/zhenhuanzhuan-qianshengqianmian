import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.llm_client import call_duet_generate
from services.tts_client import call_synthesize_stream

router = APIRouter()


class DuetRequest(BaseModel):
    character_a: str
    character_b: str
    context: str = "两位角色在宫中相遇"
    starter: str
    max_rounds: int = 10


@router.post("/duet/start")
async def duet_start(req: DuetRequest):
    characters = [req.character_a, req.character_b]

    async def event_stream():
        history: list[dict] = []
        # 用下标 0/1 交替，避免闭包内赋值的 UnboundLocalError
        current_idx = 0 if req.starter == characters[0] else 1

        for _ in range(req.max_rounds):
            current = characters[current_idx]
            other = characters[1 - current_idx]

            # 1. LLM 生成本回合台词
            try:
                llm = await call_duet_generate({
                    "my_character_id": current,
                    "other_character_id": other,
                    "context": req.context,
                    "history": history,
                })
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
                break

            text = llm["text"]
            emotion = llm.get("emotion", "平静")
            history.append({"role": current, "text": text})

            # 2. 推送文本给前端
            yield f"data: {json.dumps({'role': current, 'text': text, 'emotion': emotion}, ensure_ascii=False)}\n\n"

            # 3. TTS 流式合成 + 转发音频块
            try:
                async for chunk in call_synthesize_stream({
                    "character_id": current,
                    "text": text,
                    "emotion": emotion,
                    "engine": "cosyvoice",
                }):
                    if chunk.get("audio"):
                        yield f"data: {json.dumps({'audio': chunk['audio'], 'dur': chunk.get('dur', 0)})}\n\n"
            except Exception:
                pass  # TTS 失败不中断对话流程

            # 换对方发言
            current_idx = 1 - current_idx

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform"},
    )
