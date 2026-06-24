"""
Step 4: 构建 CosyVoice Kaldi 格式训练数据
将清洗后的数据转换为 CosyVoice 训练所需的 Kaldi 风格文件。

输入: pipeline_results/clean_data.json  (Step 3 输出)
      segments/                          (音频片段)
输出: cosyvoice_train/
      ├── wav.scp          # utt_id → 音频绝对路径
      ├── text             # utt_id → 文本内容
      ├── utt2spk          # utt_id → speaker_id
      ├── spk2utt          # speaker_id → utt_id列表
      └── instruct         # (可选) utt_id → 指令文本

用法:
    python scripts/step4_build_kaldi.py
    python scripts/step4_build_kaldi.py --with-instruct   # 生成 instruct 文件
    python scripts/step4_build_kaldi.py --split-dev 0.05  # 划分5%验证集
"""

import os, sys, json, argparse, random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    PIPELINE_RESULTS_DIR, SEGMENTS_DIR, COSYVOICE_DATA_DIR,
    TARGET_CHARACTERS,
    print_header, print_done, ensure_dirs,
)


def load_clean_data():
    path = os.path.join(PIPELINE_RESULTS_DIR, "clean_data.json")
    if not os.path.exists(path):
        print(f"❌ 未找到: {path}")
        print("   请先运行: python scripts/step3_clean.py")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_kaldi_files(data, output_dir, with_instruct=False, split_dev=0.0):
    """
    生成 CosyVoice 的 Kaldi 风格文件

    Args:
        data: 清洗后的数据列表
        output_dir: 输出根目录
        with_instruct: 是否生成 instruct 文件
        split_dev: 验证集比例 (0.0 = 全部训练集)
    """
    ensure_dirs(output_dir)

    # 按角色分组
    by_char = defaultdict(list)
    for item in data:
        by_char[item["character"]].append(item)

    # 为每个 utt 生成唯一 ID（拼音化 + 序号）
    # 格式: {role_pinyin}_{index:04d}
    utt2wav = {}
    utt2text = {}
    utt2spk = {}
    spk2utt = defaultdict(list)
    utt2instruct = {}

    # 角色名 → 拼音缩写
    PINYIN_MAP = {
        "甄嬛": "zhenhuan", "华妃·年世兰": "huafei",
        "乌拉那拉·宜修(皇后)": "huanghou",
        "沈眉庄": "meizhuang", "安陵容": "anlingrong", "苏培盛": "supeisheng",
        "叶澜依": "yelanyi", "崔槿汐": "cuijinxi", "温实初": "wenshichu",
        "浣碧": "huanbi", "皇上·爱新觉罗·胤禎": "huangshang",
        "果郡王·允礼": "guojunwang",
        "太后": "taihou", "曹贵人": "caoguiren",
    }

    for character, items in by_char.items():
        pinyin = PINYIN_MAP.get(character, "unknown")
        for i, item in enumerate(items):
            utt_id = f"{pinyin}_{i+1:04d}"

            # 音频文件的绝对路径
            wav_path = os.path.abspath(os.path.join(SEGMENTS_DIR, item["file"]))
            if not os.path.exists(wav_path):
                continue

            utt2wav[utt_id] = wav_path
            utt2text[utt_id] = item["text"]
            utt2spk[utt_id] = character
            spk2utt[character].append(utt_id)

            if with_instruct:
                utt2instruct[utt_id] = generate_instruct(character)

    # 划分训练集/验证集
    all_utts = list(utt2wav.keys())
    if split_dev > 0 and split_dev < 1:
        random.seed(42)
        random.shuffle(all_utts)
        n_dev = max(1, int(len(all_utts) * split_dev))
        dev_utts = set(all_utts[:n_dev])
        train_utts = set(all_utts[n_dev:])

        subsets = {
            "train": train_utts,
            "dev": dev_utts,
        }
    else:
        subsets = {"train": set(all_utts)}

    # 写入文件
    for subset_name, utts in subsets.items():
        sub_dir = os.path.join(output_dir, subset_name)
        ensure_dirs(sub_dir)

        write_scp(os.path.join(sub_dir, "wav.scp"), utt2wav, utts)
        write_scp(os.path.join(sub_dir, "text"), utt2text, utts)
        write_scp(os.path.join(sub_dir, "utt2spk"), utt2spk, utts, key_format="{utt} {value}")
        write_spk2utt(os.path.join(sub_dir, "spk2utt"), spk2utt, utts)

        if with_instruct:
            write_scp(os.path.join(sub_dir, "instruct"), utt2instruct, utts)

    return subsets, spk2utt, by_char


