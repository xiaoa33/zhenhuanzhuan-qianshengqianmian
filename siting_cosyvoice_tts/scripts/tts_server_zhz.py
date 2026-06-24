#!/usr/bin/env python3
"""
甄嬛传 TTS 语音合成服务 — CosyVoice3 全功能版
==============================================
覆盖: Zero-shot / Instruct(情绪+方言+风格) / Fine-grained(呼吸/笑声/叹息) / 跨语言 / 语速控制

启动方式 (AutoDL 云端):
    conda activate cosyvoice
    cd /root/autodl-tmp
    python tts_server_zhz.py --port 8002 --preload              # 全功能（情绪+精细控制）
    python tts_server_zhz.py --port 8002 --preload --no-emotion # 纯 zero-shot（音色最像）

API 端点:
    POST /synthesize          主接口（yiping-backend 调用）
    GET  /                    服务信息 + 功能清单
    GET  /health              健康检查
    GET  /web                 交互式 Web 演示页面
    GET  /api/speakers        列出已注册角色
    POST /api/instruct        自由 instruct 模式（调试用）
"""

import sys
import argparse
import time
import os
import io
import base64
import re
import json
from pathlib import Path

# ===== CosyVoice =====
COSYVOICE_ROOT = '/root/autodl-tmp/CosyVoice'
sys.path.insert(0, COSYVOICE_ROOT)
sys.path.insert(0, str(Path(COSYVOICE_ROOT) / 'third_party' / 'Matcha-TTS'))

import torch
import torchaudio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from cosyvoice.cli.cosyvoice import AutoModel
from cosyvoice.cli.frontend import CosyVoiceFrontEnd

# ===== Monkey-patch: 修 CosyVoice3 instruct2 不支持 zero_shot_spk_id 的 bug =====
# 原生: instruct2 传了 zero_shot_spk_id → instruct 被忽略（prompt_text 用的是注册时的旧文本）
# 修复: 用 spk2info embedding 做音色（比实时克隆准） + instruct_text 做情绪控制

_orig_frontend_instruct2 = CosyVoiceFrontEnd.frontend_instruct2

def _fixed_frontend_instruct2(self, tts_text, instruct_text, prompt_wav,
                               resample_rate, zero_shot_spk_id):
    if zero_shot_spk_id and zero_shot_spk_id in self.spk2info:
        # spk2info 里存了 embedding + flow 特征（注册时的角色原声参考）
        # 只需把 prompt_text 换成 instruct_text 即可，其余全用 spk2info
        spk = self.spk2info[zero_shot_spk_id]
        # 提取 tts_text 和 instruct_text 的 token
        tts_token, tts_len = self._extract_text_token(tts_text)
        instruct_token, instruct_len = self._extract_text_token(instruct_text)
        mi = {
            **spk,
            'text': tts_token, 'text_len': tts_len,
            'prompt_text': instruct_token, 'prompt_text_len': instruct_len,
        }
        del mi['llm_prompt_speech_token']
        del mi['llm_prompt_speech_token_len']
        return mi
    return _orig_frontend_instruct2(self, tts_text, instruct_text,
                                     prompt_wav, resample_rate, zero_shot_spk_id)

CosyVoiceFrontEnd.frontend_instruct2 = _fixed_frontend_instruct2

# ===== 配置 =====
MODEL_DIR = os.environ.get(
    'COSYVOICE_MODEL_DIR',
    '/root/autodl-tmp/CosyVoice/pretrained_models/Fun-CosyVoice3-0.5B'
)
OUTPUT_DIR = Path('/root/autodl-tmp/tts_outputs')
OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR = '/root/autodl-tmp/data/zero_shot_data'

