from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.llm_client import call_summarize

router = APIRouter()


class Message(BaseModel):
    role: str
    text: str


class SummaryRequest(BaseModel):
    character_id: str
    messages: list[Message]


@router.post("/summary")
async def summary(req: SummaryRequest):
    try:
        result = await call_summarize(req.model_dump())
        rounds = sum(1 for m in req.messages if m.role == "user")
        return {
            "attitude": result["attitude"],
            "comment": result["comment"],
            "rounds": rounds,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
