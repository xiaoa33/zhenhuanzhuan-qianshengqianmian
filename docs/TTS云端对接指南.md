# TTS 云端对接指南

CosyVoice 部署在 AutoDL 云端，本地通过 SSH 隧道调用。

## 架构

```
前端 :5173  →  yiping-backend :8000  →  SSH隧道 :8002  →  云端 TTS :8003
                  │                       localhost:8002       CosyVoice
                  │                       → cloud:8003         14角色
                  └── LLM :8001 (队友模块，就绪前用 mock)
```

## 启动步骤

打开 4 个终端：

### 终端1 — 云端 TTS 服务

```bash
ssh -p 28281 root@connect.bjb1.seetacloud.com

# 进去后
conda activate cosyvoice
cd /root/autodl-tmp

# 全功能模式（情绪控制 + 精细控制 + 跨语言）
python tts_server_zhz.py --port 8003 --preload

# 纯 zero-shot 模式（音色最像，不加情绪控制）
python tts_server_zhz.py --port 8003 --preload --no-emotion
```

> `--no-emotion`：LLM 仍然正常传 emotion 字段，但 TTS 全部走 zero_shot。API 接口不变，随时可切换。
>
> 若端口被占：`python tts_server_zhz.py --port 8004 --preload`（隧道端口跟着改即可）。

### 终端2 — SSH 隧道（本地）

```bash
ssh -L 8002:localhost:8003 -p 28281 root@connect.bjb1.seetacloud.com
ssh -L 8002:localhost:8003 -p 40916 root@connect.bjb1.seetacloud.com（新服务器）
ssh -p 11755 root@connect.bjb2.seetacloud.com
ssh -L 8002:localhost:8003 -p 11755 root@connect.bjb2.seetacloud.com（最新服务器）
```

> 格式：`-L 本地端口:localhost:云端端口`。保持运行不关。  
> 验证：浏览器打开 `http://localhost:8002/docs`，能看到 Swagger 页面即通。

### 终端3 — 后端

```bash
cd yiping-backend
uvicorn main:app --reload --port 8000
```

### 终端4 — 前端

```bash
cd yiping-frontend
npm install   # 仅首次
npm run dev
```

浏览器访问 `http://localhost:5173`。

## 上传/更新 TTS 代码

```bash
scp -P 28281 "VIP大作业\scripts\tts_server_zhz.py" root@connect.bjb1.seetacloud.com:/root/autodl-tmp/
```

上传后云端重启 TTS 服务即可。

## .env 关键配置

```env
USE_MOCK=true          # LLM 队友未就绪时用 mock
USE_MOCK_TTS=false     # TTS 走真实云端合成
TTS_SERVICE_URL=http://localhost:8002
```

## 角色对照

| character_id | 角色 | CosyVoice spk |
|---|---|---|
| zhenhuan | 甄嬛 | 甄嬛 |
| huafei | 华妃 | 华妃 |
| yixiu | 宜修(皇后) | 皇后 |
| meizhuang | 沈眉庄 | 沈眉庄 |
| anlinrong | 安陵容 | 安陵容 |
| supeisheng | 苏培盛 | 苏培盛 |
| yelanyi | 叶澜依 | 叶澜依 |
| cuijinxi | 崔槿汐 | 崔槿汐 |
| wensichu | 温实初 | 温实初 |
| huanbi | 浣碧 | 浣碧 |
| huangshang | 皇上 | 皇上 |
| guojunwang | 果郡王 | 果郡王 |
