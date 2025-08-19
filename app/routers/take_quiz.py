"""
Quiz Router.

This module provides an endpoint for fetching quiz questions
(MCQs or True/False) for a specific video.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.utils.get_db import get_db
from app.models.mcqs import MCQ


# Router instance
router = APIRouter(prefix="/take-quiz", tags=["Take Quiz"])


# ---------- Pydantic Schemas ---------- #
class QuizQuestionSchema(BaseModel):
    """Schema for a single quiz question."""
    question: str
    options: List[str]


# ---------- Routes ---------- #
@router.get(
    "/{video_title}",
    summary="Fetch quiz questions for a given video",
    response_model=List[QuizQuestionSchema],
)
def get_quiz_questions(video_title: str, db: Session = Depends(get_db)) -> List[QuizQuestionSchema]:
    """
    Fetch all quiz questions (MCQs/True-False) for a given video title,
    excluding the correct answers.

    Args:
        video_title (str): The title of the video to fetch questions for.
        db (Session): Database session dependency.

    Raises:
        HTTPException: If no quiz is found for the video.

    Returns:
        List[QuizQuestionSchema]: List of quiz questions with options only.
    """
    questions = db.query(MCQ).filter(MCQ.video_title == video_title).all()

    if not questions:
        raise HTTPException(status_code=404, detail="No quiz found for this video.")

    return [
        {
            "question": q.question,
            "options": q.options if q.options else ["True", "False"],  # Default for T/F
        }
        for q in questions
    ]
