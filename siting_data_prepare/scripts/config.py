"""
共享配置 — 所有脚本的统一参数。
修改此文件即可调整整个 pipeline 的行为，无需逐个脚本修改。
"""

import os

# ============================================================
# 路径配置
# ============================================================

# 项目根目录（此脚本向上两级：scripts/ → VIP大作业/）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 原始 MP3 音频目录
RAW_AUDIO_DIR = os.path.join(
    PROJECT_ROOT, "data",
    "甄嬛传原声_无人播剧音频去片头片尾_正常音量_MP3"
)

# UVR5 人声分离输出目录
CLEAN_VOCALS_DIR = os.path.join(PROJECT_ROOT, "data", "clean_vocals")

# demucs 输出子目录（取决于 -n 参数，如 mdx_extra_q 或 htdemucs）
DEMUCS_MODEL_NAME = "mdx_extra_q"
DEMUCS_OUTPUT_DIR = os.path.join(CLEAN_VOCALS_DIR, DEMUCS_MODEL_NAME)

# VAD 切分片段输出目录
SEGMENTS_DIR = os.path.join(PROJECT_ROOT, "data", "segments")

# Pipeline 中间结果
PIPELINE_RESULTS_DIR = os.path.join(PROJECT_ROOT, "data", "pipeline_results")

# CosyVoice 训练数据目录
COSYVOICE_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "cosyvoice_train")

# ============================================================
# CosyVoice 路径（按需修改）
# ============================================================

COSYVOICE_ROOT = os.path.join(PROJECT_ROOT, "..", "CosyVoice")
PRETRAINED_MODEL_DIR = os.path.join(PROJECT_ROOT, "..", "pretrained_models", "CosyVoice-300M")

# ============================================================
# 目标角色列表（14 位）
# ============================================================

TARGET_CHARACTERS = [
    "甄嬛",
    "华妃·年世兰",
    "乌拉那拉·宜修(皇后)",
    "沈眉庄",
    "安陵容",
    "苏培盛",
    "叶澜依",
    "崔槿汐",
    "温实初",
    "浣碧",
    "皇上·爱新觉罗·胤禎",
    "果郡王·允礼",
    "太后",
    "曹贵人",
]

# ============================================================
# 音频参数
# ============================================================

# CosyVoice 默认采样率（不要改）
COSYVOICE_SAMPLE_RATE = 22050

# VAD 切分参数
VAD_MIN_DURATION = 2.0   # 最短片段（秒）
VAD_MAX_DURATION = 15.0  # 最长片段（秒）

# 质量控制
MIN_RMS = 0.003          # 最小 RMS 能量（低于此值视为静音）
MIN_TEXT_LENGTH = 2      # 最短文本（字）
MAX_TEXT_LENGTH = 100    # 最长文本（字）

# 每角色最低数据量（分钟）
MIN_MINUTES_PER_CHARACTER = 10

# ============================================================
# FunASR 模型配置
# ============================================================

# 三合一模型（VAD + ASR + 说话人识别）
# 注意：FunASR 1.3.x 模型名需要 -pytorch 后缀
# SeacoParaformer 自带 VAD + 标点，只需额外加 SPK 模型
FUNASR_MODEL = "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
FUNASR_VAD_MODEL = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
FUNASR_SPK_MODEL = "iic/speech_eres2netv2_sv_zh-cn_16k-common"

# ============================================================
# 角色关键词（用于自动提示，加速人工标注）
# ============================================================

CHARACTER_KEYWORDS = {
    "甄嬛":   ["臣妾", "本宫", "莞莞", "嬛嬛", "碎玉轩", "永寿宫"],
    "华妃·年世兰": ["贱人", "矫情", "年氏", "年羹尧", "翊坤宫", "赏你一丈红"],
    "乌拉那拉·宜修(皇后)": ["中宫", "乌拉那拉", "景仁宫", "皇额娘", "哀家"],
    "沈眉庄": ["眉庄", "沈答应", "存菊堂", "温太医"],
    "安陵容": ["陵容", "安答应", "安常在", "嫔妾出身低微", "延禧宫"],
    "苏培盛": ["奴才", "老奴", "万岁爷", "皇上息怒"],
    "叶澜依": ["叶答应", "宁贵人", "百骏园"],
    "崔槿汐": ["槿汐", "小主", "奴婢"],
    "温实初": ["微臣", "温太医", "太医院"],
    "浣碧":   ["浣碧", "玉娆", "义妹"],
    "皇上·爱新觉罗·胤禎": ["朕", "赐死", "爱卿", "斩立决", "御前", "养心殿"],
    "太后": ["哀家", "太后", "皇额娘"],
    "曹贵人": ["曹贵人", "曹琴默"],
}

# ============================================================
# Parquet 转换参数
# ============================================================

NUM_UTTS_PER_PARQUET = 1000
NUM_PROCESSES = 4

# ============================================================
# 辅助函数
# ============================================================

def ensure_dirs(*dirs):
    """批量创建目录"""
    for d in dirs:
        os.makedirs(d, exist_ok=True)

def print_header(title):
    """打印分节标题"""
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")

def print_done():
    """打印完成标志"""
    print(f"\n{'─' * 60}")
    print("  ✅ 完成")
    print(f"{'─' * 60}\n")
