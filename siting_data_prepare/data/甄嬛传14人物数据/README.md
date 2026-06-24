# 甄嬛传 14 人物完整数据集

> ⚠️ 本目录仅存放说明文件，实际数据请从网盘下载。

## 网盘下载

- **链接**：https://pan.baidu.com/s/1_uacMyl9y5YvrWsh77Mtww?pwd=kcs7
- **提取码**：kcs7
- **网盘文件**：`甄嬛传14人物数据.tar`

## 内容说明

该 tar 包为清洗后的完整数据集，包含：

| 内容 | 说明 |
|---|---|
| `segments/` | 13,605 段 WAV 音频（16kHz mono PCM） |
| `cosyvoice_train/train/` | 训练集 Kaldi 格式（wav.scp / text / utt2spk / spk2utt / instruct） |
| `cosyvoice_train/dev/` | 验证集 Kaldi 格式 |

## 使用方式

```bash
# 1. 下载后解压到本目录
tar -xf 甄嬛传14人物数据.tar -C siting_data_prepare/data/

# 2. 解压后目录结构
data/
├── segments/           # 13,605 个 WAV
└── cosyvoice_train/    # Kaldi 格式元数据
```

## 用途

- 重新微调 CosyVoice3-0.5B（先跑 `siting_data_prepare/scripts/step5_export_parquet.sh`）
- 注册 Zero-shot Speaker（`siting_cosyvoice_tts/scripts/register_speakers.py`）
- 转 GPT-SoVITS / VITS / Bert-VITS2 / Fish-Speech 等格式
