# app/routers/video_list.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.video import Video
from app.utils.get_db import get_db

router = APIRouter(prefix="/videos list ", tags=["Videos Management"])


get_db()


@router.get("/", summary="Get all videos with transcript preview")
def list_videos(db: Session = Depends(get_db)):
    videos = db.query(Video).all()

    video_list = []
    for vid in videos:
        preview = (vid.transcript or "").splitlines()[0:3]  # first 3 lines
        preview_text = " ".join(preview).strip()

        video_list.append({
            "id": str(vid.id),
            "title": vid.title,
            "transcript_preview": preview_text
        })

    return {"videos": video_list}
