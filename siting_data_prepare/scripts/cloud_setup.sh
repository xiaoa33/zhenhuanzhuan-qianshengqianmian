#!/bin/bash
# ================================================================
# 云端环境一键配置脚本（在 AutoDL / 云服务器上运行）
#
# 用法:
#   chmod +x scripts/cloud_setup.sh
#   bash scripts/cloud_setup.sh
#
# 前置条件:
#   - AutoDL 镜像选择: PyTorch 2.x + CUDA 12.x
#   - VIP大作业/ 文件夹已上传到 /root/autodl-tmp/ 或工作目录
# ================================================================

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   云端环境配置 — 甄嬛传 CosyVoice 数据集构建              ║"
echo "╚══════════════════════════════════════════════════════════╝"

WORK_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo ""
echo "工作目录: $WORK_DIR"

# ---- 1. 基础依赖 ----
echo ""
echo "[1/5] 安装 Python 依赖..."
pip install funasr modelscope soundfile librosa pydub tqdm pandas \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# ---- 2. UVR5 命令行版 ----
echo ""
echo "[2/5] 安装 UVR5 命令行版（人声分离）..."
pip install audio-separator -i https://pypi.tuna.tsinghua.edu.cn/simple

# ---- 3. 克隆 CosyVoice ----
echo ""
echo "[3/5] 克隆 CosyVoice..."
cd "$(dirname "$WORK_DIR")"
if [ ! -d "CosyVoice" ]; then
    git clone https://github.com/FunAudioLLM/CosyVoice.git
else
    echo "  CosyVoice 已存在，跳过克隆"
fi

cd CosyVoice
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# ---- 4. 下载预训练模型 ----
echo ""
echo "[4/5] 下载 CosyVoice-300M 预训练模型..."
mkdir -p pretrained_models

if [ ! -d "pretrained_models/CosyVoice-300M" ]; then
    python -c "
from modelscope import snapshot_download
snapshot_download('iic/CosyVoice-300M', local_dir='pretrained_models/CosyVoice-300M')
print('预训练模型下载完成')
"
else
    echo "  预训练模型已存在，跳过下载"
fi

# ---- 5. 验证 GPU ----
echo ""
echo "[5/5] 验证 GPU 环境..."
python -c "
import torch
print(f'  PyTorch: {torch.__version__}')
print(f'  CUDA 可用: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'  GPU 数量: {torch.cuda.device_count()}')
    for i in range(torch.cuda.device_count()):
        print(f'  GPU[{i}]: {torch.cuda.get_device_name(i)}')
        print(f'    显存: {torch.cuda.get_device_properties(i).total_mem/1024**3:.1f} GB')
else:
    print('  ⚠️  CUDA 不可用，请检查 GPU 配置')
"

# ---- 完成 ----
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ 云端环境配置完成！                                   ║"
echo "║                                                        ║"
echo "║  下一步：                                              ║"
echo "║  1. 运行 UVR5 人声分离                                  ║"
echo "║  2. python scripts/step1_pipeline.py                   ║"
echo "║  3. (角色标注完成后) python scripts/step3_clean.py     ║"
echo "║  4. python scripts/step4_build_kaldi.py                ║"
echo "║  5. bash scripts/step5_export_parquet.sh               ║"
echo "╚══════════════════════════════════════════════════════════╝"
