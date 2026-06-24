# yiping-backend

甄嬛传·千声千面 后端服务，基于 FastAPI，为前端提供对话、语音合成、数字人视频生成等接口。

## 快速启动

```bash
cd yiping-backend
pip install -r requirements.txt

# 复制并编辑环境变量
cp .env.example .env

# 准备角色参考图（数字人功能需要）
# 将 yiping-frontend/resource/角色剧照/ 下的图片复制到 resource/portraits/
# 并按下表重命名：
#   甄嬛剧照.jpg    → zhenhuan.jpg
#   华妃剧照.jpg    → huafei.jpg
#   宜修剧照.jpg    → yixiu.jpg
#   眉庄剧照.jpg    → meizhuang.jpg
#   安陵容剧照.jpg  → anlinrong.jpg
#   苏培盛剧照.jpg  → supeisheng.jpg
#   叶澜依剧照.jpg  → yelanyi.jpg
#   崔槿汐剧照.jpg  → cuijinxi.jpg
#   温实初剧照.jpeg → wensichu.jpg
#   浣碧剧照.jpg    → huanbi.jpg
#   皇上剧照.jpg    → huangshang.jpg
#   果郡王剧照.jpg  → guojunwang.jpg

# 准备 mock 音频（mock 模式需要）
# 在 static/audio/ 放一个名为 mock_silence.wav 的音频文件（16kHz 单声道 WAV）

# 启动服务
uvicorn main:app --reload --port 8000
```

访问 http://localhost:8000/docs 可查看 Swagger 接口文档。

---

## 环境变量说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `USE_MOCK` | `true` | `true` 时 /chat、/synthesize、/summary 使用预设数据 |
| `USE_MOCK_ASR` | `false` | `true` 时 /asr 返回固定演示文本 |
| `LLM_SERVICE_URL` | `http://localhost:8001` | xiao-asr_llm 模块地址 |
| `TTS_SERVICE_URL` | `http://localhost:8002` | TTS 语音合成模块地址 |
| `SADTALKER_PATH` | `../SadTalker` | SadTalker 仓库路径 |
| `SADTALKER_PYTHON` | `python` | SadTalker 虚拟环境的 Python 解释器路径（Windows 下需设为 `.venv\Scripts\python.exe` 的绝对路径） |
| `STATIC_BASE_URL` | `http://localhost:8000` | 返回给前端的静态资源基础 URL |

---

## Mock 替换指引

当对应模块就绪后，按以下步骤接入真实实现：

### 接入 LLM 模块（/chat 和 /summary）

文件：`services/llm_client.py`

1. 将 `.env` 中 `USE_MOCK` 改为 `false`
2. 确认 `LLM_SERVICE_URL` 指向正在运行的 xiao-asr_llm 服务
3. 该文件中 `call_generate()` 和 `call_summarize()` 函数已按接口规范调用，无需修改
4. 若 xiao-asr_llm 的接口路径或字段名有差异，在这两个函数中调整

### 接入 ASR 模块（/asr）

文件：`services/asr_client.py`

1. 确认 `LLM_SERVICE_URL` 指向正在运行的 xiao-asr_llm 服务
2. xiao-asr_llm 需实现 `POST /asr`，multipart 字段名为 `audio`
3. 前端录音按钮会调用主后端 `/asr`，识别结果只填入输入框，不会自动发送

### 接入 TTS 语音合成模块（/synthesize）

文件：`services/tts_client.py`

1. 将 `.env` 中 `USE_MOCK` 改为 `false`
2. 确认 `TTS_SERVICE_URL` 指向正在运行的 TTS 服务
3. TTS 服务需返回以下两种格式之一（已自动识别）：
   - `{ "audio_path": "/absolute/path/to/output.wav" }`
   - `{ "audio_base64": "...", "format": "wav" }`
4. 若响应格式不同，在 `call_synthesize()` 函数中修改解析逻辑

GPT-SoVITS 本地服务位于 `../xiao-gpt-sovits`，启动后监听 `8004` 并返回 `{ "audio_path": "..." }`。

### 接入 SadTalker（/digital-human）

文件：`digital_human/sadtalker.py`

1. 克隆 SadTalker 并安装依赖（Windows 需 Python 3.8 虚拟环境）：
   ```powershell
   git clone https://github.com/OpenTalker/SadTalker.git
   cd SadTalker\SadTalker
   uv venv --python 3.8 .venv
   .venv\Scripts\activate
   # lmdb 2.x 与 Python 3.8 不兼容，先单独装预编译旧版
   uv pip install "lmdb==1.4.1" --only-binary :all:
   uv pip install -r requirements.txt
   ```
2. 下载预训练模型权重（约 3-4 GB），**Windows 不支持 bash 脚本**，手动从以下任一地址下载后按目录结构放置：
   - 百度云盘（推荐国内）：https://pan.baidu.com/s/1kb1BCPaLOWX1JJb9Czbn6w 密码：`sadt`
   - GitHub Releases：https://github.com/OpenTalker/SadTalker/releases
   - Google Drive：https://drive.google.com/file/d/1gwWh45pF7aelNP_P78uDJL8Sycep-K7j/view

   GFPGAN 离线补丁（同上渠道）：
   - 百度云盘：https://pan.baidu.com/s/1P4fRgk9gaSutZnn8YW034Q 密码：`sadt`

   下载后解压，确保目录结构为：
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
3. 在 `.env` 中设置：
   ```env
   SADTALKER_PATH=../SadTalker/SadTalker
   SADTALKER_PYTHON=<SadTalker项目路径>/.venv/Scripts/python.exe
   ```
4. 确认 `resource/portraits/` 下有对应角色的参考图
4. `/digital-human` 接口无需 `USE_MOCK` 控制，始终调用 SadTalker；失败时自动返回 `{"video_url": null}`，前端降级显示静态剧照

---

## 文件结构

```
yiping-backend/
├── main.py                      # FastAPI 入口，CORS，路由注册
├── routers/
│   ├── chat.py                  # POST /chat
│   ├── synthesize.py            # POST /synthesize
│   ├── digital_human.py         # POST /digital-human
│   └── summary.py               # POST /summary
├── services/
│   ├── llm_client.py            # 调用 xiao-asr_llm（含 mock 分支）
│   └── tts_client.py            # 调用 TTS 模块（含 mock 分支）
├── digital_human/
│   └── sadtalker.py             # SadTalker subprocess 封装
├── mock/
│   └── mock_data.py             # 12个角色预设回复和总结数据
├── static/
│   ├── audio/                   # 生成/复制的音频文件
│   │   └── mock_silence.wav     # mock 用音频（16kHz 单声道 WAV，需手动放置）
│   └── video/                   # SadTalker 生成的视频文件
├── resource/
│   └── portraits/               # 角色参考图（character_id.jpg）
├── .env.example
├── requirements.txt
└── README.md
```
