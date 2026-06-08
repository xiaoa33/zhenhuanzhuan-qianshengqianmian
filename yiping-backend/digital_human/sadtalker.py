import os
import glob
import uuid
import asyncio
import urllib.parse

SADTALKER_PATH = os.getenv("SADTALKER_PATH", "../SadTalker")
SADTALKER_PYTHON = os.getenv("SADTALKER_PYTHON", "python")
STATIC_BASE_URL = os.getenv("STATIC_BASE_URL", "http://localhost:8000")

_BASE_DIR = os.path.dirname(__file__)
PORTRAITS_DIR = os.path.join(_BASE_DIR, "..", "resource", "portraits")
VIDEO_OUTPUT_DIR = os.path.join(_BASE_DIR, "..", "static", "video")


def _audio_url_to_path(audio_url: str) -> str:
    """将 http://localhost:8000/static/audio/xxx.wav 转为本地路径"""
    parsed = urllib.parse.urlparse(audio_url)
    # parsed.path 形如 /static/audio/xxx.wav
    rel = parsed.path.lstrip("/")  # static/audio/xxx.wav
    return os.path.join(_BASE_DIR, "..", rel)


async def generate_video(character_id: str, audio_url: str) -> str | None:
    """
    调用 SadTalker 生成数字人说话视频，返回可访问的 video_url。
    失败时返回 None，前端自动降级显示静态剧照。
    """
    sadtalker_script = os.path.join(SADTALKER_PATH, "inference.py")
    if not os.path.isfile(sadtalker_script):
        raise FileNotFoundError(
            f"SadTalker 未找到: {sadtalker_script}\n"
            "请先克隆 SadTalker 并在 .env 中设置 SADTALKER_PATH"
        )

    portrait_path = os.path.join(PORTRAITS_DIR, f"{character_id}.jpg")
    if not os.path.isfile(portrait_path):
        raise FileNotFoundError(
            f"角色参考图未找到: {portrait_path}\n"
            "请将角色剧照复制到 resource/portraits/ 并重命名为 {{character_id}}.jpg"
        )

    audio_path = _audio_url_to_path(audio_url)
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"音频文件未找到: {audio_path}")

    os.makedirs(VIDEO_OUTPUT_DIR, exist_ok=True)

    cmd = [
        os.path.abspath(SADTALKER_PYTHON),
        os.path.abspath(sadtalker_script),
        "--driven_audio", os.path.abspath(audio_path),
        "--source_image", os.path.abspath(portrait_path),
        "--result_dir", os.path.abspath(VIDEO_OUTPUT_DIR),
        "--still",        # 减少头部晃动，更自然
        "--preprocess", "full",
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=os.path.abspath(SADTALKER_PATH),
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"SadTalker 执行失败:\n{stderr.decode(errors='ignore')}")

    # 取 result_dir 下最新生成的 .mp4
    mp4_files = glob.glob(os.path.join(VIDEO_OUTPUT_DIR, "**", "*.mp4"), recursive=True)
    if not mp4_files:
        raise RuntimeError("SadTalker 未生成视频文件")

    newest = max(mp4_files, key=os.path.getmtime)
    filename = os.path.basename(newest)
    return f"{STATIC_BASE_URL}/static/video/{filename}"
