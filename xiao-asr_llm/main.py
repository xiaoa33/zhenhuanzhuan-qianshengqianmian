import json
import logging
import os
import random
import re
import tempfile
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field


load_dotenv()

app = FastAPI(title="xiao-asr_llm")
logger = logging.getLogger("xiao_asr_llm")

EMOTIONS = ("喜悦", "愤怒", "悲伤", "平静")
COSYVOICE_TOKENS = ("breath", "laughter", "sigh", "cough", "lipsmack", "noise")

CHARACTER_NAMES = {
    "zhenhuan": "甄嬛",
    "huafei": "华妃",
    "yixiu": "宜修",
    "meizhuang": "沈眉庄",
    "anlinrong": "安陵容",
    "supeisheng": "苏培盛",
    "yelanyi": "叶澜依",
    "cuijinxi": "崔槿汐",
    "wensichu": "温实初",
    "huanbi": "浣碧",
    "huangshang": "皇上",
    "guojunwang": "果郡王",
}

CHARACTER_STYLE = {
    "zhenhuan": "聪慧克制，语气温婉却有锋芒，常含机心与分寸。",
    "huafei": "骄矜凌厉，爱自称本宫，语气强势，喜怒分明。",
    "yixiu": "端庄隐忍，言语看似平和，实际锋利而疏离。",
    "meizhuang": "清雅稳重，重情重义，言语淡泊而坚定。",
    "anlinrong": "自卑敏感，话语轻柔，常带委屈与试探。",
    "supeisheng": "谨慎圆滑，奴才口吻，处处顾全规矩。",
    "yelanyi": "冷淡直率，不爱虚礼，话语有刺但坦荡。",
    "cuijinxi": "忠心稳妥，善劝诫，话语清醒周到。",
    "wensichu": "温和克制，医者口吻，情感隐忍。",
    "huanbi": "直来直去，护主心切，偶有怨气。",
    "huangshang": "帝王口吻，自称朕，威严克制，圣意难测。",
    "guojunwang": "温柔深情，语气雅致，重情但守分寸。",
}

FALLBACK_REPLIES = {
    "zhenhuan": [
        ("宫中之事，向来人心难测。你既问起，本宫便与你细说一二。", "平静"),
        ("难得你有这份心，本宫听着，倒也觉得宽慰。", "喜悦"),
        ("这深宫冷暖，哪里是一两句话能说尽的……", "悲伤"),
    ],
    "huangshang": [
        ("朕心里有数，此事不必再多言。", "平静"),
        ("放肆！朕的话，难道是说着玩的？", "愤怒"),
        ("你这话倒也有几分道理，朕记下了。", "喜悦"),
    ],
    "huafei": [
        ("哼，你倒是有几分胆色，敢在本宫面前开口。", "平静"),
        ("本宫今日心情尚可，你说吧，有什么事。", "喜悦"),
        ("贱人就是矫情！本宫懒得与你计较。", "愤怒"),
    ],
}

