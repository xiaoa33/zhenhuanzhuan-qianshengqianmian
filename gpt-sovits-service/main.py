import asyncio
import gc
import json
import os
import random
import re
import sys
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


APP_ROOT = Path(__file__).resolve().parents[1]
VIP_ROOT = APP_ROOT.parent
GSV_ROOT = Path(os.getenv("GSV_ROOT", VIP_ROOT / "GPT-SoVITS")).resolve()
GSV_PYTHON = os.getenv("GSV_PYTHON", "/mnt/sdc/zhangyuxuan/envs/zx_VIP/bin/python")
OUTPUT_DIR = Path(os.getenv("GSV_OUTPUT_DIR", VIP_ROOT / "inference_outputs" / "web")).resolve()
EMOTION_SAMPLE_ROOT = Path(os.getenv("GSV_EMOTION_SAMPLE_ROOT", APP_ROOT / "emotion_samples")).resolve()
LIST_DIR = Path(os.getenv("GSV_LIST_DIR", VIP_ROOT / "dataset" / "gpt_sovits_lists" / "by_role")).resolve()

DEFAULT_VERSION = os.getenv("GSV_VERSION", "v4")
FALLBACK_VERSION = os.getenv("GSV_FALLBACK_VERSION", "v2ProPlus")
GPT_EPOCH = os.getenv("GSV_GPT_EPOCH", "10")
SOVITS_EPOCH = os.getenv("GSV_SOVITS_EPOCH", "10")
DEVICE = os.getenv("GSV_DEVICE", "cuda")
TIMEOUT_SEC = float(os.getenv("GSV_TIMEOUT_SEC", "600"))
BACKEND = os.getenv("GSV_BACKEND", "subprocess").lower()
CACHE_SIZE = int(os.getenv("GSV_CACHE_SIZE", "1"))
SEED = int(os.getenv("GSV_SEED", "1234"))

ROLE_ID_MAP = {
    "anlinrong": "anlingrong",
    "yixiu": "huanghou",
    "wensichu": "wenshichu",
}

EMOTIONS = {"喜悦", "愤怒", "悲伤", "平静"}

app = FastAPI(title="GPT-SoVITS TTS service")
_tts_cache: OrderedDict[tuple[str, str], object] = OrderedDict()
_gpu_lock = asyncio.Lock()
_runtime = None


class SynthesizeRequest(BaseModel):
    character_id: str
    text: str
    emotion: str = "平静"
    engine: Optional[str] = None
    version: Optional[str] = None


def _gsv_role(character_id: str) -> str:
    return ROLE_ID_MAP.get(character_id, character_id)


def _clean_text_for_gpt_sovits(text: str) -> str:
    text = re.sub(r"\[(breath|laughter|sigh|cough|lipsmack|noise)\]", "", text, flags=re.I)
    text = re.sub(r"\[[^\]]+\]", "", text)
    text = re.sub(r"</?strong>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", "", text)
    if text and text[-1] not in "。！？…":
        text += "。"
    return text


def _role_list_path(gsv_role: str) -> Path:
    path = LIST_DIR / f"{gsv_role}_all.list"
    if not path.exists():
        raise FileNotFoundError(f"角色 list 不存在: {path}")
    return path


def _load_role_refs(gsv_role: str) -> list[tuple[Path, str]]:
    refs: list[tuple[Path, str]] = []
    with _role_list_path(gsv_role).open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("|", 3)
            if len(parts) != 4:
                continue
            wav_path = Path(parts[0])
            prompt_text = parts[3]
            if wav_path.exists() and prompt_text:
                refs.append((wav_path, prompt_text))
    if not refs:
        raise FileNotFoundError(f"角色 {gsv_role} 没有可读参考音频")
    return refs


