"""
Step 0: 环境检查
验证所有依赖是否正确安装，目录和文件是否就位。
"""

import sys
import os

# 将 scripts/ 的父目录加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    RAW_AUDIO_DIR, CLEAN_VOCALS_DIR, SEGMENTS_DIR,
    COSYVOICE_ROOT, PRETRAINED_MODEL_DIR,
    TARGET_CHARACTERS, ensure_dirs, print_header, print_done,
)

def check_python():
    print_header("检查 Python 版本")
    v = sys.version_info
    print(f"  Python {v.major}.{v.minor}.{v.micro}")
    if v.major < 3 or (v.major == 3 and v.minor < 9):
        print("  ⚠️  建议 Python ≥ 3.9")
    else:
        print("  ✅ OK")

def check_packages():
    print_header("检查依赖包")
    packages = {
        "torch": "torch",
        "torchaudio": "torchaudio",
        "funasr": "funasr",
        "soundfile": "soundfile",
        "librosa": "librosa",
        "numpy": "numpy",
        "tqdm": "tqdm",
        "json": "(内置)",
        "pydub": "pydub",
    }
    for import_name, pkg_name in packages.items():
        try:
            __import__(import_name)
            print(f"  ✅ {pkg_name}")
        except ImportError:
            print(f"  ❌ {pkg_name} — 请运行: pip install {pkg_name}")

def check_raw_audio():
    print_header("检查原始音频")
    if not os.path.isdir(RAW_AUDIO_DIR):
        print(f"  ❌ 目录不存在: {RAW_AUDIO_DIR}")
        return

    mp3_files = sorted([
        f for f in os.listdir(RAW_AUDIO_DIR) if f.endswith(".mp3")
    ])
    if not mp3_files:
        print(f"  ❌ 目录中没有 MP3 文件")
        return

    print(f"  目录: {RAW_AUDIO_DIR}")
    print(f"  MP3 文件数: {len(mp3_files)}")
    print(f"  范围: {mp3_files[0]} ~ {mp3_files[-1]}")

    # 检查文件大小一致性
    import hashlib
    sizes = set()
    for f in mp3_files[:5]:
        path = os.path.join(RAW_AUDIO_DIR, f)
        sizes.add(os.path.getsize(path))
    if len(sizes) == 1:
        print(f"  文件大小一致: {list(sizes)[0]/1024/1024:.1f} MB/集")
    else:
        print(f"  ⚠️  文件大小不一致，请检查")

    # 估算总时长
    try:
        import subprocess, json
        ffprobe = "ffprobe"
        total_sec = 0
        for f in mp3_files[:3]:
            r = subprocess.run(
                [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format",
                 os.path.join(RAW_AUDIO_DIR, f)],
                capture_output=True, text=True
            )
            total_sec += float(json.loads(r.stdout)["format"]["duration"])
        avg_min = total_sec / min(3, len(mp3_files)) / 60
        total_hr = avg_min * len(mp3_files) / 60
        print(f"  平均每集: {avg_min:.0f} 分钟")
        print(f"  预估总时长: {total_hr:.0f} 小时")
    except Exception:
        print(f"  ⚠️  无法检测时长（ffprobe 不可用）")

def check_directories():
    print_header("创建工作目录")
    dirs = [CLEAN_VOCALS_DIR, SEGMENTS_DIR]
    ensure_dirs(*dirs)
    for d in dirs:
        print(f"  ✅ {d}")

def check_cosyvoice():
    print_header("检查 CosyVoice")
    if not os.path.isdir(COSYVOICE_ROOT):
        print(f"  ⚠️  CosyVoice 目录不存在: {COSYVOICE_ROOT}")
        print(f"  （后续训练时需要，当前数据处理阶段可忽略）")
        return

    tools = [
        "tools/extract_embedding.py",
        "tools/extract_speech_token.py",
        "tools/make_parquet_list.py",
        "cosyvoice/bin/train.py",
    ]
    for t in tools:
        p = os.path.join(COSYVOICE_ROOT, t)
        if os.path.exists(p):
            print(f"  ✅ {t}")
        else:
            print(f"  ❌ 缺失: {t}")

    if os.path.isdir(PRETRAINED_MODEL_DIR):
        onnx_files = [f for f in os.listdir(PRETRAINED_MODEL_DIR) if f.endswith(".onnx")]
        print(f"  预训练模型: {PRETRAINED_MODEL_DIR}")
        for onnx in onnx_files:
            print(f"    ✅ {onnx}")
    else:
        print(f"  ⚠️  预训练模型目录不存在（训练时需要）")

def print_summary():
    print_header("目标角色清单")
    for i, char in enumerate(TARGET_CHARACTERS, 1):
        print(f"  {i:2d}. {char}")
    print(f"\n  共 {len(TARGET_CHARACTERS)} 位角色")

def main():
    print("=" * 60)
    print("  甄嬛传 CosyVoice 数据集构建 — 环境检查")
    print("=" * 60)

    check_python()
    check_packages()
    check_raw_audio()
    check_directories()
    check_cosyvoice()
    print_summary()

    print_header("下一步")
    print("  如果上述检查全部通过，请运行:")
    print("    python scripts/step1_pipeline.py")
    print("  如果 UVR5 尚未运行，请先对原始音频做人声分离。")
    print_done()

if __name__ == "__main__":
    main()
