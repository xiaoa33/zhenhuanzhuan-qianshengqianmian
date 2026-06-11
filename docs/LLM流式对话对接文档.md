# LLM 流式对话对接文档

## 概述

在现有 `/generate` 基础上新增流式版本，LLM 逐字/逐句输出，TTS 边接收边合成，实现更低首播延迟。

### 调用链路

```
前端 POST /chat/stream → yiping-backend
  → POST /generate/stream → LLM (:8001)   SSE 推送 text chunks
  → 非流式 POST /synthesize → TTS (:8002)  整句合成（简单方案）
  或
  → 流式 POST /synthesize/stream → TTS    边生成边播放（高级方案）
```

---

## LLM 需要实现的接口

### POST /generate/stream — 流式角色对话

监听端口 **8001**，和 `/generate` 同一个服务。

**请求体**（和普通 `/generate` 完全一致）：

```json
{
  "character_id": "huafei",
  "user_identity": "modern",
  "user_role_id": null,
  "user_role_name": null,
  "history": [
    {"role": "user", "text": "华妃娘娘好"},
    {"role": "character", "text": "贱人就是矫情"}
  ],
  "user_input": "娘娘今日心情如何？"
}
```

**响应**：SSE (Server-Sent Events)，`Content-Type: text/event-stream`

```
data: {"text_chunk": "本宫"}
data: {"text_chunk": "今日"}
data: {"text_chunk": "心情"}
data: {"text_chunk": "极佳，"}
data: {"text_chunk": "你倒是有眼力见儿。"}
event: done
data: {"emotion": "喜悦", "full_text": "本宫今日心情极佳，你倒是有眼力见儿。"}
```

### 字段说明

| SSE 事件 | 字段 | 说明 |
|---|---|---|
| `data:` | `text_chunk` | 本次推送的文本片段（1~5字），逐词或逐句 |
| `event: done` | `emotion` | 整句的情绪标签（4选1，同 /generate） |
| `event: done` | `full_text` | 完整回复文本（方便后端校验） |

### emotion 枚举

| 值 | 含义 |
|---|---|
| `喜悦` | 开心、愉快 |
| `愤怒` | 生气、不满 |
| `悲伤` | 难过、哀怨 |
| `平静` | 无情绪、陈述 |

---

## FastAPI 骨架代码

```python
# main.py（放在 xiao-asr_llm 目录）
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import json

app = FastAPI()

class GenerateRequest(BaseModel):
    character_id: str
    user_identity: str
    user_role_id: Optional[str] = None
    user_role_name: Optional[str] = None
    history: list
    user_input: str


@app.post("/generate/stream")
async def generate_stream(req: GenerateRequest):
    """
    流式角色对话 — SSE 推送文本片段
    """
    async def event_stream():
        # TODO: 替换为你的 LLM 流式调用
        reply = "本宫今日心情极佳，你倒是有眼力见儿。"
        emotion = "喜悦"

        # 逐字推送（模拟）
        for char in reply:
            yield f"data: {json.dumps({'text_chunk': char}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)  # 模拟生成延迟

        # 结束信号 + 元信息
        yield f"event: done\ndata: {json.dumps({'emotion': emotion, 'full_text': reply}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

```bash
# 启动
uvicorn main:app --reload --port 8001
```

### 本地验证

```bash
curl -N -X POST http://localhost:8001/generate/stream \
  -H "Content-Type: application/json" \
  -d '{"character_id":"huafei","user_identity":"modern","history":[],"user_input":"娘娘好"}'
```

---

## yiping-backend 侧（供 yiping 参考）

流式 `/chat/stream` 大致逻辑：

```python
@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def event_stream():
        # 1. 调用 LLM 流式
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", f"{LLM_URL}/generate/stream", json=req.dict()) as resp:
                full_text = ""
                emotion = "平静"
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if "text_chunk" in data:
                            full_text += data["text_chunk"]
                    elif line.startswith("event: done"):
                        data_part = await read_next_data_line()
                        data = json.loads(data_part)
                        emotion = data.get("emotion", "平静")

        # 2. 转发文本给前端
        yield f"data: {json.dumps({'text': full_text, 'emotion': emotion})}\n\n"

        # 3. TTS 合成（非流式，简单方案）
        tts = await call_synthesize({"character_id": req.character_id, "text": full_text, "emotion": emotion})
        yield f"data: {json.dumps({'audio_url': tts})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

> 高级方案：LLM 流式文本 → 前端先显示文字，同时后端调 TTS 流式 `/synthesize/stream` 推送音频 chunk，前端 MediaSource 逐块播放。可后续迭代。

---

## 对接步骤

1. **LLM 队友**按本文档实现 `POST /generate/stream`，监听 8001
2. **yiping** 按上方骨架实现 `/chat/stream`
3. **前端**增加 SSE 消费逻辑（或在现有 ChatPage 基础上扩展）
4. 测试：`curl -N http://localhost:8000/chat/stream -d '...'`
