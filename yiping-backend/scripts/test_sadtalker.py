"""
单独调试 SadTalker 数字人生成。
从 yiping-backend/ 目录运行：
    python scripts/test_sadtalker.py
    python scripts/test_sadtalker.py --character huafei
"""
import argparse
import asyncio
import os
import sys

# 让脚本能找到上层模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from digital_human.sadtalker import generate_video, SADTALKER_PATH, SADTALKER_PYTHON

MOCK_AUDIO_URL = "http://localhost:8000/static/audio/mock_silence.wav"


async def main(character_id: str):
    print(f"SADTALKER_PATH   = {SADTALKER_PATH}")
    print(f"SADTALKER_PYTHON = {SADTALKER_PYTHON}")
    print(f"character_id     = {character_id}")
    print(f"audio_url        = {MOCK_AUDIO_URL}")
    print("-" * 50)

    # 检查 inference.py 是否存在
    script = os.path.join(SADTALKER_PATH, "inference.py")
    print(f"inference.py 存在: {os.path.isfile(script)}  ({os.path.abspath(script)})")

    # 检查 Python 解释器
    python_abs = os.path.abspath(SADTALKER_PYTHON)
    print(f"Python 解释器存在: {os.path.isfile(python_abs)}  ({python_abs})")

    # 检查角色参考图
    portrait = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "resource", "portraits", f"{character_id}.jpg")
    )
    print(f"角色参考图存在:  {os.path.isfile(portrait)}  ({portrait})")

    # 检查音频文件
    audio_local = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "static", "audio", "mock_silence.wav")
    )
    print(f"mock 音频存在:   {os.path.isfile(audio_local)}  ({audio_local})")
    print("-" * 50)

    print("开始调用 generate_video ...")
    try:
        video_url = await generate_video(character_id, MOCK_AUDIO_URL)
        print(f"成功！video_url = {video_url}")
    except FileNotFoundError as e:
        print(f"[FileNotFoundError] {e}")
    except RuntimeError as e:
        print(f"[RuntimeError] {e}")
    except Exception as e:
        print(f"[未知错误] {type(e).__name__}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--character", default="huafei", help="角色 ID，默认 huafei")
    args = parser.parse_args()
    asyncio.run(main(args.character))