DUET_FALLBACK_REPLIES = {
    "zhenhuan": [
        ("这宫中风声向来细密，你我既在此相逢，有些话便点到为止吧。", "平静"),
        ("你这话听着轻巧，落在本宫心里，却不免叫人添几分寒意。", "悲伤"),
    ],
    "huafei": [
        ("哟，今日倒巧，本宫才走到这儿，就遇见你了。", "平静"),
        ("本宫最不耐烦这些弯弯绕绕，有什么话便直说。", "愤怒"),
    ],
    "yixiu": [
        ("后宫最要紧的是规矩，你我说话，也该顾着分寸。", "平静"),
        ("本宫不过盼着六宫安稳，可人心二字，最是难测。", "悲伤"),
    ],
    "meizhuang": [
        ("难得此处清静，你若有话，不妨慢慢说来。", "平静"),
        ("这宫里真心难得，若能彼此留些余地，也是好的。", "喜悦"),
    ],
    "anlinrong": [
        ("你这样说，倒叫本宫不知该如何接话了。", "悲伤"),
        ("本宫向来人微言轻，有些心思，说了也未必有人懂。", "悲伤"),
    ],
    "supeisheng": [
        ("奴才不过是奉命行事，哪里敢多说半句。", "平静"),
        ("这宫里的话，传出去便变了味，还是谨慎些好。", "平静"),
    ],
    "yelanyi": [
        ("我说话直，你若听着不顺耳，也不必勉强。", "平静"),
        ("这宫里虚情假意太多，倒不如把话说清楚。", "愤怒"),
    ],
    "cuijinxi": [
        ("奴婢瞧着，此事还需从长计议，急不得。", "平静"),
        ("宫墙之内隔墙有耳，您这话还是轻些说才稳妥。", "平静"),
    ],
    "wensichu": [
        ("身在宫中，许多事并非只凭本心便能周全。", "平静"),
        ("有些话说出口便成了伤，不如留三分余地。", "悲伤"),
    ],
    "huanbi": [
        ("我说话直，你可别拿那些虚礼来压我。", "平静"),
        ("哼，这宫里装模作样的人多了，我偏不吃这一套。", "愤怒"),
    ],
    "huangshang": [
        ("朕既听见了，自会有个计较，你不必急着分辩。", "平静"),
        ("放肆，宫中言行皆有规矩，岂容随口妄言。", "愤怒"),
    ],
    "guojunwang": [
        ("今日既然相逢，便把心中所想坦然说了吧。", "平静"),
        ("这宫墙困得住人，却未必困得住一颗真心。", "悲伤"),
    ],
}


class Message(BaseModel):
    role: str
    text: str


class GenerateRequest(BaseModel):
    character_id: str
    user_identity: str = "modern"
    user_role_id: Optional[str] = None
    user_role_name: Optional[str] = None
    history: list[Message] = Field(default_factory=list)
    user_input: str
    preferred_emotion: Optional[str] = None


class SummarizeRequest(BaseModel):
    character_id: str
    messages: list[Message] = Field(default_factory=list)


class DuetRequest(BaseModel):
    my_character_id: str
    other_character_id: str
    context: str = ""
    history: list[Message] = Field(default_factory=list)
    my_turn: bool = True


_asr_model = None


def _character_name(character_id: str) -> str:
    return CHARACTER_NAMES.get(character_id, character_id)


