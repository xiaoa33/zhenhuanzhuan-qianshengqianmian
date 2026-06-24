# CosyVoice3 微调与部署说明

> 本文是 CosyVoice3 从克隆、环境搭建、SFT 微调，到 Zero-shot 注册与 TTS 服务部署的完整操作手册。
> 踩坑细节另见同目录 [`CosyVoice3微调填坑记录.md`](CosyVoice3微调填坑记录.md)。

---

## 一、克隆 CosyVoice 与下载模型

### 1.1 克隆官方仓库

```bash
git clone https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice
```

仓库地址：https://github.com/FunAudioLLM/CosyVoice （阿里 FunAudioLLM 团队官方实现）

### 1.2 下载预训练模型

本项目最终微调用的是 **CosyVoice3-0.5B**：

```bash
mkdir -p pretrained_models
python -c "
from modelscope import snapshot_download
snapshot_download('iic/Fun-CosyVoice3-0.5B', local_dir='pretrained_models/Fun-CosyVoice3-0.5B')
"
```

模型页面：https://www.modelscope.cn/models/iic/Fun-CosyVoice3-0.5B

> 注：数据 Parquet 导出阶段（`siting_data_prepare/scripts/step5_export_parquet.sh`）用的是早期 `iic/CosyVoice-300M`，微调阶段升级到 `Fun-CosyVoice3-0.5B`。

---

## 二、环境搭建

```bash
conda create -n cosyvoice -y python=3.10
conda activate cosyvoice

pip install -r requirements_no_whisper.txt \
  -i https://mirrors.aliyun.com/pypi/simple/ \
  --trusted-host=mirrors.aliyun.com

# 必须用内置 Matcha-TTS，--no-deps 防止把 torch 升到 2.12
cd third_party/Matcha-TTS
pip install -e . --no-deps
cd ..

# 补缺失依赖
pip install setuptools==69.5.1
pip install optuna hydra-optuna-sweeper tiktoken

export PYTHONPATH="$(pwd):$(pwd)/third_party/Matcha-TTS:$PYTHONPATH"
```

⚠️ 千万**不要** `pip install matcha-tts`（公网版会把 PyTorch 从 2.3.1 拉到 2.12.0，环境全崩）。

---

## 三、SFT 微调

### 3.1 数据准备

数据来自 `siting_data_prepare/` 的 Pipeline 产物：

- `step4_build_kaldi.py` → CosyVoice Kaldi 格式（wav.scp/text/utt2spk/spk2utt/instruct）
- `step5_export_parquet.sh` → 训练用 Parquet（train 95% / dev 5%）

### 3.2 创建 SFT 配置

```bash
cp pretrained_models/Fun-CosyVoice3-0.5B/cosyvoice3.yaml conf/zhenhuan_sft.yaml

sed -i 's/lr: 0.001/lr: 1e-5/' conf/zhenhuan_sft.yaml
sed -i 's/scheduler: warmuplr/scheduler: constantlr/' conf/zhenhuan_sft.yaml
sed -i 's/max_epoch: 200/max_epoch: 20/' conf/zhenhuan_sft.yaml
sed -i 's/use_spk_embedding: False/use_spk_embedding: True/' conf/zhenhuan_sft.yaml
sed -i 's/max_frames_in_batch: 2000/max_frames_in_batch: 800/' conf/zhenhuan_sft.yaml
sed -i "s|qwen_pretrain_path: ''|qwen_pretrain_path: 'pretrained_models/Fun-CosyVoice3-0.5B/CosyVoice-BlankEN'|" conf/zhenhuan_sft.yaml
```

### 3.3 修复 data.list 路径

```bash
sed -i 's|/root/autodl-tmp/||g' ../data/cosyvoice_train/train.data.list ../data/cosyvoice_train/dev.data.list
sed -i 's|data/cosyvoice|../data/cosyvoice|g' ../data/cosyvoice_train/train.data.list ../data/cosyvoice_train/dev.data.list
```

### 3.4 训练命令

