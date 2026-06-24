# CosyVoice3 微调填坑记录

> 项目：甄嬛传 14 角色语音克隆数据集 → CosyVoice3-0.5B SFT 微调
> 服务器：AutoDL RTX 4080 SUPER 单卡
> 日期：2026-06-08

---

## 一、数据从处理服务器传到训练服务器

### 1.1 打包

在处理服务器（gpufree-container）上：

```bash
cd /root/gpufree-data/VIP大作业

# 无压缩打包（WAV 不压缩，gzip 白费时间）
tar cf cosyvoice_data.tar data/cosyvoice_train/ data/segments/
# 约 13GB，15 分钟
```

### 1.2 传输

```bash
# 服务器间对传（不经过本地网络）
scp -P 28281 cosyvoice_data.tar root@connect.bjb1.seetacloud.com:/root/autodl-tmp/
```

### 1.3 解压后修复路径

`wav.scp` 里的音频路径是旧服务器的绝对路径 `/root/gpufree-data/VIP大作业/data/segments/...`，新服务器路径不同，需要修正：

```bash
cd /root/autodl-tmp
tar xf cosyvoice_data.tar

# 替换 wav.scp 中的路径
sed -i 's|/root/gpufree-data/VIP大作业|/root/autodl-tmp|g' \
  data/cosyvoice_train/train/wav.scp \
  data/cosyvoice_train/dev/wav.scp
```

### 1.4 删除 segments（Parquet 已自包含音频）

```bash
rm -rf data/segments/
rm -f cosyvoice_data.tar
```

---

## 二、环境安装

### 2.1 重要教训

**严格按 README 安装，不要随便 pip install 额外包。**

CosyVoice3 的正确安装方式：

```bash
conda create -n cosyvoice -y python=3.10
conda activate cosyvoice
cd CosyVoice

# 使用项目提供的 requirements_no_whisper.txt（Whisper 仅英文需要）
pip install -r requirements_no_whisper.txt \
  -i https://mirrors.aliyun.com/pypi/simple/ \
  --trusted-host=mirrors.aliyun.com
```

### 2.2 必须用内置 Matcha-TTS

`cosyvoice3.yaml` 引用了 `matcha.utils.audio.mel_spectrogram`，必须用项目内置的 `third_party/Matcha-TTS`，**不能** `pip install matcha-tts`（会上把 PyTorch 从 2.3.1 升级到 2.12.0，全部崩坏）。

```bash
cd CosyVoice/third_party/Matcha-TTS
pip install -e . --no-deps   # --no-deps 防止它拉 PyTorch 2.12
cd /root/autodl-tmp/CosyVoice
```

依赖链缺少的包单独补：

```bash
pip install setuptools==69.5.1 -i https://mirrors.aliyun.com/pypi/simple/
pip install optuna hydra-optuna-sweeper tiktoken -i https://mirrors.aliyun.com/pypi/simple/
```

### 2.3 setuptools 版本问题

新版 setuptools 移除了 `pkg_resources`，而 lightning 库用到了它。需要降级：

```bash
pip install setuptools==69.5.1
```

### 2.4 Python 路径

训练需要把 CosyVoice 和 Matcha-TTS 加入 PYTHONPATH：

```bash
export PYTHONPATH="/root/autodl-tmp/CosyVoice:/root/autodl-tmp/CosyVoice/third_party/Matcha-TTS:$PYTHONPATH"
```

---

## 三、代码修改（全是坑）

### 3.1 修复 `cosyvoice/utils/executor.py`

**问题**：`train_one_epoc` 函数在循环结束后调用 `cv()`，但 `info_dict["tag"]` 只在循环内设置。如果 DataLoader 为空（比如路径错误导致数据加载失败），循环不执行，`cv()` 访问 `info_dict["tag"]` 触发 `KeyError`。

**修复**：在 for 循环前加一行（本地改好 SCP 上传）：

```python
        with model_context():
            info_dict["tag"] = "TRAIN"    # ← 加这行
            for batch_idx, batch_dict in enumerate(train_data_loader):
```

**SCP 上传**：
```powershell
scp -P 28281 "E:\BUPT\github\tts_new\CosyVoice\cosyvoice\utils\executor.py" root@connect.bjb1.seetacloud.com:/root/autodl-tmp/CosyVoice/cosyvoice/utils/executor.py
```

### 3.2 修复 `cosyvoice/dataset/processor.py`

**问题**：顶部 `import whisper` 在无 Whisper 环境下崩溃。CosyVoice3 用 Qwen tokenizer，不需要 Whisper。

**修复**：
```bash
sed -i 's/^import whisper$/try:\n    import whisper\nexcept ImportError:\n    whisper = None/' cosyvoice/dataset/processor.py
```

### 3.3 修复 `cosyvoice/tokenizer/tokenizer.py`

