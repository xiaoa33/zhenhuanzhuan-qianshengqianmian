from fastapi import APIRouter, File, HTTPException, UploadFile

from services.asr_client import call_asr

router = APIRouter()


@router.post("/asr")
async def asr(audio: UploadFile = File(...)):
    try:
        content = await audio.read()
        if not content:
            raise HTTPException(status_code=400, detail="音频文件为空")
        return await call_asr(audio.filename or "recording.webm", content, audio.content_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
