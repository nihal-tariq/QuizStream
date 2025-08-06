from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.models.video import Video
from app.db import SessionLocal
from deepgram import Deepgram
import shutil
import os
import uuid
import ffmpeg
import imageio_ffmpeg
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
UPLOAD_DIR = "uploads/videos/"
AUDIO_DIR = "uploads/audio/"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
dg_client = Deepgram(DEEPGRAM_API_KEY)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def extract_audio(video_path: str, audio_path: str):
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    (
        ffmpeg
        .input(video_path)
        .output(audio_path, format='mp3', acodec='libmp3lame')
        .overwrite_output()
        .run(cmd=ffmpeg_path)
    )

def transcribe_audio(audio_path: str):
    with open(audio_path, "rb") as audio:
        source = {"buffer": audio, "mimetype": "audio/mpeg"}
        response = dg_client.transcription.sync_prerecorded(source, {"punctuate": True})
        return response['results']['channels'][0]['alternatives'][0]['transcript']

@router.post("/upload-video/")
def upload_video(title: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    filepath = os.path.join(UPLOAD_DIR, file.filename)

    # Save video
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract audio
    audio_filename = f"{uuid.uuid4()}.mp3"
    audio_path = os.path.join(AUDIO_DIR, audio_filename)
    extract_audio(filepath, audio_path)

    # Transcribe using Deepgram
    transcript = transcribe_audio(audio_path)

    # Save metadata to DB
    video = Video(
        title=title,
        filename=file.filename,
        filepath=filepath,
        transcript=transcript
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    return {
        "id": str(video.id),
        "message": "Video uploaded and transcribed successfully",
        "transcript": transcript
    }
