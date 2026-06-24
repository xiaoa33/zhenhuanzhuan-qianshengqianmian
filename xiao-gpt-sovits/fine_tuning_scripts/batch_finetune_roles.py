#!/usr/bin/env python3
"""Batch fine-tune GPT-SoVITS role models without using the WebUI.

Default mode is dry-run. Add --run to execute the generated commands.
Run from the GPT-SoVITS repository root, or pass --gsv-root.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml


SUPPORTED_VERSIONS = ("v4", "v2ProPlus")


@dataclass(frozen=True)
class VersionConfig:
    pretrained_s1: str
    pretrained_s2g: str
    pretrained_s2d: str
    s2_config: str
    s2_script: str
    sovits_weight_dir: str
    gpt_weight_dir: str
    default_s2_epochs: int
    default_s2_batch_size: int
    default_s2_save_every_epoch: int
    default_gpt_epochs: int = 15
    default_gpt_batch_size: int = 40
    default_gpt_save_every_epoch: int = 5


VERSION_CONFIGS: dict[str, VersionConfig] = {
    "v4": VersionConfig(
        pretrained_s1="GPT_SoVITS/pretrained_models/s1v3.ckpt",
        pretrained_s2g="GPT_SoVITS/pretrained_models/gsv-v4-pretrained/s2Gv4.pth",
        pretrained_s2d="GPT_SoVITS/pretrained_models/gsv-v4-pretrained/s2Dv4.pth",
        s2_config="GPT_SoVITS/configs/s2.json",
        s2_script="GPT_SoVITS/s2_train_v3_lora.py",
        sovits_weight_dir="SoVITS_weights_v4",
        gpt_weight_dir="GPT_weights_v4",
        default_s2_epochs=2,
        default_s2_batch_size=9,
        default_s2_save_every_epoch=1,
    ),
    "v2ProPlus": VersionConfig(
        pretrained_s1="GPT_SoVITS/pretrained_models/s1v3.ckpt",
        pretrained_s2g="GPT_SoVITS/pretrained_models/v2Pro/s2Gv2ProPlus.pth",
        pretrained_s2d="GPT_SoVITS/pretrained_models/v2Pro/s2Dv2ProPlus.pth",
        s2_config="GPT_SoVITS/configs/s2v2ProPlus.json",
        s2_script="GPT_SoVITS/s2_train.py",
        sovits_weight_dir="SoVITS_weights_v2ProPlus",
        gpt_weight_dir="GPT_weights_v2ProPlus",
        default_s2_epochs=8,
        default_s2_batch_size=40,
        default_s2_save_every_epoch=4,
    ),
}


def parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[1]
    default_list_dir = default_root.parent / "dataset" / "gpt_sovits_lists" / "by_role"

    parser = argparse.ArgumentParser(
        description="Batch fine-tune GPT-SoVITS by_role/*.list files for v4 and v2ProPlus."
    )
    parser.add_argument("--run", action="store_true", help="Execute commands. Default is dry-run.")
    parser.add_argument("--force", action="store_true", help="Re-run stages even if expected outputs exist.")
    parser.add_argument("--gsv-root", type=Path, default=default_root, help="GPT-SoVITS repository root.")
    parser.add_argument("--list-dir", type=Path, default=default_list_dir, help="Directory containing *_all.list files.")
    parser.add_argument(
        "--versions",
        nargs="+",
        default=list(SUPPORTED_VERSIONS),
        choices=SUPPORTED_VERSIONS,
        help="Versions to train.",
    )
    parser.add_argument(
        "--roles",
        nargs="*",
        help="Role slugs to train, for example: anlingrong zhenhuan. Default: all *_all.list files.",
    )
    parser.add_argument("--python", default=sys.executable, help="Python executable inside the zx_VIP environment.")
    parser.add_argument("--prep-gpus", default="0-1", help="GPU ids for 1A/1B/1C, split by '-'.")
    parser.add_argument("--s2-gpus", default="0-1", help="GPU ids for SoVITS training, split by '-'.")
    parser.add_argument("--gpt-gpus", default="0-1", help="GPU ids for GPT training, split by '-'.")
    parser.add_argument("--s2-epochs-v4", type=int, default=VERSION_CONFIGS["v4"].default_s2_epochs)
    parser.add_argument("--s2-epochs-v2proplus", type=int, default=VERSION_CONFIGS["v2ProPlus"].default_s2_epochs)
    parser.add_argument("--s2-save-every-epoch-v4", type=int, help="SoVITS v4 exported-weight save interval.")
    parser.add_argument(
        "--s2-save-every-epoch-v2proplus",
        type=int,
        help="SoVITS v2ProPlus exported-weight save interval.",
    )
    parser.add_argument("--s2-batch-v4", type=int, default=VERSION_CONFIGS["v4"].default_s2_batch_size)
    parser.add_argument("--s2-batch-v2proplus", type=int, default=VERSION_CONFIGS["v2ProPlus"].default_s2_batch_size)
    parser.add_argument("--gpt-epochs", type=int, default=15)
    parser.add_argument("--gpt-save-every-epoch", type=int, help="GPT exported-weight save interval.")
    parser.add_argument("--gpt-batch", type=int, default=40)
    parser.add_argument("--lora-rank", type=int, default=32, help="Used by v4 only.")
    parser.add_argument("--text-low-lr-rate", type=float, default=0.4, help="Used by v2ProPlus only.")
    parser.add_argument("--skip-prep-if-exists", action="store_true", default=True)
    parser.add_argument(
        "--no-skip-prep-if-exists",
        dest="skip_prep_if_exists",
        action="store_false",
        help="Always run 1A/1B/1C preprocessing.",
    )
    parser.add_argument(
        "--clean-train-ckpt",
        action="store_true",
        help="After successful training, remove large intermediate training checkpoints under logs/<exp>.",
    )
    parser.add_argument(
        "--prune-exported-weights",
        action="store_true",
        help="After each role/version finishes, remove exported weights for that experiment except the configured final epoch.",
    )
    parser.add_argument("--language", default="zh_CN")
    parser.add_argument("--is-half", default="True", choices=("True", "False"))
    return parser.parse_args()


def split_gpus(value: str) -> list[str]:
    gpus = [part.strip() for part in value.replace(",", "-").split("-") if part.strip()]
    if not gpus:
        raise ValueError("GPU list cannot be empty")
    return gpus


def discover_roles(list_dir: Path, selected: list[str] | None) -> list[tuple[str, Path]]:
    all_lists = sorted(list_dir.glob("*_all.list"))
    if selected:
        selected_set = set(selected)
        all_lists = [path for path in all_lists if path.name.removesuffix("_all.list") in selected_set]
        found = {path.name.removesuffix("_all.list") for path in all_lists}
        missing = sorted(selected_set - found)
        if missing:
            raise FileNotFoundError(f"Missing role lists for: {', '.join(missing)}")
    roles = [(path.name.removesuffix("_all.list"), path.resolve()) for path in all_lists]
    if not roles:
        raise FileNotFoundError(f"No *_all.list files found in {list_dir}")
    return roles


def ensure_paths(root: Path, versions: Iterable[str]) -> None:
    required = [
        root / "GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large",
        root / "GPT_SoVITS/pretrained_models/chinese-hubert-base",
    ]
    for version in versions:
        meta = VERSION_CONFIGS[version]
        required.extend(
            [
                root / meta.pretrained_s1,
                root / meta.pretrained_s2g,
                root / meta.s2_config,
            ]
        )
        if version == "v2ProPlus":
            required.append(root / "GPT_SoVITS/pretrained_models/sv/pretrained_eres2netv2w24s4ep4.ckpt")
            required.append(root / meta.pretrained_s2d)
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required files:\n" + "\n".join(missing))


def print_cmd(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    exports = ""
    if env:
        interesting = {
            key: env[key]
            for key in sorted(env)
            if key
            in {
                "CUDA_VISIBLE_DEVICES",
                "_CUDA_VISIBLE_DEVICES",
                "inp_text",
                "inp_wav_dir",
                "exp_name",
                "opt_dir",
                "i_part",
                "all_parts",
                "version",
                "hz",
            }
        }
        exports = " ".join(f"{key}={value!r}" for key, value in interesting.items())
    joined = " ".join(cmd)
    if exports:
        print(f"(cd {cwd} && {exports} {joined})")
    else:
        print(f"(cd {cwd} && {joined})")


def run_command(cmd: list[str], root: Path, env: dict[str, str] | None, dry_run: bool) -> None:
    print_cmd(cmd, root, env)
    if dry_run:
        return
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    merged_env.setdefault("NO_PROXY", "127.0.0.1,localhost")
    merged_env.setdefault("no_proxy", "127.0.0.1,localhost")
    subprocess.run(cmd, cwd=root, env=merged_env, check=True)


def run_parallel_parts(
    root: Path,
    python_exec: str,
    script: str,
    base_env: dict[str, str],
    gpus: list[str],
    dry_run: bool,
) -> None:
    commands: list[tuple[list[str], dict[str, str]]] = []
    for i_part, gpu in enumerate(gpus):
        env = dict(base_env)
        env.update(
            {
                "i_part": str(i_part),
                "all_parts": str(len(gpus)),
                "_CUDA_VISIBLE_DEVICES": gpu,
                "CUDA_VISIBLE_DEVICES": gpu,
            }
        )
        commands.append(([python_exec, "-s", script], env))

    if dry_run:
        for cmd, env in commands:
            print_cmd(cmd, root, env)
        return

    procs: list[subprocess.Popen] = []
    for cmd, env in commands:
        print_cmd(cmd, root, env)
        merged_env = os.environ.copy()
        merged_env.update(env)
        merged_env.setdefault("NO_PROXY", "127.0.0.1,localhost")
        merged_env.setdefault("no_proxy", "127.0.0.1,localhost")
        procs.append(subprocess.Popen(cmd, cwd=root, env=merged_env))

    failures = []
    for proc in procs:
        code = proc.wait()
        if code != 0:
            failures.append(code)
    if failures:
        raise subprocess.CalledProcessError(failures[0], script)


def merge_parts(opt_dir: Path, prefix: str, suffix: str, count: int, header: str | None = None) -> None:
    lines: list[str] = [header] if header else []
    for idx in range(count):
        part_path = opt_dir / f"{prefix}-{idx}{suffix}"
        part_lines = part_path.read_text(encoding="utf-8").strip("\n").split("\n")
        lines.extend(line for line in part_lines if line)
        part_path.unlink()
    out_path = opt_dir / f"{prefix}{suffix}"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def stage_done(path: Path, min_lines: int = 2) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        return len(path.read_text(encoding="utf-8").strip("\n").split("\n")) >= min_lines
    except UnicodeDecodeError:
        return True


def prep_dataset(args: argparse.Namespace, version: str, exp_name: str, list_path: Path, opt_dir: Path) -> None:
    dry_run = not args.run
    gpus = split_gpus(args.prep_gpus)
    base_env = {
        "inp_text": str(list_path),
        "inp_wav_dir": "",
        "exp_name": exp_name,
        "opt_dir": str(opt_dir),
        "is_half": args.is_half,
        "version": version,
        "language": args.language,
        "TEMP": str(args.gsv_root / "TEMP"),
    }

    text_path = opt_dir / "2-name2text.txt"
    if args.skip_prep_if_exists and not args.force and stage_done(text_path):
        print(f"[skip] 1A text features exist: {text_path}")
    else:
        env = dict(base_env)
        env["bert_pretrained_dir"] = "GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large"
        run_parallel_parts(args.gsv_root, args.python, "GPT_SoVITS/prepare_datasets/1-get-text.py", env, gpus, dry_run)
        if not dry_run:
            merge_parts(opt_dir, "2-name2text", ".txt", len(gpus))

    hubert_dir = opt_dir / "4-cnhubert"
    wav32_dir = opt_dir / "5-wav32k"
    if args.skip_prep_if_exists and not args.force and hubert_dir.exists() and wav32_dir.exists():
        print(f"[skip] 1B ssl/wav32k features exist: {hubert_dir}, {wav32_dir}")
    else:
        env = dict(base_env)
        env["cnhubert_base_dir"] = "GPT_SoVITS/pretrained_models/chinese-hubert-base"
        env["sv_path"] = "GPT_SoVITS/pretrained_models/sv/pretrained_eres2netv2w24s4ep4.ckpt"
        run_parallel_parts(
            args.gsv_root,
            args.python,
            "GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py",
            env,
            gpus,
            dry_run,
        )
        if "Pro" in version:
            run_parallel_parts(
                args.gsv_root,
                args.python,
                "GPT_SoVITS/prepare_datasets/2-get-sv.py",
                env,
                gpus,
                dry_run,
            )

    semantic_path = opt_dir / "6-name2semantic.tsv"
    if args.skip_prep_if_exists and not args.force and stage_done(semantic_path):
        print(f"[skip] 1C semantic tokens exist: {semantic_path}")
    else:
        meta = VERSION_CONFIGS[version]
        env = dict(base_env)
        env["pretrained_s2G"] = meta.pretrained_s2g
        env["s2config_path"] = meta.s2_config
        run_parallel_parts(
            args.gsv_root,
            args.python,
            "GPT_SoVITS/prepare_datasets/3-get-semantic.py",
            env,
            gpus,
            dry_run,
        )
        if not dry_run:
            merge_parts(opt_dir, "6-name2semantic", ".tsv", len(gpus), header="item_name\tsemantic_audio")


def get_s2_epochs(args: argparse.Namespace, version: str) -> int:
    return args.s2_epochs_v4 if version == "v4" else args.s2_epochs_v2proplus


def get_s2_batch(args: argparse.Namespace, version: str) -> int:
    return args.s2_batch_v4 if version == "v4" else args.s2_batch_v2proplus


def get_s2_save_every_epoch(args: argparse.Namespace, version: str) -> int:
    if version == "v4":
        return args.s2_save_every_epoch_v4 or VERSION_CONFIGS["v4"].default_s2_save_every_epoch
    return args.s2_save_every_epoch_v2proplus or VERSION_CONFIGS["v2ProPlus"].default_s2_save_every_epoch


def get_gpt_save_every_epoch(args: argparse.Namespace, version: str) -> int:
    return args.gpt_save_every_epoch or VERSION_CONFIGS[version].default_gpt_save_every_epoch


def expected_sovits_weights(root: Path, version: str, exp_name: str, epoch: int, lora_rank: int) -> list[Path]:
    meta = VERSION_CONFIGS[version]
    weight_dir = root / meta.sovits_weight_dir
    if version == "v4":
        return sorted(weight_dir.glob(f"{exp_name}_e{epoch}_s*_l{lora_rank}.pth"))
    return sorted(weight_dir.glob(f"{exp_name}_e{epoch}_s*.pth"))


def write_s2_config(args: argparse.Namespace, version: str, exp_name: str, opt_dir: Path) -> Path:
    meta = VERSION_CONFIGS[version]
    with (args.gsv_root / meta.s2_config).open("r", encoding="utf-8") as f:
        data = json.load(f)

    s2_epochs = get_s2_epochs(args, version)
    data["train"]["batch_size"] = get_s2_batch(args, version)
    data["train"]["epochs"] = s2_epochs
    data["train"]["text_low_lr_rate"] = args.text_low_lr_rate
    data["train"]["pretrained_s2G"] = meta.pretrained_s2g
    data["train"]["pretrained_s2D"] = meta.pretrained_s2d
    data["train"]["if_save_latest"] = True
    data["train"]["if_save_every_weights"] = True
    data["train"]["save_every_epoch"] = get_s2_save_every_epoch(args, version)
    data["train"]["gpu_numbers"] = args.s2_gpus
    data["train"]["grad_ckpt"] = False
    data["train"]["lora_rank"] = str(args.lora_rank)
    data["model"]["version"] = version
    data["data"]["exp_dir"] = str(opt_dir)
    data["s2_ckpt_dir"] = str(opt_dir)
    data["save_weight_dir"] = meta.sovits_weight_dir
    data["name"] = exp_name
    data["version"] = version

    temp_dir = args.gsv_root / "TEMP"
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_path = temp_dir / f"batch_{exp_name}_{version}_s2.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return out_path


def train_sovits(args: argparse.Namespace, version: str, exp_name: str, opt_dir: Path) -> None:
    dry_run = not args.run
    epoch = get_s2_epochs(args, version)
    existing = expected_sovits_weights(args.gsv_root, version, exp_name, epoch, args.lora_rank)
    if existing and not args.force:
        print(f"[skip] SoVITS final weight exists: {existing[-1]}")
        return

    meta = VERSION_CONFIGS[version]
    (args.gsv_root / meta.sovits_weight_dir).mkdir(parents=True, exist_ok=True)
    if args.run:
        (opt_dir / f"logs_s2_{version}").mkdir(parents=True, exist_ok=True)
    if dry_run:
        config_path = args.gsv_root / "TEMP" / f"batch_{exp_name}_{version}_s2.json"
    else:
        config_path = write_s2_config(args, version, exp_name, opt_dir)

    env = {"version": version, "TEMP": str(args.gsv_root / "TEMP"), "language": args.language}
    run_command([args.python, "-s", meta.s2_script, "--config", str(config_path)], args.gsv_root, env, dry_run)


def expected_gpt_weight(root: Path, version: str, exp_name: str, epoch: int) -> Path:
    return root / VERSION_CONFIGS[version].gpt_weight_dir / f"{exp_name}-e{epoch}.ckpt"


def write_gpt_config(args: argparse.Namespace, version: str, exp_name: str, opt_dir: Path) -> Path:
    meta = VERSION_CONFIGS[version]
    with (args.gsv_root / "GPT_SoVITS/configs/s1longer-v2.yaml").open("r", encoding="utf-8") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)

    data["train"]["batch_size"] = args.gpt_batch
    data["train"]["epochs"] = args.gpt_epochs
    data["train"]["save_every_n_epoch"] = get_gpt_save_every_epoch(args, version)
    data["train"]["if_save_every_weights"] = True
    data["train"]["if_save_latest"] = True
    data["train"]["if_dpo"] = False
    data["train"]["half_weights_save_dir"] = meta.gpt_weight_dir
    data["train"]["exp_name"] = exp_name
    data["pretrained_s1"] = meta.pretrained_s1
    data["train_semantic_path"] = str(opt_dir / "6-name2semantic.tsv")
    data["train_phoneme_path"] = str(opt_dir / "2-name2text.txt")
    data["output_dir"] = str(opt_dir / f"logs_s1_{version}")

    temp_dir = args.gsv_root / "TEMP"
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_path = temp_dir / f"batch_{exp_name}_{version}_s1.yaml"
    out_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    return out_path


def train_gpt(args: argparse.Namespace, version: str, exp_name: str, opt_dir: Path) -> None:
    dry_run = not args.run
    expected = expected_gpt_weight(args.gsv_root, version, exp_name, args.gpt_epochs)
    if expected.exists() and not args.force:
        print(f"[skip] GPT final weight exists: {expected}")
        return

    (args.gsv_root / VERSION_CONFIGS[version].gpt_weight_dir).mkdir(parents=True, exist_ok=True)
    if dry_run:
        config_path = args.gsv_root / "TEMP" / f"batch_{exp_name}_{version}_s1.yaml"
    else:
        config_path = write_gpt_config(args, version, exp_name, opt_dir)

    env = {
        "_CUDA_VISIBLE_DEVICES": args.gpt_gpus.replace("-", ","),
        "CUDA_VISIBLE_DEVICES": args.gpt_gpus.replace("-", ","),
        "hz": "25hz",
        "version": version,
        "TEMP": str(args.gsv_root / "TEMP"),
        "language": args.language,
    }
    run_command([args.python, "-s", "GPT_SoVITS/s1_train.py", "--config_file", str(config_path)], args.gsv_root, env, dry_run)


def clean_intermediate_checkpoints(exp_dir: Path, dry_run: bool) -> None:
    targets: set[Path] = set()
    for pattern in (
        "logs_s1_*/ckpt/*.ckpt",
        "logs_s2_*/G_*.pth",
        "logs_s2_*/D_*.pth",
        "logs_s2_*_lora_*/G_*.pth",
        "logs_s2_*_lora_*/D_*.pth",
    ):
        targets.update(exp_dir.glob(pattern))
    if not targets:
        return
    print(f"[clean] {len(targets)} intermediate training checkpoints under {exp_dir}")
    for path in sorted(targets):
        print(f"  remove {path}")
        if not dry_run:
            path.unlink()


def prune_exported_weights(
    root: Path,
    version: str,
    exp_name: str,
    s2_epoch: int,
    gpt_epoch: int,
    lora_rank: int,
    dry_run: bool,
) -> None:
    meta = VERSION_CONFIGS[version]
    targets: list[Path] = []

    if version == "v4":
        keep_sovits = set(root.joinpath(meta.sovits_weight_dir).glob(f"{exp_name}_e{s2_epoch}_s*_l{lora_rank}.pth"))
        sovits_candidates = root.joinpath(meta.sovits_weight_dir).glob(f"{exp_name}_e*_s*_l{lora_rank}.pth")
    else:
        keep_sovits = set(root.joinpath(meta.sovits_weight_dir).glob(f"{exp_name}_e{s2_epoch}_s*.pth"))
        sovits_candidates = root.joinpath(meta.sovits_weight_dir).glob(f"{exp_name}_e*_s*.pth")

    targets.extend(path for path in sovits_candidates if path not in keep_sovits)

    keep_gpt = root / meta.gpt_weight_dir / f"{exp_name}-e{gpt_epoch}.ckpt"
    gpt_candidates = root.joinpath(meta.gpt_weight_dir).glob(f"{exp_name}-e*.ckpt")
    targets.extend(path for path in gpt_candidates if path != keep_gpt)

    if not targets:
        return

    print(f"[prune] remove {len(targets)} non-final exported weights for {exp_name}")
    for path in sorted(targets):
        print(f"  remove {path}")
        if not dry_run:
            path.unlink()


def train_one(args: argparse.Namespace, version: str, role: str, list_path: Path) -> None:
    exp_name = f"{role}_{version}"
    opt_dir = args.gsv_root / "logs" / exp_name
    print("\n" + "=" * 100)
    print(f"role={role} version={version} exp_name={exp_name}")
    print(f"list={list_path}")
    print("=" * 100)

    if args.run:
        opt_dir.mkdir(parents=True, exist_ok=True)
        (args.gsv_root / "TEMP").mkdir(parents=True, exist_ok=True)

    prep_dataset(args, version, exp_name, list_path, opt_dir)
    train_sovits(args, version, exp_name, opt_dir)
    train_gpt(args, version, exp_name, opt_dir)

    if args.clean_train_ckpt:
        clean_intermediate_checkpoints(opt_dir, dry_run=not args.run)

    if args.prune_exported_weights:
        prune_exported_weights(
            args.gsv_root,
            version,
            exp_name,
            get_s2_epochs(args, version),
            args.gpt_epochs,
            args.lora_rank,
            dry_run=not args.run,
        )


def main() -> None:
    args = parse_args()
    args.gsv_root = args.gsv_root.resolve()
    args.list_dir = args.list_dir.resolve()
    if not (args.gsv_root / "webui.py").exists():
        raise FileNotFoundError(f"Not a GPT-SoVITS root: {args.gsv_root}")
    ensure_paths(args.gsv_root, args.versions)
    roles = discover_roles(args.list_dir, args.roles)

    mode = "RUN" if args.run else "DRY-RUN"
    print(f"Mode: {mode}")
    print(f"GPT-SoVITS root: {args.gsv_root}")
    print(f"Role count: {len(roles)}")
    print(f"Versions: {', '.join(args.versions)}")
    print(f"Python: {args.python}")
    if not args.run:
        print("Nothing will be executed. Re-run with --run to start training.")

    for version in args.versions:
        for role, list_path in roles:
            train_one(args, version, role, list_path)


if __name__ == "__main__":
    main()
