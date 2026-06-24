# CosyVoice 微调与 TTS 服务部署（个人工作存档）

> 本文件夹汇总**我本人**负责的 CosyVoice 部分：从云端克隆 CosyVoice3、下载预训练模型、SFT 微调实验，到最终的 Zero-shot Speaker 注册与完整 TTS 推理服务部署。
>
> 对应 PPT 汇报中的：**CosyVoice 微调实验（8 页）+ Zero-shot 与情绪 Speaker（9 页）+ TTS 服务部分**。
>
> 数据集构建部分见姊妹文件夹 [`../siting_data_prepare/`](../siting_data_prepare/)。

---

## 一、技术路线

```
CosyVoice3-0.5B 预训练模型（ModelScope 下载）
    │
    ├─ 路线 A：SFT 微调（14 角色联合）
    │     └─ ❌ Epoch 3 起过拟合（CV Loss 3.59→4.59），数据不均衡致小角色崩盘，放弃
    │
    └─ 路线 B：Zero-shot（最终方案）✅
          ├─ 14 角色 Zero-shot 注册（register_speakers.py）
          ├─ 16 情绪 Speaker 注册（register_emotion_speakers_v2.py）
          └─ TTS 服务部署（tts_server_zhz.py，30 个 Speaker）
```

**为什么 CosyVoice 效果更好**：Zero-shot 复用预训练模型的强泛化能力，无需训练、即插即用；音色还原度和发音清晰度实测均优于 GPT-SoVITS 微调和 CosyVoice SFT 微调，作为系统主力 TTS 引擎。

---

## 二、目录结构

```
siting_cosyvoice_tts/
├── README.md                          ← 本文件（clone + setup + 微调 + 部署总览）
├── scripts/                           ← 微调相关与推理服务代码
│   ├── register_speakers.py           ← 14 角色 Zero-shot 注册
│   ├── register_emotion_speakers.py   ← 情绪 Speaker 注册 v1
│   ├── register_emotion_speakers_v2.py← 情绪 Speaker 注册 v2（ASR 对齐文本）
│   ├── infer.py                       ← 推理 CLI（vLLM/流式/对话）
│   └── tts_server_zhz.py              ← 完整 TTS 服务（FastAPI，30 Speaker）
└── docs/
    ├── CosyVoice3微调与部署说明.md     ← clone、setup、微调训练、服务部署全流程
    ├── CosyVoice3微调填坑记录.md       ← 微调踩坑全过程与问题速查表
    └── training_llm_log               ← LLM 训练阶段完整日志（原始输出）
```

---

## 三、从哪里 clone CosyVoice

### 官方仓库

```bash
git clone https://github.com/FunAudioLLM/CosyVoice.git
```

- 仓库地址：https://github.com/FunAudioLLM/CosyVoice
- 这是阿里 FunAudioLLM 团队的官方实现，本项目用的是 **CosyVoice3-0.5B** 分支代码。

### 预训练模型（ModelScope 下载）

```bash
cd CosyVoice
mkdir -p pretrained_models
python -c "
from modelscope import snapshot_download
snapshot_download('iic/Fun-CosyVoice3-0.5B', local_dir='pretrained_models/Fun-CosyVoice3-0.5B')
"
```

- 模型页面：https://www.modelscope.cn/models/iic/Fun-CosyVoice3-0.5B
- ⚠️ 注意：早期用的是 `iic/CosyVoice-300M`（旧版），微调实验最终用的是 `Fun-CosyVoice3-0.5B`。

---

## 四、环境搭建（Setup）

> 详细踩坑过程见 [`docs/CosyVoice3微调填坑记录.md`](docs/CosyVoice3微调填坑记录.md)。

```bash
# 1. 创建环境
conda create -n cosyvoice -y python=3.10
conda activate cosyvoice
cd CosyVoice

# 2. 安装依赖（用项目提供的无 whisper 版）
pip install -r requirements_no_whisper.txt \
  -i https://mirrors.aliyun.com/pypi/simple/ \
  --trusted-host=mirrors.aliyun.com

# 3. 必须用内置 Matcha-TTS（--no-deps 防止它把 torch 升到 2.12）
cd third_party/Matcha-TTS
pip install -e . --no-deps
cd ..

# 4. 补缺失依赖
pip install setuptools==69.5.1 -i https://mirrors.aliyun.com/pypi/simple/
pip install optuna hydra-optuna-sweeper tiktoken

# 5. 设置 PYTHONPATH
export PYTHONPATH="$(pwd):$(pwd)/third_party/Matcha-TTS:$PYTHONPATH"
```

### 关键坑点（详见填坑记录）

