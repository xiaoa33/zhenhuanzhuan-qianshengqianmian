from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.llm_client import call_generate

router = APIRouter()


class Message(BaseModel):
    role: str
    text: str


class ChatRequest(BaseModel):
    character_id: str
    user_identity: str = "modern"
    user_role_id: str | None = None
    user_role_name: str | None = None
    history: list[Message] = []
    user_input: str
    preferred_emotion: str | None = None


@router.post("/chat")
async def chat(req: ChatRequest):
    try:
        result = await call_generate(req.model_dump())
        return {
            "text": result["text"],
            "emotion": result["emotion"],
            "tts_texts": result.get("tts_texts") or {},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