def _ref_text_by_basename(gsv_role: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    with _role_list_path(gsv_role).open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("|", 3)
            if len(parts) == 4 and parts[3]:
                mapping[Path(parts[0]).name] = parts[3]
    return mapping


def _choose_reference(character_id: str, gsv_role: str, emotion: str) -> tuple[Path, str, str]:
    if emotion not in EMOTIONS:
        emotion = "平静"

    text_by_name = _ref_text_by_basename(gsv_role)
    sample_dirs = [
        EMOTION_SAMPLE_ROOT / character_id / emotion,
        EMOTION_SAMPLE_ROOT / gsv_role / emotion,
    ]
    emotion_samples = []
    for sample_dir in sample_dirs:
        if sample_dir.exists():
            emotion_samples.extend(path for path in sample_dir.glob("*.wav") if path.is_file())

    if emotion_samples:
        random.shuffle(emotion_samples)
        for ref_audio in emotion_samples:
            ref_text = text_by_name.get(ref_audio.name)
            if ref_text:
                return ref_audio.resolve(), ref_text, "emotion_sample"

    ref_audio, ref_text = random.choice(_load_role_refs(gsv_role))
    return ref_audio.resolve(), ref_text, "role_list"


async def _run_inference(
    *,
    role: str,
    version: str,
    text: str,
    ref_audio: Path,
    ref_text: str,
    request_id: str,
) -> Path:
    cmd = [
        GSV_PYTHON,
        "scripts/run_role_inference.py",
        "--roles",
        role,
        "--version",
        version,
        "--gpt-epoch",
        GPT_EPOCH,
        "--sovits-epoch",
        SOVITS_EPOCH,
        "--text",
        text,
        "--ref-audio",
        str(ref_audio),
        "--ref-text",
        ref_text,
        "--text-lang",
        "all_zh",
        "--prompt-lang",
        "all_zh",
        "--device",
        DEVICE,
        "--output-dir",
        str(OUTPUT_DIR),
        "--output-suffix",
        request_id,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(GSV_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SEC)
    except asyncio.TimeoutError as exc:
        proc.kill()
        await proc.communicate()
        raise RuntimeError(f"GPT-SoVITS 推理超时: {TIMEOUT_SEC}s") from exc

    if proc.returncode != 0:
        detail = stderr.decode(errors="ignore") or stdout.decode(errors="ignore")
        raise RuntimeError(detail)

    output_wav = (
        OUTPUT_DIR
        / version
        / role
        / f"{role}_{version}_{request_id}_gpt{GPT_EPOCH}_sovits{SOVITS_EPOCH}.wav"
    )
    if not output_wav.exists():
        raise FileNotFoundError(f"GPT-SoVITS 未生成预期音频: {output_wav}")
    return output_wav.resolve()


def _load_runtime():
    global _runtime
    if _runtime is not None:
        return _runtime

    gsv_root = str(GSV_ROOT)
    gsv_pkg = str(GSV_ROOT / "GPT_SoVITS")
    for path in (gsv_pkg, gsv_root):
        if path not in sys.path:
            sys.path.insert(0, path)
    os.chdir(gsv_root)

    from scripts.run_role_inference import (  # noqa: PLC0415
        find_weights,
        patch_torchaudio_load,
        resolve_device,
        write_tts_config,
    )
    from GPT_SoVITS.TTS_infer_pack.TTS import TTS, TTS_Config  # noqa: PLC0415
    import soundfile as sf  # noqa: PLC0415
    import torch  # noqa: PLC0415

    patch_torchaudio_load()
    _runtime = {
        "find_weights": find_weights,
        "resolve_device": resolve_device,
        "write_tts_config": write_tts_config,
        "TTS": TTS,
        "TTS_Config": TTS_Config,
        "sf": sf,
        "torch": torch,
    }
    return _runtime


def _evict_cache_if_needed() -> None:
    while len(_tts_cache) > max(CACHE_SIZE, 0):
        _, old_tts = _tts_cache.popitem(last=False)
        del old_tts
        gc.collect()
        runtime = _runtime
        if runtime is not None and runtime["torch"].cuda.is_available():
            runtime["torch"].cuda.empty_cache()


def _get_cached_tts(role: str, version: str):
    runtime = _load_runtime()
    cache_key = (role, version)
    if cache_key in _tts_cache:
        _tts_cache.move_to_end(cache_key)
        return _tts_cache[cache_key], runtime

    gpt_weight, sovits_weight = runtime["find_weights"](
        GSV_ROOT,
        role,
        version,
        int(GPT_EPOCH),
        int(SOVITS_EPOCH),
    )
    device, is_half = runtime["resolve_device"](DEVICE)
    config_path = OUTPUT_DIR / "_configs" / version / role / "tts_infer.yaml"
    runtime["write_tts_config"](config_path, GSV_ROOT, version, gpt_weight, sovits_weight, device, is_half)

    tts = runtime["TTS"](runtime["TTS_Config"](str(config_path)))
    _tts_cache[cache_key] = tts
    _tts_cache.move_to_end(cache_key)
    _evict_cache_if_needed()
    return tts, runtime


def _run_cached_tts_sync(
    *,
    role: str,
    version: str,
    text: str,
    ref_audio: Path,
    ref_text: str,
    request_id: str,
) -> Path:
    tts, runtime = _get_cached_tts(role, version)
    role_output_dir = OUTPUT_DIR / version / role
    role_output_dir.mkdir(parents=True, exist_ok=True)
    output_wav = role_output_dir / f"{role}_{version}_{request_id}_gpt{GPT_EPOCH}_sovits{SOVITS_EPOCH}.wav"

    result = list(
        tts.run(
            {
                "text": text,
                "text_lang": "all_zh",
                "ref_audio_path": str(ref_audio),
                "prompt_text": ref_text,
                "prompt_lang": "all_zh",
                "top_k": int(os.getenv("GSV_TOP_K", "15")),
                "top_p": float(os.getenv("GSV_TOP_P", "1.0")),
                "temperature": float(os.getenv("GSV_TEMPERATURE", "1.0")),
                "text_split_method": os.getenv("GSV_TEXT_SPLIT_METHOD", "cut5"),
                "batch_size": int(os.getenv("GSV_BATCH_SIZE", "1")),
                "batch_threshold": 0.75,
                "split_bucket": True,
                "speed_factor": float(os.getenv("GSV_SPEED_FACTOR", "1.0")),
                "fragment_interval": float(os.getenv("GSV_FRAGMENT_INTERVAL", "0.3")),
                "seed": SEED,
                "parallel_infer": os.getenv("GSV_PARALLEL_INFER", "true").lower() != "false",
                "repetition_penalty": float(os.getenv("GSV_REPETITION_PENALTY", "1.35")),
                "sample_steps": int(os.getenv("GSV_SAMPLE_STEPS", "32")),
                "super_sampling": False,
                "return_fragment": False,
                "streaming_mode": False,
            }
        )
    )
    if not result:
        raise RuntimeError(f"GPT-SoVITS 没有生成音频: {role}")

    sr, audio = result[-1]
    runtime["sf"].write(str(output_wav), audio, sr)
    metadata = {
        "role": role,
        "version": version,
        "output_wav": str(output_wav),
        "sample_rate": sr,
        "text": text,
        "reference_audio": str(ref_audio),
        "reference_text": ref_text,
        "backend": "persistent",
    }
    metadata_text = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    output_wav.with_suffix(".json").write_text(metadata_text, encoding="utf-8")
    return output_wav.resolve()


async def _run_inference_persistent(
    *,
    role: str,
    version: str,
    text: str,
    ref_audio: Path,
    ref_text: str,
    request_id: str,
) -> Path:
    async with _gpu_lock:
        return await asyncio.to_thread(
            _run_cached_tts_sync,
            role=role,
            version=version,
            text=text,
            ref_audio=ref_audio,
            ref_text=ref_text,
            request_id=request_id,
        )


async def _synthesize_with_fallback(req: SynthesizeRequest, version: str) -> tuple[Path, str, Path, str, str]:
    role = _gsv_role(req.character_id)
    text = _clean_text_for_gpt_sovits(req.text)
    if not text:
        raise ValueError("待合成文本为空")

    ref_audio, ref_text, ref_source = _choose_reference(req.character_id, role, req.emotion)
    request_id = uuid.uuid4().hex
    runner = _run_inference_persistent if BACKEND == "persistent" else _run_inference
    output_wav = await runner(
        role=role,
        version=version,
        text=text,
        ref_audio=ref_audio,
        ref_text=ref_text,
        request_id=request_id,
    )
    return output_wav, role, ref_audio, ref_text, ref_source


@app.get("/")
def health():
    return {
        "status": "ok",
        "gsv_root": str(GSV_ROOT),
        "emotion_sample_root": str(EMOTION_SAMPLE_ROOT),
        "output_dir": str(OUTPUT_DIR),
        "default_version": DEFAULT_VERSION,
        "backend": BACKEND,
        "cache_size": CACHE_SIZE,
        "cached_models": [f"{role}:{version}" for role, version in _tts_cache.keys()],
    }


@app.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    if req.engine and req.engine not in {"gpt_sovits", "gpt-sovits"}:
        raise HTTPException(status_code=400, detail="此服务只支持 engine=gpt_sovits")

    version = req.version or DEFAULT_VERSION
    try:
        try:
            output_wav, role, ref_audio, ref_text, ref_source = await _synthesize_with_fallback(req, version)
        except Exception:
            if not FALLBACK_VERSION or version == FALLBACK_VERSION:
                raise
            output_wav, role, ref_audio, ref_text, ref_source = await _synthesize_with_fallback(req, FALLBACK_VERSION)
            version = FALLBACK_VERSION

        return {
            "audio_path": str(output_wav),
            "engine": "gpt_sovits",
            "role": role,
            "version": version,
            "reference_audio": str(ref_audio),
            "reference_text": ref_text,
            "reference_source": ref_source,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
