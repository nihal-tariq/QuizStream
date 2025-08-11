import os
import re
import uuid
import shutil
import logging
import subprocess
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from deepgram import Deepgram
from dotenv import load_dotenv
import ffmpeg
import imageio_ffmpeg

from app.models.video import Video
from app.db import SessionLocal
from app.services.embeddings import embed_and_store_transcript
from app.services.mcqs_generation import generate_and_store_mcqs

# ------------------ CONFIG ------------------
load_dotenv()
router = APIRouter()

UPLOAD_DIR = "uploads/videos/"
AUDIO_DIR = "uploads/audio/"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

dg_client = Deepgram(os.getenv("DEEPGRAM_API_KEY"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------ HELPERS ------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def sanitize_filename(title: str) -> str:
    return re.sub(r'[^A-Za-z0-9_\-]+', '_', title)

def extract_audio(video_path: str, audio_path: str):
    try:
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        (
            ffmpeg.input(video_path)
            .output(audio_path, format='mp3', acodec='libmp3lame')
            .overwrite_output()
            .run(cmd=ffmpeg_path, quiet=True)
        )
        logger.info(f"Audio extracted to {audio_path}")
    except Exception as e:
        logger.error(f"Error extracting audio: {e}")
        raise HTTPException(status_code=500, detail=f"Audio extraction failed: {e}")

def transcribe_audio(audio_path: str) -> str:
    try:
        with open(audio_path, "rb") as audio:
            source = {"buffer": audio, "mimetype": "audio/mpeg"}
            response = dg_client.transcription.sync_prerecorded(source, {"punctuate": True})
            transcript = response['results']['channels'][0]['alternatives'][0]['transcript']
            logger.info("Audio transcription completed")
            return transcript.strip()
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

def save_video_and_transcript(title: str, filename: str, filepath: str, transcript: str, db: Session):
    try:
        video = Video(title=title, filename=filename, filepath=filepath, transcript=transcript)
        db.add(video)
        db.commit()
        db.refresh(video)
        embed_and_store_transcript(transcript, title)
        logger.info(f"Video saved with ID {video.id}")
        return video
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving video: {e}")
        raise HTTPException(status_code=500, detail=f"Saving video failed: {e}")

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

    try:
        generate_and_store_mcqs(transcript, title, db)
    except Exception as e:
        logger.error(f"MCQ generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"MCQ generation failed: {e}")

    return {
        "id": str(video.id),
        "message": "Video uploaded, transcribed, and MCQs generated successfully",
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

    try:
        generate_and_store_mcqs(transcript, title, db)
    except Exception as e:
        logger.error(f"MCQ generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"MCQ generation failed: {e}")

    return {
        "id": str(video.id),
        "message": "YouTube video processed, transcribed, and MCQs generated successfully",
        "transcript": transcript
    }
