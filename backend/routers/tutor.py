from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from middleware.auth import get_current_user
from services import tutor_service

router = APIRouter(prefix="/tutor", tags=["tutor"])


class ChatMessage(BaseModel):
    role: str       # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []
    week_number: int | None = None


class Citation(BaseModel):
    filename: str
    week_number: int | None
    url: str | None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user_id: str = Depends(get_current_user)):
    try:
        result = tutor_service.ask(
            question=req.question,
            user_id=user_id,
            history=[m.model_dump() for m in req.history],
            week_number=req.week_number,
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
