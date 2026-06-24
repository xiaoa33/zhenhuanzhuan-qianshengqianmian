# 甄嬛传·千声千面

基于大语言模型与语音合成的甄嬛传角色互动系统，支持 AI 角色对话、情感语音合成与数字人视频生成。

---

## 系统架构

```
前端 React (:5173)
    │
    ▼
yiping-backend FastAPI (:8003)   ← 主后端，负责路由、TTS分发和 SadTalker 调用
    │
    ├── xiao-asr_llm (:8001)     ← 模块A：ASR + LLM 对话生成 + 情绪分析
    ├── CosyVoice TTS (:8002)    ← 队友模块：CosyVoice 语音合成
    └── GPT-SoVITS TTS (:8004)   ← 本机模块：GPT-SoVITS 语音合成
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
VITE_API_BASE_URL=http://localhost:8003
VITE_TTS_ENGINE=gpt_sovits
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
| `TTS_SERVICE_URL` | `http://localhost:8002` | 默认 TTS 地址，当前通常指向 CosyVoice |
| `GPT_SOVITS_SERVICE_URL` | `http://localhost:8004` | GPT-SoVITS 服务地址 |
| `COSYVOICE_SERVICE_URL` | `http://localhost:8002` | CosyVoice 服务地址 |
| `SADTALKER_PATH` | `../SadTalker/SadTalker` | SadTalker 仓库路径（数字人功能必填） |
| `SADTALKER_PYTHON` | `python` | SadTalker 专属 Python 3.8 解释器路径（Windows 必填） |
| `STATIC_BASE_URL` | `http://localhost:8003` | 返回给前端的静态资源基础 URL |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 允许访问主后端的前端地址 |
| `PORT` | `8003` | 主后端端口 |

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
uvicorn main:app --reload --port 8003
```

访问 `http://localhost:8003/docs` 可查看 Swagger 接口文档。

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
GPT_SOVITS_SERVICE_URL=http://localhost:8004
COSYVOICE_SERVICE_URL=http://localhost:8002
STATIC_BASE_URL=http://localhost:8003
```

接口规范见 [`docs/外部模块接口规范.md`](docs/外部模块接口规范.md)。

---

## 五、完整启动（所有模块就绪后）

当前约定端口：

| 服务 | 端口 |
|---|---|
| 前端 | `5173` |
| xiao-asr_llm | `8001` |
| CosyVoice | `8002` |
| yiping-backend | `8003` |
| GPT-SoVITS | `8004` |

### 0. 可选：下载 ASR 模型

如果服务器不能在线下载模型，先手动下载 faster-whisper 模型：

```bash
cd /mnt/sdb/wangxinran/zhangxiao/template/VIP_BigHW
mkdir -p models

hf download Systran/faster-whisper-small \
  --local-dir models/faster-whisper-small
```

然后在 `xiao-asr_llm/.env` 中配置：

```env
ASR_MODEL=/mnt/sdb/wangxinran/zhangxiao/template/VIP_BigHW/models/faster-whisper-small
ASR_DEVICE=cuda
ASR_COMPUTE_TYPE=int8_float16
ASR_LANGUAGE=zh
```

### 1. 启动 ASR + LLM 模块

```bash
cd /mnt/sdb/wangxinran/zhangxiao/template/VIP_BigHW/zhenhuanzhuan-qianshengqianmian/xiao-asr_llm
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 2. 启动 GPT-SoVITS 模块

推荐使用常驻缓存模式，避免每轮重新加载权重：

```bash
cd /mnt/sdb/wangxinran/zhangxiao/template/VIP_BigHW/zhenhuanzhuan-qianshengqianmian/gpt-sovits-service

GSV_BACKEND=persistent GSV_CACHE_SIZE=1 \
  /mnt/sdc/zhangyuxuan/envs/zx_VIP/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8004
```

### 3. 启动或接入 CosyVoice

CosyVoice 维持原来的 `8002`。如果 CosyVoice 队友的服务可以直接访问，在 `yiping-backend/.env` 中配置：

```env
COSYVOICE_SERVICE_URL=http://队友CosyVoice地址:8002
```

如果 CosyVoice 是云端 `8003`，并通过 SSH 隧道接到本机 `8002`：

```bash
ssh -L 8002:localhost:8003 -p 28281 root@connect.bjb1.seetacloud.com
```

然后 `yiping-backend/.env` 中保持：

```env
COSYVOICE_SERVICE_URL=http://localhost:8002
```

### 4. 启动主后端

本机调试：

