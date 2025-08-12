from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.utils.get_db import get_db
from app.models.video import Video
from app.models.mcqs import MCQ
from app.services.mcqs_generation import generate_and_store_mcqs

import logging

get_db()

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.post("/review-video/")
def review_video(title: str, action: str, db: Session = Depends(get_db)):
    """
    Review a video by title.
    - delete: remove video, transcript, and MCQs
    - approve: generate MCQs from transcript
    """
    video = db.query(Video).filter(Video.title == title).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if action.lower() == "delete":
        # Delete related MCQs
        deleted_mcqs = db.query(MCQ).filter(MCQ.video_id == video.id).delete()
        logger.info(f"Deleted {deleted_mcqs} MCQs for video '{title}'")

        # Delete video record
        db.delete(video)
        db.commit()
        return {"message": f"Video '{title}' and related MCQs deleted successfully"}

    elif action.lower() == "approve":
        if not video.transcript:
            raise HTTPException(status_code=400, detail="Transcript missing for this video")

        try:
            generate_and_store_mcqs(video.transcript, video.title, db)
        except Exception as e:
            logger.error(f"MCQ generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"MCQ generation failed: {e}")

        return {"message": f"Video '{title}' approved and MCQs generated successfully"}

    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'delete' or 'approve'.")
