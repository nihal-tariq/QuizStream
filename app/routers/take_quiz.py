# app/routers/take_quiz.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.utils.get_db import get_db
from app.models.mcqs import MCQ


get_db()

router = APIRouter(prefix="/take_quiz", tags=["Take Quiz"])

@router.get("/{video_title}")
def get_quiz_questions(video_title: str, db: Session = Depends(get_db)):
    """
    Fetch all MCQs/True-False questions for a given video title,
    excluding the correct answers.
    """
    questions = (
        db.query(MCQ)
        .filter(MCQ.video_title == video_title)
        .all()
    )

    if not questions:
        raise HTTPException(status_code=404, detail="No quiz found for this video.")

    # Return only question text and options
    return [
        {
            "question": q.question,
            "options": q.options if q.options else ["True", "False"]  # Default for T/F
        }
        for q in questions
    ]
