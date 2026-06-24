"""
Step 2: 角色标注辅助工具
从 Step 1 的输出中，为每个 speaker 随机抽样 N 条供人工试听，
并提供关键词自动提示以加速标注。

输出:
    pipeline_results/samples_for_labeling.json  — 供试听的样本
    pipeline_results/speaker_map_template.json  — 待填写的映射表模板
    pipeline_results/auto_hints.json            — 关键词自动提示结果

用法:
    python scripts/step2_sample_labeling.py                        # 抽样 + 提示
    python scripts/step2_sample_labeling.py --apply-map            # 应用已填写的映射表
    python scripts/step2_sample_labeling.py --samples 15           # 每人抽样15条
"""

import os, sys, json, random, argparse
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    PIPELINE_RESULTS_DIR, CHARACTER_KEYWORDS, TARGET_CHARACTERS,
    print_header, print_done,
)


def load_segments():
    """加载 Step 1 输出的全部片段"""
    path = os.path.join(PIPELINE_RESULTS_DIR, "all_segments.json")
    if not os.path.exists(path):
        print(f"❌ 未找到: {path}")
        print("   请先运行: python scripts/step1_pipeline.py")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sample_for_labeling(data, samples_per_speaker=10):
    """为每个 speaker 随机抽样"""
    spk_data = defaultdict(list)
    for item in data:
        spk_data[item["speaker"]].append(item)

    samples = {}
    for spk, items in spk_data.items():
        samples[spk] = random.sample(items, min(samples_per_speaker, len(items)))

    return samples, spk_data


def auto_hint(data):
    """
    基于关键词为每个 speaker 猜测角色。
    注意：这仅是提示，不能替代人工确认！
    """
    spk_texts = defaultdict(list)
    for item in data:
        spk_texts[item["speaker"]].append(item["text"])

    hints = {}
    for spk, texts in spk_texts.items():
        all_text = " ".join(texts)
        scores = {}
        for char, keywords in CHARACTER_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in all_text)
            if score > 0:
                scores[char] = score
        if scores:
            best = max(scores, key=scores.get)
            second = sorted(scores, key=scores.get, reverse=True)
            hints[spk] = {
                "best_guess": best,
                "confidence": "high" if len(second) == 1 or scores[best] >= scores[second[1]] * 2 else "low",
                "all_scores": dict(sorted(scores.items(), key=lambda x: -x[1])),
            }
        else:
            hints[spk] = {"best_guess": None, "confidence": "none", "all_scores": {}}

    return hints


def create_speaker_map_template(spk_data):
    """生成待填写的映射表模板"""
    template = {}
    for spk in sorted(spk_data.keys()):
        template[spk] = ""  # 空字符串，待用户填写角色名
    return template


def print_samples(samples, spk_data, hints, show_count=5):
    """打印每个 speaker 的样本供人工审阅"""
    print_header("角色标注 — 请逐个 speaker 试听并判断角色")
    print("  对于每个 speaker:")
    print("  1. 试听下面列出的 3~5 条文本/音频")
    print("  2. 判断说话人是谁")
    print("  3. 在 speaker_map.json 中填写对应角色名")
    print("  4. 无法判断的标为 \"other\"（后续会被过滤）\n")

    for spk in sorted(spk_data.keys(), key=lambda s: -len(spk_data[s])):
        n_total = len(spk_data[spk])
        hint = hints.get(spk, {})
        best = hint.get("best_guess", "")

        # 提示信息
        hint_str = ""
        if best and hint.get("confidence") == "high":
            hint_str = f"  🔍 关键词提示: 可能是「{best}」(置信度: 高)"
        elif best:
            hint_str = f"  🔍 关键词提示: 可能是「{best}」(置信度: 低, 需确认)"

        print(f"\n{'─' * 50}")
        print(f"Speaker: {spk}  ({n_total} 段, 共 {sum(s['duration'] for s in spk_data[spk])/60:.1f} 分钟)")
        print(f"{hint_str}")
        print(f"请在 speaker_map.json 中将 \"{spk}\" 映射到角色名:\n")

        for item in samples[spk][:show_count]:
            print(f"  📝 {item['text'][:60]}")
            print(f"     ⏱ {item['duration']}s | 来源: {item['source']}")
        print()


