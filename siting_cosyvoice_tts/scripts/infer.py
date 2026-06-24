#!/usr/bin/env python3
"""
甄嬛传 14 角色 TTS 推理 — 支持 vLLM 加速 + 流式对话

用法:
    python infer.py                              # 普通推理
    python infer.py --vllm                       # vLLM 加速（需先 pip install vllm）
    python infer.py --stream                     # 流式输出
    python infer.py --stream --text "贱人就是矫情" --spk 华妃   # 指定文本和角色
    python infer.py --dialogue                   # 交互式对话模式
"""
import sys, argparse, time
sys.path.append('/root/autodl-tmp/CosyVoice/third_party/Matcha-TTS')
from cosyvoice.cli.cosyvoice import AutoModel
import torch
import torchaudio

MODEL_DIR = '/root/autodl-tmp/CosyVoice/pretrained_models/Fun-CosyVoice3-0.5B'


def load_model(use_vllm=False):
    t0 = time.time()
    cosyvoice = AutoModel(model_dir=MODEL_DIR, load_vllm=use_vllm)
    print(f'✅ 加载完成 ({time.time()-t0:.1f}s)  |  vLLM={use_vllm}')
    print(f'📋 可用角色: {cosyvoice.list_available_spks()}')
    return cosyvoice


def synthesize(cosyvoice, text, spk, stream=False):
    """合成一句话，返回音频 tensor"""
    t0 = time.time()
    wavs = []
    for i, out in enumerate(
        cosyvoice.inference_zero_shot(
            text, '', '',                     # 无需参考音频
            zero_shot_spk_id=spk,
            stream=stream,
        )
    ):
        speech = out['tts_speech']
        dur = speech.shape[1] / cosyvoice.sample_rate
        wavs.append(speech)
        if stream:
            # 流式：拿到一个 chunk 就能立刻播放
            print(f'  📦 chunk {i}: {dur:.2f}s (首包延迟 {time.time()-t0:.1f}s)')

    full = torch.cat(wavs, dim=1) if wavs else None
    if full is not None:
        total_dur = full.shape[1] / cosyvoice.sample_rate
        rtf = (time.time() - t0) / total_dur
        status = '⚡流式' if stream else '📦批量'
        print(f'{status} [{spk}]: {text[:30]}...  |  {total_dur:.1f}s  |  RTF={rtf:.2f}')
    return full


def dialogue_loop(cosyvoice):
    """交互式对话：输入文本 → 流式合成 → 保存为 wav"""
    print('\n🗣️  交互对话模式 (输入 q 退出)')
    print('   格式: 角色名 台词')
    print('   示例: 华妃 贱人就是矫情！\n')

    spks = cosyvoice.list_available_spks()
    n = 0
    while True:
        try:
            line = input('>>> ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line.lower() in ('q', 'quit', 'exit', ''):
            break

        # 解析输入: "华妃 贱人就是矫情"
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            spk, text = parts
            if spk not in spks:
                print(f'  ⚠️ 未知角色: {spk}  |  可选: {spks}')
                continue
        else:
            spk, text = '甄嬛', parts[0]

        audio = synthesize(cosyvoice, text, spk, stream=True)
        if audio is not None:
            fname = f'dialogue_{n:03d}_{spk}.wav'
            torchaudio.save(fname, audio, cosyvoice.sample_rate)
            print(f'  💾 {fname}\n')
            n += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--vllm', action='store_true', help='vLLM 加速 LLM（需 pip install vllm）')
    parser.add_argument('--stream', action='store_true', help='流式输出（边生成边播放）')
    parser.add_argument('--dialogue', action='store_true', help='交互对话模式')
    parser.add_argument('--text', default='臣妾参见皇上，愿皇上万福金安。')
    parser.add_argument('--spk', default='甄嬛')
    parser.add_argument('--output', default=None, help='输出文件名')
    args = parser.parse_args()

    cosyvoice = load_model(use_vllm=args.vllm)

    if args.dialogue:
        dialogue_loop(cosyvoice)
    else:
        out = synthesize(cosyvoice, args.text, args.spk, stream=args.stream)
        if out is not None:
            fname = args.output or f'{args.spk}_output.wav'
            torchaudio.save(fname, out, cosyvoice.sample_rate)
            print(f'💾 {fname}')


if __name__ == '__main__':
    main()
