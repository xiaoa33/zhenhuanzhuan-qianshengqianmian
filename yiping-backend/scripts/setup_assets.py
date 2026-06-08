"""
运行此脚本完成首次部署前的资产准备：
  1. 生成 static/audio/mock_silence.mp3（实为 WAV，前端可直接播放）
  2. 创建 resource/portraits/ 目录并打印角色图片重命名指引
"""
import os
import struct

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def make_silence_wav(path: str, duration_sec: float = 1.0, sample_rate: int = 8000):
    """生成一个单声道 16-bit PCM 静音 WAV 文件"""
    num_samples = int(sample_rate * duration_sec)
    data_size = num_samples * 2  # 16-bit = 2 bytes/sample
    with open(path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        # fmt chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))       # chunk size
        f.write(struct.pack("<H", 1))        # PCM
        f.write(struct.pack("<H", 1))        # mono
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", sample_rate * 2))  # byte rate
        f.write(struct.pack("<H", 2))        # block align
        f.write(struct.pack("<H", 16))       # bits per sample
        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)
    print(f"[OK] 生成静音音频: {path}")


def main():
    # 1. 静音音频
    audio_dir = os.path.join(BASE_DIR, "static", "audio")
    os.makedirs(audio_dir, exist_ok=True)
    silence_path = os.path.join(audio_dir, "mock_silence.mp3")
    if not os.path.exists(silence_path):
        make_silence_wav(silence_path)
    else:
        print(f"[SKIP] 已存在: {silence_path}")

    # 2. 角色参考图目录
    portraits_dir = os.path.join(BASE_DIR, "resource", "portraits")
    os.makedirs(portraits_dir, exist_ok=True)
    print(f"[OK] 目录已创建: {portraits_dir}")

    # 3. 打印重命名指引
    mapping = [
        ("甄嬛剧照.jpg",    "zhenhuan.jpg"),
        ("华妃剧照.jpg",    "huafei.jpg"),
        ("宜修剧照.jpg",    "yixiu.jpg"),
        ("眉庄剧照.jpg",    "meizhuang.jpg"),
        ("安陵容剧照.jpg",  "anlinrong.jpg"),
        ("苏培盛剧照.jpg",  "supeisheng.jpg"),
        ("叶澜依剧照.jpg",  "yelanyi.jpg"),
        ("崔槿汐剧照.jpg",  "cuijinxi.jpg"),
        ("温实初剧照.jpeg", "wensichu.jpg"),
        ("浣碧剧照.jpg",    "huanbi.jpg"),
        ("皇上剧照.jpg",    "huangshang.jpg"),
        ("果郡王剧照.jpg",  "guojunwang.jpg"),
    ]

    print("\n请将 yiping-frontend/resource/角色剧照/ 中的图片复制到:")
    print(f"  {portraits_dir}")
    print("并按以下映射重命名：\n")
    for src, dst in mapping:
        target = os.path.join(portraits_dir, dst)
        status = "[OK]" if os.path.exists(target) else "[缺失]"
        print(f"  {status}  {src}  →  {dst}")


if __name__ == "__main__":
    main()
