"""
Step 1b: 说话人聚类（Speaker Clustering）
对 step1 产出的每个 segment 提取 speaker embedding → 聚类 → 分配 speaker ID

输入: all_segments.json + segments/
输出: all_segments.json (更新 speaker 字段)

用法:
    python scripts/step1b_speaker_cluster.py
    python scripts/step1b_speaker_cluster.py --n-speakers 30  # 预估说话人数
"""

import os, sys, json, argparse, numpy as np
from collections import Counter
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import PIPELINE_RESULTS_DIR, SEGMENTS_DIR, print_header, print_done


def load_segments():
    path = os.path.join(PIPELINE_RESULTS_DIR, "all_segments.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extract_embeddings(data):
    """用 eres2netv2 逐段提取 speaker embedding"""
    from funasr import AutoModel

    print("加载 eres2netv2 说话人模型...")
    model = AutoModel(model="iic/speech_eres2netv2_sv_zh-cn_16k-common")

    embeddings = []
    valid_indices = []

    for i, item in enumerate(tqdm(data, desc="提取 speaker embedding")):
        wav_path = os.path.join(SEGMENTS_DIR, item["file"])
        if not os.path.exists(wav_path):
            embeddings.append(None)
            continue
        try:
            result = model.generate(input=wav_path)
            if result and len(result) > 0:
                emb = result[0].get("spk_embedding")
                if emb is not None:
                    # CUDA tensor → numpy
                    if hasattr(emb, 'cpu'):
                        emb = emb.cpu().numpy().flatten()
                    embeddings.append(emb)
                    valid_indices.append(i)
                else:
                    embeddings.append(None)
            else:
                embeddings.append(None)
        except Exception as e:
            if i == 0:
                print(f"  ⚠️ 示例错误: {e}")
            embeddings.append(None)

    print(f"  有效 embedding: {len(valid_indices)}/{len(data)}")
    return embeddings, valid_indices


def cluster_embeddings(embeddings, valid_indices, n_speakers=30):
    """对 embedding 做 KMeans 聚类"""
    from sklearn.cluster import KMeans

    X = np.array([embeddings[i] for i in valid_indices])
    print(f"  聚类到 {n_speakers} 个说话人...")
    kmeans = KMeans(n_clusters=n_speakers, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    # 映射回原始索引
    speaker_map = {}
    for idx, label in zip(valid_indices, labels):
        speaker_map[idx] = f"spk_{label:02d}"

    return speaker_map, Counter(labels)


def apply_speakers(data, speaker_map):
    """应用聚类结果到数据"""
    for i, item in enumerate(data):
        item["speaker"] = speaker_map.get(i, "unknown")
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-speakers", type=int, default=30, help="预估说话人数")
    args = parser.parse_args()

    print_header("Step 1b: 说话人聚类")
    data = load_segments()
    print(f"  {len(data)} 段待处理")

    # 提取 embedding
    embeddings, valid_indices = extract_embeddings(data)

    # 聚类
    speaker_map, distribution = cluster_embeddings(embeddings, valid_indices, args.n_speakers)

    # 应用
    data = apply_speakers(data, speaker_map)

    # 保存
    with open(os.path.join(PIPELINE_RESULTS_DIR, "all_segments.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 统计
    spk_counter = Counter(d["speaker"] for d in data)
    print(f"\n  说话人分布 (Top 15):")
    for spk, cnt in spk_counter.most_common(15):
        dur = sum(d["duration"] for d in data if d["speaker"] == spk)
        print(f"    {spk}: {cnt}段, {dur/60:.1f}分钟")

    print_done()
    print("下一步: python scripts/step2_sample_labeling.py")


if __name__ == "__main__":
    main()
