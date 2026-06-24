#!/usr/bin/env python3
"""
情绪 Speaker 注册脚本 v2 — 自动转写 + 注册
==========================================
对每个情绪样本用 FunASR 转写，得到匹配的 prompt_text 后再注册，
确保 prompt_text 与实际音频内容一致。

用法（AutoDL 云端）:
    conda activate cosyvoice
    cd /root/autodl-tmp
    pip install funasr -q
    python register_emotion_speakers_v2.py

前置条件:
    emotion_samples/ 已上传到 /root/autodl-tmp/data/emotion_samples/
"""

import sys
import os
from pathlib import Path

COSYVOICE_ROOT = '/root/autodl-tmp/CosyVoice'
sys.path.insert(0, COSYVOICE_ROOT)
sys.path.insert(0, str(Path(COSYVOICE_ROOT) / 'third_party' / 'Matcha-TTS'))

from cosyvoice.cli.cosyvoice import AutoModel
from funasr import AutoModel as FunASRModel

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


def transcribe(audio_path: str, asr_model) -> str:
    """用 FunASR 转写一段音频，返回文本"""
    result = asr_model.generate(input=audio_path)
    if result and len(result) > 0:
        return result[0].get("text", "").strip()
    return ""


if __name__ == '__main__':
    # 1. 加载 ASR
    print("⏳ 加载 FunASR 转写模型...")
    asr = FunASRModel(
        model="iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        disable_pbar=True,
    )
    print("✅ ASR 就绪")

    # 2. 加载 CosyVoice
    print(f"⏳ 加载 CosyVoice: {MODEL_DIR}")
    cosyvoice = AutoModel(model_dir=MODEL_DIR)
    print(f"✅ 已注册基础角色: {cosyvoice.list_available_spks()}")

    ok = 0
    for folder_name, char_id in FOLDER_TO_ID.items():
        char_dir = os.path.join(EMOTION_DIR, folder_name)
        if not os.path.isdir(char_dir):
            print(f"⚠ 目录不存在: {char_dir}")
            continue

        for emo_cn, emo_en in EMOTION_SUFFIX.items():
            emo_dir = os.path.join(char_dir, emo_cn)
            if not os.path.isdir(emo_dir):
                print(f"  ⚠ 缺失: {folder_name}/{emo_cn}")
                continue

            # 挑文件最大的（通常质量最好）
            wavs = sorted(
                [f for f in os.listdir(emo_dir) if f.endswith('.wav')],
                key=lambda x: os.path.getsize(os.path.join(emo_dir, x)),
                reverse=True,
            )
            if not wavs:
                print(f"  ⚠ 无音频: {folder_name}/{emo_cn}")
                continue

            wav_path = os.path.join(emo_dir, wavs[0])
            spk_id = f"{char_id}_{emo_en}"

            # 3. ASR 转写 → 得到匹配的 prompt_text
            print(f"  🎤 转写: {folder_name}/{emo_cn}/{wavs[0]} ...", end=" ", flush=True)
            actual_text = transcribe(wav_path, asr)
            if not actual_text:
                print("❌ 转写失败")
                continue
            print(f'"{actual_text[:30]}..."')

            # 4. 用匹配的文本注册
            success = cosyvoice.add_zero_shot_spk(
                f"You are a helpful assistant.<|endofprompt|>{actual_text}",
                wav_path, spk_id,
            )
            status = "✅" if success else "❌"
            print(f"    {status} {spk_id} | prompt: \"{actual_text[:40]}...\"")
            if success:
                ok += 1

    cosyvoice.save_spkinfo()
    print(f"\n💾 {ok}/16 情绪 speaker 已保存到 spk2info.pt")
    print(f"📋 全部 speaker ({len(cosyvoice.list_available_spks())}): {cosyvoice.list_available_spks()}")
