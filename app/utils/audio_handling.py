"""
Video processing services.
Handles audio extraction, transcription, and storing video with transcript in the database.
"""

import logging
import os

import ffmpeg
import imageio_ffmpeg
from deepgram import Deepgram
from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.video import Video
from app.services.embeddings import embed_and_store_transcript

# Load environment variables
load_dotenv()
dg_client = Deepgram(os.getenv("DEEPGRAM_API_KEY"))

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_audio(video_path: str, audio_path: str):
    """
    Extract audio from a video file and save as MP3.

    Args:
        video_path (str): Path to the input video file.
        audio_path (str): Path to save the extracted audio file.

    Raises:
        HTTPException: If audio extraction fails.
    """
    try:
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        (
            ffmpeg.input(video_path)
            .output(audio_path, format="mp3", acodec="libmp3lame")
            .overwrite_output()
            .run(cmd=ffmpeg_path, quiet=True)
        )
        logger.info("Audio extracted to %s", audio_path)
    except Exception as e:
        logger.error("Error extracting audio: %s", e)
        raise HTTPException(status_code=500, detail=f"Audio extraction failed: {e}")


def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe an audio file using Deepgram.

    Args:
        audio_path (str): Path to the audio file.

    Returns:
        str: Transcribed text.

    Raises:
        HTTPException: If transcription fails.
    """
    try:
        with open(audio_path, "rb") as audio:
            source = {"buffer": audio, "mimetype": "audio/mpeg"}
            response = dg_client.transcription.sync_prerecorded(
                source, {"punctuate": True}
            )
            transcript = response["results"]["channels"][0]["alternatives"][0][
                "transcript"
            ]
            logger.info("Audio transcription completed")
            return transcript.strip()
    except Exception as e:
        logger.error("Transcription error: %s", e)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")


def save_video_and_transcript(
    title: str, filename: str, filepath: str, transcript: str, db: Session
):
    """
    Save video details and transcript to the database, then store embeddings.

    Args:
        title (str): Video title.
        filename (str): Video filename.
        filepath (str): Path to the video file.
        transcript (str): Transcript of the video.
        db (Session): SQLAlchemy session.

    Returns:
        Video: Saved video instance.

    Raises:
        HTTPException: If saving fails.
    """
    try:
        video = Video(
            title=title, filename=filename, filepath=filepath, transcript=transcript
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        embed_and_store_transcript(transcript, title)
        logger.info("Video saved with ID %s", video.id)
        return video
    except Exception as e:
        db.rollback()
        logger.error("Error saving video: %s", e)
        raise HTTPException(status_code=500, detail=f"Saving video failed: {e}")
