# 数据集构建脚本说明

## 文件清单

```
scripts/
├── config.py                  # 共享配置（路径、参数、角色列表）
├── step0_env_check.py         # 环境检查
├── step1_pipeline.py          # VAD + ASR + 说话人识别（三合一）
├── step2_sample_labeling.py   # 角色标注辅助（抽样 + 关键词提示 + 映射）
├── step3_clean.py             # 数据清洗 & 质量过滤
├── step4_build_kaldi.py       # 构建 CosyVoice Kaldi 格式
├── step5_export_parquet.sh    # 提取 Embedding/Token → Parquet
├── run_all.sh                 # 一键运行脚本
└── README.md                  # 本文件
```

## 快速开始

### 方式一：逐步运行

```bash
# 0. 环境检查
python scripts/step0_env_check.py

# 1. VAD切分 + ASR转写 + 说话人识别（需先完成 UVR5 人声分离）
python scripts/step1_pipeline.py

# 2. 生成标注样本（然后人工填写 speaker_map.json）
python scripts/step2_sample_labeling.py
#    ... 试听样本，编辑 data/pipeline_results/speaker_map.json ...
python scripts/step2_sample_labeling.py --apply-map

# 3. 数据清洗
python scripts/step3_clean.py

# 4. 构建 CosyVoice Kaldi 格式
python scripts/step4_build_kaldi.py --with-instruct --split-dev 0.05

# 5. 提取 Embedding + Speech Token + 转 Parquet
bash scripts/step5_export_parquet.sh
```

### 方式二：一键交互运行

```bash
bash scripts/run_all.sh
```

## 前置条件

| 步骤 | 前置条件 |
|------|----------|
| Step 1 | UVR5 人声分离完成，输出到 `data/clean_vocals/` |
| Step 2 | Step 1 完成 |
| Step 2 `--apply-map` | 人工填写 `speaker_map.json` |
| Step 3 | Step 2 `--apply-map` 完成 |
| Step 4 | Step 3 完成 |
| Step 5 | CosyVoice 仓库 + 预训练模型就位 |

## 数据流

```
原始MP3 (data/甄嬛传原声_.../)
    │  UVR5（手动）
    ▼
纯净人声 (data/clean_vocals/)
    │  step1_pipeline.py
    ▼
音频片段 (data/segments/) + 全部标注 (data/pipeline_results/all_segments.json)
    │  step2_sample_labeling.py (抽样 → 人工标角色 → --apply-map)
    ▼
角色标注数据 (data/pipeline_results/labeled_segments.json)
    │  step3_clean.py
    ▼
清洗后数据 (data/pipeline_results/clean_data.json)
    │  step4_build_kaldi.py
    ▼
Kaldi格式 (data/cosyvoice_train/{train,dev}/)
    │  step5_export_parquet.sh
    ▼
Parquet格式 (data/cosyvoice_train/{train,dev}/parquet/)
    │  CosyVoice train.py
    ▼
微调模型
```

## 常见问题

**Q: Step 1 报错找不到模块？**
A: `pip install funasr modelscope soundfile librosa tqdm`

**Q: 说话人聚类不准确？**
A: 这是主要瓶颈。UVR5 分离质量直接影响聚类效果。建议先用 1-2 集测试效果。
   如果聚类太差，可以尝试用独立的 3D-Speaker 工具。

**Q: 某个角色数据量不足？**
A: 小角色（如温实初、叶澜依）在剧中出场本身就少。可以：
   1. 降低 `MIN_MINUTES_PER_CHARACTER` 阈值
   2. 合并数据量不足的角色（如与其他 TTS 数据混合）
   3. 优先保证主角（甄嬛、华妃、皇上、皇后）的数据量

**Q: UVR5 分离需要多久？**
A: 单集约 3 分钟（GPU），76 集约 4 小时。
