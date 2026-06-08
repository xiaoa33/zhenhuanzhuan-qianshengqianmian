import logging
from fastapi import APIRouter
from pydantic import BaseModel
from digital_human.sadtalker import generate_video

router = APIRouter()
logger = logging.getLogger(__name__)


class DigitalHumanRequest(BaseModel):
    character_id: str
    audio_url: str


@router.post("/digital-human")
async def digital_human(req: DigitalHumanRequest):
    try:
        video_url = await generate_video(req.character_id, req.audio_url)
        return {"video_url": video_url}
    except Exception as e:
        # 失败时静默降级：返回 null，前端自动显示静态剧照
        logger.warning("数字人生成失败，降级为静态剧照: %s", e)
        return {"video_url": None}
