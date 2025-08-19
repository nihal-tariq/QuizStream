"""
Video Management Router.

This module provides endpoints to retrieve a list of uploaded videos
with transcript previews.
"""

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.video import Video
from app.utils.get_db import get_db


# Router instance
router = APIRouter(prefix="/videos", tags=["Videos Management"])


# ---------- Pydantic Schemas ---------- #
class VideoPreviewSchema(BaseModel):
    """Schema for video preview response."""
    id: str
    title: str
    transcript_preview: str


class VideoListResponse(BaseModel):
    """Schema for response containing multiple videos."""
    videos: List[VideoPreviewSchema]


# ---------- Routes ---------- #
@router.get("/", summary="Get all videos with transcript preview", response_model=VideoListResponse)
def list_videos(db: Session = Depends(get_db)) -> VideoListResponse:
    """
    Retrieve all videos with their transcript preview.

    Args:
        db (Session): Database session dependency.

    Returns:
        VideoListResponse: List of videos with basic info and transcript preview.
    """
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
