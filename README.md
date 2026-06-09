# 甄嬛传·千声千面

基于大语言模型与语音合成的甄嬛传角色互动系统，支持 AI 角色对话、情感语音合成与数字人视频生成。

---

## 系统架构

```
前端 React (:5173)
    │
    ▼
yiping-backend FastAPI (:8000)   ← 主后端，负责路由和 SadTalker 调用
    │
    ├── xiao-asr_llm (:8001)     ← 模块A：ASR + LLM 对话生成 + 情绪分析
    └── GPT-SoVITS TTS (:8002)   ← 模块B：角色声音合成
```

各模块独立运行，主后端通过 `USE_MOCK=true` 可在外部模块未就绪时用预设数据运行。

---

## 环境要求

| 工具 | 版本要求 |
|------|---------|
| Python | 3.10+（主后端）；3.8（SadTalker 专用虚拟环境） |
| Node.js | 18+ |
| npm | 9+ |
| uv（可选） | 用于管理 SadTalker Python 3.8 虚拟环境 |

---

## 一、配置并启动前端

```bash
cd yiping-frontend
npm install
```

复制环境变量模板：

```bash
# Windows
copy .env.example .env.local

# macOS / Linux
cp .env.example .env.local
```

编辑 `.env.local`，确认后端地址：

```env
VITE_API_BASE_URL=http://localhost:8000
```

启动开发服务器：

```bash
npm run dev
```

浏览器访问 `http://localhost:5173`。

---

## 二、配置并启动主后端

```bash
cd yiping-backend
pip install -r requirements.txt
```

复制环境变量模板：

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

**`.env` 关键配置说明：**

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `USE_MOCK` | `true` | `true` 时 /chat、/synthesize、/summary 使用预设数据，外部模块未就绪时保持 true |
| `USE_MOCK_ASR` | `false` | `true` 时 /asr 返回固定演示文本 |
| `LLM_SERVICE_URL` | `http://localhost:8001` | LLM 模块地址，默认无需修改 |
| `TTS_SERVICE_URL` | `http://localhost:8002` | TTS 模块地址，默认无需修改 |
| `SADTALKER_PATH` | `../SadTalker/SadTalker` | SadTalker 仓库路径（数字人功能必填） |
| `SADTALKER_PYTHON` | `python` | SadTalker 专属 Python 3.8 解释器路径（Windows 必填） |
| `STATIC_BASE_URL` | `http://localhost:8000` | 返回给前端的静态资源基础 URL |

准备角色参考图（数字人功能需要）：

将 `yiping-frontend/resource/角色剧照/` 下的图片复制到 `yiping-backend/resource/portraits/`，并按下表重命名：

| 原文件名 | 重命名为 |
|---------|---------|
| 甄嬛剧照.jpg | zhenhuan.jpg |
| 华妃剧照.jpg | huafei.jpg |
| 宜修剧照.jpg | yixiu.jpg |
| 眉庄剧照.jpg | meizhuang.jpg |
| 安陵容剧照.jpg | anlinrong.jpg |
| 苏培盛剧照.jpg | supeisheng.jpg |
| 叶澜依剧照.jpg | yelanyi.jpg |
| 崔槿汐剧照.jpg | cuijinxi.jpg |
| 温实初剧照.jpeg | wensichu.jpg |
| 浣碧剧照.jpg | huanbi.jpg |
| 皇上剧照.jpg | huangshang.jpg |
| 果郡王剧照.jpg | guojunwang.jpg |

准备 mock 音频（mock 模式需要）：

在 `yiping-backend/static/audio/` 放一个名为 `mock_silence.wav` 的音频文件（16kHz 单声道 WAV）。

启动服务：

```bash
uvicorn main:app --reload --port 8000
```

访问 `http://localhost:8000/docs` 可查看 Swagger 接口文档。

---

## 三、配置 SadTalker（数字人功能）

> 如暂不需要数字人视频，可跳过此节。未配置时 `/digital-human` 接口返回 `video_url: null`，前端自动降级显示静态剧照。

### 1. 克隆仓库并安装依赖

SadTalker 需要独立的 Python 3.8 环境（与主后端隔离）：

```powershell
# 在项目根目录执行
git clone https://github.com/OpenTalker/SadTalker.git
cd SadTalker\SadTalker

uv venv --python 3.8 .venv
.venv\Scripts\activate

# lmdb 2.x 与 Python 3.8 不兼容，先单独安装旧版
uv pip install "lmdb==1.4.1" --only-binary :all:
uv pip install -r requirements.txt
```

### 2. 下载预训练模型权重（约 3–4 GB）

Windows 不支持官方的 bash 下载脚本，手动从以下任一地址下载后按目录结构放置：

| 资源 | 下载地址 |
|------|---------|
| 预训练模型 checkpoints | 百度云盘：https://pan.baidu.com/s/1kb1BCPaLOWX1JJb9Czbn6w 密码：`sadt` |
| 预训练模型 checkpoints（备用） | GitHub Releases：https://github.com/OpenTalker/SadTalker/releases |
| GFPGAN 离线补丁 gfpgan/ | 百度云盘：https://pan.baidu.com/s/1P4fRgk9gaSutZnn8YW034Q 密码：`sadt` |

解压后确保目录结构为：

```
SadTalker/SadTalker/
├── checkpoints/
│   ├── mapping_00109-model.pth.tar
│   ├── mapping_00229-model.pth.tar
│   ├── SadTalker_V0.0.2_256.safetensors
│   └── SadTalker_V0.0.2_512.safetensors
└── gfpgan/
    └── weights/
        ├── alignment_WFLW_4HG.pth
        ├── detection_Resnet50_Final.pth
        ├── GFPGANv1.4.pth
        └── parsing_parsenet.pth
```

### 3. 配置 .env

在 `yiping-backend/.env` 中填入 SadTalker 路径：

```env
SADTALKER_PATH=../SadTalker/SadTalker
SADTALKER_PYTHON=D:/path/to/SadTalker/SadTalker/.venv/Scripts/python.exe
```

`SADTALKER_PYTHON` 填 SadTalker 专属 Python 3.8 虚拟环境的解释器绝对路径，避免与主后端 Python 环境冲突。

---

## 四、接入外部模块（ASR + LLM + TTS）

外部模块就绪后，修改 `yiping-backend/.env`：

```env
USE_MOCK=false
USE_MOCK_ASR=false
LLM_SERVICE_URL=http://localhost:8001
TTS_SERVICE_URL=http://localhost:8002
```

接口规范见 [`docs/外部模块接口规范.md`](docs/外部模块接口规范.md)。

---

## 五、完整启动（所有模块就绪后）

打开四个终端分别执行：

```bash
# 终端1：主后端
cd yiping-backend
uvicorn main:app --reload --port 8000
```

```bash
# 终端2：ASR + LLM 模块
cd xiao-asr_llm
uvicorn main:app --reload --port 8001
```

```bash
# 终端3：GPT-SoVITS TTS 模块
cd gpt-sovits-service
uvicorn main:app --reload --port 8002
```

```bash
# 终端4：前端
cd yiping-frontend
npm run dev
```

浏览器访问 `http://localhost:5173` 即可使用完整功能。

---

## 目录结构

```
/
├── yiping-frontend/     # React 前端
├── yiping-backend/      # FastAPI 主后端
├── xiao-asr_llm/        # 模块A：ASR + LLM 对话生成
├── gpt-sovits-service/  # 模块B：GPT-SoVITS 语音合成
├── SadTalker/           # 数字人（克隆后生成）
└── docs/
    ├── 后端设计文档.md
    └── 外部模块接口规范.md
```
