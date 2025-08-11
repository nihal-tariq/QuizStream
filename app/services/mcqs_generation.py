import os
import re
import uuid
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.models.mcqs import MCQ
from google import genai

logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Gemini client
api_key = os.getenv("GEMINI_FLASH_KEY")
if not api_key:
    raise ValueError("GEMINI_FLASH_KEY is not set in environment variables.")
client = genai.Client(api_key=api_key)


def extract_json_from_text(text: str) -> str:
    """
    Extract valid JSON from Gemini output, stripping markdown fences or extra text.
    Ensures we return only the JSON array.
    """
    if not text:
        return text

    text = text.strip()

    # Remove markdown JSON fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text, flags=re.IGNORECASE).strip()
        if text.endswith("```"):
            text = text[:-3].strip()

    # If there's a JSON array inside the text, extract it
    if "[" in text and "]" in text:
        start = text.index("[")
        end = text.rindex("]") + 1
        return text[start:end]

    return text


def generate_and_store_mcqs(transcript: str, video_title: str, db: Session):
    """
    Generate MCQs and True/False questions from transcript using Gemini 2.5 Flash
    and store them in the MCQ table with video_title.
    """
    if not transcript or not transcript.strip():
        raise ValueError("Transcript is empty. Cannot generate MCQs.")

    prompt = f"""
    You are an educational quiz generator.
    Based on the transcript below, create:
    - 5 Multiple Choice Questions (4 options each, only 1 correct answer)
    - 5 True/False questions

    Return ONLY valid JSON in the following format:
    [
        {{
            "question": "...",
            "options": ["A", "B", "C", "D"],  
            "answer": "...",
            "type": "mcq"
        }},
        {{
            "question": "...",
            "answer": "True" or "False",
            "type": "true_false"
        }}
    ]

    Transcript:
    {transcript}
    """

    logger.info("Calling Gemini API for MCQ generation...")
    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt
        )
    except Exception as e:
        logger.exception("Gemini API call failed")
        raise RuntimeError(f"Gemini API call failed: {e}")

    # Get raw response text
    try:
        raw_text = getattr(response, "text", None) or getattr(response, "output_text", None) or str(response)
        logger.debug(f"Raw Gemini output (first 500 chars): {raw_text[:500]}")

        clean_text = extract_json_from_text(raw_text)
        mcqs_data = json.loads(clean_text)

        if not isinstance(mcqs_data, list):
            raise ValueError("Parsed JSON is not a list.")
    except Exception as e:
        logger.error(f"Invalid JSON from Gemini: {e}")
        raise ValueError(f"Gemini response is not valid JSON: {e}")

    # Store MCQs in database
    logger.info(f"Storing {len(mcqs_data)} MCQs in database...")
    try:
        for item in mcqs_data:
            mcq_entry = MCQ(
                id=uuid.uuid4(),
                video_title=video_title,
                question=item.get("question"),
                options=item.get("options") if item.get("type") == "mcq" else None,
                answer=item.get("answer"),
                created_at=datetime.utcnow()
            )
            db.add(mcq_entry)

        db.commit()
        logger.info(f"✅ Stored {len(mcqs_data)} MCQs for '{video_title}'")

    except Exception as e:
        db.rollback()
        logger.exception("Database insert failed for MCQs")
        raise RuntimeError(f"Failed to store MCQs: {e}")

    return {"message": f"{len(mcqs_data)} questions stored successfully"}