```bash
export CUDA_VISIBLE_DEVICES="0"
export PYTHONPATH="/root/autodl-tmp/CosyVoice:/root/autodl-tmp/CosyVoice/third_party/Matcha-TTS:$PYTHONPATH"

torchrun --nnodes=1 --nproc_per_node=1 \
  cosyvoice/bin/train.py \
  --config conf/zhenhuan_sft.yaml \
  --train_data ../data/cosyvoice_train/train.data.list \
  --cv_data ../data/cosyvoice_train/dev.data.list \
  --model llm \
  --checkpoint pretrained_models/Fun-CosyVoice3-0.5B/llm.pt \
  --onnx_path pretrained_models/Fun-CosyVoice3-0.5B \
  --model_dir exp/zhenhuan/llm \
  --num_workers 2 --use_amp
```

三个模型依次训练（llm → flow → hifigan），训练完成后模型平均和导出。

### 3.5 结果与决策

| Epoch | Train Loss | CV Loss |
|---|---|---|
| 0 | 1.69 | 3.59 |
| 3 | 1.08 | **4.05** ⚠️ |
| 4 | 0.86 | **4.59** ⚠️ |

Epoch 3 起 CV Loss 反转上升，严重过拟合。根因：14 角色数据极度不均衡（甄嬛 29.5% vs 温实初 2.0%），模型容量倾斜给大角色。**放弃 SFT，转向 Zero-shot。**

---

## 四、Zero-shot Speaker 注册

### 4.1 前置数据

需要 `siting_data_prepare/data/zero_shot_data/` 的 127 条精选参考音频（14 角色，单独放网盘，见该文件夹 README）。

### 4.2 注册 14 角色

```bash
python scripts/register_speakers.py
```

每个角色注册格式：

```python
cosyvoice.add_zero_shot_spk(
    f"You are a helpful assistant.<|endofprompt|>{prompt_text}",
    wav_path,   # 5~10s 高质量角色原声
    spk_id      # 如 "华妃"
)
cosyvoice.save_spkinfo()  # 持久化到 spk2info.pt
```

### 4.3 注册 16 情绪 Speaker

```bash
python scripts/register_emotion_speakers_v2.py
```

- 4 角色（甄嬛/华妃/皇上/皇后）× 4 情绪（喜悦/愤怒/悲伤/平静）= 16 个情绪 Speaker
- v2 改进：用 FunASR 自动转写每条情绪样本，保证 prompt_text 与音频内容一致（v1 固定文本会降低质量）
- 情绪音频从 76 集原声手工筛选，共 107 段

最终 `spk2info.pt` 含 **30 个 Speaker**。

---

## 五、推理与服务部署

### 5.1 推理 CLI

```bash
# 基础推理
python scripts/infer.py --text "贱人就是矫情" --spk huafei

# vLLM 加速
python scripts/infer.py --text "..." --spk huafei --vllm

# 流式输出
python scripts/infer.py --text "..." --spk huafei --stream

# 交互式对话（角色名 + 台词）
python scripts/infer.py --dialogue
```

### 5.2 TTS 服务

```bash
python scripts/tts_server_zhz.py  # 默认监听 :8003
```

端点：

| 端点 | 功能 |
|---|---|
| `POST /synthesize` | 非流式合成 |
| `POST /synthesize/stream` | SSE 流式合成（首音延迟 ~1.5s，RTF 0.5~0.8） |
| `GET /` | 内嵌 Web 演示页 |

**智能路由**（请求带 character_id + emotion）：

```
EMOTION_SPEAKER_MAP[(character, emotion)] → 命中情绪 Speaker → zero_shot
                                          ↓ 未命中
副语言 token（[breath][laughter]）→ 跨语种 → instruct2 → zero-shot
```

**源码 bug 修复**：CosyVoice3 的 `instruct2` 默认忽略 `zero_shot_spk_id`，通过 monkey-patch `CosyVoiceFrontEnd.frontend_instruct2` 修复。

### 5.3 与前端对接（SSH 隧道）

```
AutoDL 云端 tts_server (:8003)
    │ SSH 隧道 (:8002→:8003)
    ▼
本地 yiping-backend (:8000) /synthesize/stream
    │ SSE 推送 {i, audio(base64), dur}
    ▼
前端 Web Audio API 排队播放
```

---

## 六、算力与服务器

- **数据处理 + Parquet 导出**：Gpufree 云 GPU
- **CosyVoice 微调 + Zero-shot 推理服务**：AutoDL（RTX 4080 SUPER 单卡）
- **数据传输**：服务器间 scp 对传（详见填坑记录第一章）
- 本项目数据处理与模型微调全程租用云 GPU。