# ===== 14角色完整数据 =====
CHARACTERS = {
    "zhenhuan": {
        "spk": "甄嬛",
        "prompt_text": "不如你回去时把我抄好的经文送去宝华殿捎给那孩子",
        "prompt_wav": f"{DATA_DIR}/甄嬛/zhenhuan_2069.wav",
    },
    "huangshang": {
        "spk": "皇上",
        "prompt_text": "这几日朕虽然病着心却惦记着你这里你可有再来等朕吗",
        "prompt_wav": f"{DATA_DIR}/皇上·爱新觉罗·胤禎/huangshang_0141.wav",
    },
    "yixiu": {
        "spk": "皇后",
        "prompt_text": "初闻只是感觉清淡闻久了牡丹那种雍容的底蕴才会缓缓渗透出来沁人心脾呀",
        "prompt_wav": f"{DATA_DIR}/乌拉那拉·宜修(皇后)/huanghou_0366.wav",
    },
    "huafei": {
        "spk": "华妃",
        "prompt_text": "哥哥在前朝替皇上效力臣妾在后宫为皇上尽心",
        "prompt_wav": f"{DATA_DIR}/华妃·年世兰/huafei_0087.wav",
    },
    "meizhuang": {
        "spk": "沈眉庄",
        "prompt_text": "臣妾想与其等公主大了再挪腾地方不如现在就让臣妾搬去碎玉轩居住吧",
        "prompt_wav": f"{DATA_DIR}/沈眉庄/meizhuang_0389.wav",
    },
    "anlinrong": {
        "spk": "安陵容",
        "prompt_text": "听闻夏姐姐出身骁勇世家妹妹好生景仰",
        "prompt_wav": f"{DATA_DIR}/安陵容/anlingrong_0016.wav",
    },
    "supeisheng": {
        "spk": "苏培盛",
        "prompt_text": "华妃呃年嫔娘娘来了要求面圣怎么回事啊年嫔娘娘带着江城江慎两位太医来说是一定要见皇上似乎是有急事",
        "prompt_wav": f"{DATA_DIR}/苏培盛/supeisheng_0121.wav",
    },
    "yelanyi": {
        "spk": "叶澜依",
        "prompt_text": "何况这满殿里坐着的人谁知有哪个是口是心非的呢",
        "prompt_wav": f"{DATA_DIR}/叶澜依/yelanyi_0275.wav",
    },
    "cuijinxi": {
        "spk": "崔槿汐",
        "prompt_text": "此番之事奴婢也是有责任的奴婢只是觉得那件衣裳眼熟可怎么也没有想起来那是纯元皇后的旧衣",
        "prompt_wav": f"{DATA_DIR}/崔槿汐/cuijinxi_0372.wav",
    },
    "wensichu": {
        "spk": "温实初",
        "prompt_text": "娘娘素来胃寒若在因为饮食不调而伤了脾胃岂不是亏了身子吗",
        "prompt_wav": f"{DATA_DIR}/温实初/wenshichu_0206.wav",
    },
    "huanbi": {
        "spk": "浣碧",
        "prompt_text": "小主昨日受了惊吓午膳吃不下晚膳也没用",
        "prompt_wav": f"{DATA_DIR}/浣碧/huanbi_0056.wav",
    },
    "guojunwang": {
        "spk": "果郡王",
        "prompt_text": "可是我看不如用漂色玉纤纤更见玉足的雪白纤细之妙",
        "prompt_wav": f"{DATA_DIR}/果郡王·允礼/guojunwang_0023.wav",
    },
    "taihou": {
        "spk": "太后",
        "prompt_text": "身为皇后是要掌管群花而不是一味的修剪终致花叶凋零",
        "prompt_wav": f"{DATA_DIR}/太后/taihou_0275.wav",
    },
    "caoguiren": {
        "spk": "曹贵人",
        "prompt_text": "华妃生怕日后再度失宠其实自从失去丽萍帮助后她便已有心栽培人手",
        "prompt_wav": f"{DATA_DIR}/曹贵人/caoguiren_0244.wav",
    },
}

# ===== emotion → instruct 映射 =====
EMOTION_INSTRUCT = {
    "喜悦": "用开心愉快的语气说话，声音明亮轻快，面带笑意",
    "愤怒": "用愤怒不满的语气说话，声音低沉有力，带威胁感和压迫感",
    "悲伤": "用悲伤哀怨的语气说话，声音轻柔低沉，断断续续，略带哭腔",
    "平静": "",   # 空 = 走 zero-shot 纯音色
}

# ===== 情绪 Speaker 映射（register_emotion_speakers.py 注册后生效）=====
# 4角色 × 4情绪 = 16个专用 speaker，走 zero_shot 音色不丢
EMOTION_SPEAKER_MAP = {
    # 甄嬛
    ("zhenhuan",   "喜悦"): "zhenhuan_joy",
    ("zhenhuan",   "愤怒"): "zhenhuan_anger",
    ("zhenhuan",   "悲伤"): "zhenhuan_sad",
    ("zhenhuan",   "平静"): "zhenhuan_calm",
    # 华妃
    ("huafei",     "喜悦"): "huafei_joy",
    ("huafei",     "愤怒"): "huafei_anger",
    ("huafei",     "悲伤"): "huafei_sad",
    ("huafei",     "平静"): "huafei_calm",
    # 皇上
    ("huangshang", "喜悦"): "huangshang_joy",
    ("huangshang", "愤怒"): "huangshang_anger",
    ("huangshang", "悲伤"): "huangshang_sad",
    ("huangshang", "平静"): "huangshang_calm",
    # 皇后
    ("yixiu",      "喜悦"): "yixiu_joy",
    ("yixiu",      "愤怒"): "yixiu_anger",
    ("yixiu",      "悲伤"): "yixiu_sad",
    ("yixiu",      "平静"): "yixiu_calm",
}

