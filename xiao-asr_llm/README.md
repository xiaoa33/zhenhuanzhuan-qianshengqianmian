# xiao-asr_llm

ASR + LLM 模块，监听 `8001`，供 `yiping-backend` 调用。

## 接口

- `POST /asr`：浏览器录音转文字，字段名为 multipart `audio`
- `POST /generate`：生成角色回复、情绪、两套 TTS 文本
- `POST /generate/duet`：生成即兴对话中当前角色的一句台词和情绪
- `POST /summarize`：生成对话总结

`/generate` 返回示例：

```json
{
  "text": "本宫今日心情尚可，你倒是有眼力见儿。",
  "emotion": "喜悦",
  "tts_texts": {
    "cosyvoice": "[laughter]本宫今日心情尚可，你倒是有眼力见儿。",
    "gpt_sovits": "本宫今日心情尚可，你倒是有眼力见儿。"
  }
}
```

## 启动

```bash
cd zhenhuanzhuan-qianshengqianmian/xiao-asr_llm
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

## LLM 配置

未配置 LLM 时，`/generate` 和 `/summarize` 会走 fallback，保证网站可演示。

如需接 OpenAI-compatible Chat Completions：

```env
LLM_API_KEY=...
LLM_BASE_URL=https://your-compatible-endpoint/v1
LLM_MODEL=your-chat-model
LLM_TEMPERATURE=0.75
```

也兼容 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`。

## ASR 配置

`/asr` 使用 `faster-whisper`。需要先配置本地模型名或模型路径：

```env
ASR_MODEL=large-v3
ASR_DEVICE=cuda
ASR_COMPUTE_TYPE=float16
ASR_LANGUAGE=zh
```

如果没有配置 `ASR_MODEL` 或 `ASR_MODEL_PATH`，`/asr` 会返回 501，文本输入不受影响。
