"""
Video Upload Router.

This module provides endpoints for:
1. Uploading and processing a local video file.
2. Downloading, processing, and transcribing a YouTube video.

Each uploaded video is saved, audio is extracted, transcribed,
and stored in the database with metadata.
"""

import logging
import os
import re
import shutil
import subprocess
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.utils.get_db import get_db
from app.utils.audio_handling import (
    extract_audio,
    transcribe_audio,
    save_video_and_transcript,
)


# Router instance
router = APIRouter(tags=["Video Upload"])

# Directories for storing uploads
UPLOAD_DIR = "uploads/videos/"
AUDIO_DIR = "uploads/audio/"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------- Helper Functions ---------- #
def sanitize_filename(title: str) -> str:
    """
    Sanitize a video title to create a safe filename.

    Args:
        title (str): Original video title.

    Returns:
        str: Sanitized filename-safe version of the title.
    """
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", title)


# ---------- Pydantic Schemas ---------- #
class VideoUploadResponse(BaseModel):
    """Schema for video upload response."""
    id: str
    message: str
    transcript: str


# ---------- Routes ---------- #
@router.post("/upload-video/", response_model=VideoUploadResponse, summary="Upload and process a local video file")
def upload_video(
    title: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> VideoUploadResponse:
    """
    Upload a local video file, extract audio, transcribe it, and save metadata.

    Args:
        title (str): Title of the video.
        file (UploadFile): Video file uploaded by user.
        db (Session): Database session dependency.

    Raises:
        HTTPException: If file saving fails.

    Returns:
        VideoUploadResponse: Process result including transcript.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    safe_title = sanitize_filename(title)
    unique_filename = f"{safe_title}_{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    filepath = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info("Video saved at %s", filepath)
    except Exception as e:
        logger.error("File saving failed: %s", e)
        raise HTTPException(status_code=500, detail=f"File saving failed: {e}")

    audio_filename = f"{uuid.uuid4()}.mp3"
    audio_path = os.path.join(AUDIO_DIR, audio_filename)

    extract_audio(filepath, audio_path)
    transcript = transcribe_audio(audio_path)
    video = save_video_and_transcript(title, unique_filename, filepath, transcript, db)

    return {
        "id": str(video.id),
        "message": "Video uploaded and transcribed successfully",
        "transcript": transcript,
    }


@router.post("/upload-youtube/", response_model=VideoUploadResponse, summary="Download, process and transcribe a YouTube video")
def upload_youtube_video(
    youtube_url: str,
    title: str,
    db: Session = Depends(get_db),
) -> VideoUploadResponse:
    """
    Download a YouTube video, extract audio, transcribe it, and save metadata.

    Args:
        youtube_url (str): URL of the YouTube video.
        title (str): Title to assign to the downloaded video.
        db (Session): Database session dependency.

    Raises:
        HTTPException: If YouTube download fails.

    Returns:
        VideoUploadResponse: Process result including transcript.
    """
    safe_title = sanitize_filename(title)
    video_filename = f"{safe_title}_{uuid.uuid4()}.mp4"
    video_path = os.path.join(UPLOAD_DIR, video_filename)

    try:
        subprocess.run(["yt-dlp", "-o", video_path, youtube_url], check=True)
        logger.info("YouTube video downloaded to %s", video_path)
    except subprocess.CalledProcessError as e:
        logger.error("YouTube download failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to download video: {e}")

    audio_filename = f"{uuid.uuid4()}.mp3"
    audio_path = os.path.join(AUDIO_DIR, audio_filename)

    extract_audio(video_path, audio_path)
    transcript = transcribe_audio(audio_path)
    video = save_video_and_transcript(title, video_filename, video_path, transcript, db)

    return {
        "id": str(video.id),
        "message": "YouTube video processed and transcribed successfully",
        "transcript": transcript,
    }
