"""
Video Approval Router.

This module provides an endpoint for reviewing videos:
- Approve: generates MCQs from transcript.
- Delete: removes video, transcript, and related MCQs.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.video import Video
from app.models.mcqs import MCQ
from app.services.mcqs_generation import generate_and_store_mcqs
from app.utils.get_db import get_db


# Router instance
router = APIRouter(prefix="/videos-approval", tags=["Videos Management"])

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------- Pydantic Schemas ---------- #
class ReviewVideoRequest(BaseModel):
    """Schema for reviewing a video."""
    title: str
    action: str


class ReviewVideoResponse(BaseModel):
    """Schema for review response."""
    message: str


# ---------- Routes ---------- #
@router.post(
    "/review-video/",
    summary="Review a video by approving or deleting",
    response_model=ReviewVideoResponse,
)
def review_video(
    title: str,
    action: str,
    db: Session = Depends(get_db),
) -> ReviewVideoResponse:
    """
    Review a video by title.

    Actions:
    - **delete**: Remove the video, transcript, and related MCQs.
    - **approve**: Generate MCQs from the transcript.

    Args:
        title (str): Title of the video to review.
        action (str): Action to perform ("delete" or "approve").
        db (Session): Database session dependency.

    Raises:
        HTTPException: If the video is not found, transcript is missing,
                       or MCQ generation fails.

    Returns:
        ReviewVideoResponse: Confirmation message about the performed action.
    """
    video = db.query(Video).filter(Video.title == title).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if action.lower() == "delete":
        # Delete related MCQs
        deleted_mcqs = db.query(MCQ).filter(MCQ.video_id == video.id).delete()
        logger.info("Deleted %s MCQs for video '%s'", deleted_mcqs, title)

        # Delete video record
        db.delete(video)
        db.commit()
        return {"message": f"Video '{title}' and related MCQs deleted successfully"}

    elif action.lower() == "approve":
        if not video.transcript:
            raise HTTPException(
                status_code=400, detail="Transcript missing for this video"
            )

        try:
            generate_and_store_mcqs(video.transcript, video.title, db)
        except Exception as e:
            logger.error("MCQ generation failed: %s", e)
            raise HTTPException(status_code=500, detail=f"MCQ generation failed: {e}")

        return {"message": f"Video '{title}' approved and MCQs generated successfully"}

    else:
        raise HTTPException(
            status_code=400, detail="Invalid action. Use 'delete' or 'approve'."
        )