# ===== Fine-grained 控制 token 正则 =====
# CosyVoice3 支持的副语言控制 token
FINE_GRAINED_TOKENS = re.compile(
    r'\[(breath|laughter|cough|noise|sigh|lipsmack|sneeze|sob|yawn)\]|<strong>|</strong>'
)


# ===== Pydantic Models =====
class SynthesizeRequest(BaseModel):
    character_id: str
    text: str
    emotion: str = "平静"
    speed: float = 1.0


class InstructRequest(BaseModel):
    """自由 instruct 模式（调试用）"""
    text: str
    character_id: str
    instruct: str              # 自定义指令，如 "请用东北话表达。"
    speed: float = 1.0


# ===== FastAPI App =====
app = FastAPI(
    title="甄嬛传 TTS 全功能服务",
    description="CosyVoice3 驱动 | Zero-shot + Instruct(情绪/方言/风格) + Fine-grained(呼吸/笑声) + 跨语言 + 语速",
    version="2.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_model = None
USE_EMOTION = True  # --no-emotion 启动时设为 False


def get_model():
    global _model
    if _model is None:
        print(f"⏳ 加载模型: {MODEL_DIR}")
        t0 = time.time()
        _model = AutoModel(model_dir=MODEL_DIR)
        print(f"✅ 加载完成 ({time.time()-t0:.1f}s)")
        print(f"📋 已注册角色: {_model.list_available_spks()}")
    return _model


# ==================== 核心合成引擎 ====================

def _collect(chunks_iter):
    """收集生成器输出，拼接为 tensor"""
    chunks = [r['tts_speech'] for r in chunks_iter]
    if not chunks:
        raise RuntimeError("TTS 生成返回为空")
    return torch.cat(chunks, dim=1)


def synthesize_zero_shot(text: str, spk_name: str, speed: float) -> torch.Tensor:
    """
    Zero-shot 模式：纯角色音色，无情绪控制。
    最快、最稳定，适合"平静"情绪。
    """
    cosyvoice = get_model()
    return _collect(cosyvoice.inference_zero_shot(
        text, '', '', zero_shot_spk_id=spk_name, stream=False, speed=speed))


def synthesize_instruct(text: str, instruct: str, prompt_wav: str,
                        spk_name: str, speed: float) -> torch.Tensor:
    """
    Instruct2 模式：spk2info 提供角色音色，instruct 控制情绪/风格。
    依赖 monkey-patch，修复了原生 CosyVoice3 此模式下 instruct 被忽略的 bug。
    """
    cosyvoice = get_model()
    full_instruct = f"You are a helpful assistant. {instruct}<|endofprompt|>"
    return _collect(cosyvoice.inference_instruct2(
        text, full_instruct, prompt_wav,
        zero_shot_spk_id=spk_name, stream=False, speed=speed))


def synthesize_fine_grained(text: str, prompt_wav: str,
                             spk_name: str, speed: float) -> torch.Tensor:
    """Fine-grained 模式：prompt_wav 提供音色参考，文本含控制 token"""
    cosyvoice = get_model()
    cv3_text = f"You are a helpful assistant.<|endofprompt|>{text}"
    return _collect(cosyvoice.inference_cross_lingual(
        cv3_text, prompt_wav, zero_shot_spk_id=spk_name,
        stream=False, speed=speed))


def synthesize_cross_lingual(text: str, prompt_wav: str,
                              spk_name: str, speed: float) -> torch.Tensor:
    """跨语言合成"""
    cosyvoice = get_model()
    cv3_text = f"You are a helpful assistant.<|endofprompt|>{text}"
    return _collect(cosyvoice.inference_cross_lingual(
        cv3_text, prompt_wav, zero_shot_spk_id=spk_name,
        stream=False, speed=speed))


def smart_synthesize(text: str, char: dict, emotion: str, speed: float,
                     character_id: str = ''):
    """
    智能路由。
      1. 情绪 speaker 命中 → zero_shot（音色最像）
      2. fine-grained token → fine_grained
      3. 跨语言标签 → cross_lingual
      4. 情绪 instruct → instruct2
      5. 默认 → zero_shot
    """
    spk_name = char["spk"]

    # --no-emotion 模式：全走 zero_shot
    if not USE_EMOTION:
        speech = synthesize_zero_shot(text, spk_name, speed)
        return speech, "zero_shot"

    # 路由 0: 情绪 speaker（最高优先级，zero_shot 不丢音色）
    emo_spk = EMOTION_SPEAKER_MAP.get((character_id, emotion))
    if emo_spk:
        cosyvoice = get_model()
        if emo_spk in cosyvoice.list_available_spks():
            speech = synthesize_zero_shot(text, emo_spk, speed)
            return speech, f"emo_spk({emo_spk})"

    prompt_wav = char["prompt_wav"]

    # 路由 1: fine-grained token
    if FINE_GRAINED_TOKENS.search(text):
        speech = synthesize_fine_grained(text, prompt_wav, spk_name, speed)
        return speech, "fine_grained"

    # 路由 2: 跨语言标签
    if re.search(r'<\|[a-z]{2,4}\|>', text):
        speech = synthesize_cross_lingual(text, prompt_wav, spk_name, speed)
        return speech, "cross_lingual"

    # 路由 3: 情绪 instruct（fallback，非情绪 speaker 角色用）
    instruct = EMOTION_INSTRUCT.get(emotion)
    if instruct:
        speech = synthesize_instruct(text, instruct, prompt_wav, spk_name, speed)
        return speech, f"instruct2({emotion})"

    # 路由 4: zero-shot
    speech = synthesize_zero_shot(text, spk_name, speed)
    return speech, "zero_shot"


# ==================== API 路由 ====================

@app.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    """
    主接口 — yiping-backend 调用。
    请求: { character_id, text, emotion, speed? }
    响应: { audio_base64, format, mode, ... }
    """
    if not req.text.strip():
        raise HTTPException(400, "text 不能为空")
    if req.character_id not in CHARACTERS:
        raise HTTPException(400,
            f"未知角色: {req.character_id}，可选: {list(CHARACTERS.keys())}")
    speed = max(0.5, min(2.0, req.speed))

    char = CHARACTERS[req.character_id]
    cosyvoice = get_model()

    if char["spk"] not in cosyvoice.list_available_spks():
        raise HTTPException(500,
            f"角色 '{char['spk']}' 未注册到 spk2info.pt")

    t0 = time.time()
    try:
        speech, mode = smart_synthesize(
            req.text.strip(), char, req.emotion.strip(), speed,
            character_id=req.character_id)
    except Exception as e:
        raise HTTPException(500, f"合成失败: {str(e)}")

    duration = speech.shape[1] / cosyvoice.sample_rate
    rtf = (time.time() - t0) / duration

    # base64 编码
    buf = io.BytesIO()
    torchaudio.save(buf, speech, cosyvoice.sample_rate, format="wav")
    buf.seek(0)
    audio_b64 = base64.b64encode(buf.read()).decode("utf-8")

    print(f"🎤 [{req.character_id}/{char['spk']}] {mode} speed={speed:.1f} "
          f"\"{req.text[:35]}...\" | {duration:.1f}s | RTF={rtf:.2f} | "
          f"{len(audio_b64)//1024}KB")

    return {
        "audio_base64": audio_b64,
        "format": "wav",
        "character_id": req.character_id,
        "emotion": req.emotion,
        "mode": mode,
        "speed": speed,
        "duration_sec": round(duration, 2),
        "rtf": round(rtf, 2),
    }


@app.post("/synthesize/stream")
async def synthesize_stream(req: SynthesizeRequest):
    """
    流式 TTS — SSE 推送音频块，边生成边播放，降低首播延迟。
    用法和 /synthesize 完全一致，只是返回 SSE 流而非一次性 JSON。
    """
    if not req.text.strip():
        raise HTTPException(400, "text 不能为空")
    if req.character_id not in CHARACTERS:
        raise HTTPException(400,
            f"未知角色: {req.character_id}，可选: {list(CHARACTERS.keys())}")
    speed = max(0.5, min(2.0, req.speed))

    char = CHARACTERS[req.character_id]
    cosyvoice = get_model()

    if char["spk"] not in cosyvoice.list_available_spks():
        raise HTTPException(500,
            f"角色 '{char['spk']}' 未注册到 spk2info.pt")

    spk_name = char["spk"]
    emotion = req.emotion.strip()
    t0 = time.time()

    # 确定 spk_id（情绪 speaker 优先）
    emo_spk = EMOTION_SPEAKER_MAP.get((req.character_id, emotion))
    use_spk = emo_spk if emo_spk and emo_spk in cosyvoice.list_available_spks() else spk_name

    async def event_stream():
        chunk_idx = 0
        total_samples = 0
        # 立即发送 start 事件，告诉前端连接已建立
        yield f"event: start\ndata: {json.dumps({'spk': use_spk})}\n\n"
        try:
            for result in cosyvoice.inference_zero_shot(
                req.text.strip(), '', '',
                zero_shot_spk_id=use_spk, stream=True, speed=speed,
            ):
                speech = result['tts_speech']  # tensor [1, samples]
                total_samples += speech.shape[1]
                dur = speech.shape[1] / cosyvoice.sample_rate

                buf = io.BytesIO()
                torchaudio.save(buf, speech, cosyvoice.sample_rate, format="wav")
                buf.seek(0)
                b64 = base64.b64encode(buf.read()).decode()

                yield f"data: {json.dumps({'i': chunk_idx, 'audio': b64, 'dur': round(dur, 2)})}\n\n"
                chunk_idx += 1

            total_dur = total_samples / cosyvoice.sample_rate
            rtf = (time.time() - t0) / total_dur
            yield f"event: done\ndata: {json.dumps({'chunks': chunk_idx, 'total_dur': round(total_dur, 2), 'rtf': round(rtf, 2), 'spk': use_spk})}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    print(f"🌊 [stream] [{req.character_id}] spk={use_spk} \"{req.text[:30]}...\"")
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/instruct")
async def api_instruct(req: InstructRequest):
    """
    自由 instruct 模式 — 调试/演示用。
    可传入任意 instruct 文本，如 "请用东北话表达。"
    """
    if not req.text.strip():
        raise HTTPException(400, "text 不能为空")
    if req.character_id not in CHARACTERS:
        raise HTTPException(400, f"未知角色: {req.character_id}")

    char = CHARACTERS[req.character_id]
    speed = max(0.5, min(2.0, req.speed))
    cosyvoice = get_model()

    speech = synthesize_instruct(
        req.text.strip(), req.instruct.strip(),
        char["prompt_wav"], char["spk"], speed)

    buf = io.BytesIO()
    torchaudio.save(buf, speech, cosyvoice.sample_rate, format="wav")
    buf.seek(0)
    audio_b64 = base64.b64encode(buf.read()).decode("utf-8")

    duration = speech.shape[1] / cosyvoice.sample_rate
    return {
        "audio_base64": audio_b64,
        "format": "wav",
        "character_id": req.character_id,
        "instruct": req.instruct,
        "speed": speed,
        "duration_sec": round(duration, 2),
    }


