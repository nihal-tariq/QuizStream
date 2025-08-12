from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List
import json
import os
from datetime import datetime
from app.models.mcqs import MCQ
from app.utils.get_db import get_db

router = APIRouter(prefix="/view mcqs", tags=["Manage MCQs"])

get_db()

@router.get("/by-title", )
def get_mcqs_by_video_title(
    video_title: str = Query(..., description="Title of the video"),
    download: bool = Query(False, description="If true, returns a downloadable JSON file"),
    db: Session = Depends(get_db)
):
    """
    Fetch MCQs and True/False questions for a given video title.
    - Returns JSON via API by default.
    - If `download=true`, returns a downloadable JSON file.
    """
    mcqs = db.query(MCQ).filter(MCQ.video_title == video_title).all()

    if not mcqs:
        raise HTTPException(status_code=404, detail=f"No MCQs found for video title '{video_title}'")

    data = []
    for item in mcqs:
        entry = {
            "id": str(item.id),  
            "question": item.question,
            "options": item.options if item.options else None,
            "answer": item.answer,
            "type": "mcq" if item.options else "true_false"
        }
        data.append(entry)

    if not download:
        return JSONResponse(content={"video_title": video_title, "questions": data})

    # Create a downloadable file
    filename = f"{video_title.replace(' ', '_')}_mcqs_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json"
    filepath = os.path.join("/tmp", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"video_title": video_title, "questions": data}, f, ensure_ascii=False, indent=4)

    return FileResponse(
        filepath,
        media_type="application/json",
        filename=filename
    )
