"""
Step 1: VAD 切分 + ASR 转写 + 说话人识别（三合一）
使用 FunASR 一次性完成语音检测、识别和说话人分离。

输入: clean_vocals/  (UVR5 分离后的纯净人声)
输出: segments/      (切分后的短音频片段)
      pipeline_results/all_segments.json  (完整标注结果)

用法:
    python scripts/step1_pipeline.py                    # 处理所有文件
    python scripts/step1_pipeline.py --episode zhz_01   # 只处理指定集
    python scripts/step1_pipeline.py --dry-run          # 预览不实际处理
"""

import os, sys, json, argparse
from tqdm import tqdm
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    DEMUCS_OUTPUT_DIR, SEGMENTS_DIR, PIPELINE_RESULTS_DIR,
    VAD_MIN_DURATION, VAD_MAX_DURATION,
    MIN_TEXT_LENGTH, MAX_TEXT_LENGTH,
    FUNASR_MODEL, FUNASR_VAD_MODEL,
    ensure_dirs, print_header, print_done,
)


def load_vad_model():
    """加载 VAD 模型（含时序信息）"""
    from funasr import AutoModel

    print("加载 VAD 模型（SeacoParaformer + FSMN）...")
    model = AutoModel(
        model=FUNASR_MODEL,
        vad_model=FUNASR_VAD_MODEL,
    )
    print("  ✅ VAD 模型加载完成")
    return model


def find_vocal_files(input_dir):
    """
    扫描 demucs 输出目录，找到所有 vocals.wav
    目录结构: clean_vocals/mdx_extra_q/zhz_01/vocals.wav
    返回: [(source_name, wav_path), ...]
    """
    files = []
    if not os.path.isdir(input_dir):
        return files
    for episode_dir in sorted(os.listdir(input_dir)):
        episode_path = os.path.join(input_dir, episode_dir)
        if not os.path.isdir(episode_path):
            continue
        vocal_path = os.path.join(episode_path, "vocals.wav")
        if os.path.exists(vocal_path):
            files.append((episode_dir, vocal_path))
    return files


def merge_timestamps(timestamps, min_gap_ms=400):
    """将字级时间戳合并为句子级片段（间隔 > min_gap_ms 时分段）"""
    if not timestamps:
        return []
    merged = []
    cur_start, cur_end = timestamps[0][0], timestamps[0][1]
    for t in timestamps[1:]:
        if t[0] - cur_end > min_gap_ms:
            merged.append([cur_start, cur_end])
            cur_start, cur_end = t[0], t[1]
        else:
            cur_end = t[1]
    merged.append([cur_start, cur_end])
    return merged


def load_asr_model():
    """单独加载 ASR 模型（用于逐段转写）"""
    from funasr import AutoModel
    return AutoModel(model="iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch")


def process_episode(vad_model, asr_model, wav_path, source_name, output_dir):
    """
    处理单集：先用 VAD 模型获取时间段 → 合并为句子级 → 再逐段 ASR 转写

    Returns:
        list[dict]
    """
    import soundfile as sf

    # Step A: VAD 获取时间戳
    result = vad_model.generate(input=wav_path, batch_size=64)
    if result is None or len(result) == 0:
        print(f"    ⚠️  VAD 无输出")
        return []

    timestamps = result[0].get("timestamp", [])
    if not timestamps:
        print(f"    ⚠️  timestamp 为空")
        return []

    # Step B: 合并为句子级片段
    merged = merge_timestamps(timestamps, min_gap_ms=800)

    # Step C: 读取音频 + 逐段切分 + ASR
    audio, sr = sf.read(wav_path)
    segments = []

    for i, (start_ms, end_ms) in enumerate(merged):
        duration = (end_ms - start_ms) / 1000.0
        if duration < VAD_MIN_DURATION or duration > VAD_MAX_DURATION:
            continue

        start_sample = int(start_ms * sr / 1000)
        end_sample = int(end_ms * sr / 1000)

        seg_name = f"{source_name}_seg{i:04d}.wav"
        seg_path = os.path.join(output_dir, seg_name)
        sf.write(seg_path, audio[start_sample:end_sample], sr)

        # ASR 转写本段
        asr_result = asr_model.generate(input=seg_path)
        text = ""
        if asr_result and len(asr_result) > 0:
            text = asr_result[0].get("text", "").strip()

        if len(text) < MIN_TEXT_LENGTH:
            continue

        segments.append({
            "file": seg_name,
            "text": text,
            "speaker": "unknown",  # 后续单独步骤做
            "start": round(start_ms / 1000.0, 2),
            "end": round(end_ms / 1000.0, 2),
            "duration": round(duration, 2),
            "source": source_name,
        })

    return segments