@app.get("/api/speakers")
async def api_list_speakers():
    """列出所有已注册角色"""
    cosyvoice = get_model()
    return {
        "registered": cosyvoice.list_available_spks(),
        "supported_characters": list(CHARACTERS.keys()),
    }


@app.get("/")
async def root():
    cosyvoice = get_model()
    return {
        "service": "甄嬛传 TTS 全功能服务",
        "model_dir": MODEL_DIR,
        "emotion_control": USE_EMOTION,
        "mode": "zero_shot only (--no-emotion)" if not USE_EMOTION else "full (zero_shot + instruct2 + fine_grained + cross_lingual)",
        "features": {
            "zero_shot":       "纯角色音色克隆",
            "instruct2":       "情绪控制（喜悦/愤怒/悲伤）+ 方言 + 风格",
            "fine_grained":    "副语言控制：[breath]呼吸 [laughter]笑 [sigh]叹息 [cough]咳嗽 <strong>强调",
            "cross_lingual":   "跨语言：<|en|>英文 <|ja|>日语 <|ko|>韩语",
            "speed":           "语速 0.5~2.0",
        },
        "emotions": list(EMOTION_INSTRUCT.keys()),
        "characters": list(CHARACTERS.keys()),
        "registered_speakers": cosyvoice.list_available_spks(),
        "endpoints": [
            "POST /synthesize",
            "POST /api/instruct",
            "GET  /api/speakers",
            "GET  /web",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


# ==================== Web 演示页面 ====================

WEB_HTML = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>甄嬛传 TTS 演示</title>
<style>
    :root { --bg:#0f172a; --card:#1e293b; --border:#334155; --text:#e2e8f0;
            --muted:#94a3b8; --accent:#38bdf8; --success:#34d399; --danger:#f87171; }
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:'Segoe UI',system-ui,sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }
    .container { max-width:900px; margin:0 auto; padding:20px; }
    h1 { font-size:1.8rem; text-align:center; padding:20px 0 5px;
         background:linear-gradient(135deg,var(--accent),#818cf8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
    .subtitle { text-align:center; color:var(--muted); margin-bottom:20px; font-size:0.85rem; }
    .card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:20px; margin-bottom:16px; }
    .card h2 { font-size:1.1rem; color:var(--accent); margin-bottom:12px; }
    label { display:block; font-size:0.8rem; color:var(--muted); margin:8px 0 4px; }
    textarea, select, input { width:100%; padding:10px; border-radius:8px; border:1px solid var(--border);
        background:var(--bg); color:var(--text); font-size:0.9rem; font-family:inherit; resize:vertical; }
    textarea:focus, select:focus, input:focus { outline:none; border-color:var(--accent); }
    textarea { min-height:70px; }
    .row { display:flex; gap:12px; }
    .row>* { flex:1; }
    .btn { padding:10px 24px; border-radius:8px; border:none; font-size:0.9rem; cursor:pointer; font-weight:600;
           transition:all 0.2s; }
    .btn-primary { background:var(--accent); color:#0f172a; }
    .btn-primary:hover { opacity:0.85; }
    .btn-primary:disabled { opacity:0.5; cursor:not-allowed; }
    .btn-outline { background:transparent; border:1px solid var(--border); color:var(--text); margin-left:8px; }
    .result { margin-top:12px; padding:14px; border-radius:8px; background:rgba(52,211,153,0.08); border:1px solid rgba(52,211,153,0.2); }
    .result audio { width:100%; margin-top:8px; }
    .tag { display:inline-block; padding:2px 8px; border-radius:12px; font-size:0.7rem;
           background:rgba(56,189,248,0.15); color:var(--accent); margin:2px; }
    .preset { font-size:0.75rem; padding:4px 10px; border-radius:14px; cursor:pointer;
              border:1px solid var(--border); background:transparent; color:var(--muted); margin:2px; }
    .preset:hover { border-color:var(--accent); color:var(--accent); }
    #loading { display:none; text-align:center; padding:12px; color:var(--accent); }
    @media (max-width:600px) { .row { flex-direction:column; } }
</style>
</head>
<body>
<div class="container">
    <h1>🎙️ 甄嬛传 TTS 演示</h1>
    <p class="subtitle">CosyVoice3 全功能 | Zero-shot + Instruct(情绪/方言) + Fine-grained(呼吸/笑声) + 跨语言</p>

    <div class="card">
        <h2>📝 语音合成</h2>
        <div class="row">
            <div>
                <label>角色</label>
                <select id="character">
                    <option value="zhenhuan">甄嬛</option><option value="huafei">华妃</option>
                    <option value="huangshang">皇上</option><option value="yixiu">皇后</option>
                    <option value="meizhuang">沈眉庄</option><option value="anlinrong">安陵容</option>
                    <option value="supeisheng">苏培盛</option><option value="yelanyi">叶澜依</option>
                    <option value="cuijinxi">崔槿汐</option><option value="wensichu">温实初</option>
                    <option value="huanbi">浣碧</option><option value="guojunwang">果郡王</option>
                </select>
            </div>
            <div>
                <label>情绪</label>
                <select id="emotion">
                    <option value="喜悦">喜悦</option><option value="愤怒">愤怒</option>
                    <option value="悲伤">悲伤</option><option value="平静" selected>平静</option>
                </select>
            </div>
            <div>
                <label>语速</label>
                <select id="speed">
                    <option value="0.8">0.8x 慢</option><option value="1.0" selected>1.0x 正常</option>
                    <option value="1.2">1.2x 快</option><option value="1.5">1.5x 很快</option>
                </select>
            </div>
        </div>
        <label>文本 <span style="font-weight:normal;color:var(--muted);">（支持 [breath] [laughter] [sigh] [cough] &lt;strong&gt; 标签，自动路由到精细控制管道）</span></label>
        <textarea id="text" placeholder="输入台词..."></textarea>
        <div style="margin-top:12px;">
            <button class="btn btn-primary" onclick="synthesize()">▶ 生成语音</button>
            <button class="btn btn-primary" onclick="synthesizeStream()" style="background:#34d399;color:#0f172a;margin-left:4px;">🌊 流式生成</button>
            <button class="btn btn-outline" id="btn-stop" onclick="stopStream()" style="display:none;">⏹ 停止</button>
        </div>
        <div id="loading">⏳ 合成中... 云端 GPU 推理大约需要 1~3 秒</div>
        <div id="result-area"></div>
    </div>

    <div class="card">
        <h2>⚡ 快捷预设</h2>
        <div>
            <span style="color:var(--muted);font-size:0.75rem;">情绪:</span>
            <button class="preset" onclick="setPreset('贱人就是矫情！','愤怒')">华妃怒斥</button>
            <button class="preset" onclick="setPreset('臣妾参见皇上，愿皇上万福金安。','喜悦')">甄嬛请安</button>
            <button class="preset" onclick="setPreset('这深宫寂寞，连个说话的人都没有……','悲伤')">安陵容伤怀</button>
            <button class="preset" onclick="setPreset('朕乏了，你们都退下吧。','平静')">皇上倦怠</button>
        </div>
        <div style="margin-top:8px;">
            <span style="color:var(--muted);font-size:0.75rem;">精细控制:</span>
            <button class="preset" onclick="setPreset('[breath]贱人就是矫情！','愤怒')">华妃+呼吸</button>
            <button class="preset" onclick="setPreset('[laughter]皇上说笑了，臣妾哪里敢。','喜悦')">甄嬛+轻笑</button>
            <button class="preset" onclick="setPreset('[sigh]嫔妾出身低微，实在不敢奢望……','悲伤')">安陵容+叹息</button>
            <button class="preset" onclick="setPreset('在面对后宫争斗时，她展现了非凡的<strong>勇气</strong>与<strong>智慧</strong>。','平静')">强调语气</button>
        </div>
        <div style="margin-top:8px;">
            <span style="color:var(--muted);font-size:0.75rem;">跨语言:</span>
            <button class="preset" onclick="document.getElementById('text').value='<|en|>Life is what happens when you are busy making other plans.'">英文名言</button>
            <button class="preset" onclick="document.getElementById('text').value='<|ja|>今日はとてもいい天気ですね。'">日语问候</button>
        </div>
    </div>

    <div class="card">
        <h2>🎭 自由 Instruct 模式</h2>
        <label>自定义 instruct（覆盖情绪预设）</label>
        <div class="row">
            <input id="instruct_text" placeholder="如: 请用东北话表达。 / 请用小猪佩奇风格。 / 请非常伤心地说。" style="flex:3;">
            <button class="btn btn-primary" onclick="synthesizeInstruct()" style="flex:0 0 auto;">生成</button>
        </div>
        <div id="instruct-result"></div>
    </div>
</div>

<script>
const BASE = '';

function setPreset(text, emotion) {
    document.getElementById('text').value = text;
    document.getElementById('emotion').value = emotion;
}

async function synthesize() {
    const text = document.getElementById('text').value.trim();
    if (!text) return alert('请输入文本');

    const btn = document.querySelector('.btn-primary');
    const loading = document.getElementById('loading');
    btn.disabled = true; loading.style.display = 'block';
    document.getElementById('result-area').innerHTML = '';

    try {
        const resp = await fetch(BASE + '/synthesize', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({
                character_id: document.getElementById('character').value,
                text: text,
                emotion: document.getElementById('emotion').value,
                speed: parseFloat(document.getElementById('speed').value),
            }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || '未知错误');

        const audioUrl = 'data:audio/wav;base64,' + data.audio_base64;
        document.getElementById('result-area').innerHTML = `
            <div class="result">
                <strong style="color:var(--success);">✅ 生成成功</strong>
                <span class="tag">${data.mode}</span>
                <span class="tag">${data.duration_sec}s</span>
                <span class="tag">RTF ${data.rtf}</span>
                <audio controls autoplay src="${audioUrl}"></audio>
            </div>`;
    } catch(e) {
        document.getElementById('result-area').innerHTML =
            `<div style="color:var(--danger);margin-top:8px;">❌ ${e.message}</div>`;
    } finally {
        btn.disabled = false; loading.style.display = 'none';
    }
}

async function synthesizeInstruct() {
    const text = document.getElementById('text').value.trim();
    const instruct = document.getElementById('instruct_text').value.trim();
    if (!text || !instruct) return alert('请填写文本和 instruct');

    const resultEl = document.getElementById('instruct-result');
    resultEl.innerHTML = '<div style="color:var(--accent);">⏳ 生成中...</div>';

    try {
        const resp = await fetch(BASE + '/api/instruct', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({
                character_id: document.getElementById('character').value,
                text: text,
                instruct: instruct,
                speed: parseFloat(document.getElementById('speed').value),
            }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || '未知错误');

        const audioUrl = 'data:audio/wav;base64,' + data.audio_base64;
        resultEl.innerHTML = `
            <div class="result">
                <strong style="color:var(--success);">✅ Instruct 生成成功</strong>
                <span class="tag">${data.instruct}</span>
                <span class="tag">${data.duration_sec}s</span>
                <audio controls autoplay src="${audioUrl}"></audio>
            </div>`;
    } catch(e) {
        resultEl.innerHTML = `<div style="color:var(--danger);">❌ ${e.message}</div>`;
    }
}

let streamAbort = null;
let streamAudioCtx = null;
let streamNextTime = 0;

async function synthesizeStream() {
    const text = document.getElementById('text').value.trim();
    if (!text) return alert('请输入文本');

    const resultEl = document.getElementById('result-area');
    const stopBtn = document.getElementById('btn-stop');
    resultEl.innerHTML = '';
    streamAbort = new AbortController();
    streamAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
    streamNextTime = streamAudioCtx.currentTime + 0.05;
    let chunkCount = 0;

    stopBtn.style.display = 'inline-block';
    resultEl.innerHTML = '<div style="color:var(--accent);">🌊 流式生成中... <span id="chunk-num">0</span> chunks | 首块播放中...</div><div id="stream-progress"></div>';

    try {
        const resp = await fetch(BASE + '/synthesize/stream', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({
                character_id: document.getElementById('character').value,
                text: text,
                emotion: document.getElementById('emotion').value,
                speed: parseFloat(document.getElementById('speed').value),
            }),
            signal: streamAbort.signal,
        });

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, {stream: true});

            const lines = buffer.split('\n');
            buffer = lines.pop();
            for (const line of lines) {
                if (line.startsWith('event: start')) {
                    const d = JSON.parse(line.split('data: ')[1] || '{}');
                    document.getElementById('stream-progress').innerHTML =
                        `<span class="tag">已连接 | spk: ${d.spk}</span>`;
                } else if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));
                    if (data.audio) {
                        chunkCount++;
                        document.getElementById('chunk-num').textContent = chunkCount;
                        document.getElementById('stream-progress').innerHTML +=
                            `<span class="tag">#${data.i} ${data.dur}s</span>`;
                        // 立即解码并调度播放，不等后续 chunk
                        playChunkNow(data.audio);
                    }
                } else if (line.startsWith('event: done')) {
                    document.getElementById('result-area').innerHTML +=
                        `<div class="result"><strong style="color:var(--success);">✅ 流式完成</strong>
                        <span class="tag">${chunkCount} chunks</span></div>`;
                } else if (line.startsWith('event: error')) {
                    const err = JSON.parse(line.split('data: ')[1]);
                    throw new Error(err.error);
                }
            }
        }
    } catch(e) {
        if (e.name !== 'AbortError') {
            resultEl.innerHTML += `<div style="color:var(--danger);margin-top:8px;">❌ ${e.message}</div>`;
        }
    } finally {
        stopBtn.style.display = 'none';
        streamAbort = null;
    }
}

