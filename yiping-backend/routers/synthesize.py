from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.tts_client import call_synthesize

router = APIRouter()


class SynthesizeRequest(BaseModel):
    character_id: str
    text: str
    emotion: str


@router.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    try:
        audio_url = await call_synthesize(req.model_dump())
        return {"audio_url": audio_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
