from datetime import datetime
import json
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session

from app.models.mcqs import MCQ
from app.utils.get_db import get_db
from pydantic import BaseModel


router = APIRouter(prefix="/view-mcqs", tags=["Manage MCQs"])


# --- Pydantic Schemas ---
class QuestionResponse(BaseModel):
    """Schema for a single question (MCQ or True/False)."""

    id: str
    question: str
    options: Optional[List[str]] = None
    answer: str
    type: str


class MCQResponse(BaseModel):
    """Schema for all questions belonging to a video."""

    video_title: str
    questions: List[QuestionResponse]


# --- API Endpoints ---
@router.get("/by-title", response_model=MCQResponse)
def get_mcqs_by_video_title(
    video_title: str = Query(..., description="Title of the video"),
    download: bool = Query(False, description="If true, returns a downloadable JSON file"),
    db: Session = Depends(get_db),
):
    """
    Fetch MCQs and True/False questions for a given video title.

    - Returns structured JSON response via API by default.
    - If `download=true`, generates and returns a downloadable JSON file.
    """
    mcqs = db.query(MCQ).filter(MCQ.video_title == video_title).all()

    if not mcqs:
        raise HTTPException(
            status_code=404, detail=f"No MCQs found for video title '{video_title}'"
        )

    questions = [
        {
            "id": str(item.id),
            "question": item.question,
            "options": item.options if item.options else None,
            "answer": item.answer,
            "type": "mcq" if item.options else "true_false",
        }
        for item in mcqs
    ]

    if not download:
        return {"video_title": video_title, "questions": questions}

    # Generate downloadable file
    filename = (
        f"{video_title.replace(' ', '_')}_mcqs_"
        f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json"
    )
    filepath = os.path.join("/tmp", filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(
            {"video_title": video_title, "questions": questions},
            f,
            ensure_ascii=False,
            indent=4,
        )

    return FileResponse(
        filepath,
        media_type="application/json",
        filename=filename,
    )
