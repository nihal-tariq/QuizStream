from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.video import Video
from app.db import SessionLocal
from deepgram import Deepgram
from dotenv import load_dotenv
import shutil, os, uuid, re, subprocess, ffmpeg, imageio_ffmpeg
from app.services.embeddings import embed_and_store_transcript

load_dotenv()

router = APIRouter()

# Directories
UPLOAD_DIR = "uploads/videos/"
AUDIO_DIR = "uploads/audio/"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# Deepgram Client
dg_client = Deepgram(os.getenv("DEEPGRAM_API_KEY"))

# ---------- COMMON HELPERS ----------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def sanitize_filename(title: str) -> str:
    """Remove special characters from a string for safe file naming."""
    return re.sub(r'[^A-Za-z0-9_\-]+', '_', title)

def extract_audio(video_path, audio_path):
    """Extract MP3 audio from video using FFmpeg."""
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    (
        ffmpeg.input(video_path)
        .output(audio_path, format='mp3', acodec='libmp3lame')
        .overwrite_output()
        .run(cmd=ffmpeg_path)
    )

def transcribe_audio(audio_path):
    """Transcribe audio file using Deepgram."""
    with open(audio_path, "rb") as audio:
        source = {"buffer": audio, "mimetype": "audio/mpeg"}
        response = dg_client.transcription.sync_prerecorded(source, {"punctuate": True})
        return response['results']['channels'][0]['alternatives'][0]['transcript']

def save_video_and_transcript(title: str, filename: str, filepath: str, transcript: str, db: Session):
    """Save video record and store embeddings."""
    video = Video(title=title, filename=filename, filepath=filepath, transcript=transcript)
    db.add(video)
    db.commit()
    db.refresh(video)
    embed_and_store_transcript(transcript, title)
    return video

# ---------- ROUTES ----------

@router.post("/upload-video/")
def upload_video(title: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    audio_filename = f"{uuid.uuid4()}.mp3"
    audio_path = os.path.join(AUDIO_DIR, audio_filename)
    extract_audio(filepath, audio_path)
    transcript = transcribe_audio(audio_path)

    video = save_video_and_transcript(title, file.filename, filepath, transcript, db)

    return {
        "id": video.id,
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
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to download video: {str(e)}")

    audio_filename = f"{uuid.uuid4()}.mp3"
    audio_path = os.path.join(AUDIO_DIR, audio_filename)
    extract_audio(video_path, audio_path)
    transcript = transcribe_audio(audio_path)

    video = save_video_and_transcript(title, video_filename, video_path, transcript, db)

    return {
        "id": video.id,
        "message": "YouTube video processed and transcribed successfully",
        "transcript": transcript
    }
