import json
import logging
import os
import re
import uuid
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy.orm import Session
from pathlib import Path
from jinja2 import Template

from app.models.mcqs import MCQ
import google.generativeai as genai

logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("GEMINI_FLASH_KEY")
if not api_key:
    raise ValueError("GEMINI_FLASH_KEY not found in .env")

genai.configure(api_key=api_key)


def load_prompt_template(name: str) -> Template:
    """
    Load a Jinja2 template from the prompts directory.

    Args:
        name (str): The base name of the prompt file (without extension).

    Returns:
        Template: A compiled Jinja2 template ready for rendering.
    """
    prompt_path = Path("app/prompts") / f"{name}.txt"
    text = prompt_path.read_text(encoding="utf-8")
    return Template(text)


def extract_json_from_text(text: str) -> str:
    """
    Extract valid JSON from Gemini output, stripping markdown fences or extra text.

    Args:
        text (str): Raw text output from Gemini.

    Returns:
        str: Extracted JSON string.
    """
    if not text:
        return text

    text = text.strip()

    # Remove markdown JSON fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text, flags=re.IGNORECASE).strip()
        if text.endswith("```"):
            text = text[:-3].strip()

    # Extract JSON array if present
    if "[" in text and "]" in text:
        start = text.index("[")
        end = text.rindex("]") + 1
        return text[start:end]

    return text


def generate_and_store_mcqs(transcript: str, video_title: str, db: Session):
    """
    Generate MCQs and True/False questions from a transcript using Gemini 2.5 Flash
    and store them in the database.

    Args:
        transcript (str): Transcript text of the video.
        video_title (str): Title of the associated video.
        db (Session): SQLAlchemy session.

    Returns:
        dict: Summary message of stored questions.

    Raises:
        ValueError: If transcript is empty or Gemini response is invalid JSON.
        RuntimeError: If API call or DB insert fails.
    """
    if not transcript or not transcript.strip():
        raise ValueError("Transcript is empty. Cannot generate MCQs.")

    # Load and render MCQ generation prompt
    template = load_prompt_template("mcq_generator")
    prompt = template.render(transcript=transcript)

    logger.info("Calling Gemini API for MCQ generation...")

    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        response = model.generate_content(prompt)
    except Exception as e:
        logger.exception("Gemini API call failed")
        raise RuntimeError(f"Gemini API call failed: {e}")

    try:
        raw_text = getattr(response, "text", None) or getattr(
            response, "output_text", None
        ) or str(response)

        logger.debug("Raw Gemini output (first 500 chars): %s", raw_text[:500])

        clean_text = extract_json_from_text(raw_text)
        mcqs_data = json.loads(clean_text)

        if not isinstance(mcqs_data, list):
            raise ValueError("Parsed JSON is not a list.")
    except Exception as e:
        logger.error("Invalid JSON from Gemini: %s", e)
        raise ValueError(f"Gemini response is not valid JSON: {e}")

    logger.info("Storing %d MCQs in database...", len(mcqs_data))
    try:
        for item in mcqs_data:
            mcq_entry = MCQ(
                id=uuid.uuid4(),
                video_title=video_title,
                question=item.get("question"),
                options=item.get("options") if item.get("type") == "mcq" else None,
                answer=item.get("answer"),
                created_at=datetime.utcnow(),
            )
            db.add(mcq_entry)

        db.commit()
        logger.info("✅ Stored %d MCQs for '%s'", len(mcqs_data), video_title)
    except Exception as e:
        db.rollback()
        logger.exception("Database insert failed for MCQs")
        raise RuntimeError(f"Failed to store MCQs: {e}")

    return {"message": f"{len(mcqs_data)} questions stored successfully"}