def main():
    parser = argparse.ArgumentParser(description="VAD + ASR + Speaker Diarization")
    parser.add_argument("--input-dir", default=DEMUCS_OUTPUT_DIR, help="demucs 输出目录")
    parser.add_argument("--output-dir", default=SEGMENTS_DIR, help="片段输出目录")
    parser.add_argument("--episode", default=None, help="只处理指定集（如 zhz_01）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    args = parser.parse_args()

    ensure_dirs(args.output_dir, PIPELINE_RESULTS_DIR)

    # 扫描文件 → [(episode_name, vocals_path), ...]
    vocal_files = find_vocal_files(args.input_dir)
    if not vocal_files:
        print(f"❌ 未找到音频文件: {args.input_dir}")
        print(f"   请先运行 demucs 将人声输出到该目录")
        return

    if args.episode:
        vocal_files = [(name, path) for name, path in vocal_files if args.episode in name]
        if not vocal_files:
            print(f"❌ 未找到匹配的音频: {args.episode}")
            return

    print_header("Step 1: VAD 切分 + ASR 转写 + 说话人识别")
    print(f"  输入目录: {args.input_dir}")
    print(f"  输出目录: {args.output_dir}")
    print(f"  待处理: {len(vocal_files)} 集")
    if args.dry_run:
        print("  🔍 预览模式（不实际处理）")
        for name, path in vocal_files:
            print(f"    - {name}")
        print_done()
        return

    # 加载模型：VAD + ASR 分开
    print("加载 VAD 模型...")
    vad_model = load_vad_model()
    print("加载 ASR 模型（Paraformer）...")
    asr_model = load_asr_model()

    # 逐文件处理
    all_segments = []
    episode_stats = {}

    for source_name, wav_path in tqdm(vocal_files, desc="处理进度"):
        segments = process_episode(vad_model, asr_model, wav_path, source_name, args.output_dir)
        all_segments.extend(segments)
        episode_stats[source_name] = len(segments)

    # 保存完整结果
    result_path = os.path.join(PIPELINE_RESULTS_DIR, "all_segments.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(all_segments, f, ensure_ascii=False, indent=2)

    # 保存每集统计
    stats_path = os.path.join(PIPELINE_RESULTS_DIR, "episode_stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(episode_stats, f, ensure_ascii=False, indent=2)

    # 打印统计
    print_header("处理结果统计")
    print(f"  总片段数: {len(all_segments)}")
    print(f"  总集数: {len(episode_stats)}")

    speaker_counter = Counter(s["speaker"] for s in all_segments)
    print(f"  检测到的说话人数: {len(speaker_counter)}")
    print(f"\n  Top 20 说话人:")
    for spk, cnt in speaker_counter.most_common(20):
        total_dur = sum(s["duration"] for s in all_segments if s["speaker"] == spk)
        print(f"    {spk}: {cnt}段, {total_dur/60:.1f}分钟")

    print(f"\n  结果已保存:")
    print(f"    {result_path}")
    print(f"    {stats_path}")
    print(f"    音频片段: {args.output_dir}/")

    print_header("下一步")
    print("  python scripts/step2_sample_labeling.py")
    print_done()


if __name__ == "__main__":
    main()
