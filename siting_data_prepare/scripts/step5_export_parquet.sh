#!/bin/bash
# ================================================================
# Step 5: 提取 Embedding / Speech Token → 转 Parquet 格式
# 将 Kaldi 格式数据转换为 CosyVoice 训练用的 Parquet 格式。
#
# 前置条件:
#   - Step 4 已完成 (cosyvoice_train/train/ 目录已生成)
#   - CosyVoice 已克隆到项目中
#   - 预训练模型已下载
#
# 用法:
#   bash scripts/step5_export_parquet.sh
# ================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COSYVOICE_DIR="${PROJECT_DIR}/../CosyVoice"
DATA_DIR="${PROJECT_DIR}/data/cosyvoice_train"
PRETRAINED_DIR="${PROJECT_DIR}/../pretrained_models/CosyVoice-300M"

echo "============================================"
echo "  Step 5: Parquet 格式导出"
echo "============================================"

# ---- 检查 CosyVoice 是否存在 ----
if [ ! -d "$COSYVOICE_DIR" ]; then
    echo "❌ CosyVoice 目录不存在: $COSYVOICE_DIR"
    echo "   请先克隆: git clone https://github.com/FunAudioLLM/CosyVoice.git"
    exit 1
fi

# ---- 检查预训练模型 ----
if [ ! -d "$PRETRAINED_DIR" ]; then
    echo "❌ 预训练模型目录不存在: $PRETRAINED_DIR"
    echo "   请从 ModelScope 下载 CosyVoice-300M 模型"
    echo "   https://www.modelscope.cn/models/iic/CosyVoice-300M"
    exit 1
fi

# ---- 处理 train 和 dev 子集 ----
for SUBSET in train dev; do
    SRC_DIR="${DATA_DIR}/${SUBSET}"
    if [ ! -f "${SRC_DIR}/wav.scp" ]; then
        echo "⚠️  跳过 ${SUBSET}/ (wav.scp 不存在)"
        continue
    fi

    echo ""
    echo "--- 处理 ${SUBSET} ---"

    # 统计
    N_UTTS=$(wc -l < "${SRC_DIR}/wav.scp")
    N_SPKS=$(wc -l < "${SRC_DIR}/spk2utt")
    echo "  片段数: ${N_UTTS}"
    echo "  说话人数: ${N_SPKS}"

    # 1. 提取 Speaker Embedding
    echo "  [1/3] 提取 Speaker Embedding..."
    python "${COSYVOICE_DIR}/tools/extract_embedding.py" \
        --dir "${SRC_DIR}" \
        --onnx_path "${PRETRAINED_DIR}/campplus.onnx"
    echo "  ✅ spk2embedding.pt / utt2embedding.pt 已生成"

    # 2. 提取 Speech Token
    echo "  [2/3] 提取 Speech Token..."
    python "${COSYVOICE_DIR}/tools/extract_speech_token.py" \
        --dir "${SRC_DIR}" \
        --onnx_path "${PRETRAINED_DIR}/speech_tokenizer_v1.onnx"
    echo "  ✅ utt2speech_token.pt 已生成"

    # 3. 转换为 Parquet
    echo "  [3/3] 转换为 Parquet 格式..."
    PARQUET_DIR="${SRC_DIR}/parquet"
    mkdir -p "${PARQUET_DIR}"

    python "${COSYVOICE_DIR}/tools/make_parquet_list.py" \
        --num_utts_per_parquet 1000 \
        --num_processes 4 \
        --src_dir "${SRC_DIR}" \
        --des_dir "${PARQUET_DIR}"
    echo "  ✅ Parquet 文件已生成到 ${PARQUET_DIR}/"
done

# ---- 合并 data.list ----
echo ""
echo "--- 合并训练集和验证集 ---"
TRAIN_LIST="${DATA_DIR}/train/parquet/data.list"
DEV_LIST="${DATA_DIR}/dev/parquet/data.list"

if [ -f "$TRAIN_LIST" ]; then
    cp "$TRAIN_LIST" "${DATA_DIR}/train.data.list"
    echo "  ✅ ${DATA_DIR}/train.data.list"
fi

if [ -f "$DEV_LIST" ]; then
    cp "$DEV_LIST" "${DATA_DIR}/dev.data.list"
    echo "  ✅ ${DATA_DIR}/dev.data.list"
fi

echo ""
echo "============================================"
echo "  ✅ Parquet 格式导出完成！"
echo ""
echo "  训练数据: ${DATA_DIR}/train.data.list"
echo "  验证数据: ${DATA_DIR}/dev.data.list"
echo ""
echo "  下一步 — 开始微调训练:"
echo "    参考 CosyVoice/examples/libritts/cosyvoice/run.sh"
echo "    将 --train_data 指向 ${DATA_DIR}/train.data.list"
echo "============================================"