function playChunkNow(audioBase64) {
    // 解码 base64 wav → AudioBuffer → 调度播放
    const wavUrl = 'data:audio/wav;base64,' + audioBase64;
    fetch(wavUrl).then(r => r.arrayBuffer()).then(buf =>
        streamAudioCtx.decodeAudioData(buf, (decoded) => {
            const src = streamAudioCtx.createBufferSource();
            src.buffer = decoded;
            src.connect(streamAudioCtx.destination);
            const t = Math.max(streamAudioCtx.currentTime, streamNextTime);
            src.start(t);
            streamNextTime = t + decoded.duration;
        })
    );
}

function stopStream() {
    if (streamAbort) { streamAbort.abort(); streamAbort = null; }
    if (streamAudioCtx) { streamAudioCtx.close(); streamAudioCtx = null; }
}
</script>
</body>
</html>
"""


@app.get("/web", response_class=HTMLResponse)
async def web_demo():
    """交互式 Web 演示页面"""
    return HTMLResponse(content=WEB_HTML)


# ==================== 启动 ====================

def main():
    global _model, MODEL_DIR, USE_EMOTION

    parser = argparse.ArgumentParser(description="甄嬛传 TTS 全功能服务")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--model_dir", default=MODEL_DIR)
    parser.add_argument("--preload", action="store_true")
    parser.add_argument("--no-emotion", action="store_true",
                        help="禁用情绪控制，全部走 zero_shot（角色音色最像）")
    args = parser.parse_args()

    MODEL_DIR = args.model_dir
    USE_EMOTION = not args.no_emotion

    if args.preload:
        print("🚀 预加载...")
        _model = get_model()

    emotion_status = "❌ 禁用 (纯 zero_shot)" if not USE_EMOTION else "✅ 启用 (zero_shot + instruct2 + fine_grained)"
    print(f"""
{'='*55}
  甄嬛传 TTS 全功能服务  v2.1
  http://{args.host}:{args.port}
  API 文档:  http://{args.host}:{args.port}/docs
  Web 演示:  http://{args.host}:{args.port}/web
{'='*55}
  情绪控制: {emotion_status}
{'='*55}
""")

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