def apply_speaker_map(data, speaker_map):
    """应用映射表，将 speaker_id 转为角色名"""
    mapped = []
    unmapped_speakers = set()

    for item in data:
        spk = item["speaker"]
        char = speaker_map.get(spk, "")
        if char == "" or char is None:
            char = "other"
            unmapped_speakers.add(spk)
        item["character"] = char
        mapped.append(item)

    return mapped, unmapped_speakers


def main():
    parser = argparse.ArgumentParser(description="角色标注辅助工具")
    parser.add_argument("--samples", type=int, default=10, help="每个 speaker 抽样数")
    parser.add_argument("--apply-map", action="store_true", help="应用已填写的 speaker_map.json")
    args = parser.parse_args()

    data = load_segments()
    if data is None:
        return

    # 按 speaker 分组
    spk_data = defaultdict(list)
    for item in data:
        spk_data[item["speaker"]].append(item)

    print_header("Step 2: 角色标注辅助")
    print(f"  总片段数: {len(data)}")
    print(f"  说话人数: {len(spk_data)}")

    map_path = os.path.join(PIPELINE_RESULTS_DIR, "speaker_map.json")

    if args.apply_map:
        # 应用已填写的映射表
        if not os.path.exists(map_path):
            print(f"❌ 映射表不存在: {map_path}")
            print("   请先运行不带 --apply-map 的模式，生成模板后填写")
            return

        with open(map_path, encoding="utf-8") as f:
            speaker_map = json.load(f)

        # 检查填写进度
        filled = sum(1 for v in speaker_map.values() if v)
        print(f"  映射表填写进度: {filled}/{len(speaker_map)}")

        # 应用映射
        mapped_data, unmapped = apply_speaker_map(data, speaker_map)
        output_path = os.path.join(PIPELINE_RESULTS_DIR, "labeled_segments.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(mapped_data, f, ensure_ascii=False, indent=2)

        # 统计
        char_counter = Counter(item["character"] for item in mapped_data)
        print(f"\n  角色分布:")
        for char in TARGET_CHARACTERS + ["other"]:
            cnt = char_counter.get(char, 0)
            dur = sum(item["duration"] for item in mapped_data if item["character"] == char)
            status = "✅" if dur >= 600 else ("⚠️" if dur > 0 else "❌")
            if cnt > 0 or char == "other":
                print(f"    {status} {char}: {cnt}段, {dur/60:.1f}分钟")

        if unmapped:
            print(f"\n  ⚠️  仍有 {len(unmapped)} 个 speaker 未映射: {unmapped}")

        print(f"\n  结果已保存: {output_path}")
        print_header("下一步")
        print("  python scripts/step4_clean.py")
        print_done()
        return

    # === 默认模式：抽样 + 生成模板 ===

    # 随机抽样
    samples, _ = sample_for_labeling(data, args.samples)
    samples_path = os.path.join(PIPELINE_RESULTS_DIR, "samples_for_labeling.json")
    with open(samples_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)

    # 关键词提示
    hints = auto_hint(data)
    hints_path = os.path.join(PIPELINE_RESULTS_DIR, "auto_hints.json")
    with open(hints_path, "w", encoding="utf-8") as f:
        json.dump(hints, f, ensure_ascii=False, indent=2)

    # 映射表模板
    template = create_speaker_map_template(spk_data)
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    # 打印样本供人工审阅
    print_samples(samples, spk_data, hints, show_count=5)

    # 打印操作指引
    print_header("操作指引")
    print(f"  1. 逐个 speaker 试听音频片段")
    print(f"    抽样文件: {samples_path}")
    print(f"  2. 角色关键词提示: {hints_path}")
    print(f"    置信度为 'high' 的可优先确认")
    print(f"  3. 填写映射表: {map_path}")
    print(f'     格式: {{"spk_01": "甄嬛", "spk_02": "华妃", ...}}')
    print(f'     无法确定的标为 "" (将被过滤)')
    print(f"  4. 填写完成后运行:")
    print(f"     python scripts/step2_sample_labeling.py --apply-map")
    print_done()


if __name__ == "__main__":
    main()
