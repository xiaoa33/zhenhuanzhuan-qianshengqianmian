#!/bin/bash
# ================================================================
# 甄嬛传 CosyVoice 数据集构建 — 一键运行脚本
#
# 用法:
#   bash scripts/run_all.sh              # 逐步交互运行
#   bash scripts/run_all.sh --auto       # 自动运行（跳过人工标注步骤）
# ================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$(dirname "$SCRIPT_DIR")"

AUTO_MODE=false
if [ "$1" = "--auto" ]; then
    AUTO_MODE=true
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   甄嬛传 CosyVoice 数据集构建 Pipeline                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ---- Step 0: 环境检查 ----
echo "════════════════════════════════════════════════════════════"
echo "  Step 0: 环境检查"
echo "════════════════════════════════════════════════════════════"
python scripts/step0_env_check.py
if [ "$AUTO_MODE" = false ]; then
    echo ""
    read -p "继续? (Enter=继续, Ctrl+C=退出) " _
fi

# ---- Step 1: Pipeline ----
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Step 1: VAD + ASR + 说话人识别"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "  ⚠️  请确认 UVR5 人声分离已完成，输出到 data/clean_vocals/"
echo ""
if [ "$AUTO_MODE" = false ]; then
    read -p "继续运行 Step 1? (Enter=继续, s=跳过) " answer
    if [ "$answer" = "s" ]; then
        echo "  跳过 Step 1"
    else
        python scripts/step1_pipeline.py
    fi
else
    python scripts/step1_pipeline.py
fi

# ---- Step 2: 角色标注 ----
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Step 2: 角色标注"
echo "════════════════════════════════════════════════════════════"
python scripts/step2_sample_labeling.py
echo ""
echo "  ⚠️  请按以下步骤操作："
echo "  1. 查看 data/pipeline_results/samples_for_labeling.json"
echo "  2. 逐个 speaker 试听音频片段"
echo "  3. 编辑 data/pipeline_results/speaker_map.json"
echo "     将每个 spk_XX 映射到真实角色名"
echo "  4. 完成后运行: python scripts/step2_sample_labeling.py --apply-map"
echo ""

if [ "$AUTO_MODE" = false ]; then
    read -p "按 Enter 继续到 Step 3 (确保已运行 --apply-map) " _
fi

# ---- Step 3: 数据清洗 ----
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Step 3: 数据清洗"
echo "════════════════════════════════════════════════════════════"
python scripts/step3_clean.py

# ---- Step 4: 构建 Kaldi 格式 ----
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Step 4: 构建 CosyVoice Kaldi 格式"
echo "════════════════════════════════════════════════════════════"
python scripts/step4_build_kaldi.py --with-instruct --split-dev 0.05

# ---- Step 5: Parquet 导出 ----
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Step 5: Parquet 格式导出"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "  这步需要 CosyVoice 预训练模型，耗时较长。"
echo "  确认 CosyVoice 和预训练模型已就位后再运行:"
echo "    bash scripts/step5_export_parquet.sh"
echo ""

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ Pipeline 完成！                                       ║"
echo "║                                                          ║"
echo "║  输出目录: data/cosyvoice_train/                         ║"
echo "║  中间产物: data/pipeline_results/                        ║"
echo "║  音频片段: data/segments/                                ║"
echo "╚══════════════════════════════════════════════════════════╝"
