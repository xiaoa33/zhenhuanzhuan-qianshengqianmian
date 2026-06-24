"""
Step 3: 数据清洗 & 质量过滤
从标注后的数据中筛选高质量片段，确保每个目标角色有足够数据。

输入: pipeline_results/labeled_segments.json  (Step 2 输出)
输出: pipeline_results/clean_data.json        (清洗后数据)
      pipeline_results/clean_stats.json       (统计报告)

用法:
    python scripts/step3_clean.py
    python scripts/step3_clean.py --min-minutes 15  # 提高最低时长要求
"""

import os, sys, json, argparse
import numpy as np
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    PIPELINE_RESULTS_DIR, SEGMENTS_DIR,
    TARGET_CHARACTERS,
    VAD_MIN_DURATION, VAD_MAX_DURATION,
    MIN_RMS, MIN_TEXT_LENGTH, MAX_TEXT_LENGTH,
    MIN_MINUTES_PER_CHARACTER,
    print_header, print_done,
)


def load_labeled_data():
    """加载 Step 2 标注后的数据"""
    path = os.path.join(PIPELINE_RESULTS_DIR, "labeled_segments.json")
    if not os.path.exists(path):
        print(f"❌ 未找到: {path}")
        print("   请先运行: python scripts/step2_sample_labeling.py --apply-map")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compute_audio_quality(item):
    """检查音频质量"""
    import soundfile as sf

    file_path = os.path.join(SEGMENTS_DIR, item["file"])
    if not os.path.exists(file_path):
        return {"error": "file_missing"}

    try:
        audio, sr = sf.read(file_path)
        if len(audio) == 0:
            return {"error": "empty_audio"}

        rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
        peak = float(np.abs(audio).max())
        duration = len(audio) / sr

        # 削波检测
        clipped_ratio = float(np.mean(np.abs(audio) > 0.98))

        return {
            "rms": round(rms, 6),
            "peak": round(peak, 4),
            "duration": round(duration, 2),
            "sample_rate": sr,
            "clipped_ratio": round(clipped_ratio, 4),
        }
    except Exception as e:
        return {"error": str(e)}


def clean_data(data, min_rms=MIN_RMS, min_dur=VAD_MIN_DURATION, max_dur=VAD_MAX_DURATION):
    """
    多轮过滤：
    1. 角色过滤（只保留目标角色）
    2. 文本质量过滤
    3. 音频质量过滤
    4. 文本去重（完全重复的去掉）
    """

    # ---- 第 1 轮：角色过滤 ----
    filtered = [item for item in data if item.get("character", "other") in TARGET_CHARACTERS]
    n_dropped_char = len(data) - len(filtered)
    print(f"  角色过滤: {len(data)} → {len(filtered)} (丢弃 {n_dropped_char} 段非目标角色)")

    # ---- 第 2 轮：文本质量 ----
    text_ok = []
    for item in filtered:
        text = item.get("text", "").strip()
        # 去除纯标点/数字
        if len(text) < MIN_TEXT_LENGTH:
            continue
        if len(text) > MAX_TEXT_LENGTH:
            continue
        # 去除纯噪音标记
        if text in {"", "。", "，", "啊", "嗯", "哦", "呃", "唔"}:
            continue
        text_ok.append(item)
    n_dropped_text = len(filtered) - len(text_ok)
    print(f"  文本过滤: {len(filtered)} → {len(text_ok)} (丢弃 {n_dropped_text} 段)")

    # ---- 第 3 轮：文本去重 ----
    seen_texts = set()
    deduped = []
    for item in text_ok:
        text = item["text"].strip()
        if text not in seen_texts:
            seen_texts.add(text)
            deduped.append(item)
    n_dropped_dup = len(text_ok) - len(deduped)
    print(f"  文本去重: {len(text_ok)} → {len(deduped)} (丢弃 {n_dropped_dup} 段重复)")

    # ---- 第 4 轮：音频质量 ----
    print(f"\n  检查音频质量（可能需要几分钟）...")
    clean = []
    quality_issues = Counter()

    for item in deduped:
        q = compute_audio_quality(item)
        if "error" in q:
            quality_issues[q["error"]] += 1
            continue
        if q["rms"] < min_rms:
            quality_issues["low_rms"] += 1
            continue
        if q["duration"] < min_dur or q["duration"] > max_dur:
            quality_issues["bad_duration"] += 1
            continue
        if q["clipped_ratio"] > 0.1:  # 超过10%削波
            quality_issues["clipped"] += 1
            continue

        # 补充音频元信息
        item["duration"] = q["duration"]
        item["rms"] = q["rms"]
        item["sample_rate"] = q["sample_rate"]
        clean.append(item)

    n_dropped_quality = len(deduped) - len(clean)
    print(f"  音频质量: {len(deduped)} → {len(clean)} (丢弃 {n_dropped_quality} 段)")
    if quality_issues:
        print(f"  质量问题分布: {dict(quality_issues)}")

    return clean