| 坑 | 解法 |
|---|---|
| `pip install matcha-tts` 把 torch 升到 2.12 全崩 | 必须用内置 `third_party/Matcha-TTS` + `--no-deps` |
| 新版 setuptools 移除 `pkg_resources` | 降级 `setuptools==69.5.1` |
| 多个文件 `import whisper` 崩溃 | sed 改为 try/except 包裹 |
| `executor.py` 空 DataLoader 时 KeyError | for 循环前加 `info_dict["tag"] = "TRAIN"` |
| `qwen_pretrain_path` 为空 | 指向 `Fun-CosyVoice3-0.5B/CosyVoice-BlankEN` |
| `data.list` 绝对路径拼接错误 | 改为相对路径（`../data/...`） |

---

## 五、SFT 微调实验（最终放弃，保留实验记录）

基于 `siting_data_prepare/scripts/step4_build_kaldi.py` 生成的 Kaldi 格式数据 + `step5_export_parquet.sh` 导出的 Parquet，进行 SFT 微调。

```bash
torchrun --nnodes=1 --nproc_per_node=1 \
  cosyvoice/bin/train.py \
  --config conf/zhenhuan_sft.yaml \
  --train_data ../data/cosyvoice_train/train.data.list \
  --cv_data ../data/cosyvoice_train/dev.data.list \
  --model llm \
  --checkpoint pretrained_models/Fun-CosyVoice3-0.5B/llm.pt \
  --model_dir exp/zhenhuan/llm \
  --num_workers 2 --use_amp
```

**SFT 配置**（基于预训练 yaml 修改）：

| 参数 | 值 |
|---|---|
| 学习率 | 1e-5（预训练的 1/100） |
| 调度器 | ConstantLR |
| 最大 Epoch | 20（实际跑到 5 轮停止） |
| max_frames_in_batch | 800（单卡 16G） |
| use_spk_embedding | True |

**结果**：Epoch 3 起 CV Loss 反转上升（3.59→4.59），严重过拟合。根因是 14 角色数据极度不均衡（甄嬛 29.5% vs 温实初 2.0%），模型把容量分给大角色、系统性忽视小角色。果断转向 Zero-shot。

完整配置生成与训练命令见 [`docs/CosyVoice3微调与部署说明.md`](docs/CosyVoice3微调与部署说明.md)。

---

## 六、Zero-shot 与情绪 Speaker 注册

> 前置：需要 `siting_data_prepare/data/zero_shot_data/` 的 127 条精选参考音频（该数据单独放网盘，见该文件夹说明）。

```bash
# 1. 注册 14 角色 Zero-shot Speaker
python scripts/register_speakers.py
# → 生成 spk2info.pt（含 14 个基础角色声纹）

# 2. 注册 16 情绪 Speaker（4 角色 × 4 情绪）
python scripts/register_emotion_speakers_v2.py
# → spk2info.pt 追加 16 个情绪 Speaker
# v2 用 FunASR 自动转写每条情绪样本，保证 prompt_text 与音频一致
```

最终 `spk2info.pt` 含 **30 个 Speaker**：14 基础 + 16 情绪。

---

## 七、TTS 服务部署

```bash
# 启动 TTS 服务（FastAPI，默认 :8003）
python scripts/tts_server_zhz.py
```

服务能力：

| 端点 | 功能 |
|---|---|
| `POST /synthesize` | 非流式合成 |
| `POST /synthesize/stream` | SSE 流式合成（首音延迟 ~1.5s） |
| 内嵌 `/` | Web 演示页 |

**核心亮点**：
- **智能路由**：情绪 Speaker（Zero-shot，音色最佳）→ 副语言 token（`[breath][laughter]`）→ 跨语种 → instruct2 → Zero-shot
- **源码 bug 修复**：monkey-patch 修复了 CosyVoice3 `instruct2` 忽略 `zero_shot_spk_id` 的 bug
- **推理 CLI**：`infer.py` 支持 vLLM 加速、流式输出、交互式对话

部署细节（SSH 隧道、与 yiping-backend 对接）见 [`docs/CosyVoice3微调与部署说明.md`](docs/CosyVoice3微调与部署说明.md)。

---

## 八、云端部署说明

本项目数据处理、模型微调、TTS 推理**均在云端 GPU 完成**：

- **服务器**：AutoDL（RTX 4080 SUPER 单卡），数据构建阶段另用 Gpufree
- **数据传输**：服务器间 scp 对传（不经本地网络），见填坑记录第一章
- **本地对接**：SSH 隧道穿透（:8002→:8003），本地 yiping-backend :8000 路由调用

本项目数据处理与模型微调全程租用云 GPU。
