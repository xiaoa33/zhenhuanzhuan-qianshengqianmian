# 甄嬛传·千声千面 — 前端

《甄嬛传·千声千面》的 React 前端，实现角色选择、AI 对话、语音播放、数字人视频展示与对话总结卡片。

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | React 18 + React Router v6 |
| 构建 | Vite 5 |
| 样式 | 纯 CSS（CSS Variables + Keyframes） |
| 字体 | Ma Shan Zheng（毛笔风，Google Fonts）+ 宋体 |
| 截图导出 | html2canvas |

---

## 快速启动

### 1. 安装依赖

```bash
cd yiping-frontend
npm install
```

### 2. 配置后端地址

复制环境变量模板：

```bash
cp .env.example .env.local
```

编辑 `.env.local`，填入后端服务地址：

```
VITE_API_BASE_URL=http://localhost:8000
```

### 3. 启动开发服务器

```bash
npm run dev
```

浏览器自动打开 `http://localhost:5173`。

### 4. 构建生产包

```bash
npm run build
```

产物输出到 `dist/`。构建后需将 `resource/` 文件夹整体复制到 `dist/resource/`，或通过 Web 服务器（Nginx/Apache）将 `/resource/` 路由到该目录。

```bash
# 构建后复制静态资源示例
cp -r resource dist/resource
```

---

## 项目结构

```
yiping-frontend/
├── index.html                   # HTML 入口（含 Google Font 引入）
├── vite.config.js               # Vite 配置（含 resource/ 静态资源插件）
├── package.json
├── .env.example                 # 环境变量模板
├── resource/                    # 静态资源（背景图、角色剧照、背景音乐）
│   ├── 背景图/
│   ├── 角色剧照/
│   └── 长相思（甄嬛传背景音乐）.mp3
└── src/
    ├── main.jsx                 # 入口
    ├── App.jsx                  # 路由 + 全局音乐 Context
    ├── styles/
    │   └── global.css           # CSS 变量、全局动画、重置样式
    ├── data/
    │   └── characters.js        # 12 个角色的配置数据
    ├── api/
    │   └── index.js             # 后端接口封装
    ├── pages/
    │   ├── HomePage.jsx / .css          # 主页
    │   ├── CharacterSelectPage.jsx / .css  # 角色选择页
    │   └── ChatPage.jsx / .css          # 对话页
    └── components/
        └── SummaryCard.jsx / .css       # 对话总结弹窗
```

---

## 需要后端提供的服务

### 数字人服务

| 项目 | 说明 |
|------|------|
| 推荐方案 | SadTalker 或 MuseTalk |
| 输入 | 角色剧照 + 合成音频 |
| 输出 | 说话视频（MP4/WebM），通过 URL 返回给前端 |
| 前端行为 | 收到 `video_url` 后替换左侧剧照播放视频；视频结束后自动恢复剧照 |
| 降级方案 | 若生成延迟高，可预录精彩对话视频片段作为演示素材 |

---

### HTTP 接口列表

所有接口均为 POST 请求，`Content-Type: application/json`，Base URL 由 `VITE_API_BASE_URL` 配置。

---

#### `POST /chat` — 对话

**请求体**

```json
{
  "character_id": "huafei",
  "user_identity": "modern",
  "user_role_id": null,
  "history": [
    { "role": "user", "text": "华妃娘娘好" },
    { "role": "character", "text": "贱人就是矫情" }
  ],
  "user_input": "娘娘今日心情如何？"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `character_id` | string | 对话角色 ID（见下方角色 ID 表） |
| `user_identity` | `"modern"` \| `"ancient"` | 用户身份 |
| `user_role_id` | string \| null | 用户扮演的角色 ID（仅 `ancient` 时有值） |
| `history` | array | 历史对话记录 |
| `user_input` | string | 本轮用户输入 |

**响应体**

```json
{
  "text": "本宫今日心情极佳，你倒是有眼力见儿。",
  "emotion": "喜悦"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | 角色回复文本 |
| `emotion` | string | 情绪标签：`愤怒` \| `悲伤` \| `喜悦` \| `平静` |

---

#### `POST /synthesize` — 语音合成

**请求体**

```json
{
  "character_id": "huafei",
  "text": "本宫今日心情极佳，你倒是有眼力见儿。",
  "emotion": "喜悦"
}
```

**响应体**

```json
{
  "audio_url": "http://localhost:8000/static/audio/reply_001.mp3"
}
```

前端收到 `audio_url` 后用 `<audio>` 标签播放，同时触发左侧声波动画。

---

#### `POST /digital-human` — 数字人视频生成

**请求体**

```json
{
  "character_id": "huafei",
  "audio_url": "http://localhost:8000/static/audio/reply_001.mp3"
}
```

**响应体**

```json
{
  "video_url": "http://localhost:8000/static/video/reply_001.mp4"
}
```

前端收到 `video_url` 后用 `<video>` 标签替换左侧角色剧照播放；视频播完后自动恢复剧照。

---

#### `POST /summary` — 对话总结

在用户点击"结束对话"时调用，由 LLM 生成本次对话的角色态度评价。

**请求体**

```json
{
  "character_id": "huafei",
  "messages": [
    { "role": "user", "text": "华妃娘娘好" },
    { "role": "character", "text": "贱人就是矫情" }
  ]
}
```

**响应体**

```json
{
  "attitude": "戒备有加",
  "comment": "你尚未入她眼，需再努力",
  "rounds": 8
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `attitude` | string | 角色对用户的态度（简短词语） |
| `comment` | string | 角色风格总结语 |
| `rounds` | number | 对话轮次（可由后端计算，也可由前端传入） |

---

### 角色 ID 对照表

| 角色名 | `character_id` |
|--------|----------------|
| 甄嬛 | `zhenhuan` |
| 华妃·年世兰 | `huafei` |
| 乌拉那拉·宜修 | `yixiu` |
| 沈眉庄 | `meizhuang` |
| 安陵容 | `anlinrong` |
| 苏培盛 | `supeisheng` |
| 叶澜依 | `yelanyi` |
| 崔槿汐 | `cuijinxi` |
| 温实初 | `wensichu` |
| 浣碧 | `huanbi` |
| 皇上·胤禛 | `huangshang` |
| 果郡王·允礼 | `guojunwang` |

---

## 情绪视觉效果说明

后端 `/chat` 返回的 `emotion` 字段会触发前端对话区的视觉效果，持续约 2.5 秒：

| 情绪值 | 视觉效果 |
|--------|---------|
| `愤怒` | 对话区背景闪烁红色遮罩（3 次，每次 0.5s） |
| `悲伤` | 对话区整体亮度降低 10%（transition 1s） |
| `喜悦` | 对话区内侧金色光晕（3 次，每次 0.5s） |
| `平静`（或其他） | 无特殊效果 |

---

## 跨域说明

前端开发服务器运行在 `localhost:5173`，后端若在不同端口，需在后端开启 CORS，允许来自前端地址的请求。

FastAPI 示例：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```
