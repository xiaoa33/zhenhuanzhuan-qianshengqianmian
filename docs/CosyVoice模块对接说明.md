# CosyVoice 模块对接说明

本文档给 CosyVoice 模块负责人看，说明当前网站接入 TTS 的方式、最近改动，以及 CosyVoice 服务需要保持的接口契约。

## 1. 当前整体链路

```text
前端 React
  -> yiping-backend
      -> xiao-asr_llm 生成角色回复、emotion、两套 TTS 文本
      -> 按前端选择的语音模型调用对应 TTS 服务
          - GPT-SoVITS
          - CosyVoice
```

前端现在有两个可选项：

- 情绪：`自动` / `喜悦` / `愤怒` / `悲伤` / `平静`
- 模型：`GPT-SoVITS` / `CosyVoice`

如果用户选 `自动`，LLM 会自行判断回复应使用的情绪。如果用户手动选情绪，LLM 会按指定情绪生成回复，TTS 也会收到该情绪。

## 2. LLM 现在返回什么

`xiao-asr_llm` 的 `POST /generate` 现在只调用一次 LLM，但会返回三类文本：

```json
{
  "text": "本宫今日心情尚可，你倒是有眼力见儿。",
  "emotion": "喜悦",
  "tts_texts": {
    "cosyvoice": "[laughter]本宫今日心情尚可，你倒是有<strong>眼力见儿</strong>。",
    "gpt_sovits": "本宫今日心情尚可，你倒是有眼力见儿。"
  }
}
```

字段含义：

| 字段 | 用途 |
|---|---|
| `text` | 前端气泡展示，干净文本，不含 token |
| `emotion` | 四选一：`喜悦`、`愤怒`、`悲伤`、`平静` |
| `tts_texts.cosyvoice` | 给 CosyVoice 的文本，可包含 CosyVoice 精细控制 token |
| `tts_texts.gpt_sovits` | 给 GPT-SoVITS 的文本，不含 token/HTML |

重点：现在不是固定规则给 CosyVoice 加 token，而是让 LLM 在 `tts_texts.cosyvoice` 中按语义自行插入 token。后端只做合法性清洗和兜底。

## 3. CosyVoice 会收到什么请求

主后端的 `POST /synthesize` 会根据前端选择的模型分发：

- `engine=gpt_sovits` -> `GPT_SOVITS_SERVICE_URL`
- `engine=cosyvoice` -> `COSYVOICE_SERVICE_URL`

CosyVoice 服务仍然只需要实现：

```text
POST /synthesize
```

请求体示例：

```json
{
  "character_id": "zhenhuan",
  "text": "[laughter]本宫今日心情尚可，你倒是有<strong>眼力见儿</strong>。",
  "emotion": "喜悦",
  "engine": "cosyvoice"
}
```

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `character_id` | string | 网站角色 ID，例如 `zhenhuan`、`huafei`、`huangshang` |
| `text` | string | CosyVoice 合成文本，可能包含 token 和 `<strong>` |
| `emotion` | string | 情绪标签，四选一 |
| `engine` | string | 当前为 `cosyvoice`，可忽略 |

## 4. CosyVoice 返回什么

CosyVoice 返回格式保持不变，二选一即可。

推荐返回绝对路径：

```json
{
  "audio_path": "/absolute/path/to/output.wav"
}
```

或返回 base64：

```json
{
  "audio_base64": "UklGRiQ...",
  "format": "wav"
}
```

`yiping-backend` 会把音频复制/写入 `static/audio/`，再返回给前端可访问的 `audio_url`。

## 5. CosyVoice 需要支持的 token

LLM 目前只允许这些 token 出现在 `tts_texts.cosyvoice`：

| token | 预期效果 |
|---|---|
| `[breath]` | 呼吸/换气 |
| `[laughter]` | 笑声或带笑说话 |
| `[sigh]` | 叹息 |
| `[cough]` | 咳嗽 |
| `[lipsmack]` | 咂嘴/轻微口腔音 |
| `[noise]` | 噪声/特殊非语音 |
| `<strong>...</strong>` | 强调/重读 |

后端会把不在上表的方括号 token 删除，并且最多保留 2 个副语言 token，避免 LLM 滥用。

注意：用户有时口头会说 `[laugh]`，但后端会规范成 `[laughter]`。

## 6. 端口和环境变量

当前建议端口：

| 服务 | 端口 |
|---|---|
| yiping-backend | `8003` |
| xiao-asr_llm | `8001` |
| CosyVoice 本地入口/SSH 隧道 | `8002` |
| GPT-SoVITS service | `8004` |

主后端 `.env` 当前相关配置：

```env
TTS_SERVICE_URL=http://localhost:8002
GPT_SOVITS_SERVICE_URL=http://localhost:8004
COSYVOICE_SERVICE_URL=http://localhost:8002
```

如果 CosyVoice 云端实际跑在 `cloud:8003`，本地可以这样建隧道：

```bash
ssh -L 8002:localhost:8003 -p 28281 root@connect.bjb1.seetacloud.com
```

这样 CosyVoice 维持原来的本地 `8002`，不会和本地 GPT-SoVITS 的 `8004` 冲突。

## 7. 角色 ID

CosyVoice 继续使用网站角色 ID：

| character_id | 角色 |
|---|---|
| `zhenhuan` | 甄嬛 |
| `huafei` | 华妃 |
| `yixiu` | 宜修/皇后 |
| `meizhuang` | 沈眉庄 |
| `anlinrong` | 安陵容 |
| `supeisheng` | 苏培盛 |
| `yelanyi` | 叶澜依 |
| `cuijinxi` | 崔槿汐 |
| `wensichu` | 温实初 |
| `huanbi` | 浣碧 |
| `huangshang` | 皇上 |
| `guojunwang` | 果郡王 |

GPT-SoVITS 内部有自己的角色 ID 映射，但这不影响 CosyVoice。

## 8. CosyVoice 负责人需要做什么

需要确认：

1. CosyVoice 服务监听的本地地址与 `COSYVOICE_SERVICE_URL` 一致。
2. `POST /synthesize` 接收上面定义的 JSON。
3. `text` 字段可以解析 `[laughter]`、`[sigh]`、`[breath]` 等 token。
4. 如果暂时不支持某些 token，至少不要报错，可以选择忽略。
5. 返回 `audio_path` 时必须是 yiping-backend 进程可读的绝对路径。

不需要做：

- 不需要自己判断用户选的是哪个 TTS 模型。
- 不需要调用 LLM。
- 不需要处理 GPT-SoVITS 的文本清洗。
- 不需要处理前端静态资源 URL，主后端会统一复制音频并返回 URL。

## 9. 调试命令

直接测 CosyVoice 服务：

```bash
curl -X POST http://localhost:8002/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "zhenhuan",
    "text": "[laughter]本宫今日心情尚可，你倒是有<strong>眼力见儿</strong>。",
    "emotion": "喜悦",
    "engine": "cosyvoice"
  }'
```

通过主后端测 CosyVoice 分发：

```bash
curl -X POST http://localhost:8003/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "zhenhuan",
    "text": "[laughter]本宫今日心情尚可，你倒是有<strong>眼力见儿</strong>。",
    "emotion": "喜悦",
    "engine": "cosyvoice"
  }'
```

第二个命令成功时，会返回：

```json
{
  "audio_url": "http://localhost:8003/static/audio/reply_xxx.wav"
}
```
