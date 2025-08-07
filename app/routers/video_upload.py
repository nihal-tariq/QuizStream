from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.models.video import Video
from app.db import SessionLocal
from deepgram import Deepgram
import shutil, os, uuid, ffmpeg, imageio_ffmpeg
from dotenv import load_dotenv
from app.services.embeddings import embed_and_store_transcript

load_dotenv()
router = APIRouter()
UPLOAD_DIR = "uploads/videos/"
AUDIO_DIR = "uploads/audio/"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

dg_client = Deepgram(os.getenv("DEEPGRAM_API_KEY"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def extract_audio(video_path, audio_path):
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    (
        ffmpeg.input(video_path)
        .output(audio_path, format='mp3', acodec='libmp3lame')
        .overwrite_output()
        .run(cmd=ffmpeg_path)
    )


def transcribe_audio(audio_path):
    with open(audio_path, "rb") as audio:
        source = {"buffer": audio, "mimetype": "audio/mpeg"}
        response = dg_client.transcription.sync_prerecorded(source, {"punctuate": True})
        return response['results']['channels'][0]['alternatives'][0]['transcript']


@router.post("/upload-video/")
def upload_video(title: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    audio_filename = f"{uuid.uuid4()}.mp3"
    audio_path = os.path.join(AUDIO_DIR, audio_filename)
    extract_audio(filepath, audio_path)
    transcript = transcribe_audio(audio_path)

    video = Video(title=title, filename=file.filename, filepath=filepath, transcript=transcript)
    db.add(video)
    db.commit()
    db.refresh(video)

    embed_and_store_transcript(transcript, title)

    return {
        "id": video.id,
        "message": "Video uploaded and transcribed successfully",
        "transcript": transcript
    }
