#!/usr/bin/env python3
"""Offline inference for fine-tuned role models.

Example:
  python scripts/run_role_inference.py --roles caoguiren zhenhuan --version v4
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import random
import re
from datetime import datetime
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/numba_cache")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/xdg_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import soundfile as sf
import torch
import torchaudio
import yaml

from GPT_SoVITS.TTS_infer_pack.TTS import TTS, TTS_Config


DEFAULT_TEXT = "今天天气很好，我们来测试一下微调后的声音效果。"


def patch_torchaudio_load() -> None:
    """Avoid torchcodec-backed torchaudio.load in environments with broken FFmpeg libs."""

    def soundfile_load(path, *_, **__):
        audio, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
        tensor = torch.from_numpy(audio.T).contiguous()
        return tensor, sample_rate

    torchaudio.load = soundfile_load


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Run GPT-SoVITS inference for role fine-tuned models.")
    parser.add_argument("--gsv-root", type=Path, default=root)
    parser.add_argument("--roles", nargs="+", help="Role slugs. Default: all *_all.list roles.")
    parser.add_argument("--version", default="v4", choices=["v4", "v2ProPlus"])
    parser.add_argument("--gpt-epoch", type=int, help="Use a specific GPT epoch, for example 5, 10, or 15.")
    parser.add_argument("--sovits-epoch", type=int, help="Use a specific SoVITS epoch.")
    parser.add_argument("--text", default=DEFAULT_TEXT)
    parser.add_argument("--text-lang", default="all_zh")
    parser.add_argument("--prompt-lang", default="all_zh")
    parser.add_argument("--ref-audio", type=Path, help="Use one reference audio for all roles.")
    parser.add_argument("--ref-text", help="Reference text matching --ref-audio.")
    parser.add_argument("--random-ref", action="store_true", help="Randomly choose one valid reference audio per role.")
    parser.add_argument("--ref-seed", type=int, help="Seed for --random-ref. Omit for non-deterministic random choice.")
    parser.add_argument("--output-dir", type=Path, default=root.parent / "inference_outputs")
    parser.add_argument("--output-suffix", default="test")
    parser.add_argument("--timestamp-output", action="store_true", help="Append a timestamp to the output suffix.")
    parser.add_argument("--device", default="auto", help='Use "auto", "cuda", "cuda:0", or "cpu".')
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--top-k", type=int, default=15)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--repetition-penalty", type=float, default=1.35)
    parser.add_argument("--sample-steps", type=int, default=32)
    parser.add_argument("--speed-factor", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--text-split-method", default="cut5")
    parser.add_argument("--no-parallel-infer", action="store_true")
    parser.add_argument("--min-ref-sec", type=float, default=3.0)
    parser.add_argument("--max-ref-sec", type=float, default=10.0)
    return parser.parse_args()


def discover_roles(list_dir: Path, selected: list[str] | None) -> list[str]:
    all_roles = sorted(path.name.removesuffix("_all.list") for path in list_dir.glob("*_all.list"))
    if not all_roles:
        raise FileNotFoundError(f"No *_all.list files found in {list_dir}")
    if selected:
        wanted = set(selected)
        missing = sorted(wanted - set(all_roles))
        if missing:
            raise FileNotFoundError(f"Missing role lists for: {', '.join(missing)}")
        return [role for role in all_roles if role in wanted]
    return all_roles


def latest_by_epoch(paths: list[Path], pattern: str) -> Path:
    regex = re.compile(pattern)
    candidates = []
    for path in paths:
        match = regex.search(path.name)
        if match:
            candidates.append((tuple(int(item) for item in match.groups()), path))
    if not candidates:
        raise FileNotFoundError("No matching weight found")
    return sorted(candidates)[-1][1]


def find_weights(
    root: Path,
    role: str,
    version: str,
    gpt_epoch: int | None = None,
    sovits_epoch: int | None = None,
) -> tuple[Path, Path]:
    exp = f"{role}_{version}"
    if version == "v4":
        gpt_dir = root / "GPT_weights_v4"
        sovits_dir = root / "SoVITS_weights_v4"
        if gpt_epoch is None:
            gpt = latest_by_epoch(list(gpt_dir.glob(f"{exp}-e*.ckpt")), rf"{re.escape(exp)}-e(\d+)\.ckpt$")
        else:
            gpt = gpt_dir / f"{exp}-e{gpt_epoch}.ckpt"
            if not gpt.exists():
                raise FileNotFoundError(gpt)
        sovits_paths = list(sovits_dir.glob(f"{exp}_e*_s*_l*.pth"))
        if sovits_epoch is not None:
            sovits_paths = [path for path in sovits_paths if re.search(rf"{re.escape(exp)}_e{sovits_epoch}_s", path.name)]
        sovits = latest_by_epoch(
            sovits_paths,
            rf"{re.escape(exp)}_e(\d+)_s(\d+)_l(\d+)\.pth$",
        )
        return gpt, sovits

    gpt_dir = root / "GPT_weights_v2ProPlus"
    sovits_dir = root / "SoVITS_weights_v2ProPlus"
    if gpt_epoch is None:
        gpt = latest_by_epoch(list(gpt_dir.glob(f"{exp}-e*.ckpt")), rf"{re.escape(exp)}-e(\d+)\.ckpt$")
    else:
        gpt = gpt_dir / f"{exp}-e{gpt_epoch}.ckpt"
        if not gpt.exists():
            raise FileNotFoundError(gpt)
    sovits_paths = list(sovits_dir.glob(f"{exp}_e*_s*.pth"))
    if sovits_epoch is not None:
        sovits_paths = [path for path in sovits_paths if re.search(rf"{re.escape(exp)}_e{sovits_epoch}_s", path.name)]
    sovits = latest_by_epoch(sovits_paths, rf"{re.escape(exp)}_e(\d+)_s(\d+)\.pth$")
    return gpt, sovits


def role_list_path(root: Path, role: str) -> Path:
    path = root.parent / "dataset" / "gpt_sovits_lists" / "by_role" / f"{role}_all.list"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def collect_references(list_path: Path) -> list[tuple[Path, str, float]]:
    refs: list[tuple[Path, str, float]] = []
    with list_path.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("|", 3)
            if len(parts) != 4:
                continue
            wav_path = Path(parts[0])
            prompt_text = parts[3]
            if not wav_path.exists():
                continue
            try:
                info = sf.info(str(wav_path))
                duration = float(info.duration)
            except Exception:
                continue
            refs.append((wav_path, prompt_text, duration))
    return refs


def choose_reference(
    list_path: Path,
    min_sec: float,
    max_sec: float,
    random_ref: bool = False,
    rng: random.Random | None = None,
) -> tuple[Path, str, float]:
    refs = collect_references(list_path)
    if not refs:
        raise FileNotFoundError(f"No readable reference audio in {list_path}")
    valid = [item for item in refs if min_sec <= item[2] <= max_sec]
    pool = valid or refs
    if random_ref:
        return (rng or random).choice(pool)

    fallback = None
    for item in refs:
        fallback = fallback or item
        if min_sec <= item[2] <= max_sec:
            return item
    return fallback


def resolve_device(device: str) -> tuple[str, bool]:
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    is_half = device.startswith("cuda")
    return device, is_half


def write_tts_config(
    config_path: Path,
    root: Path,
    version: str,
    gpt_weight: Path,
    sovits_weight: Path,
    device: str,
    is_half: bool,
) -> None:
    config = {
        "custom": {
            "device": device,
            "is_half": is_half,
            "version": version,
            "t2s_weights_path": str(gpt_weight),
            "vits_weights_path": str(sovits_weight),
            "cnhuhbert_base_path": str(root / "GPT_SoVITS/pretrained_models/chinese-hubert-base"),
            "bert_base_path": str(root / "GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large"),
        }
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.dump(config, allow_unicode=True, default_flow_style=False), encoding="utf-8")


def infer_one(args: argparse.Namespace, role: str, rng: random.Random | None = None) -> Path:
    root = args.gsv_root.resolve()
    version = args.version
    gpt_weight, sovits_weight = find_weights(root, role, version, args.gpt_epoch, args.sovits_epoch)
    if args.ref_audio:
        ref_audio = args.ref_audio.resolve()
        if not ref_audio.exists():
            raise FileNotFoundError(ref_audio)
        if not args.ref_text:
            raise ValueError("--ref-text is required when --ref-audio is used")
        prompt_text = args.ref_text
        ref_sec = float(sf.info(str(ref_audio)).duration)
    else:
        ref_audio, prompt_text, ref_sec = choose_reference(
            role_list_path(root, role),
            min_sec=args.min_ref_sec,
            max_sec=args.max_ref_sec,
            random_ref=args.random_ref,
            rng=rng,
        )
    device, is_half = resolve_device(args.device)

    role_output_dir = args.output_dir.resolve() / version / role
    role_output_dir.mkdir(parents=True, exist_ok=True)
    config_path = role_output_dir / "tts_infer.yaml"
    write_tts_config(config_path, root, version, gpt_weight, sovits_weight, device, is_half)

    print(f"\nrole={role} version={version}")
    print(f"GPT: {gpt_weight}")
    print(f"SoVITS: {sovits_weight}")
    print(f"ref: {ref_audio} ({ref_sec:.2f}s)")
    print(f"text: {args.text}")
    print(f"device: {device}, is_half={is_half}")

    tts = TTS(TTS_Config(str(config_path)))
    output_suffix = args.output_suffix
    if args.timestamp_output:
        output_suffix = f"{output_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    epoch_suffix = f"gpt{args.gpt_epoch or 'latest'}_sovits{args.sovits_epoch or 'latest'}"
    output_wav = role_output_dir / f"{role}_{version}_{output_suffix}_{epoch_suffix}.wav"
    result = list(
        tts.run(
            {
                "text": args.text,
                "text_lang": args.text_lang,
                "ref_audio_path": str(ref_audio),
                "prompt_text": prompt_text,
                "prompt_lang": args.prompt_lang,
                "top_k": args.top_k,
                "top_p": args.top_p,
                "temperature": args.temperature,
                "text_split_method": args.text_split_method,
                "batch_size": args.batch_size,
                "batch_threshold": 0.75,
                "split_bucket": True,
                "speed_factor": args.speed_factor,
                "fragment_interval": 0.3,
                "seed": args.seed,
                "parallel_infer": not args.no_parallel_infer,
                "repetition_penalty": args.repetition_penalty,
                "sample_steps": args.sample_steps,
                "super_sampling": False,
                "return_fragment": False,
                "streaming_mode": False,
            }
        )
    )
    if not result:
        raise RuntimeError(f"No inference result for {role}")

    sr, audio = result[-1]
    sf.write(str(output_wav), audio, sr)
    metadata = {
        "role": role,
        "version": version,
        "output_wav": str(output_wav),
        "sample_rate": sr,
        "text": args.text,
        "text_lang": args.text_lang,
        "prompt_lang": args.prompt_lang,
        "reference_audio": str(ref_audio),
        "reference_duration_sec": ref_sec,
        "reference_text": prompt_text,
        "gpt_weight": str(gpt_weight),
        "sovits_weight": str(sovits_weight),
        "device": device,
        "is_half": is_half,
        "seed": args.seed,
    }
    metadata_text = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    (role_output_dir / "metadata.json").write_text(metadata_text, encoding="utf-8")
    output_wav.with_suffix(".json").write_text(metadata_text, encoding="utf-8")
    print(f"saved: {output_wav}")

    del tts
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return output_wav


def main() -> None:
    patch_torchaudio_load()
    args = parse_args()
    list_dir = args.gsv_root.resolve().parent / "dataset" / "gpt_sovits_lists" / "by_role"
    roles = discover_roles(list_dir, args.roles)
    rng = random.Random(args.ref_seed) if args.ref_seed is not None else random.Random()
    outputs = [infer_one(args, role, rng=rng) for role in roles]
    print("\nGenerated files:")
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