def _strip_json_fence(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    return content.strip()


def _normalize_emotion(value: str | None, text: str = "") -> str:
    if value in EMOTIONS:
        return value
    if any(item in text for item in ("放肆", "岂有此理", "大胆", "休怪", "不饶")):
        return "愤怒"
    if any(item in text for item in ("……", "委屈", "难过", "伤心", "寂寞", "冷暖")):
        return "悲伤"
    if any(item in text for item in ("欢喜", "宽慰", "甚好", "高兴", "有趣")):
        return "喜悦"
    return "平静"


def _clean_display_text(text: str) -> str:
    text = re.sub(r"\[(breath|laughter|sigh|cough|lipsmack|noise)\]", "", text, flags=re.I)
    text = re.sub(r"</?strong>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _clean_for_gpt_sovits(text: str) -> str:
    text = _clean_display_text(text)
    text = re.sub(r"\[[^\]]+\]", "", text)
    text = re.sub(r"\s+", "", text)
    if text and text[-1] not in "。！？…":
        text += "。"
    return text


def _cosyvoice_text(text: str, emotion: str) -> str:
    text = _clean_display_text(text)
    if emotion == "喜悦":
        return f"[laughter]{text}"
    if emotion == "悲伤":
        return f"[sigh]{text}"
    if emotion == "愤怒":
        return f"[breath]{text}"
    return text


def _sanitize_cosyvoice_text(text: str, display_text: str, emotion: str) -> str:
    text = str(text or "").strip()
    if not text:
        return _cosyvoice_text(display_text, emotion)

    text = re.sub(r"\[laugh\]", "[laughter]", text, flags=re.I)
    allowed = "|".join(re.escape(token) for token in COSYVOICE_TOKENS)
    text = re.sub(rf"\[(?!(?:{allowed})\])([^\]]+)\]", "", text, flags=re.I)
    text = re.sub(r"<(?!/?strong\b)[^>]+>", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()

    token_count = 0

    def keep_first_two_tokens(match: re.Match) -> str:
        nonlocal token_count
        token_count += 1
        return match.group(0) if token_count <= 2 else ""

    text = re.sub(rf"\[(?:{allowed})\]", keep_first_two_tokens, text, flags=re.I)

    clean_cosy = _clean_display_text(text).replace(" ", "")
    clean_display = display_text.replace(" ", "")
    if clean_display and clean_cosy != clean_display:
        return _cosyvoice_text(display_text, emotion)
    return text


def _normalize_tts_texts(llm_tts_texts: object, display_text: str, emotion: str) -> dict:
    if not isinstance(llm_tts_texts, dict):
        return _render_tts_texts(display_text, emotion)

    cosyvoice = _sanitize_cosyvoice_text(
        llm_tts_texts.get("cosyvoice", ""),
        display_text,
        emotion,
    )
    gpt_sovits_source = llm_tts_texts.get("gpt_sovits") or display_text
    return {
        "cosyvoice": cosyvoice,
        "gpt_sovits": _clean_for_gpt_sovits(str(gpt_sovits_source)),
    }


def _render_tts_texts(display_text: str, emotion: str) -> dict:
    return {
        "cosyvoice": _cosyvoice_text(display_text, emotion),
        "gpt_sovits": _clean_for_gpt_sovits(display_text),
    }


def _history_text(history: list[Message]) -> str:
    if not history:
        return "无"
    recent = history[-10:]
    lines = []
    for item in recent:
        speaker = "用户" if item.role == "user" else "角色"
        lines.append(f"{speaker}: {item.text}")
    return "\n".join(lines)


def _duet_history_text(history: list[Message]) -> str:
    if not history:
        return "无"
    recent = history[-12:]
    lines = []
    for item in recent:
        speaker = _character_name(item.role)
        lines.append(f"{speaker}: {item.text}")
    return "\n".join(lines)


def _clean_duet_text(text: str, character_id: str) -> str:
    text = _clean_display_text(text)
    character = re.escape(_character_name(character_id))
    character_id_escaped = re.escape(character_id)
    text = re.sub(rf"^\s*(?:{character}|{character_id_escaped})\s*[:：]\s*", "", text)
    text = re.sub(r"^\s*[（(][^）)]{1,12}[）)]\s*", "", text)
    text = text.strip(" \t\r\n\"'“”‘’")
    return text.strip()


def _fallback_generate_duet(req: DuetRequest) -> tuple[str, str]:
    replies = DUET_FALLBACK_REPLIES.get(req.my_character_id)
    if replies:
        own_turns = sum(1 for item in req.history if item.role == req.my_character_id)
        return replies[own_turns % len(replies)]

    character = _character_name(req.my_character_id)
    other = _character_name(req.other_character_id)
    if req.history:
        return f"{character}略一沉吟，道：{other}这话，本也有几分道理，只是宫中行事还需谨慎。", "平静"
    return f"{character}看向{other}，缓缓说道：今日既然相逢，有些话不妨说开。", "平静"


async def _call_llm_json(system_prompt: str, user_prompt: str, max_tokens: int = 320) -> dict | None:
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL")
    if not api_key or not model:
        return None

    base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.75")),
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        return json.loads(_strip_json_fence(content))
    except Exception as exc:
        logger.warning("LLM 调用失败，改用本地 fallback: %s", exc)
        return None


def _fallback_generate(req: GenerateRequest) -> tuple[str, str]:
    replies = FALLBACK_REPLIES.get(req.character_id)
    if not replies:
        character = _character_name(req.character_id)
        replies = [
            (f"{character}听罢，略一沉吟，道：此事还需从长计议。", "平静"),
            (f"你这话倒有几分意思，{character}愿意再听你说下去。", "喜悦"),
            (f"这宫里的事，原不是一句话能说清的……", "悲伤"),
        ]
    lowered = req.user_input
    target_emotion = None
    if any(item in lowered for item in ("生气", "骂", "放肆", "欺负", "不服")):
        target_emotion = "愤怒"
    elif any(item in lowered for item in ("难过", "伤心", "想哭", "离别", "委屈")):
        target_emotion = "悲伤"
    elif any(item in lowered for item in ("开心", "高兴", "赏", "喜欢", "笑")):
        target_emotion = "喜悦"

    if req.preferred_emotion in EMOTIONS:
        target_emotion = req.preferred_emotion

    if target_emotion:
        candidates = [item for item in replies if item[1] == target_emotion]
        if candidates:
            return random.choice(candidates)
        character = _character_name(req.character_id)
        if target_emotion == "喜悦":
            return f"{character}听罢，眉眼间添了几分笑意，道：你这话倒叫人心里宽慰。", "喜悦"
        if target_emotion == "愤怒":
            return f"{character}神色一沉，道：放肆，此话岂是你能随意说的？", "愤怒"
        if target_emotion == "悲伤":
            return f"{character}垂眸良久，轻声道：这宫里的冷暖，终究无人能真正懂得……", "悲伤"
        return f"{character}略一沉吟，道：此事还需从长计议。", "平静"

    return random.choice(replies)


@app.get("/")
def health():
    return {
        "status": "ok",
        "llm_configured": bool((os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")) and (os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL"))),
        "asr_configured": bool(os.getenv("ASR_MODEL") or os.getenv("ASR_MODEL_PATH")),
    }


@app.post("/generate")
async def generate(req: GenerateRequest):
    character = _character_name(req.character_id)
    system_prompt = (
        "你是《甄嬛传》角色对话生成器。只输出 JSON，不要输出 Markdown。"
        "JSON 顶层字段必须是 text、emotion、tts_texts。"
        "text 为角色回复，1 到 3 句，不能包含旁白、舞台说明、表情符号、英文控制 token 或 HTML 标签。"
        "emotion 必须是 喜悦、愤怒、悲伤、平静 四选一。"
        "如果用户指定了期望情绪，回复内容和 emotion 必须匹配该情绪。"
        "tts_texts 必须包含 cosyvoice 和 gpt_sovits。"
        "tts_texts.cosyvoice 必须与 text 是同一句回复，只允许额外插入少量 CosyVoice 控制 token 或 <strong>强调</strong>，不能增删语义。"
        "可用 token 只有 [breath]、[laughter]、[sigh]、[cough]、[lipsmack]、[noise]；每次最多 2 个 token。"
        "token 应按语境放在句首、停顿处或强调处，不要机械固定在句首。"
        "tts_texts.gpt_sovits 必须是干净中文文本，不能包含 token 或 HTML，主要用中文标点控制停顿。"
    )
    identity = "现代来客" if req.user_identity == "modern" else f"宫廷中人：{req.user_role_name or req.user_role_id or '未知'}"
    user_prompt = (
        f"对话角色：{character}\n"
        f"角色风格：{CHARACTER_STYLE.get(req.character_id, '保持古风、贴合人物身份。')}\n"
        f"用户身份：{identity}\n"
        f"最近对话：\n{_history_text(req.history)}\n"
        f"用户本轮输入：{req.user_input}\n"
        f"用户指定情绪：{req.preferred_emotion if req.preferred_emotion in EMOTIONS else '自动判断'}\n"
        "请生成贴合角色身份的回复。"
    )

    llm_data = await _call_llm_json(system_prompt, user_prompt, max_tokens=520)
    if llm_data:
        display_text = _clean_display_text(str(llm_data.get("text", "")).strip())
        emotion = _normalize_emotion(str(llm_data.get("emotion", "")), display_text)
        if req.preferred_emotion in EMOTIONS:
            emotion = req.preferred_emotion
        tts_texts = _normalize_tts_texts(llm_data.get("tts_texts"), display_text, emotion)
    else:
        display_text, emotion = _fallback_generate(req)
        tts_texts = _render_tts_texts(display_text, emotion)

    if not display_text:
        display_text, emotion = _fallback_generate(req)
        tts_texts = _render_tts_texts(display_text, emotion)

    return {
        "text": display_text,
        "emotion": emotion,
        "tts_texts": tts_texts,
    }


@app.post("/generate/duet")
async def generate_duet(req: DuetRequest):
    my_character = _character_name(req.my_character_id)
    other_character = _character_name(req.other_character_id)
    system_prompt = (
        "你是《甄嬛传》双人即兴对话生成器。只输出 JSON，不要输出 Markdown。"
        "JSON 顶层字段必须是 text、emotion。"
        "text 是当前发言角色的一次自然回复，20 到 50 个汉字，1 到 2 句。"
        "只写台词本身，不要写角色名、引号、旁白、舞台说明、动作描写、表情符号、英文控制 token 或 HTML 标签。"
        "回复必须衔接最近一句对话，贴合场景，不要重复历史台词。"
        "emotion 必须是 喜悦、愤怒、悲伤、平静 四选一。"
    )
    user_prompt = (
        f"当前发言角色：{my_character}\n"
        f"当前角色风格：{CHARACTER_STYLE.get(req.my_character_id, '保持古风、贴合人物身份。')}\n"
        f"对方角色：{other_character}\n"
        f"对方角色风格：{CHARACTER_STYLE.get(req.other_character_id, '保持古风、贴合人物身份。')}\n"
        f"场景/话题：{req.context or '两位角色在宫中相遇'}\n"
        f"完整对话历史：\n{_duet_history_text(req.history)}\n"
        "请生成当前发言角色的下一句台词，并判断情绪。"
    )

    llm_data = await _call_llm_json(system_prompt, user_prompt, max_tokens=220)
    if llm_data:
        text = _clean_duet_text(str(llm_data.get("text", "")).strip(), req.my_character_id)
        emotion = _normalize_emotion(str(llm_data.get("emotion", "")), text)
    else:
        text, emotion = _fallback_generate_duet(req)

    if not text:
        text, emotion = _fallback_generate_duet(req)

    return {
        "text": text,
        "emotion": emotion,
    }


@app.post("/summarize")
async def summarize(req: SummarizeRequest):
    character = _character_name(req.character_id)
    system_prompt = (
        "你是《甄嬛传》对话总结器。只输出 JSON，不要输出 Markdown。"
        "JSON 字段必须是 attitude 和 comment。"
        "attitude 不超过 4 个汉字，comment 不超过 20 个汉字，口吻古风。"
    )
    user_prompt = f"角色：{character}\n完整对话：\n{_history_text(req.messages)}"
    llm_data = await _call_llm_json(system_prompt, user_prompt, max_tokens=120)
    if llm_data:
        attitude = str(llm_data.get("attitude", "不置可否")).strip()[:4]
        comment = str(llm_data.get("comment", "此次对话已入宫廷密录")).strip()[:20]
        return {"attitude": attitude, "comment": comment}
    return {"attitude": "不置可否", "comment": "此次对话已入宫廷密录"}


def _get_asr_model():
    global _asr_model
    if _asr_model is not None:
        return _asr_model

    model_name = os.getenv("ASR_MODEL") or os.getenv("ASR_MODEL_PATH")
    if not model_name:
        raise HTTPException(status_code=501, detail="ASR_MODEL 或 ASR_MODEL_PATH 未配置")
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="缺少 faster-whisper 依赖，无法执行 ASR") from exc

    _asr_model = WhisperModel(
        model_name,
        device=os.getenv("ASR_DEVICE", "auto"),
        compute_type=os.getenv("ASR_COMPUTE_TYPE", "auto"),
    )
    return _asr_model


@app.post("/asr")
async def asr(audio: UploadFile = File(...)):
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = Path(tmp.name)

    try:
        model = _get_asr_model()
        segments, info = model.transcribe(
            str(tmp_path),
            language=os.getenv("ASR_LANGUAGE", "zh"),
            vad_filter=True,
        )
        text = "".join(segment.text.strip() for segment in segments).strip()
        return {
            "text": text,
            "language": getattr(info, "language", "zh"),
            "confidence": getattr(info, "language_probability", None),
        }
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass
