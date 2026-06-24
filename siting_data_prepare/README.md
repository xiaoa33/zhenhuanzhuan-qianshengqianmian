# 甄嬛传数据集构建（个人工作存档）

> 本文件夹汇总**我本人**负责的**数据工程部分**：从《甄嬛传》76 集原声出发，自主构建 14 角色语音数据集，并导出 CosyVoice 训练所需格式。
>
> 对应 PPT 汇报中的：**数据集构建（4-6 页）**。
>
> CosyVoice 的微调与 TTS 服务部署见姊妹文件夹 [`../siting_cosyvoice_tts/`](../siting_cosyvoice_tts/)。

---

## 一、整体流程

```
76 集 MP3 原声（~80h）
    │  UVR5 人声分离
    ▼
FunASR VAD+ASR → 15,685 段
    │  eres2netv2 声纹提取 + KMeans 聚类(n=30)
    ▼
30 个说话人簇 → 人工标注（每簇抽5条试听）→ 14 角色
    │  4 轮清洗
    ▼
13,605 段 · 14 角色 · 16.7h
    │
    └─ 导出 CosyVoice Kaldi 格式 + Parquet（供 siting_cosyvoice_tts 微调使用）
```

---

## 二、目录结构

```
siting_data_prepare/
├── README.md                  ← 本文件（工作总览）
├── requirements.txt           ← Python 依赖
├── scripts/                   ← 数据处理代码（11 个脚本 + 1 个 README）
│   ├── config.py              ← 全局配置（14角色、模型ID、标注关键词、音频参数）
│   ├── step0_env_check.py     ← 环境检查
│   ├── step1_pipeline.py      ← VAD + ASR
│   ├── step1b_speaker_cluster.py ← 声纹聚类
│   ├── step2_sample_labeling.py  ← 人工标注辅助
│   ├── step3_clean.py         ← 质量过滤
│   ├── step4_build_kaldi.py   ← Kaldi 格式构建
│   ├── step5_export_parquet.sh← Parquet 导出
│   ├── run_all.sh             ← 一键驱动
│   ├── cloud_setup.sh         ← 云端环境初始化
│   └── README.md              ← 脚本索引与快速开始
├── docs/                      ← 文档
│   ├── 数据集构建与训练说明.md    ← Pipeline 设计、训练命令、适配指南
│   └── 甄嬛传14角色语音数据集说明.md
└── data/                      ← 数据产物（⚠️ 实际数据均放网盘）
    ├── zero_shot_data/        ← README.md 说明文件（网盘下载后解压到此处）
    ├── 甄嬛传14人物数据/       ← README.md 说明文件（网盘 tar 解压到此处）
    └── pipeline_results/      ← 人工标注产物（speaker_map.json 等）
```

---

## 三、环境搭建（Setup）

### 3.1 安装依赖

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

依赖含：funasr、modelscope、soundfile、librosa、pydub、tqdm、pandas、scikit-learn、onnxruntime 等。

### 3.2 安装 UVR5 命令行版（人声分离）

```bash
pip install audio-separator -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3.3 模型下载（首次运行自动下载）

Pipeline 用到的模型由 FunASR / ModelScope 自动下载，无需手动操作：

| 模型 | 用途 | 来源 |
|---|---|---|
| FSMN VAD + Paraformer | 语音切分 + ASR 转写 | FunASR（modelscope） |
| eres2netv2 | 声纹特征提取 | FunASR |
| UVR5 mdx_extra_q | 人声分离 | audio-separator |

### 3.4 云端环境（可选）

```bash
bash scripts/cloud_setup.sh   # 一键初始化云端 GPU 环境
```

---

## 四、运行流程

### 4.1 一键运行

```bash
bash scripts/run_all.sh           # 交互模式（人工标注时暂停）
bash scripts/run_all.sh --auto    # 自动模式（跳过人工暂停）
```

### 4.2 分步运行

| 步骤 | 命令 | 产出 |
|---|---|---|
| 0 环境检查 | `python scripts/step0_env_check.py` | — |
| 1 VAD+ASR | `python scripts/step1_pipeline.py` | `all_segments.json` |
| 1b 声纹聚类 | `python scripts/step1b_speaker_cluster.py` | 更新 segments（含 spk_XX） |
| 2 标注 | `python scripts/step2_sample_labeling.py` | `samples_for_labeling.json`（每簇10条） |
| 2 应用标注 | `python scripts/step2_sample_labeling.py --apply-map` | `labeled_segments.json` |
| 3 清洗 | `python scripts/step3_clean.py` | `clean_data.json` |
| 4 Kaldi | `python scripts/step4_build_kaldi.py` | cosyvoice_train/ Kaldi 格式 |
| 5 Parquet | `bash scripts/step5_export_parquet.sh` | 训练用 Parquet |

---

## 五、scripts/ 代码索引

### 数据处理 Pipeline（5 步）

| 脚本 | 功能 |
|---|---|
| `config.py` | **全局配置**：14 角色列表、FunASR 模型 ID、标注关键词字典、音频参数（VAD 2-15s、MIN_RMS 0.003）。整个流程的唯一配置源。 |
| `step0_env_check.py` | 环境检查：Python 版本、依赖、原始 MP3、CosyVoice + ONNX 模型、估算总时长。 |
| `step1_pipeline.py` | **VAD + ASR 核心**：FSMN VAD + Paraformer ASR，字符时间戳合并为句子级片段（>800ms 间隔切分），输出 `all_segments.json`。 |
| `step1b_speaker_cluster.py` | **说话人聚类**：eres2netv2 提取声纹 + KMeans（默认 30 簇）分配 spk_XX。 |
| `step2_sample_labeling.py` | **标注辅助**：每簇随机抽 10 条 + 关键词自动提示；`--apply-map` 应用人工 `speaker_map.json` 生成标注结果。 |
| `step3_clean.py` | **质量过滤**：4 轮——角色过滤 → 文本长度/噪声 → 文本去重 → 音频质检（RMS/时长/削波）。 |
| `step4_build_kaldi.py` | **Kaldi 构建**：转 CosyVoice 格式（wav.scp/text/utt2spk/spk2utt/instruct），含拼音映射与每角色 instruct 语气指令。 |
| `step5_export_parquet.sh` | **Parquet 导出**：调用 CosyVoice 的 embedding/speech_token 提取脚本，生成训练 parquet。 |

### 一键驱动与云端环境

| 脚本 | 功能 |
|---|---|
| `run_all.sh` | 一键驱动 step0→step5，支持 `--auto`（跳过人工暂停）和交互模式。 |
| `cloud_setup.sh` | 云端环境初始化：清华镜像装依赖、克隆 CosyVoice、modelscope 下载模型、GPU 检查。 |

---

## 六、docs/ 文档

| 文档 | 内容 |
|---|---|
| `数据集构建与训练说明.md` | Pipeline 设计、CosyVoice 训练/导出命令、Kaldi 格式规范、数据集统计、GPT-SoVITS 适配指南。 |
| `甄嬛传14角色语音数据集说明.md` | 数据集规格：14 角色、各角色片段统计、文件格式（wav.scp/text/utt2spk/spk2utt/instruct）、16kHz mono PCM 规格。 |

> CosyVoice 微调踩坑记录已移至 [`../siting_cosyvoice_tts/docs/CosyVoice3微调填坑记录.md`](../siting_cosyvoice_tts/docs/CosyVoice3微调填坑记录.md)。

---

## 七、data/ 数据产物

> ⚠️ **76 集 2.8GB 原始 MP3 不在此处**（源素材，非工作产出）。原始位置：`VIP大作业/data/甄嬛传原声_..._MP3/`。

### 7.1 网盘数据下载

以下数据产物因体积较大，统一上传到百度网盘，不随代码仓库分发：

> **网盘链接**：https://pan.baidu.com/s/1_uacMyl9y5YvrWsh77Mtww?pwd=kcs7
> **提取码**：kcs7

网盘目录结构：

```
甄嬛传千声千面_相关数据/
├── zero_shot_data/           ← 127 条精选参考音频（14 角色子目录）
├── emotion_examples/         ← 107 条情绪参考音频（华妃/皇后，4 情绪）
├── 甄嬛传14人物数据.tar      ← 清洗后全量数据集（13,605 段 WAV + Kaldi 元数据）
└── model_weights/            ← （待上传）CosyVoice3 微调模型权重
```

| 数据 | 内容 | 使用方式 |
|---|---|---|
| `zero_shot_data/` | 14 角色 × 3~10 条参考音频，共 127 段 WAV | 解压到 `data/zero_shot_data/`，供 `../siting_cosyvoice_tts/scripts/register_speakers.py` 注册 Zero-shot Speaker |
| `emotion_examples/` | 华妃 + 皇后 × 4 情绪，共 107 段 WAV | 供 `../siting_cosyvoice_tts/scripts/register_emotion_speakers_v2.py` 注册情绪 Speaker |
| `甄嬛传14人物数据.tar` | 完整清洗数据（13,605 段 + Kaldi 格式） | 解压到 `data/`，用于重新微调 CosyVoice3、转 GPT-SoVITS/VITS 等格式 |
| `model_weights/`（待上传） | CosyVoice3-0.5B LLM 微调权重 | 解压到 CosyVoice 项目的 `exp/zhenhuan/llm/` |

zero_shot_data 各角色音频数量：

| 角色 | 条数 | | 角色 | 条数 |
|---|---|---|---|---|
| 甄嬛 | 7 | | 崔槿汐 | 10 |
| 皇上·爱新觉罗·胤禎 | 9 | | 温实初 | 10 |
| 乌拉那拉·宜修(皇后) | 10 | | 浣碧 | 10 |
| 华妃·年世兰 | 10 | | 果郡王·允礼 | 10 |
| 沈眉庄 | 10 | | 太后 | 10 |
| 安陵容 | 9 | | 曹贵人 | 9 |
| 苏培盛 | 10 | | 叶澜依 | 3 |
| | | | **合计** | **127** |

### 7.2 `data/pipeline_results/` —— 人工标注产物

| 文件 | 内容 | 类型 |
|---|---|---|
| `speaker_map.json` | **人工标注的说话人映射**（spk_XX → 角色）。30 簇中 14 个映射到角色（部分角色如甄嬛/皇上跨多个簇），体现人工标注结果。 | 人工标注 |
| `samples_for_labeling.json` | 每簇随机抽取的 10 条标注样本清单。 | 自动生成 |

---

## 八、关键工作量与成果

- **数据集**：13,605 段、14 角色、16.7 小时，全流程自主构建，未用任何现成数据集
- **说话人识别**：eres2netv2 + KMeans 聚类 + 人工试听标注（每簇抽 5 条），三轮迭代
- **数据清洗**：4 轮过滤（角色/文本/去重/音频质检），15,685 → 13,605 段
- **训练数据导出**：CosyVoice Kaldi 格式 + Parquet，供 [`siting_cosyvoice_tts/`](../siting_cosyvoice_tts/) 微调使用