**问题**：`from whisper.tokenizer import Tokenizer` 在无 Whisper 环境下崩溃。

**修复**：
```bash
sed -i 's/^from whisper.tokenizer import Tokenizer$/try:\n    from whisper.tokenizer import Tokenizer\nexcept ImportError:\n    Tokenizer = None/' cosyvoice/tokenizer/tokenizer.py
```

### 3.4 修复 `cosyvoice/cli/frontend.py`

**问题**：`import whisper` 在无 Whisper 环境下崩溃。

**修复**：
```bash
sed -i 's/^import whisper$/try:\n    import whisper\nexcept ImportError:\n    whisper = None/' cosyvoice/cli/frontend.py
```

---

## 四、配置文件

### 4.1 创建 SFT 配置

基于 CosyVoice3 预训练配置修改：

```bash
cd /root/autodl-tmp/CosyVoice
cp pretrained_models/Fun-CosyVoice3-0.5B/cosyvoice3.yaml conf/zhenhuan_sft.yaml

# 微调关键参数
sed -i 's/lr: 0.001/lr: 1e-5/' conf/zhenhuan_sft.yaml       # 学习率降 100 倍
sed -i 's/scheduler: warmuplr/scheduler: constantlr/' conf/zhenhuan_sft.yaml  # 恒定学习率
sed -i 's/max_epoch: 200/max_epoch: 20/' conf/zhenhuan_sft.yaml               # 微调轮数
sed -i 's/use_spk_embedding: False/use_spk_embedding: True/' conf/zhenhuan_sft.yaml  # 启用说话人声纹
sed -i 's/max_frames_in_batch: 2000/max_frames_in_batch: 800/' conf/zhenhuan_sft.yaml  # 单卡 16G 减 batch
```

### 4.2 修复 Qwen 路径

`cosyvoice3.yaml` 中 `qwen_pretrain_path: ''` 为空，需要指向预训练模型中的 Qwen 子目录：

```bash
sed -i "s|qwen_pretrain_path: ''|qwen_pretrain_path: 'pretrained_models/Fun-CosyVoice3-0.5B/CosyVoice-BlankEN'|" conf/zhenhuan_sft.yaml
```

---

## 五、data.list 路径问题

### 5.1 路径必须是相对路径

`data.list` 中的 parquet 路径被训练代码拼接当前目录。如果路径是 `/root/autodl-tmp/...`（绝对路径），会导致 `/root/autodl-tmp/CosyVoice/root/autodl-tmp/...` 错误拼接。

**正确做法**：用相对路径，从 CosyVoice 目录往外指：

```bash
# data.list 内容示例（相对于 CosyVoice 目录）
../data/cosyvoice_train/train/parquet/parquet_000000000.tar
```

### 5.2 修复命令

```bash
sed -i 's|/root/autodl-tmp/||g' ../data/cosyvoice_train/train.data.list ../data/cosyvoice_train/dev.data.list
sed -i 's|data/cosyvoice|../data/cosyvoice|g' ../data/cosyvoice_train/train.data.list ../data/cosyvoice_train/dev.data.list
```

---

## 六、正式训练命令

```bash
cd /root/autodl-tmp/CosyVoice
conda activate cosyvoice
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
  --num_workers 2 \
  --use_amp
```

三个模型依次训练（llm → flow → hifigan），训练完成后模型平均和导出。

---

## 七、问题速查表

| 错误 | 原因 | 解决 |
|------|------|------|
| `KeyError: 'tag'` | executor.py 在空 DataLoader 时未设 tag | 在 for 循环前加 `info_dict["tag"] = "TRAIN"` |
| `No module named 'pkg_resources'` | setuptools 太新 | `pip install setuptools==69.5.1` |
| `No module named 'matcha'` | 没用内置 Matcha | 装 `third_party/Matcha-TTS --no-deps` |
| torch 被升级到 2.12 | `pip install matcha-tts` 拉公网版 | 必须用内置版 + `--no-deps` |
| `ImportError: torch.library has no attribute 'register_fake'` | torch 2.12 与 torchvision 不兼容 | 降回 `torch==2.3.1 torchaudio==2.3.1` |
| parquet 文件找不到 | data.list 路径不对 | 改为相对于 CosyVoice 目录的路径 |
| `No module named 'whisper'` | 多个文件 import whisper | sed 改为 try/except 包裹 |
| `No module named 'tiktoken'` | tokenizer 依赖未声明 | `pip install tiktoken` |
| `No module named 'torchcodec'` | torchaudio 2.11+ 需要 FFmpeg | `apt-get install ffmpeg` 或降 torchaudio |
| `AttributeError: 'ProcessGroup' has no attribute 'options'` | PyTorch 版本不兼容 | 装对版本 torch==2.3.1+cu121 |