```bash
cd /mnt/sdb/wangxinran/zhangxiao/template/VIP_BigHW/zhenhuanzhuan-qianshengqianmian/yiping-backend
uvicorn main:app --reload --port 8003
```

多人异地联调：

```bash
cd /mnt/sdb/wangxinran/zhangxiao/template/VIP_BigHW/zhenhuanzhuan-qianshengqianmian/yiping-backend
uvicorn main:app --host 0.0.0.0 --port 8003
```

多人联调时，`yiping-backend/.env` 需要把 `localhost` 改成你的服务器可访问地址，例如：

```env
STATIC_BASE_URL=http://你的校内IP:8003
CORS_ORIGINS=http://你的校内IP:5173
```

临时联调也可以：

```env
CORS_ORIGINS=*
```

### 5. 启动前端

本机调试：

```bash
cd /mnt/sdb/wangxinran/zhangxiao/template/VIP_BigHW/zhenhuanzhuan-qianshengqianmian/yiping-frontend
npm install
npm run dev
```

多人异地联调：

```bash
cd /mnt/sdb/wangxinran/zhangxiao/template/VIP_BigHW/zhenhuanzhuan-qianshengqianmian/yiping-frontend
npm run dev -- --host 0.0.0.0
```

前端 `.env.local` 本机调试：

```env
VITE_API_BASE_URL=http://localhost:8003
VITE_TTS_ENGINE=gpt_sovits
```

多人联调时改成：

```env
VITE_API_BASE_URL=http://你的校内IP:8003
VITE_TTS_ENGINE=gpt_sovits
```

浏览器访问：

```text
http://localhost:5173
```

多人联调时访问：

```text
http://你的校内IP:5173
```

### 6. 启动后验证

在服务器本机执行：

```bash
curl http://localhost:8001/
curl http://localhost:8003/
curl http://localhost:8004/
```

通过主后端测试 GPT-SoVITS：

```bash
curl -X POST http://localhost:8003/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "zhenhuan",
    "text": "本宫今日心情尚可，你倒是有眼力见儿。",
    "emotion": "喜悦",
    "engine": "gpt_sovits"
  }'
```

通过主后端测试 CosyVoice：

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

---

## 六、数据集与模型权重下载

以下数据产物因体积较大，统一上传到百度网盘，不随代码仓库分发：

> **网盘链接**：https://pan.baidu.com/s/1_uacMyl9y5YvrWsh77Mtww?pwd=kcs7
> **提取码**：kcs7

网盘目录结构：

```
甄嬛传千声千面_相关数据/
├── zero_shot_data/           ← 127 条精选参考音频（14 角色子目录）
├── emotion_examples/         ← 107 条情绪参考音频（4 角色 × 4 情绪）
├── 甄嬛传14人物数据.tar      ← 清洗后全量数据集（13,605 段 WAV + Kaldi 元数据）
└── model_weights/            ← （待上传）CosyVoice3-0.5B 微调模型权重
```

| 数据 | 说明 | 使用方式 |
|---|---|---|
| `zero_shot_data/` | 14 角色 Zero-shot 声纹参考音频 | 解压到 `siting_data_prepare/data/zero_shot_data/`，运行 `register_speakers.py` |
| `emotion_examples/` | 4 角色 × 4 情绪参考音频 | 供 `register_emotion_speakers_v2.py` 注册情绪 Speaker |
| `甄嬛传14人物数据.tar` | 13,605 段 WAV + Kaldi 格式 | 解压到 `siting_data_prepare/data/`，用于重训练或转其他格式 |
| `model_weights/`（待上传） | CosyVoice3-0.5B LLM 微调权重 | 解压到 CosyVoice 项目 `exp/zhenhuan/llm/` |

数据处理与模型代码见：
- [`siting_data_prepare/`](siting_data_prepare/) — 数据 Pipeline（UVR5 → ASR → 聚类 → 清洗 → Kaldi/Parquet）
- [`siting_cosyvoice_tts/`](siting_cosyvoice_tts/) — CosyVoice 微调、Zero-shot 注册、TTS 服务部署

---

## 目录结构

```
/
├── yiping-frontend/         # React 前端
├── yiping-backend/          # FastAPI 主后端
├── xiao-asr_llm/            # 模块A：ASR + LLM 对话生成
├── gpt-sovits-service/      # 模块B：GPT-SoVITS 语音合成
├── siting_data_prepare/     # 数据处理 Pipeline（代码 + 文档）
├── siting_cosyvoice_tts/    # CosyVoice 微调与部署（代码 + 文档）
├── SadTalker/               # 数字人（克隆后生成）
└── docs/
    ├── 后端设计文档.md
    └── 外部模块接口规范.md
```
