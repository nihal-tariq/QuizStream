import os, re, uuid, shutil, logging, subprocess

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.utils.get_db import get_db
from app.utils.audio_handling import extract_audio, transcribe_audio, save_video_and_transcript

router = APIRouter(tags=['Video Upload'])

UPLOAD_DIR = "uploads/videos/"
AUDIO_DIR = "uploads/audio/"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


get_db()

def sanitize_filename(title: str) -> str:
    """Ensure file name is safe for storage."""
    return re.sub(r'[^A-Za-z0-9_\-]+', '_', title)


# ------------------ ROUTES ------------------
@router.post("/upload-video/")
def upload_video(title: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    safe_title = sanitize_filename(title)
    unique_filename = f"{safe_title}_{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    filepath = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Video saved at {filepath}")
    except Exception as e:
        logger.error(f"File saving failed: {e}")
        raise HTTPException(status_code=500, detail=f"File saving failed: {e}")

    audio_filename = f"{uuid.uuid4()}.mp3"
    audio_path = os.path.join(AUDIO_DIR, audio_filename)

    extract_audio(filepath, audio_path)
    transcript = transcribe_audio(audio_path)
    video = save_video_and_transcript(title, unique_filename, filepath, transcript, db)

    return {
        "id": str(video.id),
        "message": "Video uploaded and transcribed successfully",
        "transcript": transcript
    }


@router.post("/upload-youtube/")
def upload_youtube_video(youtube_url: str, title: str, db: Session = Depends(get_db)):
    safe_title = sanitize_filename(title)
    video_filename = f"{safe_title}_{uuid.uuid4()}.mp4"
    video_path = os.path.join(UPLOAD_DIR, video_filename)

    try:
        subprocess.run(
            ["yt-dlp", "-o", video_path, youtube_url],
            check=True
        )
        logger.info(f"YouTube video downloaded to {video_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"YouTube download failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download video: {e}")

    audio_filename = f"{uuid.uuid4()}.mp3"
    audio_path = os.path.join(AUDIO_DIR, audio_filename)

    extract_audio(video_path, audio_path)
    transcript = transcribe_audio(audio_path)
    video = save_video_and_transcript(title, video_filename, video_path, transcript, db)

    return {
        "id": str(video.id),
        "message": "YouTube video processed and transcribed successfully",
        "transcript": transcript
    }
