#!/usr/bin/env python3
"""
情绪 Speaker 注册脚本 — 4角色 × 4情绪 = 16个 zero-shot speaker

用法（AutoDL 云端）:
    conda activate cosyvoice
    cd /root/autodl-tmp
    python register_emotion_speakers.py

前置条件:
    1. emotion_samples/ 已上传到 /root/autodl-tmp/data/emotion_samples/
    2. 14角色已通过 register_speakers.py 注册到 spk2info.pt
"""

import sys
import os
from pathlib import Path

# 把 CosyVoice 项目根目录加入 Python 路径
COSYVOICE_ROOT = '/root/autodl-tmp/CosyVoice'
sys.path.insert(0, COSYVOICE_ROOT)
sys.path.insert(0, str(Path(COSYVOICE_ROOT) / 'third_party' / 'Matcha-TTS'))

from cosyvoice.cli.cosyvoice import AutoModel

MODEL_DIR = '/root/autodl-tmp/CosyVoice/pretrained_models/Fun-CosyVoice3-0.5B'
EMOTION_DIR = '/root/autodl-tmp/data/emotion_samples'

# 文件夹名 → character_id
FOLDER_TO_ID = {
    "zhenhuan":   "zhenhuan",
    "huangshang": "huangshang",
    "华妃":       "huafei",
    "皇后":       "yixiu",
}

# 中文情绪 → 英文后缀
EMOTION_SUFFIX = {
    "喜悦": "joy",
    "愤怒": "anger",
    "悲伤": "sad",
    "平静": "calm",
}

# 角色原始 prompt_text（和 register_speakers.py 一致）
CHAR_PROMPT = {
    "zhenhuan":   "不如你回去时把我抄好的经文送去宝华殿捎给那孩子",
    "huangshang": "这几日朕虽然病着心却惦记着你这里你可有再来等朕吗",
    "huafei":     "哥哥在前朝替皇上效力臣妾在后宫为皇上尽心",
    "yixiu":      "初闻只是感觉清淡闻久了牡丹那种雍容的底蕴才会缓缓渗透出来沁人心脾呀",
}

if __name__ == '__main__':
    print(f"模型: {MODEL_DIR}")
    cosyvoice = AutoModel(model_dir=MODEL_DIR)
    print(f"已注册角色: {cosyvoice.list_available_spks()}")

    ok = 0
    for folder_name, char_id in FOLDER_TO_ID.items():
        char_dir = os.path.join(EMOTION_DIR, folder_name)
        if not os.path.isdir(char_dir):
            print(f"⚠ 目录不存在: {char_dir}")
            continue

        prompt_text = CHAR_PROMPT[char_id]

        for emo_cn, emo_en in EMOTION_SUFFIX.items():
            emo_dir = os.path.join(char_dir, emo_cn)
            if not os.path.isdir(emo_dir):
                print(f"  ⚠ 缺失: {folder_name}/{emo_cn}")
                continue

            wavs = sorted(
                [f for f in os.listdir(emo_dir) if f.endswith('.wav')],
                key=lambda x: os.path.getsize(os.path.join(emo_dir, x)),
                reverse=True  # 挑文件最大的（通常质量最好）
            )
            if not wavs:
                print(f"  ⚠ 无音频: {folder_name}/{emo_cn}")
                continue

            wav_path = os.path.join(emo_dir, wavs[0])
            spk_id = f"{char_id}_{emo_en}"

            success = cosyvoice.add_zero_shot_spk(
                f"You are a helpful assistant.<|endofprompt|>{prompt_text}",
                wav_path, spk_id
            )
            status = "✅" if success else "❌"
            print(f"{status} {spk_id} ← {folder_name}/{emo_cn}/{wavs[0]}")
            if success:
                ok += 1

    cosyvoice.save_spkinfo()
    print(f"\n💾 {ok}/16 情绪 speaker 已保存到 spk2info.pt")
    print(f"📋 全部 speaker: {cosyvoice.list_available_spks()}")
