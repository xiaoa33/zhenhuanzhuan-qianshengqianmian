# LLM 模块对接文档（供 xiao 参考）

## ⚠️ 重要：你不需要关心 TTS 跑在什么模式

TTS 服务有两种启动模式，但对你是**完全透明**的——你始终正常返回 `emotion` 即可：

| TTS 启动方式 | 效果 | 你需要改吗？ |
|---|---|---|
| `--preload` | 情绪控制生效，不同 emotion 不同语调 | 不用 |
| `--preload --no-emotion` | TTS 内部忽略 emotion，全部走纯角色音色 | **不用** |

**你的接口契约不变：永远返回正确的 `emotion`。** TTS 是否使用它由 TTS 端决定，前端也会用 `emotion` 做 UI 特效（愤怒=红色边框等）。

---

## 你的接口

三个 POST，监听 **8001**：

### POST /asr — 用户语音识别

前端录音会经主后端转发到这里。请求为 `multipart/form-data`，字段名：

```text
audio
```

响应：

```json
{
  "text": "娘娘今日心情如何？",
  "language": "zh",
  "confidence": 0.93
}
```

### POST /generate — 角色对话

**请求**（yiping-backend 发给你）：

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

**响应**（你返回）：

```json
{
  "text": "本宫今日心情极佳，你倒是有眼力见儿。",
  "emotion": "喜悦",
  "tts_texts": {
    "cosyvoice": "[laughter]本宫今日心情极佳，你倒是有眼力见儿。",
    "gpt_sovits": "本宫今日心情极佳，你倒是有眼力见儿。"
  }
}
```

`text` 给前端气泡展示，必须干净；`tts_texts` 给不同 TTS 引擎使用。

### POST /summarize — 对话总结

略，见 `外部模块接口规范.md`。

---

## emotion 字段说明（重点）

`emotion` 必须从以下 4 个值中选一，**不要超出、不要自定义**。这个值会传给 TTS 模块控制语音语调。

| emotion | 含义 | TTS 效果 |
|---|---|---|
| `喜悦` | 开心、愉快、满意 | 声音明亮轻快 |
| `愤怒` | 生气、不满、威胁 | 声音低沉有力，带威胁感 |
| `悲伤` | 难过、哀怨、委屈 | 声音轻柔低沉，略带哭腔 |
| `平静` | 无明显情绪、陈述事实 | 纯角色音色，不加风格控制 |

### 选值建议

- 角色在威胁、训斥、发火 → `愤怒`
- 角色在感伤、诉苦、委屈、告别 → `悲伤`
- 角色在笑、满意、夸赞、心情好 → `喜悦`
- 角色在陈述、回答事实性问题 → `平静`

**不确定时选 `平静`**，好过选错。

### 示例

| 角色回复 | emotion |
|---|---|
| "贱人就是矫情！" | `愤怒` |
| "皇上万福金安，臣妾有礼了。" | `平静` |
| "本宫今日得见皇上，心中甚是欢喜。" | `喜悦` |
| "这深宫寂寞，连个说话的人都没有……" | `悲伤` |

---

## 启动方式

```bash
cd xiao-asr_llm
uvicorn main:app --reload --port 8001
```

## 验证

```bash
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{"character_id":"huafei","user_identity":"modern","history":[],"user_input":"娘娘好"}'
```

应返回包含 `text` 和 `emotion` 的 JSON。

---

## CosyVoice 文本中的精细控制 token（可选增强）

> 这是可选功能，不做也没关系。但如果做了，语音表现力会大幅提升。

LLM 应在 `tts_texts.cosyvoice` 中按语义和情绪自行插入以下 token，TTS 模块会自动识别并合成对应的副语言效果。不要把这些 token 放进顶层 `text`，也不要放进 `tts_texts.gpt_sovits`。

| token | 效果 | 适用场景 |
|---|---|---|
| `[breath]` | 呼吸/换气 | 角色犹豫、紧张、或说不下去时 |
| `[laughter]` | 轻笑 | 角色边说边笑 |
| `[sigh]` | 叹息 | 角色无奈、感伤 |
| `[cough]` | 咳嗽 | 角色身体不适 |
| `[lipsmack]` | 咂嘴 | 思考、犹豫 |
| `[noise]` | 环境噪声 | 特殊场景 |
| `<strong>xxx</strong>` | 强调 | 重读/强调某个词 |

### 使用示例

| emotion | text | 效果 |
|---|---|---|
| `愤怒` | `[breath]贱人就是矫情！` | 深吸一口气后怒斥 |
| `喜悦` | `[laughter]皇上说笑了，臣妾哪里敢。` | 边说边轻笑 |
| `悲伤` | `[sigh]嫔妾出身低微，实在不敢奢望……[breath]只求平安度日罢了。` | 叹息+换气 |
| `平静` | `在面对后宫争斗时，她展现了非凡的<strong>勇气</strong>与<strong>智慧</strong>。` | 强调关键词 |

### 建议规则

- `[breath]` — emotion=`愤怒` `悲伤` 的台词，可放在句首或长句中间
- `[laughter]` — emotion=`喜悦` 的台词，可放在轻松、得意、调侃的位置
- `[sigh]` — emotion=`悲伤` 的台词，可放在无奈、感伤、停顿处
- `<strong>` — 需要强调的关键词，1~2 个即可，不要过多
- 每个回复最多 2 个副语言 token，不要机械固定在句首

## GPT-SoVITS 文本规则

`tts_texts.gpt_sovits` 必须是干净中文文本：

- 不要包含 `[breath]`、`[laughter]`、`[sigh]` 等 token
- 不要包含 `<strong>` 或其他 HTML 标签
- 主要使用 `，`、`。`、`！`、`？`、`……` 控制停顿和语气