def write_scp(filepath, data_dict, utt_subset=None, key_format="{utt} {value}"):
    """写入 Kaldi 格式文件"""
    with open(filepath, "w", encoding="utf-8") as f:
        for utt_id in sorted(data_dict.keys()):
            if utt_subset is not None and utt_id not in utt_subset:
                continue
            line = key_format.format(utt=utt_id, value=data_dict[utt_id])
            f.write(line + "\n")


def write_spk2utt(filepath, spk2utt, utt_subset=None):
    """写入 spk2utt 文件"""
    with open(filepath, "w", encoding="utf-8") as f:
        for spk in sorted(spk2utt.keys()):
            utts = spk2utt[spk]
            if utt_subset is not None:
                utts = [u for u in utts if u in utt_subset]
            if utts:
                f.write(f"{spk} {' '.join(sorted(utts))}\n")


def generate_instruct(character):
    """为每个角色生成指令文本（用于 instruct TTS）"""
    instructs = {
        "甄嬛": "用甄嬛的语气说话，温柔但坚定，端庄大气。",
        "华妃·年世兰": "用华妃的语气说话，嚣张跋扈，目中无人，语气凌厉。",
        "乌拉那拉·宜修(皇后)": "用皇后的语气说话，表面温和大度，实则暗藏心机。",
        "沈眉庄": "用沈眉庄的语气说话，温婉贤淑，大家闺秀风范。",
        "安陵容": "用安陵容的语气说话，表面柔弱可怜，内心自卑敏感。",
        "苏培盛": "用苏培盛的语气说话，老练圆滑，忠心护主。",
        "叶澜依": "用叶澜依的语气说话，清冷孤傲，不卑不亢。",
        "崔槿汐": "用崔槿汐的语气说话，忠心耿耿，温柔体贴。",
        "温实初": "用温实初的语气说话，老实本分，医者仁心。",
        "浣碧": "用浣碧的语气说话，活泼直率，有时任性。",
        "皇上·爱新觉罗·胤禎": "用皇上的语气说话，威严霸气，君临天下。",
        "果郡王·允礼": "用果郡王的语气说话，风流倜傥，深情款款。",
        "太后": "用太后的语气说话，慈祥威严。",
        "曹贵人": "用曹贵人的语气说话。",
    }
    return instructs.get(character, f"用{character}的语气说话。")


def main():
    parser = argparse.ArgumentParser(description="构建 CosyVoice Kaldi 格式数据")
    parser.add_argument("--with-instruct", action="store_true", help="生成 instruct 文件")
    parser.add_argument("--split-dev", type=float, default=0.05,
                        help="验证集比例（默认 0.05 = 5%%）")
    parser.add_argument("--output-dir", default=COSYVOICE_DATA_DIR, help="输出目录")
    args = parser.parse_args()

    print_header("Step 4: 构建 CosyVoice Kaldi 格式")

    data = load_clean_data()
    if data is None:
        return

    print(f"  输入: {len(data)} 段（{len(set(d['character'] for d in data))} 个角色）")

    subsets, spk2utt, by_char = build_kaldi_files(
        data, args.output_dir,
        with_instruct=args.with_instruct,
        split_dev=args.split_dev,
    )

    # 重新计算统计
    print_statistics(subsets, spk2utt, data)

    print_header("下一步")
    print("  bash scripts/step5_export_parquet.sh")
    print_done()


def print_statistics(subsets, spk2utt, data):
    """打印数据统计"""
    by_char = defaultdict(list)
    for item in data:
        by_char[item["character"]].append(item)

    print(f"\n{'─' * 70}")
    print(f"  {'角色':<10} {'片段数':<10} {'时长':<12}")
    print(f"{'─' * 70}")

    for char in TARGET_CHARACTERS:
        utts = spk2utt.get(char, [])
        total_dur = sum(it.get("duration", 5) for it in by_char.get(char, []))
        print(f"  {char:<10} {len(utts):<10} {total_dur/60:>6.1f}分钟")

    total_utts = sum(len(v) for v in spk2utt.values())
    print(f"{'─' * 70}")
    print(f"  总计: {total_utts} 段")

    print(f"\n  输出目录: {COSYVOICE_DATA_DIR}/")
    for sub in subsets:
        sub_dir = os.path.join(COSYVOICE_DATA_DIR, sub)
        print(f"    {sub}/")
        for fname in ["wav.scp", "text", "utt2spk", "spk2utt"]:
            fpath = os.path.join(sub_dir, fname)
            if os.path.exists(fpath):
                n_lines = sum(1 for _ in open(fpath, encoding="utf-8"))
                print(f"      {fname}  ({n_lines} 行)")


if __name__ == "__main__":
    main()
