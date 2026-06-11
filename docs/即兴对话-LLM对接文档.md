# 即兴对话——LLM 对接文档（供 xiao）

## 需要新增的接口

一个 POST，监听 **8001**。

### POST /generate/duet

**请求体**（后端发给你）：

```json
{
  "my_character_id": "huafei",
  "other_character_id": "zhenhuan",
  "context": "华妃和甄嬛在御花园偶遇，华妃想借机刁难甄嬛",
  "history": [
    {"role": "huafei", "text": "哟，这不是甄嬛妹妹吗？"},
    {"role": "zhenhuan", "text": "华妃娘娘安好。"}
  ],
  "my_turn": true
}
```

| 字段 | 说明 |
|---|---|
| `my_character_id` | **本轮要生成回复的角色** |
| `other_character_id` | 对方角色 |
| `context` | 场景/话题描述 |
| `history` | 完整对话历史，每条的 role 是 character_id |
| `my_turn` | 固定为 true（后端每次只让你生成一方） |

**响应体**：

```json
{
  "text": "妹妹倒是有闲情逸致，这御花园的花再好看，也比不上碎玉轩的清净吧？",
  "emotion": "平静"
}
```

| 字段 | 说明 |
|---|---|
| `text` | 当前角色的回复 |
| `emotion` | 4 选 1：`喜悦` `愤怒` `悲伤` `平静` |

---

## 调用方式

后端会循环调用你：A 说 → B 说 → A 说 → B 说 → ... 直到达到 `max_rounds` 或用户停止。每次只让你生成**一方**的回复。

```
后端调 /generate/duet(my="huafei", other="zhenhuan", history=[])
  → 你返回 "哟，这不是甄嬛妹妹吗？" / 平静

后端调 /generate/duet(my="zhenhuan", other="huafei", history=[...])
  → 你返回 "华妃娘娘安好。" / 平静

后端调 /generate/duet(my="huafei", other="zhenhuan", history=[..., ...])
  → 你返回 "妹妹倒是有闲情逸致..." / 平静
```

---

## FastAPI 骨架

```python
# 加到 xiao-asr_llm/main.py

class DuetRequest(BaseModel):
    my_character_id: str
    other_character_id: str
    context: str = ""
    history: list = []
    my_turn: bool = True


@app.post("/generate/duet")
def generate_duet(req: DuetRequest):
    # TODO: 根据 my_character_id 选对应角色 prompt
    # TODO: 根据 other_character_id + context + history 生成符合人设的回复
    # TODO: 根据回复内容判断 emotion

    # 示例 prompt 结构：
    # system: 你是{my_character}，正在和{other_character}对话。场景：{context}。
    #         请用角色口吻回复，20~50字。

    return {"text": "（即兴回复）", "emotion": "平静"}
```

```bash
uvicorn main:app --reload --port 8001
```

### 验证

```bash
curl -X POST http://localhost:8001/generate/duet \
  -H "Content-Type: application/json" \
  -d '{"my_character_id":"huafei","other_character_id":"zhenhuan","context":"御花园偶遇","history":[],"my_turn":true}'
```

---

## emotion 枚举

| 值 | TTS 效果 |
|---|---|
| `喜悦` | 开心愉快的语气 |
| `愤怒` | 低沉有力的威胁语气 |
| `悲伤` | 轻柔低沉的哀怨语气 |
| `平静` | 纯角色音色，无额外情绪控制 |

不确定时选 `平静`。

---

## 角色 ID 列表

| character_id | 角色 |
|---|---|
| zhenhuan | 甄嬛 |
| huafei | 华妃 |
| yixiu | 皇后 |
| huangshang | 皇上 |
| meizhuang | 沈眉庄 |
| anlinrong | 安陵容 |
| supeisheng | 苏培盛 |
| yelanyi | 叶澜依 |
| cuijinxi | 崔槿汐 |
| wensichu | 温实初 |
| huanbi | 浣碧 |
| guojunwang | 果郡王 |