def generate_report(clean_data):
    """生成各角色数据报告"""
    by_char = defaultdict(list)
    for item in clean_data:
        by_char[item["character"]].append(item)

    report = {}
    print(f"\n{'─' * 70}")
    print(f"  {'角色':<10} {'片段数':<8} {'时长':<12} {'状态'}")
    print(f"{'─' * 70}")

    total_ok = 0
    for char in TARGET_CHARACTERS:
        items = by_char.get(char, [])
        total_dur = sum(it.get("duration", 5) for it in items)
        avg_dur = total_dur / len(items) if items else 0
        meets_min = total_dur >= MIN_MINUTES_PER_CHARACTER * 60

        status = "✅ 达标" if meets_min else f"⚠️ 不足{MIN_MINUTES_PER_CHARACTER}分钟"
        if len(items) == 0:
            status = "❌ 无数据"

        print(f"  {char:<10} {len(items):<8} {total_dur/60:>6.1f}分钟   {status}")

        report[char] = {
            "segments": len(items),
            "total_duration_minutes": round(total_dur / 60, 1),
            "avg_duration_seconds": round(avg_dur, 1),
            "meets_minimum": meets_min,
        }
        if meets_min:
            total_ok += 1

    print(f"{'─' * 70}")
    print(f"  达标角色: {total_ok}/{len(TARGET_CHARACTERS)}")
    return report


def main():
    parser = argparse.ArgumentParser(description="数据清洗 & 质量过滤")
    parser.add_argument("--min-minutes", type=int, default=MIN_MINUTES_PER_CHARACTER,
                        help=f"每角色最低分钟数（默认 {MIN_MINUTES_PER_CHARACTER}）")
    parser.add_argument("--skip-audio-check", action="store_true", help="跳过音频质量检查（加速）")
    args = parser.parse_args()

    print_header("Step 3: 数据清洗 & 质量过滤")

    data = load_labeled_data()
    if data is None:
        return

    print(f"  输入: {len(data)} 段")

    if args.skip_audio_check:
        # 快速模式：只做文本过滤
        print("  ⚠️  跳过音频质量检查")
        clean = [
            item for item in data
            if item.get("character") in TARGET_CHARACTERS
            and MIN_TEXT_LENGTH <= len(item.get("text", "").strip()) <= MAX_TEXT_LENGTH
        ]
    else:
        clean = clean_data(data)

    # 保存清洗后数据
    clean_path = os.path.join(PIPELINE_RESULTS_DIR, "clean_data.json")
    with open(clean_path, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)

    # 生成报告
    report = generate_report(clean)
    report_path = os.path.join(PIPELINE_RESULTS_DIR, "clean_stats.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n  清洗后数据: {clean_path}")
    print(f"  统计报告: {report_path}")

    # 警告不足的角色
    low_chars = [c for c, r in report.items() if not r["meets_minimum"]]
    if low_chars:
        print(f"\n  ⚠️  以下角色数据不足 {args.min_minutes} 分钟:")
        for c in low_chars:
            r = report[c]
            print(f"      {c}: {r['segments']}段, {r['total_duration_minutes']}分钟")

    print_header("下一步")
    print("  python scripts/step4_build_kaldi.py")
    print_done()


if __name__ == "__main__":
    main()
