from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from middleware.auth import get_current_user
from services import quiz_service

router = APIRouter(prefix="/quiz", tags=["quiz"])


class QuizRequest(BaseModel):
    week_number: int | None = None
    count: int = 5  # 5, 10, or 15


class Citation(BaseModel):
    filename: str
    week_number: int | None
    url: str | None


class Question(BaseModel):
    question: str
    choices: list[str]      # 4 items: ["A. ...", "B. ...", "C. ...", "D. ..."]
    correct_index: int       # 0-3
    explanation: str
    material_id: str | None
    citation: Citation | None


class QuizResponse(BaseModel):
    questions: list[Question]


@router.post("/generate", response_model=QuizResponse)
async def generate_quiz(req: QuizRequest, user_id: str = Depends(get_current_user)):
    try:
        result = quiz_service.generate_quiz(
            user_id=user_id,
            week_number=req.week_number,
            count=req.count,
        )
        return QuizResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
