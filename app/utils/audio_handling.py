import os,  logging
from dotenv import load_dotenv
import ffmpeg
from deepgram import Deepgram
import imageio_ffmpeg
from fastapi import  HTTPException
from app.models.video import Video
from app.services.embeddings import embed_and_store_transcript
from sqlalchemy.orm import Session



load_dotenv()
dg_client = Deepgram(os.getenv("DEEPGRAM_API_KEY"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



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